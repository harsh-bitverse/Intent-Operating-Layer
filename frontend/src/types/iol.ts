export type TaskStatus = 
  | 'PENDING'
  | 'RUNNING'
  | 'COMPLETED'
  | 'FAILED'
  | 'CANCELLED'
  | 'PAUSED_FOR_APPROVAL';

export interface ExecutionBudget {
  max_duration_seconds: number;
  max_steps: number;
  max_cost_usd: number;
  retry_limit: number;
}

export interface CardMetric {
  label: string;
  value: string | number;
  unit?: string;
  change?: string;
}

export interface CardComponent {
  type: 'card';
  id: string;
  title: string;
  subtitle?: string;
  variant: 'default' | 'highlight' | 'warning' | 'success' | 'info';
  metrics: CardMetric[];
  badges: string[];
  content?: string;
}

export interface TableColumn {
  key: string;
  header: string;
  type: 'text' | 'badge' | 'number' | 'link' | 'score';
  format?: string;
}

export interface TableComponent {
  type: 'table';
  id: string;
  title: string;
  subtitle?: string;
  columns: TableColumn[];
  rows: Record<string, any>[];
  total_count?: number;
}

export interface TimelineItem {
  id: string;
  title: string;
  description?: string;
  status: 'pending' | 'running' | 'success' | 'failed' | 'skipped';
  timestamp?: string;
  metadata?: Record<string, any>;
}

export interface TimelineComponent {
  type: 'timeline';
  id: string;
  title: string;
  items: TimelineItem[];
}

export interface FieldEvidence {
  field_name: string;
  field_value: any;
  evidence_url?: string;
  source_type: 'DIRECT_API_FIELD' | 'BIBLIOGRAPHIC_PROFILE' | 'OFFICIAL_WEBSITE' | 'HTML_TITLE' | 'DOM_SNIPPET' | 'INFERRED_CONTEXT' | 'UNKNOWN';
  relevant_excerpt?: string;
  retrieval_timestamp: string;
  verification_method: string;
  verification_status: 'DIRECTLY_SUPPORTED' | 'DERIVED' | 'INFERRED' | 'UNKNOWN' | 'UNSUPPORTED';
  confidence: number;
}

export interface ComparisonEntity {
  entity_id: string;
  name: string;
  subtitle?: string;
  badge?: string;
  primary_metric?: string;
  url?: string;
}

export interface ComparisonFeature {
  key: string;
  label: string;
  values: Record<string, any>;
  winner_entity_id?: string;
  confidence_tier?: string;
}

export interface ComparisonComponent {
  type: 'comparison';
  id: string;
  title: string;
  subtitle?: string;
  entities: ComparisonEntity[];
  features: ComparisonFeature[];
}

export type UIComponent = CardComponent | TableComponent | TimelineComponent | ComparisonComponent;

export interface DeclarativeUIRoot {
  title: string;
  summary?: string;
  components: UIComponent[];
  last_updated: string;
}

export interface Task {
  task_id: string;
  user_id?: string;
  intent: string;
  status: TaskStatus;
  created_at: string;
  started_at?: string;
  completed_at?: string;
  budget: ExecutionBudget;
  current_step: number;
  total_steps: number;
  error_message?: string;
  retry_count: number;
  result?: Record<string, any>;
  ui_state?: DeclarativeUIRoot;
  metadata: Record<string, any>;
}

export interface TaskEvent {
  event_id: number;
  task_id: string;
  event_type: string;
  timestamp: string;
  data: Record<string, any>;
}

export interface CapabilityMetadata {
  capability_id: string;
  name: string;
  description: string;
  version: string;
  required_permissions: string[];
  input_schema: Record<string, any>;
  output_schema: Record<string, any>;
  verification_metadata: Record<string, any>;
  estimated_cost_usd: number;
}
