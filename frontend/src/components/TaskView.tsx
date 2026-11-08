'use client';

import React, { useEffect, useRef, useState } from 'react';
import { Task, TaskEvent, TaskStatus } from '../types/iol';
import { DeclarativeUIRenderer } from './DeclarativeUIRenderer';
import ExperienceRenderer from './experience/ExperienceRenderer';
import ActionPanel from './experience/ActionPanel';

interface TaskViewProps {
  taskId: string;
  apiKey?: string;
  apiBaseUrl?: string;
  onClose?: () => void;
}

export const TaskView: React.FC<TaskViewProps> = ({
  taskId,
  apiKey = 'iol_demo_operator_key',
  apiBaseUrl = 'http://127.0.0.1:8000',
  onClose,
}) => {
  const [task, setTask] = useState<Task | null>(null);
  const [events, setEvents] = useState<TaskEvent[]>([]);
  const [activeTab, setActiveTab] = useState<'workspace' | 'ui' | 'events'>('workspace');
  const [isExperienceFullscreen, setIsExperienceFullscreen] = useState(false);
  const [isCancelling, setIsCancelling] = useState(false);
  const [connectionStatus, setConnectionStatus] = useState<'connecting' | 'connected' | 'disconnected'>('connecting');
  const [expandedEventId, setExpandedEventId] = useState<number | null>(null);
  const [accessDenied, setAccessDenied] = useState(false);

  const lastEventIdRef = useRef<number | null>(null);

  const getAuthHeaders = (): Record<string, string> => {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    };
    if (apiKey) {
      headers['X-API-Key'] = apiKey;
    }
    return headers;
  };

  // 1. Initial Task Fetch
  useEffect(() => {
    let isMounted = true;
    setAccessDenied(false);
    const fetchTask = async () => {
      try {
        const res = await fetch(`${apiBaseUrl}/api/tasks/${taskId}`, {
          headers: getAuthHeaders(),
        });
        if (res.ok && isMounted) {
          const data: Task = await res.json();
          if (!data.experience_plan && data.metadata?.experience_plan) {
            data.experience_plan = data.metadata.experience_plan;
          }
          if (!data.outcome_envelope && data.metadata?.outcome_envelope) {
            data.outcome_envelope = data.metadata.outcome_envelope;
          }
          if (!data.pending_action && data.metadata?.pending_action) {
            data.pending_action = data.metadata.pending_action;
          }
          setTask(data);
          setAccessDenied(false);
        } else if (res.status === 403 || res.status === 401) {
          if (isMounted) setAccessDenied(true);
          console.warn(`Access denied to task ${taskId} for key ${apiKey}`);
        }
      } catch (err) {
        console.error('Failed to fetch task:', err);
      }
    };
    fetchTask();
    return () => {
      isMounted = false;
    };
  }, [taskId, apiBaseUrl, apiKey]);

  // 2. Authenticated Fetch-Based SSE Stream with Last-Event-ID Replay
  useEffect(() => {
    let reconnectTimeout: any = null;
    let isCancelled = false;
    const abortController = new AbortController();

    const connectSSE = async () => {
      if (isCancelled) return;
      setConnectionStatus('connecting');

      const headers: Record<string, string> = {
        Accept: 'text/event-stream',
      };
      if (apiKey) {
        headers['X-API-Key'] = apiKey;
      }
      if (lastEventIdRef.current !== null) {
        headers['Last-Event-ID'] = lastEventIdRef.current.toString();
      }

      try {
        const res = await fetch(`${apiBaseUrl}/api/tasks/${taskId}/events`, {
          headers,
          signal: abortController.signal,
        });

        if (!res.ok) {
          if (res.status === 401 || res.status === 403) {
            setConnectionStatus('disconnected');
            return; // Terminate reconnection on auth failures
          }
          throw new Error(`SSE HTTP error ${res.status}`);
        }

        setConnectionStatus('connected');
        const reader = res.body?.getReader();
        if (!reader) throw new Error('Response body stream is unavailable');

        const decoder = new TextDecoder();
        let buffer = '';

        while (!isCancelled) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const blocks = buffer.split('\n\n');
          buffer = blocks.pop() || '';

          for (const block of blocks) {
            if (!block.trim() || block.startsWith(':')) continue;

            let eventId: number | null = null;
            let eventType = 'message';
            let dataStr = '';

            const lines = block.split('\n');
            for (const line of lines) {
              if (line.startsWith('id:')) {
                const parsedId = parseInt(line.slice(3).trim(), 10);
                if (!isNaN(parsedId)) eventId = parsedId;
              } else if (line.startsWith('event:')) {
                eventType = line.slice(6).trim();
              } else if (line.startsWith('data:')) {
                dataStr = line.slice(5).trim();
              }
            }

            if (eventId !== null) {
              lastEventIdRef.current = Math.max(lastEventIdRef.current || 0, eventId);
            }

            if (dataStr) {
              try {
                const parsed = JSON.parse(dataStr);
                setEvents((prev) => {
                  if (prev.some((item) => item.event_id === parsed.event_id)) return prev;
                  return [...prev, parsed];
                });

                if (eventType === 'EXPERIENCE_UPDATED' && parsed.data) {
                  setTask((prev) => (prev ? { ...prev, experience_plan: parsed.data } : prev));
                } else if (eventType === 'OUTCOME_UPDATED' && parsed.data) {
                  setTask((prev) => (prev ? { ...prev, outcome_envelope: parsed.data } : prev));
                } else if ((eventType === 'APPROVAL_REQUIRED' || eventType === 'ACTION_REQUESTED') && parsed.data) {
                  setTask((prev) => (prev ? { ...prev, status: 'PAUSED_FOR_APPROVAL' as TaskStatus, pending_action: parsed.data } : prev));
                } else if (eventType === 'ACTION_APPROVED') {
                  setTask((prev) => (prev ? { ...prev, status: 'RUNNING' as TaskStatus, pending_action: undefined } : prev));
                } else if (eventType === 'ACTION_REJECTED') {
                  setTask((prev) => (prev ? { ...prev, pending_action: undefined } : prev));
                } else if (eventType === 'UI_UPDATED' && parsed.data) {
                  setTask((prev) => (prev ? { ...prev, ui_state: parsed.data } : prev));
                } else if (eventType === 'TASK_COMPLETED') {
                  setTask((prev) => (prev ? { ...prev, status: 'COMPLETED' as TaskStatus } : prev));
                } else if (eventType === 'TASK_FAILED') {
                  setTask((prev) => (prev ? { ...prev, status: 'FAILED' as TaskStatus, error_message: parsed.data?.error } : prev));
                } else if (eventType === 'TASK_CANCELLED') {
                  setTask((prev) => (prev ? { ...prev, status: 'CANCELLED' as TaskStatus } : prev));
                } else if (eventType === 'STEP_COMPLETED' && parsed.data) {
                  setTask((prev) =>
                    prev
                      ? {
                          ...prev,
                          current_step: parsed.data.step_number || prev.current_step,
                          total_steps: parsed.data.total_steps || prev.total_steps,
                        }
                      : prev
                  );
                }
              } catch (e) {
                console.error('Failed to parse SSE payload:', e);
              }
            }
          }
        }
      } catch (err: any) {
        if (err.name === 'AbortError') return;
        setConnectionStatus('disconnected');
        if (!isCancelled) {
          reconnectTimeout = setTimeout(connectSSE, 2000);
        }
      }
    };

    connectSSE();

    return () => {
      isCancelled = true;
      abortController.abort();
      if (reconnectTimeout) clearTimeout(reconnectTimeout);
    };
  }, [taskId, apiBaseUrl, apiKey]);

  // 3. Task Cancellation Trigger
  const handleCancel = async () => {
    if (!task || task.status === 'COMPLETED' || task.status === 'CANCELLED' || isCancelling) return;
    setIsCancelling(true);
    try {
      const res = await fetch(`${apiBaseUrl}/api/tasks/${taskId}/cancel`, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify({ reason: 'Operator requested cancellation via dashboard' }),
      });
      if (res.ok) {
        setTask((prev) => (prev ? { ...prev, status: 'CANCELLED' as TaskStatus } : prev));
      }
    } catch (err) {
      console.error('Failed to cancel task:', err);
    } finally {
      setIsCancelling(false);
    }
  };

  if (accessDenied) {
    return (
      <div className="rounded-2xl border border-red-500/40 bg-red-950/20 p-8 text-center text-sm space-y-3">
        <span className="text-3xl block">🔒</span>
        <h3 className="font-semibold text-red-300 text-base">Access Restricted (403 Forbidden)</h3>
        <p className="text-xs text-slate-400 max-w-md mx-auto leading-relaxed">
          Task <code className="text-slate-300 font-mono">{taskId}</code> is protected by tenant authorization boundaries. The active session key does not have permission to inspect this task.
        </p>
        {onClose && (
          <button
            onClick={onClose}
            className="rounded-lg border border-slate-700 bg-slate-800 px-3.5 py-1.5 text-xs text-slate-300 hover:bg-slate-700 transition-colors"
          >
            Dismiss
          </button>
        )}
      </div>
    );
  }

  if (!task) {
    return (
      <div className="flex h-64 items-center justify-center rounded-2xl border border-slate-800 bg-slate-900/60 p-8 shadow-inner">
        <div className="flex items-center space-x-3 text-slate-400">
          <span className="h-5 w-5 animate-spin rounded-full border-2 border-blue-500 border-t-transparent" />
          <span className="text-sm font-medium">Retrieving persistent task state from store...</span>
        </div>
      </div>
    );
  }

  const isTerminal = ['COMPLETED', 'FAILED', 'CANCELLED'].includes(task.status);

  const statusBadge = {
    PENDING: 'bg-slate-800 text-slate-300 border-slate-700',
    RUNNING: 'bg-blue-500/20 text-blue-300 border-blue-500/40 animate-pulse',
    COMPLETED: 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40',
    FAILED: 'bg-red-500/20 text-red-300 border-red-500/40',
    CANCELLED: 'bg-amber-500/20 text-amber-300 border-amber-500/40',
    PAUSED_FOR_APPROVAL: 'bg-purple-500/20 text-purple-300 border-purple-500/40',
  }[task.status];

  // Extract dynamic execution mode from declarative metric card
  const executionMode: string | null = (() => {
    if (!task?.ui_state?.components) return null;
    for (const comp of task.ui_state.components) {
      if (comp.id === 'metric_summary' && 'metrics' in comp) {
        const m = (comp as any).metrics?.find((item: any) => item.label === 'Execution Mode');
        if (m && m.value && m.value !== 'INITIALIZING') {
          return String(m.value);
        }
      }
    }
    return null;
  })();

  // 4. Export Verified Results (JSON / CSV)
  const tableComponent = task?.ui_state?.components.find((c) => c.type === 'table') as any;
  const hasExportableResults = !!(tableComponent && tableComponent.rows && tableComponent.rows.length > 0);

  const handleExportJSON = () => {
    if (!hasExportableResults) return;
    const blob = new Blob([JSON.stringify(tableComponent.rows, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `iol_verified_results_${taskId}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleExportCSV = () => {
    if (!hasExportableResults || !tableComponent.columns) return;
    const cols = tableComponent.columns;
    const headers = cols.map((c: any) => `"${c.header.replace(/"/g, '""')}"`).join(',');
    const rows = tableComponent.rows.map((row: any) => {
      return cols
        .map((c: any) => {
          const val = row[c.key];
          const str = val !== null && val !== undefined ? String(val) : '';
          return `"${str.replace(/"/g, '""')}"`;
        })
        .join(',');
    });
    const csvContent = [headers, ...rows].join('\n');
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `iol_verified_results_${taskId}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleExportReplayBundle = async () => {
    try {
      const res = await fetch(`${apiBaseUrl}/api/tasks/${taskId}/replay-bundle`, {
        headers: getAuthHeaders(),
      });
      if (!res.ok) throw new Error('Failed to download replay bundle');
      const data = await res.json();
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `iol_replay_bundle_${taskId}.json`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      console.error('Failed to export replay bundle:', err);
    }
  };

  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-900/90 shadow-2xl backdrop-blur-xl overflow-hidden transition-all duration-200">
      {/* Task Header */}
      <div className="border-b border-slate-800 p-6">
        <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4">
          <div className="space-y-1.5 flex-1 min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <span className="font-mono text-xs text-slate-500 font-semibold">{task.task_id}</span>
              <span className={`inline-flex rounded-full border px-2.5 py-0.5 text-xs font-semibold ${statusBadge}`}>
                {task.status}
              </span>
              {executionMode && (
                <span
                  data-testid="execution-mode-badge"
                  className={`rounded px-2 py-0.5 text-[11px] font-semibold border ${
                    executionMode.includes('LIVE')
                      ? 'bg-emerald-950/60 text-emerald-300 border-emerald-500/40'
                      : executionMode.includes('FALLBACK')
                      ? 'bg-amber-950/60 text-amber-300 border-amber-500/40'
                      : 'bg-purple-950/60 text-purple-300 border-purple-500/40'
                  }`}
                >
                  {executionMode.includes('LIVE') ? '⚡ ' : executionMode.includes('FALLBACK') ? '⚠️ ' : '📼 '}
                  {executionMode}
                </span>
              )}
              <span
                className={`inline-flex items-center space-x-1.5 text-[11px] font-mono ${
                  connectionStatus === 'connected' ? 'text-emerald-400' : 'text-slate-500'
                }`}
              >
                <span
                  className={`h-2 w-2 rounded-full ${
                    connectionStatus === 'connected' ? 'bg-emerald-400 animate-pulse' : 'bg-slate-500'
                  }`}
                />
                <span>SSE {connectionStatus}</span>
              </span>
              {task.user_id && (
                <span className="rounded bg-slate-800 border border-slate-700/80 px-2 py-0.5 text-[10px] text-slate-400 font-mono">
                  Owner: {task.user_id}
                </span>
              )}
            </div>
            <h2 className="text-lg font-bold text-slate-100 break-words leading-snug">{task.intent}</h2>
          </div>

          <div className="flex items-center space-x-2 shrink-0">
            {!isTerminal && (
              <button
                onClick={handleCancel}
                disabled={isCancelling}
                data-testid="cancel-task-button"
                className="rounded-lg border border-red-500/30 bg-red-950/40 px-3.5 py-1.5 text-xs font-semibold text-red-300 hover:bg-red-900/50 hover:border-red-500/60 transition-colors disabled:opacity-50"
              >
                {isCancelling ? 'Halting Execution...' : 'Cancel Task'}
              </button>
            )}
            {onClose && (
              <button
                onClick={onClose}
                className="rounded-lg border border-slate-800 p-1.5 text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition-colors"
                title="Close task view"
              >
                ✕
              </button>
            )}
          </div>
        </div>

        {/* Execution Budget & Step Progress */}
        <div className="mt-4 flex flex-wrap items-center justify-between gap-4 text-xs text-slate-400 border-t border-slate-800/60 pt-3">
          <div className="flex flex-wrap items-center gap-4">
            <div>
              Step:{' '}
              <span className="font-semibold text-slate-200">
                {task.current_step} / {task.total_steps || '—'}
              </span>
            </div>
            <div>
              Max Duration: <span className="text-slate-200">{task.budget.max_duration_seconds}s</span>
            </div>
            <div>
              Budget: <span className="text-slate-200">${task.budget.max_cost_usd.toFixed(2)}</span>
            </div>
            <div>
              Durable Events: <span className="font-mono text-blue-400 font-semibold">{events.length}</span>
            </div>
          </div>

          {/* Export Verified Results & Replay Bundle */}
          <div className="flex items-center space-x-2">
            {hasExportableResults && (
              <>
                <span className="text-[11px] text-slate-500 font-medium">Export Verified:</span>
                <button
                  onClick={handleExportJSON}
                  data-testid="export-json-button"
                  className="rounded bg-slate-800 hover:bg-slate-700 px-2.5 py-1 text-[11px] font-medium text-slate-200 border border-slate-700 transition-colors shadow-sm"
                  title="Download verified records with field-level evidence metadata in JSON"
                >
                  JSON
                </button>
                <button
                  onClick={handleExportCSV}
                  data-testid="export-csv-button"
                  className="rounded bg-slate-800 hover:bg-slate-700 px-2.5 py-1 text-[11px] font-medium text-slate-200 border border-slate-700 transition-colors shadow-sm"
                  title="Download verified records table in CSV"
                >
                  CSV
                </button>
              </>
            )}
            {events.length > 0 && (
              <button
                onClick={handleExportReplayBundle}
                data-testid="export-replay-bundle-btn"
                className="rounded bg-purple-950/80 hover:bg-purple-900/80 px-2.5 py-1 text-[11px] font-semibold text-purple-200 border border-purple-800/80 transition-colors shadow-sm flex items-center gap-1"
                title="Download offline replay bundle with verified evidence, sanitized credentials, and cryptographic integrity proof"
              >
                <span>📦 Replay Bundle</span>
              </button>
            )}
          </div>
        </div>

        {/* Dynamic Execution Progress Bar: Indeterminate while Running, Real steps otherwise */}
        <div className="mt-3">
          <div className="h-1.5 w-full bg-slate-800 rounded-full overflow-hidden relative">
            {task.status === 'RUNNING' ? (
              <div className="h-full bg-gradient-to-r from-blue-500 via-indigo-400 to-blue-500 w-1/3 rounded-full animate-pulse transition-all duration-300" />
            ) : (
              <div
                className={`h-full transition-all duration-500 ${
                  task.status === 'COMPLETED'
                    ? 'bg-emerald-500'
                    : task.status === 'FAILED'
                    ? 'bg-red-500'
                    : task.status === 'CANCELLED'
                    ? 'bg-amber-500'
                    : 'bg-blue-500'
                }`}
                style={{
                  width: `${
                    task.status === 'COMPLETED'
                      ? 100
                      : task.total_steps > 0
                      ? Math.min(100, Math.round((task.current_step / task.total_steps) * 100))
                      : 10
                  }%`,
                }}
              />
            )}
          </div>
        </div>

        {/* Error Banner */}
        {task.status === 'FAILED' && (
          <div className="mt-4 rounded-xl border border-red-500/30 bg-red-950/30 p-4 text-xs text-red-300">
            <span className="font-semibold text-red-200">Execution Error: </span>
            {task.error_message || 'Task halted due to execution failure.'}
          </div>
        )}

        {/* Cancelled Banner */}
        {task.status === 'CANCELLED' && (
          <div className="mt-4 rounded-xl border border-amber-500/30 bg-amber-950/30 p-4 text-xs text-amber-300">
            <span className="font-semibold text-amber-200">Execution Terminated: </span>
            Task was halted by operator cancellation request. All completed partial steps and evidence remain preserved.
          </div>
        )}

        {/* Scoped Action Approval Banner */}
        {(task.status === 'PAUSED_FOR_APPROVAL' || task.pending_action) && (
          <div className="mt-4" data-testid="task-pending-approval-wrapper">
            <ActionPanel
              taskId={task.task_id}
              actionRequest={task.pending_action}
              apiKey={apiKey}
              apiBaseUrl={apiBaseUrl}
              onActionHandled={(decision) => {
                if (decision === 'APPROVED') {
                  setTask((prev) => (prev ? { ...prev, status: 'RUNNING' as TaskStatus, pending_action: undefined } : prev));
                } else {
                  setTask((prev) => (prev ? { ...prev, pending_action: undefined } : prev));
                }
              }}
            />
          </div>
        )}
      </div>

      {/* Tabs */}
      <div className="flex border-b border-slate-800 bg-slate-950/40 px-6">
        <button
          onClick={() => setActiveTab('workspace')}
          data-testid="tab-workspace"
          className={`border-b-2 py-3 px-4 text-xs font-semibold transition-colors flex items-center space-x-1.5 ${
            activeTab === 'workspace'
              ? 'border-cyan-500 text-cyan-400 font-bold'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          <span>⛶ Adaptive Workspace</span>
          <span className="rounded bg-cyan-950/80 border border-cyan-800/80 px-1.5 py-0.2 text-[9px] text-cyan-300 font-mono">
            v0.6
          </span>
        </button>
        <button
          onClick={() => setActiveTab('ui')}
          data-testid="tab-outcomes"
          className={`border-b-2 py-3 px-4 text-xs font-semibold transition-colors ${
            activeTab === 'ui'
              ? 'border-blue-500 text-blue-400 font-bold'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          Declarative UI & Outcomes
        </button>
        <button
          onClick={() => setActiveTab('events')}
          data-testid="tab-event-log"
          className={`border-b-2 py-3 px-4 text-xs font-semibold transition-colors flex items-center space-x-1.5 ${
            activeTab === 'events'
              ? 'border-blue-500 text-blue-400 font-bold'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          <span>SSE Event Stream Log</span>
          <span className="rounded-full bg-slate-800 px-1.5 py-0.2 text-[10px] text-slate-300 font-mono">
            {events.length}
          </span>
        </button>
      </div>

      {/* Tab Content */}
      <div className="p-6">
        {activeTab === 'workspace' ? (
          task.experience_plan ? (
            <ExperienceRenderer
              plan={task.experience_plan}
              isFullscreen={isExperienceFullscreen}
              onToggleFullscreen={() => setIsExperienceFullscreen(!isExperienceFullscreen)}
              executionMode={executionMode}
              taskStatus={task.status}
              apiKey={apiKey}
              apiBaseUrl={apiBaseUrl}
              onActionHandled={(decision) => {
                if (decision === 'APPROVED') {
                  setTask((prev) => (prev ? { ...prev, status: 'RUNNING' as TaskStatus, pending_action: undefined } : prev));
                } else {
                  setTask((prev) => (prev ? { ...prev, pending_action: undefined } : prev));
                }
              }}
            />
          ) : (
            <div className="text-center py-12 text-slate-400 text-xs">
              Initializing Adaptive Workspace experience plan...
            </div>
          )
        ) : activeTab === 'ui' ? (
          <DeclarativeUIRenderer uiRoot={task.ui_state} />
        ) : (
          <div className="space-y-3">
            <div className="flex items-center justify-between text-xs text-slate-400 pb-2 border-b border-slate-800">
              <span>Sequential Event Replay Stream (Last-Event-ID Supported)</span>
              <span className="font-mono">Total Recorded: {events.length}</span>
            </div>
            <div className="max-h-[500px] overflow-y-auto space-y-2 pr-1 font-mono text-xs">
              {events.length === 0 ? (
                <div className="text-slate-500 text-center py-8">No events captured in stream yet.</div>
              ) : (
                events.map((ev) => {
                  const isExpanded = expandedEventId === ev.event_id;
                  return (
                    <div
                      key={ev.event_id}
                      className="rounded-lg bg-slate-950/70 border border-slate-800/80 p-3 hover:border-slate-700 transition-colors"
                    >
                      <div
                        className="flex items-center justify-between cursor-pointer select-none"
                        onClick={() => setExpandedEventId(isExpanded ? null : ev.event_id)}
                      >
                        <div className="flex items-center space-x-2.5">
                          <span className="rounded bg-blue-950/80 border border-blue-800/50 px-1.5 py-0.5 text-blue-400 font-bold text-[10px]">
                            #{ev.event_id}
                          </span>
                          <span className="font-semibold text-slate-200">{ev.event_type}</span>
                        </div>
                        <div className="flex items-center space-x-3 text-[11px] text-slate-500">
                          <span>{new Date(ev.timestamp).toLocaleTimeString()}</span>
                          <span className="text-slate-400 text-xs">{isExpanded ? '▲' : '▼'}</span>
                        </div>
                      </div>

                      {/* Expandable JSON payload details */}
                      {isExpanded ? (
                        <pre className="mt-3 p-3 rounded bg-slate-900/90 text-slate-300 text-[11px] overflow-x-auto border border-slate-800/60 leading-relaxed">
                          {JSON.stringify(ev.data, null, 2)}
                        </pre>
                      ) : (
                        <p className="mt-1 text-[11px] text-slate-400 truncate">
                          {JSON.stringify(ev.data)}
                        </p>
                      )}
                    </div>
                  );
                })
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
