import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Topbar } from '../../components/Topbar';
import { Button } from '../../components/Button';
import { EmptyState } from '../../components/EmptyState';
import { IconDataset, IconPlus } from '../../components/Icons';
import { api } from '../../lib/api';
import { timeAgo } from '../../lib/format';
import { useToast } from '../../components/Toast';
import { NewDatasetPanel } from './NewDatasetPanel';
import styles from './DatasetsList.module.css';

export function DatasetsList() {
  const navigate = useNavigate();
  const { flash } = useToast();
  const queryClient = useQueryClient();
  const [panelOpen, setPanelOpen] = useState(false);

  const { data: datasets, isLoading } = useQuery({ queryKey: ['datasets'], queryFn: api.listDatasets });

  const createMutation = useMutation({
    mutationFn: (input: { name: string; description: string; items: { question: string; ground_truth: string }[] }) =>
      api.createDataset(input.name, input.description, input.items),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['datasets'] });
      setPanelOpen(false);
      flash('Dataset created', 'var(--green)');
    },
    onError: (err) => flash(err instanceof Error ? err.message : 'Failed to create dataset', 'var(--red)'),
  });

  return (
    <>
      <Topbar
        title="Datasets"
        actions={
          <Button variant="primary" onClick={() => setPanelOpen(true)}>
            <IconPlus width={14} height={14} />
            New dataset
          </Button>
        }
      />
      <div className={styles.content}>
        {!isLoading && datasets && datasets.length === 0 && (
          <EmptyState
            icon={<IconDataset width={20} height={20} />}
            title="No datasets yet"
            description="Create a golden Q/A dataset to benchmark pipelines against."
            action={
              <Button variant="primary" onClick={() => setPanelOpen(true)}>
                Create your first dataset
              </Button>
            }
          />
        )}
        {datasets && datasets.length > 0 && (
          <div className={styles.grid}>
            {datasets.map((d) => (
              <button key={d.id} className={styles.card} onClick={() => navigate(`/datasets/${d.id}`)}>
                <IconDataset width={18} height={18} />
                <div className={styles.name}>{d.name}</div>
                <div className={styles.meta}>Created {timeAgo(d.created_at)}</div>
              </button>
            ))}
          </div>
        )}
      </div>

      <NewDatasetPanel
        open={panelOpen}
        onClose={() => setPanelOpen(false)}
        onSave={(input) => createMutation.mutate(input)}
        saving={createMutation.isPending}
      />
    </>
  );
}
