export const fetchAllActiveJobs = async () => {
  const response = await fetch(`http://localhost:8000/job_info/all_active`);
  const data = await response.json();
  return data;
};

export const fetchJobCountByTag = async () => {
  const response = await fetch(`http://localhost:8000/tag/job_count`);
  const data = await response.json();
  return data;
};

export const fetchJobCountByCompany = async () => {
  const response = await fetch(
    `http://localhost:8000/company/job_count_including_affiliate_companies`
  );
  const data = await response.json();
  return data;
};
