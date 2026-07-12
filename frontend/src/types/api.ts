export type JobStatus =
  | "PENDING"
  | "NORMALIZING_PROBLEM"
  | "MATCHING_LOCAL_KNOWLEDGE"
  | "REUSING_VERIFIED_SOLUTION"
  | "ADAPTING_REUSED_SOLUTION"
  | "SEARCHING_EXTERNAL_KNOWLEDGE"
  | "INGESTING_EXTERNAL_KNOWLEDGE"
  | "VERIFYING_RETRIEVED_SOLUTION"
  | "GENERATING_FROM_GROUNDED_SOLUTION"
  | "PROMOTING_KNOWLEDGE"
  | "ANALYZING"
  | "RETRIEVING_SOURCES"
  | "BUILDING_EVIDENCE"
  | "GENERATING_SOLUTION"
  | "GENERATING_TESTS"
  | "VERIFYING"
  | "REPAIRING"
  | "GENERATING_EXPLANATION"
  | "COMPLETED"
  | "FAILED";

export interface JobCreate {
  title?: string;
  problem_text: string;
  language: string;
  source_urls: string[];
}

export interface JobCreated {
  job_id: string;
  status: JobStatus;
}

export interface HealthResponse {
  status: string;
  service: string;
  database: string;
  model_provider: string;
  model_gateway?: string;
  model: {
    loaded?: boolean;
    provider?: string;
    model?: string;
    display_name?: string | null;
    remote?: boolean;
    gateway_status?: string;
    error?: string | null;
  };
}

export interface JobStatusResponse {
  job_id: string;
  status: JobStatus;
  progress_percent: number;
  current_step: string;
  error_message: string | null;
}

export interface JobListItem {
  id: string;
  title: string | null;
  language: string;
  difficulty: string | null;
  status: JobStatus;
  progress_percent: number;
  current_step: string;
  detected_pattern: string | null;
  created_at: string;
  completed_at: string | null;
}

export interface SourceDocument {
  id: string;
  title: string;
  url: string;
  source_name: string;
  source_tier: number;
  license_note: string | null;
  retrieval_method: string;
  is_cache_allowed: boolean;
}

export interface EvidenceItem {
  id: string;
  claim: string;
  support_score: number;
  source_chunk_id: string | null;
}

export interface GeneratedSolution {
  id: string;
  approach_type: string;
  algorithm_pattern: string;
  explanation: string;
  pseudocode: string;
  code: string;
  time_complexity: string;
  space_complexity: string;
  verification_status: string | null;
}

export interface TestCase {
  id: string;
  input_data: string;
  expected_output: string | null;
  test_type: string;
}

export interface VerificationRun {
  id: string;
  solution_id: string;
  status: string;
  stdout: string;
  stderr: string;
  execution_time_ms: number;
  memory_used_mb: number | null;
  passed_count: number;
  failed_count: number;
}

export interface ExecutionRequest {
  language: string;
  code: string;
  input: string;
  expected_output: string | null;
  tests?: Array<{
    input: string;
    expected_output: string | null;
  }>;
  timeout_seconds?: number;
  memory_mb?: number;
}

export interface ExecutionResultItem {
  test_index: number;
  status: string;
  stdout: string;
  stderr: string;
  execution_time_ms: number;
}

export interface ExecutionResponse {
  status: string;
  passed_count: number;
  failed_count: number;
  results: ExecutionResultItem[];
  average_execution_time_ms: number | null;
}

export interface Explanation {
  id: string;
  intuition: string;
  brute_force: string;
  optimized_approach: string;
  dry_run: string;
  pitfalls: string;
  complexity_analysis: string;
}

export interface SlideArtifact {
  id: string;
  markdown_path: string;
  html_path: string | null;
  pdf_path: string | null;
  pptx_path: string | null;
}

export interface JobDetail extends JobListItem {
  problem_text: string;
  error_message: string | null;
  problem_summary: string | null;
  updated_at: string;
  sources: SourceDocument[];
  evidence_items: EvidenceItem[];
  solutions: GeneratedSolution[];
  test_cases: TestCase[];
  verification_runs: VerificationRun[];
  explanations: Explanation[];
  slide_artifacts: SlideArtifact[];
  retrieval_trace: {
    route: string;
    match_type: string;
    confidence: number;
    reused_prior_solution: boolean;
    external_discovery_used: boolean;
    canonical_source_count: number;
    related_source_count: number;
    verification_status: string | null;
    asserting_test_count: number;
    code_adapted: boolean;
    source_titles: string[];
  } | null;
}
