import styles from './Skeleton.module.css';

export function Skeleton({ width = '100%', height = 14 }: { width?: string | number; height?: number }) {
  return <div className={styles.skel} style={{ width, height }} />;
}
