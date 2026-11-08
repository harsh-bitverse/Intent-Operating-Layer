'use client';

import React, { useState } from 'react';
import { DocumentPreviewProps } from '../../types/experience';

export default function DocumentPreview({
  title = 'Document Preview',
  document_type = 'MARKDOWN',
  content,
  sections = [],
  metadata = {},
  download_url,
}: DocumentPreviewProps) {
  const [copied, setCopied] = useState(false);

  const fullText = content || sections.map((s) => `## ${s.heading}\n\n${s.text}`).join('\n\n');

  const handleCopy = () => {
    if (fullText) {
      navigator.clipboard.writeText(fullText);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  return (
    <div
      className="bg-slate-900 border border-slate-700/80 rounded-xl p-5 shadow-2xl space-y-4"
      data-testid="document-preview-root"
    >
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-800 pb-3">
        <div className="flex items-center gap-2.5">
          <span className="p-1.5 rounded-lg bg-indigo-950 text-indigo-400 border border-indigo-800/60 text-sm">
            📄
          </span>
          <div>
            <h3 className="text-base font-semibold text-white tracking-wide">{title}</h3>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-400 border border-slate-700 uppercase">
              {document_type}
            </span>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {fullText && (
            <button
              onClick={handleCopy}
              data-testid="document-copy-btn"
              className="px-2.5 py-1 text-xs font-mono text-slate-300 bg-slate-800 hover:bg-slate-700 rounded border border-slate-700 transition flex items-center gap-1"
            >
              {copied ? '✓ Copied' : '📋 Copy Text'}
            </button>
          )}
          {download_url && (
            <a
              href={download_url}
              target="_blank"
              rel="noreferrer"
              data-testid="document-download-link"
              className="px-2.5 py-1 text-xs font-mono text-cyan-300 bg-cyan-950/80 hover:bg-cyan-900 rounded border border-cyan-800 transition"
            >
              ⬇ Download
            </a>
          )}
        </div>
      </div>

      {/* Metadata strip if present */}
      {Object.keys(metadata).length > 0 && (
        <div className="flex flex-wrap gap-2 text-xs">
          {Object.entries(metadata).map(([k, v]) => (
            <span
              key={k}
              className="px-2 py-0.5 rounded bg-slate-800/80 text-slate-300 border border-slate-700/60 font-mono text-[11px]"
            >
              <strong className="text-slate-400">{k}:</strong> {String(v)}
            </span>
          ))}
        </div>
      )}

      {/* Content Rendering */}
      <div className="bg-slate-950 border border-slate-800/80 rounded-lg p-4 max-h-96 overflow-y-auto font-sans text-sm text-slate-200 leading-relaxed space-y-4">
        {content ? (
          <div className="whitespace-pre-wrap font-mono text-xs text-slate-300 bg-slate-900/60 p-3 rounded border border-slate-800">
            {content}
          </div>
        ) : sections.length > 0 ? (
          sections.map((sec, idx) => (
            <div key={idx} className="space-y-1.5 border-b border-slate-800/60 pb-3 last:border-b-0 last:pb-0">
              <h4 className="text-xs font-bold text-cyan-400 uppercase tracking-wider">{sec.heading}</h4>
              <p className="text-xs text-slate-300 whitespace-pre-wrap">{sec.text}</p>
            </div>
          ))
        ) : (
          <div className="text-center py-6 text-xs text-slate-500 italic">No document content available.</div>
        )}
      </div>
    </div>
  );
}
