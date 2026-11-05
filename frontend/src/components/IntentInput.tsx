'use client';

import React, { useState } from 'react';

interface IntentInputProps {
  onSubmit: (intent: string) => Promise<void>;
  isLoading: boolean;
}

export const IntentInput: React.FC<IntentInputProps> = ({ onSubmit, isLoading }) => {
  const [intent, setIntent] = useState('');

  const suggestions = [
    'Research top US AI & SciML professors for Summer 2027 internship',
    'Discover leading AI and robotics startups for research collaboration',
    'Reconcile faculty database and schedule 8:00 AM destination delivery windows',
  ];

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!intent.trim() || isLoading) return;
    onSubmit(intent);
  };

  const handleSelectSuggestion = (s: string) => {
    setIntent(s);
  };

  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-900/90 p-6 shadow-2xl backdrop-blur-xl">
      <div className="mb-3">
        <label htmlFor="intent-input" className="block text-sm font-semibold text-slate-200">
          State Your High-Level Intent
        </label>
        <p className="text-xs text-slate-400 mt-0.5">
          IOL decomposes your intent into reusable capabilities, validates evidence, and generates verified outcomes.
        </p>
      </div>

      <form onSubmit={handleSubmit} className="relative">
        <textarea
          id="intent-input"
          data-testid="intent-input"
          rows={3}
          value={intent}
          onChange={(e) => setIntent(e.target.value)}
          placeholder="e.g. Find top AI & SciML professors in the US, extract verified emails, draft tailored 4-paragraph outreach, and schedule 8:00 AM destination windows..."
          className="w-full resize-none rounded-xl border border-slate-700 bg-slate-950 p-4 text-sm text-slate-100 placeholder-slate-500 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 disabled:opacity-50"
          disabled={isLoading}
        />
        <div className="mt-3 flex items-center justify-between">
          <div className="flex flex-wrap items-center gap-1.5">
            <span className="text-xs text-slate-500 mr-1">Examples:</span>
            {suggestions.map((s, idx) => (
              <button
                key={idx}
                type="button"
                onClick={() => handleSelectSuggestion(s)}
                className="rounded-full border border-slate-800 bg-slate-950 px-2.5 py-1 text-xs text-slate-400 hover:border-slate-700 hover:text-slate-200 transition-colors"
              >
                {s.length > 40 ? s.slice(0, 38) + '...' : s}
              </button>
            ))}
          </div>

          <button
            type="submit"
            data-testid="submit-intent-btn"
            disabled={!intent.trim() || isLoading}
            className="inline-flex items-center space-x-2 rounded-xl bg-blue-600 px-5 py-2.5 text-sm font-medium text-white shadow-lg shadow-blue-500/25 hover:bg-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-400 disabled:opacity-40 disabled:cursor-not-allowed transition-all"
          >
            {isLoading ? (
              <>
                <span className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
                <span>Executing Pipeline...</span>
              </>
            ) : (
              <>
                <span>Execute Intent</span>
                <span>→</span>
              </>
            )}
          </button>
        </div>
      </form>
    </div>
  );
};
