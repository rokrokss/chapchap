from langchain.chat_models import init_chat_model
from core.config import settings
from typing import Optional
from langgraph.graph import StateGraph
from langgraph.graph.message import add_messages
from langgraph.graph.state import CompiledStateGraph
import structlog
from typing_extensions import TypedDict
from typing import Annotated
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from psycopg_pool import AsyncConnectionPool


class State(TypedDict):
    messages: Annotated[list, add_messages]


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

    async def close(self):
        await self._db_pool.close()
