import styles from './Slider.module.css';

interface Props {
  value: number;
  min: number;
  max: number;
  step?: number;
  unit?: string;
  onChange: (v: number) => void;
}

export function Slider({ value, min, max, step = 1, unit = '', onChange }: Props) {
  return (
    <div className={styles.wrap}>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        className={styles.range}
      />
      <span className={styles.readout}>
        {value}
        {unit}
      </span>
    </div>
  );
}
