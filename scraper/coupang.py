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
JOB_BASE_URL = "https://www.coupang.jobs/kr/jobs"


# --- 스크래핑 관련 함수 ---
def scrape_jobs(session: requests.Session) -> List[Dict[str, str]]:
    jobs = []
    for search in ["engineer", "developer", "scientist", "research"]:
        page = 1
        while True:
            params = {
                "page": page,
                "location": "Seoul, South Korea",
                "pagesize": 100,
                "search": search,
            }
            target_url = f"{JOB_BASE_URL}/"
            print(f"Requesting URL: {target_url} with params: {params}")
            res = session.get(target_url, params=params, headers=DEFAULT_HEADERS)
            res.encoding = "utf-8"
            soup = BeautifulSoup(res.text, "html.parser")
            job_container = soup.find("div", id="js-job-search-results")
            job_cards = job_container.select("div.card.card-job")

            if not job_cards:
                break

            for card in job_cards:
                a_tag = card.select_one("h2.card-title > a")
                if a_tag:
                    title = a_tag.get_text(strip=True)
                    affiliate_company_name = (
                        title[1 : title.find("]")].strip() if "]" in title else "쿠팡"
                    )
                    if " — Coupang Play" in title:
                        title = title.split(" — Coupang Play")[0].strip()
                        affiliate_company_name = "쿠팡플레이"
                    if " - Coupang Play" in title:
                        title = title.split(" - Coupang Play")[0].strip()
                        affiliate_company_name = "쿠팡플레이"
                    if " (Coupang Play)" in title:
                        title = title.split(" (Coupang Play)")[0].strip()
                        affiliate_company_name = "쿠팡플레이"
                    if " — Coupang Pay" in title:
                        title = title.split(" — Coupang Pay")[0].strip()
                        affiliate_company_name = "쿠팡페이"
                    if " - Coupang Pay" in title:
                        title = title.split(" - Coupang Pay")[0].strip()
                        affiliate_company_name = "쿠팡페이"
                    if "Eats" in title:
                        affiliate_company_name = "쿠팡이츠"
                    title = title.split("]")[1].strip() if "]" in title else title
                    link = "https://www.coupang.jobs" + a_tag["href"]
                    if affiliate_company_name.lower() == "coupang":
                        affiliate_company_name = "쿠팡"
                    elif affiliate_company_name.lower() == "coupang pay":
                        affiliate_company_name = "쿠팡페이"
                    elif affiliate_company_name.lower() == "search & discovery":
                        affiliate_company_name = "쿠팡"
                    elif (
                        affiliate_company_name.lower() == "coupang fulfillment services"
                    ):
                        affiliate_company_name = "쿠팡풀필먼트서비스"
                    elif affiliate_company_name.lower() == "coupang play":
                        affiliate_company_name = "쿠팡플레이"

                    if (
                        (
                            "Engineer" in title
                            or "Developer" in title
                            or "Scientist" in title
                            or "Research" in title
                            or "Director" in title
                            or "Architect" in title
                        )
                        and not "UX Research" in title
                        and not "Product Management" in title
                        and not "Product Design" in title
                        and not "Marketing" in title
                        and affiliate_company_name != "쿠팡풀필먼트서비스"
                    ):
                        jobs.append(
                            {
                                "title": title,
                                "affiliate_company_name": affiliate_company_name,
                                "link": link,
                            }
                        )

            page += 1

    unique_jobs = {job["link"]: job for job in jobs}
    return list(unique_jobs.values())


def scrape_job_detail(session: requests.Session, url: str) -> str:
    """상세 채용 공고 내용을 스크래핑합니다."""
    res = session.get(url, headers=DEFAULT_HEADERS)
    soup = BeautifulSoup(res.content, "html.parser")

    content_elem = soup.select_one("article.cms-content")

    detail = content_elem.get_text(separator="\n", strip=True) if content_elem else None

    time_elem = soup.select_one("div.job-table time")
    updated_date = (
        time_elem["datetime"] if time_elem and time_elem.has_attr("datetime") else None
    )

    return {"detail": detail, "updated_date": updated_date}


# --- 메인 실행 ---
def main():
    api_key, model_type, test_mode = get_env_vars(
        "GOOGLE_API_KEY", "GEMINI_SYNTHETIC_DATA_GENERATION_MODEL", "TEST_MODE"
    )
    test_mode = test_mode == "1"
    session = requests.Session()
    company_name = "쿠팡"
    alternate_names = ["coupang"]

    jobs = scrape_jobs(session)
    logging.info(f"총 {len(jobs)}건 추출했습니다.")

    for idx, job in enumerate(jobs, 1):
        logging.info(f"공고 처리 중... ({idx}/{len(jobs)})")
        logging.info(f"공고: {job['title']} - {job['link']}")
        job_detail = scrape_job_detail(session, job["link"])

        logging.info("Gemini를 통해 구조화된 데이터 추출 중...")
        job_info_response = extract_structured_data_with_gemini(
            company_name, job_detail["detail"], api_key, model_type
        )
        job_info = JobInfo(
            company_name=company_name,
            affiliate_company_name=job["affiliate_company_name"],
            link=job["link"],
            job_title=job["title"],
            uploaded_date=(
                datetime.strptime(job_detail["updated_date"], "%Y-%m-%d").date()
                if job_detail["updated_date"]
                else datetime.now().date()
            ),
            **job_info_response.model_dump(),
        )

        save_job_info(job_info, alternate_names, test_mode)

        if test_mode:
            break


if __name__ == "__main__":
    main()
