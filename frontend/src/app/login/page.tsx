"use client";

import { ArrowRight, Info } from "lucide-react";
import Image from "next/image";
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
    <main className="grid flex-1 bg-white lg:min-h-screen lg:grid-cols-[11fr_9fr]">
      <section className="relative hidden overflow-hidden bg-zinc-900 lg:block">
        <Image
          src="/images/login-hero.jpg"
          alt="A team working together at a shared desk with laptops, notebooks and phones"
          fill
          preload
          sizes="(min-width: 1024px) 55vw, 0px"
          className="object-cover"
        />
        <div
          className="absolute inset-0 bg-gradient-to-t from-zinc-950/85 via-zinc-950/35 to-zinc-950/10"
          aria-hidden
        />
        <div className="absolute inset-x-0 bottom-0 space-y-3 p-12 text-white xl:p-16">
          <p className="max-w-lg text-4xl font-semibold leading-tight tracking-tight xl:text-5xl">
            Open jobs that fit your CV
          </p>
          <p className="max-w-md text-lg text-white/80">
            We check company job boards for open, recent roles and show how well you match.
          </p>
        </div>
      </section>

      <div className="flex items-center justify-center px-4 py-12 sm:px-8 lg:py-16">
        <div className="w-full max-w-md">
          <div className="mb-8 flex justify-center lg:justify-start">
            <Logo />
          </div>
          <form
            onSubmit={submit}
            className="space-y-6 rounded-2xl border border-zinc-200 bg-white p-6 sm:p-8"
          >
            <div className="space-y-2">
              <h1 className="text-2xl font-semibold tracking-tight sm:text-3xl">
                Find open jobs that fit you
              </h1>
              <p className="text-base text-zinc-500">
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
                className="h-11 text-base"
              />
              {error && <p className="text-sm text-rose-600">{error}</p>}
            </div>
            <Button type="submit" size="lg" className="h-11 w-full text-base" disabled={busy}>
              {busy ? "Signing in…" : "Continue"}
              <ArrowRight data-icon="inline-end" />
            </Button>
            <p className="flex gap-2 rounded-lg bg-zinc-50 p-3 text-sm text-zinc-500">
              <Info className="mt-0.5 size-4 shrink-0" aria-hidden />
              No password: anyone who knows your name can open this account. We remove email and
              phone numbers from your CV before saving it.
            </p>
          </form>
        </div>
      </div>
    </main>
  );
}
