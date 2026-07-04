import type { PipelineStatus } from '../lib/types';
import styles from './StatusPill.module.css';

const MAP: Record<PipelineStatus, { bg: string; color: string; label: string }> = {
  ready: { bg: 'var(--pill-green-bg)', color: 'var(--green)', label: 'ready' },
  ingesting: { bg: 'var(--pill-amber-bg)', color: 'var(--amber)', label: 'ingesting' },
  draft: { bg: 'var(--pill-gray-bg)', color: 'var(--gray)', label: 'draft' },
  error: { bg: 'var(--pill-red-bg)', color: 'var(--red)', label: 'error' },
};

export function StatusPill({ status }: { status: PipelineStatus }) {
  const cfg = MAP[status];
  return (
    <span className={styles.pill} style={{ background: cfg.bg, color: cfg.color }}>
      <span className={styles.dot} style={{ background: cfg.color }} />
      {cfg.label}
    </span>
  );
}
