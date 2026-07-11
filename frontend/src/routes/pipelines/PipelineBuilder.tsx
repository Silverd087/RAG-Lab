import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { Topbar } from '../../components/Topbar';
import { Button } from '../../components/Button';
import { Field } from '../../components/Field';
import { Select, Input, TextArea } from '../../components/Select';
import { Slider } from '../../components/Slider';
import { Toggle } from '../../components/Toggle';
import { IconCheck } from '../../components/Icons';
import { api } from '../../lib/api';
import { useToast } from '../../components/Toast';
import type {
  ChunkingStrategy,
  Provider,
  RetrievalMode,
  RerankerConfig,
  VectorDb,
} from '../../lib/types';
import styles from './PipelineBuilder.module.css';

const STEP_META = [
  { title: 'General', desc: 'Name your pipeline.' },
  { title: 'Chunking', desc: 'How documents are split before indexing.' },
  { title: 'Indexing', desc: 'Vector store and embedding model.' },
  { title: 'Query translation', desc: 'Rewrite the query before retrieval.' },
  { title: 'Retrieval', desc: 'How chunks are searched and ranked.' },
  { title: 'Post-retrieval', desc: 'Rerank or filter retrieved chunks.' },
  { title: 'Generation', desc: 'LLM and prompt template.' },
  { title: 'Review', desc: 'Confirm your configuration.' },
];

const DEFAULT_PROMPT = 'Answer the question using only the context below.\n\nContext:\n{context}\n\nQuestion: {question}';

const PROVIDER_LABELS: Record<Provider, string> = {
  google: 'Google',
  anthropic: 'Anthropic',
  huggingface: 'Hugging Face',
};

const EMBEDDING_MODELS: Record<Provider, string[]> = {
  google: ['gemini-embedding-001', 'text-embedding-004'],
  anthropic: ['voyage-3-large', 'voyage-3.5'],
  huggingface: ['sentence-transformers/all-MiniLM-L6-v2', 'sentence-transformers/all-mpnet-base-v2', 'BAAI/bge-small-en-v1.5'],
};

// Backend get_llm only supports Google and Anthropic
type GenerationProvider = Exclude<Provider, 'huggingface'>;

const LLM_MODELS: Record<GenerationProvider, string[]> = {
  google: ['gemini-2.5-flash', 'gemini-2.5-pro'],
  anthropic: ['claude-sonnet-5', 'claude-haiku-4-5-20251001', 'claude-opus-4-8'],
};

export function PipelineBuilder() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { flash } = useToast();
  const [step, setStep] = useState(0);

  const [name, setName] = useState('');
  const [chunkStrategy, setChunkStrategy] = useState<ChunkingStrategy>('recursive');
  const [chunkSize, setChunkSize] = useState(500);
  const [overlap, setOverlap] = useState(50);
  const [parentDoc, setParentDoc] = useState(false);

  const [vectorDb, setVectorDb] = useState<VectorDb>('qdrant');
  const [indexingProvider, setIndexingProvider] = useState<Provider>('google');
  const [embeddingModel, setEmbeddingModel] = useState('gemini-embedding-001');

  const [multiQuery, setMultiQuery] = useState(false);
  const [hyde, setHyde] = useState(false);
  const [stepBack, setStepBack] = useState(false);

  const [mode, setMode] = useState<RetrievalMode>('dense');
  const [topK, setTopK] = useState(5);

  const [reranker, setReranker] = useState<RerankerConfig>('none');
  const [topN, setTopN] = useState(5);
  const [reorder, setReorder] = useState(false);

  const [generationProvider, setGenerationProvider] = useState<GenerationProvider>('google');
  const [llm, setLlm] = useState('gemini-2.5-flash');
  const [prompt, setPrompt] = useState(DEFAULT_PROMPT);

  const changeIndexingProvider = (p: Provider) => {
    setIndexingProvider(p);
    setEmbeddingModel(EMBEDDING_MODELS[p][0]);
  };

  const changeGenerationProvider = (p: GenerationProvider) => {
    setGenerationProvider(p);
    setLlm(LLM_MODELS[p][0]);
  };

  const changeMultiQuery = (v: boolean) => {
    setMultiQuery(v);
    if (!v && reranker === 'reciprocal_rank_fusion') setReranker('none');
  };

  const createMutation = useMutation({
    mutationFn: () =>
      api.createPipeline({
        name,
        chunking: {
          strategy: chunkStrategy,
          chunk_size: chunkSize,
          overlap,
          parent_doc: parentDoc,
        },
        indexing: { vector_db: vectorDb, provider: indexingProvider, embedding_model: embeddingModel },
        query_translation: { multi_query: multiQuery, hyde, step_back: stepBack },
        retrieval: { mode, top_k: topK },
        post_retrieval: {
          reranker,
          top_n: reranker === 'none' ? null : topN,
          reorder,
        },
        generation: { llm, provider: generationProvider, prompt: { prompt } },
      }),
    onSuccess: (created) => {
      queryClient.invalidateQueries({ queryKey: ['pipelines'] });
      flash('Pipeline created', 'var(--green)');
      navigate(`/pipelines/${created.id}`);
    },
    onError: (err) => flash(err instanceof Error ? err.message : 'Failed to create pipeline', 'var(--red)'),
  });

  const isLast = step === STEP_META.length - 1;
  const pct = ((step + 1) / STEP_META.length) * 100;
  const canNext = step === 0 ? name.trim().length > 0 : true;

  return (
    <>
      <Topbar title="New pipeline" />
      <div className={styles.wrap}>
        <div className={styles.stepNav}>
          {STEP_META.map((s, i) => (
            <button
              key={s.title}
              className={styles.stepItem}
              data-active={i === step}
              onClick={() => i < step && setStep(i)}
            >
              <span className={styles.stepCircle} data-done={i < step} data-active={i === step}>
                {i < step ? <IconCheck width={11} height={11} /> : i + 1}
              </span>
              {s.title}
            </button>
          ))}
        </div>

        <div className={styles.pane}>
          <div className={styles.progressTrack}>
            <div className={styles.progressFill} style={{ width: `${pct}%` }} />
          </div>
          <h2 className={styles.stepTitle}>{STEP_META[step].title}</h2>
          <p className={styles.stepDesc}>{STEP_META[step].desc}</p>

          <div className={styles.body}>
            {step === 0 && (
              <Field label="Pipeline name">
                <Input
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="e.g. baseline-v1"
                  autoFocus
                />
              </Field>
            )}

            {step === 1 && (
              <>
                <Field label="Chunking strategy">
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
                  desc="Index small chunks, retrieve their larger parent document."
                />
              </>
            )}

            {step === 2 && (
              <>
                <Field label="Vector store">
                  <Select value={vectorDb} onChange={(e) => setVectorDb(e.target.value as VectorDb)}>
                    <option value="qdrant">Qdrant</option>
                    <option value="chroma">Chroma</option>
                  </Select>
                </Field>
                <Field label="Provider">
                  <Select value={indexingProvider} onChange={(e) => changeIndexingProvider(e.target.value as Provider)}>
                    <option value="google">Google</option>
                    <option value="anthropic">Anthropic</option>
                    <option value="huggingface">Hugging Face</option>
                  </Select>
                </Field>
                <Field label="Embedding model">
                  <Select value={embeddingModel} onChange={(e) => setEmbeddingModel(e.target.value)}>
                    {EMBEDDING_MODELS[indexingProvider].map((m) => (
                      <option key={m} value={m}>{m}</option>
                    ))}
                  </Select>
                </Field>
              </>
            )}

            {step === 3 && (
              <>
                <Toggle checked={multiQuery} onChange={changeMultiQuery} label="Multi-query" desc="Generate several query variants and merge results." />
                <Toggle checked={hyde} onChange={setHyde} label="HyDE" desc="Retrieve using a hypothetical answer document." />
                <Toggle checked={stepBack} onChange={setStepBack} label="Step-back prompting" desc="Ask a more general question first." />
              </>
            )}

            {step === 4 && (
              <>
                <Field label="Retrieval mode">
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
              </>
            )}

            {step === 5 && (
              <>
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
              </>
            )}

            {step === 6 && (
              <>
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
                  <TextArea rows={8} value={prompt} onChange={(e) => setPrompt(e.target.value)} />
                </Field>
              </>
            )}

            {step === 7 && (
              <div className={styles.review}>
                {[
                  ['Name', name],
                  ['Chunking', `${chunkStrategy} · ${chunkSize}/${overlap}${parentDoc ? ' · parent-doc' : ''}`],
                  ['Indexing', `${vectorDb} · ${PROVIDER_LABELS[indexingProvider]} · ${embeddingModel}`],
                  [
                    'Query translation',
                    [multiQuery && 'multi-query', hyde && 'HyDE', stepBack && 'step-back'].filter(Boolean).join(', ') || 'none',
                  ],
                  ['Retrieval', `${mode} · top-${topK}`],
                  ['Post-retrieval', `${reranker}${reranker !== 'none' ? ` · top-${topN}` : ''}${reorder ? ' · reorder' : ''}`],
                  ['Generation', `${PROVIDER_LABELS[generationProvider]} · ${llm}`],
                ].map(([k, v]) => (
                  <div key={k} className={styles.reviewRow}>
                    <span className={styles.reviewKey}>{k}</span>
                    <span className={styles.reviewValue}>{v}</span>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div className={styles.footer}>
            <Button variant="secondary" onClick={() => setStep((s) => s - 1)} disabled={step === 0}>
              Back
            </Button>
            {!isLast && (
              <Button variant="primary" onClick={() => setStep((s) => s + 1)} disabled={!canNext}>
                Next
              </Button>
            )}
            {isLast && (
              <Button variant="primary" onClick={() => createMutation.mutate()} disabled={createMutation.isPending}>
                {createMutation.isPending ? 'Creating…' : 'Create pipeline'}
              </Button>
            )}
          </div>
        </div>
      </div>
    </>
  );
}
