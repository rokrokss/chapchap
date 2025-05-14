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


# --- 스크래핑 관련 함수 ---
def scrape_jobs(session: requests.Session) -> List[Dict[str, str]]:
    jobs = []
    page = 1
    while True:
        params = {
            "part": "TECHNOLOGY",
            "company": "KAKAO",
            "page": page,
        }
        res = session.get(
            "https://careers.kakao.com/public/api/job-list",
            params=params,
            headers=DEFAULT_HEADERS,
        )
        res.raise_for_status()
        data = res.json()
        job_list = data.get("jobList", [])
        if not job_list:
            break

        for job in job_list:
            jobs.append(
                {
                    "title": job["jobOfferTitle"],
                    "affiliate_company_name": "카카오",
                    "link": f"https://careers.kakao.com/jobs/{job['realId']}",
                    "detail": (
                        f"조직소개\n"
                        f"{job['introduction']}\n\n"
                        f"업무내용\n"
                        f"{job['workContentDesc']}\n\n"
                        f"지원자격\n"
                        f"{job['qualification']}\n\n"
                        f"채용절차\n"
                        f"{job['jobOfferProcessDesc']}"
                    ),
                    "uploaded_date": job["uptDate"].split("T")[0],
                }
            )

        page += 1
    return jobs


# --- 메인 실행 ---
def main():
    api_key, model_type, test_mode = get_env_vars(
        "GOOGLE_API_KEY", "GEMINI_SYNTHETIC_DATA_GENERATION_MODEL", "TEST_MODE"
    )
    test_mode = test_mode == "1"
    session = requests.Session()
    company_name = "카카오"
    alternate_names = ["kakao"]

    jobs = scrape_jobs(session)
    logging.info(f"총 {len(jobs)}건 추출했습니다.")

    for idx, job in enumerate(jobs, 1):
        logging.info(f"공고 처리 중... ({idx}/{len(jobs)})")
        logging.info(f"공고: {job['title']} - {job['link']}")

        logging.info("Gemini를 통해 구조화된 데이터 추출 중...")
        job_info_response = extract_structured_data_with_gemini(
            company_name, job["detail"], api_key, model_type
        )
        job_info = JobInfo(
            company_name=company_name,
            affiliate_company_name=job["affiliate_company_name"],
            link=job["link"],
            job_title=job["title"],
            uploaded_date=datetime.strptime(job["uploaded_date"], "%Y-%m-%d").date(),
            **job_info_response.model_dump(),
        )

        save_job_info(job_info, alternate_names, test_mode)

        if test_mode:
            break


if __name__ == "__main__":
    main()
