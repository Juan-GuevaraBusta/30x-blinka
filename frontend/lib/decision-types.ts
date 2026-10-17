export type Decision = "PAGAR" | "ESCALAR" | "FRENAR";

export type CheckResultKind = "OK" | "FALLA" | "INDETERMINADO";

export type FailAction = "FRENAR" | "ESCALAR";

export type CheckEvidence = {
  clause: string | null;
  quote: string | null;
};

export type CheckResult = {
  rule: string;
  name: string;
  result: CheckResultKind;
  detail: string;
  on_fail?: FailAction | null;
  evidence?: CheckEvidence | null;
};

export type FxQuote = {
  rate: number;
  date: string;
};

export type LineItem = {
  description: string;
  amount?: number | null;
  source_span?: string | null;
};

export type Extraction = {
  beneficiary?: string | null;
  amount?: number | null;
  currency?: string | null;
  amount_base?: number | null;
  fx?: FxQuote | null;
  due_date?: string | null;
  invoice_number?: string | null;
  recipient?: string | null;
  department?: string | null;
  invoice_type?: string | null;
  lines?: LineItem[];
  source_spans?: Record<string, string>;
};

export type JevSignal = {
  id: string;
  answer: boolean | string;
  probability: number;
};

export type VerifierIssue = {
  code: string;
  kind: "violation" | "uncertainty";
  evidence?: string | null;
  admin_message?: string | null;
};

export type VerifierReport = {
  consistent: boolean;
  issues: VerifierIssue[];
};

export type TraceRef = {
  langsmith_run_id?: string | null;
  url?: string | null;
};

export type ModelVersions = {
  rules_version: string;
  model_extractor: string;
  model_verifier: string;
  jev: string;
};

export type HumanEvent = {
  author: string;
  at: string;
  action: "aprobada_humano" | "rechazada_humano";
  reason: string;
};

export type DecisionRecord = {
  id: string;
  invoice_id: string;
  received_at: string;
  decision: Decision;
  severity: 0 | 1 | 2;
  summary: string;
  extracted: Extraction;
  checks: CheckResult[];
  jev_signals: JevSignal[];
  verifier: VerifierReport;
  admin_notice: string | null;
  next_step: string;
  trace: TraceRef;
  versions: ModelVersions;
  human_events: HumanEvent[];
};
