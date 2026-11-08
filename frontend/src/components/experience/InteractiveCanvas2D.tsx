'use client';

import React, { useState, useEffect } from 'react';
import { NeuralCanvasProps, NeuralSimulationStep } from '../../types/experience';

export default function InteractiveCanvas2D({
  title = 'Interactive 2D Neural Network Learning Simulation',
  architecture,
  nodes: initialNodes = [],
  edges: initialEdges = [],
  current_step: defaultStep = 0,
  steps_detail = [],
  initial_loss = 0.500,
  final_loss = 0.041,
  explanation = ''
}: NeuralCanvasProps) {
  const [currentStep, setCurrentStep] = useState<number>(defaultStep);
  const [isPlaying, setIsPlaying] = useState<boolean>(false);
  const [inputX1, setInputX1] = useState<number>(0.5);
  const [inputX2, setInputX2] = useState<number>(0.8);
  const [learningRate, setLearningRate] = useState<number>(0.1);

  const totalSteps = steps_detail.length || 5;

  // Auto-play timer
  useEffect(() => {
    let interval: NodeJS.Timeout | null = null;
    if (isPlaying) {
      interval = setInterval(() => {
        setCurrentStep((prev) => {
          if (prev >= totalSteps - 1) {
            setIsPlaying(false);
            return prev;
          }
          return prev + 1;
        });
      }, 1500);
    }
    return () => {
      if (interval) clearInterval(interval);
    };
  }, [isPlaying, totalSteps]);

  const activeStepDetail: NeuralSimulationStep | undefined = steps_detail[currentStep] || {
    step_idx: currentStep,
    phase: currentStep === 0 ? '1. Input Layer Feeding' : currentStep === totalSteps - 1 ? '5. Parameter Update & Loss Reduction' : `Step ${currentStep + 1}`,
    description: 'Propagating activations and calculating gradients.',
    activations: { x1: inputX1, x2: inputX2, h1: 0.701, h2: 0.490, y_out: 0.570 },
    active_layer: currentStep === 0 ? 'input' : currentStep === 1 ? 'hidden' : currentStep === 2 ? 'output' : 'backward',
    loss: currentStep >= 4 ? final_loss : initial_loss,
    weights: { w_x1_h1: 0.45, w_x1_h2: -0.32, w_x2_h1: 0.78, w_x2_h2: 0.15, w_h1_y: 0.85, w_h2_y: -0.65 },
    formula: 'W := W - η · ∇_W L'
  };

  const isCustomGraph =
    (architecture as any)?.type === 'DIJKSTRA_GRAPH' ||
    (architecture as any)?.type === 'GRAPH_SIMULATION' ||
    (initialNodes && initialNodes.length > 0 && !initialNodes.some((n: any) => n.id === 'x1'));

  // Dynamic weights from current step
  const weightsMap = activeStepDetail.weights || {};

  // Node positions on the 2D canvas (adaptive for arbitrary topologies)
  const nodeLayout = isCustomGraph
    ? initialNodes.map((n: any, idx: number) => {
        const count = initialNodes.length;
        const cx = n.cx ?? n.x ?? (count <= 6 ? 120 + (idx % 3) * 250 : 100 + (idx % 4) * 180);
        const cy = n.cy ?? n.y ?? (count <= 6 ? 130 + Math.floor(idx / 3) * 160 : 100 + Math.floor(idx / 4) * 120);
        const rawVal = activeStepDetail.activations?.[n.id] ?? (activeStepDetail as any).distances?.[n.id] ?? n.value ?? n.val ?? '';
        return {
          id: n.id,
          label: n.label || n.id,
          layer: n.layer || (idx === 0 ? 'input' : idx === count - 1 ? 'output' : 'hidden'),
          cx,
          cy,
          val: rawVal,
          bias: n.bias,
        };
      })
    : [
        { id: 'x1', label: 'Input x₁', layer: 'input', cx: 120, cy: 120, val: activeStepDetail.activations?.x1 ?? inputX1 },
        { id: 'x2', label: 'Input x₂', layer: 'input', cx: 120, cy: 280, val: activeStepDetail.activations?.x2 ?? inputX2 },
        { id: 'h1', label: 'Hidden h₁', layer: 'hidden', cx: 380, cy: 120, val: activeStepDetail.activations?.h1 ?? 0.701, bias: 0.1 },
        { id: 'h2', label: 'Hidden h₂', layer: 'hidden', cx: 380, cy: 280, val: activeStepDetail.activations?.h2 ?? 0.490, bias: -0.2 },
        { id: 'y_out', label: 'Output ŷ', layer: 'output', cx: 640, cy: 200, val: activeStepDetail.activations?.y_out ?? 0.570, bias: 0.05 },
      ];

  const edges = isCustomGraph
    ? (initialEdges || []).map((e: any, idx: number) => {
        const srcNode = nodeLayout.find((n) => n.id === (e.source || e.src || e.x1_id));
        const tgtNode = nodeLayout.find((n) => n.id === (e.target || e.dst || e.x2_id));
        const x1 = e.x1 ?? (srcNode ? srcNode.cx : 120);
        const y1 = e.y1 ?? (srcNode ? srcNode.cy : 120);
        const x2 = e.x2 ?? (tgtNode ? tgtNode.cx : 380);
        const y2 = e.y2 ?? (tgtNode ? tgtNode.cy : 120);
        const rawW = weightsMap[e.id] ?? e.weight ?? e.w ?? 1.0;
        return {
          id: e.id || `edge_${idx}`,
          x1,
          y1,
          x2,
          y2,
          w: typeof rawW === 'number' ? rawW : 1.0,
          label: e.label || (typeof rawW === 'number' ? (rawW > 0 ? `+${rawW.toFixed(2)}` : rawW.toFixed(2)) : String(rawW)),
        };
      })
    : [
        { id: 'e1', x1: 120, y1: 120, x2: 380, y2: 120, w: weightsMap.w_x1_h1 ?? 0.45 },
        { id: 'e2', x1: 120, y1: 120, x2: 380, y2: 280, w: weightsMap.w_x1_h2 ?? -0.32 },
        { id: 'e3', x1: 120, y1: 280, x2: 380, y2: 120, w: weightsMap.w_x2_h1 ?? 0.78 },
        { id: 'e4', x1: 120, y1: 280, x2: 380, y2: 280, w: weightsMap.w_x2_h2 ?? 0.15 },
        { id: 'e5', x1: 380, y1: 120, x2: 640, y2: 200, w: weightsMap.w_h1_y ?? 0.85 },
        { id: 'e6', x1: 380, y1: 280, x2: 640, y2: 200, w: weightsMap.w_h2_y ?? -0.65 },
      ];

  const handleStepForward = () => {
    if (currentStep < totalSteps - 1) {
      setCurrentStep(currentStep + 1);
    }
  };

  const handleStepBack = () => {
    if (currentStep > 0) {
      setCurrentStep(currentStep - 1);
    }
  };

  const handleReset = () => {
    setIsPlaying(false);
    setCurrentStep(0);
  };

  const archType = (activeStepDetail as any).architecture_type || (isCustomGraph ? 'Graph Topology & Algorithm Simulation' : '2-Layer Perceptron (2-2-1)');
  const metricLabel = (activeStepDetail as any).metric_label || 'Loss';
  const metricVal = (activeStepDetail as any).metric_value ?? (activeStepDetail.loss !== undefined ? (activeStepDetail.loss ?? initial_loss).toFixed(4) : 'Optimal');

  return (
    <div className="bg-slate-900 border border-slate-700/80 rounded-xl p-5 shadow-2xl space-y-5" data-testid="interactive-canvas-2d">
      {/* Header & Status */}
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-slate-800 pb-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-cyan-400 animate-pulse" />
            <h3 className="text-lg font-semibold text-white tracking-wide">{title}</h3>
            <span className="px-2 py-0.5 text-xs font-mono bg-cyan-950/80 text-cyan-300 border border-cyan-800/60 rounded">
              {archType}
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            {explanation || 'Interactive 2D graph computation with real mathematical state transitions and step-by-step playback.'}
          </p>
        </div>

        {/* Step Badges */}
        <div className="flex items-center gap-2">
          <div className="px-3 py-1 bg-slate-800/90 border border-slate-700 rounded-lg text-xs font-mono text-slate-300">
            Step <span className="text-cyan-400 font-bold">{currentStep + 1}</span> of {totalSteps}
          </div>
          <div className="px-3 py-1 bg-slate-800/90 border border-slate-700 rounded-lg text-xs font-mono text-slate-300">
            {metricLabel}: <span className="font-bold text-emerald-400 font-mono">{String(metricVal)}</span>
          </div>
        </div>
      </div>

      {/* SVG Canvas */}
      <div className="relative w-full bg-slate-950 border border-slate-800 rounded-xl overflow-hidden shadow-inner flex items-center justify-center p-2">
        <svg viewBox="0 0 760 400" className="w-full h-auto max-h-[420px] select-none">
          <defs>
            <linearGradient id="gradInput" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor="#38bdf8" />
              <stop offset="100%" stopColor="#0284c7" />
            </linearGradient>
            <linearGradient id="gradHidden" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor="#a855f7" />
              <stop offset="100%" stopColor="#7e22ce" />
            </linearGradient>
            <linearGradient id="gradOutput" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor="#10b981" />
              <stop offset="100%" stopColor="#047857" />
            </linearGradient>
            <filter id="glow" x="-20%" y="-20%" width="140%" height="140%">
              <feGaussianBlur stdDeviation="6" result="blur" />
              <feComposite in="SourceGraphic" in2="blur" operator="over" />
            </filter>
          </defs>

          {/* Layer Background Guides for neural net; subtle grid for custom graph */}
          {!isCustomGraph ? (
            <>
              <rect x="70" y="40" width="100" height="320" rx="8" fill="#0f172a" fillOpacity="0.4" stroke="#1e293b" strokeDasharray="3 3" />
              <text x="120" y="65" textAnchor="middle" fill="#64748b" fontSize="11" fontWeight="600" letterSpacing="1">INPUT LAYER</text>

              <rect x="330" y="40" width="100" height="320" rx="8" fill="#0f172a" fillOpacity="0.4" stroke="#1e293b" strokeDasharray="3 3" />
              <text x="380" y="65" textAnchor="middle" fill="#64748b" fontSize="11" fontWeight="600" letterSpacing="1">HIDDEN LAYER</text>

              <rect x="590" y="40" width="100" height="320" rx="8" fill="#0f172a" fillOpacity="0.4" stroke="#1e293b" strokeDasharray="3 3" />
              <text x="640" y="65" textAnchor="middle" fill="#64748b" fontSize="11" fontWeight="600" letterSpacing="1">OUTPUT LAYER</text>
            </>
          ) : (
            <g opacity="0.15">
              <line x1="0" y1="100" x2="760" y2="100" stroke="#475569" strokeDasharray="4 4" />
              <line x1="0" y1="200" x2="760" y2="200" stroke="#475569" strokeDasharray="4 4" />
              <line x1="0" y1="300" x2="760" y2="300" stroke="#475569" strokeDasharray="4 4" />
              <line x1="190" y1="0" x2="190" y2="400" stroke="#475569" strokeDasharray="4 4" />
              <line x1="380" y1="0" x2="380" y2="400" stroke="#475569" strokeDasharray="4 4" />
              <line x1="570" y1="0" x2="570" y2="400" stroke="#475569" strokeDasharray="4 4" />
            </g>
          )}

          {/* Edges (Synapses / Connections) */}
          {edges.map((e) => {
            const isPositive = e.w >= 0;
            const strokeColor = isPositive ? '#10b981' : '#f43f5e';
            const midX = (e.x1 + e.x2) / 2;
            const midY = (e.y1 + e.y2) / 2;
            return (
              <g key={e.id}>
                <line
                  x1={e.x1}
                  y1={e.y1}
                  x2={e.x2}
                  y2={e.y2}
                  stroke={strokeColor}
                  strokeWidth={Math.min(Math.max(Math.abs(e.w) * 4, 1.5), 6)}
                  strokeOpacity={0.65}
                  strokeLinecap="round"
                />
                {/* Weight Label Badge */}
                <rect
                  x={midX - 18}
                  y={midY - 8}
                  width="36"
                  height="16"
                  rx="4"
                  fill="#090d16"
                  stroke="#334155"
                  strokeWidth="1"
                />
                <text
                  x={midX}
                  y={midY + 4}
                  textAnchor="middle"
                  fill={isPositive ? '#34d399' : '#fb7185'}
                  fontSize="9"
                  fontFamily="monospace"
                  fontWeight="600"
                >
                  {e.w > 0 ? `+${e.w.toFixed(2)}` : e.w.toFixed(2)}
                </text>
              </g>
            );
          })}

          {/* Nodes (Neurons) */}
          {nodeLayout.map((node) => {
            const isActiveLayer =
              (node.layer === 'input' && (activeStepDetail.active_layer === 'input' || currentStep === 0)) ||
              (node.layer === 'hidden' && (activeStepDetail.active_layer === 'hidden' || currentStep === 1)) ||
              (node.layer === 'output' && (activeStepDetail.active_layer === 'output' || currentStep >= 2));

            const gradId =
              node.layer === 'input'
                ? 'url(#gradInput)'
                : node.layer === 'hidden'
                ? 'url(#gradHidden)'
                : 'url(#gradOutput)';

            return (
              <g key={node.id} className="transition-all duration-300">
                {/* Glow ring if active */}
                {isActiveLayer && (
                  <circle
                    cx={node.cx}
                    cy={node.cy}
                    r={36}
                    fill="none"
                    stroke={node.layer === 'input' ? '#38bdf8' : node.layer === 'hidden' ? '#a855f7' : '#10b981'}
                    strokeWidth="3"
                    strokeOpacity="0.8"
                    filter="url(#glow)"
                  />
                )}

                {/* Main Circle */}
                <circle
                  cx={node.cx}
                  cy={node.cy}
                  r={28}
                  fill={gradId}
                  stroke="#0f172a"
                  strokeWidth="2.5"
                />

                {/* Node Label */}
                <text
                  x={node.cx}
                  y={node.cy - 5}
                  textAnchor="middle"
                  fill="#ffffff"
                  fontSize="12"
                  fontWeight="bold"
                >
                  {node.label}
                </text>

                {/* Activation Value */}
                <text
                  x={node.cx}
                  y={node.cy + 13}
                  textAnchor="middle"
                  fill="#f1f5f9"
                  fontSize="11"
                  fontFamily="monospace"
                >
                  {typeof node.val === 'number' ? node.val.toFixed(3) : node.val}
                </text>

                {/* Bias indicator for hidden/output */}
                {node.bias !== undefined && (
                  <text
                    x={node.cx}
                    y={node.cy + 42}
                    textAnchor="middle"
                    fill="#94a3b8"
                    fontSize="9"
                    fontFamily="monospace"
                  >
                    b = {node.bias > 0 ? `+${node.bias}` : node.bias}
                  </text>
                )}
              </g>
            );
          })}
        </svg>
      </div>

      {/* Narrative & Mathematical Explanation Box */}
      <div className="bg-slate-950/80 border border-slate-800 rounded-xl p-4 space-y-2">
        <div className="flex items-center justify-between">
          <span className="text-xs uppercase tracking-wider text-cyan-400 font-bold font-mono">
            {activeStepDetail.phase}
          </span>
          <span className="text-xs font-mono bg-slate-900 text-slate-300 px-2 py-0.5 rounded border border-slate-800">
            Formula: {activeStepDetail.formula}
          </span>
        </div>
        <p className="text-sm text-slate-300 leading-relaxed">
          {activeStepDetail.description}
        </p>

        {currentStep === totalSteps - 1 && (
          <div className="mt-3 p-3 bg-emerald-950/40 border border-emerald-800/60 rounded-lg flex items-center justify-between text-xs text-emerald-300">
            <span>🎉 Gradient Descent Convergence: Loss decreased by {(initial_loss - final_loss).toFixed(4)}</span>
            <span className="font-mono font-bold">New MSE = {final_loss.toFixed(4)}</span>
          </div>
        )}
      </div>

      {/* Controller & Interactive Sliders */}
      <div className="flex flex-wrap items-center justify-between gap-4 pt-2">
        {/* Step Buttons */}
        <div className="flex items-center gap-2">
          <button
            onClick={handleReset}
            data-testid="sim-reset"
            className="px-3 py-1.5 text-xs font-medium text-slate-300 bg-slate-800 hover:bg-slate-700 rounded-lg transition"
            title="Reset to Step 1"
          >
            ⏮ Reset
          </button>
          <button
            onClick={handleStepBack}
            disabled={currentStep === 0}
            data-testid="sim-step-back"
            className="px-3 py-1.5 text-xs font-medium text-slate-300 bg-slate-800 hover:bg-slate-700 disabled:opacity-40 disabled:cursor-not-allowed rounded-lg transition"
          >
            ◀ Step Back
          </button>
          <button
            onClick={() => setIsPlaying(!isPlaying)}
            data-testid="sim-autoplay"
            className={`px-4 py-1.5 text-xs font-semibold rounded-lg transition shadow flex items-center gap-1.5 ${
              isPlaying
                ? 'bg-amber-600 hover:bg-amber-500 text-white'
                : 'bg-cyan-600 hover:bg-cyan-500 text-white'
            }`}
          >
            {isPlaying ? '⏸ Pause' : '▶ Auto Play'}
          </button>
          <button
            onClick={handleStepForward}
            disabled={currentStep >= totalSteps - 1}
            data-testid="sim-step-forward"
            className="px-3 py-1.5 text-xs font-medium text-slate-300 bg-slate-800 hover:bg-slate-700 disabled:opacity-40 disabled:cursor-not-allowed rounded-lg transition"
          >
            Step Forward ▶
          </button>
        </div>

        {/* Feature Sliders or Graph Metadata */}
        {!isCustomGraph ? (
          <div className="flex items-center gap-4 text-xs font-mono text-slate-300 bg-slate-950/60 p-2 rounded-lg border border-slate-800">
            <div className="flex items-center gap-2">
              <span>x₁:</span>
              <input
                type="range"
                min="0.0"
                max="1.0"
                step="0.05"
                value={inputX1}
                onChange={(e) => setInputX1(parseFloat(e.target.value))}
                className="w-16 accent-sky-400 cursor-pointer"
              />
              <span className="text-sky-300 font-bold">{inputX1.toFixed(2)}</span>
            </div>

            <div className="flex items-center gap-2">
              <span>x₂:</span>
              <input
                type="range"
                min="0.0"
                max="1.0"
                step="0.05"
                value={inputX2}
                onChange={(e) => setInputX2(parseFloat(e.target.value))}
                className="w-16 accent-sky-400 cursor-pointer"
              />
              <span className="text-sky-300 font-bold">{inputX2.toFixed(2)}</span>
            </div>

            <div className="flex items-center gap-2 border-l border-slate-800 pl-3">
              <span>η (LR):</span>
              <span className="text-cyan-300 font-bold">0.10</span>
            </div>
          </div>
        ) : (
          <div className="flex items-center gap-3 text-xs font-mono text-slate-300 bg-slate-950/60 p-2 rounded-lg border border-slate-800">
            <span className="text-slate-400">Topology:</span>
            <span className="text-cyan-300 font-bold">{nodeLayout.length} Vertices</span>
            <span className="text-slate-600">|</span>
            <span className="text-cyan-300 font-bold">{edges.length} Edges</span>
            {(activeStepDetail as any).active_vertex && (
              <>
                <span className="text-slate-600">|</span>
                <span className="text-emerald-400 font-semibold">Active: {(activeStepDetail as any).active_vertex}</span>
              </>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
