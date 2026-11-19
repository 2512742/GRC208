import { ArrowDownTrayIcon, ArrowUpTrayIcon } from "@heroicons/react/24/outline";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { api, download } from "../api/client";
import type { ImportBatchOut, ImportType } from "../api/types";
import { useAuth } from "../auth/AuthContext";
import { ConfirmDialog } from "../components/Modal";
import { useToast } from "../components/Toast";
import { Card, DataTable, DateTime, ErrorState, Loading, Notice, PageHeader } from "../components/ui";
import { cx } from "../components/ui";

const STATUS_TONE: Record<string, string> = {
  valid: "border-band-low text-band-low",
  rejected: "chip-strong",
  duplicate: "border-band-medium text-band-medium",
};

export default function ImportsPage() {
  const { can } = useAuth();
  const toast = useToast();
  const qc = useQueryClient();
  const [kind, setKind] = useState<ImportType>("assets");
  const [file, setFile] = useState<File | null>(null);
  const [batch, setBatch] = useState<ImportBatchOut | null>(null);
  const [confirm, setConfirm] = useState(false);
  const history = useQuery({ queryKey: ["imports"], queryFn: () => api.get<ImportBatchOut[]>("/imports") });

  const refreshAll = () => {
    for (const k of ["imports", "assets", "risks", "dashboard", "services"]) qc.invalidateQueries({ queryKey: [k] });
  };

  const preview = useMutation({
    mutationFn: () => {
      const form = new FormData();
      form.set("file", file!);
      return api.upload<ImportBatchOut>(`/imports/${kind}`, form);
    },
    onSuccess: (b) => {
      setBatch(b);
      qc.invalidateQueries({ queryKey: ["imports"] });
    },
  });
  const commit = useMutation({
    mutationFn: (id: number) => api.post<ImportBatchOut>(`/imports/${id}/commit`),
    onSuccess: (b) => {
      setBatch(b);
      const created = b.rows.filter((r) => r.created).map((r) => r.created);
      toast.success(created.length ? `Imported ${created.length}: ${created.join(", ")}.` : "Nothing new to import.");
      refreshAll();
    },
    onError: toast.error,
  });
  const cancel = useMutation({
    mutationFn: (id: number) => api.post<ImportBatchOut>(`/imports/${id}/cancel`),
    onSuccess: (b) => {
      setBatch(b);
      toast.success("Import cancelled; nothing was created.");
      qc.invalidateQueries({ queryKey: ["imports"] });
    },
    onError: toast.error,
  });

  return (
    <>
      <PageHeader
        eyebrow="Data"
        title="CSV import"
        description="Two steps: upload to preview every row with reasons, then commit. Nothing is created by a preview, and each row is checked again on commit."
      />
      <div className="grid grid-cols-1 gap-6 xl:grid-cols-3">
        <Card title="1. Choose and upload">
          <div className="flex flex-col gap-4">
            <fieldset className="flex gap-4">
              <legend className="label-caps mb-1">What are you importing?</legend>
              {(["assets", "risks"] as ImportType[]).map((k) => (
                <label key={k} className="flex items-center gap-2">
                  <input type="radio" name="kind" checked={kind === k} onChange={() => setKind(k)} />
                  {k === "assets" ? "Assets" : "Risks"}
                </label>
              ))}
            </fieldset>
            {kind === "risks" && !can("create_risk") && (
              <Notice tone="warning">Your role can import assets but not risks.</Notice>
            )}
            <button
              type="button"
              className="btn-secondary w-fit"
              onClick={() => download(`/imports/templates/${kind}.csv`).catch(toast.error)}
            >
              <ArrowDownTrayIcon className="h-4 w-4" aria-hidden /> Download the {kind} template
            </button>
            <label className="label-caps">
              CSV file (UTF-8)
              <input
                type="file"
                accept=".csv,text/csv"
                className="input mt-1 font-normal normal-case tracking-normal file:mr-3 file:border-0 file:bg-container file:px-3 file:py-1 file:text-ink"
                onChange={(e) => {
                  setFile(e.target.files?.[0] ?? null);
                  setBatch(null);
                  preview.reset();
                }}
              />
            </label>
            {preview.error && <Notice tone="danger">{preview.error.message}</Notice>}
            <button type="button" className="btn-primary" disabled={!file || preview.isPending} onClick={() => preview.mutate()}>
              <ArrowUpTrayIcon className="h-4 w-4" aria-hidden /> {preview.isPending ? "Checking…" : "Upload and preview"}
            </button>
          </div>
        </Card>

        <Card title="2. Review and commit" className="xl:col-span-2">
          {!batch ? (
            <div className="text-muted">Upload a file to see each row's result here.</div>
          ) : (
            <BatchView
              batch={batch}
              busy={commit.isPending || cancel.isPending}
              onCommit={() => setConfirm(true)}
              onCancel={() => cancel.mutate(batch.id)}
            />
          )}
        </Card>
      </div>

      <div className="mt-6">
        <Card title="Earlier imports" bodyClassName="p-0 md:p-0">
          {history.isLoading ? (
            <Loading />
          ) : history.error ? (
            <ErrorState error={history.error} />
          ) : (
            <div className="p-2 md:p-0">
              <DataTable
                caption="Earlier imports"
                rows={history.data ?? []}
                rowKey={(b) => b.id}
                onRowClick={(b) => setBatch(b)}
                empty="No imports yet."
                columns={[
                  { key: "id", header: "#", render: (b) => <span className="mono-data">{b.id}</span> },
                  { key: "file", header: "File", render: (b) => b.file_name ?? "—" },
                  { key: "type", header: "Type", render: (b) => b.import_type },
                  { key: "status", header: "Status", render: (b) => <span className="chip">{b.status}</span> },
                  { key: "rows", header: "Valid / rejected / duplicate", render: (b) => <span className="mono-data">{b.valid_rows} / {b.rejected_rows} / {b.duplicate_rows}</span> },
                  { key: "by", header: "Uploaded", render: (b) => <span>{b.uploaded_by} · <DateTime iso={b.uploaded_at} /></span> },
                ]}
              />
            </div>
          )}
        </Card>
      </div>

      {batch && (
        <ConfirmDialog
          open={confirm}
          title="Commit this import?"
          message={`${batch.valid_rows} valid row(s) will be created. Rejected and duplicate rows are skipped. Each row is re-checked now, in case the register changed since the preview.`}
          confirmLabel="Commit"
          onConfirm={() => commit.mutateAsync(batch.id).then(() => undefined)}
          onClose={() => setConfirm(false)}
        />
      )}
    </>
  );
}

function BatchView({
  batch,
  busy,
  onCommit,
  onCancel,
}: {
  batch: ImportBatchOut;
  busy: boolean;
  onCommit: () => void;
  onCancel: () => void;
}) {
  const open = batch.status === "previewed";
  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-center gap-2">
        <span className="chip">{batch.status}</span>
        <span className="font-medium">{batch.file_name}</span>
        <span className="text-xs text-muted">
          {batch.total_rows} rows · {batch.valid_rows} valid · {batch.rejected_rows} rejected · {batch.duplicate_rows} duplicate
        </span>
      </div>
      <div className="max-h-[28rem] overflow-auto border border-line">
        <table className="table-base text-xs">
          <thead className="sticky top-0 bg-surface">
            <tr>
              <th>Row</th>
              <th>Result</th>
              <th>Values</th>
              <th>Reasons</th>
            </tr>
          </thead>
          <tbody>
            {batch.rows.map((r) => (
              <tr key={r.row}>
                <td className="mono-data">{r.row}</td>
                <td>
                  <span className={cx("chip", STATUS_TONE[r.status])}>{r.status}</span>
                  {r.created && <div className="mono-data mt-1 font-bold">{r.created}</div>}
                </td>
                <td className="max-w-[16rem] break-words text-muted">
                  {Object.entries(r.values as Record<string, unknown>)
                    .filter(([, v]) => v !== "" && v !== null)
                    .slice(0, 4)
                    .map(([k, v]) => `${k}: ${String(v)}`)
                    .join(" · ")}
                </td>
                <td className={r.reasons.length ? "font-medium text-danger" : "text-muted"}>{r.reasons.join("; ") || "OK"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {open && (
        <div className="flex flex-wrap gap-2">
          <button type="button" className="btn-primary" disabled={busy || batch.valid_rows === 0} onClick={onCommit}>
            Commit {batch.valid_rows} valid row{batch.valid_rows === 1 ? "" : "s"}
          </button>
          <button type="button" className="btn-secondary" disabled={busy} onClick={onCancel}>
            Cancel import
          </button>
        </div>
      )}
      <p className="text-xs text-muted">The uploaded file is kept as evidence, and the import is recorded in the audit log.</p>
    </div>
  );
}
