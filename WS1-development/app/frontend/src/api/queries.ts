/** Shared reference-data queries (cached across screens). */
import { useQuery } from "@tanstack/react-query";

import { api } from "./client";
import type {
  AssetOut,
  ControlOut,
  Methodology,
  ObligationOut,
  ServiceOut,
  SettingsOut,
  UserSummary,
} from "./types";

const LONG = 5 * 60 * 1000;

export const useServices = () =>
  useQuery({ queryKey: ["services"], queryFn: () => api.get<ServiceOut[]>("/services"), staleTime: LONG });

export const useObligations = () =>
  useQuery({
    queryKey: ["obligations"],
    queryFn: () => api.get<ObligationOut[]>("/obligations"),
    staleTime: LONG,
  });

export const useControls = () =>
  useQuery({ queryKey: ["controls"], queryFn: () => api.get<ControlOut[]>("/controls"), staleTime: LONG });

export const useAssets = () =>
  useQuery({ queryKey: ["assets"], queryFn: () => api.get<AssetOut[]>("/assets"), staleTime: LONG });

export const useUsers = () =>
  useQuery({
    queryKey: ["users", "active"],
    queryFn: () => api.get<UserSummary[]>("/users", { active: true }),
    staleTime: LONG,
  });

export const useSettings = () =>
  useQuery({ queryKey: ["settings"], queryFn: () => api.get<SettingsOut>("/settings"), staleTime: LONG });

export const useMethodology = () =>
  useQuery({ queryKey: ["methodology"], queryFn: () => api.get<Methodology>("/methodology"), staleTime: LONG });
