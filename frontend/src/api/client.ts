import type {
  ExecutionRequest,
  ExecutionResponse,
  HealthResponse,
  JobCreate,
  JobCreated,
  JobDetail,
  JobListItem,
  JobStatusResponse
} from "../types/api";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      headers: {
        "content-type": "application/json",
        ...init?.headers
      },
      ...init
    });
  } catch (error) {
    throw new Error(
      "The application API is unavailable. Check that the backend service is running and reachable through the frontend proxy.",
      { cause: error }
    );
  }
  if (!response.ok) {
    const body = await response.text();
    throw new Error(body || `Request failed with ${response.status}`);
  }
  if (response.status === 204) {
    return undefined as T;
  }
  return (await response.json()) as T;
}

export function createJob(payload: JobCreate): Promise<JobCreated> {
  return request<JobCreated>("/api/jobs", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export function getHealth(): Promise<HealthResponse> {
  return request<HealthResponse>("/api/health");
}

export function listJobs(): Promise<JobListItem[]> {
  return request<JobListItem[]>("/api/jobs");
}

export function getJob(jobId: string): Promise<JobDetail> {
  return request<JobDetail>(`/api/jobs/${jobId}`);
}

export function getJobStatus(jobId: string): Promise<JobStatusResponse> {
  return request<JobStatusResponse>(`/api/jobs/${jobId}/status`);
}

export function rerunJob(jobId: string): Promise<JobCreated> {
  return request<JobCreated>(`/api/jobs/${jobId}/rerun`, { method: "POST" });
}

export function deleteJob(jobId: string): Promise<void> {
  return request<void>(`/api/jobs/${jobId}`, { method: "DELETE" });
}

export function executeCode(payload: ExecutionRequest): Promise<ExecutionResponse> {
  return request<ExecutionResponse>("/api/execute", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}
