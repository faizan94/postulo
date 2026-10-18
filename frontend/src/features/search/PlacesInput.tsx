"use client";

import { useQuery } from "@tanstack/react-query";
import { Building2, Globe2, Laptop, MapPin, Plus, X } from "lucide-react";
import { useState } from "react";
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from "@/components/ui/command";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { api } from "@/lib/api";
import type { Place } from "@/lib/types";

export const MAX_PLACES = 5;

const ICON = { city: Building2, country: Globe2, remote: Laptop };

function same(a: Place, b: Place) {
  return a.kind === b.kind && a.name === b.name;
}

/** Places from the fixed list (D9): city, country or Remote; up to 5. */
export function PlacesInput({ value, onChange }: { value: Place[]; onChange: (p: Place[]) => void }) {
  const [open, setOpen] = useState(false);
  const [q, setQ] = useState("");
  const { data = [], isFetching } = useQuery({
    queryKey: ["places", q],
    queryFn: () => api.places(q),
    staleTime: 60 * 60_000,
  });
  const full = value.length >= MAX_PLACES;

  return (
    <div className="flex flex-wrap items-center gap-2">
      {value.map((p) => {
        const Icon = ICON[p.kind];
        return (
          <span
            key={`${p.kind}-${p.name}`}
            className="inline-flex items-center gap-1.5 rounded-full bg-zinc-100 py-1 pr-1 pl-2.5 text-sm text-zinc-800 ring-1 ring-zinc-200"
          >
            <Icon className="size-3.5 text-zinc-500" aria-hidden />
            {p.name}
            <button
              type="button"
              onClick={() => onChange(value.filter((v) => !same(v, p)))}
              className="rounded-full p-0.5 hover:bg-zinc-200"
              aria-label={`Remove ${p.name}`}
            >
              <X className="size-3.5" aria-hidden />
            </button>
          </span>
        );
      })}
      {!full && (
        <Popover open={open} onOpenChange={setOpen}>
          <PopoverTrigger asChild>
            <button
              type="button"
              className="inline-flex items-center gap-1 rounded-full border border-dashed border-zinc-300 px-3 py-1 text-sm text-zinc-600 hover:border-zinc-400 hover:bg-zinc-50"
            >
              <Plus className="size-3.5" aria-hidden />
              Add place
            </button>
          </PopoverTrigger>
          <PopoverContent className="w-72 p-0" align="start">
            <Command shouldFilter={false}>
              <CommandInput placeholder="City, country or Remote" value={q} onValueChange={setQ} />
              <CommandList>
                <CommandEmpty>{isFetching ? "Searching…" : "No place found."}</CommandEmpty>
                <CommandGroup>
                  {data
                    .filter((p) => !value.some((v) => same(v, p)))
                    .map((p) => {
                      const Icon = ICON[p.kind] ?? MapPin;
                      return (
                        <CommandItem
                          key={`${p.kind}-${p.name}`}
                          value={`${p.kind}-${p.name}`}
                          onSelect={() => {
                            onChange([...value, p]);
                            setOpen(false);
                            setQ("");
                          }}
                        >
                          <Icon className="text-zinc-500" aria-hidden />
                          {p.name}
                          <span className="ml-auto text-xs text-zinc-400 capitalize">{p.kind}</span>
                        </CommandItem>
                      );
                    })}
                </CommandGroup>
              </CommandList>
            </Command>
          </PopoverContent>
        </Popover>
      )}
    </div>
  );
}
