import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Topbar } from '../../components/Topbar';
import { Button } from '../../components/Button';
import { StatusPill } from '../../components/StatusPill';
import { ConfigPill } from '../../components/ConfigPill';
import { EmptyState } from '../../components/EmptyState';
import { Skeleton } from '../../components/Skeleton';
import { IconGrid, IconPlus, IconChevronRight, IconTrash } from '../../components/Icons';
import { api } from '../../lib/api';
import { useToast } from '../../components/Toast';
import { timeAgo } from '../../lib/format';
import { pipelinePills } from '../../lib/pipelineLabels';
import styles from './PipelinesList.module.css';

export function PipelinesList() {
  const navigate = useNavigate();
  const { flash } = useToast();
  const queryClient = useQueryClient();
  const [confirmId, setConfirmId] = useState<string | null>(null);
  const { data: pipelines, isLoading } = useQuery({
    queryKey: ['pipelines'],
    queryFn: api.listPipelines,
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.deletePipeline(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['pipelines'] });
      flash('Pipeline deleted', 'var(--green)');
    },
    onError: (err) => flash(err instanceof Error ? err.message : 'Failed to delete pipeline', 'var(--red)'),
    onSettled: () => setConfirmId(null),
  });

  return (
    <>
      <Topbar
        title="Pipelines"
        actions={
          <Button variant="primary" onClick={() => navigate('/pipelines/new')}>
            <IconPlus width={14} height={14} />
            New pipeline
          </Button>
        }
      />
      <div className={styles.content}>
        {isLoading && (
          <div className={styles.grid}>
            {[0, 1, 2].map((i) => (
              <div key={i} className={styles.card}>
                <Skeleton height={18} width="60%" />
                <Skeleton height={12} width="40%" />
              </div>
            ))}
          </div>
        )}

        {!isLoading && pipelines && pipelines.length === 0 && (
          <EmptyState
            icon={<IconGrid width={22} height={22} />}
            title="No pipelines yet"
            description="Create a RAG pipeline to start ingesting documents and running queries."
            action={
              <Button variant="primary" onClick={() => navigate('/pipelines/new')}>
                Create your first pipeline
              </Button>
            }
          />
        )}

        {!isLoading && pipelines && pipelines.length > 0 && (
          <div className={styles.grid}>
            {pipelines.map((p) => (
              <div key={p.id} className={styles.card} onClick={() => navigate(`/pipelines/${p.id}`)}>
                <div className={styles.cardHeader}>
                  <div>
                    <div className={styles.name}>{p.name}</div>
                    <div className={styles.created}>Created {timeAgo(p.created_at)}</div>
                  </div>
                  <StatusPill status={p.status} />
                </div>
                <div className={styles.pills}>
                  {pipelinePills(p).map((pill) => (
                    <ConfigPill key={pill}>{pill}</ConfigPill>
                  ))}
                </div>
                {confirmId === p.id ? (
                  <div className={styles.footer}>
                    <span className={styles.confirmLabel}>Delete this pipeline?</span>
                    <Button
                      variant="secondary"
                      onClick={(e) => {
                        e.stopPropagation();
                        setConfirmId(null);
                      }}
                      disabled={deleteMutation.isPending}
                    >
                      Cancel
                    </Button>
                    <Button
                      variant="danger"
                      onClick={(e) => {
                        e.stopPropagation();
                        deleteMutation.mutate(p.id);
                      }}
                      disabled={deleteMutation.isPending}
                    >
                      {deleteMutation.isPending ? 'Deleting…' : 'Delete'}
                    </Button>
                  </div>
                ) : (
                  <div className={styles.footer}>
                    <Button
                      variant="secondary"
                      className={styles.footerBtn}
                      onClick={(e) => {
                        e.stopPropagation();
                        navigate(`/query?pipeline=${p.id}`);
                      }}
                    >
                      Query
                    </Button>
                    <Button
                      variant="secondary"
                      className={styles.footerBtn}
                      onClick={(e) => {
                        e.stopPropagation();
                        navigate(`/compare?a=${p.id}`);
                      }}
                    >
                      Compare
                    </Button>
                    <Button
                      variant="icon"
                      aria-label="Delete pipeline"
                      onClick={(e) => {
                        e.stopPropagation();
                        setConfirmId(p.id);
                      }}
                    >
                      <IconTrash width={14} height={14} />
                    </Button>
                    <Button
                      variant="icon"
                      aria-label="Open pipeline"
                      onClick={(e) => {
                        e.stopPropagation();
                        navigate(`/pipelines/${p.id}`);
                      }}
                    >
                      <IconChevronRight width={14} height={14} />
                    </Button>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </>
  );
}
