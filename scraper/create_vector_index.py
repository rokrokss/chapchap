import os
import logging
from dotenv import load_dotenv
import psycopg
from pgvector.psycopg import register_vector
from util import DB_CONFIG

load_dotenv(dotenv_path=".env.production")
logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")


def create_vector_index():
    with psycopg.connect(**DB_CONFIG) as conn:
        with conn.cursor() as cur:
            cur.execute(f"SET search_path TO {os.getenv('DB_SCHEMA', 'chapchap')}")
            cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
            cur.execute("ALTER EXTENSION vector SET SCHEMA chapchap;")
            register_vector(conn)
            cur.execute(
                "CREATE INDEX idx_job_qualification_sentences_embedding ON job_qualification_sentences USING hnsw (embedding vector_cosine_ops);"
            )
            cur.execute(
                "CREATE INDEX idx_job_embeddings_embedding ON job_embeddings USING hnsw (embedding vector_cosine_ops);"
            )
            conn.commit()


if __name__ == "__main__":
    create_vector_index()
