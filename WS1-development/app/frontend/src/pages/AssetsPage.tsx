import { PlusIcon } from "@heroicons/react/24/outline";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { api } from "../api/client";
import { useAssets, useObligations, useServices, useUsers } from "../api/queries";
import type { AssetOut, AssetType, Classification } from "../api/types";
import { useAuth } from "../auth/AuthContext";
import { Modal } from "../components/Modal";
import { BandBadge } from "../components/risk";
import { useToast } from "../components/Toast";
import { Card, DataTable, ErrorState, Loading, Notice, PageHeader, SelectField, TextArea, TextField } from "../components/ui";
import type { Column } from "../components/ui";
import { bandFor, titleCase } from "../lib/format";

const TYPES: AssetType[] = ["application", "api", "database", "saas", "endpoint", "network", "data_store", "third_party_service"];
const CLASSES: Classification[] = ["public", "internal", "confidential", "restricted"];

export default function AssetsPage() {
  const { can } = useAuth();
  const assets = useAssets();
  const services = useServices();
  const [filter, setFilter] = useState("");
  const [editing, setEditing] = useState<AssetOut | "new" | null>(null);

  if (assets.isLoading || services.isLoading) return <Loading />;
  if (assets.error) return <ErrorState error={assets.error} retry={() => assets.refetch()} />;

  const visible = (assets.data ?? []).filter((a) =>
    `${a.asset_code} ${a.name} ${a.asset_type} ${a.owner?.full_name ?? ""}`.toLowerCase().includes(filter.toLowerCase()),
  );

  const columns: Column<AssetOut>[] = [
    { key: "code", header: "ID", render: (a) => <span className="mono-data">{a.asset_code}</span> },
    {
      key: "name",
      header: "Asset",
      render: (a) => (
        <div>
          <div className="font-medium">{a.name}</div>
          {a.status === "retired" && <span className="chip">Retired</span>}
        </div>
      ),
    },
    { key: "type", header: "Type", render: (a) => titleCase(a.asset_type) },
    { key: "class", header: "Classification", render: (a) => titleCase(a.classification) },
    { key: "owner", header: "Owner", render: (a) => a.owner?.full_name ?? "—" },
    {
      key: "obligations",
      header: "Obligations",
      render: (a) =>
        a.obligations.length ? (
          <div className="flex flex-wrap gap-1">
            {a.obligations.map((o) => (
              <span key={o.id} className="chip mono-data" title={o.short_title}>
                {o.reference}
              </span>
            ))}
          </div>
        ) : (
          "—"
        ),
    },
    {
      key: "risk",
      header: "Highest risk",
      render: (a) =>
        a.highest_score ? (
          <span className="inline-flex items-center gap-2" title="Highest current score among linked risks">
            <span className="mono-data font-bold">{a.highest_score}</span>
            <BandBadge band={bandFor(a.highest_score)} />
            <span className="text-xs text-muted">({a.risk_count} risk{a.risk_count === 1 ? "" : "s"})</span>
          </span>
        ) : (
          <span className="text-muted">No risks</span>
        ),
    },
    ...(can("manage_register")
      ? [
          {
            key: "edit",
            header: <span className="sr-only">Edit</span>,
            render: (a: AssetOut) => (
              <button type="button" className="btn-ghost btn-sm" onClick={() => setEditing(a)}>
                Edit
              </button>
            ),
          },
        ]
      : []),
  ];

  return (
    <>
      <PageHeader
        eyebrow="Register"
        title="Assets and compliance"
        description="The Alajo's information assets by business service, with the obligations they carry and the highest linked risk score."
        actions={
          can("manage_register") && (
            <button type="button" className="btn-primary" onClick={() => setEditing("new")}>
              <PlusIcon className="h-4 w-4" aria-hidden /> New asset
            </button>
          )
        }
      />
      <input className="input mb-4 max-w-md" type="search" placeholder="Filter assets" aria-label="Filter assets" value={filter} onChange={(e) => setFilter(e.target.value)} />
      <div className="flex flex-col gap-6">
        {(services.data ?? []).map((s) => {
          const rows = visible.filter((a) => (a.service.id as number) === s.id);
          if (!rows.length && filter) return null;
          return (
            <Card
              key={s.id}
              title={
                <>
                  <span className="mono-data">{s.code}</span> {s.name}
                </>
              }
              actions={<span className="text-xs text-muted">Owner: {s.owner?.full_name ?? "—"} · Criticality {s.criticality}/5</span>}
              bodyClassName="p-0 md:p-0"
            >
              <div className="p-2 md:p-0">
                <DataTable caption={`${s.name} assets`} rows={rows} columns={columns} rowKey={(a) => a.id} empty="No assets in this service." />
              </div>
            </Card>
          );
        })}
      </div>
      {editing && <AssetDialog asset={editing === "new" ? undefined : editing} onClose={() => setEditing(null)} />}
    </>
  );
}

function AssetDialog({ asset, onClose }: { asset?: AssetOut; onClose: () => void }) {
  const toast = useToast();
  const qc = useQueryClient();
  const services = useServices();
  const users = useUsers();
  const obligations = useObligations();
  const [name, setName] = useState(asset?.name ?? "");
  const [serviceId, setServiceId] = useState<number | "">((asset?.service.id as number) ?? "");
  const [type, setType] = useState<AssetType>(asset?.asset_type ?? "application");
  const [classification, setClassification] = useState<Classification>(asset?.classification ?? "internal");
  const [ownerId, setOwnerId] = useState<number | "">(asset?.owner?.id ?? "");
  const [description, setDescription] = useState(asset?.description ?? "");
  const [status, setStatus] = useState(asset?.status ?? "active");
  const [obligationIds, setObligationIds] = useState<number[]>(asset?.obligations.map((o) => o.id) ?? []);

  const m = useMutation({
    mutationFn: () => {
      const common = {
        name,
        asset_type: type,
        classification,
        owner_id: ownerId === "" ? null : ownerId,
        description: description || null,
        obligation_ids: obligationIds,
      };
      return asset
        ? api.patch<AssetOut>(`/assets/${asset.id}`, { ...common, status })
        : api.post<AssetOut>("/assets", { ...common, service_id: serviceId });
    },
    onSuccess: (a) => {
      toast.success(`${a.asset_code} ${asset ? "updated" : "created"}.`);
      qc.invalidateQueries({ queryKey: ["assets"] });
      qc.invalidateQueries({ queryKey: ["services"] });
      onClose();
    },
  });

  return (
    <Modal
      open
      wide
      onClose={onClose}
      title={asset ? `Edit ${asset.asset_code}` : "New asset"}
      footer={
        <>
          <button type="button" className="btn-secondary" onClick={onClose}>
            Cancel
          </button>
          <button type="submit" form="asset-form" className="btn-primary" disabled={m.isPending}>
            {m.isPending ? "Saving…" : "Save"}
          </button>
        </>
      }
    >
      <form
        id="asset-form"
        className="flex flex-col gap-4"
        onSubmit={(e) => {
          e.preventDefault();
          m.mutate();
        }}
      >
        {m.error && <Notice tone="danger">{m.error.message}</Notice>}
        <TextField label="Name" required value={name} onChange={(e) => setName(e.target.value)} />
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <SelectField
            label="Business service"
            required
            disabled={!!asset}
            value={serviceId}
            placeholder="Choose…"
            onChange={(e) => setServiceId(e.target.value ? Number(e.target.value) : "")}
            options={(services.data ?? []).map((s) => ({ value: s.id, label: `${s.code} ${s.name}` }))}
          />
          <SelectField label="Owner" value={ownerId} placeholder="None" onChange={(e) => setOwnerId(e.target.value ? Number(e.target.value) : "")} options={(users.data ?? []).map((u) => ({ value: u.id, label: u.full_name }))} />
          <SelectField label="Type" value={type} onChange={(e) => setType(e.target.value as AssetType)} options={TYPES.map((t) => ({ value: t, label: titleCase(t) }))} />
          <SelectField label="Classification" value={classification} onChange={(e) => setClassification(e.target.value as Classification)} options={CLASSES.map((c) => ({ value: c, label: titleCase(c) }))} />
          {asset && (
            <SelectField label="Status" value={status} onChange={(e) => setStatus(e.target.value as "active" | "retired")} options={[{ value: "active", label: "Active" }, { value: "retired", label: "Retired" }]} />
          )}
        </div>
        <TextArea label="Description" value={description} onChange={(e) => setDescription(e.target.value)} />
        <fieldset>
          <legend className="label-caps mb-1">Obligations</legend>
          <div className="max-h-48 overflow-y-auto border border-line">
            {(obligations.data ?? []).map((o) => (
              <label key={o.id} className="flex items-start gap-2 border-b border-line px-3 py-1.5 last:border-0">
                <input
                  type="checkbox"
                  className="mt-1"
                  checked={obligationIds.includes(o.id)}
                  onChange={(e) => setObligationIds((ids) => (e.target.checked ? [...ids, o.id] : ids.filter((x) => x !== o.id)))}
                />
                <span>
                  <span className="mono-data">{o.reference}</span> {o.short_title}
                </span>
              </label>
            ))}
          </div>
        </fieldset>
      </form>
    </Modal>
  );
}
