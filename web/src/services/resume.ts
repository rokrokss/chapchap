import axios from 'axios';

const API_URL = import.meta.env.VITE_API_URL;

export const fetchAnalyzeResume = async (file: File) => {
  const formData = new FormData();
  formData.append('file', file);
  const response = await axios.post(`${API_URL}/resume/analyze`, formData, {
    withCredentials: true,
    headers: { 'content-type': file.type },
  });
  return response.data;
};
