'use client';

import React, { useEffect, useState, useRef } from 'react';
import { IntentInput } from '../components/IntentInput';
import { TaskView } from '../components/TaskView';
import { ModelSettingsModal } from '../components/ModelSettingsModal';
import { CapabilityMetadata, Task } from '../types/iol';

const PRESET_ACCOUNTS = [
  { label: 'Demo Operator', key: 'iol_demo_operator_key', role: 'Operator' },
  { label: 'Tenant Alpha', key: 'iol_key_user_alpha', role: 'Tenant A' },
  { label: 'Tenant Beta', key: 'iol_key_user_beta', role: 'Tenant B' },
  { label: 'Enterprise 42', key: 'iol_key_tenant_enterprise_42', role: 'Enterprise' },
  { label: 'Administrator', key: 'iol_admin_secret_key_prod_2026', role: 'Admin' },
];

const DEMO_PRESETS = [
  {
    title: 'Demo A: Academic Research',
    desc: 'Top 5 AI faculty in robotics & control theory with official affiliation URLs',
    intent: 'Find 5 university professors researching robotics and autonomous systems with verified affiliations, citations, and homepage URLs.',
  },
  {
    title: 'Demo B: Indian AI Startups',
    desc: '5 Indian AI startups founded since 2021 with headquarters, funding & product category',
    intent: 'Discover 5 active AI startups headquartered in India founded in 2021 or later with product categories and evidence.',
  },
  {
    title: 'Demo C: Evaluation Tools Comparison',
    desc: '5 open-source LLM evaluation frameworks with GitHub stars, licenses & comparative metrics',
    intent: 'Find 5 open-source AI evaluation and developer frameworks with licenses, primary language, and feature comparison matrix.',
  },
];

export default function Home() {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [activeTaskId, setActiveTaskId] = useState<string | null>(null);
  const [capabilities, setCapabilities] = useState<CapabilityMetadata[]>([]);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [backendOnline, setBackendOnline] = useState(true);
  const [selectedApiKey, setSelectedApiKey] = useState('iol_demo_operator_key');
  const [customKey, setCustomKey] = useState('');
  const [showCustomKeyInput, setShowCustomKeyInput] = useState(false);
  const [showModelSettings, setShowModelSettings] = useState(false);

  const activeTaskIdRef = useRef<string | null>(null);
  activeTaskIdRef.current = activeTaskId;

  const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000';
  const effectiveApiKey = showCustomKeyInput && customKey.trim() ? customKey.trim() : selectedApiKey;

  const getHeaders = () => ({
    'Content-Type': 'application/json',
    'X-API-Key': effectiveApiKey,
  });

  // Check URL params on initial load
  useEffect(() => {
    if (typeof window !== 'undefined') {
      const urlParams = new URLSearchParams(window.location.search);
      const qTaskId = urlParams.get('task_id');
      if (qTaskId) {
        setActiveTaskId(qTaskId);
      }
    }
  }, []);

  const handleSelectTask = (taskId: string | null) => {
    setActiveTaskId(taskId);
    if (typeof window !== 'undefined') {
      const url = new URL(window.location.href);
      if (taskId) {
        url.searchParams.set('task_id', taskId);
      } else {
        url.searchParams.delete('task_id');
      }
      window.history.replaceState({}, '', url.toString());
    }
  };

  // 1. Fetch initial tasks and capabilities scoped to authenticated user
  const refreshData = async () => {
    // 1. Health check
    try {
      const healthRes = await fetch(`${API_URL}/api/health`);
      if (healthRes.ok) {
        setBackendOnline(true);
      } else {
        setBackendOnline(false);
      }
    } catch (_) {
      setBackendOnline(false);
    }

    // 2. Fetch tasks scoped by X-API-Key
    try {
      const tasksRes = await fetch(`${API_URL}/api/tasks?limit=100`, {
        headers: getHeaders(),
      });
      if (tasksRes.ok) {
        let data: Task[] = await tasksRes.json();
        const urlParams = typeof window !== 'undefined' ? new URLSearchParams(window.location.search) : null;
        const qTaskId = urlParams?.get('task_id');
        if (qTaskId && !data.some((t) => t.task_id === qTaskId)) {
          try {
            const singleRes = await fetch(`${API_URL}/api/tasks/${qTaskId}`, { headers: getHeaders() });
            if (singleRes.ok) {
              const singleTask: Task = await singleRes.json();
              data = [singleTask, ...data];
            }
          } catch (_) {}
        }
        setTasks(data);
        if (data.length > 0 && !activeTaskIdRef.current) {
          if (qTaskId && data.some((t) => t.task_id === qTaskId)) {
            setActiveTaskId(qTaskId);
          } else if (!qTaskId) {
            handleSelectTask(data[0].task_id);
          }
        } else if (data.length === 0) {
          setActiveTaskId(null);
        }
      }
    } catch (err) {
      console.error('Failed to fetch tasks:', err);
    }

    // 3. Fetch capabilities
    try {
      const capsRes = await fetch(`${API_URL}/api/capabilities`);
      if (capsRes.ok) {
        const capsData = await capsRes.json();
        setCapabilities(capsData);
      }
    } catch (err) {
      console.error('Failed to fetch capabilities:', err);
    }
  };

  useEffect(() => {
    refreshData();
    const interval = setInterval(refreshData, 3000);
    return () => clearInterval(interval);
  }, [effectiveApiKey]);

  // 2. Submit New Intent
  const handleIntentSubmit = async (intent: string) => {
    setIsSubmitting(true);
    try {
      const res = await fetch(`${API_URL}/api/tasks`, {
        method: 'POST',
        headers: getHeaders(),
        body: JSON.stringify({
          intent,
          budget: {
            max_duration_seconds: 300,
            max_steps: 15,
            max_cost_usd: 1.0,
          },
          metadata: {
            submitted_via: 'web_dashboard',
          },
        }),
      });
      if (res.ok) {
        const newTask: Task = await res.json();
        setTasks((prev) => [newTask, ...prev]);
        handleSelectTask(newTask.task_id);
      } else {
        const err = await res.json();
        alert(`Task creation failed: ${err.detail || 'Unauthorized or invalid request'}`);
      }
    } catch (err) {
      console.error('Failed to submit intent:', err);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans selection:bg-blue-600 selection:text-white">
      {/* Top Navigation Bar */}
      <header className="border-b border-slate-800/80 bg-slate-900/70 backdrop-blur-md sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between gap-4">
          <div className="flex items-center space-x-3 shrink-0">
            <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-tr from-blue-600 to-indigo-500 shadow-md shadow-blue-500/20">
              <span className="font-extrabold text-white text-base tracking-tighter">IO</span>
            </div>
            <div>
              <h1 className="text-sm font-bold tracking-tight text-white flex items-center space-x-2">
                <span>Intent Operating Layer</span>
                <span className="rounded bg-blue-500/10 px-1.5 py-0.5 text-[10px] text-blue-400 font-mono border border-blue-500/20">
                  MVP v0.5.0
                </span>
              </h1>
              <p className="text-[11px] text-slate-400 hidden sm:block">General-Purpose Autonomous Execution Platform</p>
            </div>
          </div>

          <div className="flex items-center space-x-3 text-xs">
            {/* Health Indicator */}
            <div className="flex items-center space-x-2 bg-slate-900 px-2.5 py-1 rounded-full border border-slate-800">
              <span className={`h-2 w-2 rounded-full ${backendOnline ? 'bg-emerald-400 animate-pulse' : 'bg-red-500'}`} />
              <span className="text-slate-400 font-mono text-[11px]">
                {backendOnline ? 'Core Online' : 'Core Offline'}
              </span>
            </div>

            {/* Authenticated Tenant / Operator Selector */}
            <div className="flex items-center space-x-1.5 bg-slate-900/90 border border-slate-800 rounded-lg p-1">
              <span className="text-[10px] uppercase font-bold text-slate-500 px-1">Session:</span>
              <select
                aria-label="Active Authenticated Session"
                value={showCustomKeyInput ? 'custom' : selectedApiKey}
                onChange={(e) => {
                  if (e.target.value === 'custom') {
                    setShowCustomKeyInput(true);
                  } else {
                    setShowCustomKeyInput(false);
                    setSelectedApiKey(e.target.value);
                  }
                }}
                className="bg-slate-950 border border-slate-700/80 rounded px-2 py-0.5 text-xs text-slate-200 font-medium focus:outline-none focus:border-blue-500"
              >
                {PRESET_ACCOUNTS.map((acc) => (
                  <option key={acc.key} value={acc.key}>
                    {acc.label} ({acc.role})
                  </option>
                ))}
                <option value="custom">Custom API Key...</option>
              </select>
            </div>

            {showCustomKeyInput && (
              <input
                type="password"
                placeholder="Enter X-API-Key"
                value={customKey}
                onChange={(e) => setCustomKey(e.target.value)}
                className="bg-slate-900 border border-slate-700 rounded px-2 py-1 text-xs text-slate-200 font-mono w-32 focus:outline-none focus:border-blue-500"
              />
            )}

            <div className="hidden lg:flex items-center rounded-full bg-slate-900 border border-slate-800 px-3 py-1 text-xs text-slate-300">
              <span className="font-semibold text-blue-400 mr-1">{capabilities.length}</span> Capabilities
            </div>

            <button
              onClick={() => setShowModelSettings(true)}
              className="flex items-center space-x-1.5 px-3 py-1.5 bg-slate-900 hover:bg-slate-800 border border-slate-800 hover:border-slate-700 rounded-lg text-xs text-slate-200 transition"
              title="Configure foundation model runtimes, local Ollama models, and functional routing"
            >
              <svg className="w-3.5 h-3.5 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
              </svg>
              <span>Model Runtimes</span>
            </button>
          </div>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 flex-1 w-full space-y-8">
        {/* Intent Hero Bar */}
        <section className="space-y-4">
          <div className="text-center max-w-3xl mx-auto space-y-2 mb-2">
            <h2 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">
              State Any Objective. Observe Real Execution.
            </h2>
            <p className="text-sm text-slate-400">
              IOL dynamically synthesizes verified web, academic, and code intelligence into durable structured outcomes.
            </p>
          </div>

          <IntentInput onSubmit={handleIntentSubmit} isLoading={isSubmitting} />

          {/* Quick Conclave Demonstration Presets */}
          <div className="flex flex-wrap items-center justify-center gap-2 pt-1">
            <span className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider mr-1">
              Conclave Demos:
            </span>
            {DEMO_PRESETS.map((preset, idx) => (
              <button
                key={idx}
                onClick={() => handleIntentSubmit(preset.intent)}
                disabled={isSubmitting}
                className="text-xs rounded-lg border border-slate-800 bg-slate-900/60 hover:bg-slate-850 hover:border-slate-700 px-3 py-1.5 text-slate-300 transition-all hover:text-white flex items-center space-x-1.5 shadow-sm disabled:opacity-50"
                title={preset.desc}
              >
                <span className="font-semibold text-blue-400">{preset.title.split(':')[0]}</span>
                <span className="text-slate-500">|</span>
                <span className="text-slate-300 truncate max-w-[200px]">{preset.title.split(':')[1]}</span>
              </button>
            ))}
          </div>
        </section>

        {/* Dashboard Grid: Tasks List & Active Task View */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
          {/* Left Column: Persistent Task Queue */}
          <div className="lg:col-span-4 space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-400 flex items-center space-x-1.5">
                <span>Task Store</span>
                <span className="rounded bg-slate-800 px-1.5 py-0.2 text-[10px] text-slate-400 font-mono">
                  {tasks.length}
                </span>
              </h3>
              <button
                onClick={refreshData}
                className="text-[11px] text-blue-400 hover:text-blue-300 font-medium"
              >
                Refresh
              </button>
            </div>

            <div className="space-y-2.5 max-h-[650px] overflow-y-auto pr-1">
              {tasks.length === 0 ? (
                <div className="rounded-xl border border-slate-800/80 bg-slate-900/40 p-6 text-center text-xs text-slate-500">
                  No active tasks found for session <code className="text-slate-400">{effectiveApiKey}</code>.
                  State an intent above to dispatch work.
                </div>
              ) : (
                tasks.map((t) => {
                  const isSelected = t.task_id === activeTaskId;
                  const statusColor = {
                    PENDING: 'border-slate-700 bg-slate-800/40 text-slate-400',
                    RUNNING: 'border-blue-500/40 bg-blue-950/20 text-blue-400 animate-pulse',
                    COMPLETED: 'border-emerald-500/40 bg-emerald-950/20 text-emerald-400',
                    FAILED: 'border-red-500/40 bg-red-950/20 text-red-400',
                    CANCELLED: 'border-amber-500/40 bg-amber-950/20 text-amber-400',
                    PAUSED_FOR_APPROVAL: 'border-purple-500/40 bg-purple-950/20 text-purple-400',
                  }[t.status];

                  return (
                    <button
                      key={t.task_id}
                      onClick={() => handleSelectTask(t.task_id)}
                      data-testid={`task-item-${t.task_id}`}
                      className={`w-full text-left rounded-xl border p-4 transition-all duration-150 ${
                        isSelected
                          ? 'border-blue-500 bg-slate-900/90 shadow-lg shadow-blue-500/5'
                          : 'border-slate-800/80 bg-slate-900/40 hover:border-slate-700 hover:bg-slate-900/60'
                      }`}
                    >
                      <div className="flex items-center justify-between mb-1.5">
                        <span className="font-mono text-[10px] text-slate-500">{t.task_id}</span>
                        <span className={`rounded-full border px-2 py-0.2 text-[10px] font-semibold ${statusColor}`}>
                          {t.status}
                        </span>
                      </div>
                      <p className="text-xs font-medium text-slate-200 line-clamp-2 leading-relaxed">
                        {t.intent}
                      </p>
                      <div className="mt-2.5 flex items-center justify-between text-[11px] text-slate-500 pt-2 border-t border-slate-800/40 font-mono">
                        <span>
                          Step {t.current_step} / {t.total_steps || '—'}
                        </span>
                        <span>{new Date(t.created_at).toLocaleTimeString()}</span>
                      </div>
                    </button>
                  );
                })
              )}
            </div>
          </div>

          {/* Right Column: Active Task View */}
          <div className="lg:col-span-8">
            {activeTaskId ? (
              <TaskView
                taskId={activeTaskId}
                apiKey={effectiveApiKey}
                apiBaseUrl={API_URL}
                onClose={() => handleSelectTask(null)}
              />
            ) : (
              <div className="flex flex-col items-center justify-center rounded-2xl border border-dashed border-slate-800 bg-slate-900/20 p-12 text-center text-sm text-slate-500 space-y-3">
                <span className="text-3xl">🎯</span>
                <p className="font-medium text-slate-400">Select a task or submit a new intent to view live execution.</p>
                <p className="text-xs text-slate-600 max-w-sm">
                  Tasks persist across page reloads and tab closures. All outcomes and provenance are stored durably.
                </p>
              </div>
            )}
          </div>
        </div>

        {/* Reusable Capability Contract Tray */}
        <section className="pt-4 border-t border-slate-800/80">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-sm font-semibold text-slate-200">Registered Capabilities</h3>
              <p className="text-xs text-slate-400">
                Composable, typed capability contracts registered in the IOL registry and executed by the planner.
              </p>
            </div>
            <span className="text-xs text-slate-500 font-mono">{capabilities.length} active</span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {capabilities.map((c) => (
              <div
                key={c.capability_id}
                className="rounded-xl border border-slate-800/80 bg-slate-900/40 p-4 hover:border-slate-700 transition-colors"
              >
                <div className="flex items-start justify-between">
                  <span className="font-mono text-xs font-semibold text-blue-400">{c.capability_id}</span>
                  <span className="text-[10px] font-mono text-slate-500">v{c.version}</span>
                </div>
                <h4 className="mt-1 text-xs font-bold text-slate-200">{c.name}</h4>
                <p className="mt-1 text-[11px] text-slate-400 line-clamp-2 leading-relaxed">{c.description}</p>
                <div className="mt-3 flex items-center justify-between text-[10px] text-slate-500 pt-2 border-t border-slate-800/60 font-mono">
                  <span>Perms: {c.required_permissions.length > 0 ? c.required_permissions.join(', ') : 'None'}</span>
                  <span className="text-emerald-400/90 font-medium">Verified Contract</span>
                </div>
              </div>
            ))}
          </div>
        </section>
      </main>

      {/* Footer */}
      <footer className="border-t border-slate-800/80 py-6 text-center text-xs text-slate-500">
        Intent Operating Layer (IOL) — Principle: Primary: Complete work. Secondary: Learn reusable capabilities.
      </footer>

      {/* Model Providers and Intelligent Routing Modal */}
      <ModelSettingsModal
        isOpen={showModelSettings}
        onClose={() => setShowModelSettings(false)}
        apiUrl={API_URL}
        headers={getHeaders()}
      />
    </div>
  );
}
