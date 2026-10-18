// One function per backend endpoint (PHASE1_PLAN.md §5.4).
import type {
  CvConfirmed,
  CvDraft,
  CvVersion,
  HealthResponse,
  HowResponse,
  LoginResponse,
  MeResponse,
  Place,
  PostingDetail,
  SearchDetail,
  SearchSummary,
  User,
} from "@/lib/types";
import { json, request } from "./client";

export { ApiError, API_URL, getToken, setToken, setUnauthorizedHandler } from "./client";

export const api = {
  health: () => request<HealthResponse>("/health"),

  login: (name: string) => request<LoginResponse>("/api/auth/login", json("POST", { name })),
  logout: () => request<void>("/api/auth/logout", { method: "POST" }),

  me: () => request<MeResponse>("/api/me"),
  saveSettings: (titles: string[], places: Place[]) =>
    request<User>("/api/me/settings", json("PUT", { titles, places })),
  deleteMe: () => request<void>("/api/me", { method: "DELETE" }),

  places: (q: string) => request<Place[]>(`/api/places?q=${encodeURIComponent(q)}`),

  uploadCvFile: (file: File) => {
    const form = new FormData();
    form.append("file", file);
    return request<CvDraft>("/api/cv", { method: "POST", body: form });
  },
  uploadCvText: (text: string) => {
    const form = new FormData();
    form.append("text", text);
    return request<CvDraft>("/api/cv", { method: "POST", body: form });
  },
  confirmCv: (id: number, text: string) =>
    request<CvConfirmed>(`/api/cv/${id}`, json("PUT", { text })),
  cvVersions: () => request<CvVersion[]>("/api/cv"),
  deleteCv: (id: number) => request<void>(`/api/cv/${id}`, { method: "DELETE" }),

  startSearch: (cv_version_id: number, titles: string[], places: Place[]) =>
    request<{ search_id: number }>("/api/searches", json("POST", { cv_version_id, titles, places })),
  history: () => request<SearchSummary[]>("/api/searches"),
  search: (id: number) => request<SearchDetail>(`/api/searches/${id}`),
  rerun: (id: number) => request<{ search_id: number }>(`/api/searches/${id}/rerun`, { method: "POST" }),

  posting: (postingId: number, searchId: number) =>
    request<PostingDetail>(`/api/postings/${postingId}?search_id=${searchId}`),
  how: (searchId: number) => request<HowResponse>(`/api/how/${searchId}`),
};
