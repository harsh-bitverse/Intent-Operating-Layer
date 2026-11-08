'use client';

import React, { useState } from 'react';
import { ActionEffect, TaskActionRequest } from '../../types/experience';

interface ActionPanelProps {
  taskId: string;
  actionRequest?: TaskActionRequest;
  action_id?: string;
  action_type?: string;
  effect?: ActionEffect;
  target_url?: string;
  parameters?: Record<string, any>;
  explanation?: string;
  ticket?: any;
  apiKey?: string;
  apiBaseUrl?: string;
  onActionHandled?: (decision: 'APPROVED' | 'REJECTED') => void;
}

export default function ActionPanel({
  taskId,
  actionRequest,
  action_id,
  action_type,
  effect = 'EXTERNAL_WRITE',
  target_url,
  parameters = {},
  explanation,
  ticket,
  apiKey = 'iol_demo_operator_key',
  apiBaseUrl = 'http://127.0.0.1:8000',
  onActionHandled,
}: ActionPanelProps) {
  const rawReq: any = actionRequest || {};
  const rawTicket = rawReq.ticket || (rawReq.ticket_id ? rawReq : ticket);

  const req = {
    action_id: rawReq.action_id || action_id || 'act_pending',
    action_type: rawReq.action_type || action_type || 'browser.action',
    effect: (rawReq.effect || effect || 'EXTERNAL_WRITE') as ActionEffect,
    target_url: rawReq.target_url || rawReq.target_endpoint || target_url || '',
    parameters: rawReq.parameters || parameters || {},
    explanation: rawReq.explanation || rawReq.rationale || explanation || 'This action requires explicit operator approval before modifying external state.',
    ticket: rawTicket,
  };

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [decision, setDecision] = useState<'APPROVED' | 'REJECTED' | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const activeTicket = rawTicket;

  const effectBadges: Record<ActionEffect, { label: string; bg: string; text: string; border: string }> = {
    READ: { label: 'READ (Low Risk)', bg: 'bg-emerald-950/60', text: 'text-emerald-300', border: 'border-emerald-700/60' },
    LOCAL_DRAFT: { label: 'LOCAL DRAFT (Safe)', bg: 'bg-cyan-950/60', text: 'text-cyan-300', border: 'border-cyan-700/60' },
    EXTERNAL_WRITE: { label: 'EXTERNAL WRITE (Approval Required)', bg: 'bg-amber-950/80', text: 'text-amber-300', border: 'border-amber-600/80' },
    PAYMENT_OR_ORDER: { label: 'FINANCIAL / ORDER (High Consequence)', bg: 'bg-orange-950/90', text: 'text-orange-300', border: 'border-orange-600/80' },
    DESTRUCTIVE: { label: 'DESTRUCTIVE / IRREVERSIBLE (Critical)', bg: 'bg-red-950/90', text: 'text-red-300', border: 'border-red-600/80' },
  };

  const badge = effectBadges[req.effect] || effectBadges.EXTERNAL_WRITE;

  const handleApprove = async () => {
    if (!activeTicket || isSubmitting) return;
    setIsSubmitting(true);
    setErrorMessage(null);

    try {
      const headers: Record<string, string> = {
        'Content-Type': 'application/json',
      };
      if (apiKey) headers['X-API-Key'] = apiKey;

      const res = await fetch(`${apiBaseUrl}/api/tasks/${taskId}/actions/approve`, {
        method: 'POST',
        headers,
        body: JSON.stringify({
          ticket_id: activeTicket.ticket_id,
          fingerprint: activeTicket.fingerprint,
        }),
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: 'Approval failed' }));
        throw new Error(err.detail || `Server returned ${res.status}`);
      }

      setDecision('APPROVED');
      if (onActionHandled) {
        setTimeout(() => onActionHandled('APPROVED'), 1200);
      }
    } catch (err: any) {
      setErrorMessage(err.message || 'Failed to approve action');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleReject = async () => {
    if (!activeTicket || isSubmitting) return;
    setIsSubmitting(true);
    setErrorMessage(null);

    try {
      const headers: Record<string, string> = {
        'Content-Type': 'application/json',
      };
      if (apiKey) headers['X-API-Key'] = apiKey;

      const res = await fetch(`${apiBaseUrl}/api/tasks/${taskId}/actions/reject`, {
        method: 'POST',
        headers,
        body: JSON.stringify({
          ticket_id: activeTicket.ticket_id,
          reason: 'Operator declined execution via Action Panel',
        }),
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: 'Rejection failed' }));
        throw new Error(err.detail || `Server returned ${res.status}`);
      }

      setDecision('REJECTED');
      if (onActionHandled) onActionHandled('REJECTED');
    } catch (err: any) {
      setErrorMessage(err.message || 'Failed to reject action');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div
      data-testid="action-approval-panel"
      className="bg-slate-900 border-2 border-amber-500/40 rounded-xl p-5 shadow-2xl space-y-4 transition-all"
    >
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-800 pb-3">
        <div className="flex items-center gap-2.5">
          <span className="text-xl">🛡️</span>
          <div>
            <h3 className="text-sm font-bold text-slate-100 flex items-center gap-2">
              Action Approval Required
              <span
                data-testid="action-effect-badge"
                className={`text-[11px] font-mono px-2 py-0.5 rounded border uppercase font-semibold ${badge.bg} ${badge.text} ${badge.border}`}
              >
                {badge.label}
              </span>
            </h3>
            <p className="text-xs text-slate-400 mt-0.5">
              IOL safety boundary paused execution until an operator confirms this consequential action.
            </p>
          </div>
        </div>

        {activeTicket && (
          <div className="text-right text-[11px] font-mono text-slate-400">
            <div>Ticket: <span className="text-slate-200">{activeTicket.ticket_id.slice(0, 14)}...</span></div>
            <div>Expires: <span className="text-amber-400">{new Date(activeTicket.expires_at).toLocaleTimeString()}</span></div>
          </div>
        )}
      </div>

      {/* Rationale & Action Details */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
        <div className="space-y-2 bg-slate-950/60 p-3 rounded-lg border border-slate-800">
          <div className="text-slate-400 font-semibold uppercase text-[10px] tracking-wider">Action Intent</div>
          <div className="text-slate-200 font-mono font-medium">{req.action_type}</div>
          {req.target_url && (
            <div className="break-all text-cyan-400 font-mono text-[11px]">
              Target: <span className="underline">{req.target_url}</span>
            </div>
          )}
          <p className="text-slate-300 text-xs leading-relaxed pt-1">
            {req.explanation}
          </p>
        </div>

        <div className="space-y-2 bg-slate-950/60 p-3 rounded-lg border border-slate-800">
          <div className="text-slate-400 font-semibold uppercase text-[10px] tracking-wider">Parameters & Payload</div>
          <pre className="text-[11px] font-mono text-slate-300 max-h-32 overflow-y-auto bg-slate-900/90 p-2 rounded border border-slate-800/80">
            {JSON.stringify(req.parameters, null, 2)}
          </pre>
        </div>
      </div>

      {/* Error Banner */}
      {errorMessage && (
        <div className="text-xs text-red-300 bg-red-950/60 border border-red-800/80 p-2.5 rounded-lg">
          ⚠️ {errorMessage}
        </div>
      )}

      {/* Decision Status or Action Buttons */}
      {decision ? (
        <div
          data-testid="action-decision-status"
          className={`p-3 rounded-lg text-xs font-semibold text-center border ${
            decision === 'APPROVED'
              ? 'bg-emerald-950/60 text-emerald-300 border-emerald-800'
              : 'bg-red-950/60 text-red-300 border-red-800'
          }`}
        >
          {decision === 'APPROVED'
            ? '✓ Action approved. Resuming execution...'
            : '✕ Action rejected. Task will handle rejection gracefully.'}
        </div>
      ) : (
        <div className="flex items-center justify-end gap-3 pt-2">
          <button
            onClick={handleReject}
            disabled={isSubmitting || !activeTicket}
            data-testid="reject-action-btn"
            className="px-4 py-2 text-xs font-semibold rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white border border-slate-700 transition disabled:opacity-50"
          >
            {isSubmitting ? 'Processing...' : 'Reject Action'}
          </button>
          <button
            onClick={handleApprove}
            disabled={isSubmitting || !activeTicket}
            data-testid="approve-action-btn"
            className="px-5 py-2 text-xs font-bold rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white shadow-lg transition disabled:opacity-50 flex items-center gap-1.5"
          >
            {isSubmitting ? 'Submitting...' : '✓ Approve & Execute'}
          </button>
        </div>
      )}
    </div>
  );
}
