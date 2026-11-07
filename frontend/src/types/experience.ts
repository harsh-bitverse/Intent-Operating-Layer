/**
 * TypeScript types for IOL v0.6 Experience Engine.
 * Matches backend ExperiencePlan, component catalog, and simulation data structures.
 */

export type ExperienceMode = 'INLINE_VISUAL' | 'EXPANDABLE_VISUAL' | 'FULL_WORKSPACE';

export interface ExperienceComponent {
  id: string;
  type: string; // 'workspace_layout' | 'metric_strip' | 'data_grid' | 'interactive_canvas_2d' | 'evidence_drawer' | etc.
  props: Record<string, any>;
  children?: string[];
}

export interface ExperiencePlan {
  plan_id: string;
  task_id: string;
  mode: ExperienceMode;
  title: string;
  subtitle?: string;
  status: string; // 'ACTIVE' | 'COMPLETED' | 'FAILED'
  components: ExperienceComponent[];
  metadata?: Record<string, any>;
}

export interface MetricItem {
  label: string;
  value: string | number;
  unit?: string;
  badge_color?: 'blue' | 'green' | 'emerald' | 'purple' | 'amber' | 'cyan' | 'gray';
}

export interface DataGridColumn {
  key: string;
  header: string;
  type: 'text' | 'badge' | 'number' | 'link' | 'score';
}

export interface NeuralNode {
  id: string;
  label: string;
  layer: 'input' | 'hidden' | 'output';
  value: number;
  bias?: number;
  x: number;
  y: number;
}

export interface NeuralEdge {
  id: string;
  source: string;
  target: string;
  weight: number;
  gradient?: number;
  animated?: boolean;
}

export interface NeuralSimulationStep {
  step_idx: number;
  phase: string;
  description: string;
  activations: Record<string, number>;
  active_layer: string;
  loss: number;
  weights: Record<string, number>;
  formula: string;
}

export interface NeuralCanvasProps {
  title?: string;
  architecture?: {
    input_nodes: number;
    hidden_nodes: number;
    output_nodes: number;
  };
  nodes?: NeuralNode[];
  edges?: NeuralEdge[];
  current_step?: number;
  total_steps?: number;
  steps_detail?: NeuralSimulationStep[];
  initial_loss?: number;
  final_loss?: number;
  explanation?: string;
}
