"use client";

import { Loader2, Search } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/features/auth/AuthProvider";
import { CvReview } from "@/features/cv/CvReview";
import { CvUpload } from "@/features/cv/CvUpload";
import { ProfileCard } from "@/features/cv/ProfileCard";
import { PlacesInput } from "@/features/search/PlacesInput";
import { TitlesInput } from "@/features/search/TitlesInput";
import { api } from "@/lib/api";
import type { CvConfirmed, CvDraft, Place } from "@/lib/types";
import { cn } from "@/lib/utils";

type Step = "upload" | "review" | "details" | "starting";
const STEPS: { key: Step; label: string }[] = [
  { key: "upload", label: "Your CV" },
  { key: "review", label: "Check the text" },
  { key: "details", label: "What and where" },
];

export default function OnboardingPage() {
  const router = useRouter();
  const { refresh } = useAuth();
  const [step, setStep] = useState<Step>("upload");
  const [draft, setDraft] = useState<CvDraft | null>(null);
  const [confirmed, setConfirmed] = useState<CvConfirmed | null>(null);
  const [titles, setTitles] = useState<string[]>([]);
  const [places, setPlaces] = useState<Place[]>([]);

  async function start(cvId: number, t: string[], p: Place[]) {
    setStep("starting");
    try {
      const { search_id } = await api.startSearch(cvId, t, p);
      await refresh();
      router.replace(`/search/${search_id}`);
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Could not start the search.");
      setStep("details");
    }
  }

  function onConfirmed(c: CvConfirmed) {
    setConfirmed(c);
    const t = c.suggested.titles.slice(0, 3);
    const p = c.suggested.place ? [c.suggested.place] : [];
    setTitles(t);
    setPlaces(p);
    c.warnings.forEach((w) => toast.info(w));
    // D11/D22: run the first search automatically; no place in the CV means Anywhere.
    if (t.length) void start(c.cv_version.id, t, p);
    else setStep("details");
  }

  const current = STEPS.findIndex((s) => s.key === step);

  return (
    <div className="mx-auto max-w-2xl">
      <div className="mb-8 space-y-2">
        <h1 className="text-2xl font-semibold tracking-tight">Let&apos;s find jobs that fit you</h1>
        <p className="text-zinc-500">
          Upload your CV once. We search company job boards for open, recent roles and score how
          well you match.
        </p>
      </div>
      <ol className="mb-6 flex items-center gap-2 text-sm" aria-label="Progress">
        {STEPS.map((s, i) => (
          <li key={s.key} className="flex items-center gap-2">
            <span
              className={cn(
                "flex size-6 items-center justify-center rounded-full text-xs font-semibold",
                i <= Math.max(current, step === "starting" ? 2 : current)
                  ? "bg-indigo-600 text-white"
                  : "bg-zinc-100 text-zinc-400",
              )}
            >
              {i + 1}
            </span>
            <span className={i <= current ? "text-zinc-900" : "text-zinc-400"}>{s.label}</span>
            {i < STEPS.length - 1 && <span className="mx-1 h-px w-6 bg-zinc-200" />}
          </li>
        ))}
      </ol>

      <section className="rounded-2xl border border-zinc-200 bg-white p-6 shadow-sm">
        {step === "upload" && (
          <CvUpload
            onDraft={(d) => {
              setDraft(d);
              setStep("review");
            }}
          />
        )}
        {step === "review" && draft && (
          <CvReview
            draft={draft}
            onConfirmed={onConfirmed}
            onBack={() => setStep("upload")}
            confirmLabel="Looks right, find jobs"
          />
        )}
        {step === "details" && confirmed && (
          <form
            className="space-y-6"
            onSubmit={(e) => {
              e.preventDefault();
              if (!titles.length) {
                toast.error("Add at least one job title.");
                return;
              }
              void start(confirmed.cv_version.id, titles, places);
            }}
          >
            <ProfileCard profile={confirmed.profile} collapsible />
            <div className="space-y-2">
              <h2 className="font-medium">What jobs should we look for?</h2>
              <TitlesInput
                value={titles}
                onChange={setTitles}
                suggestions={confirmed.profile.target_titles}
              />
            </div>
            <div className="space-y-2">
              <h2 className="font-medium">Where do you want to work?</h2>
              <PlacesInput value={places} onChange={setPlaces} />
            </div>
            <Button type="submit" size="lg" className="h-10">
              <Search data-icon="inline-start" aria-hidden />
              Find jobs
            </Button>
          </form>
        )}
        {step === "starting" && (
          <div className="flex items-center gap-3 py-10 text-zinc-600" role="status">
            <Loader2 className="size-5 animate-spin text-indigo-600" aria-hidden />
            Starting your first search…
          </div>
        )}
      </section>
    </div>
  );
}
