import axios from 'axios';

const API_URL = import.meta.env.VITE_API_URL;

export const fetchAllActiveJobs = async () => {
  const response = await axios.get(`${API_URL}/job_info/all_active`, {
    withCredentials: true,
  });
  return response.data;
};

export const fetchJobCountByTag = async () => {
  const response = await axios.get(`${API_URL}/job_info/tag/job_count`, {
    withCredentials: true,
  });
  return response.data;
};

export const fetchJobCountByCompany = async () => {
  const response = await axios.get(
    `${API_URL}/job_info/company/job_count_including_affiliate_companies`,
    { withCredentials: true }
  );
  return response.data;
};
