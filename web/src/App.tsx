import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Layout from './pages/Layout';
import JobList from './pages/JobList';
import JobMatcher from './pages/JobMatcher';
import NoPage from './pages/NoPage';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<JobList />} />
          <Route path="match" element={<JobMatcher />} />
          <Route path="*" element={<NoPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;
