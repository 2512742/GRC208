/**
 * Display-only time helpers (PLAN.md §2.7). Business rules ("today", overdue, expired) are
 * decided by the server in Africa/Lagos; the browser only formats what it is given.
 *
 * - Timestamps arrive as ISO 8601 UTC ("...Z") and are shown in the viewer's chosen zone with
 *   its abbreviation: "5 Dec 2026, 14:30 WAT".
 * - Calendar dates ("2026-12-05") have no zone and are never converted.
 */

export const SYSTEM = "system";
export const ORG_ZONE = "Africa/Lagos";
export const TZ_STORAGE_KEY = "risktrack-tz";

const ABBREVIATIONS: Record<string, string> = {
  "Africa/Lagos": "WAT",
  "Africa/Douala": "WAT",
  "Africa/Kampala": "EAT",
  "Africa/Nairobi": "EAT",
  "Africa/Accra": "GMT",
  UTC: "UTC",
};

export function deviceZone(): string {
  try {
    return Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC";
  } catch {
    return "UTC";
  }
}

/** "system" means the device's zone; anything else is an IANA name from the allow-list. */
export function resolveZone(preference: string | null | undefined): string {
  return !preference || preference === SYSTEM ? deviceZone() : preference;
}

export function zoneAbbreviation(zone: string, at: Date = new Date()): string {
  if (ABBREVIATIONS[zone]) return ABBREVIATIONS[zone];
  try {
    const part = new Intl.DateTimeFormat("en-GB", { timeZone: zone, timeZoneName: "short" })
      .formatToParts(at)
      .find((p) => p.type === "timeZoneName");
    return part?.value ?? zone;
  } catch {
    return zone;
  }
}

export function formatDateTime(iso: string | null | undefined, zone: string): string {
  if (!iso) return "—";
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return iso;
  const text = new Intl.DateTimeFormat("en-GB", {
    timeZone: zone,
    day: "numeric",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    hourCycle: "h23",
  }).format(date);
  return `${text} ${zoneAbbreviation(zone, date)}`;
}

/** Exact UTC value, for tooltips (auditors compare against UTC). */
export function formatUtc(iso: string | null | undefined): string {
  if (!iso) return "";
  const date = new Date(iso);
  return Number.isNaN(date.getTime()) ? iso : `${date.toISOString().replace(".000", "")} (UTC)`;
}

/** Calendar date, shown as-is: "2026-12-05" -> "5 Dec 2026". */
export function formatDate(day: string | null | undefined): string {
  if (!day) return "—";
  const match = /^(\d{4})-(\d{2})-(\d{2})/.exec(day);
  if (!match) return day;
  const date = new Date(Date.UTC(Number(match[1]), Number(match[2]) - 1, Number(match[3])));
  return new Intl.DateTimeFormat("en-GB", {
    timeZone: "UTC",
    day: "numeric",
    month: "short",
    year: "numeric",
  }).format(date);
}

/** Deadline hint so EAT and GMT users know when "overdue" starts. */
export function deadlineHint(day: string): string {
  return `Due ${formatDate(day)} (overdue after midnight ${zoneAbbreviation(ORG_ZONE)})`;
}

/** yyyy-mm-dd for <input type="date"> defaults, offset from today in the device's calendar. */
export function isoDay(offsetDays = 0): string {
  const d = new Date();
  d.setDate(d.getDate() + offsetDays);
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
}
