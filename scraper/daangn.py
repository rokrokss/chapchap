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
import re
import json

# --- 기본 설정 ---
load_dotenv(dotenv_path=".env.production")
logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")

# --- 상수 ---
JOB_BASE_URL = "https://about.daangn.com"


# --- 스크래핑 관련 함수 ---
def scrape_jobs(session: requests.Session) -> List[Dict[str, str]]:
    """채용 공고 리스트를 스크래핑합니다."""
    params = {"q": "Engineer"}
    target_url = f"{JOB_BASE_URL}/jobs/"
    res = session.get(target_url, params=params, headers=DEFAULT_HEADERS)
    res.encoding = "utf-8"  # 응답 인코딩을 UTF-8로 설정
    soup = BeautifulSoup(res.text, "html.parser")
    jobs = []

    for li in soup.select("ul.c-jpGEAj li.c-deAcZv"):
        a_tag = li.find("a", href=True)
        if not a_tag:
            continue

        job_title = re.sub(
            r"[\x00-\x1F\x7F]",
            "",
            a_tag.find("h3", class_="c-boyXyq").get_text(strip=True),
        )
        job_link = a_tag["href"]
        if (
            "engineer" not in job_title.lower()
            and "developer" not in job_title.lower()
            and "scientist" not in job_title.lower()
        ):
            continue
        jobs.append(
            {
                "title": job_title,
                "link": f"https://about.daangn.com{job_link}",
            }
        )

    return jobs


def scrape_job_detail(session: requests.Session, url: str) -> str:
    """상세 채용 공고 내용을 스크래핑합니다."""
    res = session.get(url, headers=DEFAULT_HEADERS)
    soup = BeautifulSoup(res.content, "html.parser")

    content_elem = soup.select_one("article.c-kJtTwH")

    detail = content_elem.get_text(separator="\n", strip=True) if content_elem else None

    json_ld_tags = soup.find_all("script", type="application/ld+json")
    uploaded_date = None
    for tag in json_ld_tags:
        data = json.loads(tag.string)
        date_posted = data.get("datePosted", None)
        if date_posted:
            uploaded_date = date_posted

    return detail, uploaded_date


# --- 메인 실행 ---
def main():
    api_key, model_type, test_mode = get_env_vars(
        "GOOGLE_API_KEY", "GEMINI_SYNTHETIC_DATA_GENERATION_MODEL", "TEST_MODE"
    )
    test_mode = test_mode == "1"
    session = requests.Session()
    company_name = "당근"
    alternate_names = ["daangn"]

    jobs = scrape_jobs(session)
    logging.info(f"총 {len(jobs)}건 추출했습니다.")

    for idx, job in enumerate(jobs, 1):
        logging.info(f"공고 처리 중... ({idx}/{len(jobs)})")
        logging.info(f"공고: {job['title']} - {job['link']}")
        detail_text, uploaded_date = scrape_job_detail(session, job["link"])

        logging.info("Gemini를 통해 구조화된 데이터 추출 중...")
        job_info_response = extract_structured_data_with_gemini(
            company_name, detail_text, api_key, model_type
        )
        job_info = JobInfo(
            company_name=company_name,
            affiliate_company_name=company_name,
            link=job["link"],
            job_title=job["title"],
            uploaded_date=datetime.strptime(uploaded_date, "%Y-%m-%d").date(),
            **job_info_response.model_dump(),
        )

        save_job_info(job_info, alternate_names, test_mode)

        if test_mode:
            break


if __name__ == "__main__":
    main()
