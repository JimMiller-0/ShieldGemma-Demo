import { Routes, Route } from 'react-router-dom';
import Layout from './components/Layout';
import AnalyzerPage from './pages/AnalyzerPage';
import PoliciesPage from './pages/PoliciesPage';

export default function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<AnalyzerPage />} />
        <Route path="/policies" element={<PoliciesPage />} />
      </Routes>
    </Layout>
  );
}
