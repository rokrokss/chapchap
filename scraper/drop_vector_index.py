import os
import logging
from dotenv import load_dotenv
import psycopg

load_dotenv(dotenv_path=".env.production")
logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")

DB_CONFIG = {
    "dbname": os.getenv("DB_NAME", "postgres"),
    "user": os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASSWORD", "postgres"),
    "host": os.getenv("DB_HOST", "localhost"),
    "port": os.getenv("DB_PORT", "54322"),
    "options": f"-c search_path={os.getenv('DB_SCHEMA', 'chapchap')}",
}


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
