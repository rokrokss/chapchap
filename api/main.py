from fastapi import FastAPI
from routers import job_info
from contextlib import asynccontextmanager
from db.connection import get_db

from fastapi.middleware.cors import CORSMiddleware


origins = [
    "http://localhost:5173",
]


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.db = await get_db()
    yield
    await app.state.db.close()


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(job_info.router)
