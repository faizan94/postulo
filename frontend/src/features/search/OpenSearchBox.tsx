"use client";

import { Loader2, Sparkles } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { api } from "@/lib/api";
import type { SearchIntent } from "@/lib/types";

const EXAMPLES = ["AI engineer, remote, Python", "Data analyst in Hamburg", "Backend developer Europe Go"];

/** Open search (D21): describe the job in your own words; we fill in the fields below. */
export function OpenSearchBox({ onParsed }: { onParsed: (intent: SearchIntent) => void }) {
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);

  async function parse(value: string) {
    const t = value.trim();
    if (t.length < 2) return;
    setBusy(true);
    try {
      const intent = await api.parseSearch(t);
      if (!intent.titles.length) toast.info("Add at least one job title below.");
      onParsed(intent);
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Could not read that search.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-2">
      <form
        className="flex gap-2"
        onSubmit={(e) => {
          e.preventDefault();
          void parse(text);
        }}
      >
        <Input
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="Describe the job you want, e.g. AI engineer, remote, Python"
          className="h-10"
          aria-label="Describe the job you want"
          maxLength={300}
        />
        <Button type="submit" variant="outline" className="h-10" disabled={busy || text.trim().length < 2}>
          {busy ? <Loader2 className="animate-spin" aria-hidden /> : <Sparkles data-icon="inline-start" aria-hidden />}
          Fill in
        </Button>
      </form>
      <div className="flex flex-wrap items-center gap-2 text-xs text-zinc-400">
        Try:
        {EXAMPLES.map((ex) => (
          <button
            key={ex}
            type="button"
            className="rounded-full border border-zinc-200 px-2 py-0.5 hover:bg-zinc-50 hover:text-zinc-700"
            onClick={() => {
              setText(ex);
              void parse(ex);
            }}
          >
            {ex}
          </button>
        ))}
      </div>
    </div>
  );
}
