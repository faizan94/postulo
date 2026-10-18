"use client";

import { ClipboardPaste, FileUp, Loader2 } from "lucide-react";
import { useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { api } from "@/lib/api";
import type { CvDraft } from "@/lib/types";
import { cn } from "@/lib/utils";

// Images (photo or scan) are read by Nemotron vision on the backend (D19).
const ACCEPT =
  ".pdf,.docx,.png,.jpg,.jpeg,.webp,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document,image/png,image/jpeg,image/webp";

/** Step 1: drop a PDF/.docx/image or paste text. Calls POST /api/cv and returns the draft. */
export function CvUpload({ onDraft }: { onDraft: (d: CvDraft) => void }) {
  const input = useRef<HTMLInputElement>(null);
  const [mode, setMode] = useState<"file" | "paste">("file");
  const [dragging, setDragging] = useState(false);
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function send(promise: Promise<CvDraft>) {
    setBusy(true);
    setError(null);
    try {
      onDraft(await promise);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Upload failed.");
    } finally {
      setBusy(false);
    }
  }

  function pick(file: File | undefined) {
    if (!file) return;
    if (file.size > 10 * 1024 * 1024) {
      setError("The file is larger than 10 MB.");
      return;
    }
    void send(api.uploadCvFile(file));
  }

  return (
    <div className="space-y-4">
      {mode === "file" ? (
        <button
          type="button"
          onClick={() => input.current?.click()}
          onDragOver={(e) => {
            e.preventDefault();
            setDragging(true);
          }}
          onDragLeave={() => setDragging(false)}
          onDrop={(e) => {
            e.preventDefault();
            setDragging(false);
            pick(e.dataTransfer.files[0]);
          }}
          disabled={busy}
          className={cn(
            "flex w-full flex-col items-center justify-center gap-3 rounded-xl border-2 border-dashed px-6 py-12 text-center transition-colors",
            dragging ? "border-indigo-400 bg-indigo-50" : "border-zinc-200 hover:border-zinc-300 hover:bg-zinc-50",
          )}
        >
          {busy ? (
            <Loader2 className="size-8 animate-spin text-indigo-500" aria-hidden />
          ) : (
            <FileUp className="size-8 text-indigo-500" aria-hidden />
          )}
          <span className="font-medium text-zinc-900">
            {busy ? "Reading your CV…" : "Drop your CV here or click to choose"}
          </span>
          <span className="text-sm text-zinc-500">PDF, Word (.docx) or a photo/scan (PNG, JPG), up to 10 MB</span>
          <input
            ref={input}
            type="file"
            accept={ACCEPT}
            className="sr-only"
            onChange={(e) => pick(e.target.files?.[0])}
          />
        </button>
      ) : (
        <div className="space-y-3">
          <Textarea
            rows={12}
            placeholder="Paste the text of your CV here"
            value={text}
            onChange={(e) => setText(e.target.value)}
            className="text-sm"
          />
          <Button
            onClick={() => {
              if (text.trim().length < 50) {
                setError("Paste at least a few lines of your CV.");
                return;
              }
              void send(api.uploadCvText(text));
            }}
            disabled={busy}
          >
            {busy ? "Reading…" : "Use this text"}
          </Button>
        </div>
      )}
      {error && (
        <p role="alert" className="rounded-lg bg-rose-50 px-3 py-2 text-sm text-rose-700">
          {error}
        </p>
      )}
      <button
        type="button"
        className="inline-flex items-center gap-1.5 text-sm text-zinc-500 hover:text-zinc-800"
        onClick={() => {
          setMode(mode === "file" ? "paste" : "file");
          setError(null);
        }}
      >
        {mode === "file" ? (
          <>
            <ClipboardPaste className="size-3.5" aria-hidden /> Paste text instead
          </>
        ) : (
          <>
            <FileUp className="size-3.5" aria-hidden /> Upload a file instead
          </>
        )}
      </button>
    </div>
  );
}
