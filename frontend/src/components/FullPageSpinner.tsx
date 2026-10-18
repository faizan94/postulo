import { Loader2 } from "lucide-react";

export function FullPageSpinner({ label = "Loading" }: { label?: string }) {
  return (
    <div className="flex flex-1 items-center justify-center py-24 text-zinc-400" role="status">
      <Loader2 className="size-5 animate-spin" aria-hidden />
      <span className="sr-only">{label}</span>
    </div>
  );
}
