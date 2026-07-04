import type { ReactNode } from 'react';
import styles from './Topbar.module.css';

export function Topbar({ title, actions }: { title: string; actions?: ReactNode }) {
  return (
    <header className={styles.bar}>
      <h1 className={styles.title}>{title}</h1>
      <div className={styles.actions}>{actions}</div>
    </header>
  );
}
