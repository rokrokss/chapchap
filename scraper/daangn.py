import os
import logging
import requests
import json
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from typing import List, Dict, Optional, Union
from pydantic import BaseModel
from google import genai
from google.genai import types
from datetime import datetime, date
import psycopg

# --- 기본 설정 ---
load_dotenv()
logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")

# --- 상수 ---
JOB_BASE_URL = "https://about.daangn.com"
DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Referer": "https://about.daangn.com/",
    "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
}

# --- 데이터베이스 설정 ---
DB_CONFIG = {
    "dbname": os.getenv("DB_NAME", "postgres"),
    "user": os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASSWORD", "postgres"),
    "host": os.getenv("DB_HOST", "localhost"),
    "port": os.getenv("DB_PORT", "54322"),
    "options": f"-c search_path={os.getenv('DB_SCHEMA', 'chapchap')}",
}


# --- 데이터 모델 ---
class JobInfo(BaseModel):
    job_title: str
    company_name: str
    affiliate_company_name: str
    link: str
    team_info: str
    responsibilities: List[str]
    qualifications: List[str]
    preferred_qualifications: List[str]
    hiring_process: List[str]
    additional_info: List[str]
    uploaded_date: date


class JobInfoResponse(BaseModel):
    team_info: str
    responsibilities: List[str]
    qualifications: List[str]
    preferred_qualifications: List[str]
    hiring_process: List[str]
    additional_info: List[str]


# --- 유틸 함수 ---
def get_env_vars(*var_names: str) -> Union[str, tuple]:
    """환경 변수들을 가져옵니다."""
    values = []
    for var_name in var_names:
        value = os.getenv(var_name)
        if not value:
            raise ValueError(f"{var_name} 환경 변수가 설정되지 않았습니다.")
        values.append(value)
    return tuple(values) if len(values) > 1 else values[0]


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

        job_title = a_tag.find("h3", class_="c-boyXyq").get_text(strip=True)
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


# --- Gemini 추출 함수 ---
def extract_structured_data_with_gemini(
    company_name: str, job_content_text: str, api_key: str, model_type: str
) -> Optional[JobInfoResponse]:
    """Gemini API를 사용하여 구조화된 데이터를 추출합니다."""
    try:
        client = genai.Client(api_key=api_key)

        prompt = f"""
당신은 친절한 헤드헌터입니다.
다음은 '{company_name}' 회사의 개발자 채용 공고 상세 내용 원본 텍스트입니다:

```text
{job_content_text}
```

작업 목표:
주어진 원본 텍스트에서 구조화된 정보를 추출하고, 아래 설명된 '토스(Toss) 글쓰기 5가지 원칙' 에 따라 각 항목의 내용을 재작성하여 지정된 JSON 형식으로 반환합니다. 최종 결과물은 지원자가 쉽고 명확하게 이해하며, 친근하고 존중받는 느낌을 받도록 작성되어야 합니다.

재작성 시 적용할 '토스 글쓰기 5가지 원칙':

명확하게: 쉽고 명확한 단어/문장 사용. 사용자 입장에서 이해하기 쉽게 작성. 모호함 제거.
간결하게: 핵심만 간결하게 전달. 불필요한 내용 제거. 빠르게 훑어볼 수 있도록 구성. (예: 주요 목록은 불렛포인트 활용)
친근하게: 부드럽고 친근한 어조 사용 (~해요). 어려운 전문 용어 대신 쉬운 표현 사용.
존중하며: 솔직하고 투명하게 정보 전달. 과장 없이. 지원자를 존중하는 태도 유지.
공감하며: 긍정적/공감적 언어 사용. 팀/성장의 매력 전달 (단, 명확/정직함 우선).

작업 단계:

1. 원본 텍스트에서 다음 항목들에 해당하는 핵심 정보를 정확하게 추출합니다:

"팀 소개" (key: team_info)
"담당업무" (key: responsibilities)
"지원자격" (key: qualifications)
"우대사항" (key: preferred_qualifications)
"채용프로세스" (key: hiring_process)
"추가사항" (key: additional_info)

2. 추출된 각 항목의 내용을 위에 요약된 '토스 글쓰기 5가지 원칙'을 종합적으로 고려하여 새롭게 재작성합니다.

- 원본 텍스트의 문장을 그대로 가져오지 않고, 원칙에 맞춰 의미는 유지하되 표현 방식을 완전히 바꾼다는 생각으로 다시 작성해주세요.
- 당신은 회사가 아닙니다. '저희', '우리 회사' 같은 회사를 자칭하는 말은 사용하지 않고, 회사의 이름을 명시해주세요.
- 채용공고가 사용하는 화살표, >, 괄호 등의 표시는 사용하지 않습니다.
- 공고 전체가 영어로 쓰여졌을 경우, 한글로 재작성합니다.
- 매우 중요: 담당업무, 지원자격, 우대사항, 채용프로세스, 추가사항은 리스트로 응답합니다.

3. 2단계에서 재작성된 내용만을 사용하여, JSON 형식으로 최종 결과를 반환합니다.

출력 형식 및 예외 처리:
- 만약 특정 항목에 대한 내용을 원본 텍스트에서 찾을 수 없다면, 해당 JSON key의 값으로 "해당 내용 없음"을 사용해주세요.
- JSON 객체 외에 다른 부가적인 설명, 인사말, 코드 블록 마커(```json ... ```) 등은 절대 포함하지 마세요. 오직 순수한 JSON 객체만 출력해야 합니다.
"""

        response = client.models.generate_content(
            model=model_type,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.2,
                response_schema=JobInfoResponse,
            ),
        )
        return response.parsed

    except Exception as e:
        logging.error(f"Gemini 호출 실패: {e}")
        return None


# --- 메인 실행 ---
def main():
    api_key, model_type, test_mode = get_env_vars(
        "GEMINI_APIKEY", "GEMINI_SYNTHETIC_DATA_GENERATION_MODEL", "TEST_MODE"
    )
    test_mode = test_mode == "1"
    session = requests.Session()
    company_name = "당근"

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

        if job_info:
            if test_mode:
                print(job_info.model_dump_json(indent=2))

            with psycopg.connect(**DB_CONFIG) as conn:
                with conn.cursor() as cur:
                    # 회사 ID 가져오기 또는 삽입
                    cur.execute(
                        "SELECT id FROM companies WHERE name = %s",
                        (job_info.company_name,),
                    )
                    company = cur.fetchone()
                    if company:
                        company_id = company[0]
                    else:
                        cur.execute(
                            "INSERT INTO companies (name) VALUES (%s) RETURNING id",
                            (job_info.company_name,),
                        )
                        company_id = cur.fetchone()[0]

                    # 자회사 ID 가져오기 또는 삽입
                    cur.execute(
                        "SELECT id FROM affiliate_companies WHERE name = %s",
                        (job_info.affiliate_company_name,),
                    )
                    affiliate_company = cur.fetchone()
                    if affiliate_company:
                        affiliate_company_id = affiliate_company[0]
                    else:
                        cur.execute(
                            "INSERT INTO affiliate_companies (name, parent_company_id) VALUES (%s, %s) RETURNING id",
                            (job_info.affiliate_company_name, company_id),
                        )
                        affiliate_company_id = cur.fetchone()[0]

                    # 기존 공고가 있는지 확인
                    cur.execute(
                        "SELECT id FROM job_info WHERE link = %s", (job_info.link,)
                    )
                    existing_job = cur.fetchone()

                    if existing_job:
                        # 기존 공고가 있으면 업데이트
                        cur.execute(
                            """
                            UPDATE job_info SET
                                company_id             = %s,
                                affiliate_company_id   = %s,
                                job_title              = %s,
                                team_info              = %s,
                                responsibilities       = %s,
                                qualifications         = %s,
                                preferred_qualifications = %s,
                                hiring_process         = %s,
                                additional_info        = %s,
                                updated_at             = NOW()
                            WHERE link = %s
                            """,
                            (
                                company_id,
                                affiliate_company_id,
                                job_info.job_title,
                                job_info.team_info,
                                job_info.responsibilities,
                                job_info.qualifications,
                                job_info.preferred_qualifications,
                                job_info.hiring_process,
                                job_info.additional_info,
                                job_info.link,
                            ),
                        )
                    else:
                        cur.execute(
                            """
                            INSERT INTO job_info (
                                company_id,
                                affiliate_company_id,
                                link,
                                job_title,
                                team_info,
                                responsibilities,
                                qualifications,
                                preferred_qualifications,
                                hiring_process,
                                additional_info,
                                uploaded_date
                            ) VALUES (
                                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                            )
                            """,
                            (
                                company_id,
                                affiliate_company_id,
                                job_info.link,
                                job_info.job_title,
                                job_info.team_info,
                                job_info.responsibilities,
                                job_info.qualifications,
                                job_info.preferred_qualifications,
                                job_info.hiring_process,
                                job_info.additional_info,
                                job_info.uploaded_date,
                            ),
                        )
                    conn.commit()
        else:
            logging.error("구조화 실패")

        if test_mode:
            break


if __name__ == "__main__":
    main()
