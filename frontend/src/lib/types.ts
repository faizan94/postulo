// Mirrors backend/app/models/schemas.py. Keep the two in sync.

export type SkillStatus = "gold" | "orange" | "red";
export type LocationPref = "Berlin" | "Germany" | "World";

export interface Profile {
  name?: string | null;
  headline?: string | null;
  summary?: string | null;
  skills: string[];
  years?: number | null;
  languages: string[];
  target_roles: string[];
  location_pref?: LocationPref | null;
}

export interface Preferences {
  location: LocationPref;
  prompt: string;
}

export interface Skill {
  name: string;
  status: SkillStatus;
  note?: string | null;
}

export interface VerifiedFlags {
  company_exists: boolean;
  posting_live: boolean;
  recent: boolean;
}

export interface Posting {
  title: string;
  company: string;
  url: string;
  posted?: string | null;
  location?: string | null;
  source?: string | null;
  verified: VerifiedFlags;
  score: number;
  skills: Skill[];
  why: string;
}

export interface RejectedPosting {
  title: string;
  company?: string | null;
  url: string;
  reason: string;
}

export interface AgentStep {
  agent: "orchestrator" | "search" | "verify" | "score";
  message: string;
  duration_ms?: number | null;
}

export interface CVResponse {
  profile: Profile;
  cv_text_chars: number;
  mock: boolean;
}

export interface SearchResponse {
  profile: Profile;
  postings: Posting[];
  rejected: RejectedPosting[];
  trace: AgentStep[];
  mock: boolean;
}

export interface HealthResponse {
  status: "ok";
  version: string;
  mock_mode: boolean;
  nebius_configured: boolean;
  tavily_configured: boolean;
  model: string;
}
