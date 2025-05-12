import axios from 'axios';

const API_URL = import.meta.env.VITE_API_URL;

export const fetchAnalyzeResumeStream = async (file: File, sessionId: string) => {
  const formData = new FormData();
  formData.append('file', file);

  const response = await fetch(`${API_URL}/resume/analyze`, {
    method: 'POST',
    body: formData,
    headers: {
      'X-Session-Id': sessionId,
    },
    credentials: 'include',
  });

  return response.body?.getReader();
};

export const fetchAnalyzeResumeStreamByText = async (resume: string, sessionId: string) => {
  const response = await fetch(`${API_URL}/resume/analyze_raw`, {
    method: 'POST',
    body: JSON.stringify({ resume: resume }),
    headers: {
      'Content-Type': 'application/json',
      'X-Session-Id': sessionId,
    },
    credentials: 'include',
  });

  return response.body?.getReader();
};

export const fetchMatchJob = async (sessionId: string) => {
  const response = await axios.get(`${API_URL}/resume/match_job`, {
    withCredentials: true,
    headers: {
      'X-Session-Id': sessionId,
    },
  });
  return response.data;
};

export const fetchGenerateCoverLetter = async (jobId: string, sessionId: string) => {
  const response = await fetch(`${API_URL}/resume/generate_cover_letter/${jobId}`, {
    method: 'GET',
    headers: {
      'X-Session-Id': sessionId,
    },
    credentials: 'include',
  });

  return response.body?.getReader();
};
