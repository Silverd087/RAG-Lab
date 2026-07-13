import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { App } from './App';
import { ToastProvider } from './components/Toast';
import { PipelinesList } from './routes/pipelines/PipelinesList';
import { PipelineBuilder } from './routes/pipelines/PipelineBuilder';
import { PipelineDetail } from './routes/pipelines/PipelineDetail';
import { QueryPlayground } from './routes/query/QueryPlayground';
import { ComparePage } from './routes/compare/ComparePage';
import { BenchmarkPage } from './routes/benchmark/BenchmarkPage';
import { DatasetsList } from './routes/datasets/DatasetsList';
import { DatasetDetail } from './routes/datasets/DatasetDetail';
import './styles/global.css';

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: 1, refetchOnWindowFocus: false } },
});
 
createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <ToastProvider>
        <BrowserRouter>
          <Routes>
            <Route path="/" element={<App />}>
              <Route index element={<Navigate to="/pipelines" replace />} />
              <Route path="pipelines" element={<PipelinesList />} />
              <Route path="pipelines/new" element={<PipelineBuilder />} />
              <Route path="pipelines/:id" element={<PipelineDetail />} />
              <Route path="query" element={<QueryPlayground />} />
              <Route path="compare" element={<ComparePage />} />
              <Route path="benchmark" element={<BenchmarkPage />} />
              <Route path="datasets" element={<DatasetsList />} />
              <Route path="datasets/:id" element={<DatasetDetail />} />
            </Route>
          </Routes>
        </BrowserRouter>
      </ToastProvider>
    </QueryClientProvider>
  </StrictMode>,
);
