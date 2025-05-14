import logging
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from typing import List, Dict
from datetime import datetime
from util import (
    get_env_vars,
    save_job_info,
    JobInfo,
    DEFAULT_HEADERS,
    extract_structured_data_with_gemini,
)

# --- 기본 설정 ---
load_dotenv(dotenv_path=".env.production")
logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")

# --- 상수 ---
JOB_BASE_URL = "https://careers.flipster.io"


# --- 스크래핑 관련 함수 ---
def scrape_jobs(session: requests.Session) -> List[Dict[str, str]]:
    jobs = []
    res = session.get(f"{JOB_BASE_URL}/api/postings", headers=DEFAULT_HEADERS)
    data = res.json()

    scraped_jobs = data.get("jobs", [])

    for job in scraped_jobs:
        job_id = job["id"]
        title = job["title"]
        if job["team"]["value"] != "engineering":
            continue
        if job["location"]["value"] != "south-korea":
            continue
        url = f"{JOB_BASE_URL}/jobs/{job_id}"

        jobs.append({"id": job_id, "title": title, "link": url})

    return jobs


def scrape_job_detail(session: requests.Session, url: str) -> str:
    """상세 채용 공고 내용을 스크래핑합니다."""
    res = session.get(url, headers=DEFAULT_HEADERS)
    soup = BeautifulSoup(res.content, "html.parser")

    content_elem = soup.select_one("div.styles_lever_content__ql2gg")

    detail = content_elem.get_text(separator="\n", strip=True) if content_elem else None

    return detail


# --- 메인 실행 ---
def main():
    api_key, model_type, test_mode = get_env_vars(
        "GOOGLE_API_KEY", "GEMINI_SYNTHETIC_DATA_GENERATION_MODEL", "TEST_MODE"
    )
    test_mode = test_mode == "1"
    session = requests.Session()
    company_name = "플립스터"
    alternate_names = ["flipster"]

    jobs = scrape_jobs(session)
    logging.info(f"총 {len(jobs)}건 추출했습니다.")

    for idx, job in enumerate(jobs, 1):
        logging.info(f"공고 처리 중... ({idx}/{len(jobs)})")
        logging.info(f"공고: {job['title']} - {job['link']}")
        detail_text = scrape_job_detail(session, job["link"])

        logging.info("Gemini를 통해 구조화된 데이터 추출 중...")
        job_info_response = extract_structured_data_with_gemini(
            company_name, detail_text, api_key, model_type
        )
        job_info = JobInfo(
            company_name=company_name,
            affiliate_company_name=company_name,
            link=job["link"],
            job_title=job["title"],
            uploaded_date=datetime.now().date(),
            **job_info_response.model_dump(),
        )

        save_job_info(job_info, alternate_names, test_mode)

        if test_mode:
            break


if __name__ == "__main__":
    main()
