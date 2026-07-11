import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Topbar } from '../../components/Topbar';
import { Button } from '../../components/Button';
import { Select } from '../../components/Select';
import { Field } from '../../components/Field';
import { Table, TableHead, TableRow } from '../../components/DataTable';
import { EmptyState } from '../../components/EmptyState';
import { IconBenchmark } from '../../components/Icons';
import { api } from '../../lib/api';
import { timeAgo } from '../../lib/format';
import { useToast } from '../../components/Toast';
import type { PipelineScores } from '../../lib/types';
import styles from './BenchmarkPage.module.css';

const TERMINAL_STATUSES = new Set(['completed', 'completed_with_errors']);

export function BenchmarkPage() {
  const { flash } = useToast();
  const queryClient = useQueryClient();
  const { data: pipelines } = useQuery({ queryKey: ['pipelines'], queryFn: api.listPipelines });
  const { data: datasets } = useQuery({ queryKey: ['datasets'], queryFn: api.listDatasets });
  const { data: benchmarkList } = useQuery({ queryKey: ['benchmarks'], queryFn: api.listBenchmarks });
  const [datasetId, setDatasetId] = useState('');
  const [selectedPipelineIds, setSelectedPipelineIds] = useState<string[]>([]);
  const [openBenchmarkId, setOpenBenchmarkId] = useState<string | null>(null);

  const readyPipelines = (pipelines ?? []).filter((p) => p.status === 'ready');

  const runMutation = useMutation({
    mutationFn: () => api.runBenchmark(selectedPipelineIds, datasetId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['benchmarks'] });
      flash('Benchmark submitted', 'var(--amber)');
    },
    onError: (err) => flash(err instanceof Error ? err.message : 'Benchmark failed to start', 'var(--red)'),
  });

  const benchmarkDetailQuery = useQuery({
    queryKey: ['benchmark', openBenchmarkId],
    queryFn: () => api.getBenchmark(openBenchmarkId!),
    enabled: !!openBenchmarkId,
    refetchInterval: (query) => (query.state.data && TERMINAL_STATUSES.has(query.state.data.status) ? false : 2000),
  });

  function togglePipeline(id: string) {
    setSelectedPipelineIds((prev) => (prev.includes(id) ? prev.filter((p) => p !== id) : [...prev, id]));
  }

  function datasetName(id: string) {
    return datasets?.find((d) => d.id === id)?.name ?? id;
  }

  function pipelineName(id: string) {
    return pipelines?.find((p) => p.id === id)?.name ?? id;
  }

  if (openBenchmarkId) {
    const detail = benchmarkDetailQuery.data;
    return (
      <>
        <Topbar
          title={detail ? `${datasetName(detail.dataset_id)} benchmark` : 'Benchmark'}
          actions={
            <Button variant="secondary" onClick={() => setOpenBenchmarkId(null)}>
              ← Back to benchmarks
            </Button>
          }
        />
        <div className={styles.content}>
          <ResultsTable results={detail?.results ?? null} pipelineName={pipelineName} />
        </div>
      </>
    );
  }

  const pastBenchmarks = benchmarkList?.benchmarks ?? [];

  return (
    <>
      <Topbar title="Benchmark" />
      <div className={styles.content}>
        <div className={styles.controlCard}>
          <Field label="Dataset">
            <Select value={datasetId} onChange={(e) => setDatasetId(e.target.value)}>
              <option value="">Select dataset…</option>
              {(datasets ?? []).map((d) => (
                <option key={d.id} value={d.id}>
                  {d.name}
                </option>
              ))}
            </Select>
          </Field>
          <Field label="Pipelines">
            <div className={styles.chipRow}>
              {readyPipelines.map((p) => (
                <button
                  key={p.id}
                  className={styles.chip}
                  data-active={selectedPipelineIds.includes(p.id)}
                  onClick={() => togglePipeline(p.id)}
                >
                  {p.name}
                </button>
              ))}
            </div>
          </Field>
          <Button
            variant="primary"
            onClick={() => runMutation.mutate()}
            disabled={!datasetId || selectedPipelineIds.length === 0 || runMutation.isPending}
          >
            {runMutation.isPending ? 'Running…' : 'Run benchmark'}
          </Button>
        </div>

        {runMutation.isPending && (
          <div className={styles.runningRow}>
            <span className={styles.pulseDot} />
            Evaluating {selectedPipelineIds.length} pipeline{selectedPipelineIds.length === 1 ? '' : 's'}…
          </div>
        )}

        <div>
          <div className={styles.sectionLabel}>Past benchmarks</div>
          {pastBenchmarks.length === 0 ? (
            <EmptyState
              icon={<IconBenchmark width={20} height={20} />}
              title="No benchmarks yet"
              description="Run a benchmark above to score pipelines against a golden dataset."
            />
          ) : (
            <div className={styles.pastGrid}>
              {pastBenchmarks.map((b) => (
                <button key={b.benchmark_id} className={styles.pastCard} onClick={() => setOpenBenchmarkId(b.benchmark_id)}>
                  <div className={styles.pastDataset}>{datasetName(b.dataset_id)}</div>
                  <div className={styles.pastMeta}>
                    {timeAgo(b.created_at)} · {b.results?.length ?? 0} pipelines
                  </div>
                  <div className={styles.pastStatus} data-status={b.status}>
                    {b.status}
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>
      </div>
    </>
  );
}

function ResultsTable({
  results,
  pipelineName,
}: {
  results: PipelineScores[] | null;
  pipelineName: (id: string) => string;
}) {
  if (!results || results.length === 0) {
    return <div className={styles.pendingNote}>Evaluating pipelines against the dataset in the background…</div>;
  }

  return (
    <Table columns="1.4fr 90px 90px 90px 90px">
      <TableHead labels={['Pipeline', 'Faithful', 'Ans rel', 'Ctx prec', 'Ctx rec']} />
      {results.map((r) => (
        <TableRow key={r.pipeline_id}>
          <span>
            {pipelineName(r.pipeline_id)}
            {r.status === 'failed' && <span className={styles.failedTag}> — failed: {r.error}</span>}
          </span>
          <span>{r.scores ? r.scores.faithfulness.toFixed(2) : '—'}</span>
          <span>{r.scores ? r.scores.answer_relevance.toFixed(2) : '—'}</span>
          <span>{r.scores?.context_precision != null ? r.scores.context_precision.toFixed(2) : '—'}</span>
          <span>{r.scores?.context_recall != null ? r.scores.context_recall.toFixed(2) : '—'}</span>
        </TableRow>
      ))}
    </Table>
  );
}
