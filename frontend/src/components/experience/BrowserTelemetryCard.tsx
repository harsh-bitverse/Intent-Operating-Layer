'use client';

import React, { useState } from 'react';
import { BrowserObservationData } from '../../types/experience';

interface BrowserTelemetryCardProps {
  observation?: BrowserObservationData;
  url?: string;
  title?: string;
  http_status?: number;
  thumbnail_base64?: string;
  screenshot_path?: string;
  accessible_elements_count?: number;
  text_content_snippet?: string;
}

export default function BrowserTelemetryCard({
  observation,
  url,
  title,
  http_status,
  thumbnail_base64,
  screenshot_path,
  accessible_elements_count,
  text_content_snippet,
}: BrowserTelemetryCardProps) {
  const currentUrl = observation?.url || url || '';
  const currentTitle = observation?.title || title || 'Browser Session';
  const status = observation?.http_status ?? http_status ?? 200;
  const thumbnail = observation?.thumbnail_base64 || thumbnail_base64;
  const elementsCount = observation?.accessible_elements_count ?? accessible_elements_count ?? 0;
  const snippet = observation?.text_content_snippet || text_content_snippet || '';

  const [expanded, setExpanded] = useState(false);

  if (!currentUrl && !currentTitle) return null;

  return (
    <div
      data-testid="browser-telemetry-card"
      className="bg-slate-900/90 border border-slate-800 rounded-xl p-4 shadow-lg space-y-3"
    >
      {/* Browser chrome header bar */}
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-800/80 pb-3">
        <div className="flex items-center gap-2 flex-1 min-w-0">
          <div className="flex items-center gap-1.5 text-xs text-slate-500">
            <span className="w-2.5 h-2.5 rounded-full bg-red-500/80 inline-block" />
            <span className="w-2.5 h-2.5 rounded-full bg-amber-500/80 inline-block" />
            <span className="w-2.5 h-2.5 rounded-full bg-emerald-500/80 inline-block" />
          </div>
          <div className="flex-1 bg-slate-950 border border-slate-800 rounded px-2.5 py-1 text-xs font-mono text-cyan-300 truncate">
            {currentUrl}
          </div>
        </div>

        <div className="flex items-center gap-2">
          <span
            data-testid="browser-status-badge"
            className={`px-2 py-0.5 text-[11px] font-mono font-bold rounded border ${
              status >= 200 && status < 300
                ? 'bg-emerald-950 text-emerald-300 border-emerald-800'
                : 'bg-amber-950 text-amber-300 border-amber-800'
            }`}
          >
            HTTP {status}
          </span>
          <span className="px-2 py-0.5 text-[11px] font-mono rounded bg-slate-800 text-slate-300 border border-slate-700">
            {elementsCount} interactive elements
          </span>
        </div>
      </div>

      {/* Page Title & Screenshot Thumbnail */}
      <div className="flex flex-col sm:flex-row items-start gap-4">
        {thumbnail && (
          <div className="shrink-0 w-36 h-24 rounded border border-slate-800 overflow-hidden bg-slate-950 shadow-inner">
            <img
              src={`data:image/png;base64,${thumbnail}`}
              alt="Browser Page Screenshot"
              data-testid="browser-screenshot-thumbnail"
              className="w-full h-full object-cover object-top"
            />
          </div>
        )}

        <div className="space-y-1.5 flex-1 min-w-0">
          <h4 className="text-sm font-semibold text-slate-200">{currentTitle}</h4>
          {snippet && (
            <p className="text-xs text-slate-400 line-clamp-3 leading-relaxed">
              {snippet}
            </p>
          )}

          {snippet && snippet.length > 150 && (
            <button
              onClick={() => setExpanded(!expanded)}
              className="text-[11px] font-medium text-cyan-400 hover:text-cyan-300 transition"
            >
              {expanded ? '▲ Collapse extracted text' : '▼ Read full extracted snippet'}
            </button>
          )}
        </div>
      </div>

      {/* Expanded Text Snippet */}
      {expanded && snippet && (
        <pre className="text-[11px] font-mono text-slate-300 bg-slate-950 p-3 rounded border border-slate-800 max-h-48 overflow-y-auto whitespace-pre-wrap">
          {snippet}
        </pre>
      )}
    </div>
  );
}
