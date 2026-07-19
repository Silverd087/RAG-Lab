import { createContext, useCallback, useContext, useRef, useState, type ReactNode } from 'react';
import styles from './Toast.module.css';

interface ToastMsg {
  id: number;
  message: string;
  color: string;
}

interface ToastCtx {
  flash: (message: string, color?: string) => void;
}

const Ctx = createContext<ToastCtx | null>(null);

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<ToastMsg[]>([]);
  const idRef = useRef(0);

  const flash = useCallback((message: string, color = 'var(--brand)') => {
    const id = ++idRef.current;
    setToasts((prev) => [...prev, { id, message, color }]);
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id));
    }, 3500);
  }, []);

  return (
    <Ctx.Provider value={{ flash }}>
      {children}
      <div className={styles.stack} role="status" aria-live="polite">
        {toasts.map((t) => (
          <div key={t.id} className={styles.toast}>
            <span className={styles.dot} style={{ background: t.color }} />
            {t.message}
          </div>
        ))}
      </div>
    </Ctx.Provider>
  );
}

export function useToast() {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error('useToast must be used within ToastProvider');
  return ctx;
}
