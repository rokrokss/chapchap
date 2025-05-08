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
from langchain_core.messages.human import HumanMessage
from langchain_core.messages.ai import AIMessage


class State(TypedDict):
    messages: Annotated[list, add_messages]


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
        self._graph: Optional[CompiledStateGraph] = None
        self._db_pool: Optional[AsyncConnectionPool] = None

        self.logger.info(
            "llm_initialized",
            model=settings.LLM_MODEL,
            environment=settings.ENVIRONMENT.value,
        )

    async def _chat(self, state: State) -> dict:
        return {"messages": [await self.model.ainvoke(state["messages"])]}

    async def get_response(
        self, messages: list[Message], session_id: str
    ) -> list[dict]:
        config = {"configurable": {"thread_id": session_id}}
        # self.logger.info("get_response", messages=messages)
        response = await self._graph.ainvoke(
            {
                "messages": [message.model_dump() for message in messages],
                "session_id": session_id,
            },
            config,
        )
        response_messages = []
        for m in response["messages"]:
            if isinstance(m, HumanMessage):
                response_messages.append(Message(role="user", content=m.content))
            elif isinstance(m, AIMessage):
                response_messages.append(Message(role="assistant", content=m.content))
        return response_messages

    async def get_stream_response(
        self, messages: list[Message], session_id: str
    ) -> AsyncGenerator[Message, None]:
        config = {"configurable": {"thread_id": session_id}}

        try:
            async for token, _ in self._graph.astream(
                {
                    "messages": [message.model_dump() for message in messages],
                    "session_id": session_id,
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
        except Exception as e:
            self.logger.error("error_stream", error=str(e), session_id=session_id)
            raise e

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

    async def _create_graph(self) -> Optional[CompiledStateGraph]:
        checkpointer = AsyncPostgresSaver(self._db_pool)
        await checkpointer.setup()

        graph_builder = StateGraph(State)
        graph_builder.add_node("chat", self._chat)
        graph_builder.set_entry_point("chat")

        self._graph = graph_builder.compile(
            checkpointer=checkpointer, name="chapchap_agent"
        )
        return self._graph

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
