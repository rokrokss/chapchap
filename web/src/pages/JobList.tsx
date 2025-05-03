import { useEffect, useState, useCallback } from 'react';
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from '@/components/ui/accordion';
import { fetchAllActiveJobs } from '@/services/jobs';
import { Button } from '@/components/ui/button';

type Job = {
  id: string;
  job_title: string;
  company_name: string;
  affiliate_company_name: string;
  link: string;
  team_info: string;
  responsibilities: string;
  qualifications: string;
  preferred_qualifications: string;
  hiring_process: string[];
  additional_info: string;
  uploaded_date: string;
  created_at: string;
  updated_at: string;
  is_active: boolean;
};

const JobList = () => {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [filteredJobs, setFilteredJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(false);
  const [accordianOpen, setAccordionOpen] = useState('');
  const [selectedCompanies, setSelectedCompanies] = useState<string[]>([]);
  const [selectedTags, setSelectedTags] = useState<string[]>([]);

  const loadAllActiveJobs = useCallback(async () => {
    setLoading(true);
    const newJobs = await fetchAllActiveJobs();
    console.log(newJobs);
    setJobs(newJobs);
    setLoading(false);
    await filterJobs(newJobs, selectedCompanies, selectedTags);
  }, []);

  useEffect(() => {
    loadAllActiveJobs();
  }, []);

  const onClickAccordion = (id: string) => {
    setAccordionOpen(accordianOpen === id ? '' : id);
  };

  const onClickCompany = (
    event: React.MouseEvent<HTMLButtonElement>,
    jobId: string,
    companyName: string
  ) => {
    event.stopPropagation();
    console.log(jobId, companyName);
    if (selectedCompanies.includes(companyName)) {
      const newSelectedCompanies = selectedCompanies.filter(company => company !== companyName);
      setSelectedCompanies(newSelectedCompanies);
      filterJobs(jobs, newSelectedCompanies, selectedTags);
    } else {
      const newSelectedCompanies = [...selectedCompanies, companyName];
      setSelectedCompanies(newSelectedCompanies);
      filterJobs(jobs, newSelectedCompanies, selectedTags);
    }
  };

  const filterJobs = async (
    allJobs: Job[],
    selectedCompanies: string[],
    selectedTags: string[]
  ) => {
    const newFilteredJobs = allJobs.filter(
      job =>
        selectedCompanies.length === 0 ||
        selectedCompanies.includes(job.company_name) ||
        selectedCompanies.includes(job.affiliate_company_name)
    );
    setFilteredJobs(newFilteredJobs);
  };

  return (
    <div>
      <Accordion
        type="single"
        collapsible
        className="w-3xl px-6"
        value={accordianOpen}
        onValueChange={setAccordionOpen}
      >
        {filteredJobs.map((job, _) => (
          <AccordionItem key={job.id} value={job.id}>
            <AccordionTrigger className="mb-0 pb-4">
              <div>{`${job.job_title} @ ${job.company_name}`}</div>
            </AccordionTrigger>
            <div onClick={() => onClickAccordion(`${job.id}`)}>
              <div className="mb-4">
                <Button
                  variant={selectedCompanies.includes(job.company_name) ? 'default' : 'outline'}
                  size="xs"
                  className="mr-1 duration-0"
                  onClick={e => onClickCompany(e, job.id, job.company_name)}
                >
                  {job.company_name}
                </Button>
                {job.affiliate_company_name != job.company_name ? (
                  <Button
                    variant={
                      selectedCompanies.includes(job.affiliate_company_name) ? 'default' : 'outline'
                    }
                    size="xs"
                    className="mr-1 duration-0"
                    onClick={e => onClickCompany(e, job.id, job.affiliate_company_name)}
                  >
                    {job.affiliate_company_name}
                  </Button>
                ) : null}
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
                  {job.responsibilities.split('\n').map(line => (
                    <div>{line}</div>
                  ))}
                </div>
              </div>
              <div className="mb-2">
                <strong>지원자격</strong>
                <div className="text-sm">
                  {job.qualifications.split('\n').map(line => (
                    <div>{line}</div>
                  ))}
                </div>
              </div>
              <div className="mb-2">
                <strong>우대사항</strong>
                <div className="text-sm">
                  {job.preferred_qualifications.split('\n').map(line => (
                    <div>{line}</div>
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
                  <div className="text-sm">
                    {job.additional_info.split('\n').map(line => (
                      <div>{line}</div>
                    ))}
                  </div>
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
        ))}
        {loading ? <div>Loading...</div> : null}
      </Accordion>
    </div>
  );
};

export default JobList;
