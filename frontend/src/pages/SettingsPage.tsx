import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";

import { api } from "../api/client";
import { useSettings } from "../api/queries";
import type { SettingsOut } from "../api/types";
import { useToast } from "../components/Toast";
import { Card, DateTime, ErrorState, Loading, Notice, PageHeader, TextField } from "../components/ui";

type Key = Exclude<keyof SettingsOut, "updated_at" | "updated_by" | "org_timezone">;

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

  useEffect(() => {
    if (settings.data) {
      const next: Partial<Record<Key, number>> = {};
      for (const g of GROUPS) for (const [k] of g.fields) next[k] = settings.data[k];
      setValues(next);
    }
  }, [settings.data]);

  const save = useMutation({
    mutationFn: () => {
      const changed = Object.fromEntries(Object.entries(values).filter(([k, v]) => settings.data?.[k as Key] !== v));
      return api.patch<SettingsOut>("/settings", changed);
    },
    onSuccess: (s) => {
      qc.setQueryData(["settings"], s);
      for (const k of ["dashboard", "risks", "risk"]) qc.invalidateQueries({ queryKey: [k] });
      toast.success("Settings saved and recorded in the audit log.");
    },
  });

  if (settings.isLoading) return <Loading />;
  if (settings.error || !settings.data) return <ErrorState error={settings.error} />;
  const dirty = Object.entries(values).some(([k, v]) => settings.data[k as Key] !== v);

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
        <div>
          <button type="submit" className="btn-primary" disabled={!dirty || save.isPending}>
            {save.isPending ? "Saving…" : "Save settings"}
          </button>
        </div>
      </form>
    </>
  );
}
