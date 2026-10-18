"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import { ChevronRight, RotateCw } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { FullPageSpinner } from "@/components/FullPageSpinner";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";
import { formatDate, placesLabel } from "@/lib/format";
import type { SearchStatus } from "@/lib/types";
import { cn } from "@/lib/utils";

const STATUS_CHIP: Record<SearchStatus, string> = {
  queued: "bg-zinc-100 text-zinc-600",
  running: "bg-indigo-50 text-indigo-700",
  done: "bg-emerald-50 text-emerald-700",
  failed: "bg-rose-50 text-rose-700",
};

export default function HistoryPage() {
  const router = useRouter();
  const { data, isLoading } = useQuery({ queryKey: ["history"], queryFn: api.history });
  const rerun = useMutation({
    mutationFn: (id: number) => api.rerun(id),
    onSuccess: ({ search_id }) => router.push(`/search/${search_id}`),
    onError: (e) => toast.error(e.message),
  });

  if (isLoading) return <FullPageSpinner />;

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Your searches</h1>
        <p className="text-zinc-500">Open a past search or run it again with fresh results.</p>
      </div>
      {!data?.length ? (
        <div className="rounded-2xl border border-zinc-200 bg-white p-8 text-center text-zinc-500">
          No searches yet.{" "}
          <Link href="/new-search" className="text-indigo-700 hover:underline">
            Start one
          </Link>
        </div>
      ) : (
        <ul className="divide-y divide-zinc-100 rounded-2xl border border-zinc-200 bg-white shadow-sm">
          {data.map((s) => (
            <li key={s.id} className="flex items-center gap-4 px-5 py-4">
              <div className="min-w-0 flex-1">
                <p className="truncate font-medium">{s.titles.join(" · ")}</p>
                <p className="truncate text-sm text-zinc-500">
                  {placesLabel(s.places)} · {formatDate(s.created_at)} · {s.result_count} jobs
                </p>
              </div>
              <span className={cn("rounded-full px-2 py-0.5 text-xs font-medium capitalize", STATUS_CHIP[s.status])}>
                {s.status}
              </span>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => rerun.mutate(s.id)}
                disabled={rerun.isPending || !s.cv_version_id}
                aria-label="Re-run this search"
              >
                <RotateCw aria-hidden />
              </Button>
              <Button asChild variant="outline" size="sm">
                <Link href={`/search/${s.id}`}>
                  Open <ChevronRight data-icon="inline-end" aria-hidden />
                </Link>
              </Button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
