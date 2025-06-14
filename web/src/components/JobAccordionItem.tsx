import React from 'react';
import { AccordionItem, AccordionTrigger, AccordionContent } from '@/components/ui/accordion';
import { Button } from '@/components/ui/button';
import { Job } from '@/store/useResumeStore';

type Props = {
  job: Job;
  index: number;
  selectedCompanies: string[];
  selectedTags: string[];
  onClickAccordion: (id: string) => void;
  onClickCompany: (e: React.MouseEvent<HTMLButtonElement>, companyName: string) => void;
  onClickTag: (e: React.MouseEvent<HTMLButtonElement>, tag: string) => void;
  filterByRecentWeek: boolean;
  filterByRecentDay: boolean;
  onClickRecentWeek: (e: React.MouseEvent<HTMLButtonElement>) => void;
  onClickRecentDay: (e: React.MouseEvent<HTMLButtonElement>) => void;
};

const JobAccordionItem = ({
  job,
  index,
  selectedCompanies,
  selectedTags,
  onClickAccordion,
  onClickCompany,
  onClickTag,
  filterByRecentWeek,
  filterByRecentDay,
  onClickRecentWeek,
  onClickRecentDay,
}: Props) => {
  return (
    <AccordionItem key={job.id} value={job.id}>
      <AccordionTrigger className="mb-0 pb-4">
        <div>{`${job.reason ? `${index + 1}. ` : ''}${job.job_title} @ ${job.company_name}`}</div>
      </AccordionTrigger>
      <div onClick={() => onClickAccordion(`${job.id}`)}>
        {job.reason ? <div className="mb-4 text-sm italic">"{job.reason.trim()}"</div> : null}
        <div className="mb-4 flex justify-between items-center flex-wrap">
          <div className="flex flex-wrap items-center">
            <Button
              variant={selectedCompanies.includes(job.company_name) ? 'default' : 'outline'}
              size="xs"
              className="mr-1 duration-0"
              onClick={e => onClickCompany(e, job.company_name)}
            >
              {job.company_name}
            </Button>
            {job.affiliate_company_name !== job.company_name && (
              <Button
                variant={
                  selectedCompanies.includes(job.affiliate_company_name) ? 'default' : 'outline'
                }
                size="xs"
                className="mr-1 duration-0"
                onClick={e => onClickCompany(e, job.affiliate_company_name)}
              >
                {job.affiliate_company_name}
              </Button>
            )}
            {job.tags.map(tag => (
              <Button
                key={tag}
                variant={selectedTags.includes(tag) ? 'default' : 'outline'}
                size="xs"
                className="mr-1 duration-0"
                onClick={e => onClickTag(e, tag)}
              >
                {tag}
              </Button>
            ))}
            {job.uploaded_in_a_day && (
              <Button
                variant={filterByRecentDay ? 'default' : 'outline'}
                size="xs"
                className="mr-1 duration-0"
                onClick={e => onClickRecentDay(e)}
              >
                1일
              </Button>
            )}
            {(!job.uploaded_in_a_day || filterByRecentWeek) && job.uploaded_in_a_week && (
              <Button
                variant={filterByRecentWeek ? 'default' : 'outline'}
                size="xs"
                className="mr-1 duration-0"
                onClick={e => onClickRecentWeek(e)}
              >
                일주일
              </Button>
            )}
          </div>
          <div className="text-sm text-right whitespace-nowrap">{job.uploaded_date}</div>
        </div>
      </div>
      <AccordionContent>
        <div className="mb-2">
          <strong>회사:</strong> {job.affiliate_company_name}
        </div>
        <div className="mb-2">
          <strong>팀 소개</strong>
          <div className="text-sm">{job.team_info}</div>
        </div>
        <div className="mb-2">
          <strong>담당업무</strong>
          <div className="text-sm">
            {job.responsibilities.map((line, index) => (
              <div key={`${job.id}-r-${index}`}>- {line}</div>
            ))}
          </div>
        </div>
        <div className="mb-2">
          <strong>지원자격</strong>
          <div className="text-sm">
            {job.qualifications.map((line, index) => (
              <div key={`${job.id}-q-${index}`}>- {line}</div>
            ))}
          </div>
        </div>
        <div className="mb-2">
          <strong>우대사항</strong>
          <div className="text-sm">
            {job.preferred_qualifications.map((line, index) => (
              <div key={`${job.id}-pq-${index}`}>- {line}</div>
            ))}
          </div>
        </div>
        <div className="mb-2">
          <strong>채용절차</strong>
          <div className="text-sm">{job.hiring_process.join(' -> ')}</div>
        </div>
        <div className="mb-2">
          <strong>추가정보</strong>
          <div className="text-sm">
            {job.additional_info.map((line, index) => (
              <div key={`${job.id}-ai-${index}`}>- {line}</div>
            ))}
          </div>
        </div>
        <div className="mb-2">
          <strong>업데이트:</strong> {job.uploaded_date}
        </div>
        <div className="mb-2">
          <strong>Link:</strong>{' '}
          <a href={job.link} target="_blank" rel="noopener noreferrer">
            공고 보러가기
          </a>
        </div>
      </AccordionContent>
    </AccordionItem>
  );
};

export default JobAccordionItem;
