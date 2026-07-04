import { NavLink } from 'react-router-dom';
import styles from './Sidebar.module.css';
import { IconGrid, IconChat, IconCompare, IconBenchmark, IconDataset } from './Icons';

const NAV = [
  { to: '/pipelines', label: 'Pipelines', icon: IconGrid },
  { to: '/query', label: 'Query', icon: IconChat },
  { to: '/compare', label: 'Compare', icon: IconCompare },
  { to: '/benchmark', label: 'Benchmark', icon: IconBenchmark },
  { to: '/datasets', label: 'Datasets', icon: IconDataset },
];

export function Sidebar() {
  return (
    <aside className={styles.sidebar}>
      <div className={styles.logo}>
        <span className={styles.logoMark} />
        <span className={styles.logoText}>RAG Lab</span>
      </div>
      <nav className={styles.nav}>
        {NAV.map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) => `${styles.item} ${isActive ? styles.active : ''}`}
          >
            <Icon width={16} height={16} />
            {label}
          </NavLink>
        ))}
      </nav>
    </aside>
  );
}
