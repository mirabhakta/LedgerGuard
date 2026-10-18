import {
  createContext,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { useQueryClient } from "@tanstack/react-query";

import { API_BASE } from "./client";
import { EVENT_TYPES, type LedgerEvent } from "./types";

const LAST_EVENT_ID_KEY = "ledgerguard.lastEventId";
const MAX_BUFFERED_EVENTS = 120;

export type StreamStatus = "connecting" | "connected" | "reconnecting";

interface StreamState {
  status: StreamStatus;
  lastEvent: LedgerEvent | null;
  lastEventId: number;
  /** Recent events, oldest first. SSE is notification-only; detail is refetched. */
  events: LedgerEvent[];
  reconnect: () => void;
}

const StreamContext = createContext<StreamState | null>(null);

function readStoredEventId(): number {
  try {
    const raw = window.localStorage.getItem(LAST_EVENT_ID_KEY);
    const parsed = raw ? Number(raw) : 0;
    return Number.isFinite(parsed) && parsed > 0 ? parsed : 0;
  } catch {
    return 0;
  }
}

export function StreamProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient();
  const [status, setStatus] = useState<StreamStatus>("connecting");
  const [events, setEvents] = useState<LedgerEvent[]>([]);
  const [lastEvent, setLastEvent] = useState<LedgerEvent | null>(null);
  const [attempt, setAttempt] = useState(0);
  const lastEventIdRef = useRef<number>(readStoredEventId());

  useEffect(() => {
    let disposed = false;
    let retryDelay = 3_000;
    let timer: number | null = null;
    let source: EventSource | null = null;

    const handleEvent = (message: MessageEvent<string>) => {
      try {
        const event = JSON.parse(message.data) as LedgerEvent;
        if (typeof event.event_id !== "number") return;
        lastEventIdRef.current = event.event_id;
        try {
          window.localStorage.setItem(LAST_EVENT_ID_KEY, String(event.event_id));
        } catch {
          /* storage can be unavailable in private mode; replay from 0 still works */
        }
        setLastEvent(event);
        setEvents((prev) => [...prev.slice(-(MAX_BUFFERED_EVENTS - 1)), event]);
        // Treat SSE as a notification: refetch the persisted truth.
        queryClient.invalidateQueries({ queryKey: ["actions"] });
        queryClient.invalidateQueries({ queryKey: ["dashboard"] });
        queryClient.invalidateQueries({ queryKey: ["action", event.action_id] });
      } catch {
        /* malformed frame: ignore, the next refetch restores truth */
      }
    };

    const connect = () => {
      if (disposed) return;
      const cursor = lastEventIdRef.current;
      const url = `${API_BASE}/api/stream${cursor > 0 ? `?last_event_id=${cursor}` : ""}`;
      source = new EventSource(url);

      source.onopen = () => {
        if (disposed) return;
        retryDelay = 3_000;
        setStatus("connected");
      };

      // The backend emits named events (event: policy_decision), so listen per type.
      for (const type of EVENT_TYPES) {
        source.addEventListener(type, handleEvent as EventListener);
      }
      // Fallback for unnamed frames.
      source.onmessage = handleEvent;

      source.onerror = () => {
        if (disposed) return;
        source?.close();
        source = null;
        setStatus("reconnecting");
        timer = window.setTimeout(connect, retryDelay);
        retryDelay = Math.min(retryDelay + 2_000, 15_000);
      };
    };

    setStatus((prev) => (prev === "connected" ? "reconnecting" : "connecting"));
    connect();

    return () => {
      disposed = true;
      if (timer !== null) window.clearTimeout(timer);
      source?.close();
      source = null;
    };
  }, [queryClient, attempt]);

  const value = useMemo<StreamState>(
    () => ({
      status,
      lastEvent,
      lastEventId: lastEventIdRef.current,
      events,
      reconnect: () => setAttempt((n) => n + 1),
    }),
    [status, lastEvent, events],
  );

  return <StreamContext.Provider value={value}>{children}</StreamContext.Provider>;
}

export function useStream(): StreamState {
  const context = useContext(StreamContext);
  if (!context) throw new Error("useStream must be used inside StreamProvider");
  return context;
}
