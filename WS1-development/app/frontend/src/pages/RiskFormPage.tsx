import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useMemo, useState } from "react";
import type { FormEvent } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

import { api } from "../api/client";
import { useAssets, useObligations, useUsers } from "../api/queries";
import type { RiskDetail, RiskPage } from "../api/types";
import { useAuth, useMe } from "../auth/AuthContext";
import { Explanation } from "../components/risk";
import { useToast } from "../components/Toast";
import { AssessmentInputs } from "../components/treatment";
import { Card, ErrorState, Loading, Notice, PageHeader, SelectField, TextArea, TextField } from "../components/ui";

interface FormState {
  title: string;
  category: string;
  owner_id: number | "";
  threat: string;
  vulnerability: string;
  business_impact: string;
  description: string;
  next_review_date: string;
  asset_ids: number[];
  obligation_ids: number[];
}

const EMPTY: FormState = {
  title: "",
  category: "",
  owner_id: "",
  threat: "",
  vulnerability: "",
  business_impact: "",
  description: "",
  next_review_date: "",
  asset_ids: [],
  obligation_ids: [],
};

export default function RiskFormPage() {
  const { code } = useParams();
  const editing = !!code;
  const me = useMe();
  const { can } = useAuth();
  const toast = useToast();
  const navigate = useNavigate();
  const qc = useQueryClient();
  const users = useUsers();
  const assets = useAssets();
  const obligations = useObligations();

  const existing = useQuery({
    queryKey: ["risk", code],
    enabled: editing,
    queryFn: async () => {
      const page = await api.get<RiskPage>("/risks", { q: code, page_size: 100 });
      const hit = page.items.find((r) => r.risk_code.toLowerCase() === code!.toLowerCase());
      if (!hit) throw new Error(`Risk ${code} not found.`);
      return api.get<RiskDetail>(`/risks/${hit.id}`);
    },
  });

  const [form, setForm] = useState<FormState>(EMPTY);
  const [assess, setAssess] = useState(true);
  const [likelihood, setLikelihood] = useState(3);
  const [impact, setImpact] = useState(3);
  const [rationale, setRationale] = useState("");
  const [assetFilter, setAssetFilter] = useState("");

  useEffect(() => {
    const r = existing.data;
    if (!r) return;
    setForm({
      title: r.title,
      category: r.category ?? "",
      owner_id: r.owner.id,
      threat: r.threat,
      vulnerability: r.vulnerability,
      business_impact: r.business_impact,
      description: r.description,
      next_review_date: r.next_review_date ?? "",
      asset_ids: r.assets.map((a) => a.id),
      obligation_ids: r.obligations.map((o) => o.id),
    });
  }, [existing.data]);

  const risk = existing.data;
  const fullEdit = !editing || can("edit_risk");
  const ownerOnly = editing && !can("edit_risk") && risk?.owner.id === me.id;
  const canAssess = can("assess_risk") && (!editing || (risk && !risk.current));
  const set = <K extends keyof FormState>(key: K, value: FormState[K]) => setForm((f) => ({ ...f, [key]: value }));

  const save = useMutation({
    mutationFn: async () => {
      const assessment = canAssess && assess ? { likelihood, impact, rationale } : null;
      if (!editing) {
        return api.post<RiskDetail>("/risks", {
          ...form,
          category: form.category || null,
          owner_id: form.owner_id,
          next_review_date: undefined,
          initial_assessment: assessment,
        });
      }
      const body = ownerOnly
        ? { description: form.description, next_review_date: form.next_review_date || null }
        : {
            ...form,
            category: form.category || null,
            next_review_date: form.next_review_date || null,
          };
      let saved = await api.patch<RiskDetail>(`/risks/${risk!.id}`, body);
      if (assessment) saved = await api.post<RiskDetail>(`/risks/${risk!.id}/assessments`, assessment);
      return saved;
    },
    onSuccess: (saved) => {
      toast.success(editing ? `${saved.risk_code} saved.` : `${saved.risk_code} created${saved.current ? `: score ${saved.current.score}` : ""}.`);
      for (const k of ["risks", "risk", "dashboard", "assets"]) qc.invalidateQueries({ queryKey: [k] });
      navigate(`/risks/${saved.risk_code}`);
    },
  });

  const filteredAssets = useMemo(
    () =>
      (assets.data ?? []).filter((a) =>
        `${a.asset_code} ${a.name} ${a.service.code as string}`.toLowerCase().includes(assetFilter.toLowerCase()),
      ),
    [assets.data, assetFilter],
  );

  if (editing && existing.isLoading) return <Loading />;
  if (editing && existing.error) return <ErrorState error={existing.error} />;
  if (editing && risk && !can("edit_risk") && risk.owner.id !== me.id) {
    return <ErrorState error={new Error("Only the risk owner or a GRC analyst can edit this risk.")} />;
  }

  const submit = (e: FormEvent) => {
    e.preventDefault();
    save.mutate();
  };

  return (
    <>
      <PageHeader
        eyebrow={
          <>
            <Link to="/risks">Risk register</Link>
            {risk && (
              <>
                {" / "}
                <Link to={`/risks/${risk.risk_code}`} className="mono-data">
                  {risk.risk_code}
                </Link>
              </>
            )}
          </>
        }
        title={editing ? `Edit ${risk?.risk_code ?? ""}` : "New risk"}
        description={
          ownerOnly
            ? "As the risk owner you can update the description and the next review date. Other changes go through the GRC analyst."
            : "Describe the risk as threat, vulnerability and business impact. The risk ID is assigned automatically."
        }
      />
      <form onSubmit={submit} className="grid grid-cols-1 gap-6 xl:grid-cols-3" noValidate={false}>
        <div className="flex flex-col gap-6 xl:col-span-2">
          {save.error && <Notice tone="danger">{save.error.message}</Notice>}
          <Card title="Risk statement">
            <div className="flex flex-col gap-4">
              <TextField label="Title" required minLength={5} maxLength={200} disabled={!fullEdit} value={form.title} onChange={(e) => set("title", e.target.value)} />
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                <SelectField
                  label="Risk owner"
                  required
                  disabled={!fullEdit}
                  value={form.owner_id}
                  placeholder="Choose…"
                  onChange={(e) => set("owner_id", e.target.value ? Number(e.target.value) : "")}
                  options={(users.data ?? [])
                    .filter((u) => u.role === "owner" || u.role === "approver" || u.role === "analyst")
                    .map((u) => ({ value: u.id, label: `${u.full_name}${u.job_title ? `, ${u.job_title}` : ""}` }))}
                />
                <TextField label="Category" maxLength={60} disabled={!fullEdit} value={form.category} onChange={(e) => set("category", e.target.value)} placeholder="e.g. Fraud, Data protection" />
              </div>
              <TextArea label="Threat" required disabled={!fullEdit} value={form.threat} onChange={(e) => set("threat", e.target.value)} />
              <TextArea label="Vulnerability" required disabled={!fullEdit} value={form.vulnerability} onChange={(e) => set("vulnerability", e.target.value)} />
              <TextArea label="Business impact" required disabled={!fullEdit} value={form.business_impact} onChange={(e) => set("business_impact", e.target.value)} />
              <TextArea label="Description" required rows={4} value={form.description} onChange={(e) => set("description", e.target.value)} />
              {editing && (
                <TextField label="Next review date" type="date" value={form.next_review_date} onChange={(e) => set("next_review_date", e.target.value)} hint="Set automatically from the band; change it if the review should happen sooner." />
              )}
            </div>
          </Card>

          {canAssess && (
            <Card
              title="Initial assessment"
              actions={
                !editing && (
                  <label className="flex items-center gap-2 text-sm">
                    <input type="checkbox" checked={assess} onChange={(e) => setAssess(e.target.checked)} />
                    Assess now
                  </label>
                )
              }
            >
              {assess ? (
                <div className="flex flex-col gap-4">
                  <AssessmentInputs likelihood={likelihood} impact={impact} setLikelihood={setLikelihood} setImpact={setImpact} />
                  <TextArea label="Rationale" required minLength={10} value={rationale} onChange={(e) => setRationale(e.target.value)} hint="Why these scores: evidence, incidents, existing controls." />
                </div>
              ) : (
                <div className="text-muted">The risk will be saved as "not assessed".</div>
              )}
            </Card>
          )}
          {editing && risk?.current && (
            <Card title="Current assessment">
              <Explanation text={risk.current.explanation} />
              <p className="mt-2 text-xs text-muted">Assessments can't be edited. Use "Reassess" on the risk page, with evidence.</p>
            </Card>
          )}
        </div>

        <div className="flex flex-col gap-6">
          <Card title={`Assets (${form.asset_ids.length})`}>
            <input className="input mb-2" type="search" placeholder="Filter assets" aria-label="Filter assets" value={assetFilter} onChange={(e) => setAssetFilter(e.target.value)} disabled={!fullEdit} />
            <div className="max-h-72 overflow-y-auto border border-line">
              {filteredAssets.map((a) => (
                <label key={a.id} className="flex items-start gap-2 border-b border-line px-3 py-1.5 last:border-0 hover:bg-hover">
                  <input
                    type="checkbox"
                    className="mt-1"
                    disabled={!fullEdit}
                    checked={form.asset_ids.includes(a.id)}
                    onChange={(e) =>
                      set("asset_ids", e.target.checked ? [...form.asset_ids, a.id] : form.asset_ids.filter((x) => x !== a.id))
                    }
                  />
                  <span>
                    <span className="mono-data">{a.asset_code}</span> {a.name}
                    <span className="block text-xs text-muted">{a.service.code as string} {a.service.name as string}</span>
                  </span>
                </label>
              ))}
            </div>
            <div className="mt-1 text-xs text-muted">At least one asset.</div>
          </Card>
          <Card title={`Obligations (${form.obligation_ids.length})`}>
            <div className="max-h-72 overflow-y-auto border border-line">
              {(obligations.data ?? []).map((o) => (
                <label key={o.id} className="flex items-start gap-2 border-b border-line px-3 py-1.5 last:border-0 hover:bg-hover">
                  <input
                    type="checkbox"
                    className="mt-1"
                    disabled={!fullEdit}
                    checked={form.obligation_ids.includes(o.id)}
                    onChange={(e) =>
                      set(
                        "obligation_ids",
                        e.target.checked ? [...form.obligation_ids, o.id] : form.obligation_ids.filter((x) => x !== o.id),
                      )
                    }
                  />
                  <span>
                    <span className="mono-data">{o.reference}</span> {o.short_title}
                  </span>
                </label>
              ))}
            </div>
          </Card>
          <div className="flex gap-2">
            <button type="submit" className="btn-primary flex-1" disabled={save.isPending}>
              {save.isPending ? "Saving…" : editing ? "Save changes" : "Create risk"}
            </button>
            <button type="button" className="btn-secondary" onClick={() => navigate(-1)}>
              Cancel
            </button>
          </div>
        </div>
      </form>
    </>
  );
}
