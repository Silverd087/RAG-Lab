import { useEffect, useMemo, useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { Button } from '../../components/Button';
import { Select } from '../../components/Select';
import { StatusPill } from '../../components/StatusPill';
import { TypingIndicator } from '../../components/TypingIndicator';
import { ScoreBar } from '../../components/ScoreBar';
import { IconPlus, IconThumbsDown, IconThumbsUp } from '../../components/Icons';
import { api } from '../../lib/api';
import { renderMarkdownLite, timeAgo } from '../../lib/format';
import { randomUUID } from '../../lib/uuid';
import { useToast } from '../../components/Toast';
import type { ChunkTrace, PipelineResult } from '../../lib/types';
import styles from './QueryPlayground.module.css';

interface Message {
  role: 'user' | 'assistant';
  text: string;
  result?: PipelineResult;
  showSources?: boolean;
  /** true while tokens are still arriving over the wire */
  streaming?: boolean;
  /** false until the typewriter reveal has caught up with the full answer */
  revealed?: boolean;
}

interface Session {
  id: string;
  pipelineId: string;
  title: string;
  time: string;
  messages: Message[];
}

export function QueryPlayground() {
  const { flash } = useToast();
  const queryClient = useQueryClient();
  const { data: pipelines } = useQuery({ queryKey: ['pipelines'], queryFn: api.listPipelines });
  const [pipelineId, setPipelineId] = useState<string>('');
  const [sessions, setSessions] = useState<Session[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [input, setInput] = useState('');

  const activePipeline = pipelines?.find((p) => p.id === pipelineId) ?? pipelines?.[0];
  const effectivePipelineId = pipelineId || activePipeline?.id || '';

  const { data: pastResults } = useQuery({
    queryKey: ['pipeline-results', effectivePipelineId],
    queryFn: () => api.getPipelineResults(effectivePipelineId),
    enabled: !!effectivePipelineId,
  });

  // Queries answered before this page load, grouped by session and replayed in the sidebar.
  const historySessions = useMemo<Session[]>(() => {
    const groups = new Map<string, PipelineResult[]>();
    for (const r of pastResults ?? []) {
      const key = r.session_id ?? r.id;
      if (!key) continue;
      const group = groups.get(key);
      if (group) group.push(r);
      else groups.set(key, [r]);
    }
    return [...groups.entries()]
      .map(([key, results]) => ({
        id: key,
        pipelineId: effectivePipelineId,
        title: results[0].query.slice(0, 60),
        time: results[results.length - 1].created_at ?? '',
        messages: results.flatMap((r): Message[] => [
          { role: 'user', text: r.query },
          { role: 'assistant', text: r.answer, result: r },
        ]),
      }))
      .sort((a, b) => (b.time || '').localeCompare(a.time || ''));
  }, [pastResults, effectivePipelineId]);

  const allSessions = [
    ...sessions,
    ...historySessions.filter((h) => !sessions.some((s) => s.id === h.id)),
  ];

  const sessionsForPipeline = allSessions.filter((s) => s.pipelineId === effectivePipelineId);
  const activeSession = allSessions.find((s) => s.id === activeSessionId);
  const messages = activeSession?.messages ?? [];
  const lastAssistant = [...messages].reverse().find((m) => m.role === 'assistant');

  const [isStreaming, setIsStreaming] = useState(false);

  function updateLastAssistant(sessionId: string, updater: (m: Message) => Message) {
    setSessions((prev) =>
      prev.map((s) => {
        if (s.id !== sessionId) return s;
        const msgs = [...s.messages];
        for (let i = msgs.length - 1; i >= 0; i--) {
          if (msgs[i].role === 'assistant') {
            msgs[i] = updater(msgs[i]);
            break;
          }
        }
        return { ...s, messages: msgs };
      }),
    );
  }

  async function send() {
    const query = input.trim();
    if (!query || !effectivePipelineId || isStreaming) return;
    setInput('');

    const existingSession = allSessions.find((s) => s.id === activeSessionId && s.pipelineId === effectivePipelineId);
    const sessionId = existingSession ? existingSession.id : randomUUID();
    setSessions((prev) => {
      let next = prev;
      if (!prev.find((s) => s.id === sessionId)) {
        // Continuing a server-history session copies it into local state.
        const newSession: Session = existingSession ?? {
          id: sessionId,
          pipelineId: effectivePipelineId,
          title: query.slice(0, 60),
          time: new Date().toISOString(),
          messages: [],
        };
        next = [newSession, ...prev];
      }
      return next.map((s) =>
        s.id === sessionId
          ? {
              ...s,
              messages: [
                ...s.messages,
                { role: 'user', text: query },
                { role: 'assistant', text: '', streaming: true, revealed: false },
              ],
              time: new Date().toISOString(),
            }
          : s,
      );
    });
    setActiveSessionId(sessionId);

    const baseResult: PipelineResult = {
      id: null,
      pipeline_id: effectivePipelineId,
      session_id: sessionId,
      created_at: null,
      query,
      query_variants: null,
      translated_query: null,
      chunks: [],
      answer: '',
      latency: {},
    };

    setIsStreaming(true);
    try {
      await api.queryPipelineStream(effectivePipelineId, query, sessionId, {
        onMetadata: (meta) => {
          updateLastAssistant(sessionId, (m) => ({
            ...m,
            result: {
              ...(m.result ?? baseResult),
              chunks: meta.chunks,
              query_variants: meta.query_variants,
              translated_query: meta.query_translation,
            },
          }));
        },
        onToken: (text) => {
          updateLastAssistant(sessionId, (m) => ({ ...m, text: m.text + text }));
        },
        onDone: (done) => {
          updateLastAssistant(sessionId, (m) => ({
            ...m,
            result: {
              ...(m.result ?? baseResult),
              id: done.result_id,
              answer: m.text,
              latency: done.latency,
            },
          }));
          queryClient.invalidateQueries({ queryKey: ['pipeline-results', effectivePipelineId] });
        },
        onError: (detail) => {
          flash(detail, 'var(--red)');
          updateLastAssistant(sessionId, (m) => (m.text ? m : { ...m, text: `⚠ ${detail}` }));
        },
      });
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Query failed';
      flash(msg, 'var(--red)');
      updateLastAssistant(sessionId, (m) => (m.text ? m : { ...m, text: `⚠ ${msg}` }));
    } finally {
      updateLastAssistant(sessionId, (m) => ({ ...m, streaming: false }));
      setIsStreaming(false);
    }
  }

  function markRevealed(index: number) {
    const active = activeSession;
    if (!active) return;
    setSessions((prev) =>
      prev.map((s) =>
        s.id !== active.id
          ? s
          : { ...s, messages: s.messages.map((m, i) => (i === index ? { ...m, revealed: true } : m)) },
      ),
    );
  }

  function toggleSources(index: number) {
    const active = allSessions.find((s) => s.id === activeSessionId);
    if (!active) return;
    setSessions((prev) => {
      const base = prev.some((s) => s.id === active.id) ? prev : [active, ...prev];
      return base.map((s) =>
        s.id !== active.id
          ? s
          : {
              ...s,
              messages: s.messages.map((m, i) => (i === index ? { ...m, showSources: !m.showSources } : m)),
            },
      );
    });
  }

  const chunkPanel = useMemo(
    () => (lastAssistant?.revealed === false ? [] : (lastAssistant?.result?.chunks ?? [])),
    [lastAssistant],
  );

  return (
    <div className={styles.wrap}>
      <aside className={styles.left}>
        <Select value={effectivePipelineId} onChange={(e) => setPipelineId(e.target.value)}>
          {(pipelines ?? []).map((p) => (
            <option key={p.id} value={p.id}>
              {p.name}
            </option>
          ))}
        </Select>
        {activePipeline && (
          <div className={styles.pipelineStatus}>
            <StatusPill status={activePipeline.status} />
          </div>
        )}
        <Button
          variant="secondary"
          className={styles.newChatBtn}
          onClick={() => setActiveSessionId(null)}
        >
          <IconPlus width={14} height={14} />
          New chat
        </Button>
        <div className={styles.sessionList}>
          {sessionsForPipeline.map((s) => (
            <button
              key={s.id}
              className={styles.sessionItem}
              data-active={s.id === activeSessionId}
              onClick={() => setActiveSessionId(s.id)}
            >
              <div className={styles.sessionTitle}>{s.title}</div>
              <div className={styles.sessionMeta}>
                {s.time ? `${timeAgo(s.time)} · ` : ''}{s.messages.length} msgs
              </div>
            </button>
          ))}
        </div>
      </aside>

      <div className={styles.center}>
        <div className={styles.thread}>
          {messages.length === 0 && (
            <div className={styles.muted}>Ask a question to start a conversation with this pipeline.</div>
          )}
          {messages.map((m, i) =>
            m.role === 'user' ? (
              <div key={i} className={styles.userBubble}>
                {m.text}
              </div>
            ) : (
              <AssistantBubble
                key={i}
                m={m}
                onToggleSources={() => toggleSources(i)}
                onRevealed={() => markRevealed(i)}
                onFeedback={() => flash('Feedback recorded')}
              />
            ),
          )}
        </div>
        <div className={styles.inputBar}>
          <textarea
            className={styles.textarea}
            value={input}
            placeholder="Ask a question…"
            rows={1}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') send();
            }}
          />
          <Button variant="primary" onClick={send} disabled={!input.trim() || isStreaming}>
            Send
          </Button>
          <span className={styles.hint}>⌘⏎ to send</span>
        </div>
      </div>

      <aside className={styles.right}>
        <div className={styles.rightTitle}>Retrieved chunks</div>
        {chunkPanel.length === 0 && <div className={styles.muted}>Run a query to see retrieved chunks.</div>}
        {chunkPanel.map((c, i) => (
          <ChunkCard key={i} chunk={c} />
        ))}
      </aside>
    </div>
  );
}

function AssistantBubble({
  m,
  onToggleSources,
  onRevealed,
  onFeedback,
}: {
  m: Message;
  onToggleSources: () => void;
  onRevealed: () => void;
  onFeedback: () => void;
}) {
  // Typewriter reveal: display a prefix of the full text and steadily catch up.
  // Messages loaded from history mount fully revealed; streaming ones start at 0.
  const [visible, setVisible] = useState(() => (m.streaming ? 0 : m.text.length));
  const caughtUp = visible >= m.text.length;

  useEffect(() => {
    if (caughtUp) return;
    const timer = setInterval(() => {
      // reveal faster the further behind we are, min one char per tick
      setVisible((v) => Math.min(m.text.length, v + Math.max(1, Math.ceil((m.text.length - v) / 30))));
    }, 16);
    return () => clearInterval(timer);
  }, [caughtUp, m.text]);

  useEffect(() => {
    if (caughtUp && !m.streaming && m.revealed === false) onRevealed();
  }, [caughtUp, m.streaming, m.revealed, onRevealed]);

  const displayText = m.text.slice(0, visible);
  const showMeta = m.result && m.revealed !== false;

  return (
    <div className={styles.assistantBubble}>
      {displayText === '' ? (
        <TypingIndicator />
      ) : (
        <div dangerouslySetInnerHTML={{ __html: renderMarkdownLite(displayText) }} />
      )}
      {showMeta && m.result && (
        <>
          <div className={styles.assistantMeta}>
            {m.result.latency.generation_ms != null && (
              <>
                Retrieved {m.result.latency.retrieval_ms ?? 0}ms · Generated{' '}
                {((m.result.latency.generation_ms ?? 0) / 1000).toFixed(1)}s
              </>
            )}
            {m.result.chunks.length > 0 && (
              <button className={styles.sourcesToggle} onClick={onToggleSources}>
                {m.showSources ? 'Hide sources' : 'View sources'}
              </button>
            )}
          </div>
          {m.result.translated_query && (
            <div className={styles.subPanel}>
              <div className={styles.subPanelLabel}>Translated query</div>
              {m.result.translated_query}
            </div>
          )}
          {m.result.query_variants && m.result.query_variants.length > 0 && (
            <div className={styles.subPanel}>
              <div className={styles.subPanelLabel}>Query variants</div>
              {m.result.query_variants.map((v) => (
                <div key={v}>{v}</div>
              ))}
            </div>
          )}
          {m.showSources && (
            <div className={styles.inlineChunks}>
              {m.result.chunks.map((c, ci) => (
                <ChunkCard key={ci} chunk={c} />
              ))}
            </div>
          )}
          <div className={styles.feedbackRow}>
            <button className={styles.feedbackBtn} onClick={onFeedback}>
              <IconThumbsUp width={14} height={14} />
            </button>
            <button className={styles.feedbackBtn} onClick={onFeedback}>
              <IconThumbsDown width={14} height={14} />
            </button>
          </div>
        </>
      )}
    </div>
  );
}

function ChunkCard({ chunk }: { chunk: ChunkTrace }) {
  return (
    <div className={styles.chunkCard}>
      <div className={styles.chunkSource}>
        {chunk.source}
        {chunk.by && <span className={styles.chunkBy}>retrieved by: {chunk.by}</span>}
      </div>
      <div className={styles.chunkText}>{chunk.content}</div>
      <ScoreBar label="Relevance" value={chunk.raw_score} displayValue={chunk.raw_score.toFixed(2)} color="linear-gradient(90deg,#065f46,#10B981)" />
      {chunk.rerank_score != null && (
        <ScoreBar label="Rerank" value={chunk.rerank_score} displayValue={chunk.rerank_score.toFixed(2)} color="linear-gradient(90deg,#4c1d95,#a855f7)" />
      )}
    </div>
  );
}
