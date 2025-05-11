import { create } from 'zustand';

export type Job = {
  id: string;
  job_title: string;
  company_name: string;
  affiliate_company_name: string;
  link: string;
  team_info: string;
  responsibilities: string[];
  qualifications: string[];
  preferred_qualifications: string[];
  hiring_process: string[];
  additional_info: string[];
  uploaded_date: string;
  created_at: string;
  updated_at: string;
  is_active: boolean;
  tags: string[];
  cosine_similarity: number;
};

interface ResumeStoreType {
  summary: string;
  setSummary: (summary: string) => void;
  matchedJobs: Job[];
  setMatchedJobs: (jobs: Job[]) => void;
}

const useResumeStore = create<ResumeStoreType>()(set => ({
  summary: '',
  setSummary: (summary: string) => set({ summary }),
  matchedJobs: [],
  setMatchedJobs: (jobs: Job[]) => set({ matchedJobs: jobs }),
}));

export default useResumeStore;
