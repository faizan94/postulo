"use client";

import { ShieldCheck } from "lucide-react";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { api } from "@/lib/api";
import type { CvConfirmed, CvDraft } from "@/lib/types";

/** Step 2: the user checks and fixes the extracted text before anything is used (D1). */
export function CvReview({
  draft,
  onConfirmed,
  onBack,
  confirmLabel = "Looks right",
}: {
  draft: CvDraft;
  onConfirmed: (c: CvConfirmed) => void;
  onBack: () => void;
  confirmLabel?: string;
}) {
  const [text, setText] = useState(draft.text);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function confirm() {
    if (text.trim().length < 50) {
      setError("The text is too short to find jobs.");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      onConfirmed(await api.confirmCv(draft.cv_version_id, text));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not save the CV.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-4">
      <p className="flex items-start gap-2 rounded-lg bg-emerald-50 p-3 text-sm text-emerald-800">
        <ShieldCheck className="mt-0.5 size-4 shrink-0" aria-hidden />
        We removed email, phone and personal lines like date of birth. Fix anything that looks
        wrong; only this text is used.
      </p>
      {draft.warnings.map((w) => (
        <p key={w} className="rounded-lg bg-amber-50 p-3 text-sm text-amber-800">
          {w}
        </p>
      ))}
      {/* Readable sans text; grows with the CV but stays capped so the buttons stay in reach. */}
      <Textarea
        rows={20}
        value={text}
        onChange={(e) => setText(e.target.value)}
        className="max-h-[65vh] min-h-80 overflow-y-auto px-4 py-3 leading-relaxed text-zinc-800"
        aria-label="Extracted CV text"
      />
      {error && <p className="text-sm text-rose-600">{error}</p>}
      <div className="flex items-center gap-3">
        <Button onClick={confirm} disabled={busy} size="lg" className="h-10">
          {busy ? "Reading your skills…" : confirmLabel}
        </Button>
        <Button variant="ghost" onClick={onBack} disabled={busy}>
          Upload a different CV
        </Button>
      </div>
    </div>
  );
}
