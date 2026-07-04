import { useRef, useState } from 'react';
import { SlideOver } from '../../components/SlideOver';
import { Button } from '../../components/Button';
import { Field } from '../../components/Field';
import { Input, TextArea } from '../../components/Select';
import { IconTrash } from '../../components/Icons';
import { useToast } from '../../components/Toast';
import type { DatasetItemCreate } from '../../lib/types';
import styles from './NewDatasetPanel.module.css';

interface Props {
  open: boolean;
  onClose: () => void;
  onSave: (input: { name: string; description: string; items: DatasetItemCreate[] }) => void;
  saving: boolean;
}

export function NewDatasetPanel({ open, onClose, onSave, saving }: Props) {
  const { flash } = useToast();
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [items, setItems] = useState<DatasetItemCreate[]>([]);
  const fileInputRef = useRef<HTMLInputElement>(null);

  function addRow() {
    setItems((prev) => [...prev, { question: '', ground_truth: '' }]);
  }

  function updateRow(i: number, field: keyof DatasetItemCreate, value: string) {
    setItems((prev) => prev.map((it, idx) => (idx === i ? { ...it, [field]: value } : it)));
  }

  function removeRow(i: number) {
    setItems((prev) => prev.filter((_, idx) => idx !== i));
  }

  async function handleImport(file: File) {
    const text = await file.text();
    const parsed: DatasetItemCreate[] = [];
    for (const line of text.split('\n')) {
      const trimmed = line.trim();
      if (!trimmed) continue;
      try {
        const obj = JSON.parse(trimmed);
        if (typeof obj.question === 'string' && typeof obj.ground_truth === 'string') {
          parsed.push({ question: obj.question, ground_truth: obj.ground_truth });
        }
      } catch {
        /* skip malformed line */
      }
    }
    if (parsed.length === 0) {
      flash('No valid rows found — expected JSONL with question/ground_truth fields', 'var(--red)');
      return;
    }
    setItems((prev) => [...prev, ...parsed]);
    flash(`Imported ${parsed.length} rows`, 'var(--green)');
  }

  function reset() {
    setName('');
    setDescription('');
    setItems([]);
  }

  return (
    <SlideOver
      open={open}
      onClose={() => {
        reset();
        onClose();
      }}
      title="New dataset"
      footer={
        <>
          <Button
            variant="secondary"
            onClick={() => {
              reset();
              onClose();
            }}
          >
            Cancel
          </Button>
          <Button
            variant="primary"
            disabled={!name.trim() || items.length === 0 || saving}
            onClick={() => onSave({ name, description, items })}
          >
            {saving ? 'Saving…' : 'Save'}
          </Button>
        </>
      }
    >
      <Field label="Name">
        <Input value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g. transformer-qa-10" />
      </Field>
      <Field label="Description">
        <TextArea rows={2} value={description} onChange={(e) => setDescription(e.target.value)} />
      </Field>

      <div className={styles.itemsHeader}>
        <span className={styles.itemsLabel}>Golden Q/A pairs ({items.length})</span>
        <div className={styles.itemsActions}>
          <Button variant="secondary" onClick={() => fileInputRef.current?.click()}>
            Import JSONL
          </Button>
          <input
            ref={fileInputRef}
            type="file"
            accept=".jsonl,.txt"
            hidden
            onChange={(e) => {
              const f = e.target.files?.[0];
              if (f) handleImport(f);
              e.target.value = '';
            }}
          />
          <Button variant="secondary" onClick={addRow}>
            + Add item
          </Button>
        </div>
      </div>

      <div className={styles.rows}>
        {items.map((item, i) => (
          <div key={i} className={styles.row}>
            <TextArea
              rows={2}
              value={item.question}
              placeholder="Question"
              onChange={(e) => updateRow(i, 'question', e.target.value)}
            />
            <TextArea
              rows={2}
              value={item.ground_truth}
              placeholder="Ground truth answer"
              onChange={(e) => updateRow(i, 'ground_truth', e.target.value)}
            />
            <button className={styles.removeBtn} onClick={() => removeRow(i)} aria-label="Remove row">
              <IconTrash width={14} height={14} />
            </button>
          </div>
        ))}
      </div>
    </SlideOver>
  );
}
