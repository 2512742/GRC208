import { PencilSquareIcon, PlusIcon } from "@heroicons/react/24/outline";
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Link, useParams } from "react-router-dom";

import { api } from "../api/client";
import type { AcceptanceOut, ActionOut, AuditPage, DecisionOut, RiskDetail, RiskPage } from "../api/types";
import { useAuth, useMe } from "../auth/AuthContext";
import { BandBadge, Explanation, ScoreBadge, StatusChip, residualSummary } from "../components/risk";
import {
  ActionDialog,
  CompleteActionDialog,
  DecideAcceptanceDialog,
  DecisionDialog,
  EvidenceList,
  ReassessDialog,
  RequestAcceptanceDialog,
} from "../components/treatment";
import { Card, DateOnly, DateTime, EmptyState, ErrorState, KeyValue, Loading, Notice, PageHeader, Tabs } from "../components/ui";
import { bandFor, formatNaira, titleCase } from "../lib/format";
import { deadlineHint } from "../lib/time";

type Tab = "history" | "treatment" | "acceptance" | "evidence" | "audit";

/** Route by risk code (R-013); the API addresses risks by id, so resolve the code first. */
function useRiskByCode(code: string) {
  return useQuery({
    queryKey: ["risk", code],
    queryFn: async () => {
      const page = await api.get<RiskPage>("/risks", { q: code, page_size: 100 });
      const hit = page.items.find((r) => r.risk_code.toLowerCase() === code.toLowerCase());
      if (!hit) throw new Error(`Risk ${code} not found.`);
      return api.get<RiskDetail>(`/risks/${hit.id}`);
    },
  });
}

export default function RiskDetailPage() {
  const { code = "" } = useParams();
  const me = useMe();
  const { can } = useAuth();
  const [tab, setTab] = useState<Tab>("history");
  const [dialog, setDialog] = useState<null | "decision" | "action" | "reassess" | "acceptance">(null);

  const q = useRiskByCode(code);
  const risk = q.data;
  const riskId = risk?.id;

  const decisions = useQuery({
    queryKey: ["decisions", riskId],
    queryFn: () => api.get<DecisionOut[]>(`/risks/${riskId}/decisions`),
    enabled: !!riskId,
  });
  const actions = useQuery({
    queryKey: ["actions", "risk", riskId],
    queryFn: () => api.get<ActionOut[]>(`/risks/${riskId}/actions`),
    enabled: !!riskId,
  });
  const acceptances = useQuery({
    queryKey: ["acceptances", "risk", riskId],
    queryFn: () => api.get<AcceptanceOut[]>("/acceptances", { risk_id: riskId }),
    enabled: !!riskId,
  });

  if (q.isLoading) return <Loading />;
  if (q.error || !risk) return <ErrorState error={q.error} retry={() => q.refetch()} />;

  const isOwner = risk.owner.id === me.id;
  const isAnalyst = can("assess_risk");
  const canEdit = can("edit_risk") || isOwner;
  const canTreat = isAnalyst || (isOwner && me.role !== "auditor");
  const canRequestAcceptance = isOwner && risk.status !== "closed";
  const canEvidence = can("upload_evidence") || isOwner;
  const latestDecision = decisions.data?.at(-1);
  const pending = acceptances.data?.find((a) => a.status === "pending");
  const assessments = [...risk.assessments].reverse();
  const initial = risk.assessments.find((a) => a.assessment_type === "initial");

  return (
    <>
      <PageHeader
        eyebrow={
          <>
            <Link to="/risks">Risk register</Link> / <span className="mono-data">{risk.risk_code}</span>
          </>
        }
        title={risk.title}
        description={
          <span className="flex flex-wrap items-center gap-2">
            <StatusChip status={risk.display_status} />
            {risk.strategy && <span className="chip">Strategy: {titleCase(risk.strategy)}</span>}
            <span>Owner: {risk.owner.full_name}</span>
          </span>
        }
        actions={
          <>
            {canEdit && (
              <Link to={`/risks/${risk.risk_code}/edit`} className="btn-secondary no-underline hover:no-underline">
                <PencilSquareIcon className="h-4 w-4" aria-hidden /> Edit
              </Link>
            )}
            {isAnalyst && risk.current && risk.status !== "closed" && (
              <button type="button" className="btn-primary" onClick={() => setDialog("reassess")}>
                Reassess
              </button>
            )}
          </>
        }
      />

      {risk.status === "awaiting_reassessment" && (
        <div className="mb-4">
          <Notice tone="warning" title="Awaiting reassessment">
            <p>
              {(risk.awaiting_reassessment_actions ?? []).length > 1 ? "Treatment actions were" : "A treatment action was"}{" "}
              completed with evidence. The score stays as it is until an analyst reassesses the risk with supporting
              evidence.
            </p>
            {(risk.awaiting_reassessment_actions ?? []).length > 0 && (
              <ul className="mt-2 flex flex-col gap-1">
                {(risk.awaiting_reassessment_actions ?? []).map((a) => (
                  <li key={a.id}>
                    <span className="mono-data font-semibold">{a.action_code}</span> {a.title}{" "}
                    <span className="text-xs text-muted">
                      (completed <DateTime iso={a.completed_at} />, {a.evidence_count} evidence file
                      {a.evidence_count === 1 ? "" : "s"})
                    </span>
                  </li>
                ))}
              </ul>
            )}
            {isAnalyst && (
              <button type="button" className="btn-primary btn-sm mt-3" onClick={() => setDialog("reassess")}>
                Reassess now
              </button>
            )}
          </Notice>
        </div>
      )}
      {risk.display_status === "acceptance_expired" && (
        <div className="mb-4">
          <Notice tone="danger" title="Acceptance expired">
            The approved acceptance expired on <DateOnly day={risk.acceptance_expiry} />. The risk must be treated or
            accepted again.
          </Notice>
        </div>
      )}

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-3">
        <Card title="Score" className="xl:col-span-2">
          {risk.current ? (
            <div className="flex flex-col gap-4">
              <ScoreBadge score={risk.current} />
              <Explanation text={risk.current.explanation} />
              <div className="grid grid-cols-3 gap-3 text-center">
                <ScoreBox label="Inherent" score={risk.inherent?.score ?? risk.original_score} />
                <ScoreBox label="Target" score={latestDecision?.target_score ?? null} />
                <ScoreBox label="Residual" score={risk.residual?.score} empty="not yet reassessed" />
              </div>
              <p className="text-sm text-muted" data-testid="residual-summary">
                {residualSummary(risk)}
              </p>
            </div>
          ) : (
            <EmptyState title="Not assessed yet">
              {isAnalyst ? (
                <Link to={`/risks/${risk.risk_code}/edit`}>Add the initial assessment</Link>
              ) : (
                "An analyst records the initial assessment."
              )}
            </EmptyState>
          )}
        </Card>

        <Card title="Summary">
          <KeyValue
            items={[
              ["Owner", `${risk.owner.full_name}${risk.owner.job_title ? `, ${risk.owner.job_title}` : ""}`],
              ["Category", risk.category ?? "—"],
              ["Services", <span className="mono-data">{risk.services.join(", ") || "—"}</span>],
              [
                "Next review",
                <span className={risk.review_due_soon ? "font-semibold text-danger" : ""}>
                  <DateOnly day={risk.next_review_date} />
                </span>,
              ],
              ["Open actions", `${risk.open_actions ?? 0}${risk.overdue_actions ? ` (${risk.overdue_actions} overdue)` : ""}`],
              ["Created", <DateTime iso={risk.created_at} />],
            ]}
          />
        </Card>

        <Card title="Risk statement" className="xl:col-span-2">
          <KeyValue
            items={[
              ["Threat", risk.threat],
              ["Vulnerability", risk.vulnerability],
              ["Business impact", risk.business_impact],
              ["Description", <span className="whitespace-pre-line">{risk.description}</span>],
            ]}
          />
        </Card>

        <Card title="Assets and obligations">
          <div className="label-caps mb-1">Assets</div>
          <ul className="mb-4 flex flex-col gap-1">
            {risk.assets.map((a) => (
              <li key={a.id}>
                <span className="mono-data">{a.asset_code}</span> {a.name}{" "}
                <span className="text-xs text-muted">({a.service_code})</span>
              </li>
            ))}
          </ul>
          <div className="label-caps mb-1">Obligations</div>
          {risk.obligations.length ? (
            <ul className="flex flex-col gap-1">
              {risk.obligations.map((o) => (
                <li key={o.id}>
                  <span className="mono-data">{o.reference}</span> {o.short_title}
                </li>
              ))}
            </ul>
          ) : (
            <div className="text-muted">None linked</div>
          )}
        </Card>
      </div>

      <div className="mt-6">
        <Tabs<Tab>
          active={tab}
          onChange={setTab}
          tabs={[
            { key: "history", label: `Assessment history (${risk.assessments.length})` },
            { key: "treatment", label: `Treatment (${actions.data?.length ?? 0})` },
            { key: "acceptance", label: `Acceptance (${acceptances.data?.length ?? 0})` },
            { key: "evidence", label: "Evidence" },
            ...(can("view_audit") ? [{ key: "audit" as Tab, label: "Audit trail" }] : []),
          ]}
        />
        <div className="mt-4">
          {tab === "history" && (
            <div className="flex flex-col gap-3">
              {assessments.length === 0 && <EmptyState title="No assessments yet" />}
              {assessments.map((a) => (
                <div key={a.id} className="card p-4">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="chip">{a.label}</span>
                    <span className="mono-data font-bold">
                      {a.likelihood}×{a.impact}={a.score}
                    </span>
                    {a.previous_score != null && (
                      <span className="text-sm text-muted">(was {a.previous_score})</span>
                    )}
                    <BandBadge band={a.band} />
                    {a.above_appetite && <span className="chip-strong">Above appetite</span>}
                    <span className="ml-auto text-xs text-muted">
                      {a.assessed_by.full_name} · <DateTime iso={a.assessed_at} />
                    </span>
                  </div>
                  <p className="mt-2 text-sm">{a.explanation}</p>
                  <p className="mt-1 whitespace-pre-line text-sm text-muted">{a.rationale}</p>
                  {(a.follows_actions ?? []).length > 0 && (
                    <div className="mt-2 text-sm">
                      <span className="label-caps">After </span>
                      {(a.follows_actions ?? []).map((f, i) => (
                        <span key={f.id}>
                          {i > 0 && ", "}
                          <span className="mono-data font-semibold" title={f.title}>
                            {f.action_code}
                          </span>{" "}
                          {f.title}
                        </span>
                      ))}
                    </div>
                  )}
                  {a.assessment_type !== "initial" && (
                    <div className="mt-3">
                      <div className="label-caps mb-1">Evidence</div>
                      <EvidenceList target={{ type: "assessment", id: a.id, label: "this reassessment" }} />
                    </div>
                  )}
                </div>
              ))}
              {initial && assessments.length > 1 && (
                <p className="text-xs text-muted">
                  Assessments are insert-only: a reassessment adds a new row and the inherent score ({initial.score}) is
                  kept.
                </p>
              )}
            </div>
          )}

          {tab === "treatment" && (
            <div className="flex flex-col gap-6">
              <Card
                title="Treatment decisions"
                actions={
                  canTreat && (
                    <button type="button" className="btn-secondary btn-sm" onClick={() => setDialog("decision")}>
                      <PlusIcon className="h-4 w-4" aria-hidden /> Record decision
                    </button>
                  )
                }
              >
                {(decisions.data ?? []).length === 0 ? (
                  <div className="text-muted">No treatment decision yet.</div>
                ) : (
                  <ol className="flex flex-col gap-3">
                    {[...(decisions.data ?? [])].reverse().map((d) => (
                      <li key={d.id} className="border-l-2 border-line pl-3">
                        <div className="flex flex-wrap items-center gap-2">
                          <span className="chip">{titleCase(d.strategy)}</span>
                          {d.target_score && (
                            <span className="text-sm">
                              Target <span className="mono-data">{d.target_likelihood}×{d.target_impact}={d.target_score}</span>{" "}
                              <BandBadge band={bandFor(d.target_score)} />
                            </span>
                          )}
                          <span className="ml-auto text-xs text-muted">
                            {d.decided_by.full_name} · <DateTime iso={d.decided_at} />
                          </span>
                        </div>
                        <p className="mt-1 text-sm">{d.justification}</p>
                      </li>
                    ))}
                  </ol>
                )}
              </Card>

              <Card
                title="Treatment actions"
                actions={
                  canTreat && (
                    <button type="button" className="btn-secondary btn-sm" onClick={() => setDialog("action")}>
                      <PlusIcon className="h-4 w-4" aria-hidden /> Add action
                    </button>
                  )
                }
              >
                <ActionCards actions={actions.data ?? []} risk={risk} />
              </Card>
            </div>
          )}

          {tab === "acceptance" && (
            <div className="flex flex-col gap-3">
              {canRequestAcceptance && !pending && (
                <div>
                  <button type="button" className="btn-secondary" onClick={() => setDialog("acceptance")}>
                    Request risk acceptance
                  </button>
                </div>
              )}
              {(acceptances.data ?? []).length === 0 && <EmptyState title="No acceptance requests" />}
              {[...(acceptances.data ?? [])].reverse().map((a) => (
                <AcceptanceCard key={a.id} acceptance={a} />
              ))}
            </div>
          )}

          {tab === "evidence" && (
            <Card title="Evidence on this risk">
              <EvidenceList target={{ type: "risk", id: risk.id, label: risk.risk_code }} canUpload={canEvidence} />
              <p className="mt-3 text-xs text-muted">
                Evidence for actions and reassessments is listed with each action and in the assessment history.
              </p>
            </Card>
          )}

          {tab === "audit" && <RiskAudit riskId={risk.id} />}
        </div>
      </div>

      {dialog === "decision" && <DecisionDialog open risk={risk} onClose={() => setDialog(null)} />}
      {dialog === "action" && <ActionDialog open risk={risk} onClose={() => setDialog(null)} />}
      {dialog === "reassess" && <ReassessDialog open risk={risk} onClose={() => setDialog(null)} />}
      {dialog === "acceptance" && <RequestAcceptanceDialog open risk={risk} onClose={() => setDialog(null)} />}
    </>
  );
}

function ScoreBox({ label, score, empty = "not set" }: { label: string; score: number | null | undefined; empty?: string }) {
  return (
    <div className="border border-line p-3">
      <div className="label-caps">{label}</div>
      <div className="mono-data mt-1 text-2xl font-bold">{score ?? "—"}</div>
      {score ? <BandBadge band={bandFor(score)} /> : <span className="text-xs text-muted">{empty}</span>}
    </div>
  );
}

export function ActionCards({ actions, risk }: { actions: ActionOut[]; risk?: RiskDetail }) {
  const [completing, setCompleting] = useState<ActionOut | null>(null);
  const [editing, setEditing] = useState<ActionOut | null>(null);
  const [open, setOpen] = useState<number | null>(null);
  if (actions.length === 0) return <div className="text-muted">No treatment actions yet.</div>;
  return (
    <ul className="flex flex-col gap-3">
      {actions.map((a) => {
        const done = a.status === "completed" || a.status === "cancelled";
        return (
          <li key={a.id} className={`border p-3 ${a.overdue ? "border-danger" : "border-line"}`}>
            <div className="flex flex-wrap items-center gap-2">
              <span className="mono-data font-semibold">{a.action_code}</span>
              <StatusChip status={a.overdue ? "overdue" : a.status} />
              {a.overdue && <span className="text-xs font-semibold text-danger">{a.days_overdue} days overdue</span>}
              {!risk && (
                <Link to={`/risks/${a.risk.risk_code as string}`} className="mono-data">
                  {a.risk.risk_code as string}
                </Link>
              )}
              <span className="ml-auto text-xs text-muted">{a.owner.full_name}</span>
            </div>
            <div className="mt-1 font-medium">{a.title}</div>
            <div className="mt-1 flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted">
              <span>{done ? <>Due <DateOnly day={a.due_date} /></> : deadlineHint(a.due_date)}</span>
              {a.estimated_cost_ngn && <span>Est. {formatNaira(a.estimated_cost_ngn)}</span>}
              <span>{a.evidence_count} evidence file{a.evidence_count === 1 ? "" : "s"}</span>
            </div>
            {a.controls.length > 0 && (
              <div className="mt-2 flex flex-wrap gap-1">
                {a.controls.map((c) => (
                  <span key={c.id} className="chip mono-data" title={c.short_title}>
                    {c.framework} {c.control_ref}
                  </span>
                ))}
              </div>
            )}
            {a.status === "completed" && a.completion_note && (
              <p className="mt-2 text-sm">
                Completed by {a.completed_by?.full_name} on <DateTime iso={a.completed_at} />: {a.completion_note}
              </p>
            )}
            <div className="mt-2 flex flex-wrap gap-2">
              {a.can_update && !done && (
                <>
                  <button type="button" className="btn-primary btn-sm" onClick={() => setCompleting(a)}>
                    Complete with evidence
                  </button>
                  <button type="button" className="btn-secondary btn-sm" onClick={() => setEditing(a)}>
                    Edit
                  </button>
                </>
              )}
              <button type="button" className="btn-ghost btn-sm" onClick={() => setOpen(open === a.id ? null : a.id)} aria-expanded={open === a.id}>
                {open === a.id ? "Hide evidence" : "Show evidence"}
              </button>
            </div>
            {open === a.id && (
              <div className="mt-2">
                <EvidenceList target={{ type: "action", id: a.id, label: a.action_code }} canUpload={a.can_update} />
              </div>
            )}
          </li>
        );
      })}
      {completing && <CompleteActionDialog open action={completing} onClose={() => setCompleting(null)} />}
      {editing && (
        <ActionDialog open action={editing} risk={{ id: editing.risk.id as number, risk_code: editing.risk.risk_code as string }} onClose={() => setEditing(null)} />
      )}
    </ul>
  );
}

export function AcceptanceCard({ acceptance: a, showRisk }: { acceptance: AcceptanceOut; showRisk?: boolean }) {
  const [deciding, setDeciding] = useState(false);
  const { can } = useAuth();
  const status = a.expired ? "expired" : a.status;
  return (
    <div className={`card p-4 ${a.status === "pending" ? "border-l-4 border-l-accent" : ""}`}>
      <div className="flex flex-wrap items-center gap-2">
        <StatusChip status={status} />
        {showRisk && (
          <Link to={`/risks/${a.risk.risk_code as string}`} className="mono-data font-semibold">
            {a.risk.risk_code as string}
          </Link>
        )}
        {showRisk && <span className="font-medium">{a.risk.title as string}</span>}
        {a.current && <ScoreBadge score={a.current} />}
      </div>
      <p className="mt-2 whitespace-pre-line text-sm">{a.justification}</p>
      <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted">
        <span>
          Requested by {a.requested_by.full_name} · <DateTime iso={a.requested_at} />
        </span>
        <span>
          Proposed expiry <DateOnly day={a.proposed_expiry} />
        </span>
        {a.decided_by && (
          <span>
            {titleCase(a.status)} by {a.decided_by.full_name}
            {a.decision_date && (
              <>
                {" · "}
                <DateTime iso={a.decision_date} />
              </>
            )}
          </span>
        )}
        {a.expiry_date && (
          <span className={a.expired ? "font-semibold text-danger" : ""}>
            {a.expired ? "Expired" : "Expires"} <DateOnly day={a.expiry_date} />
          </span>
        )}
      </div>
      {a.decision_comment && <p className="mt-2 border-l-2 border-line pl-3 text-sm">“{a.decision_comment}”</p>}
      {a.status === "pending" && can("decide_acceptance") && (
        <div className="mt-3">
          {a.can_decide ? (
            <button type="button" className="btn-primary btn-sm" onClick={() => setDeciding(true)}>
              Approve or reject
            </button>
          ) : (
            <div className="flex flex-wrap items-center gap-2">
              <button type="button" className="btn-primary btn-sm" disabled aria-describedby={`why-${a.id}`}>
                Approve or reject
              </button>
              <span id={`why-${a.id}`} className="text-sm font-semibold text-danger">
                {a.cannot_decide_reason}
              </span>
            </div>
          )}
        </div>
      )}
      {deciding && <DecideAcceptanceDialog open acceptance={a} onClose={() => setDeciding(false)} />}
    </div>
  );
}

function RiskAudit({ riskId }: { riskId: number }) {
  const q = useQuery({
    queryKey: ["audit", "risk", riskId],
    queryFn: () => api.get<AuditPage>("/audit", { object_type: "risk", object_id: String(riskId), page_size: 100 }),
  });
  if (q.isLoading) return <Loading />;
  if (q.error) return <ErrorState error={q.error} />;
  const items = q.data?.items ?? [];
  if (!items.length) return <EmptyState title="No audit entries for this risk" />;
  return (
    <ol className="flex flex-col divide-y divide-line border border-line">
      {items.map((e) => (
        <li key={e.id} className="flex flex-col gap-1 px-3 py-2 sm:flex-row sm:items-center sm:gap-3">
          <span className="chip mono-data w-fit">{e.action}</span>
          <span className="flex-1 text-sm">{e.detail ?? `${e.object_type} ${e.object_id ?? ""}`}</span>
          <span className="text-xs text-muted">
            {e.username ?? "system"} · <DateTime iso={e.occurred_at} />
          </span>
        </li>
      ))}
    </ol>
  );
}
