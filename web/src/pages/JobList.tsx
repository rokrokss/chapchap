import React, { useEffect, useState } from 'react';
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from '@/components/ui/accordion';

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

  useEffect(() => {
    const fetchJobs = async () => {
      try {
        const response = await fetch('http://localhost:8000/job_info/active');
        const data = await response.json();
        console.log(data);
        setJobs(data);
      } catch (error) {
        console.error('Error fetching job info:', error);
      }
    };

    fetchJobs();
  }, []);

  return (
    <Accordion type="single" collapsible className="w-3xl px-6">
      {jobs.map(job => (
        <AccordionItem key={job.id} value={job.id}>
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
    </Accordion>
  );
};

export default JobList;
