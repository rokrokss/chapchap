import os
import logging
from dotenv import load_dotenv
from typing import List
import psycopg
from util import DB_CONFIG

load_dotenv(dotenv_path=".env.production")
logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")


def get_tag(job_title: str, company_name: str) -> List[str]:
    tags = []
    job_title = job_title.lower()

    if company_name == "데브시스터즈" and "클라이언트" in job_title:
        tags.append("게임")
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
        or "llm" in job_title
    ):
        tags.append("AI")
    if "sre" in job_title or "reliability" in job_title:
        tags.append("SRE")
    if (
        "back-end" in job_title
        or "백엔드" in job_title
        or "backend" in job_title
        or "be " in job_title
        or "be개발" in job_title
        or "플랫폼 개발" in job_title
        or "서버 개발" in job_title
        or "server engineer" in job_title
        or "서버 소프트웨어" in job_title
        or "plus 채용연계형 인턴십" in job_title
        or "head of engineering" in job_title
        or "platform engineer" in job_title
        or "서버 엔지니어" in job_title
    ):
        tags.append("BE")
    if (
        "front-end" in job_title
        or "프론트엔드" in job_title
        or "frontend" in job_title
        or "도구개발팀 시니어 엔지니어" in job_title
        or "웹 개발" in job_title
        or "호텔 서비스 개발" in job_title
        or "web engineer" in job_title
    ):
        tags.append("FE")
    if (
        "security" in job_title
        or "보안 " in job_title
        or "red team" in job_title
        or "soar" in job_title
    ):
        tags.append("보안")
    if (
        "systems engineer" in job_title
        or "system engineer" in job_title
        or "시스템 엔지니어" in job_title
        or "data center" in job_title
        or "system developer" in job_title
        or "systems developer" in job_title
        or "firmware" in job_title
        or "robotics" in job_title
        or "industrial engineer" in job_title
    ):
        tags.append("SE")
    if "network engineer" in job_title:
        tags.append("NE")
    if (
        "data engineer" in job_title
        or "engineer, data" in job_title
        or "bi engineer" in job_title
        or "데이터엔지니어" in job_title
        or "data warehouse" in job_title
        or "data platform" in job_title
        or "software engineer (data)" in job_title
        or "analytics engineer" in job_title
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
        or "인프라운영" in job_title
    ):
        tags.append("DevOps")
    if (
        "program manage" in job_title
        or "project manage" in job_title
        or "product manage" in job_title
        or "partner manage" in job_title
        or "asset manage" in job_title
        or "director product" in job_title
        or "지원 담당" in job_title
        or "관리 전문" in job_title
        or "director, procurement" in job_title
        or "relations manager" in job_title
        or "relation manager" in job_title
        or "it기획" in job_title
        or "acquisition" in job_title
    ):
        tags.append("PM")
    if (
        "xr" in job_title
        or "vr" in job_title
        or "augmented reality" in job_title
        or "virtual reality" in job_title
        or "모션" in job_title
        or "motion" in job_title
    ):
        tags.append("XR")
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
            "게임",
            "PM",
            "XR",
        ]

        with conn.cursor() as cur:
            cur.execute(f"SET search_path TO {os.getenv('DB_SCHEMA', 'chapchap')}")
            # 태그 테이블에 모든 태그 삽입
            for tag in all_tags:
                cur.execute(
                    "INSERT INTO tags (name) VALUES (%s) ON CONFLICT (name) DO NOTHING",
                    (tag,),
                )
            conn.commit()

            cur.execute(
                """
                SELECT j.id, j.job_title, c.name as company_name 
                FROM job_info j
                LEFT JOIN companies c ON j.company_id = c.id
                """
            )
            jobs = cur.fetchall()

            cur.execute("SELECT id, name FROM tags")
            tag_dict = {name: id for id, name in cur.fetchall()}

            for job_id, job_title, company_name in jobs:
                job_title_lower = (job_title or "").lower()
                tags = get_tag(job_title_lower, company_name)

                logging.info(f"Tagging job_title={job_title} with tags={tags}")

                for tag in tags:
                    tag_id = tag_dict.get(tag)
                    if tag_id:
                        cur.execute(
                            "INSERT INTO job_tags (job_id, tag_id) VALUES (%s, %s) ON CONFLICT DO NOTHING",
                            (job_id, tag_id),
                        )

            conn.commit()

            cur.execute(
                """
                UPDATE job_info SET is_active = false WHERE updated_at < NOW() - INTERVAL '1 days'
                """
            )
            conn.commit()


if __name__ == "__main__":
    main()
