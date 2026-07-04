import type { CSSProperties, ReactNode } from 'react';
import styles from './DataTable.module.css';

export function Table({ columns, children }: { columns: string; children: ReactNode }) {
  return (
    <div className={styles.table} style={{ '--cols': columns } as CSSProperties}>
      {children}
    </div>
  );
}

export function TableHead({ labels }: { labels: string[] }) {
  return (
    <div className={styles.headRow}>
      {labels.map((l) => (
        <span key={l}>{l}</span>
      ))}
    </div>
  );
}

export function TableRow({ children, className }: { children: ReactNode; className?: string }) {
  return <div className={`${styles.row} ${className ?? ''}`}>{children}</div>;
}
