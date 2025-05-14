import os
import logging
from dotenv import load_dotenv
import psycopg
from util import DB_CONFIG

load_dotenv(dotenv_path=".env.production")
logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")


def drop_vector_index():
    with psycopg.connect(**DB_CONFIG) as conn:
        with conn.cursor() as cur:
            cur.execute(f"SET search_path TO {os.getenv('DB_SCHEMA', 'chapchap')}")
            cur.execute(
                "DROP INDEX IF EXISTS idx_job_qualification_sentences_embedding"
            )
            cur.execute("DROP INDEX IF EXISTS idx_job_embeddings_embedding")
            conn.commit()


if __name__ == "__main__":
    drop_vector_index()
