import { useEffect, useState } from 'react';
import { Accordion } from '@/components/ui/accordion';
import { fetchAllActiveJobs, fetchJobCountByCompany, fetchJobCountByTag } from '@/services/jobs';
import { Button } from '@/components/ui/button';
import { Separator } from '@/components/ui/separator';
import JobAccordionItem from '@/components/JobAccordionItem';
import { Job } from '@/store/useResumeStore';

const JobList = () => {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [filteredJobs, setFilteredJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(false);
  const [accordianOpen, setAccordionOpen] = useState('');
  const [selectedCompanies, setSelectedCompanies] = useState<string[]>([]);
  const [selectedTags, setSelectedTags] = useState<string[]>([]);
  const [tagCounts, setTagCounts] = useState<{ tag_name: string; job_count: number }[]>([]);
  const [companyCounts, setCompanyCounts] = useState<{ company_name: string; job_count: number }[]>(
    []
  );

  const loadAllActiveJobs = async () => {
    setLoading(true);
    const newJobs = await fetchAllActiveJobs();
    setJobs(newJobs);
    await filterJobs(newJobs, selectedCompanies, selectedTags);
    setLoading(false);
  };

  const loadTagCounts = async () => {
    const newTagCounts = await fetchJobCountByTag();
    setTagCounts(newTagCounts);
  };

  const loadCompanyCounts = async () => {
    const newCompanyCounts = await fetchJobCountByCompany();
    setCompanyCounts(newCompanyCounts);
  };

  useEffect(() => {
    loadAllActiveJobs();
    loadTagCounts();
    loadCompanyCounts();
  }, []);

  const onClickAccordion = (id: string) => {
    setAccordionOpen(accordianOpen === id ? '' : id);
  };

  const onClickCompany = (event: React.MouseEvent<HTMLButtonElement>, companyName: string) => {
    event.stopPropagation();
    if (selectedCompanies.includes(companyName)) {
      const newSelectedCompanies = selectedCompanies.filter(company => company !== companyName);
      setSelectedCompanies(newSelectedCompanies);
      filterJobs(jobs, newSelectedCompanies, selectedTags);
    } else {
      const newSelectedCompanies = [...selectedCompanies, companyName];
      setSelectedCompanies(newSelectedCompanies);
      filterJobs(jobs, newSelectedCompanies, selectedTags);
    }
    setAccordionOpen('');
  };

  const onClickTag = (event: React.MouseEvent<HTMLButtonElement>, tag: string) => {
    event.stopPropagation();
    if (selectedTags.includes(tag)) {
      const newSelectedTags = selectedTags.filter(t => t !== tag);
      setSelectedTags(newSelectedTags);
      filterJobs(jobs, selectedCompanies, newSelectedTags);
    } else {
      const newSelectedTags = [...selectedTags, tag];
      setSelectedTags(newSelectedTags);
      filterJobs(jobs, selectedCompanies, newSelectedTags);
    }
    setAccordionOpen('');
  };

  const filterJobs = async (
    allJobs: Job[],
    selectedCompanies: string[],
    selectedTags: string[]
  ) => {
    const newFilteredJobs = allJobs.filter(
      job =>
        (selectedCompanies.length === 0 ||
          selectedCompanies.includes(job.company_name) ||
          selectedCompanies.includes(job.affiliate_company_name)) &&
        (selectedTags.length === 0 || job.tags.some(tag => selectedTags.includes(tag)))
    );
    setFilteredJobs(newFilteredJobs);
  };

  return (
    <div>
      <div className="w-full max-w-3xl mx-auto px-6">
        {companyCounts.map(company => (
          <Button
            key={company.company_name}
            variant={selectedCompanies.includes(company.company_name) ? 'default' : 'outline'}
            size="ss"
            className="mr-1.5 duration-0 mt-3"
            onClick={e => onClickCompany(e, company.company_name)}
          >
            {company.company_name} ({company.job_count})
          </Button>
        ))}
        {tagCounts.map(tag => (
          <Button
            key={tag.tag_name}
            variant={selectedTags.includes(tag.tag_name) ? 'default' : 'outline'}
            size="ss"
            className="mr-1.5 duration-0 mt-3"
            onClick={e => onClickTag(e, tag.tag_name)}
          >
            {tag.tag_name} ({tag.job_count})
          </Button>
        ))}
        <Separator className="mt-4" />
      </div>
      <Accordion
        type="single"
        collapsible
        className="w-full max-w-3xl mx-auto px-6"
        value={accordianOpen}
        onValueChange={setAccordionOpen}
      >
        {filteredJobs.map((job, index) => (
          <JobAccordionItem
            key={job.id}
            job={job}
            index={index}
            selectedCompanies={selectedCompanies}
            selectedTags={selectedTags}
            onClickAccordion={onClickAccordion}
            onClickCompany={onClickCompany}
            onClickTag={onClickTag}
          />
        ))}
        {loading ? <div>loading...</div> : null}
      </Accordion>
    </div>
  );
};

export default JobList;
