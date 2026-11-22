/** Treatment and governance dialogs and the evidence list (U3), shared by several screens. */
import { ArrowDownTrayIcon, ArrowPathIcon, PaperClipIcon } from "@heroicons/react/24/outline";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import type { FormEvent, ReactNode } from "react";

import { ApiError, api, download } from "../api/client";
import { useControls, useSettings, useUsers } from "../api/queries";
import type {
  AcceptanceOut,
  ActionOut,
  DecisionOut,
  EvidenceOut,
  EvidenceTarget,
  ReassessmentOut,
  RiskDetail,
  Strategy,
} from "../api/types";
import { IMPACT_LABELS, LIKELIHOOD_LABELS, bandFor, formatBytes, previewExplanation, titleCase } from "../lib/format";
import { isoDay } from "../lib/time";
import { Modal } from "./Modal";
import { BandBadge, Explanation } from "./risk";
import { useToast } from "./Toast";
import { DateTime, Loading, Notice, SelectField, TextArea, TextField } from "./ui";

export const EVIDENCE_ACCEPT = ".pdf,.png,.jpg,.jpeg,.csv,.txt,.xlsx,.docx";
const MAX_BYTES = 4 * 1024 * 1024;

/** Refresh everything a treatment change can affect. */
export function useInvalidateRisk() {
  const qc = useQueryClient();
  return () => {
    for (const key of ["risk", "risks", "dashboard", "actions", "acceptances", "decisions", "evidence", "audit"]) {
      qc.invalidateQueries({ queryKey: [key] });
    }
  };
}

function FileField({
  label,
  file,
  onChange,
  required,
  hint,
}: {
  label: string;
  file: File | null;
  onChange: (f: File | null) => void;
  required?: boolean;
  hint?: ReactNode;
}) {
  const tooBig = file && file.size > MAX_BYTES;
  return (
    <div className="flex flex-col gap-1">
      <label className="label-caps">
        {label}
        {required && <span className="text-danger"> *</span>}
        <input
          type="file"
          accept={EVIDENCE_ACCEPT}
          required={required}
          className="input mt-1 font-normal normal-case tracking-normal file:mr-3 file:border-0 file:bg-container file:px-3 file:py-1 file:text-ink"
          onChange={(e) => onChange(e.target.files?.[0] ?? null)}
        />
      </label>
      <div className={`text-xs ${tooBig ? "font-semibold text-danger" : "text-muted"}`}>
        {tooBig
          ? `This file is ${formatBytes(file.size)}; the limit is 4 MB.`
          : (hint ?? "PDF, PNG, JPG, CSV, TXT, XLSX or DOCX, up to 4 MB. Stored privately; never public.")}
      </div>
    </div>
  );
}

function ScaleSelect({
  label,
  value,
  onChange,
  labels,
}: {
  label: string;
  value: number;
  onChange: (n: number) => void;
  labels: Record<number, string>;
}) {
  return (
    <SelectField
      label={label}
      value={value}
      required
      onChange={(e) => onChange(Number(e.target.value))}
      options={[1, 2, 3, 4, 5].map((n) => ({ value: n, label: `${n} · ${labels[n]}` }))}
    />
  );
}

function Footer({ busy, onClose, label, disabled }: { busy: boolean; onClose: () => void; label: string; disabled?: boolean }) {
  return (
    <>
      <button type="button" className="btn-secondary" onClick={onClose} disabled={busy}>
        Cancel
      </button>
      <button type="submit" form="dialog-form" className="btn-primary" disabled={busy || disabled}>
        {busy ? "Saving…" : label}
      </button>
    </>
  );
}

function errorText(error: unknown): string | null {
  if (!error) return null;
  return error instanceof ApiError || error instanceof Error ? error.message : "Something went wrong.";
}

// ── Assessment preview ────────────────────────────────────────────────────────────────────

export function AssessmentInputs({
  likelihood,
  impact,
  setLikelihood,
  setImpact,
}: {
  likelihood: number;
  impact: number;
  setLikelihood: (n: number) => void;
  setImpact: (n: number) => void;
}) {
  const settings = useSettings();
  const score = likelihood * impact;
  return (
    <div className="flex flex-col gap-3">
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        <ScaleSelect label="Likelihood" value={likelihood} onChange={setLikelihood} labels={LIKELIHOOD_LABELS} />
        <ScaleSelect label="Impact" value={impact} onChange={setImpact} labels={IMPACT_LABELS} />
      </div>
      <div className="flex items-center gap-3">
        <span className="mono-data text-2xl font-bold">{score}</span>
        <BandBadge band={bandFor(score)} />
        <span className="text-xs text-muted">Preview; the server calculates and stores the result.</span>
      </div>
      <Explanation text={previewExplanation(likelihood, impact, settings.data)} />
    </div>
  );
}

// ── Decision ──────────────────────────────────────────────────────────────────────────────

export function DecisionDialog({ risk, open, onClose }: { risk: RiskDetail; open: boolean; onClose: () => void }) {
  const toast = useToast();
  const refresh = useInvalidateRisk();
  const [strategy, setStrategy] = useState<Strategy>("reduce");
  const [justification, setJustification] = useState("");
  const [targetL, setTargetL] = useState<number | "">("");
  const [targetI, setTargetI] = useState<number | "">("");
  const m = useMutation({
    mutationFn: () =>
      api.post<DecisionOut>(`/risks/${risk.id}/decisions`, {
        strategy,
        justification,
        target_likelihood: targetL === "" ? null : targetL,
        target_impact: targetI === "" ? null : targetI,
      }),
    onSuccess: () => {
      toast.success(`Treatment decision recorded: ${titleCase(strategy)}.`);
      refresh();
      onClose();
    },
  });
  const submit = (e: FormEvent) => {
    e.preventDefault();
    m.mutate();
  };
  return (
    <Modal open={open} onClose={onClose} title={`Treatment decision for ${risk.risk_code}`} footer={<Footer busy={m.isPending} onClose={onClose} label="Record decision" />}>
      <form id="dialog-form" onSubmit={submit} className="flex flex-col gap-4">
        {m.error && <Notice tone="danger">{errorText(m.error)}</Notice>}
        <SelectField
          label="Strategy"
          value={strategy}
          onChange={(e) => setStrategy(e.target.value as Strategy)}
          options={(["reduce", "accept", "transfer", "avoid"] as Strategy[]).map((s) => ({ value: s, label: titleCase(s) }))}
          hint={strategy === "accept" ? "Accepting a risk above appetite also needs an approved acceptance request." : undefined}
        />
        <TextArea label="Justification" required minLength={10} value={justification} onChange={(e) => setJustification(e.target.value)} hint="At least 10 characters." />
        <div className="grid grid-cols-2 gap-3">
          <SelectField
            label="Target likelihood"
            value={targetL}
            placeholder="Not set"
            onChange={(e) => setTargetL(e.target.value ? Number(e.target.value) : "")}
            options={[1, 2, 3, 4, 5].map((n) => ({ value: n, label: `${n} · ${LIKELIHOOD_LABELS[n]}` }))}
          />
          <SelectField
            label="Target impact"
            value={targetI}
            placeholder="Not set"
            onChange={(e) => setTargetI(e.target.value ? Number(e.target.value) : "")}
            options={[1, 2, 3, 4, 5].map((n) => ({ value: n, label: `${n} · ${IMPACT_LABELS[n]}` }))}
          />
        </div>
        {targetL !== "" && targetI !== "" && (
          <div className="text-sm">
            Target residual score: <span className="mono-data font-bold">{targetL * targetI}</span>{" "}
            <BandBadge band={bandFor(targetL * targetI)} />
          </div>
        )}
      </form>
    </Modal>
  );
}

// ── Actions ───────────────────────────────────────────────────────────────────────────────

export function ActionDialog({
  risk,
  action,
  open,
  onClose,
}: {
  risk: { id: number; risk_code: string; owner?: { id: number } };
  action?: ActionOut;
  open: boolean;
  onClose: () => void;
}) {
  const toast = useToast();
  const refresh = useInvalidateRisk();
  const users = useUsers();
  const controls = useControls();
  const [title, setTitle] = useState(action?.title ?? "");
  const [description, setDescription] = useState(action?.description ?? "");
  const [ownerId, setOwnerId] = useState<number | "">(action?.owner.id ?? risk.owner?.id ?? "");
  const [due, setDue] = useState(action?.due_date ?? "");
  const [cost, setCost] = useState(action?.estimated_cost_ngn ?? "");
  const [controlIds, setControlIds] = useState<number[]>(action?.controls.map((c) => c.id) ?? []);
  const [filter, setFilter] = useState("");

  const m = useMutation({
    mutationFn: () => {
      const body = {
        title,
        description: description || null,
        owner_id: ownerId === "" ? undefined : ownerId,
        due_date: due || null,
        estimated_cost_ngn: cost === "" ? null : cost,
        control_ids: controlIds,
      };
      return action
        ? api.patch<ActionOut>(`/actions/${action.id}`, body)
        : api.post<ActionOut>(`/risks/${risk.id}/actions`, body);
    },
    onSuccess: (saved) => {
      toast.success(action ? `${saved.action_code} updated.` : `${saved.action_code} created, due ${saved.due_date}.`);
      refresh();
      onClose();
    },
  });

  const visibleControls = (controls.data ?? []).filter((c) =>
    `${c.framework} ${c.control_ref} ${c.short_title}`.toLowerCase().includes(filter.toLowerCase()),
  );

  return (
    <Modal
      wide
      open={open}
      onClose={onClose}
      title={action ? `Edit ${action.action_code}` : `New treatment action for ${risk.risk_code}`}
      footer={<Footer busy={m.isPending} onClose={onClose} label={action ? "Save changes" : "Create action"} />}
    >
      <form
        id="dialog-form"
        onSubmit={(e) => {
          e.preventDefault();
          m.mutate();
        }}
        className="flex flex-col gap-4"
      >
        {m.error && <Notice tone="danger">{errorText(m.error)}</Notice>}
        <TextField label="Title" required minLength={5} value={title} onChange={(e) => setTitle(e.target.value)} />
        <TextArea label="Description" value={description} onChange={(e) => setDescription(e.target.value)} />
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
          <SelectField
            label="Action owner"
            required
            value={ownerId}
            placeholder="Choose…"
            onChange={(e) => setOwnerId(e.target.value ? Number(e.target.value) : "")}
            options={(users.data ?? []).map((u) => ({ value: u.id, label: u.full_name }))}
          />
          <TextField
            label="Due date"
            type="date"
            value={due}
            min={action ? undefined : isoDay(0)}
            onChange={(e) => setDue(e.target.value)}
            hint={action ? undefined : "Leave empty to use the band's SLA."}
          />
          <TextField label="Estimated cost (₦)" type="number" min={0} step="1000" value={cost} onChange={(e) => setCost(e.target.value)} />
        </div>
        <fieldset className="flex flex-col gap-2">
          <legend className="label-caps mb-1">Framework controls ({controlIds.length} selected)</legend>
          <input className="input" type="search" placeholder="Filter controls (e.g. PR.AA, 8.5, CIS 6)" value={filter} onChange={(e) => setFilter(e.target.value)} aria-label="Filter controls" />
          <div className="max-h-48 overflow-y-auto border border-line">
            {controls.isLoading ? (
              <Loading />
            ) : (
              visibleControls.map((c) => (
                <label key={c.id} className="flex items-start gap-2 border-b border-line px-3 py-1.5 text-sm last:border-0 hover:bg-hover">
                  <input
                    type="checkbox"
                    className="mt-1"
                    checked={controlIds.includes(c.id)}
                    onChange={(e) =>
                      setControlIds((ids) => (e.target.checked ? [...ids, c.id] : ids.filter((x) => x !== c.id)))
                    }
                  />
                  <span>
                    <span className="mono-data">
                      {c.framework} {c.control_ref}
                    </span>{" "}
                    {c.short_title}
                  </span>
                </label>
              ))
            )}
          </div>
        </fieldset>
      </form>
    </Modal>
  );
}

export function CompleteActionDialog({ action, open, onClose }: { action: ActionOut; open: boolean; onClose: () => void }) {
  const toast = useToast();
  const refresh = useInvalidateRisk();
  const [note, setNote] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const m = useMutation({
    mutationFn: () => {
      const form = new FormData();
      form.set("note", note);
      if (file) form.set("file", file);
      return api.upload<ActionOut>(`/actions/${action.id}/complete`, form);
    },
    onSuccess: (done) => {
      toast.success(`${done.action_code} completed. The risk now awaits reassessment.`);
      refresh();
      onClose();
    },
  });
  return (
    <Modal open={open} onClose={onClose} title={`Complete ${action.action_code}`} footer={<Footer busy={m.isPending} onClose={onClose} label="Complete with evidence" disabled={!file || file.size > MAX_BYTES} />}>
      <form
        id="dialog-form"
        onSubmit={(e) => {
          e.preventDefault();
          m.mutate();
        }}
        className="flex flex-col gap-4"
      >
        {m.error && <Notice tone="danger">{errorText(m.error)}</Notice>}
        <Notice>
          Completing an action needs evidence. The risk's score does <strong>not</strong> change: it moves to
          "Awaiting reassessment" until an analyst reassesses it with its own evidence.
        </Notice>
        <div className="text-sm font-medium">{action.title}</div>
        <TextArea label="Completion note" required minLength={5} value={note} onChange={(e) => setNote(e.target.value)} />
        <FileField label="Evidence file" required file={file} onChange={setFile} />
      </form>
    </Modal>
  );
}

// ── Reassessment ──────────────────────────────────────────────────────────────────────────

export function ReassessDialog({ risk, open, onClose }: { risk: RiskDetail; open: boolean; onClose: () => void }) {
  const toast = useToast();
  const refresh = useInvalidateRisk();
  const [likelihood, setLikelihood] = useState(risk.current?.likelihood ?? 3);
  const [impact, setImpact] = useState(risk.current?.impact ?? 3);
  const [rationale, setRationale] = useState("");
  const [closeRisk, setCloseRisk] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const m = useMutation({
    mutationFn: () => {
      const form = new FormData();
      form.set("likelihood", String(likelihood));
      form.set("impact", String(impact));
      form.set("rationale", rationale);
      form.set("close_risk", String(closeRisk));
      if (file) form.set("file", file);
      return api.upload<ReassessmentOut>(`/risks/${risk.id}/reassessments`, form);
    },
    onSuccess: (r) => {
      toast.success(`${risk.risk_code} reassessed: ${r.original_score ?? "?"} → ${r.score}.`);
      refresh();
      onClose();
    },
  });
  return (
    <Modal wide open={open} onClose={onClose} title={`Reassess ${risk.risk_code}`} footer={<Footer busy={m.isPending} onClose={onClose} label="Save reassessment" disabled={!file || file.size > MAX_BYTES} />}>
      <form
        id="dialog-form"
        onSubmit={(e) => {
          e.preventDefault();
          m.mutate();
        }}
        className="flex flex-col gap-4"
      >
        {m.error && <Notice tone="danger">{errorText(m.error)}</Notice>}
        <div className="text-sm text-muted">
          Current: <span className="mono-data">{risk.current ? `${risk.current.likelihood}×${risk.current.impact}=${risk.current.score}` : "not assessed"}</span>
          {" · "}Original: <span className="mono-data">{risk.original_score ?? "—"}</span>. The earlier assessments stay in the history unchanged.
        </div>
        <AssessmentInputs likelihood={likelihood} impact={impact} setLikelihood={setLikelihood} setImpact={setImpact} />
        <TextArea label="Rationale" required minLength={10} value={rationale} onChange={(e) => setRationale(e.target.value)} hint="Why the scores changed, citing the evidence." />
        <FileField label="Evidence for the new scores" required file={file} onChange={setFile} />
        <label className="flex items-center gap-2">
          <input type="checkbox" checked={closeRisk} onChange={(e) => setCloseRisk(e.target.checked)} />
          Close the risk after this reassessment
        </label>
      </form>
    </Modal>
  );
}

// ── Acceptance ────────────────────────────────────────────────────────────────────────────

export function RequestAcceptanceDialog({ risk, open, onClose }: { risk: RiskDetail; open: boolean; onClose: () => void }) {
  const toast = useToast();
  const refresh = useInvalidateRisk();
  const [justification, setJustification] = useState("");
  const [expiry, setExpiry] = useState(isoDay(90));
  const m = useMutation({
    mutationFn: () =>
      api.post<AcceptanceOut>(`/risks/${risk.id}/acceptances`, { justification, proposed_expiry: expiry }),
    onSuccess: () => {
      toast.success(`Acceptance requested for ${risk.risk_code}. An approver will decide.`);
      refresh();
      onClose();
    },
  });
  return (
    <Modal open={open} onClose={onClose} title={`Request risk acceptance for ${risk.risk_code}`} footer={<Footer busy={m.isPending} onClose={onClose} label="Send request" disabled={justification.trim().length < 30} />}>
      <form
        id="dialog-form"
        onSubmit={(e) => {
          e.preventDefault();
          m.mutate();
        }}
        className="flex flex-col gap-4"
      >
        {m.error && <Notice tone="danger">{errorText(m.error)}</Notice>}
        <Notice>
          An approver who doesn't own this risk decides (segregation of duties). Accepted risks must be reviewed
          again before the expiry date.
        </Notice>
        <TextArea
          label="Business justification"
          required
          minLength={30}
          rows={4}
          value={justification}
          onChange={(e) => setJustification(e.target.value)}
          hint={`${justification.trim().length} of at least 30 characters.`}
        />
        <TextField label="Proposed expiry" type="date" required min={isoDay(1)} value={expiry} onChange={(e) => setExpiry(e.target.value)} />
      </form>
    </Modal>
  );
}

export function DecideAcceptanceDialog({ acceptance, open, onClose }: { acceptance: AcceptanceOut; open: boolean; onClose: () => void }) {
  const toast = useToast();
  const refresh = useInvalidateRisk();
  const [decision, setDecision] = useState<"approve" | "reject">("approve");
  const [comment, setComment] = useState("");
  const [expiry, setExpiry] = useState(acceptance.proposed_expiry);
  const m = useMutation({
    mutationFn: () =>
      api.post<AcceptanceOut>(`/acceptances/${acceptance.id}/decision`, {
        decision,
        comment,
        expiry_date: decision === "approve" ? expiry : null,
      }),
    onSuccess: (a) => {
      toast.success(`Acceptance for ${a.risk.risk_code as string} ${a.status}.`);
      refresh();
      onClose();
    },
  });
  return (
    <Modal open={open} onClose={onClose} title={`Decide acceptance for ${acceptance.risk.risk_code as string}`} footer={<Footer busy={m.isPending} onClose={onClose} label={decision === "approve" ? "Approve" : "Reject"} disabled={comment.trim().length < 10} />}>
      <form
        id="dialog-form"
        onSubmit={(e) => {
          e.preventDefault();
          m.mutate();
        }}
        className="flex flex-col gap-4"
      >
        {m.error && <Notice tone="danger">{errorText(m.error)}</Notice>}
        <div>
          <div className="label-caps">Requested by {acceptance.requested_by.full_name}</div>
          <p className="mt-1 whitespace-pre-line">{acceptance.justification}</p>
        </div>
        {acceptance.current && <Explanation text={acceptance.current.explanation} />}
        <fieldset className="flex gap-4">
          <legend className="label-caps mb-1">Decision</legend>
          {(["approve", "reject"] as const).map((d) => (
            <label key={d} className="flex items-center gap-2">
              <input type="radio" name="decision" checked={decision === d} onChange={() => setDecision(d)} />
              {titleCase(d)}
            </label>
          ))}
        </fieldset>
        <TextArea label="Comment" required minLength={10} value={comment} onChange={(e) => setComment(e.target.value)} hint="At least 10 characters; recorded in the audit log." />
        {decision === "approve" && (
          <TextField label="Expiry date" type="date" required min={isoDay(1)} value={expiry} onChange={(e) => setExpiry(e.target.value)} />
        )}
      </form>
    </Modal>
  );
}

// ── Evidence ──────────────────────────────────────────────────────────────────────────────

export function UploadEvidenceDialog({
  target,
  supersedes,
  open,
  onClose,
}: {
  target: { type: EvidenceTarget; id: number; label: string };
  supersedes?: EvidenceOut;
  open: boolean;
  onClose: () => void;
}) {
  const toast = useToast();
  const refresh = useInvalidateRisk();
  const [description, setDescription] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const m = useMutation({
    mutationFn: () => {
      const form = new FormData();
      form.set("target_type", target.type);
      form.set("target_id", String(target.id));
      if (description) form.set("description", description);
      if (supersedes) form.set("supersedes_id", String(supersedes.id));
      if (file) form.set("file", file);
      return api.upload<EvidenceOut>("/evidence", form);
    },
    onSuccess: (ev) => {
      toast.success(`Evidence "${ev.original_name}" uploaded.`);
      refresh();
      onClose();
    },
  });
  return (
    <Modal
      open={open}
      onClose={onClose}
      title={supersedes ? `Replace "${supersedes.original_name}"` : `Add evidence to ${target.label}`}
      footer={<Footer busy={m.isPending} onClose={onClose} label="Upload" disabled={!file || file.size > MAX_BYTES} />}
    >
      <form
        id="dialog-form"
        onSubmit={(e) => {
          e.preventDefault();
          m.mutate();
        }}
        className="flex flex-col gap-4"
      >
        {m.error && <Notice tone="danger">{errorText(m.error)}</Notice>}
        {supersedes && (
          <Notice>The earlier file is kept and marked as superseded; evidence is never edited or deleted.</Notice>
        )}
        <TextField label="Description" maxLength={500} value={description} onChange={(e) => setDescription(e.target.value)} />
        <FileField label="File" required file={file} onChange={setFile} />
      </form>
    </Modal>
  );
}

export function EvidenceList({
  target,
  canUpload,
  emptyText = "No evidence yet.",
}: {
  target: { type: EvidenceTarget; id: number; label: string };
  canUpload?: boolean;
  emptyText?: string;
}) {
  const toast = useToast();
  const [uploading, setUploading] = useState(false);
  const [replacing, setReplacing] = useState<EvidenceOut | null>(null);
  const q = useQuery({
    queryKey: ["evidence", target.type, target.id],
    queryFn: () => api.get<EvidenceOut[]>("/evidence", { target_type: target.type, target_id: target.id }),
  });
  if (q.isLoading) return <Loading label="Loading evidence…" />;
  const rows = q.data ?? [];
  return (
    <div className="flex flex-col gap-2">
      {rows.length === 0 ? (
        <div className="text-sm text-muted">{emptyText}</div>
      ) : (
        <ul className="divide-y divide-line border border-line">
          {rows.map((ev) => (
            <li key={ev.id} className={`flex flex-col gap-1 px-3 py-2 sm:flex-row sm:items-center sm:gap-3 ${ev.superseded_by_id ? "opacity-60" : ""}`}>
              <PaperClipIcon className="hidden h-4 w-4 shrink-0 text-muted sm:block" aria-hidden />
              <div className="min-w-0 flex-1">
                <div className="truncate font-medium">
                  {ev.original_name}
                  {ev.superseded_by_id && <span className="chip ml-2">Superseded</span>}
                </div>
                <div className="text-xs text-muted">
                  {formatBytes(ev.size_bytes)} · {ev.uploaded_by.full_name} · <DateTime iso={ev.uploaded_at} />
                  {ev.description ? ` · ${ev.description}` : ""}
                </div>
                <div className="mono-data truncate text-[11px] text-muted" title="SHA-256 fingerprint">
                  SHA-256 {ev.sha256}
                </div>
              </div>
              <div className="flex gap-1">
                <button
                  type="button"
                  className="btn-ghost btn-sm"
                  onClick={() => download(ev.download_url.replace(/^\/api/, "")).catch(toast.error)}
                >
                  <ArrowDownTrayIcon className="h-4 w-4" aria-hidden /> Download
                </button>
                {canUpload && !ev.superseded_by_id && (
                  <button type="button" className="btn-ghost btn-sm" onClick={() => setReplacing(ev)}>
                    <ArrowPathIcon className="h-4 w-4" aria-hidden /> Replace
                  </button>
                )}
              </div>
            </li>
          ))}
        </ul>
      )}
      {canUpload && (
        <div>
          <button type="button" className="btn-secondary btn-sm" onClick={() => setUploading(true)}>
            <PaperClipIcon className="h-4 w-4" aria-hidden /> Add evidence
          </button>
        </div>
      )}
      {uploading && <UploadEvidenceDialog open target={target} onClose={() => setUploading(false)} />}
      {replacing && <UploadEvidenceDialog open target={target} supersedes={replacing} onClose={() => setReplacing(null)} />}
    </div>
  );
}
