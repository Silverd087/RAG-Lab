import { useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Topbar } from '../../components/Topbar';
import { Button } from '../../components/Button';
import { Table, TableHead, TableRow } from '../../components/DataTable';
import { TextArea } from '../../components/Select';
import { IconArrowLeft, IconPencil, IconTrash, IconCheck } from '../../components/Icons';
import { Skeleton, SkeletonStack } from '../../components/Skeleton';
import { api } from '../../lib/api';
import { useToast } from '../../components/Toast';
import type { DatasetItemResponse } from '../../lib/types';
import styles from './DatasetDetail.module.css';

const PAGE_SIZE = 5;

export function DatasetDetail() {
  const { id = '' } = useParams();
  const navigate = useNavigate();
  const { flash } = useToast();
  const queryClient = useQueryClient();
  const [page, setPage] = useState(0);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editQuestion, setEditQuestion] = useState('');
  const [editGroundTruth, setEditGroundTruth] = useState('');
  const [adding, setAdding] = useState(false);
  const [newQuestion, setNewQuestion] = useState('');
  const [newGroundTruth, setNewGroundTruth] = useState('');
  const [editingDescription, setEditingDescription] = useState(false);
  const [descriptionDraft, setDescriptionDraft] = useState('');

  const { data: dataset, isLoading } = useQuery({
    queryKey: ['dataset', id],
    queryFn: () => api.getDataset(id),
    enabled: !!id,
  });

  const invalidate = () => queryClient.invalidateQueries({ queryKey: ['dataset', id] });

  const addMutation = useMutation({
    mutationFn: () => api.addDatasetItems(id, [{ question: newQuestion, ground_truth: newGroundTruth }]),
    onSuccess: () => {
      invalidate();
      setAdding(false);
      setNewQuestion('');
      setNewGroundTruth('');
      flash('Item added', 'var(--green)');
    },
    onError: (err) => flash(err instanceof Error ? err.message : 'Failed to add item', 'var(--red)'),
  });

  const deleteMutation = useMutation({
    mutationFn: (itemId: string) => api.deleteDatasetItem(id, itemId),
    onSuccess: () => {
      invalidate();
      flash('Item deleted', 'var(--green)');
    },
    onError: (err) => flash(err instanceof Error ? err.message : 'Failed to delete item', 'var(--red)'),
  });

  const editMutation = useMutation({
    mutationFn: (item: DatasetItemResponse) =>
      api.updateDatasetItem(id, item.id, { question: editQuestion, ground_truth: editGroundTruth }),
    onSuccess: () => {
      invalidate();
      setEditingId(null);
      flash('Item updated', 'var(--green)');
    },
    onError: (err) => flash(err instanceof Error ? err.message : 'Failed to update item', 'var(--red)'),
  });

  const descriptionMutation = useMutation({
    mutationFn: () => api.updateDataset(id, { description: descriptionDraft }),
    onSuccess: () => {
      invalidate();
      setEditingDescription(false);
      flash('Description updated', 'var(--green)');
    },
    onError: (err) => flash(err instanceof Error ? err.message : 'Failed to update description', 'var(--red)'),
  });

  if (isLoading || !dataset) {
    return (
      <>
        <Topbar title="Dataset" />
        <div className={styles.content}>
          <SkeletonStack>
            <Skeleton height={20} width="30%" />
            <Skeleton height={12} width="15%" />
            <Skeleton height={13} width="55%" />
            {[0, 1, 2].map((i) => (
              <Skeleton key={i} height={44} />
            ))}
          </SkeletonStack>
        </div>
      </>
    );
  }

  const items = dataset.items ?? [];
  const totalPages = Math.max(1, Math.ceil(items.length / PAGE_SIZE));
  const pageItems = items.slice(page * PAGE_SIZE, page * PAGE_SIZE + PAGE_SIZE);

  return (
    <>
      <Topbar title={dataset.name} />
      <div className={styles.content}>
        <button className={styles.backLink} onClick={() => navigate('/datasets')}>
          <IconArrowLeft width={14} height={14} />
          Back to datasets
        </button>

        <div className={styles.headerRow}>
          <div>
            <div className={styles.name}>{dataset.name}</div>
            <div className={styles.count}>{items.length} items</div>
          </div>
          <Button variant="primary" onClick={() => setAdding(true)}>
            + Add item
          </Button>
        </div>

        {editingDescription ? (
          <div className={styles.editRow}>
            <TextArea
              rows={2}
              value={descriptionDraft}
              onChange={(e) => setDescriptionDraft(e.target.value)}
              style={{ gridColumn: '1 / -1' }}
            />
            <div className={styles.editActions}>
              <Button variant="secondary" onClick={() => setEditingDescription(false)}>
                Cancel
              </Button>
              <Button variant="primary" disabled={descriptionMutation.isPending} onClick={() => descriptionMutation.mutate()}>
                Save
              </Button>
            </div>
          </div>
        ) : (
          <div className={styles.descriptionRow}>
            <p className={styles.description}>{dataset.description || 'No description.'}</p>
            <button
              className={styles.iconBtn}
              aria-label="Edit description"
              onClick={() => {
                setDescriptionDraft(dataset.description ?? '');
                setEditingDescription(true);
              }}
            >
              <IconPencil width={13} height={13} />
            </button>
          </div>
        )}

        {adding && (
          <div className={styles.editRow}>
            <TextArea rows={2} placeholder="Question" value={newQuestion} onChange={(e) => setNewQuestion(e.target.value)} />
            <TextArea
              rows={2}
              placeholder="Ground truth answer"
              value={newGroundTruth}
              onChange={(e) => setNewGroundTruth(e.target.value)}
            />
            <div className={styles.editActions}>
              <Button variant="secondary" onClick={() => setAdding(false)}>
                Cancel
              </Button>
              <Button
                variant="primary"
                disabled={!newQuestion.trim() || !newGroundTruth.trim() || addMutation.isPending}
                onClick={() => addMutation.mutate()}
              >
                Save
              </Button>
            </div>
          </div>
        )}

        <Table columns="1fr 1fr 80px">
          <TableHead labels={['Question', 'Ground truth', '']} />
          {pageItems.map((item) =>
            editingId === item.id ? (
              <TableRow key={item.id} className={styles.editingRow}>
                <TextArea rows={2} value={editQuestion} onChange={(e) => setEditQuestion(e.target.value)} />
                <TextArea rows={2} value={editGroundTruth} onChange={(e) => setEditGroundTruth(e.target.value)} />
                <button className={styles.iconBtn} onClick={() => editMutation.mutate(item)} aria-label="Save">
                  <IconCheck width={14} height={14} />
                </button>
              </TableRow>
            ) : (
              <TableRow key={item.id}>
                <span className={styles.truncate}>{item.question}</span>
                <span className={styles.truncate}>{item.ground_truth}</span>
                <span className={styles.rowActions}>
                  <button
                    className={styles.iconBtn}
                    onClick={() => {
                      setEditingId(item.id);
                      setEditQuestion(item.question);
                      setEditGroundTruth(item.ground_truth);
                    }}
                    aria-label="Edit"
                  >
                    <IconPencil width={13} height={13} />
                  </button>
                  <button className={styles.iconBtn} onClick={() => deleteMutation.mutate(item.id)} aria-label="Delete">
                    <IconTrash width={13} height={13} />
                  </button>
                </span>
              </TableRow>
            ),
          )}
        </Table>

        {totalPages > 1 && (
          <div className={styles.pagination}>
            <Button variant="secondary" disabled={page === 0} onClick={() => setPage((p) => p - 1)}>
              Prev
            </Button>
            <span className={styles.pageLabel}>
              {page + 1} / {totalPages}
            </span>
            <Button variant="secondary" disabled={page >= totalPages - 1} onClick={() => setPage((p) => p + 1)}>
              Next
            </Button>
          </div>
        )}
      </div>
    </>
  );
}
