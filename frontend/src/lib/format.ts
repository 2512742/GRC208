import type { Band } from "../api/types";

export const BANDS: Band[] = ["low", "medium", "high", "critical"];

export const LIKELIHOOD_LABELS: Record<number, string> = {
  1: "Rare",
  2: "Unlikely",
  3: "Possible",
  4: "Likely",
  5: "Almost certain",
};

export const IMPACT_LABELS: Record<number, string> = {
  1: "Negligible",
  2: "Minor",
  3: "Moderate",
  4: "Major",
  5: "Severe",
};

/** Mirrors services/scoring.py so forms can preview; the server's answer is the one stored. */
export function bandFor(score: number): Band {
  if (score >= 15) return "critical";
  if (score >= 10) return "high";
  if (score >= 5) return "medium";
  return "low";
}

export function titleCase(value: string | null | undefined): string {
  if (!value) return "—";
  return value
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase())
    .replace(/\bApi\b/g, "API")
    .replace(/\bSaas\b/g, "SaaS");
}

export function sentenceCase(value: string | null | undefined): string {
  if (!value) return "—";
  const text = value.replace(/_/g, " ");
  return text.charAt(0).toUpperCase() + text.slice(1);
}

const naira = new Intl.NumberFormat("en-NG", {
  style: "currency",
  currency: "NGN",
  maximumFractionDigits: 0,
});

export function formatNaira(value: string | number | null | undefined): string {
  if (value === null || value === undefined || value === "") return "—";
  const n = typeof value === "number" ? value : Number(value);
  return Number.isFinite(n) ? naira.format(n) : String(value);
}

/** ₦30.65m style for KPI tiles. */
export function compactNaira(value: string | number | null | undefined): string {
  const n = Number(value ?? 0);
  if (!Number.isFinite(n)) return "—";
  if (n >= 1_000_000) return `₦${(n / 1_000_000).toFixed(2).replace(/\.?0+$/, "")}m`;
  if (n >= 1_000) return `₦${(n / 1_000).toFixed(1).replace(/\.0$/, "")}k`;
  return `₦${n}`;
}

export function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(2)} MB`;
}

export const ROLE_LABELS: Record<string, string> = {
  admin: "Administrator",
  analyst: "GRC analyst",
  owner: "Risk owner",
  approver: "Approver",
  auditor: "Auditor",
};

export interface ScoringPolicy {
  appetite_threshold: number;
  sla_days_critical: number;
  sla_days_high: number;
  sla_days_medium: number;
}

/** Live preview text for assessment forms, same wording as the server's explanation. */
export function previewExplanation(
  likelihood: number,
  impact: number,
  policy: ScoringPolicy | undefined,
): string {
  const score = likelihood * impact;
  const band = bandFor(score);
  const threshold = policy?.appetite_threshold ?? 10;
  let text =
    `Likelihood ${likelihood} (${LIKELIHOOD_LABELS[likelihood]}) × ` +
    `Impact ${impact} (${IMPACT_LABELS[impact]}) = ${score} → ${titleCase(band)}. `;
  text +=
    score >= threshold
      ? `Above appetite (threshold ${threshold}).`
      : `Within appetite (threshold ${threshold}).`;
  const sla =
    band === "critical"
      ? policy?.sla_days_critical
      : band === "high"
        ? policy?.sla_days_high
        : band === "medium"
          ? policy?.sla_days_medium
          : undefined;
  if (sla) text += ` Remediation due within ${sla} days.`;
  return text;
}
