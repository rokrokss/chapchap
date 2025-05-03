export const fetchActiveJobs = async (page: number, limit: number) => {
  const response = await fetch(
    `http://localhost:8000/job_info/active?offset=${page * limit}&limit=${limit}`
  );
  const data = await response.json();
  return data;
};

export const fetchAllActiveJobs = async () => {
  const response = await fetch(`http://localhost:8000/job_info/all_active`);
  const data = await response.json();
  return data;
};
