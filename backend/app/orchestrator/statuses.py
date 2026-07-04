from enum import StrEnum


class JobStatus(StrEnum):
    PENDING = "PENDING"
    ANALYZING = "ANALYZING"
    RETRIEVING_SOURCES = "RETRIEVING_SOURCES"
    BUILDING_EVIDENCE = "BUILDING_EVIDENCE"
    GENERATING_SOLUTION = "GENERATING_SOLUTION"
    GENERATING_TESTS = "GENERATING_TESTS"
    VERIFYING = "VERIFYING"
    REPAIRING = "REPAIRING"
    GENERATING_EXPLANATION = "GENERATING_EXPLANATION"
    GENERATING_SLIDES = "GENERATING_SLIDES"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


STATUS_PROGRESS = {
    JobStatus.PENDING: (5, "Queued"),
    JobStatus.ANALYZING: (12, "Analyzing problem"),
    JobStatus.RETRIEVING_SOURCES: (24, "Retrieving approved sources"),
    JobStatus.BUILDING_EVIDENCE: (38, "Building evidence pack"),
    JobStatus.GENERATING_SOLUTION: (52, "Generating solution"),
    JobStatus.GENERATING_TESTS: (64, "Generating tests"),
    JobStatus.VERIFYING: (74, "Verifying generated code"),
    JobStatus.REPAIRING: (82, "Repairing failed solution"),
    JobStatus.GENERATING_EXPLANATION: (88, "Generating explanation"),
    JobStatus.GENERATING_SLIDES: (94, "Generating slides"),
    JobStatus.COMPLETED: (100, "Completed"),
    JobStatus.FAILED: (100, "Failed"),
}

