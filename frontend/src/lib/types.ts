export type PipelineStatus = 'draft' | 'ingesting' | 'ready' | 'error';

export type ChunkingStrategy = 'recursive' | 'fixed' | 'semantic' | 'sentence';

export interface ChunkingConfig {
  strategy: ChunkingStrategy;
  chunk_size: number;
  parent_chunk_size: number | null;
  overlap: number;
  parent_overlap: number | null;
  parent_doc: boolean;
}

export type VectorDb = 'qdrant' | 'chroma';

export type Provider = 'google' | 'anthropic' | 'huggingface';

export interface IndexingConfig {
  vector_db: VectorDb;
  provider: Provider;
  embedding_model: string;
}

export interface QueryTranslationConfig {
  multi_query: boolean;
  hyde: boolean;
  step_back: boolean;
}

export type RetrievalMode = 'dense' | 'sparse' | 'hybrid' | 'mmr';

export interface RetrievalConfig {
  mode: RetrievalMode;
  top_k: number;
}

export type RerankerConfig = 'none' | 'cross-encoder' | 'cohere' | 'reciprocal_rank_fusion';

export interface PostRetrievalConfig {
  reranker: RerankerConfig;
  top_n: number | null;
  cross_encoder_model: string | null;
  cohere_model: string | null;
  compression: boolean;
  reorder: boolean;
}

export interface Prompt {
  prompt_id: string;
  prompt: string | null;
}

export interface GenerationConfig {
  llm: string;
  provider: Provider;
  streaming: boolean;
  prompt: Prompt | null;
}

export interface PipelineConfig {
  id: string;
  name: string;
  created_at: string;
  status: PipelineStatus;
  chunking: ChunkingConfig;
  indexing: IndexingConfig;
  query_translation: QueryTranslationConfig;
  retrieval: RetrievalConfig;
  post_retrieval: PostRetrievalConfig;
  generation: GenerationConfig;
}

export type CreatePipelineInput = {
  name: string;
  status?: PipelineStatus;
  chunking?: Partial<ChunkingConfig>;
  indexing?: Partial<IndexingConfig>;
  query_translation?: Partial<QueryTranslationConfig>;
  retrieval?: Partial<RetrievalConfig>;
  post_retrieval?: Partial<PostRetrievalConfig>;
  generation?: Partial<Omit<GenerationConfig, 'prompt'>> & { prompt?: Partial<Prompt> };
};

export type PipelineUpdate = Partial<
  Pick<PipelineConfig, 'name' | 'status' | 'chunking' | 'retrieval' | 'query_translation' | 'post_retrieval'>
>;

export interface ChunkTrace {
  content: string;
  source: string;
  raw_score: number;
  rerank_score: number | null;
  by?: string;
}

export interface PipelineResult {
  id: string | null;
  pipeline_id: string;
  session_id: string | null;
  created_at: string | null;
  query: string;
  query_variants: string[] | null;
  translated_query: string | null;
  chunks: ChunkTrace[];
  answer: string;
  latency: Record<string, number>;
}

export interface UploadResponse {
  status: PipelineStatus;
  job_id: string;
}

export interface StreamMetadataEvent {
  chunks: ChunkTrace[];
  query_variants: string[] | null;
  query_translation: string | null;
}

export interface StreamDoneEvent {
  result_id: string;
  latency: Record<string, number>;
}

export interface StreamHandlers {
  onMetadata?: (meta: StreamMetadataEvent) => void;
  onToken?: (text: string) => void;
  onDone?: (done: StreamDoneEvent) => void;
  onError?: (detail: string) => void;
}

export interface DeepEvalScores {
  faithfulness: number;
  // null for ad-hoc comparisons — these metrics need a ground-truth dataset
  context_recall: number | null;
  context_precision: number | null;
  answer_relevance: number;
}

export interface CompareResponse {
  id: string;
  result1: PipelineResult;
  result2: PipelineResult;
}

export interface CompareStatusResponse {
  id: string;
  status: string;
  query: string;
  result_1: string;
  result_2: string;
  evaluation_scores: {
    pipeline_a?: DeepEvalScores;
    pipeline_b?: DeepEvalScores;
  } | null;
  result1: PipelineResult | null;
  result2: PipelineResult | null;
}

export interface ComparisonListItem {
  id: string;
  query: string;
  status: string;
  created_at: string;
}

export interface DatasetItemCreate {
  question: string;
  ground_truth: string;
}

export interface DatasetItemUpdate {
  question?: string;
  ground_truth?: string;
}

export interface DatasetUpdate {
  name?: string;
  description?: string;
}

export interface DatasetItemResponse {
  id: string;
  question: string;
  ground_truth: string;
}

export interface DatasetResponse {
  id: string;
  name: string;
  description: string | null;
  created_at: string;
  items: DatasetItemResponse[] | null;
}

export interface DatasetListResponse {
  id: string;
  name: string;
  description: string | null;
  created_at: string;
}

export interface PipelineScores {
  pipeline_id: string;
  scores: DeepEvalScores | null;
  status: string;
  error: string | null;
}

export interface BenchmarkResultResponse {
  benchmark_id: string;
  dataset_id: string;
  status: string;
  created_at: string;
  results: PipelineScores[] | null;
  error: string | null;
}

export interface BenchmarkListResponse {
  benchmarks: BenchmarkResultResponse[];
}

export interface DocumentResponse {
  name: string;
  size: number | null;
  last_modified: string | null;
}
