import { useState } from 'react';
import { Button } from '../../components/Button';
import { Field } from '../../components/Field';
import { Select, Input, TextArea } from '../../components/Select';
import { Slider } from '../../components/Slider';
import { Toggle } from '../../components/Toggle';
import { LLM_MODELS, type GenerationProvider } from './PipelineBuilder';
import type {
  ChunkingStrategy,
  PipelineConfig,
  PipelineUpdate,
  RerankerConfig,
  RetrievalMode,
} from '../../lib/types';
import styles from './PipelineDetail.module.css';

interface Props {
  pipeline: PipelineConfig;
  saving: boolean;
  onSave: (payload: PipelineUpdate) => void;
  onCancel: () => void;
}

export function PipelineEditForm({ pipeline, saving, onSave, onCancel }: Props) {
  const [name, setName] = useState(pipeline.name);

  const [chunkStrategy, setChunkStrategy] = useState<ChunkingStrategy>(pipeline.chunking.strategy);
  const [chunkSize, setChunkSize] = useState(pipeline.chunking.chunk_size);
  const [overlap, setOverlap] = useState(pipeline.chunking.overlap);
  const [parentDoc, setParentDoc] = useState(pipeline.chunking.parent_doc);

  const [multiQuery, setMultiQuery] = useState(pipeline.query_translation.multi_query);
  const [hyde, setHyde] = useState(pipeline.query_translation.hyde);
  const [stepBack, setStepBack] = useState(pipeline.query_translation.step_back);

  const [mode, setMode] = useState<RetrievalMode>(pipeline.retrieval.mode);
  const [topK, setTopK] = useState(pipeline.retrieval.top_k);

  const [reranker, setReranker] = useState<RerankerConfig>(pipeline.post_retrieval.reranker);
  const [topN, setTopN] = useState(pipeline.post_retrieval.top_n ?? 5);
  const [reorder, setReorder] = useState(pipeline.post_retrieval.reorder);

  const [generationProvider, setGenerationProvider] = useState<GenerationProvider>(
    pipeline.generation.provider === 'anthropic' ? 'anthropic' : 'google',
  );
  const [llm, setLlm] = useState(pipeline.generation.llm);
  const [prompt, setPrompt] = useState(pipeline.generation.prompt?.prompt ?? '');

  const changeMultiQuery = (v: boolean) => {
    setMultiQuery(v);
    if (!v && reranker === 'reciprocal_rank_fusion') setReranker('none');
  };

  const changeGenerationProvider = (p: GenerationProvider) => {
    setGenerationProvider(p);
    setLlm(LLM_MODELS[p][0]);
  };

  const save = () =>
    onSave({
      name,
      chunking: {
        ...pipeline.chunking,
        strategy: chunkStrategy,
        chunk_size: chunkSize,
        overlap,
        parent_doc: parentDoc,
      },
      query_translation: { multi_query: multiQuery, hyde, step_back: stepBack },
      retrieval: { mode, top_k: topK },
      post_retrieval: {
        ...pipeline.post_retrieval,
        reranker,
        top_n: reranker === 'none' ? null : topN,
        reorder,
      },
      generation: {
        llm,
        provider: generationProvider,
        streaming: pipeline.generation.streaming,
        prompt: prompt.trim() ? { prompt } : null,
      },
    });

  return (
    <>
      <div className={styles.configGrid}>
        <div className={styles.configSection}>
          <h3 className={styles.configTitle}>General</h3>
          <Field label="Pipeline name">
            <Input value={name} onChange={(e) => setName(e.target.value)} />
          </Field>
        </div>

        <div className={styles.configSection}>
          <h3 className={styles.configTitle}>Chunking</h3>
          <Field label="Strategy">
            <Select value={chunkStrategy} onChange={(e) => setChunkStrategy(e.target.value as ChunkingStrategy)}>
              <option value="recursive">Recursive</option>
              <option value="fixed">Fixed</option>
              <option value="semantic">Semantic</option>
              <option value="sentence">Sentence</option>
            </Select>
          </Field>
          <Field label="Chunk size">
            <Slider value={chunkSize} min={100} max={2000} step={50} unit=" tok" onChange={setChunkSize} />
          </Field>
          <Field label="Overlap">
            <Slider value={overlap} min={0} max={500} step={10} unit=" tok" onChange={setOverlap} />
          </Field>
          <Toggle
            checked={parentDoc}
            onChange={setParentDoc}
            label="Parent-document retriever"
            desc="Applies to documents ingested after this change."
          />
        </div>

        <div className={styles.configSection}>
          <h3 className={styles.configTitle}>Indexing</h3>
          <div className={styles.configRow}>
            <span className={styles.configLabel}>Vector store</span>
            <span className={styles.configValue}>{pipeline.indexing.vector_db}</span>
          </div>
          <div className={styles.configRow}>
            <span className={styles.configLabel}>Provider</span>
            <span className={styles.configValue}>{pipeline.indexing.provider}</span>
          </div>
          <div className={styles.configRow}>
            <span className={styles.configLabel}>Embedding model</span>
            <span className={styles.configValue}>{pipeline.indexing.embedding_model}</span>
          </div>
          <p className={styles.lockNote}>
            Locked — the vector collection was built with these settings. Create a new pipeline to change them.
          </p>
        </div>

        <div className={styles.configSection}>
          <h3 className={styles.configTitle}>Query translation</h3>
          <Toggle checked={multiQuery} onChange={changeMultiQuery} label="Multi-query" desc="Generate several query variants and merge results." />
          <Toggle checked={hyde} onChange={setHyde} label="HyDE" desc="Retrieve using a hypothetical answer document." />
          <Toggle checked={stepBack} onChange={setStepBack} label="Step-back prompting" desc="Ask a more general question first." />
        </div>

        <div className={styles.configSection}>
          <h3 className={styles.configTitle}>Retrieval</h3>
          <Field label="Mode">
            <Select value={mode} onChange={(e) => setMode(e.target.value as RetrievalMode)}>
              <option value="dense">Dense</option>
              <option value="sparse">Sparse</option>
              <option value="hybrid">Hybrid</option>
              <option value="mmr">MMR</option>
            </Select>
          </Field>
          <Field label="Top K">
            <Slider value={topK} min={1} max={20} onChange={setTopK} />
          </Field>
        </div>

        <div className={styles.configSection}>
          <h3 className={styles.configTitle}>Post-retrieval</h3>
          <Field label="Reranker">
            <Select value={reranker} onChange={(e) => setReranker(e.target.value as RerankerConfig)}>
              <option value="none">None</option>
              <option value="cross-encoder">Cross-encoder</option>
              <option value="cohere">Cohere</option>
              <option value="reciprocal_rank_fusion" disabled={!multiQuery}>
                Reciprocal rank fusion{multiQuery ? '' : ' (requires multi-query)'}
              </option>
            </Select>
          </Field>
          {reranker !== 'none' && (
            <Field label="Top N">
              <Slider value={topN} min={1} max={20} onChange={setTopN} />
            </Field>
          )}
          <Toggle checked={reorder} onChange={setReorder} label="Reorder by relevance" desc="Move the most relevant chunks to the edges of the context window." />
        </div>

        <div className={styles.configSection}>
          <h3 className={styles.configTitle}>Generation</h3>
          <Field label="Provider">
            <Select value={generationProvider} onChange={(e) => changeGenerationProvider(e.target.value as GenerationProvider)}>
              <option value="google">Google</option>
              <option value="anthropic">Anthropic</option>
            </Select>
          </Field>
          <Field label="LLM">
            <Select value={llm} onChange={(e) => setLlm(e.target.value)}>
              {LLM_MODELS[generationProvider].map((m) => (
                <option key={m} value={m}>{m}</option>
              ))}
            </Select>
          </Field>
          <Field label="Prompt template" hint="Use {context} and {question} placeholders.">
            <TextArea rows={6} value={prompt} onChange={(e) => setPrompt(e.target.value)} />
          </Field>
        </div>
      </div>

      <div className={styles.editFooter}>
        <Button variant="secondary" onClick={onCancel} disabled={saving}>
          Cancel
        </Button>
        <Button variant="primary" onClick={save} disabled={saving || name.trim().length === 0}>
          {saving ? 'Saving…' : 'Save changes'}
        </Button>
      </div>
    </>
  );
}
