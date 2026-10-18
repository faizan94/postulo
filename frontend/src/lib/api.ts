import type {
  CVResponse,
  HealthResponse,
  Preferences,
  Profile,
  SearchResponse,
} from "./types";

// Inlined at build time. In Docker this is a build arg (see frontend/Dockerfile).
export const API_URL = (
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"
).replace(/\/$/, "");

export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
    public code?: string,
  ) {
    super(message);
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${API_URL}${path}`, init);
  } catch {
    throw new ApiError(
      `Cannot reach the backend at ${API_URL}. Is it running?`,
      0,
      "network_error",
    );
  }
  const body = await res.json().catch(() => null);
  if (!res.ok) {
    // Backend errors: {"error": {code, message}}; FastAPI validation: {"detail": ...}
    const message =
      body?.error?.message ??
      (typeof body?.detail === "string"
        ? body.detail
        : body?.detail?.[0]?.msg) ??
      `Request failed (HTTP ${res.status})`;
    throw new ApiError(message, res.status, body?.error?.code);
  }
  return body as T;
}

export function getHealth(): Promise<HealthResponse> {
  return request<HealthResponse>("/health");
}

export function uploadCv(file: File, prompt: string): Promise<CVResponse> {
  const form = new FormData();
  form.append("file", file);
  form.append("prompt", prompt);
  return request<CVResponse>("/api/cv", { method: "POST", body: form });
}

export function searchJobs(
  profile: Profile,
  preferences: Preferences,
): Promise<SearchResponse> {
  return request<SearchResponse>("/api/jobs/search", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ profile, preferences }),
  });
}
