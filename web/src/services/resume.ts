const API_URL = import.meta.env.VITE_API_URL;

export const fetchAnalyzeResumeStream = async (file: File) => {
  const formData = new FormData();
  formData.append('file', file);

  const response = await fetch(`${API_URL}/resume/analyze`, {
    method: 'POST',
    body: formData,
    credentials: 'include',
  });

  return response.body?.getReader();
};
