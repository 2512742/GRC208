import { ArrowDownTrayIcon, CheckCircleIcon, ExclamationTriangleIcon, FingerPrintIcon } from "@heroicons/react/24/outline";
import { keepPreviousData, useMutation, useQuery } from "@tanstack/react-query";
import { useState } from "react";

import { api, download } from "../api/client";
import type { AuditEntryOut, AuditPage as Page, ChainReportOut } from "../api/types";
import { Modal } from "../components/Modal";
import { useToast } from "../components/Toast";
import { DataTable, DateTime, ErrorState, Loading, Notice, PageHeader, Pagination } from "../components/ui";

const ACTIONS = ["CREATE", "UPDATE", "ASSESS", "COMPLETE", "UPLOAD", "REQUEST", "APPROVE", "REJECT", "IMPORT", "EXPORT", "LOGIN", "LOGIN_FAILED", "LOGOUT", "DENIED", "SETTING"];

export default function AuditPage() {
  const toast = useToast();
  const [action, setAction] = useState("");
  const [username, setUsername] = useState("");
  const [page, setPage] = useState(1);
  const [entry, setEntry] = useState<AuditEntryOut | null>(null);
  const filters = { action: action || undefined, username: username.trim() || undefined };

  const q = useQuery({
    queryKey: ["audit", filters, page],
    queryFn: () => api.get<Page>("/audit", { ...filters, page, page_size: 50 }),
    placeholderData: keepPreviousData,
  });
  const verify = useMutation({ mutationFn: () => api.get<ChainReportOut>("/audit/verify") });

  return (
    <>
      <PageHeader
        eyebrow="Assurance"
        title="Audit log"
        description="Every change, approval, export, sign-in and refused attempt. Entries are insert-only and hash-chained, so editing or deleting one breaks the chain."
        actions={
          <>
            <button type="button" className="btn-secondary" onClick={() => download("/audit.csv", filters).catch(toast.error)}>
              <ArrowDownTrayIcon className="h-4 w-4" aria-hidden /> CSV (UTC)
            </button>
            <button type="button" className="btn-primary" disabled={verify.isPending} onClick={() => verify.mutate()}>
              <FingerPrintIcon className="h-4 w-4" aria-hidden /> {verify.isPending ? "Verifying…" : "Verify integrity"}
            </button>
          </>
        }
      />

      {verify.error && <div className="mb-4"><Notice tone="danger">{verify.error.message}</Notice></div>}
      {verify.data && (
        <div className={`mb-4 flex items-start gap-3 border p-3 ${verify.data.ok ? "border-band-low bg-band-low/10" : "border-danger bg-danger/10"}`} role="status">
          {verify.data.ok ? (
            <CheckCircleIcon className="h-6 w-6 shrink-0 text-band-low" aria-hidden />
          ) : (
            <ExclamationTriangleIcon className="h-6 w-6 shrink-0 text-danger" aria-hidden />
          )}
          <div className="min-w-0">
            <div className="font-semibold">
              {verify.data.ok
                ? `Chain intact: ${verify.data.entries_checked} entries verified.`
                : `Chain broken at entry #${verify.data.first_broken_id}: ${verify.data.problem}.`}
            </div>
            {verify.data.head_hash && (
              <div className="mono-data mt-1 break-all text-xs text-muted">
                Newest entry hash: {verify.data.head_hash}. Note it down: a later check with a different chain can reveal truncation.
              </div>
            )}
          </div>
        </div>
      )}

      <div className="card mb-4 grid grid-cols-1 gap-3 p-3 sm:grid-cols-3">
        <select aria-label="Action" className="input" value={action} onChange={(e) => { setAction(e.target.value); setPage(1); }}>
          <option value="">All actions</option>
          {ACTIONS.map((a) => (
            <option key={a} value={a}>
              {a}
            </option>
          ))}
        </select>
        <input className="input" placeholder="Username" aria-label="Username" value={username} onChange={(e) => { setUsername(e.target.value); setPage(1); }} />
        <p className="self-center text-xs text-muted">Times in your chosen zone; hover for exact UTC.</p>
      </div>

      {q.isLoading ? (
        <Loading />
      ) : q.error ? (
        <ErrorState error={q.error} retry={() => q.refetch()} />
      ) : (
        <>
          <DataTable
            caption="Audit log"
            rows={q.data!.items}
            rowKey={(e) => e.id}
            onRowClick={setEntry}
            columns={[
              { key: "id", header: "#", render: (e) => <span className="mono-data">{e.id}</span> },
              { key: "when", header: "When", render: (e) => <DateTime iso={e.occurred_at} /> },
              { key: "who", header: "User", render: (e) => <span>{e.username ?? "system"}{e.role && <span className="text-xs text-muted"> ({e.role})</span>}</span> },
              { key: "action", header: "Action", render: (e) => <span className={e.action === "DENIED" || e.action === "LOGIN_FAILED" ? "chip-strong" : "chip"}>{e.action}</span> },
              { key: "object", header: "Record", render: (e) => <span className="mono-data">{e.object_type ? `${e.object_type} ${e.object_id ?? ""}` : "—"}</span> },
              { key: "detail", header: "Detail", render: (e) => <span className="line-clamp-2">{e.detail ?? "—"}</span>, className: "max-w-md" },
            ]}
          />
          <Pagination page={q.data!.page} pageSize={q.data!.page_size} total={q.data!.total} onPage={setPage} />
        </>
      )}

      {entry && (
        <Modal open wide title={`Audit entry #${entry.id}`} onClose={() => setEntry(null)}>
          <dl className="grid grid-cols-1 gap-3 text-sm sm:grid-cols-2">
            <div><dt className="label-caps">When</dt><dd><DateTime iso={entry.occurred_at} /> <span className="text-xs text-muted">({entry.occurred_at})</span></dd></div>
            <div><dt className="label-caps">User</dt><dd>{entry.username ?? "system"} {entry.role && `(${entry.role})`}</dd></div>
            <div><dt className="label-caps">Action</dt><dd>{entry.action}</dd></div>
            <div><dt className="label-caps">Record</dt><dd className="mono-data">{entry.object_type} {entry.object_id}</dd></div>
            <div className="sm:col-span-2"><dt className="label-caps">Detail</dt><dd>{entry.detail ?? "—"}</dd></div>
            <div><dt className="label-caps">IP</dt><dd className="mono-data">{entry.ip ?? "—"}</dd></div>
            <div className="sm:col-span-2"><dt className="label-caps">Hash</dt><dd className="mono-data break-all text-xs">{entry.hash}</dd></div>
          </dl>
          {(entry.before || entry.after) && (
            <div className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-2">
              {(["before", "after"] as const).map((k) => (
                <div key={k}>
                  <div className="label-caps mb-1">{k}</div>
                  <pre className="mono-data max-h-64 overflow-auto border border-line bg-container p-2 text-xs">{entry[k] ? JSON.stringify(entry[k], null, 2) : "—"}</pre>
                </div>
              ))}
            </div>
          )}
        </Modal>
      )}
    </>
  );
}
