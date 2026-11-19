import { MoonIcon, SunIcon } from "@heroicons/react/24/outline";
import { useQuery } from "@tanstack/react-query";

import { api } from "../api/client";
import type { TimezoneOption } from "../api/types";
import { useAuth } from "../auth/AuthContext";
import { useToast } from "../components/Toast";
import { cx } from "../components/ui";
import { deviceZone } from "../lib/time";
import { useTheme } from "../theme/useTheme";

const FALLBACK: TimezoneOption[] = [
  { value: "system", label: "System" },
  { value: "Africa/Lagos", label: "WAT: Lagos, Nigeria (UTC+1)" },
  { value: "Africa/Kampala", label: "EAT: Kampala, Uganda (UTC+3)" },
  { value: "UTC", label: "UTC" },
];

export function ThemeToggle({ onDark }: { onDark?: boolean }) {
  const { theme, toggle } = useTheme();
  const next = theme === "dark" ? "light" : "dark";
  return (
    <button
      type="button"
      className={onDark ? "p-2 text-white/80 hover:text-white" : "btn-ghost btn-sm px-2"}
      onClick={toggle}
      aria-label={`Switch to ${next} theme`}
      title={`Switch to ${next} theme`}
    >
      {theme === "dark" ? <SunIcon className="h-5 w-5" aria-hidden /> : <MoonIcon className="h-5 w-5" aria-hidden />}
    </button>
  );
}

/** Display zone only; deadlines are always evaluated in WAT by the server (PLAN.md §2.7). */
export function TimezoneSelect({ compact, onDark }: { compact?: boolean; onDark?: boolean }) {
  const { tzPreference, setTimezone } = useAuth();
  const toast = useToast();
  const { data } = useQuery({
    queryKey: ["timezones"],
    queryFn: () => api.get<TimezoneOption[]>("/timezones"),
    staleTime: Infinity,
  });
  const options = (data ?? FALLBACK).map((o) =>
    o.value === "system" ? { ...o, label: `System (${deviceZone()})` } : o,
  );
  return (
    <label className="flex items-center gap-2">
      <span className={compact ? "sr-only" : cx("label-caps hidden whitespace-nowrap xl:inline", onDark && "text-white/70")}>
        Times in
      </span>
      <select
        aria-label="Display time zone"
        className={compact ? "input w-full py-2" : "input max-w-[15rem] py-1 text-xs"}
        value={tzPreference}
        onChange={async (e) => {
          try {
            await setTimezone(e.target.value);
          } catch (error) {
            toast.error(error);
          }
        }}
      >
        {options.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
      </select>
    </label>
  );
}
