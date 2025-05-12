import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Layout from './pages/Layout';
import JobList from './pages/JobList';
import JobMatcher from './pages/JobMatcher';
import NoPage from './pages/NoPage';
import { ThemeProvider } from '@/components/theme-provider';
import JobMatcherText from './pages/JobMatcherText';

function App() {
  return (
    <ThemeProvider defaultTheme="light" storageKey="vite-ui-theme">
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Layout />}>
            <Route index element={<JobList />} />
            <Route path="match" element={<JobMatcher />} />
            <Route path="match-text" element={<JobMatcherText />} />
            <Route path="*" element={<NoPage />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </ThemeProvider>
  );
}

export default App;
