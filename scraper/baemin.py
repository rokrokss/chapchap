import logging
import requests
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
JOB_API_BASE_URL = "https://career.woowahan.com/w1/recruits"


# --- 스크래핑 관련 함수 ---
def scrape_jobs(session: requests.Session) -> List[Dict[str, str]]:
    page = 0
    params = {
        "category": "jobGroupCodes:BA005001",
        "recruitCampaignSeq": 0,
        "jobGroupCodes": "BA005001",
        "size": 21,
        "sort": "updateDate,desc",
    }
    jobs = []
    while True:
        params["page"] = page
        res = session.get(JOB_API_BASE_URL, params=params, headers=DEFAULT_HEADERS)
        data = res.json()

        scraped_jobs = data.get("data", {}).get("list", [])
        if not scraped_jobs:
            break  # 더 이상 없으면 종료

        for job in scraped_jobs:
            job_id = job["recruitNumber"]
            title = job["recruitName"]
            start_date = (
                job["recruitOpenDate"].split()[0]
                if "recruitOpenDate" in job
                else datetime.now().strftime("%Y.%m.%d")
            )
            url = f"https://career.woowahan.com/w1/recruits/{job_id}"
            title = title.split("]")[1].strip() if "]" in title else title

            jobs.append(
                {
                    "id": job_id,
                    "title": title,
                    "link": url,
                    "uploaded_date": start_date,
                }
            )

        page += 1

    return jobs


def scrape_job_detail(session: requests.Session, url: str) -> str:
    """상세 채용 공고 내용을 스크래핑합니다."""
    res = session.get(url, headers=DEFAULT_HEADERS)
    data = res.json()
    recruitContents = data.get("data", {}).get("recruitContents", {})

    return recruitContents if recruitContents else "상세 내용 없음"


# --- 메인 실행 ---
def main():
    api_key, model_type, test_mode = get_env_vars(
        "GOOGLE_API_KEY", "GEMINI_SYNTHETIC_DATA_GENERATION_MODEL", "TEST_MODE"
    )
    test_mode = test_mode == "1"
    session = requests.Session()
    company_name = "우아한형제들"
    alternate_names = ["배달의민족", "woowa", "배민", "baemin"]

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
            link=f"https://career.woowahan.com/recruitment/{job['id']}/detail",
            job_title=job["title"],
            uploaded_date=datetime.strptime(job["uploaded_date"], "%Y-%m-%d").date(),
            **job_info_response.model_dump(),
        )

        save_job_info(job_info, alternate_names, test_mode)

        if test_mode:
            break


if __name__ == "__main__":
    main()
