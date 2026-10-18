"use client";

import { useEffect, useState } from "react";
import { ApiError, getHealth, searchJobs, uploadCv } from "@/lib/api";
import type {
  HealthResponse,
  LocationPref,
  Profile,
  SearchResponse,
} from "@/lib/types";
import { AgentTrace } from "./AgentTrace";
import { PostingCard } from "./PostingCard";
import { SkillDot, STATUS_LABEL } from "./SkillChip";

type Step = "upload" | "preferences" | "results";

const LOCATIONS: { value: LocationPref; label: string; hint: string }[] = [
  { value: "Berlin", label: "Berlin", hint: "City only" },
  { value: "Germany", label: "Germany", hint: "Anywhere in DE" },
  { value: "World", label: "World", hint: "Remote / global" },
];

function errorMessage(e: unknown): string {
  if (e instanceof ApiError) return e.message;
  return e instanceof Error ? e.message : "Something went wrong.";
}

export function PostuloFlow() {
  const [step, setStep] = useState<Step>("upload");
  const [file, setFile] = useState<File | null>(null);
  const [prompt, setPrompt] = useState("");
  const [location, setLocation] = useState<LocationPref>("Berlin");
  const [profile, setProfile] = useState<Profile | null>(null);
  const [result, setResult] = useState<SearchResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [health, setHealth] = useState<HealthResponse | null>(null);

  useEffect(() => {
    getHealth()
      .then(setHealth)
      .catch((e) => setError(errorMessage(e)));
  }, []);

  async function onUpload(e: React.FormEvent) {
    e.preventDefault();
    if (!file) return;
    setLoading(true);
    setError(null);
    try {
      const res = await uploadCv(file, prompt);
      setProfile(res.profile);
      if (res.profile.location_pref) setLocation(res.profile.location_pref);
      setStep("preferences");
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setLoading(false);
    }
  }

  async function onSearch(e: React.FormEvent) {
    e.preventDefault();
    if (!profile) return;
    setLoading(true);
    setError(null);
    try {
      setResult(await searchJobs(profile, { location, prompt }));
      setStep("results");
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setLoading(false);
    }
  }

  function reset() {
    setStep("upload");
    setFile(null);
    setProfile(null);
    setResult(null);
    setError(null);
  }

  return (
    <div className="space-y-6">
      {health?.mock_mode && (
        <div className="rounded-lg border border-amber-300 bg-amber-50 px-4 py-2 text-sm text-amber-900">
          <strong>Mock mode:</strong> the backend returns fake data. Set{" "}
          <code>MOCK_MODE=false</code> and add API keys in <code>.env</code> for
          real searches.
        </div>
      )}

      <Stepper step={step} />

      {error && (
        <div
          role="alert"
          className="rounded-lg border border-red-300 bg-red-50 px-4 py-3 text-sm text-red-800"
        >
          {error}
        </div>
      )}

      {step === "upload" && (
        <form
          onSubmit={onUpload}
          className="space-y-5 rounded-2xl border border-zinc-200 bg-white p-6 shadow-sm"
        >
          <div>
            <h2 className="text-lg font-semibold text-zinc-900">
              1. Upload your CV
            </h2>
            <p className="text-sm text-zinc-500">
              PDF, up to 10 MB. Processed in memory and not stored.
            </p>
          </div>
          <label className="flex cursor-pointer flex-col items-center justify-center gap-2 rounded-xl border-2 border-dashed border-zinc-300 px-6 py-10 text-center hover:border-zinc-400 hover:bg-zinc-50">
            <span className="text-3xl">📄</span>
            <span className="text-sm font-medium text-zinc-800">
              {file ? file.name : "Click to choose a PDF"}
            </span>
            <input
              type="file"
              accept="application/pdf,.pdf"
              className="sr-only"
              onChange={(e) => setFile(e.target.files?.[0] ?? null)}
            />
          </label>
          <div>
            <label
              htmlFor="cv-prompt"
              className="mb-1 block text-sm font-medium text-zinc-800"
            >
              Anything to add? <span className="text-zinc-400">(optional)</span>
            </label>
            <textarea
              id="cv-prompt"
              rows={3}
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              placeholder="I'm looking for a job with X and Y, and these are my strengths..."
              className="w-full rounded-lg border border-zinc-300 px-3 py-2 text-sm focus:border-zinc-500 focus:outline-none"
            />
          </div>
          <PrimaryButton disabled={!file || loading}>
            {loading ? "Reading your CV..." : "Read my CV"}
          </PrimaryButton>
        </form>
      )}

      {step === "preferences" && profile && (
        <form
          onSubmit={onSearch}
          className="space-y-5 rounded-2xl border border-zinc-200 bg-white p-6 shadow-sm"
        >
          <div>
            <h2 className="text-lg font-semibold text-zinc-900">
              2. Where do you want to work?
            </h2>
            <ProfileSummary profile={profile} />
          </div>
          <fieldset>
            <legend className="mb-2 text-sm font-medium text-zinc-800">
              Location
            </legend>
            <div className="grid grid-cols-3 gap-2">
              {LOCATIONS.map((l) => (
                <label
                  key={l.value}
                  className={`cursor-pointer rounded-lg border px-3 py-2 text-center ${
                    location === l.value
                      ? "border-zinc-900 bg-zinc-900 text-white"
                      : "border-zinc-300 hover:bg-zinc-50"
                  }`}
                >
                  <input
                    type="radio"
                    name="location"
                    value={l.value}
                    checked={location === l.value}
                    onChange={() => setLocation(l.value)}
                    className="sr-only"
                  />
                  <span className="block text-sm font-medium">{l.label}</span>
                  <span
                    className={`block text-xs ${location === l.value ? "text-zinc-300" : "text-zinc-500"}`}
                  >
                    {l.hint}
                  </span>
                </label>
              ))}
            </div>
          </fieldset>
          <div>
            <label
              htmlFor="pref-prompt"
              className="mb-1 block text-sm font-medium text-zinc-800"
            >
              What are you interested in?
            </label>
            <textarea
              id="pref-prompt"
              rows={3}
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              placeholder="e.g. data roles in climate tech, hybrid, English-speaking team"
              className="w-full rounded-lg border border-zinc-300 px-3 py-2 text-sm focus:border-zinc-500 focus:outline-none"
            />
          </div>
          <div className="flex items-center gap-3">
            <PrimaryButton disabled={loading}>
              {loading
                ? "Agents searching, verifying, scoring..."
                : "Find verified jobs"}
            </PrimaryButton>
            <button
              type="button"
              onClick={reset}
              className="text-sm text-zinc-500 hover:text-zinc-800"
            >
              Start over
            </button>
          </div>
        </form>
      )}

      {step === "results" && result && (
        <div className="space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <h2 className="text-lg font-semibold text-zinc-900">
              3. {result.postings.length} verified postings for you
            </h2>
            <div className="flex items-center gap-4">
              <Legend />
              <button
                onClick={() => setStep("preferences")}
                className="text-sm text-zinc-500 hover:text-zinc-800"
              >
                Refine
              </button>
              <button
                onClick={reset}
                className="text-sm text-zinc-500 hover:text-zinc-800"
              >
                New CV
              </button>
            </div>
          </div>
          <div className="grid gap-6 lg:grid-cols-[1fr_300px]">
            <div className="space-y-4">
              {result.postings.length === 0 && (
                <p className="rounded-xl border border-zinc-200 bg-white p-6 text-sm text-zinc-600">
                  No verified postings matched. Try a wider location or a
                  different prompt.
                </p>
              )}
              {result.postings.map((p, i) => (
                <PostingCard key={p.url} posting={p} rank={i + 1} />
              ))}
            </div>
            <AgentTrace trace={result.trace} rejected={result.rejected} />
          </div>
        </div>
      )}
    </div>
  );
}

function PrimaryButton({
  children,
  disabled,
}: {
  children: React.ReactNode;
  disabled?: boolean;
}) {
  return (
    <button
      type="submit"
      disabled={disabled}
      className="rounded-lg bg-zinc-900 px-5 py-2.5 text-sm font-semibold text-white hover:bg-zinc-700 disabled:cursor-not-allowed disabled:opacity-40"
    >
      {children}
    </button>
  );
}

function Stepper({ step }: { step: Step }) {
  const steps: { key: Step; label: string }[] = [
    { key: "upload", label: "CV" },
    { key: "preferences", label: "Preferences" },
    { key: "results", label: "Results" },
  ];
  const current = steps.findIndex((s) => s.key === step);
  return (
    <ol className="flex items-center gap-2 text-sm">
      {steps.map((s, i) => (
        <li key={s.key} className="flex items-center gap-2">
          <span
            className={`flex h-6 w-6 items-center justify-center rounded-full text-xs font-semibold ${
              i <= current
                ? "bg-zinc-900 text-white"
                : "bg-zinc-200 text-zinc-500"
            }`}
          >
            {i + 1}
          </span>
          <span className={i <= current ? "text-zinc-900" : "text-zinc-400"}>
            {s.label}
          </span>
          {i < steps.length - 1 && <span className="mx-1 text-zinc-300">→</span>}
        </li>
      ))}
    </ol>
  );
}

function ProfileSummary({ profile }: { profile: Profile }) {
  return (
    <div className="mt-3 rounded-lg bg-zinc-50 p-3 text-sm text-zinc-700">
      <p>
        <span className="font-medium text-zinc-900">
          {profile.name ?? "Your profile"}
        </span>
        {profile.headline && ` · ${profile.headline}`}
        {profile.years != null && ` · ${profile.years} yrs`}
      </p>
      {profile.skills.length > 0 && (
        <p className="mt-1 text-zinc-500">
          Skills: {profile.skills.slice(0, 12).join(", ")}
        </p>
      )}
      {profile.target_roles.length > 0 && (
        <p className="mt-1 text-zinc-500">
          Searching for: {profile.target_roles.join(", ")}
        </p>
      )}
    </div>
  );
}

function Legend() {
  return (
    <div className="hidden items-center gap-3 text-xs text-zinc-600 sm:flex">
      {(["gold", "orange", "red"] as const).map((s) => (
        <span key={s} className="inline-flex items-center gap-1">
          <SkillDot status={s} /> {STATUS_LABEL[s]}
        </span>
      ))}
    </div>
  );
}
