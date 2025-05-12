import time
import uuid

import structlog
from fastapi import FastAPI, Request, Response
from routers.router import router
from contextlib import asynccontextmanager
from core.config import settings
from fastapi.middleware.cors import CORSMiddleware
from uvicorn.protocols.utils import get_path_with_query_string
from psycopg_pool import AsyncConnectionPool
from core.graph import LangGraphAgent
from core.logging import setup_logging

setup_logging(json_logs=settings.LOG_JSON_FORMAT, log_level=settings.LOG_LEVEL)

access_logger = structlog.stdlib.get_logger("api.access")


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.db_pool = AsyncConnectionPool(
        conninfo=str(settings.POSTGRES_URL),
        open=False,
        max_size=settings.POSTGRES_POOL_SIZE,
        max_lifetime=settings.POSTGRES_CONNECTION_MAX_LIFETIME,
        max_idle=settings.POSTGRES_CONNECTION_MAX_IDLE,
        kwargs={
            "prepare_threshold": None,
            "options": f"-c search_path={settings.POSTGRES_SCHEMA}",
        },
    )
    await app.state.db_pool.open(wait=True)
    logger = structlog.stdlib.get_logger("api.access")
    logger.info(
        "app_db_pool_created",
        max_size=settings.POSTGRES_POOL_SIZE,
        max_lifetime=settings.POSTGRES_CONNECTION_MAX_LIFETIME,
        max_idle=settings.POSTGRES_CONNECTION_MAX_IDLE,
    )
    app.state.agent = await LangGraphAgent.create()
    yield
    await app.state.db_pool.close()
    await app.state.agent.close()


app = FastAPI(title=settings.PROJECT_NAME, version=settings.VERSION, lifespan=lifespan)


@app.middleware("http")
async def logging_middleware(request: Request, call_next) -> Response:
    structlog.contextvars.clear_contextvars()
    # These context vars will be added to all log entries emitted during the request

    start_time = time.perf_counter_ns()
    # If the call_next raises an error, we still want to return our own 500 response,
    # so we can add headers to it (process time, request ID...)
    response = Response(status_code=500)
    try:
        response = await call_next(request)
    except Exception:
        # TODO: Validate that we don't swallow exceptions (unit test?)
        structlog.stdlib.get_logger("api.error").exception("Uncaught exception")
        raise
    finally:
        process_time = time.perf_counter_ns() - start_time
        status_code = response.status_code
        url = get_path_with_query_string(request.scope)
        client_host = request.client.host
        client_port = request.client.port
        http_method = request.method
        http_version = request.scope["http_version"]
        # Recreate the Uvicorn access log format, but add all parameters as structured information
        access_logger.info(
            f"""{client_host}:{client_port} - "{http_method} {url} HTTP/{http_version}" {status_code}""",
            http={
                "url": str(request.url),
                "status_code": status_code,
                "method": http_method,
                "version": http_version,
            },
            network={"client": {"ip": client_host, "port": client_port}},
            duration=process_time,
        )
        response.headers["X-Process-Time"] = str(process_time / 10**9)
        return response


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/health")
async def health_check():
    """Health check endpoint.

    Returns:
        dict: Health status information.
    """
    logger = structlog.stdlib.get_logger("chapchapai.health")
    logger.info("health_check_called")
    return {"status": "healthy", "version": "1.0.0"}
