"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { FileText, LogOut, Trash2 } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { useAuth } from "@/features/auth/AuthProvider";
import { PlacesInput } from "@/features/search/PlacesInput";
import { TitlesInput } from "@/features/search/TitlesInput";
import { api, setToken } from "@/lib/api";
import { formatDate } from "@/lib/format";
import type { Place } from "@/lib/types";

export default function SettingsPage() {
  const { me, refresh, logout } = useAuth();
  const qc = useQueryClient();
  const router = useRouter();
  const [titles, setTitles] = useState<string[]>(me?.user.default_titles ?? []);
  const [places, setPlaces] = useState<Place[]>(me?.user.default_places ?? []);
  const versions = useQuery({ queryKey: ["cv-versions"], queryFn: api.cvVersions });

  const save = useMutation({
    mutationFn: () => api.saveSettings(titles, places),
    onSuccess: async () => {
      await refresh();
      toast.success("Saved");
    },
    onError: (e) => toast.error(e.message),
  });
  const removeCv = useMutation({
    mutationFn: (id: number) => api.deleteCv(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["cv-versions"] }),
    onError: (e) => toast.error(e.message),
  });
  const deleteAll = useMutation({
    mutationFn: api.deleteMe,
    onSuccess: async () => {
      setToken(null);
      qc.clear();
      await refresh(); // no token -> signed out
      router.replace("/login");
    },
    onError: (e) => toast.error(e.message),
  });

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <h1 className="text-2xl font-semibold tracking-tight">Settings</h1>

      <section className="space-y-5 rounded-2xl border border-zinc-200 bg-white p-6 shadow-sm">
        <h2 className="font-medium">Default search</h2>
        <div className="space-y-2">
          <p className="text-sm text-zinc-500">Job titles</p>
          <TitlesInput value={titles} onChange={setTitles} />
        </div>
        <div className="space-y-2">
          <p className="text-sm text-zinc-500">Places</p>
          <PlacesInput value={places} onChange={setPlaces} />
        </div>
        <Button
          onClick={() => save.mutate()}
          disabled={save.isPending || !titles.length || !places.length}
        >
          Save defaults
        </Button>
      </section>

      <section className="space-y-3 rounded-2xl border border-zinc-200 bg-white p-6 shadow-sm">
        <h2 className="font-medium">Saved CVs</h2>
        {versions.data?.length ? (
          <ul className="space-y-2">
            {versions.data.map((v) => (
              <li key={v.id} className="flex items-center gap-3 rounded-xl border border-zinc-200 px-4 py-2.5 text-sm">
                <FileText className="size-4 text-zinc-500" aria-hidden />
                <span className="flex-1 truncate">{v.label}</span>
                <span className="text-zinc-500">{formatDate(v.confirmed_at ?? v.created_at)}</span>
                <Button
                  variant="ghost"
                  size="icon-sm"
                  aria-label={`Delete ${v.label}`}
                  onClick={() => removeCv.mutate(v.id)}
                >
                  <Trash2 aria-hidden />
                </Button>
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-sm text-zinc-500">No saved CVs.</p>
        )}
      </section>

      <section className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-zinc-200 bg-white p-6 shadow-sm">
        <div>
          <h2 className="font-medium">Your data</h2>
          <p className="text-sm text-zinc-500">Signed in as {me?.user.name}.</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={logout}>
            <LogOut data-icon="inline-start" aria-hidden />
            Log out
          </Button>
          <Dialog>
            <DialogTrigger asChild>
              <Button variant="destructive">
                <Trash2 data-icon="inline-start" aria-hidden />
                Delete my data
              </Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>Delete all your data?</DialogTitle>
                <DialogDescription>
                  This removes your account, saved CVs and all searches. It can&apos;t be undone.
                </DialogDescription>
              </DialogHeader>
              <DialogFooter>
                <DialogClose asChild>
                  <Button variant="outline">Cancel</Button>
                </DialogClose>
                <Button variant="destructive" onClick={() => deleteAll.mutate()} disabled={deleteAll.isPending}>
                  Delete everything
                </Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
        </div>
      </section>
    </div>
  );
}
