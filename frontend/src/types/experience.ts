/**
 * TypeScript types for IOL v0.6 / Task 008 Experience Engine.
 * Matches backend ExperiencePlan, component catalog, OutcomeEnvelopeV1, and Action approvals.
 */

export type ExperienceMode = 'INLINE_VISUAL' | 'EXPANDABLE_VISUAL' | 'FULL_WORKSPACE';

export interface ExperienceComponent {
  id: string;
  type: string; // 'workspace_layout' | 'metric_strip' | 'data_grid' | 'comparison_matrix' | 'interactive_canvas_2d' | 'form_draft' | 'timeline_view' | 'action_panel'
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
  version?: number;
  plan_origin?: 'MODEL_GENERATED' | 'TEST_SYNTHESIZED' | 'RECIPE_ADAPTED' | 'DETERMINISTIC_FALLBACK' | 'KNOWLEDGE_ADAPTED';
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

// ---------------------------------------------------------------------------
// OutcomeEnvelopeV1 & Provenance Types
// ---------------------------------------------------------------------------

export type OutcomeShape =
  | 'collection'
  | 'comparison'
  | 'document'
  | 'form'
  | 'timeline'
  | 'graph'
  | 'simulation'
  | 'single_answer'
  | 'partial'
  | 'blocked';

export type SourceMode =
  | 'LIVE_API'
  | 'LIVE_BROWSER'
  | 'LOCAL_COMPUTATION'
  | 'USER_SUPPLIED'
  | 'RECORDED_REPLAY'
  | 'TEST_FIXTURE';

export interface OutcomeFieldSchema {
  name: string;
  data_type: 'string' | 'number' | 'boolean' | 'url' | 'date' | 'object' | 'list';
  required?: boolean;
  description?: string;
}

export interface OutcomeEvidenceRecord {
  field_name: string;
  field_value?: any;
  source_type: string;
  evidence_url?: string;
  retrieval_timestamp: string;
  verification_method: string;
  verification_status: 'DIRECTLY_SUPPORTED' | 'DERIVED' | 'INFERRED' | 'UNKNOWN' | 'UNSUPPORTED';
  relevant_excerpt?: string;
  confidence: number;
}

export interface OutcomeItem {
  id: string;
  data: Record<string, any>;
  evidence: Record<string, OutcomeEvidenceRecord>;
}

export interface OutcomeEnvelope {
  schema_version: '1.0';
  shape: OutcomeShape;
  source_mode: SourceMode;
  item_schema: OutcomeFieldSchema[];
  items: OutcomeItem[];
  metadata: Record<string, any>;
  created_at: string;
  updated_at: string;
  integrity_hash?: string;
}

// ---------------------------------------------------------------------------
// Browser Observation & Telemetry Types
// ---------------------------------------------------------------------------

export interface BrowserElementSummary {
  tag: string;
  text: string;
  selector?: string;
  href?: string;
  interactive: boolean;
}

export interface BrowserObservationData {
  url: string;
  title: string;
  http_status: number;
  screenshot_path?: string;
  thumbnail_base64?: string;
  accessible_elements_count?: number;
  blocker_detected?: boolean;
  blocker_type?: string;
  interactive_elements?: BrowserElementSummary[];
  text_content_snippet?: string;
}

// ---------------------------------------------------------------------------
// Scoped Action Approval Types
// ---------------------------------------------------------------------------

export type ActionEffect =
  | 'READ'
  | 'LOCAL_DRAFT'
  | 'EXTERNAL_WRITE'
  | 'PAYMENT_OR_ORDER'
  | 'DESTRUCTIVE';

export interface ActionApprovalTicket {
  ticket_id: string;
  task_id: string;
  action_id: string;
  action_type: string;
  effect: ActionEffect;
  target_url?: string;
  parameters_hash: string;
  created_at: string;
  expires_at: string;
  hmac_signature: string;
}

export interface TaskActionRequest {
  action_id: string;
  action_type: string;
  effect: ActionEffect;
  target_url?: string;
  parameters: Record<string, any>;
  explanation: string;
  ticket?: ActionApprovalTicket;
}

// ---------------------------------------------------------------------------
// Timeline View Component Props
// ---------------------------------------------------------------------------

export interface TimelineItem {
  id: string;
  title: string;
  description?: string;
  timestamp?: string;
  status?: 'completed' | 'active' | 'pending' | 'failed';
  badge?: string;
  metadata?: Record<string, any>;
}

export interface TimelineViewProps {
  title?: string;
  subtitle?: string;
  items: TimelineItem[];
  current_stage?: string;
}

// ---------------------------------------------------------------------------
// Document Preview Component Props
// ---------------------------------------------------------------------------

export interface DocumentSection {
  heading: string;
  text: string;
}

export interface DocumentPreviewProps {
  title?: string;
  document_type?: string;
  content?: string;
  sections?: DocumentSection[];
  metadata?: Record<string, any>;
  download_url?: string;
}

