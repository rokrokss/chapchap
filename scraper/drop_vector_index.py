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
            cur.execute(
                "DROP INDEX IF EXISTS chapchap.idx_job_qualification_sentences_embedding"
            )
            cur.execute("DROP INDEX IF EXISTS chapchap.idx_job_embeddings_embedding")
            cur.execute(
                """
                UPDATE chapchap.job_embeddings
                SET embedding = NULL
                FROM chapchap.job_info
                WHERE chapchap.job_embeddings.job_id = chapchap.job_info.id
                  AND chapchap.job_info.is_active = false;
                """
            )
            cur.execute(
                """
                UPDATE chapchap.job_qualification_sentences
                SET embedding = NULL
                FROM chapchap.job_info
                WHERE chapchap.job_qualification_sentences.job_id = chapchap.job_info.id
                  AND chapchap.job_info.is_active = false;
                """
            )
        conn.commit()


if __name__ == "__main__":
    drop_vector_index()
