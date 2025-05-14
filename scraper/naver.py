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
    extract_structured_data_with_gemini,
    DEFAULT_HEADERS,
)

# --- 기본 설정 ---
load_dotenv(dotenv_path=".env.production")
logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")

# --- 상수 ---
JOB_API_BASE_URL = "https://recruit.navercorp.com/rcrt/loadJobList.do"


# --- 스크래핑 관련 함수 ---
def scrape_jobs(session: requests.Session) -> List[Dict[str, str]]:
    first_index = 0
    page_size = 10
    params = {
        "annoId": "",
        "sw": "",
        "subJobCdArr": "1010001,1010002,1010003,1010004,1010005,1010006,1010007,1010008,1010009,1010020,1020001,1030001,1030002,1040001,1040002,1040003,1050001,1050002,1060001",
        "sysCompanyCdArr": "",
        "empTypeCdArr": "",
        "entTypeCdArr": "",
        "workAreaCdArr": "",
    }
    jobs = []
    while True:
        params["firstIndex"] = first_index
        res = session.get(JOB_API_BASE_URL, params=params)
        data = res.json()

        scraped_jobs = data.get("list", [])
        if not scraped_jobs:
            break  # 더 이상 없으면 종료

        for job in scraped_jobs:
            job_id = job["annoId"] if "annoId" in job else job["id"]
            title = job["annoSubject"] if "annoSubject" in job else job["title"]
            start_date = (
                job["staYmdTime"].split()[0]
                if "staYmdTime" in job
                else datetime.now().strftime("%Y.%m.%d")
            )
            url = f"https://recruit.navercorp.com/rcrt/view.do?annoId={job_id}&lang=ko"
            affiliate_company_name = (
                title[1 : title.find("]")].strip() if "]" in title else "네이버"
            )
            title = title.split("]")[1].strip() if "]" in title else title
            if affiliate_company_name.lower() == "naver":
                affiliate_company_name = "네이버"
            elif affiliate_company_name.lower() == "naver cloud":
                affiliate_company_name = "네이버클라우드"
            elif affiliate_company_name.lower() == "naver labs":
                affiliate_company_name = "네이버랩스"

            jobs.append(
                {
                    "id": job_id,
                    "title": title,
                    "affiliate_company_name": affiliate_company_name,
                    "link": url,
                    "uploaded_date": start_date,
                }
            )

        first_index += page_size

    return jobs


def scrape_job_detail(session: requests.Session, url: str) -> str:
    """상세 채용 공고 내용을 스크래핑합니다."""
    res = session.get(url, headers=DEFAULT_HEADERS)
    soup = BeautifulSoup(res.content, "html.parser")

    detail_wrap = soup.find("div", class_="detail_wrap")
    return (
        detail_wrap.get_text(separator="\n", strip=True)
        if detail_wrap
        else "상세 내용 없음"
    )


# --- 메인 실행 ---
def main():
    api_key, model_type, test_mode = get_env_vars(
        "GOOGLE_API_KEY", "GEMINI_SYNTHETIC_DATA_GENERATION_MODEL", "TEST_MODE"
    )
    test_mode = test_mode == "1"
    session = requests.Session()
    company_name = "네이버"
    alternate_names = ["naver"]

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
            affiliate_company_name=job["affiliate_company_name"],
            link=job["link"],
            job_title=job["title"],
            uploaded_date=datetime.strptime(job["uploaded_date"], "%Y.%m.%d").date(),
            **job_info_response.model_dump(),
        )

        save_job_info(job_info, alternate_names, test_mode)

        if test_mode:
            break


if __name__ == "__main__":
    main()
