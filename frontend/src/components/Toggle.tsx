import styles from './Toggle.module.css';

interface Props {
  checked: boolean;
  onChange: (v: boolean) => void;
  label: string;
  desc?: string;
}

export function Toggle({ checked, onChange, label, desc }: Props) {
  return (
    <button
      type="button"
      className={styles.row}
      onClick={() => onChange(!checked)}
      aria-pressed={checked}
      aria-label={label}
    >
      <span>
        <span className={styles.label}>{label}</span>
        {desc && <span className={styles.desc}>{desc}</span>}
      </span>
      <span className={styles.track} data-on={checked}>
        <span className={styles.thumb} data-on={checked} />
      </span>
    </button>
  );
}
