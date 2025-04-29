import requests
from bs4 import BeautifulSoup
import time
import random

def scrape_line_jobs():
    url = "https://careers.linecorp.com/ko/jobs?ca=Engineering&ci=Gwacheon,Bundang&co=East%20Asia"
    headers = {
        "User-Agent": "Mozilla/5.0",
    "Referer": "https://careers.linecorp.com/",
    "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7"
    }

    # 페이지 요청
    res = requests.get(url, headers=headers)
    soup = BeautifulSoup(res.text, "html.parser")

    job_list = []

    # 공고 리스트 찾아서 파싱
    for li in soup.select('ul.job_list li'):
        a_tag = li.find('a', href=True)
        h3_tag = li.find('h3', class_='title')
        text_filter = li.find('div', class_='text_filter')

        if a_tag and h3_tag:
            description_text = text_filter.get_text()

            if "Taipei" in description_text:
                continue
            if "Engineering" not in description_text:
                continue

            job_link = a_tag['href']
            job_title = h3_tag.get_text(strip=True)
            job_list.append({
                "title": job_title,
                "link": f"https://careers.linecorp.com{job_link}"
            })

    return job_list

def scrape_job_detail(url):
    headers = {
        "User-Agent": "Mozilla/5.0"
    }
    res = requests.get(url, headers=headers)
    soup = BeautifulSoup(res.content, "html.parser")

    # 상세 공고 내용 추출
    job_content_section = soup.find('section', id='jobs-contents')
    if job_content_section:
        content_text = job_content_section.get_text(separator="\n", strip=True)
        return content_text
    return "상세 내용 없음"

if __name__ == "__main__":
    jobs = scrape_line_jobs()
    print(f"총 {len(jobs)}건 추출했습니다.")
    for job in jobs:
        print(f"- {job['title']} : {job['link']}")
        detail = scrape_job_detail(job['link'])
        print(detail)
        break
