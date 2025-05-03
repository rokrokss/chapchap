import os
import logging
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from typing import List, Dict, Optional, Union
from pydantic import BaseModel
from google import genai
from google.genai import types
from datetime import datetime, date
import psycopg

load_dotenv()
logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")

DB_CONFIG = {
    "dbname": os.getenv("DB_NAME", "postgres"),
    "user": os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASSWORD", "postgres"),
    "host": os.getenv("DB_HOST", "localhost"),
    "port": os.getenv("DB_PORT", "54322"),
    "options": f"-c search_path={os.getenv('DB_SCHEMA', 'chapssal')}",
}


def get_tag(job_title: str) -> List[str]:
    tags = []
    job_title = job_title.lower()

    if (
        "ai " in job_title
        or "machine learning" in job_title
        or "deep learning" in job_title
        or "머신러닝" in job_title
        or "딥러닝" in job_title
        or "rpa" in job_title
        or "추천" in job_title
        or "computer vision" in job_title
        or "data scien" in job_title
        or "ml" in job_title
        or "데이터과학자" in job_title
        or "senior staff engineer, growth engineering" in job_title
    ):
        tags.append("AI")
    if "sre" in job_title or "reliability" in job_title:
        tags.append("SRE")
    if (
        "back-end" in job_title
        or "백엔드" in job_title
        or "backend" in job_title
        or "be " in job_title
        or "플랫폼 개발" in job_title
        or "서버 개발" in job_title
        or "server engineer" in job_title
    ):
        tags.append("BE")
    if (
        "front-end" in job_title
        or "프론트엔드" in job_title
        or "frontend" in job_title
        or "도구개발" in job_title
    ):
        tags.append("FE")
    if "security" in job_title or "보안 " in job_title:
        tags.append("보안")
    if (
        "systems engineer" in job_title
        or "system engineer" in job_title
        or "시스템 엔지니어" in job_title
        or "data center" in job_title
        or "system developer" in job_title
    ):
        tags.append("SE")
    if "network engineer" in job_title:
        tags.append("NE")
    if (
        "data engineer" in job_title
        or "engineer, data" in job_title
        or "bi engineer" in job_title
        or "데이터엔지니어" in job_title
    ):
        tags.append("DE")

    if (
        "안드로이드" in job_title
        or "ios" in job_title
        or "react native" in job_title
        or "flutter" in job_title
        or "mobile" in job_title
        or "android" in job_title
    ):
        tags.append("앱")
    if (
        "qa" in job_title
        or "test engineer" in job_title
        or "test automation" in job_title
    ):
        tags.append("QA")
    if "데이터분석" in job_title or "data analyst" in job_title:
        tags.append("DA")
    if "db " in job_title or "데이터베이스" in job_title or "hbase " in job_title:
        tags.append("DB")
    if (
        "kubernetes" in job_title
        or "devops" in job_title
        or "cloud " in job_title
        or "engineer, infra" in job_title
    ):
        tags.append("DevOps")

    return tags


def main():
    with psycopg.connect(**DB_CONFIG) as conn:
        all_tags = [
            "AI",
            "SRE",
            "BE",
            "FE",
            "보안",
            "SE",
            "NE",
            "DE",
            "앱",
            "QA",
            "DA",
            "DB",
            "DevOps",
        ]

        with conn.cursor() as cur:
            # 태그 테이블에 모든 태그 삽입
            for tag in all_tags:
                cur.execute(
                    "INSERT INTO tags (name) VALUES (%s) ON CONFLICT (name) DO NOTHING",
                    (tag,),
                )
            conn.commit()

            cur.execute("SELECT id, job_title FROM job_info")
            jobs = cur.fetchall()

            cur.execute("SELECT id, name FROM tags")
            tag_dict = {name: id for id, name in cur.fetchall()}

            for job_id, job_title in jobs:
                job_title_lower = (job_title or "").lower()
                tags = get_tag(job_title_lower)

                logging.info(f"Tagging job_title={job_title} with tags={tags}")

                for tag in tags:
                    tag_id = tag_dict.get(tag)
                    if tag_id:
                        cur.execute(
                            "INSERT INTO job_tags (job_id, tag_id) VALUES (%s, %s) ON CONFLICT DO NOTHING",
                            (job_id, tag_id),
                        )

            conn.commit()


if __name__ == "__main__":
    main()
