'use client';

import React, { useEffect, useState } from 'react';

interface ProviderConfig {
  provider_id: string;
  provider_type: string;
  display_name: string;
  base_url: string;
  has_api_key: boolean;
  key_hint: string;
  default_model: string;
  available_models: string[];
  capabilities: string[];
  is_local: boolean;
  is_enabled: boolean;
  timeout_seconds: number;
}

interface LocalDiskModel {
  model_id: string;
  name: string;
  tag: string;
  size_bytes: number;
  size_mb: number;
  manifest_file: string;
}

interface RoutingPolicy {
  role: string;
  primary_provider_id: string;
  fallback_provider_id?: string;
  allow_cloud: boolean;
  allow_local: boolean;
  max_latency_ms: number;
  require_structured_output: boolean;
}

interface DiagnosticResult {
  provider_id: string;
  provider_type: string;
  status: 'HEALTHY' | 'UNHEALTHY' | 'BLOCKED' | 'OFFLINE';
  is_connected: boolean;
  latency_ms?: number;
  discovered_models: string[];
  message: string;
  error_reason?: string;
}

interface ModelSettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
  apiUrl: string;
  headers: Record<string, string>;
}

export const ModelSettingsModal: React.FC<ModelSettingsModalProps> = ({
  isOpen,
  onClose,
  apiUrl,
  headers,
}) => {
  const [activeTab, setActiveTab] = useState<'providers' | 'local_models' | 'routing'>('providers');
  const [providers, setProviders] = useState<ProviderConfig[]>([]);
  const [localModels, setLocalModels] = useState<LocalDiskModel[]>([]);
  const [policies, setPolicies] = useState<Record<string, RoutingPolicy>>({});
  const [diagnostics, setDiagnostics] = useState<Record<string, DiagnosticResult>>({});
  const [testingProvider, setTestingProvider] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);

  // Edit provider modal state
  const [editingProvider, setEditingProvider] = useState<ProviderConfig | null>(null);
  const [editBaseUrl, setEditBaseUrl] = useState('');
  const [editDefaultModel, setEditDefaultModel] = useState('');
  const [editApiKey, setEditApiKey] = useState('');
  const [editError, setEditError] = useState<string | null>(null);

  const fetchData = async () => {
    setLoading(true);
    try {
      // 1. Providers
      const provRes = await fetch(`${apiUrl}/api/models/providers`, { headers });
      if (provRes.ok) {
        setProviders(await provRes.json());
      }

      // 2. Local disk models
      const localRes = await fetch(`${apiUrl}/api/models/local`, { headers });
      if (localRes.ok) {
        setLocalModels(await localRes.json());
      }

      // 3. Routing policies
      const routeRes = await fetch(`${apiUrl}/api/models/routes`, { headers });
      if (routeRes.ok) {
        setPolicies(await routeRes.json());
      }
    } catch (err) {
      console.error('Failed to fetch model settings data:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (isOpen) {
      fetchData();
    }
  }, [isOpen]);

  const handleTestProvider = async (providerId: string) => {
    setTestingProvider(providerId);
    setStatusMessage(null);
    try {
      const res = await fetch(`${apiUrl}/api/models/providers/${providerId}/test`, {
        method: 'POST',
        headers,
      });
      if (res.ok) {
        const diag: DiagnosticResult = await res.json();
        setDiagnostics((prev) => ({ ...prev, [providerId]: diag }));
      } else {
        const err = await res.json();
        setDiagnostics((prev) => ({
          ...prev,
          [providerId]: {
            provider_id: providerId,
            provider_type: 'unknown',
            status: 'UNHEALTHY',
            is_connected: false,
            discovered_models: [],
            message: err.detail || 'Test request failed',
          },
        }));
      }
    } catch (err: any) {
      setDiagnostics((prev) => ({
        ...prev,
        [providerId]: {
          provider_id: providerId,
          provider_type: 'unknown',
          status: 'UNHEALTHY',
          is_connected: false,
          discovered_models: [],
          message: err.message || 'Network error during test',
        },
      }));
    } finally {
      setTestingProvider(null);
    }
  };

  const handleOpenEdit = (p: ProviderConfig) => {
    setEditingProvider(p);
    setEditBaseUrl(p.base_url);
    setEditDefaultModel(p.default_model);
    setEditApiKey('');
    setEditError(null);
  };

  const handleSaveProvider = async () => {
    if (!editingProvider) return;
    setEditError(null);

    const payload = {
      provider_id: editingProvider.provider_id,
      provider_type: editingProvider.provider_type,
      display_name: editingProvider.display_name,
      base_url: editBaseUrl,
      api_key: editApiKey.trim() ? editApiKey.trim() : undefined,
      default_model: editDefaultModel,
      available_models: editingProvider.available_models,
      capabilities: editingProvider.capabilities,
      is_local: editingProvider.is_local,
      is_enabled: editingProvider.is_enabled,
      timeout_seconds: editingProvider.timeout_seconds,
    };

    try {
      const res = await fetch(`${apiUrl}/api/models/providers`, {
        method: 'POST',
        headers,
        body: JSON.stringify(payload),
      });

      if (res.ok) {
        setEditingProvider(null);
        setStatusMessage(`Provider '${editingProvider.provider_id}' successfully updated.`);
        fetchData();
      } else {
        const err = await res.json();
        setEditError(err.detail || 'Failed to update provider configuration.');
      }
    } catch (e: any) {
      setEditError(e.message || 'Network error saving provider.');
    }
  };

  const handleUpdatePolicy = async (role: string, field: string, value: any) => {
    const curr = policies[role];
    if (!curr) return;
    const updated: RoutingPolicy = { ...curr, [field]: value };
    setPolicies((prev) => ({ ...prev, [role]: updated }));

    try {
      await fetch(`${apiUrl}/api/models/routes`, {
        method: 'PUT',
        headers,
        body: JSON.stringify(updated),
      });
      setStatusMessage(`Routing policy for [${role}] updated.`);
    } catch (err) {
      console.error('Failed to update policy:', err);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 backdrop-blur-sm p-4 overflow-y-auto">
      <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-4xl max-h-[90vh] flex flex-col shadow-2xl overflow-hidden">
        {/* Header */}
        <div className="px-6 py-4 border-b border-slate-800 flex items-center justify-between bg-slate-900/80">
          <div className="flex items-center space-x-3">
            <div className="h-8 w-8 rounded-lg bg-blue-600/20 border border-blue-500/30 flex items-center justify-center text-blue-400">
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
              </svg>
            </div>
            <div>
              <h2 className="text-base font-bold text-white">Universal Model Provider & Routing Architecture</h2>
              <p className="text-xs text-slate-400">Configure foundation model runtimes, SSRF safeguards, local weights, and role routing.</p>
            </div>
          </div>
          <button
            onClick={onClose}
            aria-label="Close modal"
            className="text-slate-400 hover:text-white p-1 rounded-lg hover:bg-slate-800 transition"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Security Banner */}
        <div className="px-6 py-2.5 bg-blue-950/40 border-b border-blue-900/30 flex items-center justify-between text-xs text-blue-300">
          <div className="flex items-center space-x-2">
            <span className="h-2 w-2 rounded-full bg-emerald-400" />
            <span className="font-mono text-[11px]">SSRF Boundary Active: Loopback restricted to local model ports (11434, 18080). Internal ports (8000, 3000, 5432, 6379) and cloud metadata blocked.</span>
          </div>
          <span className="font-mono text-[10px] text-blue-400/80 uppercase">Key Masking Enforced</span>
        </div>

        {/* Tab Navigation */}
        <div className="px-6 pt-3 border-b border-slate-800 flex space-x-6">
          <button
            onClick={() => setActiveTab('providers')}
            className={`pb-3 text-xs font-semibold border-b-2 transition ${
              activeTab === 'providers'
                ? 'border-blue-500 text-blue-400'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            Registered Providers ({providers.length})
          </button>
          <button
            onClick={() => setActiveTab('local_models')}
            className={`pb-3 text-xs font-semibold border-b-2 transition ${
              activeTab === 'local_models'
                ? 'border-blue-500 text-blue-400'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            Local Weights On Disk ({localModels.length})
          </button>
          <button
            onClick={() => setActiveTab('routing')}
            className={`pb-3 text-xs font-semibold border-b-2 transition ${
              activeTab === 'routing'
                ? 'border-blue-500 text-blue-400'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            Functional Role Routing ({Object.keys(policies).length})
          </button>
        </div>

        {/* Status Toast */}
        {statusMessage && (
          <div className="mx-6 mt-3 p-2 bg-emerald-950/40 border border-emerald-800/40 rounded-lg text-emerald-300 text-xs flex justify-between items-center">
            <span>{statusMessage}</span>
            <button onClick={() => setStatusMessage(null)} className="text-emerald-400 hover:text-emerald-200 text-xs ml-4">✕</button>
          </div>
        )}

        {/* Body Content */}
        <div className="p-6 overflow-y-auto flex-1 space-y-4">
          {/* TAB 1: Registered Providers */}
          {activeTab === 'providers' && (
            <div className="space-y-4">
              {providers.map((p) => {
                const diag = diagnostics[p.provider_id];
                const isTesting = testingProvider === p.provider_id;
                return (
                  <div
                    key={p.provider_id}
                    data-testid={`provider-card-${p.provider_id}`}
                    className="p-4 rounded-xl bg-slate-950/60 border border-slate-800 hover:border-slate-700/80 transition space-y-3"
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center space-x-3">
                        <div className="h-8 w-8 rounded-lg bg-slate-800 flex items-center justify-center font-bold text-xs text-white">
                          {p.provider_id.slice(0, 2).toUpperCase()}
                        </div>
                        <div>
                          <div className="flex items-center space-x-2">
                            <h3 className="text-sm font-semibold text-white">{p.display_name}</h3>
                            <span className="font-mono text-[10px] text-slate-400 px-1.5 py-0.5 rounded bg-slate-800">
                              {p.provider_type}
                            </span>
                            {p.is_local && (
                              <span className="font-mono text-[10px] text-emerald-400 px-1.5 py-0.5 rounded bg-emerald-950/50 border border-emerald-800/30">
                                LOCAL RUNTIME
                              </span>
                            )}
                          </div>
                          <p className="text-[11px] font-mono text-slate-400 truncate max-w-md">{p.base_url}</p>
                        </div>
                      </div>

                      <div className="flex items-center space-x-2">
                        <button
                          data-testid={`test-btn-${p.provider_id}`}
                          onClick={() => handleTestProvider(p.provider_id)}
                          disabled={isTesting}
                          className="px-3 py-1.5 bg-blue-600/20 hover:bg-blue-600/30 border border-blue-500/30 text-blue-300 rounded-lg text-xs font-medium transition disabled:opacity-50"
                        >
                          {isTesting ? 'Testing...' : 'Test Connection'}
                        </button>
                        <button
                          data-testid={`config-btn-${p.provider_id}`}
                          onClick={() => handleOpenEdit(p)}
                          className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg text-xs font-medium transition"
                        >
                          Configure
                        </button>
                      </div>
                    </div>

                    {/* Metadata strip */}
                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 pt-2 border-t border-slate-800/60 text-xs">
                      <div>
                        <span className="text-slate-500 text-[10px] uppercase block">Default Model</span>
                        <span className="font-mono text-slate-200 text-xs">{p.default_model}</span>
                      </div>
                      <div>
                        <span className="text-slate-500 text-[10px] uppercase block">Credential Status</span>
                        <span className="font-mono text-slate-200 text-xs">{p.key_hint || (p.has_api_key ? 'Configured' : 'None')}</span>
                      </div>
                      <div>
                        <span className="text-slate-500 text-[10px] uppercase block">Capabilities</span>
                        <span className="text-slate-300 text-[11px] truncate block">
                          {p.capabilities.join(', ') || 'General inference'}
                        </span>
                      </div>
                      <div>
                        <span className="text-slate-500 text-[10px] uppercase block">State</span>
                        <span className={`text-[11px] font-bold ${p.is_enabled ? 'text-emerald-400' : 'text-slate-400'}`}>
                          {p.is_enabled ? 'ENABLED' : 'DISABLED'}
                        </span>
                      </div>
                    </div>

                    {/* Diagnostic Result Panel */}
                    {diag && (
                      <div
                        className={`p-2.5 rounded-lg text-xs border font-mono ${
                          diag.status === 'HEALTHY'
                            ? 'bg-emerald-950/20 border-emerald-800/40 text-emerald-300'
                            : diag.status === 'BLOCKED'
                            ? 'bg-amber-950/20 border-amber-800/40 text-amber-300'
                            : 'bg-red-950/20 border-red-800/40 text-red-300'
                        }`}
                      >
                        <div className="flex items-center justify-between">
                          <span className="font-bold">[{diag.status}] {diag.message}</span>
                          {diag.latency_ms !== undefined && <span>{diag.latency_ms} ms</span>}
                        </div>
                        {diag.discovered_models && diag.discovered_models.length > 0 && (
                          <div className="mt-1 text-[11px] text-slate-400">
                            Available models: {diag.discovered_models.slice(0, 6).join(', ')}
                            {diag.discovered_models.length > 6 && ` (+${diag.discovered_models.length - 6} more)`}
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}

          {/* TAB 2: Local Disk Models */}
          {activeTab === 'local_models' && (
            <div className="space-y-4">
              <div className="p-3 bg-slate-950/60 border border-slate-800 rounded-xl text-xs text-slate-300 space-y-1">
                <p className="font-semibold text-white">Pre-downloaded GGUF Model Assets in ~/.ollama/models</p>
                <p className="text-slate-400">
                  These weights are already present on your local drive. When Ollama is started on port 11434,
                  IOL can run 100% private local inference across these models with zero latency or cloud API dependency.
                </p>
              </div>

              {localModels.length === 0 ? (
                <div className="p-8 text-center text-slate-500 text-xs">No local Ollama models found in ~/.ollama/models</div>
              ) : (
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  {localModels.map((m) => (
                    <div
                      key={m.model_id}
                      className="p-3.5 bg-slate-950/60 border border-slate-800 rounded-xl space-y-2"
                    >
                      <div className="flex items-center justify-between">
                        <span className="font-mono font-bold text-sm text-blue-400">{m.model_id}</span>
                        <span className="px-2 py-0.5 rounded bg-blue-950/50 border border-blue-800/40 text-[10px] font-mono text-blue-300">
                          {m.size_mb} MB
                        </span>
                      </div>
                      <div className="text-[11px] text-slate-400 font-mono space-y-0.5">
                        <div>Model Base: {m.name}</div>
                        <div>Tag: {m.tag}</div>
                        <div className="truncate text-slate-500">Manifest: {m.manifest_file}</div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* TAB 3: Functional Role Routing */}
          {activeTab === 'routing' && (
            <div className="space-y-3">
              <div className="p-3 bg-slate-950/60 border border-slate-800 rounded-xl text-xs text-slate-300">
                <p className="font-semibold text-white">Subsystem Role-Based Model Routing & Automated Fallback</p>
                <p className="text-slate-400 text-[11px]">
                  Configure which foundation model handles each distinct IOL subsystem role. If the primary model fails or is unconfigured,
                  IOL automatically fails over to the designated fallback provider without disrupting active user intent execution.
                </p>
              </div>

              <div className="divide-y divide-slate-800/60 border border-slate-800 rounded-xl overflow-hidden bg-slate-950/40">
                {Object.entries(policies).map(([roleKey, policy]) => (
                  <div key={roleKey} data-testid={`routing-role-${roleKey}`} className="p-3.5 flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs">
                    <div>
                      <span className="font-mono font-semibold text-white block uppercase text-[11px]">{roleKey}</span>
                      <span className="text-[11px] text-slate-400">
                        {roleKey === 'experience_synthesis' && 'Synthesizes generative ExperiencePlans and UI layouts'}
                        {roleKey === 'planning' && 'Formulates multi-step autonomous execution graphs'}
                        {roleKey === 'browser_reasoning' && 'Interprets live DOM states and plans interactive actions'}
                        {roleKey === 'intent_understanding' && 'Parses user objectives and shapes target outcomes'}
                        {roleKey === 'verification' && 'Validates structured outcomes and evidence integrity'}
                        {roleKey === 'knowledge_extraction' && 'Extracts structural signatures for recipe adaptation'}
                      </span>
                    </div>

                    <div className="flex items-center space-x-3 shrink-0">
                      <div>
                        <span className="text-[9px] uppercase text-slate-500 block">Primary</span>
                        <select
                          value={policy.primary_provider_id}
                          onChange={(e) => handleUpdatePolicy(roleKey, 'primary_provider_id', e.target.value)}
                          className="bg-slate-900 border border-slate-700 rounded px-2 py-1 text-xs text-white"
                        >
                          {providers.map((p) => (
                            <option key={p.provider_id} value={p.provider_id}>
                              {p.display_name}
                            </option>
                          ))}
                        </select>
                      </div>

                      <div>
                        <span className="text-[9px] uppercase text-slate-500 block">Fallback</span>
                        <select
                          value={policy.fallback_provider_id || 'mock'}
                          onChange={(e) => handleUpdatePolicy(roleKey, 'fallback_provider_id', e.target.value)}
                          className="bg-slate-900 border border-slate-700 rounded px-2 py-1 text-xs text-white"
                        >
                          {providers.map((p) => (
                            <option key={p.provider_id} value={p.provider_id}>
                              {p.display_name}
                            </option>
                          ))}
                        </select>
                      </div>

                      <div className="flex items-center space-x-2 pt-3">
                        <label className="flex items-center space-x-1 cursor-pointer">
                          <input
                            type="checkbox"
                            checked={policy.allow_cloud}
                            onChange={(e) => handleUpdatePolicy(roleKey, 'allow_cloud', e.target.checked)}
                            className="rounded bg-slate-900 border-slate-700 text-blue-600 focus:ring-0"
                          />
                          <span className="text-[10px] text-slate-400">Cloud</span>
                        </label>
                        <label className="flex items-center space-x-1 cursor-pointer">
                          <input
                            type="checkbox"
                            checked={policy.allow_local}
                            onChange={(e) => handleUpdatePolicy(roleKey, 'allow_local', e.target.checked)}
                            className="rounded bg-slate-900 border-slate-700 text-blue-600 focus:ring-0"
                          />
                          <span className="text-[10px] text-slate-400">Local</span>
                        </label>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Edit Provider Modal Dialog */}
        {editingProvider && (
          <div className="absolute inset-0 bg-slate-950/90 backdrop-blur-sm flex items-center justify-center p-4 z-50">
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 w-full max-w-lg space-y-4 shadow-xl">
              <h3 className="text-sm font-bold text-white">Configure {editingProvider.display_name}</h3>

              {editError && (
                <div className="p-2.5 bg-red-950/40 border border-red-800/40 rounded-lg text-red-300 text-xs">
                  {editError}
                </div>
              )}

              <div className="space-y-3 text-xs">
                <div>
                  <label className="block text-slate-400 mb-1">Base URL (SSRF Protected)</label>
                  <input
                    data-testid="edit-base-url-input"
                    type="text"
                    value={editBaseUrl}
                    onChange={(e) => setEditBaseUrl(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-700 rounded-lg p-2 text-white font-mono text-xs focus:border-blue-500 outline-none"
                  />
                  <p className="text-[10px] text-slate-500 mt-1">Loopback restricted to model ports (11434, 18080). System ports blocked.</p>
                </div>

                <div>
                  <label className="block text-slate-400 mb-1">Default Model Name</label>
                  <input
                    type="text"
                    value={editDefaultModel}
                    onChange={(e) => setEditDefaultModel(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-700 rounded-lg p-2 text-white font-mono text-xs focus:border-blue-500 outline-none"
                  />
                </div>

                <div>
                  <label className="block text-slate-400 mb-1">
                    API Key {editingProvider.has_api_key ? `(Configured: ${editingProvider.key_hint})` : '(Not configured)'}
                  </label>
                  <input
                    type="password"
                    placeholder="Enter new secret key to update, or leave blank to keep current"
                    value={editApiKey}
                    onChange={(e) => setEditApiKey(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-700 rounded-lg p-2 text-white font-mono text-xs focus:border-blue-500 outline-none"
                  />
                  <p className="text-[10px] text-slate-500 mt-1">Keys are stored securely in backend runtime memory and masked in responses.</p>
                </div>
              </div>

              <div className="flex justify-end space-x-2 pt-2 border-t border-slate-800">
                <button
                  onClick={() => setEditingProvider(null)}
                  className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg text-xs font-medium"
                >
                  Cancel
                </button>
                <button
                  data-testid="save-provider-btn"
                  onClick={handleSaveProvider}
                  className="px-3 py-1.5 bg-blue-600 hover:bg-blue-500 text-white rounded-lg text-xs font-medium shadow-md shadow-blue-500/20"
                >
                  Save Configuration
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Footer */}
        <div className="px-6 py-3 border-t border-slate-800 bg-slate-900/60 flex items-center justify-between text-xs text-slate-400">
          <span>Intent Operating Layer Universal Model Infrastructure v1.0</span>
          <button
            onClick={onClose}
            className="px-4 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-lg font-medium transition"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};
