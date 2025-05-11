import os
import logging
from dotenv import load_dotenv
import psycopg
from openai import OpenAI
import numpy as np
from typing import List, Dict
from collections import defaultdict

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

client = OpenAI()


def get_embeddings(texts: List[str]) -> List[List[float]]:
    logging.info(f"임베딩 요청 ({len(texts)} 문장)")
    response = client.embeddings.create(input=texts, model="text-embedding-3-small")
    return [item.embedding for item in response.data]


def embed_and_store_sentences():
    query = """
        SELECT job_id, type, sentence_index, sentence
        FROM chapchap.job_qualification_sentences
        ORDER BY job_id, type, sentence_index
    """

    job_sentences = defaultdict(list)

    with psycopg.connect(**DB_CONFIG) as conn:
        conn.autocommit = False
        with conn.cursor() as cur:
            cur.execute(query)
            rows = cur.fetchall()

        for job_id, type_, idx, sentence in rows:
            job_sentences[job_id].append(
                {"type": type_, "sentence_index": idx, "sentence": sentence}
            )

        total_jobs = len(job_sentences)
        with conn.cursor() as cur:
            cur.execute(f"SET search_path TO {os.getenv('DB_SCHEMA', 'chapchap')}")
            for i, (job_id, sentence_rows) in enumerate(job_sentences.items(), 1):
                try:
                    logging.info(f"▶️ ({i}/{total_jobs}) {job_id} 임베딩 시작")

                    sentences = [row["sentence"] for row in sentence_rows]
                    embeddings = get_embeddings(sentences)
                    avg_embedding = np.mean(embeddings, axis=0).tolist()

                    for i, embedding in enumerate(embeddings):
                        row = sentence_rows[i]
                        cur.execute(
                            """
                            UPDATE job_qualification_sentences SET
                                embedding = %s
                            WHERE job_id = %s AND type = %s AND sentence_index = %s
                            """,
                            (embedding, job_id, row["type"], row["sentence_index"]),
                        )

                    cur.execute(
                        "SELECT job_id FROM job_embeddings WHERE job_id = %s", (job_id,)
                    )
                    existing_job_embedding = cur.fetchone()

                    if existing_job_embedding:
                        cur.execute(
                            """
                            UPDATE job_embeddings SET
                                embedding = %s
                            WHERE job_id = %s
                            """,
                            (avg_embedding, job_id),
                        )
                    else:
                        cur.execute(
                            """
                            INSERT INTO job_embeddings (job_id, embedding)
                            VALUES (%s, %s)
                            """,
                            (job_id, avg_embedding),
                        )

                    conn.commit()
                    logging.info(f"✅ {job_id} 처리 완료")

                except Exception as e:
                    conn.rollback()
                    logging.error(f"❌ {job_id} 처리 중 오류 발생: {e}")


if __name__ == "__main__":
    embed_and_store_sentences()
