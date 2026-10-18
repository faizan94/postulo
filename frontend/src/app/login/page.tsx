"use client";

import { ArrowRight, Info } from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { Logo } from "@/components/Logo";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { homePath, useAuth } from "@/features/auth/AuthProvider";

export default function LoginPage() {
  const { ready, me, login } = useAuth();
  const router = useRouter();
  const [name, setName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (ready && me) router.replace(homePath(me));
  }, [ready, me, router]);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (name.trim().length < 2) {
      setError("Enter at least 2 characters.");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const m = await login(name.trim());
      router.replace(homePath(m));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not sign in.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="flex flex-1 items-center justify-center bg-zinc-50 px-4 py-16">
      <div className="w-full max-w-sm">
        <div className="mb-8 flex justify-center">
          <Logo />
        </div>
        <form
          onSubmit={submit}
          className="space-y-5 rounded-2xl border border-zinc-200 bg-white p-6 shadow-sm"
        >
          <div className="space-y-1">
            <h1 className="text-xl font-semibold tracking-tight">Find open jobs that fit you</h1>
            <p className="text-sm text-zinc-500">
              Sign in with a name. Use the same name to come back later.
            </p>
          </div>
          <div className="space-y-2">
            <Label htmlFor="name">Your name</Label>
            <Input
              id="name"
              autoFocus
              autoComplete="nickname"
              placeholder="e.g. Alex"
              value={name}
              maxLength={40}
              onChange={(e) => {
                setName(e.target.value);
                setError(null);
              }}
              aria-invalid={!!error}
              className="h-10"
            />
            {error && <p className="text-sm text-rose-600">{error}</p>}
          </div>
          <Button type="submit" size="lg" className="h-10 w-full" disabled={busy}>
            {busy ? "Signing in…" : "Continue"}
            <ArrowRight data-icon="inline-end" />
          </Button>
          <p className="flex gap-2 rounded-lg bg-zinc-50 p-3 text-xs text-zinc-500">
            <Info className="mt-0.5 size-3.5 shrink-0" aria-hidden />
            No password: anyone who knows your name can open this account. We remove email and
            phone numbers from your CV before saving it.
          </p>
        </form>
      </div>
    </main>
  );
}
