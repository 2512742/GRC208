import { FunnelIcon, PlusIcon } from "@heroicons/react/24/outline";
import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";

import { api } from "../api/client";
import { useObligations, useServices, useUsers } from "../api/queries";
import type { RiskPage, RiskSummary } from "../api/types";
import { useAuth } from "../auth/AuthContext";
import { ScoreBadge, StatusChip, InherentResidual } from "../components/risk";
import { RubricToggle } from "../components/methodology";
import { DataTable, DateOnly, ErrorState, Loading, PageHeader, Pagination } from "../components/ui";
import type { Column } from "../components/ui";
import { BANDS, titleCase } from "../lib/format";

const STATUSES = ["open", "treatment_in_progress", "awaiting_reassessment", "accepted", "closed"];
const FILTER_KEYS = ["q", "service_id", "owner_id", "band", "status", "obligation_id", "above_appetite"] as const;

export default function RisksPage() {
  const { can } = useAuth();
  const navigate = useNavigate();
  const [params, setParams] = useSearchParams();
  const page = Number(params.get("page") ?? 1);
  const [search, setSearch] = useState(params.get("q") ?? "");
  const [showFilters, setShowFilters] = useState(false);

  const services = useServices();
  const users = useUsers();
  const obligations = useObligations();

  const filters = Object.fromEntries(FILTER_KEYS.map((k) => [k, params.get(k) ?? undefined]));
  const query = useQuery({
    queryKey: ["risks", params.toString()],
    queryFn: () =>
      api.get<RiskPage>("/risks", { ...filters, page, page_size: 25, sort: params.get("sort") ?? undefined }),
    placeholderData: keepPreviousData,
  });

  // Debounced search box -> URL.
  useEffect(() => {
    const t = setTimeout(() => {
      if ((params.get("q") ?? "") !== search) update({ q: search || null });
    }, 300);
    return () => clearTimeout(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [search]);

  function update(changes: Record<string, string | null>) {
    const next = new URLSearchParams(params);
    for (const [k, v] of Object.entries(changes)) {
      if (v) next.set(k, v);
      else next.delete(k);
    }
    if (!("page" in changes)) next.delete("page");
    setParams(next, { replace: true });
  }

  const active = FILTER_KEYS.some((k) => params.get(k));
  const activeCount = FILTER_KEYS.filter((k) => k !== "q" && params.get(k)).length;

  const columns: Column<RiskSummary>[] = [
    {
      key: "code",
      header: "ID",
      hideOnMobile: true,
      render: (r) => (
        <Link to={`/risks/${r.risk_code}`} className="mono-data" onClick={(e) => e.stopPropagation()}>
          {r.risk_code}
        </Link>
      ),
    },
    { key: "title", header: "Risk", render: (r) => <span className="font-medium">{r.title}</span>, className: "w-[30%]" },
    { key: "score", header: "Current score", render: (r) => <ScoreBadge score={r.current} />, hideOnMobile: true },
    {
      key: "inherent",
      header: "Inherent → Residual",
      render: (r) => <InherentResidual risk={r} />,
    },
    { key: "owner", header: "Owner", render: (r) => r.owner.full_name },
    {
      key: "status",
      header: "Status",
      render: (r) => (
        <div className="flex flex-col items-start gap-1">
          <StatusChip status={r.display_status} />
          {r.strategy && <span className="text-xs text-muted">{titleCase(r.strategy)}</span>}
          {!!r.overdue_actions && <span className="chip-strong">{r.overdue_actions} overdue</span>}
        </div>
      ),
    },
    { key: "services", header: "Service", render: (r) => <span className="mono-data">{r.services.join(", ")}</span>, hideOnMobile: true },
    {
      key: "review",
      header: "Next review",
      render: (r) => (
        <span className={r.review_due_soon ? "font-semibold text-danger" : ""}>
          <DateOnly day={r.next_review_date} />
        </span>
      ),
    },
  ];

  return (
    <>
      <PageHeader
        eyebrow="Register"
        title="Cyber risk register"
        description="Every risk with its current score, owner and treatment state. Scores at or above the appetite threshold are flagged."
        actions={
          can("create_risk") && (
            <Link to="/risks/new" className="btn-primary no-underline hover:no-underline">
              <PlusIcon className="h-4 w-4" aria-hidden /> New risk
            </Link>
          )
        }
      />

      <div className="mb-3">
        <RubricToggle />
      </div>

      <div className="card mb-4 grid grid-cols-1 gap-3 p-3 sm:grid-cols-2 lg:grid-cols-4 xl:grid-cols-7">
        <div className="flex gap-2 sm:col-span-2 lg:col-span-1 xl:col-span-2">
          <input
            className="input"
            type="search"
            placeholder="Search title, ID, threat…"
            aria-label="Search risks"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
          <button
            type="button"
            className="btn-secondary shrink-0 md:hidden"
            aria-expanded={showFilters}
            aria-controls="risk-filters"
            onClick={() => setShowFilters((v) => !v)}
          >
            <FunnelIcon className="h-4 w-4" aria-hidden />
            Filters{activeCount ? ` (${activeCount})` : ""}
          </button>
        </div>
        {/* On phones the filters fold away; from md up they join the grid (display: contents). */}
        <div id="risk-filters" className={`${showFilters ? "grid" : "hidden"} grid-cols-1 gap-3 sm:grid-cols-2 md:contents`}>
        <select aria-label="Service" className="input" value={params.get("service_id") ?? ""} onChange={(e) => update({ service_id: e.target.value })}>
          <option value="">All services</option>
          {(services.data ?? []).map((s) => (
            <option key={s.id} value={s.id}>
              {s.code} {s.name}
            </option>
          ))}
        </select>
        <select aria-label="Owner" className="input" value={params.get("owner_id") ?? ""} onChange={(e) => update({ owner_id: e.target.value })}>
          <option value="">All owners</option>
          {(users.data ?? []).map((u) => (
            <option key={u.id} value={u.id}>
              {u.full_name}
            </option>
          ))}
        </select>
        <select aria-label="Band" className="input" value={params.get("band") ?? ""} onChange={(e) => update({ band: e.target.value })}>
          <option value="">All bands</option>
          {BANDS.map((b) => (
            <option key={b} value={b}>
              {titleCase(b)}
            </option>
          ))}
        </select>
        <select aria-label="Status" className="input" value={params.get("status") ?? ""} onChange={(e) => update({ status: e.target.value })}>
          <option value="">All statuses</option>
          {STATUSES.map((s) => (
            <option key={s} value={s}>
              {titleCase(s)}
            </option>
          ))}
        </select>
        <select
          aria-label="Obligation"
          className="input"
          value={params.get("obligation_id") ?? ""}
          onChange={(e) => update({ obligation_id: e.target.value })}
        >
          <option value="">All obligations</option>
          {(obligations.data ?? []).map((o) => (
            <option key={o.id} value={o.id}>
              {o.reference} {o.short_title}
            </option>
          ))}
        </select>
        </div>
        <div className="flex flex-wrap items-center justify-between gap-3 sm:col-span-2 lg:col-span-4 xl:col-span-7">
          <label className="flex items-center gap-2">
            <input
              type="checkbox"
              checked={params.get("above_appetite") === "true"}
              onChange={(e) => update({ above_appetite: e.target.checked ? "true" : null })}
            />
            Above appetite only
          </label>
          <div className="flex items-center gap-2">
            <select aria-label="Sort" className="input w-auto py-1 text-xs" value={params.get("sort") ?? ""} onChange={(e) => update({ sort: e.target.value })}>
              <option value="">Sort: highest score</option>
              <option value="code">Sort: ID</option>
              <option value="review">Sort: next review</option>
            </select>
            {active && (
              <button
                type="button"
                className="btn-ghost btn-sm"
                onClick={() => {
                  setSearch("");
                  setParams(new URLSearchParams(), { replace: true });
                }}
              >
                Clear filters
              </button>
            )}
          </div>
        </div>
      </div>

      {query.isLoading ? (
        <Loading />
      ) : query.error ? (
        <ErrorState error={query.error} retry={() => query.refetch()} />
      ) : (
        <>
          <DataTable
            caption="Risk register"
            rows={query.data!.items}
            columns={columns}
            rowKey={(r) => r.id}
            onRowClick={(r) => navigate(`/risks/${r.risk_code}`)}
            mobileHeader={(r) => (
              <div className="flex flex-col items-start gap-1.5">
                <Link to={`/risks/${r.risk_code}`} className="mono-data font-semibold" onClick={(e) => e.stopPropagation()}>
                  {r.risk_code}
                </Link>
                <ScoreBadge score={r.current} />
              </div>
            )}
            empty="No risks match these filters."
          />
          <Pagination
            page={query.data!.page}
            pageSize={query.data!.page_size}
            total={query.data!.total}
            onPage={(p) => update({ page: String(p) })}
          />
        </>
      )}
    </>
  );
}
