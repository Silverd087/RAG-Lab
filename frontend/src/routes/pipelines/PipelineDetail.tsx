import { useRef, useState } from 'react';
import { useParams } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Topbar } from '../../components/Topbar';
import { Tabs } from '../../components/Tabs';
import { StatusPill } from '../../components/StatusPill';
import { Table, TableHead, TableRow } from '../../components/DataTable';
import { EmptyState } from '../../components/EmptyState';
import { IconChat, IconDocument, IconUpload } from '../../components/Icons';
import { api } from '../../lib/api';
import { fileSize, timeAgo } from '../../lib/format';
import { useToast } from '../../components/Toast';
import styles from './PipelineDetail.module.css';

export function PipelineDetail() {
  const { id = '' } = useParams();
  const { flash } = useToast();
  const queryClient = useQueryClient();
  const [tab, setTab] = useState<'documents' | 'history'>('documents');
  const [dragOver, setDragOver] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const { data: pipeline } = useQuery({
    queryKey: ['pipeline', id],
    queryFn: () => api.getPipeline(id),
    enabled: !!id,
  });

  const { data: docs, isLoading: docsLoading } = useQuery({
    queryKey: ['pipeline-documents', id],
    queryFn: () => api.listDocuments(id),
    enabled: !!id && tab === 'documents',
  });

  const { data: results, isLoading: resultsLoading } = useQuery({
    queryKey: ['pipeline-results', id],
    queryFn: () => api.getPipelineResults(id),
    enabled: !!id && tab === 'history',
    retry: false,
  });

  const uploadMutation = useMutation({
    mutationFn: (file: File) => api.uploadDocument(id, file),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['pipeline-documents', id] });
      queryClient.invalidateQueries({ queryKey: ['pipeline', id] });
      flash('Upload started — ingesting in the background', 'var(--amber)');
    },
    onError: (err) => flash(err instanceof Error ? err.message : 'Upload failed', 'var(--red)'),
  });

  function handleFiles(files: FileList | null) {
    if (!files || files.length === 0) return;
    Array.from(files).forEach((f) => uploadMutation.mutate(f));
  }

  return (
    <>
      <Topbar
        title={pipeline?.name ?? 'Pipeline'}
        actions={pipeline && <StatusPill status={pipeline.status} />}
      />
      <div className={styles.content}>
        <Tabs
          tabs={[
            { key: 'documents', label: 'Documents' },
            { key: 'history', label: 'Query history' },
          ]}
          active={tab}
          onChange={setTab}
        />

        {tab === 'documents' && (
          <div className={styles.tabBody}>
            <div
              className={styles.dropzone}
              data-active={dragOver}
              onClick={() => fileInputRef.current?.click()}
              onDragOver={(e) => {
                e.preventDefault();
                setDragOver(true);
              }}
              onDragLeave={() => setDragOver(false)}
              onDrop={(e) => {
                e.preventDefault();
                setDragOver(false);
                handleFiles(e.dataTransfer.files);
              }}
            >
              <IconUpload width={20} height={20} />
              <div className={styles.dropText}>Drop PDFs here or click to upload</div>
              <div className={styles.dropHint}>pdf · max 50mb</div>
              <input
                ref={fileInputRef}
                type="file"
                accept=".pdf"
                multiple
                hidden
                onChange={(e) => handleFiles(e.target.files)}
              />
            </div>

            {docsLoading && <div className={styles.muted}>Loading…</div>}
            {!docsLoading && (!docs || docs.length === 0) && (
              <EmptyState
                icon={<IconDocument width={20} height={20} />}
                title="No documents uploaded yet"
                description="Upload a PDF above to start ingestion for this pipeline."
              />
            )}
            {!docsLoading && docs && docs.length > 0 && (
              <Table columns="1fr 100px 140px">
                <TableHead labels={['Name', 'Size', 'Uploaded']} />
                {docs.map((d) => (
                  <TableRow key={d.name}>
                    <span className={styles.docName}>
                      <IconDocument width={14} height={14} />
                      {d.name}
                    </span>
                    <span>{d.size != null ? fileSize(d.size) : '—'}</span>
                    <span>{d.last_modified ? timeAgo(d.last_modified) : '—'}</span>
                  </TableRow>
                ))}
              </Table>
            )}
          </div>
        )}

        {tab === 'history' && (
          <div className={styles.tabBody}>
            {resultsLoading && <div className={styles.muted}>Loading…</div>}
            {!resultsLoading && (!results || results.length === 0) && (
              <EmptyState
                icon={<IconChat width={20} height={20} />}
                title="No queries yet"
                description="Run a query against this pipeline from the Query playground to see history here."
              />
            )}
            {!resultsLoading && results && results.length > 0 && (
              <Table columns="1fr 1.4fr 100px">
                <TableHead labels={['Query', 'Answer', 'Latency']} />
                {results.map((r) => {
                  const totalMs = Object.values(r.latency).reduce((a, b) => a + b, 0);
                  return (
                    <TableRow key={r.id ?? r.query}>
                      <span className={styles.truncate}>{r.query}</span>
                      <span className={styles.truncate}>{r.answer}</span>
                      <span>{(totalMs / 1000).toFixed(1)}s</span>
                    </TableRow>
                  );
                })}
              </Table>
            )}
          </div>
        )}
      </div>
    </>
  );
}
