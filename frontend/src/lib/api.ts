import type {
  BenchmarkListResponse,
  BenchmarkResultResponse,
  CompareResponse,
  CompareStatusResponse,
  CreatePipelineInput,
  DatasetItemCreate,
  DatasetItemResponse,
  DatasetItemUpdate,
  DatasetListResponse,
  DatasetResponse,
  DatasetUpdate,
  DocumentResponse,
  PipelineConfig,
  PipelineResult,
  PipelineStatus,
  PipelineUpdate,
  UploadResponse,
} from './types';

const BASE = '/api/v1';

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    ...init,
    headers:
      init?.body && !(init.body instanceof FormData)
        ? { 'Content-Type': 'application/json', ...init?.headers }
        : init?.headers,
  });

  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail ? JSON.stringify(body.detail) : detail;
    } catch {
      /* ignore non-JSON error body */
    }
    throw new ApiError(res.status, detail);
  }

  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

export const api = {
  listPipelines: () => request<PipelineConfig[]>('/pipelines'),
  getPipeline: (id: string) => request<PipelineConfig>(`/pipelines/${id}`),
  createPipeline: (payload: CreatePipelineInput) =>
    request<PipelineConfig>('/pipelines', { method: 'POST', body: JSON.stringify(payload) }),
  updatePipeline: (id: string, payload: PipelineUpdate) =>
    request<PipelineConfig>(`/pipelines/${id}`, { method: 'PATCH', body: JSON.stringify(payload) }),
  deletePipeline: (id: string) => request<void>(`/pipelines/${id}`, { method: 'DELETE' }),
  getPipelineStatus: (id: string) => request<PipelineStatus>(`/pipelines/${id}/status`),

  uploadDocument: (id: string, file: File) => {
    const form = new FormData();
    form.append('file', file);
    return request<UploadResponse>(`/pipelines/${id}/upload`, { method: 'POST', body: form });
  },
  listDocuments: (id: string) => request<DocumentResponse[]>(`/pipelines/${id}/documents`),

  queryPipeline: (id: string, query: string) =>
    request<PipelineResult>(`/pipelines/${id}/query`, { method: 'POST', body: JSON.stringify({ query }) }),
  getPipelineResults: (id: string) => request<PipelineResult[]>(`/pipelines/${id}/results`),

  compare: (pipeline_id1: string, pipeline_id2: string, query: string) =>
    request<CompareResponse>('/compare', {
      method: 'POST',
      body: JSON.stringify({ pipeline_id1, pipeline_id2, query }),
    }),
  getCompareStatus: (comparisonId: string) => request<CompareStatusResponse>(`/compare/${comparisonId}`),

  listDatasets: () => request<DatasetListResponse[]>('/datasets'),
  getDataset: (id: string) => request<DatasetResponse>(`/datasets/${id}`),
  createDataset: (name: string, description: string, items: DatasetItemCreate[]) =>
    request<DatasetResponse>('/datasets', { method: 'POST', body: JSON.stringify({ name, description, items }) }),
  updateDataset: (id: string, payload: DatasetUpdate) =>
    request<DatasetResponse>(`/datasets/${id}`, { method: 'PATCH', body: JSON.stringify(payload) }),
  deleteDataset: (id: string) => request<void>(`/datasets/${id}`, { method: 'DELETE' }),
  addDatasetItems: (id: string, items: DatasetItemCreate[]) =>
    request<DatasetResponse>(`/datasets/${id}/items`, { method: 'POST', body: JSON.stringify({ items }) }),
  updateDatasetItem: (datasetId: string, itemId: string, payload: DatasetItemUpdate) =>
    request<DatasetItemResponse>(`/datasets/${datasetId}/items/${itemId}`, {
      method: 'PATCH',
      body: JSON.stringify(payload),
    }),
  deleteDatasetItem: (datasetId: string, itemId: string) =>
    request<void>(`/datasets/${datasetId}/items/${itemId}`, { method: 'DELETE' }),

  runBenchmark: (pipeline_ids: string[], dataset_id: string) =>
    request<BenchmarkResultResponse>('/benchmarks', {
      method: 'POST',
      body: JSON.stringify({ pipeline_ids, dataset_id }),
    }),
  listBenchmarks: () => request<BenchmarkListResponse>('/benchmarks'),
  getBenchmark: (id: string) => request<BenchmarkResultResponse>(`/benchmarks/${id}`),
};
