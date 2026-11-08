'use client';

import React from 'react';
import { ExperiencePlan, MetricItem } from '../../types/experience';
import InteractiveCanvas2D from './InteractiveCanvas2D';
import WorkspaceDataGrid from './WorkspaceDataGrid';
import FormDraft from './FormDraft';
import ActionPanel from './ActionPanel';
import BrowserTelemetryCard from './BrowserTelemetryCard';

interface ExperienceRendererProps {
  plan: ExperiencePlan;
  isFullscreen?: boolean;
  onToggleFullscreen?: () => void;
  executionMode?: string | null;
  taskStatus?: string;
  apiKey?: string;
  apiBaseUrl?: string;
  onActionHandled?: (decision: 'APPROVED' | 'REJECTED') => void;
}

export default function ExperienceRenderer({
  plan,
  isFullscreen = false,
  onToggleFullscreen,
  executionMode,
  taskStatus,
  apiKey,
  apiBaseUrl,
  onActionHandled,
}: ExperienceRendererProps) {
  if (!plan) return null;

  // Extract metric strip component
  const metricStripComp = plan.components.find((c) => c.type === 'metric_strip');
  const metrics: MetricItem[] = metricStripComp?.props?.metrics || [];

  // Browser telemetry metadata if available
  const browserInfo = plan.metadata?.browser_page_info;

  return (
    <div
      className={`space-y-6 transition-all duration-300 ${
        isFullscreen
          ? 'fixed inset-0 z-50 bg-slate-950 p-6 overflow-y-auto'
          : 'relative w-full'
      }`}
      data-testid="experience-workspace-root"
    >
      {/* Workspace Header Banner */}
      <div className="flex flex-wrap items-center justify-between gap-4 bg-slate-900/90 border border-slate-800 rounded-xl p-4 shadow-lg">
        <div className="flex items-center gap-3">
          <span className="px-2.5 py-1 text-xs font-mono font-bold uppercase rounded bg-cyan-950 text-cyan-400 border border-cyan-800" data-testid="workspace-mode-badge">
            ⛶ {plan.mode.replace('_', ' ')}
          </span>
          {plan.plan_origin && (
            <span
              data-testid="plan-origin-badge"
              className="px-2 py-0.5 text-[10px] font-mono rounded bg-slate-800 text-slate-300 border border-slate-700"
            >
              {plan.plan_origin}
            </span>
          )}
          <div>
            <h2 className="text-xl font-bold text-white tracking-tight">{plan.title}</h2>
            {plan.subtitle && (
              <p className="text-xs text-slate-400 mt-0.5 max-w-2xl truncate">
                {plan.subtitle}
              </p>
            )}
          </div>
        </div>

        <div className="flex items-center gap-3">
          {plan.status && (
            <span
              className={`px-2.5 py-1 text-xs font-mono uppercase rounded border font-semibold ${
                plan.status === 'COMPLETED'
                  ? 'bg-emerald-950 text-emerald-300 border-emerald-800'
                  : 'bg-blue-950 text-blue-300 border-blue-800 animate-pulse'
              }`}
            >
              ● {plan.status}
            </span>
          )}

          {onToggleFullscreen && (
            <button
              onClick={onToggleFullscreen}
              data-testid="workspace-fullscreen-toggle"
              className="px-3 py-1.5 text-xs font-medium text-slate-300 bg-slate-800 hover:bg-slate-700 hover:text-white rounded-lg transition border border-slate-700 flex items-center gap-1.5"
            >
              {isFullscreen ? '✕ Exit Fullscreen' : '⛶ Full Workspace'}
            </button>
          )}
        </div>
      </div>

      {/* Browser Telemetry (if present in metadata) */}
      {browserInfo && (
        <BrowserTelemetryCard
          url={browserInfo.url}
          title={browserInfo.title}
          http_status={browserInfo.http_status}
          thumbnail_base64={browserInfo.thumbnail_base64}
          accessible_elements_count={browserInfo.accessible_elements_count}
          text_content_snippet={browserInfo.text_content_snippet}
        />
      )}

      {/* Metric Strip Component */}
      {metrics.length > 0 && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3" data-testid="experience-metric-strip">
          {metrics.map((m, idx) => {
            const badgeColor = m.badge_color || 'blue';
            const colorClasses: Record<string, string> = {
              green: 'text-green-400 border-green-800/60 bg-green-950/40',
              emerald: 'text-emerald-400 border-emerald-800/60 bg-emerald-950/40',
              blue: 'text-cyan-400 border-cyan-800/60 bg-cyan-950/40',
              purple: 'text-purple-400 border-purple-800/60 bg-purple-950/40',
              amber: 'text-amber-400 border-amber-800/60 bg-amber-950/40',
              cyan: 'text-sky-400 border-sky-800/60 bg-sky-950/40',
              gray: 'text-slate-400 border-slate-700 bg-slate-800/40'
            };
            const currentClass = colorClasses[badgeColor] || colorClasses.blue;

            return (
              <div
                key={idx}
                className="bg-slate-900/70 border border-slate-800 rounded-xl p-3.5 space-y-1 shadow"
              >
                <span className="text-[11px] font-medium text-slate-400 uppercase tracking-wider">
                  {m.label}
                </span>
                <div className="flex items-center gap-2">
                  <span className={`text-base font-bold font-mono px-2 py-0.5 rounded border ${currentClass}`}>
                    {String(m.value)}
                  </span>
                  {m.unit && <span className="text-xs text-slate-500">{m.unit}</span>}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Component Catalog Dispatcher */}
      <div className="space-y-6">
        {plan.components.map((comp) => {
          if (comp.type === 'interactive_canvas_2d') {
            return <InteractiveCanvas2D key={comp.id} {...(comp.props as any)} />;
          }

          if (comp.type === 'data_grid' || comp.type === 'comparison_matrix') {
            return <WorkspaceDataGrid key={comp.id} {...(comp.props as any)} />;
          }

          if (comp.type === 'form_draft') {
            return <FormDraft key={comp.id} {...(comp.props as any)} />;
          }

          if (comp.type === 'action_panel') {
            return (
              <ActionPanel
                key={comp.id}
                taskId={plan.task_id}
                apiKey={apiKey}
                apiBaseUrl={apiBaseUrl}
                onActionHandled={onActionHandled}
                {...(comp.props as any)}
              />
            );
          }

          // Ignore metric_strip here as it is rendered above
          if (comp.type === 'metric_strip') {
            return null;
          }

          return null;
        })}
      </div>
    </div>
  );
}
