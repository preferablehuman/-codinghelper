from enum import StrEnum


class JobStatus(StrEnum):
    PENDING = "PENDING"
    NORMALIZING_PROBLEM = "NORMALIZING_PROBLEM"
    MATCHING_LOCAL_KNOWLEDGE = "MATCHING_LOCAL_KNOWLEDGE"
    REUSING_VERIFIED_SOLUTION = "REUSING_VERIFIED_SOLUTION"
    ADAPTING_REUSED_SOLUTION = "ADAPTING_REUSED_SOLUTION"
    SEARCHING_EXTERNAL_KNOWLEDGE = "SEARCHING_EXTERNAL_KNOWLEDGE"
    INGESTING_EXTERNAL_KNOWLEDGE = "INGESTING_EXTERNAL_KNOWLEDGE"
    VERIFYING_RETRIEVED_SOLUTION = "VERIFYING_RETRIEVED_SOLUTION"
    GENERATING_FROM_GROUNDED_SOLUTION = "GENERATING_FROM_GROUNDED_SOLUTION"
    PROMOTING_KNOWLEDGE = "PROMOTING_KNOWLEDGE"
    ANALYZING = "ANALYZING"
    RETRIEVING_SOURCES = "RETRIEVING_SOURCES"
    BUILDING_EVIDENCE = "BUILDING_EVIDENCE"
    GENERATING_SOLUTION = "GENERATING_SOLUTION"
    GENERATING_TESTS = "GENERATING_TESTS"
    VERIFYING = "VERIFYING"
    REPAIRING = "REPAIRING"
    GENERATING_EXPLANATION = "GENERATING_EXPLANATION"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


STATUS_PROGRESS = {
    JobStatus.PENDING: (5, "Queued"),
    JobStatus.NORMALIZING_PROBLEM: (8, "Normalizing problem"),
    JobStatus.MATCHING_LOCAL_KNOWLEDGE: (10, "Matching reusable knowledge"),
    JobStatus.REUSING_VERIFIED_SOLUTION: (30, "Reusing verified solution"),
    JobStatus.ADAPTING_REUSED_SOLUTION: (35, "Adapting verified solution"),
    JobStatus.SEARCHING_EXTERNAL_KNOWLEDGE: (20, "Searching approved external knowledge"),
    JobStatus.INGESTING_EXTERNAL_KNOWLEDGE: (28, "Ingesting compliant knowledge"),
    JobStatus.VERIFYING_RETRIEVED_SOLUTION: (70, "Reverifying retrieved solution"),
    JobStatus.GENERATING_FROM_GROUNDED_SOLUTION: (52, "Building from verified knowledge"),
    JobStatus.PROMOTING_KNOWLEDGE: (97, "Promoting verified knowledge"),
    JobStatus.ANALYZING: (12, "Analyzing problem"),
    JobStatus.RETRIEVING_SOURCES: (24, "Retrieving approved sources"),
    JobStatus.BUILDING_EVIDENCE: (38, "Building evidence pack"),
    JobStatus.GENERATING_SOLUTION: (52, "Generating solution"),
    JobStatus.GENERATING_TESTS: (64, "Generating tests"),
    JobStatus.VERIFYING: (74, "Verifying generated code"),
    JobStatus.REPAIRING: (82, "Repairing failed solution"),
    JobStatus.GENERATING_EXPLANATION: (88, "Generating explanation"),
    JobStatus.COMPLETED: (100, "Completed"),
    JobStatus.FAILED: (100, "Failed"),
}
