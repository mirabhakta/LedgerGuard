/**
 * Query keys + hooks. Keys are invalidated by the SSE provider on every event.
 */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api, type ActionListParams } from "./client";
import type { DemoRunRequest, ResolveRequest } from "./types";

export const queryKeys = {
  health: ["health"] as const,
  dashboard: ["dashboard"] as const,
  actions: (params: ActionListParams) => ["actions", params] as const,
  action: (actionId: string) => ["action", actionId] as const,
  benchmarks: ["benchmarks"] as const,
};

export function useHealth() {
  return useQuery({
    queryKey: queryKeys.health,
    queryFn: api.health,
    staleTime: 30_000,
    refetchInterval: 60_000,
  });
}

export function useDashboard() {
  return useQuery({ queryKey: queryKeys.dashboard, queryFn: api.dashboard });
}

export function useActions(params: ActionListParams) {
  return useQuery({
    queryKey: queryKeys.actions(params),
    queryFn: () => api.listActions(params),
  });
}

export function useAction(actionId: string | null) {
  return useQuery({
    queryKey: queryKeys.action(actionId ?? "none"),
    queryFn: () => api.getAction(actionId!),
    enabled: actionId !== null,
  });
}

export function useBenchmarks() {
  return useQuery({ queryKey: queryKeys.benchmarks, queryFn: api.benchmarks });
}

export function useResolveAction(actionId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: ResolveRequest) => api.resolveAction(actionId, body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["action", actionId] });
      queryClient.invalidateQueries({ queryKey: ["actions"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard"] });
    },
  });
}

export function useDemoRun() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: DemoRunRequest) => api.runDemo(body),
    onSuccess: (detail) => {
      queryClient.invalidateQueries({ queryKey: ["actions"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard"] });
      queryClient.invalidateQueries({ queryKey: ["action", detail.action_id] });
    },
  });
}
