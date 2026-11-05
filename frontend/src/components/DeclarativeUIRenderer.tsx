import React from 'react';
import {
  CardComponent,
  ComparisonComponent,
  DeclarativeUIRoot,
  TableComponent,
  TimelineComponent,
  UIComponent,
} from '../types/iol';

interface RendererProps {
  uiRoot?: DeclarativeUIRoot;
}

export const DeclarativeUIRenderer: React.FC<RendererProps> = ({ uiRoot }) => {
  if (!uiRoot || !uiRoot.components || uiRoot.components.length === 0) {
    return (
      <div className="rounded-lg border border-slate-800 bg-slate-900/50 p-6 text-center text-slate-400">
        No declarative UI components available yet. Awaiting capability output...
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header Summary */}
      {uiRoot.summary && (
        <div className="rounded-lg border border-blue-500/20 bg-blue-950/30 p-4 text-sm text-blue-200 backdrop-blur-sm">
          <div className="flex items-center space-x-2">
            <span className="flex h-2 w-2 rounded-full bg-blue-400 animate-pulse" />
            <span className="font-medium text-blue-100">{uiRoot.title}</span>
          </div>
          <p className="mt-1 text-slate-300">{uiRoot.summary}</p>
        </div>
      )}

      {/* Render Components */}
      {uiRoot.components.map((comp) => {
        if (comp.type === 'card') {
          return <SafeCard key={comp.id} card={comp} />;
        }
        if (comp.type === 'timeline') {
          return <SafeTimeline key={comp.id} timeline={comp} />;
        }
        if (comp.type === 'table') {
          return <SafeTable key={comp.id} table={comp} />;
        }
        if (comp.type === 'comparison') {
          return <SafeComparison key={comp.id} comparison={comp} />;
        }
        return null;
      })}
    </div>
  );
};

// =============================================================================
// Safe Card Renderer
// =============================================================================
const SafeCard: React.FC<{ card: CardComponent }> = ({ card }) => {
  const variantStyles = {
    default: 'border-slate-800 bg-slate-900/80',
    highlight: 'border-indigo-500/30 bg-indigo-950/20',
    warning: 'border-amber-500/30 bg-amber-950/20',
    success: 'border-emerald-500/30 bg-emerald-950/20',
    info: 'border-cyan-500/30 bg-cyan-950/20',
  }[card.variant || 'default'];

  return (
    <div className={`rounded-xl border p-5 shadow-lg backdrop-blur-sm ${variantStyles}`}>
      <div className="flex items-start justify-between">
        <div>
          <h3 className="text-base font-semibold text-white">{card.title}</h3>
          {card.subtitle && <p className="text-xs text-slate-400 mt-0.5">{card.subtitle}</p>}
        </div>
        {card.badges && card.badges.length > 0 && (
          <div className="flex flex-wrap gap-1.5">
            {card.badges.map((b, i) => (
              <span
                key={i}
                className="rounded-full bg-slate-800/80 px-2.5 py-0.5 text-xs font-medium text-slate-300 border border-slate-700"
              >
                {b}
              </span>
            ))}
          </div>
        )}
      </div>

      {/* Metrics Grid */}
      {card.metrics && card.metrics.length > 0 && (
        <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-4">
          {card.metrics.map((m, idx) => (
            <div key={idx} className="rounded-lg bg-slate-950/50 p-3 border border-slate-800/60">
              <div className="text-xs font-medium text-slate-400">{m.label}</div>
              <div className="mt-1 text-lg font-bold text-slate-100 flex items-baseline space-x-1">
                <span>{m.value}</span>
                {m.unit && <span className="text-xs text-slate-400">{m.unit}</span>}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Card Content Text */}
      {card.content && (
        <div className="mt-4 whitespace-pre-wrap rounded-lg bg-slate-950/60 p-4 font-mono text-xs text-slate-200 border border-slate-800/80 leading-relaxed max-h-96 overflow-y-auto">
          {card.content}
        </div>
      )}
    </div>
  );
};

// =============================================================================
// Safe Timeline Renderer
// =============================================================================
const SafeTimeline: React.FC<{ timeline: TimelineComponent }> = ({ timeline }) => {
  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900/80 p-5 shadow-lg">
      <h3 className="text-base font-semibold text-white mb-4">{timeline.title}</h3>
      <div className="space-y-4">
        {timeline.items.map((item, idx) => {
          const isLast = idx === timeline.items.length - 1;

          const statusIcon = {
            pending: (
              <span className="flex h-5 w-5 items-center justify-center rounded-full bg-slate-800 text-slate-400 text-xs">
                {idx + 1}
              </span>
            ),
            running: (
              <span className="flex h-5 w-5 items-center justify-center rounded-full bg-blue-500 text-white text-xs animate-spin">
                ⟳
              </span>
            ),
            success: (
              <span className="flex h-5 w-5 items-center justify-center rounded-full bg-emerald-500 text-white text-xs">
                ✓
              </span>
            ),
            failed: (
              <span className="flex h-5 w-5 items-center justify-center rounded-full bg-red-500 text-white text-xs">
                ✕
              </span>
            ),
            skipped: (
              <span className="flex h-5 w-5 items-center justify-center rounded-full bg-amber-500 text-white text-xs">
                -
              </span>
            ),
          }[item.status || 'pending'];

          return (
            <div key={item.id} className="relative flex items-start space-x-3">
              {!isLast && (
                <div className="absolute left-2.5 top-6 bottom-0 w-0.5 bg-slate-800 -translate-x-1/2" />
              )}
              <div className="relative z-10 flex-shrink-0 mt-0.5">{statusIcon}</div>
              <div className="min-w-0 flex-1">
                <div className="flex items-baseline justify-between">
                  <p className="text-sm font-medium text-slate-200">{item.title}</p>
                  {item.timestamp && (
                    <span className="text-xs text-slate-500 font-mono">{item.timestamp}</span>
                  )}
                </div>
                {item.description && (
                  <p className="mt-0.5 text-xs text-slate-400">{item.description}</p>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

// =============================================================================
// Safe Table Renderer with Expandable Field-Level Evidence
// =============================================================================
const SafeTable: React.FC<{ table: TableComponent }> = ({ table }) => {
  const [expandedRows, setExpandedRows] = React.useState<Record<number, boolean>>({});

  const toggleRow = (idx: number) => {
    setExpandedRows((prev) => ({ ...prev, [idx]: !prev[idx] }));
  };

  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900/80 p-5 shadow-lg overflow-hidden">
      <div className="mb-4 flex items-center justify-between">
        <div>
          <h3 className="text-base font-semibold text-white">{table.title}</h3>
          {table.subtitle && <p className="text-xs text-slate-400 mt-0.5">{table.subtitle}</p>}
        </div>
        <span className="text-xs text-slate-500 font-mono">
          {table.rows.length} {table.rows.length === 1 ? 'record' : 'records'}
        </span>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-left text-sm text-slate-300">
          <thead className="bg-slate-950/60 text-xs uppercase text-slate-400 border-b border-slate-800">
            <tr>
              <th className="w-8 px-3 py-3"></th>
              {table.columns.map((col) => (
                <th key={col.key} className="px-4 py-3 font-semibold">
                  {col.header}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/60 font-normal">
            {table.rows.length === 0 ? (
              <tr>
                <td
                  colSpan={table.columns.length + 1}
                  className="px-4 py-6 text-center text-xs text-slate-500"
                >
                  No records to display yet.
                </td>
              </tr>
            ) : (
              table.rows.map((row, rIdx) => {
                const hasEvidence = !!row._field_evidence;
                const isExpanded = !!expandedRows[rIdx];

                return (
                  <React.Fragment key={rIdx}>
                    <tr
                      data-testid={`table-row-${rIdx}`}
                      onClick={() => hasEvidence && toggleRow(rIdx)}
                      className={`hover:bg-slate-800/40 transition-colors ${
                        hasEvidence ? 'cursor-pointer' : ''
                      } ${isExpanded ? 'bg-slate-800/30' : ''}`}
                    >
                      <td className="px-3 py-3 text-center text-slate-500">
                        {hasEvidence ? (
                          <span className="inline-block transform transition-transform duration-200 text-xs">
                            {isExpanded ? '▼' : '▶'}
                          </span>
                        ) : null}
                      </td>
                      {table.columns.map((col) => (
                        <td key={col.key} className="px-4 py-3 whitespace-nowrap text-xs">
                          {renderTableCell(col, row[col.key])}
                        </td>
                      ))}
                    </tr>

                    {/* Expandable Field-Level Evidence Details */}
                    {isExpanded && hasEvidence && (
                      <tr className="bg-slate-950/90 border-b border-slate-800" data-testid="evidence-panel-row">
                        <td colSpan={table.columns.length + 1} className="p-4 sm:p-5">
                          <EvidenceDetailsPanel row={row} />
                        </td>
                      </tr>
                    )}
                  </React.Fragment>
                );
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};

// =============================================================================
// Field-Level Evidence Inspector Panel
// =============================================================================
const EvidenceDetailsPanel: React.FC<{ row: Record<string, any> }> = ({ row }) => {
  const evidenceMap = row._field_evidence || {};
  const classification = row._classification;
  const flags: string[] = row._validation_flags || [];

  return (
    <div className="space-y-4">
      {/* Classification & Four-Tier Intent Satisfaction Banner */}
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-800/80 pb-3">
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-xs font-semibold text-slate-300">Entity Classification:</span>
          <span className="rounded-md bg-indigo-500/10 px-2.5 py-0.5 text-xs font-medium text-indigo-300 border border-indigo-500/20">
            {classification || 'Verified Entity'}
          </span>
          {row._is_semantically_relevant && (
            <span className="rounded-md bg-emerald-500/10 px-2.5 py-0.5 text-xs font-semibold text-emerald-400 border border-emerald-500/30">
              ✓ Intent Satisfied
            </span>
          )}
        </div>
        {flags.length > 0 && (
          <div className="flex flex-wrap items-center gap-1.5">
            <span className="text-xs text-amber-400 font-medium">Flags:</span>
            {flags.map((flag, idx) => (
              <span
                key={idx}
                className="rounded bg-amber-500/10 px-2 py-0.5 text-[10px] font-mono text-amber-300 border border-amber-500/20"
              >
                {flag}
              </span>
            ))}
          </div>
        )}
      </div>

      {/* Semantic Intent Evidence Excerpt */}
      {row._relevance_evidence && (
        <div className="rounded-lg bg-emerald-950/20 border border-emerald-500/20 p-2.5 text-xs text-emerald-300 flex items-start space-x-2">
          <span className="text-emerald-400 font-semibold shrink-0">Semantic Corroboration:</span>
          <span className="text-slate-300">{row._relevance_evidence}</span>
        </div>
      )}

      {/* Field Evidence Grid */}
      <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
        {Object.entries(evidenceMap).map(([fieldName, ev]: [string, any]) => {
          const statusStyles = {
            DIRECTLY_SUPPORTED: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20',
            DERIVED: 'bg-cyan-500/10 text-cyan-400 border-cyan-500/20',
            INFERRED: 'bg-amber-500/10 text-amber-400 border-amber-500/20',
            UNKNOWN: 'bg-slate-800/80 text-slate-400 border-slate-700',
            UNSUPPORTED: 'bg-rose-500/10 text-rose-400 border-rose-500/20',
          }[ev.verification_status as string] || 'bg-slate-800 text-slate-400 border-slate-700';

          return (
            <div
              key={fieldName}
              className="rounded-lg border border-slate-800/80 bg-slate-900/60 p-3.5 space-y-2"
            >
              <div className="flex items-center justify-between">
                <span className="font-mono text-xs font-semibold text-slate-200 capitalize">
                  {fieldName.replace(/_/g, ' ')}
                </span>
                <div className="flex items-center space-x-2">
                  <span className={`rounded px-1.5 py-0.5 text-[10px] font-semibold border ${statusStyles}`}>
                    {ev.verification_status}
                  </span>
                  <span className="font-mono text-[10px] text-slate-400">
                    conf: {(ev.confidence ?? 0).toFixed(2)}
                  </span>
                </div>
              </div>

              <div className="text-xs text-slate-300">
                <span className="text-slate-500">Value: </span>
                <span className="font-medium text-slate-200">
                  {ev.field_value !== null && ev.field_value !== undefined
                    ? String(ev.field_value)
                    : <span className="text-slate-500 italic">None / Unknown</span>}
                </span>
              </div>

              {ev.relevant_excerpt && (
                <div className="rounded bg-slate-950/60 p-2 text-[11px] text-slate-400 font-mono border border-slate-800/60 leading-relaxed">
                  "{ev.relevant_excerpt}"
                </div>
              )}

              <div className="flex items-center justify-between pt-1 text-[10px] text-slate-500">
                <span>Method: {ev.verification_method || 'Check'}</span>
                {ev.evidence_url && (
                  <a
                    href={ev.evidence_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-blue-400 hover:text-blue-300 underline font-mono flex items-center space-x-1"
                    onClick={(e) => e.stopPropagation()}
                  >
                    <span>Source Evidence ↗</span>
                  </a>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

// =============================================================================
// Safe Multi-Entity Comparison Matrix Renderer
// =============================================================================
const SafeComparison: React.FC<{ comparison: ComparisonComponent }> = ({ comparison }) => {
  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900/80 p-5 shadow-lg overflow-hidden">
      <div className="mb-4">
        <h3 className="text-base font-semibold text-white">{comparison.title}</h3>
        {comparison.subtitle && <p className="text-xs text-slate-400 mt-0.5">{comparison.subtitle}</p>}
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-left text-sm text-slate-300 border-collapse">
          <thead className="bg-slate-950/70 border-b border-slate-800">
            <tr>
              <th className="px-4 py-3 text-xs uppercase text-slate-400 font-semibold w-1/4">
                Feature / Dimension
              </th>
              {comparison.entities.map((entity) => (
                <th key={entity.entity_id} className="px-4 py-3">
                  <div>
                    <div className="font-semibold text-white text-sm">{entity.name}</div>
                    {entity.badge && (
                      <span className="mt-1 inline-block rounded-full bg-blue-500/10 px-2 py-0.5 text-[10px] font-medium text-blue-400 border border-blue-500/20">
                        {entity.badge}
                      </span>
                    )}
                    {entity.primary_metric && (
                      <div className="text-[11px] text-slate-400 font-mono mt-1">
                        {entity.primary_metric}
                      </div>
                    )}
                  </div>
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/60">
            {comparison.features.map((feat) => (
              <tr key={feat.key} className="hover:bg-slate-800/30 transition-colors">
                <td className="px-4 py-3 text-xs font-semibold text-slate-300 bg-slate-950/30">
                  {feat.label}
                </td>
                {comparison.entities.map((entity) => {
                  const val = feat.values[entity.entity_id];
                  const isWinner = feat.winner_entity_id === entity.entity_id;

                  return (
                    <td
                      key={entity.entity_id}
                      className={`px-4 py-3 text-xs ${
                        isWinner ? 'bg-indigo-950/20 border-l-2 border-indigo-500 font-medium' : ''
                      }`}
                    >
                      <div className="flex items-center space-x-1.5">
                        <span className="text-slate-200">
                          {val !== null && val !== undefined ? String(val) : '—'}
                        </span>
                        {isWinner && (
                          <span className="rounded bg-indigo-500/20 px-1.5 py-0.2 text-[9px] font-bold text-indigo-300">
                            LEADER
                          </span>
                        )}
                      </div>
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

function renderTableCell(col: any, val: any) {
  if (val === null || val === undefined) return <span className="text-slate-600">—</span>;

  if (col.type === 'score') {
    const num = Number(val);
    const pct = Math.round(num * 100);
    const color =
      pct >= 85 ? 'bg-emerald-500 text-emerald-400' : pct >= 65 ? 'bg-amber-500 text-amber-400' : 'bg-red-500 text-red-400';
    return (
      <div className="flex items-center space-x-2">
        <div className="w-16 h-1.5 rounded-full bg-slate-800 overflow-hidden">
          <div className={`h-full ${color.split(' ')[0]}`} style={{ width: `${pct}%` }} />
        </div>
        <span className="font-mono text-xs text-slate-300">{num.toFixed(2)}</span>
      </div>
    );
  }

  if (col.type === 'badge') {
    const str = String(val).toUpperCase();
    const isSuccess = str.includes('VERIFIED') || str.includes('YES') || str.includes('SUCCESS');
    const isWarning = str.includes('DISCOVERED') || str.includes('FLAGGED') || str.includes('PENDING');
    const badgeColor = isSuccess
      ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
      : isWarning
      ? 'bg-amber-500/10 text-amber-400 border-amber-500/20'
      : 'bg-slate-800 text-slate-400 border-slate-700';

    return (
      <span className={`inline-block rounded-full px-2 py-0.5 text-[10px] font-medium border ${badgeColor}`}>
        {val}
      </span>
    );
  }

  if (col.type === 'link') {
    const url = String(val);
    return (
      <a
        href={url}
        target="_blank"
        rel="noopener noreferrer"
        className="text-blue-400 hover:text-blue-300 underline font-mono text-xs truncate max-w-xs block"
        onClick={(e) => e.stopPropagation()}
      >
        {url}
      </a>
    );
  }

  return <span>{String(val)}</span>;
}
