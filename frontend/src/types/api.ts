export type JobStatus =
  | "PENDING"
  | "ANALYZING"
  | "RETRIEVING_SOURCES"
  | "BUILDING_EVIDENCE"
  | "GENERATING_SOLUTION"
  | "GENERATING_TESTS"
  | "VERIFYING"
  | "REPAIRING"
  | "GENERATING_EXPLANATION"
  | "GENERATING_SLIDES"
  | "COMPLETED"
  | "FAILED";

export interface JobCreate {
  title?: string;
  problem_text: string;
  language: string;
  difficulty?: string;
  source_urls: string[];
}

export interface JobCreated {
  job_id: string;
  status: JobStatus;
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
}

export interface TestCase {
  id: string;
  input_data: string;
  expected_output: string | null;
  test_type: string;
}

export interface VerificationRun {
  id: string;
  status: string;
  stdout: string;
  stderr: string;
  execution_time_ms: number;
  memory_used_mb: number | null;
  passed_count: number;
  failed_count: number;
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
}
