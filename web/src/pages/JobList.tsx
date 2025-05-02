import { useEffect, useState, useRef, useCallback } from 'react';
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from '@/components/ui/accordion';
import { fetchActiveJobs } from '@/services/jobs';

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
  const [page, setPage] = useState(0);
  const [loading, setLoading] = useState(false);
  const [hasMore, setHasMore] = useState(true);
  const observer = useRef<IntersectionObserver | null>(null);
  const didMountRef = useRef(false); // StrictMode 방지용

  const pageLimit = 15;

  const loadMoreJobs = useCallback(async () => {
    setLoading(true);
    const newJobs = await fetchActiveJobs(page, pageLimit);
    if (newJobs.length < pageLimit) {
      setHasMore(false);
    } else {
      setJobs(prevJobs => [...prevJobs, ...newJobs]);
    }
    setLoading(false);
  }, [page]);

  useEffect(() => {
    if (didMountRef.current && hasMore) {
      loadMoreJobs();
    } else {
      didMountRef.current = true;
    }
  }, [loadMoreJobs, hasMore]);

  const lastPostElementRef = useCallback(
    (node: HTMLElement | null) => {
      if (loading || !hasMore) return; // Stop observing if loading or no more posts
      if (observer.current) observer.current.disconnect();

      observer.current = new IntersectionObserver(entries => {
        if (entries[0].isIntersecting) {
          setPage(prevPage => prevPage + 1); // Trigger loading of new posts by changing page number
        }
      });

      if (node) observer.current.observe(node);
    },
    [loading, hasMore]
  );

  return (
    <Accordion type="single" collapsible className="w-3xl px-6">
      {jobs.map((job, index) => (
        <AccordionItem
          key={job.id}
          value={job.id}
          ref={jobs.length === index + 1 ? lastPostElementRef : null}
        >
          <AccordionTrigger>{`${job.job_title} at ${job.company_name}`}</AccordionTrigger>
          <AccordionContent>
            <p>
              <strong>Affiliate Company:</strong> {job.affiliate_company_name}
            </p>
            <p>
              <strong>Link:</strong>{' '}
              <a href={job.link} target="_blank" rel="noopener noreferrer">
                {job.link}
              </a>
            </p>
            <p>
              <strong>Team Info:</strong> {job.team_info}
            </p>
            <p>
              <strong>Responsibilities:</strong> {job.responsibilities}
            </p>
            <p>
              <strong>Qualifications:</strong> {job.qualifications}
            </p>
            <p>
              <strong>Preferred Qualifications:</strong> {job.preferred_qualifications}
            </p>
            <p>
              <strong>Hiring Process:</strong> {job.hiring_process.join(', ')}
            </p>
            <p>
              <strong>Additional Info:</strong> {job.additional_info}
            </p>
            <p>
              <strong>Uploaded Date:</strong> {job.uploaded_date}
            </p>
            <p>
              <strong>Created At:</strong> {job.created_at}
            </p>
            <p>
              <strong>Updated At:</strong> {job.updated_at}
            </p>
            <p>
              <strong>Active:</strong> {job.is_active ? 'Yes' : 'No'}
            </p>
          </AccordionContent>
        </AccordionItem>
      ))}
      {loading && <p>Loading...</p>}
    </Accordion>
  );
};

export default JobList;
