"use client";

import { X } from "lucide-react";
import { useState } from "react";
import { Input } from "@/components/ui/input";

export const MAX_KEYWORDS = 5;

/** Optional skills or topics that sharpen the search ("Python", "fintech"). */
export function KeywordsInput({ value, onChange }: { value: string[]; onChange: (k: string[]) => void }) {
  const [draft, setDraft] = useState("");
  const full = value.length >= MAX_KEYWORDS;

  function add(raw: string) {
    const k = raw.trim().replace(/\s+/g, " ").slice(0, 40);
    if (!k || full || value.some((v) => v.toLowerCase() === k.toLowerCase())) return;
    onChange([...value, k]);
    setDraft("");
  }

  return (
    <div className="space-y-2">
      {value.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {value.map((k) => (
            <span
              key={k}
              className="inline-flex items-center gap-1 rounded-full bg-zinc-100 py-1 pr-1 pl-3 text-sm text-zinc-700 ring-1 ring-zinc-200"
            >
              {k}
              <button
                type="button"
                onClick={() => onChange(value.filter((v) => v !== k))}
                className="rounded-full p-0.5 hover:bg-zinc-200"
                aria-label={`Remove ${k}`}
              >
                <X className="size-3.5" aria-hidden />
              </button>
            </span>
          ))}
        </div>
      )}
      {!full && (
        <Input
          placeholder="Optional: a skill or topic, e.g. Python, fintech"
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" || e.key === ",") {
              e.preventDefault();
              add(draft);
            }
          }}
          onBlur={() => add(draft)}
          aria-label="Keyword"
        />
      )}
    </div>
  );
}
