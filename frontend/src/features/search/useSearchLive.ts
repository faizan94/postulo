"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { streamSearch } from "@/lib/sse";
import type { JobCard, SearchDetail, SearchEvent, Stage } from "@/lib/types";

const TERMINAL = new Set(["done", "failed"]);

function upsertCard(results: JobCard[], card: JobCard): JobCard[] {
  const rest = results.filter((c) => c.posting_id !== card.posting_id);
  return [...rest, card].sort((a, b) => (b.match.value ?? -1) - (a.match.value ?? -1));
}

/**
 * Search detail + live stream (§8.4). Stream events patch the query cache; on `done` the final
 * ranked list is refetched. If the stream fails twice, it falls back to polling every 2 s.
 */
export function useSearchLive(id: number) {
  const qc = useQueryClient();
  const key = ["search", id] as const;
  const [poll, setPoll] = useState(false);
  const [stage, setStage] = useState<{ stage: Stage; message: string } | null>(null);
  const [note, setNote] = useState<string | null>(null);

  const query = useQuery({
    queryKey: key,
    queryFn: () => api.search(id),
    refetchInterval: (q) =>
      poll && q.state.data && !TERMINAL.has(q.state.data.status) ? 2000 : false,
  });
  const status = query.data?.status;

  useEffect(() => {
    if (!status || TERMINAL.has(status)) return;
    const ctrl = new AbortController();
    let stopped = false;

    const apply = (e: SearchEvent) => {
      switch (e.type) {
        case "snapshot":
          qc.setQueryData(key, e.search);
          break;
        case "stage":
          setStage({ stage: e.stage, message: e.message });
          qc.setQueryData<SearchDetail>(key, (old) =>
            old ? { ...old, status: "running", stage: e.stage } : old,
          );
          break;
        case "job":
          qc.setQueryData<SearchDetail>(key, (old) =>
            old ? { ...old, results: upsertCard(old.results, e.card) } : old,
          );
          break;
        case "company":
          qc.setQueryData<SearchDetail>(key, (old) =>
            old
              ? {
                  ...old,
                  results: old.results.map((c) =>
                    c.posting_id === e.posting_id ? { ...c, company_score: e.company_score } : c,
                  ),
                }
              : old,
          );
          break;
        case "note":
          setNote(e.message);
          break;
        case "done":
        case "error":
          void qc.invalidateQueries({ queryKey: key });
          void qc.invalidateQueries({ queryKey: ["history"] });
          break;
      }
    };

    (async () => {
      for (let attempt = 0; attempt < 2 && !stopped; attempt++) {
        try {
          await streamSearch(id, apply, ctrl.signal);
          if (!stopped) void qc.invalidateQueries({ queryKey: key });
          return;
        } catch {
          if (stopped) return;
        }
      }
      setPoll(true);
    })();

    return () => {
      stopped = true;
      ctrl.abort();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id, status === undefined || TERMINAL.has(status ?? "")]);

  return { ...query, stage, note: note ?? query.data?.note ?? null };
}
