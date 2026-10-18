"use client";

import { useQuery } from "@tanstack/react-query";
import { FileText } from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { FullPageSpinner } from "@/components/FullPageSpinner";
import { ProfileCard } from "@/features/cv/ProfileCard";
import { api } from "@/lib/api";
import { formatDate } from "@/lib/format";
import { cn } from "@/lib/utils";

/** Your structured profile per saved CV (D23). */
export default function ProfilePage() {
  const versions = useQuery({ queryKey: ["cv-versions"], queryFn: api.cvVersions });
  const [picked, setPicked] = useState<number | null>(null);
  const cvId = picked ?? versions.data?.[0]?.id ?? null;
  const detail = useQuery({
    queryKey: ["cv-detail", cvId],
    queryFn: () => api.cvDetail(cvId as number),
    enabled: cvId !== null,
  });

  if (versions.isLoading) return <FullPageSpinner />;
  if (!versions.data?.length)
    return (
      <p className="mx-auto max-w-2xl rounded-2xl border border-zinc-200 bg-white p-8 text-center text-zinc-500">
        No CV yet.{" "}
        <Link href="/onboarding" className="text-indigo-700 hover:underline">
          Upload one
        </Link>
      </p>
    );

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Your profile</h1>
        <p className="text-zinc-500">
          What we read from each CV. Hover a skill to see the line it came from.
        </p>
      </div>
      {versions.data.length > 1 && (
        <div className="flex flex-wrap gap-2" role="radiogroup" aria-label="CV version">
          {versions.data.map((v) => (
            <button
              key={v.id}
              type="button"
              role="radio"
              aria-checked={cvId === v.id}
              onClick={() => setPicked(v.id)}
              className={cn(
                "inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-sm",
                cvId === v.id ? "border-indigo-300 bg-indigo-50 text-indigo-800" : "border-zinc-200 hover:bg-zinc-50",
              )}
            >
              <FileText className="size-3.5" aria-hidden />
              {v.label}
              <span className="text-xs text-zinc-400">{formatDate(v.confirmed_at ?? v.created_at)}</span>
            </button>
          ))}
        </div>
      )}
      {detail.isLoading ? (
        <FullPageSpinner />
      ) : detail.data?.profile ? (
        <ProfileCard profile={detail.data.profile} />
      ) : (
        <p className="text-zinc-500">No profile for this CV.</p>
      )}
    </div>
  );
}
