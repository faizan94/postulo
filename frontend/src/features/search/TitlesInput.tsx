"use client";

import { Plus, X } from "lucide-react";
import { useState } from "react";
import { Input } from "@/components/ui/input";
import { nameKey } from "@/lib/format";

export const MAX_TITLES = 3;

/** 1-3 job titles as chips (D10). */
export function TitlesInput({
  value,
  onChange,
  suggestions = [],
}: {
  value: string[];
  onChange: (titles: string[]) => void;
  suggestions?: string[];
}) {
  const [draft, setDraft] = useState("");
  const full = value.length >= MAX_TITLES;

  function add(title: string) {
    const t = title.trim().replace(/\s+/g, " ");
    if (!t || full || value.some((v) => nameKey(v) === nameKey(t))) return;
    onChange([...value, t.slice(0, 80)]);
    setDraft("");
  }

  const extra = suggestions.filter((s) => !value.some((v) => nameKey(v) === nameKey(s)));

  return (
    <div className="space-y-2">
      <div className="flex flex-wrap gap-2">
        {value.map((t) => (
          <span
            key={t}
            className="inline-flex items-center gap-1 rounded-full bg-indigo-50 py-1 pr-1 pl-3 text-sm text-indigo-700 ring-1 ring-indigo-200"
          >
            {t}
            <button
              type="button"
              onClick={() => onChange(value.filter((v) => v !== t))}
              className="rounded-full p-0.5 hover:bg-indigo-100"
              aria-label={`Remove ${t}`}
            >
              <X className="size-3.5" aria-hidden />
            </button>
          </span>
        ))}
      </div>
      {!full && (
        <Input
          placeholder="Add a job title, e.g. Data Engineer"
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") {
              e.preventDefault();
              add(draft);
            }
          }}
          onBlur={() => add(draft)}
          aria-label="Job title"
        />
      )}
      {!full && extra.length > 0 && (
        <div className="flex flex-wrap items-center gap-2 text-xs text-zinc-500">
          Suggested:
          {extra.slice(0, 4).map((s) => (
            <button
              key={s}
              type="button"
              onClick={() => add(s)}
              className="inline-flex items-center gap-1 rounded-full border border-zinc-200 px-2 py-0.5 hover:bg-zinc-50"
            >
              <Plus className="size-3" aria-hidden />
              {s}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
