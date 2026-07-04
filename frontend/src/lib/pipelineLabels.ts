import type { PipelineConfig, RerankerConfig } from './types';

const RERANKER_LABEL: Record<RerankerConfig, string> = {
  none: 'No rerank',
  'cross-encoder': 'Cross-encoder',
  cohere: 'Cohere rerank',
  reciprocal_rank_fusion: 'RRF',
};

function cap(s: string): string {
  return s.charAt(0).toUpperCase() + s.slice(1);
}

export function pipelinePills(config: PipelineConfig): string[] {
  const chunkLabel = config.chunking.parent_doc ? 'Parent-child' : cap(config.chunking.strategy);
  const translationExtra = config.query_translation.hyde
    ? 'HyDE'
    : config.query_translation.multi_query
      ? 'Multi-query'
      : config.query_translation.step_back
        ? 'Step-back'
        : cap(config.retrieval.mode);
  const rerankLabel = RERANKER_LABEL[config.post_retrieval.reranker];
  return [chunkLabel, translationExtra, rerankLabel];
}

export function rerankerLabel(r: RerankerConfig): string {
  return RERANKER_LABEL[r];
}
