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
  reason: string;
  uploaded_in_a_week: boolean;
  uploaded_in_a_day: boolean;
};

interface ResumeStoreType {
  summary: string;
  setSummary: (summary: string) => void;
  matchedJobs: Job[];
  setMatchedJobs: (jobs: Job[]) => void;
  coverLetter: string;
  setCoverLetter: (coverLetter: string) => void;
  selectedJobId: string;
  setSelectedJobId: (selectedJobId: string) => void;
  selectedJobName: string;
  setSelectedJobName: (selectedJobName: string) => void;
  pdfMode: boolean;
  setPdfMode: (pdfMode: boolean) => void;
  resumeText: string;
  setResumeText: (resumeText: string) => void;
}

const useResumeStore = create<ResumeStoreType>()(set => ({
  summary: '',
  setSummary: (summary: string) => set({ summary }),
  matchedJobs: [],
  setMatchedJobs: (jobs: Job[]) => set({ matchedJobs: jobs }),
  coverLetter: '',
  setCoverLetter: (coverLetter: string) => set({ coverLetter }),
  selectedJobId: '',
  setSelectedJobId: (selectedJobId: string) => set({ selectedJobId }),
  selectedJobName: '',
  setSelectedJobName: (selectedJobName: string) => set({ selectedJobName }),
  pdfMode: true,
  setPdfMode: (pdfMode: boolean) => set({ pdfMode }),
  resumeText: '',
  setResumeText: (resumeText: string) => set({ resumeText }),
}));

export default useResumeStore;
