import styles from './ScoreBar.module.css';

interface Props {
  label: string;
  value: number;
  maxValue?: number;
  displayValue: string;
  color: string;
}

export function ScoreBar({ label, value, maxValue = 1, displayValue, color }: Props) {
  const width = Math.max(0, Math.min(1, value / maxValue)) * 100;
  return (
    <div className={styles.row}>
      <span className={styles.label}>{label}</span>
      <div className={styles.track}>
        <div
          className={styles.fill}
          style={{ width: `${width}%`, background: color, transformOrigin: 'left' }}
        />
      </div>
      <span className={styles.value}>{displayValue}</span>
    </div>
  );
}
