import styles from './ConfigPill.module.css';

export function ConfigPill({ children }: { children: React.ReactNode }) {
  return <span className={styles.pill}>{children}</span>;
}
