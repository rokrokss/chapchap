import os
import logging
from dotenv import load_dotenv
import psycopg
from util import DB_CONFIG

load_dotenv(dotenv_path=".env.production")
logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")

CHECKPOINT_TABLES = [
    "checkpoint_blobs",
    "checkpoint_writes",
    "checkpoints",
]


def drop_vector_index():
    with psycopg.connect(**DB_CONFIG) as conn:
        with conn.cursor() as cur:
            for table in CHECKPOINT_TABLES:
                cur.execute(
                    f"""
                    DELETE FROM chapchap.{table}
                    """
                )
        conn.commit()


if __name__ == "__main__":
    drop_vector_index()
