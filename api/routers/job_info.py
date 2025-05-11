from fastapi import APIRouter, Request
from typing import List
from psycopg.rows import dict_row
from collections import defaultdict

router = APIRouter()


@router.get("/all_active", response_model=List[dict])
async def get_all_active_job_info(
    request: Request,
):
    job_query = """
        SELECT
        j.*,
        c.name AS company_name,
        ac.name AS affiliate_company_name,
        ARRAY_REMOVE(ARRAY_AGG(t.name), NULL) AS tags
        FROM chapchap.job_info j
        JOIN chapchap.companies c ON j.company_id = c.id
        JOIN chapchap.affiliate_companies ac ON j.affiliate_company_id = ac.id
        LEFT JOIN chapchap.job_tags jt ON j.id = jt.job_id
        LEFT JOIN chapchap.tags t ON jt.tag_id = t.id
        WHERE j.is_active = true
        GROUP BY j.id, c.name, ac.name
        ORDER BY j.uploaded_date DESC;
    """

    qualifications_query = """
        SELECT job_id, type, sentence_index, sentence
        FROM chapchap.job_qualification_sentences
        WHERE type != 'title'
        ORDER BY job_id, type, sentence_index
    """

    async with request.app.state.db_pool.connection() as conn:
        async with conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(job_query)
            job_rows = await cur.fetchall()

            await cur.execute(qualifications_query)
            sentence_rows = await cur.fetchall()

    qualifications_map = defaultdict(lambda: {"required": [], "preferred": []})
    for row in sentence_rows:
        qualifications_map[row["job_id"]][row["type"]].append(row["sentence"])

    results = []
    for job in job_rows:
        job_dict = dict(job)
        job_id = job_dict["id"]
        job_dict["qualifications"] = qualifications_map[job_id]["required"]
        job_dict["preferred_qualifications"] = qualifications_map[job_id]["preferred"]
        results.append(job_dict)

    return results


@router.get("/tag/job_count", response_model=List[dict])
async def get_job_count_by_tag(
    request: Request,
):
    query = """
        SELECT
            t.name AS tag_name,
            COUNT(jt.job_id) AS job_count
        FROM
            chapchap.tags t
        LEFT JOIN
            chapchap.job_tags jt ON t.id = jt.tag_id
        LEFT JOIN
            chapchap.job_info j ON jt.job_id = j.id
        WHERE
            j.is_active = true
        GROUP BY
            t.name
        ORDER BY
            job_count DESC;
    """
    async with request.app.state.db_pool.connection() as conn:
        async with conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(query)
            rows = await cur.fetchall()
    return [dict(row) for row in rows]


@router.get("/company/job_count", response_model=List[dict])
async def get_job_count_by_company(
    request: Request,
):
    query = """
        SELECT
            c.name AS company_name,
            COUNT(j.id) AS job_count
        FROM
            chapchap.job_info j
        JOIN
            chapchap.companies c ON j.company_id = c.id
        WHERE
            j.is_active = true
        GROUP BY
            c.name
        ORDER BY
            job_count DESC;
    """
    async with request.app.state.db_pool.connection() as conn:
        async with conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(query)
            rows = await cur.fetchall()
    return [dict(row) for row in rows]


@router.get("/affiliate_company/job_count", response_model=List[dict])
async def get_job_count_by_affiliate_company(
    request: Request,
):
    query = """
        SELECT
            ac.name AS affiliate_company_name,
            pc.name AS parent_company_name,
            COUNT(j.id) AS job_count
        FROM
            chapchap.job_info j
        JOIN
            chapchap.affiliate_companies ac ON j.affiliate_company_id = ac.id
        JOIN
            chapchap.companies c ON j.company_id = c.id
        JOIN
            chapchap.companies pc ON ac.parent_company_id = pc.id
        WHERE
            j.is_active = true AND
            ac.name != c.name
        GROUP BY
            ac.name,
            pc.name
        ORDER BY
            job_count DESC;
    """
    async with request.app.state.db_pool.connection() as conn:
        async with conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(query)
            rows = await cur.fetchall()
    return [dict(row) for row in rows]


@router.get(
    "/company/job_count_including_affiliate_companies", response_model=List[dict]
)
async def get_job_count_including_affiliate_companies(
    request: Request,
):
    job_count_by_company = await get_job_count_by_company(request)
    job_count_by_affiliate_company = await get_job_count_by_affiliate_company(request)

    # 회사 이름을 키로 하는 딕셔너리 생성
    company_dict = {
        company["company_name"]: company for company in job_count_by_company
    }

    # 자회사 정보를 회사로 추가
    for affiliate_company in job_count_by_affiliate_company:
        parent_name = affiliate_company["parent_company_name"]
        affiliate_name = affiliate_company["affiliate_company_name"]

        # 자회사를 부모 회사의 affiliates 리스트에 추가
        company_dict[parent_name].setdefault("affiliates", []).append(
            {
                "company_name": affiliate_name,
                "job_count": affiliate_company["job_count"],
            }
        )

    # 결과 리스트 생성
    job_count_by_all_companies = []
    for company in company_dict.values():
        job_count_by_all_companies.append(
            {"company_name": company["company_name"], "job_count": company["job_count"]}
        )
        # affiliates를 job_count 기준으로 정렬
        sorted_affiliates = sorted(
            company.get("affiliates", []), key=lambda x: x["job_count"], reverse=True
        )
        job_count_by_all_companies.extend(sorted_affiliates)

    return job_count_by_all_companies
