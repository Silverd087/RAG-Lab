import type { ReactNode } from 'react';
import styles from './Skeleton.module.css';

export function Skeleton({ width = '100%', height = 14 }: { width?: string | number; height?: number }) {
  return <div className={styles.skel} style={{ width, height }} />;
}

/** Vertical stack of skeletons; pass a card/row class to mimic the loaded layout. */
export function SkeletonStack({ children, className }: { children: ReactNode; className?: string }) {
  return <div className={`${styles.stack} ${className ?? ''}`}>{children}</div>;
}
