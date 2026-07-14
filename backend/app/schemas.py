from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class JobCreate(BaseModel):
    title: str | None = None
    problem_text: str = Field(min_length=10)
    language: str = "java"
    source_urls: list[str] = Field(default_factory=list)


class JobCreated(BaseModel):
    job_id: str
    status: str


class JobStatusResponse(BaseModel):
    job_id: str
    status: str
    progress_percent: int
    current_step: str
    error_message: str | None = None


class JobListItem(BaseModel):
    id: str
    title: str | None
    language: str
    difficulty: str | None
    status: str
    progress_percent: int
    current_step: str
    detected_pattern: str | None
    created_at: datetime
    completed_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


class SourceDocumentOut(BaseModel):
    id: str
    title: str
    url: str
    source_name: str
    source_tier: int
    license_note: str | None
    retrieval_method: str
    is_cache_allowed: bool

    model_config = ConfigDict(from_attributes=True)


class EvidenceItemOut(BaseModel):
    id: str
    claim: str
    support_score: float
    source_chunk_id: str | None

    model_config = ConfigDict(from_attributes=True)


class GeneratedSolutionOut(BaseModel):
    id: str
    approach_type: str
    algorithm_pattern: str
    explanation: str
    pseudocode: str
    code: str
    time_complexity: str
    space_complexity: str
    verification_status: str | None = None

    model_config = ConfigDict(from_attributes=True)


class TestCaseOut(BaseModel):
    id: str
    input_data: str
    expected_output: str | None
    test_type: str

    model_config = ConfigDict(from_attributes=True)


class VerificationRunOut(BaseModel):
    id: str
    solution_id: str
    status: str
    stdout: str
    stderr: str
    execution_time_ms: int
    memory_used_mb: int | None
    passed_count: int
    failed_count: int

    model_config = ConfigDict(from_attributes=True)


class ExplanationOut(BaseModel):
    id: str
    intuition: str
    brute_force: str
    optimized_approach: str
    dry_run: str
    pitfalls: str
    complexity_analysis: str

    model_config = ConfigDict(from_attributes=True)


class PatternSourceRef(BaseModel):
    title: str
    url: str
    source_name: str
    source_tier: int


class PatternLessonOut(BaseModel):
    id: str
    pattern_key: str
    display_name: str
    overview: str
    mental_model: str
    recognition_cues: str
    core_operations: str
    invariants: str
    worked_example: str
    implementation_guide: str
    complexity_tradeoffs: str
    pitfalls: str
    related_patterns: str
    evidence_summary: str
    source_refs: list[PatternSourceRef] = Field(default_factory=list)
    created_from_job_id: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PatternLessonResolution(BaseModel):
    lesson: PatternLessonOut
    reused: bool


class SlideArtifactOut(BaseModel):
    id: str
    markdown_path: str
    html_path: str | None
    pdf_path: str | None
    pptx_path: str | None

    model_config = ConfigDict(from_attributes=True)


class RetrievalTraceOut(BaseModel):
    route: str
    match_type: str
    confidence: float = 0.0
    reused_prior_solution: bool = False
    external_discovery_used: bool = False
    canonical_source_count: int = 0
    related_source_count: int = 0
    verification_status: str | None = None
    asserting_test_count: int = 0
    code_adapted: bool = False
    source_titles: list[str] = Field(default_factory=list)


class JobDetail(BaseModel):
    id: str
    title: str | None
    problem_text: str
    language: str
    difficulty: str | None
    status: str
    progress_percent: int
    current_step: str
    error_message: str | None
    detected_pattern: str | None
    problem_summary: str | None
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None
    sources: list[SourceDocumentOut] = Field(default_factory=list)
    evidence_items: list[EvidenceItemOut] = Field(default_factory=list)
    solutions: list[GeneratedSolutionOut] = Field(default_factory=list)
    test_cases: list[TestCaseOut] = Field(default_factory=list)
    verification_runs: list[VerificationRunOut] = Field(default_factory=list)
    explanations: list[ExplanationOut] = Field(default_factory=list)
    slide_artifacts: list[SlideArtifactOut] = Field(default_factory=list)
    retrieval_trace: RetrievalTraceOut | None = None

    model_config = ConfigDict(from_attributes=True)


class CodeExecutionTest(BaseModel):
    input: str = ""
    expected_output: str | None = None


class CodeExecutionRequest(BaseModel):
    language: str = "java"
    code: str = Field(min_length=1)
    input: str = ""
    expected_output: str | None = None
    tests: list[CodeExecutionTest] | None = None
    timeout_seconds: int = Field(default=5, ge=1, le=10)
    memory_mb: int = Field(default=256, ge=64, le=1024)


class CodeExecutionResponse(BaseModel):
    status: str
    passed_count: int
    failed_count: int
    results: list[dict[str, object]] = Field(default_factory=list)
    average_execution_time_ms: float | None = None
