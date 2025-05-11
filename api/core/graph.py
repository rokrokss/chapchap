from langchain.chat_models import init_chat_model
from core.config import settings
from typing import Optional, AsyncGenerator, Annotated, Literal
from langgraph.graph import StateGraph
from langgraph.graph.message import add_messages
from langgraph.graph.state import CompiledStateGraph
import structlog
from typing_extensions import TypedDict
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from psycopg_pool import AsyncConnectionPool
from pydantic import BaseModel, Field
from openai import AsyncOpenAI
from typing import List
import numpy as np
from psycopg.rows import dict_row

DONE_TOKEN = "[[DONE]]"


class JobMatch(TypedDict):
    job_id: int
    distance: float


class MatchJobState(TypedDict):
    messages: Annotated[list, add_messages]
    resume_text: str
    named_company_experiences: list[int]
    summary_sentences: list[str]
    sentence_embeddings: list[list[float]]
    avg_embedding: list[float]
    retrieved_matches: list[JobMatch]


class Message(BaseModel):
    role: Literal["user", "assistant", "system"] = Field(
        ..., description="The role of the message sender"
    )
    content: str = Field(..., description="The content of the message")


class LangGraphAgent:
    def __init__(self):
        self.logger = structlog.stdlib.get_logger("graph")
        self.model = init_chat_model(
            settings.LLM_MODEL,
            temperature=settings.DEFAULT_LLM_TEMPERATURE,
        )
        self.graph: Optional[CompiledStateGraph] = None
        self._db_pool: Optional[AsyncConnectionPool] = None
        self._openai_client = AsyncOpenAI()
        self.logger.info(
            "llm_initialized",
            model=settings.LLM_MODEL,
            environment=settings.ENVIRONMENT.value,
        )

    # summary
    async def _resume_summary(self, state: MatchJobState) -> dict:
        return {
            "messages": [await self.model.ainvoke(state["messages"])],
        }

    async def stream_resume_summary(
        self, messages: list[Message], session_id: str
    ) -> AsyncGenerator[str, None]:
        config = {"configurable": {"thread_id": session_id}}

        try:
            async for token, _ in self.graph.astream(
                {
                    "messages": [message.model_dump() for message in messages],
                },
                config,
                stream_mode="messages",
            ):
                try:
                    yield token.content
                except Exception as e:
                    self.logger.error(
                        "error_processing_token", error=str(e), session_id=session_id
                    )
                    raise e
            yield DONE_TOKEN
        except Exception as e:
            self.logger.error("error_stream", error=str(e), session_id=session_id)
            raise e

    async def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        self.logger.info(f"임베딩 요청 ({len(texts)} 문장)")
        response = await self._openai_client.embeddings.create(
            input=texts, model=settings.OPENAI_EMBEDDING_MODEL
        )
        return [item.embedding for item in response.data]

    # match
    async def _embed_resume(self, state: MatchJobState) -> dict:
        embeddings = await self.get_embeddings(state["summary_sentences"])
        avg_embedding = np.mean(embeddings, axis=0).tolist()
        return {
            "sentence_embeddings": embeddings,
            "avg_embedding": avg_embedding,
        }

    async def _retrieve_matches(self, state: MatchJobState) -> dict:
        avg_embedding = state["avg_embedding"]
        async with self._db_pool.connection() as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute(
                    """
                        SELECT
                            job_id, embedding <=> %s::vector AS distance
                        FROM job_embeddings
                        ORDER BY distance
                        LIMIT 10
                    """,
                    (avg_embedding,),
                )
                rows = await cur.fetchall()
                state["retrieved_matches"] = [
                    JobMatch(job_id=row["job_id"], distance=row["distance"])
                    for row in rows
                ]
        return state

    @classmethod
    async def create(cls) -> "LangGraphAgent":
        agent = cls()
        await agent._get_connection_pool()
        await agent._create_graph()
        return agent

    async def _get_connection_pool(self) -> AsyncConnectionPool:
        self._db_pool = AsyncConnectionPool(
            conninfo=str(settings.POSTGRES_URL),
            open=False,
            max_size=settings.LLM_DB_POOL_SIZE,
            kwargs={
                "autocommit": True,
                "options": f"-c search_path={settings.POSTGRES_SCHEMA}",
            },
        )
        await self._db_pool.open(wait=True)
        return self._db_pool

    async def _create_graph(self):
        checkpointer = AsyncPostgresSaver(self._db_pool)
        await checkpointer.setup()

        graph_builder = StateGraph(MatchJobState)
        graph_builder.add_node("resume_summary", self._resume_summary)
        graph_builder.add_node("embed_resume", self._embed_resume)
        graph_builder.add_node("retrieve_matches", self._retrieve_matches)
        graph_builder.add_edge("resume_summary", "embed_resume")
        graph_builder.add_edge("embed_resume", "retrieve_matches")
        graph_builder.set_entry_point("resume_summary")
        graph_builder.set_finish_point("retrieve_matches")

        self.graph = graph_builder.compile(
            checkpointer=checkpointer,
            name="chapchap_graph",
            interrupt_before=["embed_resume"],
        )

    async def clear_chat_history(self, session_id: str) -> None:
        async with self._db_pool.connection() as conn:
            async with conn.cursor() as cur:
                for table in settings.CHECKPOINT_TABLES:
                    await cur.execute(
                        f"""
                        DELETE FROM {table}
                        WHERE thread_id = %s
                        """,
                        (session_id,),
                    )
                    self.logger.info(f"Cleared {table} for session {session_id}")

    async def close(self):
        await self._db_pool.close()
