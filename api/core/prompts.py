from core.config import settings


def resume_summary_prompt() -> str:
    return """
아래 이력서를 읽고 지원자의 경력의 순서를 명시하고, 지원자가 가진 능력을 한 줄 씩 적어주세요.
경력 기준 가장 강한 능력으로 보이는 것을 먼저 적어주세요.

출력 형식:
- "->"로 구분된 학력/경력
- 능력 1
- 능력 2
- 능력 3
...

출력 예시:
- 카이스트 학부 -> 크래프톤 (프론트엔드 엔지니어) -> 토스 (DevOps 엔지니어)
- Java 및 Spring Framework 활용 개발 경험 및 AWS 환경 경험
- React, Vue 등 최신 프론트엔드 프레임워크 및 유형 컴포넌트 UI 설계 경험
- 광고 및 이커머스 도메인 경험
- MLOps와 LLMOps 파이프라인 구현 및 관리
- Kubernetes 등 컨테이너 오케스트레이션 시스템 활용 운영 경험
- 대화형 AI, 음성인식, NLP 등 AI/ML 관련 솔루션 실무 경험
"""


def rerank_job_prompt(resume_text: str, jobs: list[dict]) -> str:
    job_list = "\n\n".join(
        [
            f"공고번호 {i}. {job['job_title']} ({job['company_name']})\n"
            f"  - 팀 소개: {job['team_info']}\n"
            f"  - 담당업무:\n    " + "\n    ".join(job["responsibilities"]) + "\n"
            f"  - 지원자격:\n    " + "\n    ".join(job["qualifications"]) + "\n"
            f"  - 우대사항:\n    " + "\n    ".join(job["preferred_qualifications"])
            for i, job in enumerate(jobs)
        ]
    )
    return f"""
다음은 당신이 가진 채용공고의 리스트입니다.
당신은 이 채용공고 중 지원자가 적합한 {settings.RERANK_COUNT}개의 공고를 선별하고 적합한 순으로 정렬하고 설명을 첨부해야 합니다.
적합한 이유는 100자 이내로 명시해야 합니다.
지원자의 이름은 언급하지 않고 지원자라고 표현해야 합니다.

이력서는 다음과 같습니다.
===이력서 (정제되지 않은 텍스트)
{resume_text}


===채용공고 리스트
{job_list}


===출력 형식
"공고번호" (key: job_idx)
"공고이름" (key: job_title)
"적합한 이유" (key: reason)

{{ "results": [{{ "job_idx": "...", "job_title": "...", "reason": "..." }}, ...] }}
"""


def cover_letter_prompt(resume_text: str, job_dict: dict) -> str:
    job_responsibilities = "\n    ".join(job_dict["responsibilities"])
    job_qualifications = "\n    ".join(job_dict["qualifications"])
    job_preferred_qualifications = "\n    ".join(job_dict["preferred_qualifications"])

    return f"""
당신은 IT회사의 지원자입니다.
당신은 아래 주어진 이력서를 바탕으로 주어진 채용공고에 지원하려 합니다.
회사의 문화를 고려하여 알맞은 커버레터를 작성해 주세요.

당신의 이력서는 다음과 같습니다.
===이력서 (정제되지 않은 텍스트)
{resume_text}


===채용공고
- 공고 이름: {job_dict["job_title"]}
- 회사 이름: {job_dict["company_name"]}
- 팀 소개: {job_dict["team_info"]}
- 담당업무:
    {job_responsibilities}
- 지원자격:
    {job_qualifications}
- 우대사항:
    {job_preferred_qualifications}


===주의사항
- 문어체로 작성할 것
- 지원자의 이름은 언급하지 않을 것
- 아래 4개의 문단 외에 글을 작성하지 말 것, 인삿말도 작성하지 말 것
- 문단 1. 본인 소개, 지원동기, 지원직무 언급
- 문단 2. 업무경력, 성과, 본인의 핵심역량 어필
- 문단 3. 입사 포부
- 문단 4. 인터뷰 기회 요청으로 마무리
"""
