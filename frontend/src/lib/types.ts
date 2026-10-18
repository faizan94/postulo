// Mirrors backend/app/schemas/*.py. Change both together.

export type PlaceKind = "city" | "country" | "remote";
export interface Place {
  kind: PlaceKind;
  name: string;
  country_code: string | null;
}
export interface Evidence {
  quote: string;
}

export interface HealthResponse {
  status: "ok";
  version: string;
  mock_mode: boolean;
  nebius_configured: boolean;
  tavily_configured: boolean;
  model: string;
  fast_model: string;
  vision_model: string;
  ocr_enabled: boolean;
}

// --- auth ---
export interface User {
  id: number;
  name: string;
  default_titles: string[];
  default_places: Place[];
}
export interface LoginResponse {
  token: string;
  user: User;
}
export interface MeResponse {
  user: User;
  has_cv: boolean;
  latest_search_id: number | null;
}

// --- profile ---
export interface SkillItem {
  name: string;
  type: "tech" | "soft" | "domain";
  evidence: Evidence;
  inferred: boolean;
}
export interface Role {
  title: string;
  company: string;
  start: string | null;
  end: string | null;
  evidence: Evidence;
}
export interface LanguageItem {
  name: string;
  level: string | null;
  evidence: Evidence;
}
export interface Profile {
  headline: string | null;
  summary: string | null;
  skills: SkillItem[];
  roles: Role[];
  languages: LanguageItem[];
  education: { school: string; degree: string | null; evidence: Evidence }[];
  place: Place | null;
  years_total: number | null;
  seniority: "junior" | "mid" | "senior" | "lead" | null;
  target_titles: string[];
}

// --- cv ---
export type SourceType = "pdf" | "docx" | "image" | "text";
export interface CvVersion {
  id: number;
  label: string;
  source_type: SourceType;
  ocr_used: boolean;
  status: "draft" | "confirmed";
  created_at: string;
  confirmed_at: string | null;
}
export interface CvDraft {
  cv_version_id: number;
  text: string;
  ocr_used: boolean;
  warnings: string[];
}
export interface CvConfirmed {
  cv_version: CvVersion;
  profile: Profile;
  suggested: { titles: string[]; place: Place | null };
  warnings: string[];
}

// --- postings and scores ---
export type RequirementType = "tech" | "soft" | "domain" | "language" | "years" | "degree";
export type SkillStatus = "have" | "related" | "missing_nice" | "missing_must";
export type CompanyBand = "strong" | "okay" | "weak" | "not_enough_data" | "pending";
export type WorkplaceType = "onsite" | "hybrid" | "remote";

export interface Requirement {
  name: string;
  type: RequirementType;
  importance: "must" | "nice";
  level: string | null;
  min_years: number | null;
  evidence: Evidence;
}
export interface SkillMatch {
  requirement: Requirement;
  status: SkillStatus;
  cv_evidence: Evidence | null;
}
export interface MatchScore {
  value: number | null;
  must_met: string;
  nice_met: string;
  gates_applied: string[];
  thin: boolean;
}
export interface CompanyScore {
  value: number | null;
  band: CompanyBand;
  sources: { title: string; url: string; date: string | null }[];
}
export interface JobCard {
  posting_id: number;
  title: string;
  company: string;
  place: Place | null;
  workplace_type: WorkplaceType | null;
  posted_at: string | null;
  match: MatchScore;
  company_score: CompanyScore;
  top_skills: SkillMatch[];
}
export interface PostingDetail {
  posting_id: number;
  title: string;
  company: string;
  place: Place | null;
  workplace_type: WorkplaceType | null;
  posted_at: string | null;
  url: string;
  apply_url: string;
  full_text: string;
  match: MatchScore;
  skills: SkillMatch[];
  company_score: CompanyScore;
}

// --- searches ---
export type SearchStatus = "queued" | "running" | "done" | "failed";
export type Stage =
  | "planning"
  | "searching"
  | "checking"
  | "reading"
  | "matching"
  | "company"
  | "ranking";

export interface SkillSummaryItem {
  skill: string;
  user_status: "have" | "related" | "missing";
  demand: number;
  of: number;
  must_count: number;
}
export interface LearnNextItem {
  skill: string;
  jobs_improved: number;
  avg_gain_points: number;
  unlocks: number;
  slow: boolean;
}
export interface SearchSummary {
  id: number;
  status: SearchStatus;
  cv_version_id: number | null;
  titles: string[];
  places: Place[];
  result_count: number;
  created_at: string;
  finished_at: string | null;
}
export interface SearchDetail extends SearchSummary {
  stage: Stage | null;
  note: string | null;
  error: string | null;
  results: JobCard[];
  skill_summary: SkillSummaryItem[];
  learn_next: LearnNextItem[];
}
export interface HowResponse {
  search_id: number;
  trace: { at: string; stage: Stage; message: string; data: Record<string, unknown> }[];
  dropped: { title: string; company: string | null; url: string; reason: string }[];
  usage: { tavily_credits: number; llm_calls: number };
}

export type SearchEvent =
  | { type: "snapshot"; search: SearchDetail }
  | { type: "stage"; stage: Stage; message: string }
  | { type: "job"; card: JobCard }
  | { type: "company"; posting_id: number; company_score: CompanyScore }
  | { type: "note"; message: string }
  | { type: "done"; search_id: number }
  | { type: "error"; message: string };
