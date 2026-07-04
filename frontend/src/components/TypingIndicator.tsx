import styles from './TypingIndicator.module.css';

export function TypingIndicator() {
  return (
    <div className={styles.wrap}>
      <span className={styles.dot} style={{ animationDelay: '0ms' }} />
      <span className={styles.dot} style={{ animationDelay: '150ms' }} />
      <span className={styles.dot} style={{ animationDelay: '300ms' }} />
    </div>
  );
}
