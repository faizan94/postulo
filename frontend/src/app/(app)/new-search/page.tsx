"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { FileText, Loader2, Search, Upload } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { toast } from "sonner";
import { FullPageSpinner } from "@/components/FullPageSpinner";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/features/auth/AuthProvider";
import { CvReview } from "@/features/cv/CvReview";
import { CvUpload } from "@/features/cv/CvUpload";
import { PlacesInput } from "@/features/search/PlacesInput";
import { TitlesInput } from "@/features/search/TitlesInput";
import { api } from "@/lib/api";
import { formatDate } from "@/lib/format";
import type { CvDraft, Place } from "@/lib/types";
import { cn } from "@/lib/utils";

export default function NewSearchPage() {
  const router = useRouter();
  const qc = useQueryClient();
  const { me, refresh } = useAuth();
  const versions = useQuery({ queryKey: ["cv-versions"], queryFn: api.cvVersions });
  const [pickedCv, setCvId] = useState<number | null>(null);
  const cvId = pickedCv ?? versions.data?.[0]?.id ?? null;
  const [titles, setTitles] = useState<string[]>(me?.user.default_titles ?? []);
  const [places, setPlaces] = useState<Place[]>(me?.user.default_places ?? []);
  const [uploading, setUploading] = useState(false);
  const [draft, setDraft] = useState<CvDraft | null>(null);
  const [suggested, setSuggested] = useState<string[]>([]);
  const [busy, setBusy] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!cvId) return toast.error("Choose a CV first.");
    if (!titles.length || !places.length) return toast.error("Add a job title and a place.");
    setBusy(true);
    try {
      const { search_id } = await api.startSearch(cvId, titles, places);
      await refresh();
      void qc.invalidateQueries({ queryKey: ["history"] });
      router.push(`/search/${search_id}`);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Could not start the search.");
      setBusy(false);
    }
  }

  if (versions.isLoading) return <FullPageSpinner />;

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">New search</h1>
        <p className="text-zinc-500">Reuse a saved CV or upload a new one.</p>
      </div>

      <section className="space-y-3 rounded-2xl border border-zinc-200 bg-white p-6 shadow-sm">
        <div className="flex items-center justify-between">
          <h2 className="font-medium">Which CV?</h2>
          {!uploading && (
            <Button variant="outline" size="sm" onClick={() => setUploading(true)}>
              <Upload data-icon="inline-start" aria-hidden />
              Upload new CV
            </Button>
          )}
        </div>
        {uploading ? (
          draft ? (
            <CvReview
              draft={draft}
              confirmLabel="Save this CV"
              onBack={() => setDraft(null)}
              onConfirmed={async (c) => {
                await qc.invalidateQueries({ queryKey: ["cv-versions"] });
                setCvId(c.cv_version.id);
                setSuggested(c.profile.target_titles);
                if (!titles.length) setTitles(c.suggested.titles);
                if (!places.length && c.suggested.place) setPlaces([c.suggested.place]);
                setUploading(false);
                setDraft(null);
                toast.success("CV saved");
              }}
            />
          ) : (
            <CvUpload onDraft={setDraft} />
          )
        ) : versions.data?.length ? (
          <ul className="space-y-2" role="radiogroup" aria-label="Saved CVs">
            {versions.data.map((v) => (
              <li key={v.id}>
                <button
                  type="button"
                  role="radio"
                  aria-checked={cvId === v.id}
                  onClick={() => setCvId(v.id)}
                  className={cn(
                    "flex w-full items-center gap-3 rounded-xl border px-4 py-3 text-left text-sm transition",
                    cvId === v.id
                      ? "border-indigo-300 bg-indigo-50 ring-1 ring-indigo-200"
                      : "border-zinc-200 hover:bg-zinc-50",
                  )}
                >
                  <FileText className="size-4 text-zinc-500" aria-hidden />
                  <span className="flex-1 truncate font-medium">{v.label}</span>
                  <span className="text-zinc-500">{formatDate(v.confirmed_at ?? v.created_at)}</span>
                </button>
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-sm text-zinc-500">No saved CV yet. Upload one to start.</p>
        )}
      </section>

      <form onSubmit={submit} className="space-y-6 rounded-2xl border border-zinc-200 bg-white p-6 shadow-sm">
        <div className="space-y-2">
          <h2 className="font-medium">Job titles</h2>
          <TitlesInput value={titles} onChange={setTitles} suggestions={suggested} />
        </div>
        <div className="space-y-2">
          <h2 className="font-medium">Places</h2>
          <PlacesInput value={places} onChange={setPlaces} />
        </div>
        <Button type="submit" size="lg" className="h-10" disabled={busy || uploading}>
          {busy ? <Loader2 className="animate-spin" aria-hidden /> : <Search data-icon="inline-start" aria-hidden />}
          Find jobs
        </Button>
      </form>
    </div>
  );
}
