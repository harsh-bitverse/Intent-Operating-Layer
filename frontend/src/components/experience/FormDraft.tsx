'use client';

import React, { useState } from 'react';

export interface FormDraftField {
  name: string;
  label?: string;
  value: any;
  type?: string;
  required?: boolean;
  source_evidence?: string;
  notes?: string;
}

export interface FormDraftProps {
  title?: string;
  service_name?: string;
  jurisdiction?: string;
  official_portal_url?: string;
  fields?: FormDraftField[];
  status?: string;
  instructions?: string;
}

export default function FormDraft({
  title = 'Service Application Form Draft',
  service_name,
  jurisdiction,
  official_portal_url,
  fields = [],
  status = 'LOCAL_DRAFT',
  instructions = 'Review the extracted draft fields below. In accordance with safety policies, this form has NOT been submitted to the government agency. You may copy these values directly to the official portal.',
}: FormDraftProps) {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    const payload: Record<string, any> = {};
    for (const f of fields) {
      payload[f.name] = f.value;
    }
    navigator.clipboard.writeText(JSON.stringify(payload, null, 2));
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div
      data-testid="form-draft-container"
      className="bg-slate-900/90 border border-slate-800 rounded-xl p-5 shadow-xl space-y-5"
    >
      {/* Header Banner */}
      <div className="flex flex-wrap items-start justify-between gap-4 border-b border-slate-800 pb-4">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <span className="text-xl">📋</span>
            <h3 className="text-base font-bold text-slate-100">{title}</h3>
            <span
              data-testid="form-draft-status-badge"
              className="px-2.5 py-0.5 text-xs font-mono font-bold rounded bg-cyan-950 text-cyan-300 border border-cyan-800"
            >
              🔒 {status}
            </span>
          </div>
          {(service_name || jurisdiction) && (
            <p className="text-xs text-slate-400">
              {service_name && <span className="font-semibold text-slate-300">{service_name}</span>}
              {service_name && jurisdiction && ' • '}
              {jurisdiction && <span className="text-slate-400">{jurisdiction}</span>}
            </p>
          )}
        </div>

        <div className="flex items-center gap-2">
          {official_portal_url && (
            <a
              href={official_portal_url}
              target="_blank"
              rel="noopener noreferrer"
              data-testid="official-portal-link"
              className="px-3.5 py-1.5 text-xs font-semibold rounded-lg bg-blue-600 hover:bg-blue-500 text-white shadow transition flex items-center gap-1.5"
            >
              <span>Official Portal ↗</span>
            </a>
          )}
          <button
            onClick={handleCopy}
            data-testid="copy-form-draft-btn"
            className="px-3.5 py-1.5 text-xs font-semibold rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white border border-slate-700 transition"
          >
            {copied ? '✓ Copied JSON' : '📋 Copy Draft JSON'}
          </button>
        </div>
      </div>

      {/* Safety Notice */}
      <div className="text-xs bg-slate-950/70 border border-slate-800/80 rounded-lg p-3 text-slate-400 leading-relaxed flex items-start gap-2.5">
        <span className="text-base">ℹ️</span>
        <div>
          <span className="font-semibold text-slate-300">Safe Operator Boundary: </span>
          {instructions}
        </div>
      </div>

      {/* Field List / Inputs */}
      <div className="space-y-3">
        <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400">
          Prefilled Form Fields ({fields.length})
        </h4>

        <div className="divide-y divide-slate-800/80 border border-slate-800 rounded-lg bg-slate-950/50 overflow-hidden">
          {fields.length === 0 ? (
            <div className="p-6 text-center text-xs text-slate-500">
              No fields populated in draft.
            </div>
          ) : (
            fields.map((f, idx) => (
              <div
                key={idx}
                data-testid={`form-field-${f.name}`}
                className="p-3.5 flex flex-col md:flex-row md:items-center justify-between gap-3 hover:bg-slate-900/40 transition"
              >
                <div className="space-y-0.5 max-w-sm">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-semibold text-slate-200">
                      {f.label || f.name}
                    </span>
                    {f.required && (
                      <span className="text-[10px] font-mono text-amber-400">*required</span>
                    )}
                  </div>
                  <span className="text-[11px] font-mono text-slate-500">{f.name}</span>
                  {f.notes && <p className="text-[11px] text-slate-400">{f.notes}</p>}
                </div>

                <div className="flex flex-col md:items-end gap-1 flex-1 md:max-w-md">
                  <div className="w-full bg-slate-900 border border-slate-800 rounded px-3 py-1.5 text-xs text-slate-200 font-mono break-all">
                    {String(f.value !== undefined && f.value !== null ? f.value : '—')}
                  </div>
                  {f.source_evidence && (
                    <span className="text-[10px] text-cyan-400/90 font-mono truncate max-w-full">
                      Source: {f.source_evidence}
                    </span>
                  )}
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
