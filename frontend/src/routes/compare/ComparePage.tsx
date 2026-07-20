import { useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Topbar } from '../../components/Topbar';
import { Button } from '../../components/Button';
import { Select, Input } from '../../components/Select';
import { Field } from '../../components/Field';
import { ScoreBar } from '../../components/ScoreBar';
import { Skeleton, SkeletonStack } from '../../components/Skeleton';
import { EmptyState } from '../../components/EmptyState';
import { IconCompare } from '../../components/Icons';
import { api } from '../../lib/api';
import { renderMarkdownLite, timeAgo } from '../../lib/format';
import { pipelinePills } from '../../lib/pipelineLabels';
import { useToast } from '../../components/Toast';
import type { CompareResponse, DeepEvalScores, PipelineConfig, PipelineResult } from '../../lib/types';
import styles from './ComparePage.module.css';

const RAGAS_METRICS: { key: keyof DeepEvalScores; label: string }[] = [
  { key: 'faithfulness', label: 'faithful' },
  { key: 'answer_relevance', label: 'ans rel' },
  { key: 'context_precision', label: 'ctx prec' },
  { key: 'context_recall', label: 'ctx rec' },
];

const LATENCY_STEPS: { key: string; label: string; color: string }[] = [
  { key: 'query_translation_ms', label: 'query trans', color: 'var(--blue)' },
  { key: 'retrieval_ms', label: 'retrieval', color: 'var(--green)' },
  { key: 'post_retrieval_ms', label: 'post-retr', color: 'var(--brand-2)' },
  { key: 'generation_ms', label: 'generation', color: 'var(--amber)' },
];

const TERMINAL_STATUSES = new Set(['completed', 'failed']);

export function ComparePage() {
  const { flash } = useToast();
  const queryClient = useQueryClient();
  const { data: pipelines } = useQuery({ queryKey: ['pipelines'], queryFn: api.listPipelines });
  const { data: pastComparisons, isLoading: comparisonsLoading } = useQuery({
    queryKey: ['comparisons'],
    queryFn: api.listComparisons,
    // Keep rail statuses live while an evaluation is still running
    refetchInterval: (query) =>
      query.state.data?.some((c) => !TERMINAL_STATUSES.has(c.status)) ? 3000 : false,
  });
  const [searchParams] = useSearchParams();
  const [idA, setIdA] = useState(() => searchParams.get('a') ?? '');
  const [idB, setIdB] = useState('');
  const [query, setQuery] = useState('');
  const [result, setResult] = useState<CompareResponse | null>(null);
  // Query text of an in-flight run, shown as a pinned active rail card until
  // the server responds with the real comparison.
  const [pendingQuery, setPendingQuery] = useState<string | null>(null);

  const readyPipelines = (pipelines ?? []).filter((p) => p.status === 'ready');

  const compareMutation = useMutation({
    mutationFn: () => api.compare(idA, idB, query),
    onSuccess: (res) => {
      setPendingQuery(null);
      setResult(res);
      queryClient.invalidateQueries({ queryKey: ['comparisons'] });
    },
    onError: (err) => {
      setPendingQuery(null);
      flash(err instanceof Error ? err.message : 'Comparison failed', 'var(--red)');
    },
  });

  function runComparison() {
    setResult(null);
    setPendingQuery(query);
    compareMutation.mutate();
  }

  const statusQuery = useQuery({
    queryKey: ['compare-status', result?.id],
    queryFn: () => api.getCompareStatus(result!.id),
    enabled: !!result,
    refetchInterval: (query) =>
      query.state.data && TERMINAL_STATUSES.has(query.state.data.status) ? false : 1500,
  });

  async function openComparison(comparisonId: string) {
    // Clicking the open comparison again closes it.
    if (result?.id === comparisonId) {
      setResult(null);
      return;
    }
    try {
      const detail = await api.getCompareStatus(comparisonId);
      if (!detail.result1 || !detail.result2) {
        flash('Comparison results are not available', 'var(--red)');
        return;
      }
      setResult({ id: detail.id, result1: detail.result1, result2: detail.result2 });
    } catch (err) {
      flash(err instanceof Error ? err.message : 'Failed to load comparison', 'var(--red)');
    }
  }

  const pipelineA = pipelines?.find((p) => p.id === result?.result1.pipeline_id);
  const pipelineB = pipelines?.find((p) => p.id === result?.result2.pipeline_id);
  const evaluationDone = statusQuery.data?.status === 'completed';
  const evaluationFailed = statusQuery.data?.status === 'failed';

  return (
    <>
      <Topbar title="Compare" />
      <div className={styles.wrap}>
        <aside className={styles.rail}>
          <div className={styles.railTitle}>History</div>
          {pendingQuery !== null && (
            <button className={styles.pastItem} data-active="true">
              <span className={styles.pastQuery}>{pendingQuery}</span>
              <span className={styles.pastMeta}>
                <span className={styles.pastStatus} data-status="running">
                  running
                </span>
                just now
              </span>
            </button>
          )}
          {comparisonsLoading &&
            [0, 1, 2].map((i) => (
              <SkeletonStack key={i} className={styles.pastItem}>
                <Skeleton height={13} width="85%" />
                <Skeleton height={10} width="55%" />
              </SkeletonStack>
            ))}
          {!comparisonsLoading && pendingQuery === null && (!pastComparisons || pastComparisons.length === 0) && (
            <div className={styles.railEmpty}>No comparisons yet.</div>
          )}
          {(pastComparisons ?? []).map((c) => (
            <button
              key={c.id}
              className={styles.pastItem}
              data-active={c.id === result?.id}
              onClick={() => openComparison(c.id)}
            >
              <span className={styles.pastQuery}>{c.query}</span>
              <span className={styles.pastMeta}>
                <span className={styles.pastStatus} data-status={c.status}>
                  {c.status}
                </span>
                {timeAgo(c.created_at)}
              </span>
            </button>
          ))}
        </aside>

        <div className={styles.content}>
        <div className={styles.controlCard}>
          <div className={styles.controlRow}>
            <Field label="Pipeline A">
              <Select value={idA} onChange={(e) => setIdA(e.target.value)}>
                <option value="">Select pipeline…</option>
                {readyPipelines.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name}
                  </option>
                ))}
              </Select>
            </Field>
            <Field label="Pipeline B">
              <Select value={idB} onChange={(e) => setIdB(e.target.value)}>
                <option value="">Select pipeline…</option>
                {readyPipelines.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name}
                  </option>
                ))}
              </Select>
            </Field>
          </div>
          <Field label="Query">
            <Input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Ask both pipelines the same question…" />
          </Field>
          <Button
            variant="primary"
            onClick={runComparison}
            disabled={!idA || !idB || idA === idB || !query.trim() || compareMutation.isPending}
          >
            {compareMutation.isPending ? 'Running…' : 'Run comparison'}
          </Button>
        </div>

        {compareMutation.isPending && (
          <div className={styles.columns}>
            {[0, 1].map((i) => (
              <div key={i} className={styles.column}>
                <Skeleton height={16} width="45%" />
                <Skeleton height={96} />
                <Skeleton height={11} width={90} />
                <Skeleton height={56} />
                <Skeleton height={11} width={90} />
                <Skeleton height={56} />
              </div>
            ))}
          </div>
        )}

        {!result && !compareMutation.isPending && (
          <EmptyState
            icon={<IconCompare width={20} height={20} />}
            title="No comparison yet"
            description="Pick two ready pipelines and a query, then run a comparison to see answers, latency, and retrieval side by side."
          />
        )}

        {result && pipelineA && pipelineB && (
          <div className={styles.columns}>
            <ResultColumn
              pipeline={pipelineA}
              result={result.result1}
              otherChunks={result.result2.chunks}
              scores={statusQuery.data?.evaluation_scores?.pipeline_a}
              evaluationDone={evaluationDone}
              evaluationFailed={evaluationFailed}
            />
            <ResultColumn
              pipeline={pipelineB}
              result={result.result2}
              otherChunks={result.result1.chunks}
              scores={statusQuery.data?.evaluation_scores?.pipeline_b}
              evaluationDone={evaluationDone}
              evaluationFailed={evaluationFailed}
            />
          </div>
        )}

        </div>
      </div>
    </>
  );
}

function ResultColumn({
  pipeline,
  result,
  otherChunks,
  scores,
  evaluationDone,
  evaluationFailed,
}: {
  pipeline: PipelineConfig;
  result: PipelineResult;
  otherChunks: PipelineResult['chunks'];
  scores: DeepEvalScores | undefined;
  evaluationDone: boolean;
  evaluationFailed: boolean;
}) {
  return (
    <div className={styles.column}>
      <div className={styles.columnHeader}>
        <div className={styles.columnName}>{pipeline.name}</div>
        <div className={styles.columnConfig}>{pipelinePills(pipeline).join(' · ')}</div>
      </div>

      <div className={styles.answer} dangerouslySetInnerHTML={{ __html: renderMarkdownLite(result.answer) }} />

      <div className={styles.sectionLabel}>Latency</div>
      <div className={styles.latencyBlock}>
        {LATENCY_STEPS.map((step) => {
          const ms = result.latency[step.key] ?? 0;
          return <ScoreBar key={step.key} label={step.label} value={ms} maxValue={2500} displayValue={`${ms}ms`} color={step.color} />;
        })}
      </div>

      <div className={styles.sectionLabel}>DEEPEVAL evaluation</div>
      {evaluationDone && scores ? (
        <div className={styles.latencyBlock}>
          {RAGAS_METRICS.map((m) => {
            const value = scores[m.key];
            if (value == null) return null;
            return (
              <ScoreBar
                key={m.key}
                label={m.label}
                value={value}
                displayValue={value.toFixed(2)}
                color="linear-gradient(90deg,#065f46,#10B981)"
              />
            );
          })}
        </div>
      ) : evaluationFailed || (evaluationDone && !scores) ? (
        <div className={styles.evalFailed}>Evaluation failed — check the evaluation-service logs.</div>
      ) : (
        <div className={styles.latencyBlock}>
          {RAGAS_METRICS.map((m) => (
            <div key={m.key} className={styles.ragasSkeletonRow}>
              <Skeleton width={80} height={11} />
              <Skeleton height={6} />
            </div>
          ))}
        </div>
      )}

      <div className={styles.sectionLabel}>Retrieved chunks</div>
      <div className={styles.chunkList}>
        {result.chunks.map((c, i) => {
          const unique = !otherChunks.some((o) => o.source === c.source && o.content === c.content);
          return (
            <div key={i} className={styles.chunkCard}>
              <div className={styles.chunkSource}>
                {c.source}
                {unique && <span className={styles.uniqueTag}>◆ only in this pipeline</span>}
              </div>
              <div className={styles.chunkText}>{c.content}</div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
