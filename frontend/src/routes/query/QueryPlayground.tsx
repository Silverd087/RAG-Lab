import { useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Button } from '../../components/Button';
import { Select } from '../../components/Select';
import { StatusPill } from '../../components/StatusPill';
import { TypingIndicator } from '../../components/TypingIndicator';
import { ScoreBar } from '../../components/ScoreBar';
import { IconPlus, IconThumbsDown, IconThumbsUp } from '../../components/Icons';
import { api } from '../../lib/api';
import { renderMarkdownLite, timeAgo } from '../../lib/format';
import { useToast } from '../../components/Toast';
import type { ChunkTrace, PipelineResult } from '../../lib/types';
import styles from './QueryPlayground.module.css';

interface Message {
  role: 'user' | 'assistant';
  text: string;
  result?: PipelineResult;
  showSources?: boolean;
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

  const queryMutation = useMutation({
    mutationFn: ({ query, sessionId }: { query: string; sessionId: string }) =>
      api.queryPipeline(effectivePipelineId, query, sessionId),
    onError: (err) => flash(err instanceof Error ? err.message : 'Query failed', 'var(--red)'),
  });

  function send() {
    const query = input.trim();
    if (!query || !effectivePipelineId) return;
    setInput('');

    const existingSession = allSessions.find((s) => s.id === activeSessionId && s.pipelineId === effectivePipelineId);
    const sessionId = existingSession ? existingSession.id : crypto.randomUUID();
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
        s.id === sessionId ? { ...s, messages: [...s.messages, { role: 'user', text: query }], time: new Date().toISOString() } : s,
      );
    });
    setActiveSessionId(sessionId);

    queryMutation.mutate({ query, sessionId }, {
      onSuccess: (result) => {
        setSessions((prev) =>
          prev.map((s) =>
            s.id === sessionId
              ? { ...s, messages: [...s.messages, { role: 'assistant', text: result.answer, result }] }
              : s,
          ),
        );
        queryClient.invalidateQueries({ queryKey: ['pipeline-results', effectivePipelineId] });
      },
    });
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

  const chunkPanel = useMemo(() => lastAssistant?.result?.chunks ?? [], [lastAssistant]);

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
          {messages.map((m, i) => (
            <div key={i} className={m.role === 'user' ? styles.userBubble : styles.assistantBubble}>
              {m.role === 'user' ? (
                m.text
              ) : (
                <>
                  <div dangerouslySetInnerHTML={{ __html: renderMarkdownLite(m.text) }} />
                  {m.result && (
                    <>
                      <div className={styles.assistantMeta}>
                        Retrieved {m.result.latency.retrieval_ms ?? 0}ms · Generated{' '}
                        {((m.result.latency.generation_ms ?? 0) / 1000).toFixed(1)}s
                        {m.result.chunks.length > 0 && (
                          <button className={styles.sourcesToggle} onClick={() => toggleSources(i)}>
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
                        <button className={styles.feedbackBtn} onClick={() => flash('Feedback recorded')}>
                          <IconThumbsUp width={14} height={14} />
                        </button>
                        <button className={styles.feedbackBtn} onClick={() => flash('Feedback recorded')}>
                          <IconThumbsDown width={14} height={14} />
                        </button>
                      </div>
                    </>
                  )}
                </>
              )}
            </div>
          ))}
          {queryMutation.isPending && (
            <div className={styles.assistantBubble}>
              <TypingIndicator />
            </div>
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
          <Button variant="primary" onClick={send} disabled={!input.trim() || queryMutation.isPending}>
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
