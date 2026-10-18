// Reads a text/event-stream body via fetch (EventSource can't send the auth header).
import type { SearchEvent } from "@/lib/types";
import { API_URL, authHeaders } from "@/lib/api/client";

export async function streamSearch(
  searchId: number,
  onEvent: (e: SearchEvent) => void,
  signal: AbortSignal,
): Promise<void> {
  const res = await fetch(`${API_URL}/api/searches/${searchId}/events`, {
    headers: { ...authHeaders(), Accept: "text/event-stream" },
    signal,
  });
  if (!res.ok || !res.body) throw new Error(`Stream failed (HTTP ${res.status})`);
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  for (;;) {
    const { value, done } = await reader.read();
    if (done) return;
    buffer += decoder.decode(value, { stream: true });
    let idx: number;
    while ((idx = buffer.indexOf("\n\n")) !== -1) {
      const chunk = buffer.slice(0, idx);
      buffer = buffer.slice(idx + 2);
      for (const line of chunk.split("\n")) {
        if (line.startsWith("data: ")) {
          try {
            onEvent(JSON.parse(line.slice(6)) as SearchEvent);
          } catch {
            // ignore a malformed line; the snapshot on reconnect repairs state
          }
        }
      }
    }
  }
}
