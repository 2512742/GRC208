import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";

import { api } from "../api/client";
import { useSettings } from "../api/queries";
import type { SettingsOut } from "../api/types";
import { IMPACT_LABELS, LIKELIHOOD_LABELS } from "../lib/format";
import { useToast } from "../components/Toast";
import { Card, DateTime, ErrorState, KeyValue, Loading, Notice, PageHeader, TextArea, TextField } from "../components/ui";
import { useSecurity } from "./AccountPage";

type Key = Exclude<
  keyof SettingsOut,
  "updated_at" | "updated_by" | "org_timezone" | "likelihood_definitions" | "impact_definitions"
>;
type DefKey = "likelihood_definitions" | "impact_definitions";

const SCALES: { key: DefKey; title: string; labels: Record<number, string> }[] = [
  { key: "likelihood_definitions", title: "Likelihood level definitions", labels: LIKELIHOOD_LABELS },
  { key: "impact_definitions", title: "Impact level definitions", labels: IMPACT_LABELS },
];

const sameList = (a: string[] | undefined, b: string[] | undefined) =>
  !!a && !!b && a.length === b.length && a.every((v, i) => v.trim() === b[i]);

const GROUPS: { title: string; fields: [Key, string, number, number][] }[] = [
  { title: "Risk appetite", fields: [["appetite_threshold", "Appetite threshold (score)", 1, 25]] },
  {
    title: "Remediation deadlines (days)",
    fields: [
      ["sla_days_critical", "Critical", 1, 365],
      ["sla_days_high", "High", 1, 365],
      ["sla_days_medium", "Medium", 1, 730],
    ],
  },
  {
    title: "Review cycle (days)",
    fields: [
      ["review_days_critical", "Critical", 1, 365],
      ["review_days_high", "High", 1, 365],
      ["review_days_medium", "Medium", 1, 730],
      ["review_days_low", "Low", 1, 730],
      ["review_warning_days", "Warn before review", 1, 365],
    ],
  },
];

export default function SettingsPage() {
  const toast = useToast();
  const qc = useQueryClient();
  const settings = useSettings();
  const [values, setValues] = useState<Partial<Record<Key, number>>>({});
  const [defs, setDefs] = useState<Partial<Record<DefKey, string[]>>>({});

  useEffect(() => {
    if (settings.data) {
      const next: Partial<Record<Key, number>> = {};
      for (const g of GROUPS) for (const [k] of g.fields) next[k] = settings.data[k];
      setValues(next);
      setDefs({
        likelihood_definitions: [...settings.data.likelihood_definitions],
        impact_definitions: [...settings.data.impact_definitions],
      });
    }
  }, [settings.data]);

  const save = useMutation({
    mutationFn: () => {
      const changed: Record<string, unknown> = Object.fromEntries(
        Object.entries(values).filter(([k, v]) => settings.data?.[k as Key] !== v),
      );
      for (const { key } of SCALES) {
        if (!sameList(defs[key], settings.data?.[key])) changed[key] = defs[key]?.map((d) => d.trim());
      }
      return api.patch<SettingsOut>("/settings", changed);
    },
    onSuccess: (s) => {
      qc.setQueryData(["settings"], s);
      for (const k of ["dashboard", "risks", "risk", "methodology"]) qc.invalidateQueries({ queryKey: [k] });
      toast.success("Settings saved and recorded in the audit log.");
    },
  });

  if (settings.isLoading) return <Loading />;
  if (settings.error || !settings.data) return <ErrorState error={settings.error} />;
  const dirty =
    Object.entries(values).some(([k, v]) => settings.data[k as Key] !== v) ||
    SCALES.some(({ key }) => !sameList(defs[key], settings.data[key]));

  return (
    <>
      <PageHeader
        eyebrow="Administration"
        title="Governance settings"
        description={
          <>
            Last changed by {settings.data.updated_by ?? "the system"} on <DateTime iso={settings.data.updated_at} />. Business
            rules use {settings.data.org_timezone} (WAT).
          </>
        }
      />
      <form
        className="flex max-w-3xl flex-col gap-6"
        onSubmit={(e) => {
          e.preventDefault();
          save.mutate();
        }}
      >
        <Notice>
          Changes apply to new assessments and actions. Stored assessments keep the threshold in force when they were made,
          so history doesn't change retroactively.
        </Notice>
        {save.error && <Notice tone="danger">{save.error.message}</Notice>}
        {GROUPS.map((g) => (
          <Card key={g.title} title={g.title}>
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
              {g.fields.map(([key, label, min, max]) => (
                <TextField
                  key={key}
                  label={label}
                  type="number"
                  required
                  min={min}
                  max={max}
                  value={values[key] ?? ""}
                  onChange={(e) => setValues((v) => ({ ...v, [key]: Number(e.target.value) }))}
                />
              ))}
            </div>
          </Card>
        ))}
        {SCALES.map(({ key, title, labels }) => (
          <Card key={key} title={title}>
            <p className="mb-3 text-sm text-muted">
              Shown in the scoring rubric and on the How scoring works page. Write one definition per level (for
              example the outage hours and ₦ loss range agreed by the risk framework team).
            </p>
            <div className="flex flex-col gap-3">
              {[0, 1, 2, 3, 4].map((i) => (
                <TextArea
                  key={i}
                  label={`${i + 1} · ${labels[i + 1]}`}
                  required
                  minLength={3}
                  maxLength={300}
                  rows={2}
                  value={defs[key]?.[i] ?? ""}
                  onChange={(e) =>
                    setDefs((d) => {
                      const list = [...(d[key] ?? [])];
                      list[i] = e.target.value;
                      return { ...d, [key]: list };
                    })
                  }
                />
              ))}
            </div>
          </Card>
        ))}
        <div>
          <button type="submit" className="btn-primary w-full sm:w-auto" disabled={!dirty || save.isPending}>
            {save.isPending ? "Saving…" : "Save settings"}
          </button>
        </div>
      </form>
      <SecurityPolicy />
    </>
  );
}

/** Read-only: these come from the server configuration (.env), not from the database. */
function SecurityPolicy() {
  const q = useSecurity();
  if (!q.data) return null;
  const p = q.data;
  return (
    <Card title="Account security policy" className="mt-6 max-w-3xl">
      <KeyValue
        items={[
          ["Password", `At least ${p.password_min_length} characters and 5 different ones, not containing the username; Argon2 hashed`],
          ["Sign-in lockout", `${p.lockout_after_failures} failed attempts (passwords or recovery codes) pause sign-in for ${p.lockout_minutes} minutes`],
          ["Sessions", `Up to ${p.session_hours} hours; end after ${p.session_idle_minutes} minutes idle; HttpOnly cookie with CSRF protection`],
          ["Password recovery", "One-time recovery code per user (no email); otherwise an administrator sets a temporary password that must be changed at next sign-in"],
          ["Lost administrator password", "python -m app.cli reset-password --username <name> on the server"],
        ]}
      />
      <p className="mt-3 text-xs text-muted">
        Changed through the server's environment (SESSION_HOURS, SESSION_IDLE_MINUTES, LOGIN_MAX_FAILURES,
        LOGIN_LOCKOUT_MINUTES), not here, so a compromised admin account can't weaken them.
      </p>
    </Card>
  );
}
