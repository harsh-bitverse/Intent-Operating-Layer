'use client';

import React from 'react';
import { TimelineViewProps } from '../../types/experience';

export default function TimelineView({
  title = 'Execution & Milestone Timeline',
  subtitle,
  items = [],
  current_stage
}: TimelineViewProps) {
  if (!items || items.length === 0) {
    return null;
  }

  const statusStyles: Record<string, { dot: string; text: string; bg: string; border: string }> = {
    completed: {
      dot: 'bg-emerald-400 ring-emerald-950',
      text: 'text-emerald-300',
      bg: 'bg-emerald-950/40',
      border: 'border-emerald-800/60'
    },
    active: {
      dot: 'bg-cyan-400 ring-cyan-950 animate-pulse',
      text: 'text-cyan-300 font-bold',
      bg: 'bg-cyan-950/40',
      border: 'border-cyan-800/80 shadow-md shadow-cyan-950/50'
    },
    pending: {
      dot: 'bg-slate-600 ring-slate-900',
      text: 'text-slate-400',
      bg: 'bg-slate-900/40',
      border: 'border-slate-800'
    },
    failed: {
      dot: 'bg-red-400 ring-red-950',
      text: 'text-red-300',
      bg: 'bg-red-950/40',
      border: 'border-red-800/60'
    }
  };

  return (
    <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-5 shadow-lg space-y-4" data-testid="timeline-view">
      <div className="flex items-center justify-between border-b border-slate-800 pb-3">
        <div>
          <h3 className="text-base font-semibold text-white tracking-wide">{title}</h3>
          {subtitle && <p className="text-xs text-slate-400 mt-0.5">{subtitle}</p>}
        </div>
        {current_stage && (
          <span className="px-2.5 py-1 text-xs font-mono rounded bg-cyan-950 text-cyan-300 border border-cyan-800">
            Active: {current_stage}
          </span>
        )}
      </div>

      <div className="relative pl-6 space-y-6 before:absolute before:left-2 before:top-3 before:bottom-3 before:w-0.5 before:bg-slate-800">
        {items.map((item, idx) => {
          const status = item.status || (idx === items.length - 1 ? 'active' : 'completed');
          const style = statusStyles[status] || statusStyles.pending;

          return (
            <div key={item.id || idx} className="relative group">
              {/* Dot marker */}
              <div
                className={`absolute -left-6 top-1.5 w-3.5 h-3.5 rounded-full ring-4 transition-all duration-300 ${style.dot}`}
              />

              {/* Card Container */}
              <div className={`rounded-xl p-4 border transition-all duration-200 ${style.bg} ${style.border}`}>
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <span className={`text-sm font-semibold tracking-tight ${style.text}`}>
                    {item.title}
                  </span>
                  <div className="flex items-center gap-2">
                    {item.badge && (
                      <span className="px-2 py-0.5 text-[10px] font-mono uppercase rounded bg-slate-800 text-slate-300 border border-slate-700">
                        {item.badge}
                      </span>
                    )}
                    {item.timestamp && (
                      <span className="text-xs font-mono text-slate-500">
                        {item.timestamp}
                      </span>
                    )}
                  </div>
                </div>

                {item.description && (
                  <p className="text-xs text-slate-300 mt-1.5 leading-relaxed">
                    {item.description}
                  </p>
                )}

                {item.metadata && Object.keys(item.metadata).length > 0 && (
                  <div className="mt-2.5 pt-2 border-t border-slate-800/60 flex flex-wrap gap-2 text-[11px] font-mono text-slate-400">
                    {Object.entries(item.metadata).map(([k, v]) => (
                      <span key={k} className="bg-slate-950 px-2 py-0.5 rounded border border-slate-800">
                        <span className="text-slate-500">{k}:</span> {String(v)}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
