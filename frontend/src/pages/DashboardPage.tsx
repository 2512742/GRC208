import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { api } from "../api/client";
import { useServices } from "../api/queries";
import type { ExposureLine, HeatCell, Overview, ServiceLine, Totals } from "../api/types";
import { useMe } from "../auth/AuthContext";
import { HeatMap, ScoreBadge, StatusChip } from "../components/risk";
import { Card, DateOnly, EmptyState, ErrorState, Loading, PageHeader, StatTile, Tabs } from "../components/ui";
import { BANDS, compactNaira, titleCase } from "../lib/format";
import { deadlineHint } from "../lib/time";

export default function DashboardPage() {
  const me = useMe();
  const navigate = useNavigate();
  const services = useServices();
  const [serviceId, setServiceId] = useState("");
  const [view, setView] = useState<"current" | "original">("current");
  const [cell, setCell] = useState<HeatCell | null>(null);

  const query = useQuery({
    queryKey: ["dashboard", serviceId],
    queryFn: () => api.get<Overview>("/dashboard", { service_id: serviceId || undefined }),
  });

  if (query.isLoading) return <Loading />;
  if (query.error || !query.data) return <ErrorState error={query.error} retry={() => query.refetch()} />;
  const data = query.data;
  const totals = data.totals as unknown as Totals;
  const byService = data.by_service as unknown as ServiceLine[];
  const exposure = data.regulatory_exposure as unknown as ExposureLine[];
  const cells = view === "current" ? data.heat_map_current : data.heat_map_original;

  return (
    <>
      <PageHeader
        eyebrow="Executive overview"
        title="Cyber risk dashboard"
        description={`Good to see you, ${me.full_name.split(" ")[0]}. Appetite threshold: score ${data.appetite_threshold} or more must be treated or formally accepted.`}
        actions={
          <select
            aria-label="Filter by business service"
            className="input w-auto"
            value={serviceId}
            onChange={(e) => {
              setServiceId(e.target.value);
              setCell(null);
            }}
          >
            <option value="">All services</option>
            {(services.data ?? []).map((s) => (
              <option key={s.id} value={s.id}>
                {s.code} {s.name}
              </option>
            ))}
          </select>
        }
      />

      <div className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-6">
        <StatTile label="Risks" value={totals.risks} hint={`${totals.assessed} assessed`} onClick={() => navigate("/risks")} />
        <StatTile
          label="Above appetite"
          value={totals.above_appetite}
          tone={totals.above_appetite ? "alert" : "normal"}
          hint={`Score ≥ ${data.appetite_threshold}`}
          onClick={() => navigate("/risks?above_appetite=true")}
        />
        <StatTile
          label="Pending approvals"
          value={totals.pending_acceptances}
          onClick={() => navigate("/approvals")}
        />
        <StatTile
          label="Overdue actions"
          value={totals.overdue_actions}
          tone={totals.overdue_actions ? "alert" : "normal"}
          hint={`${totals.open_actions} open`}
          onClick={() => navigate("/actions?overdue=true")}
        />
        <StatTile
          label="Expired acceptances"
          value={totals.expired_acceptances}
          tone={totals.expired_acceptances ? "alert" : "normal"}
          onClick={() => navigate("/approvals?expired=true")}
        />
        <StatTile label="Open treatment cost" value={compactNaira(data.open_treatment_cost_ngn)} hint="Estimated, open actions" />
      </div>

      <div className="mt-6 grid grid-cols-1 gap-6 xl:grid-cols-5">
        <Card
          className="xl:col-span-3"
          title="Heat map"
          actions={
            <Tabs
              tabs={[
                { key: "current", label: "Current" },
                { key: "original", label: "Original" },
              ]}
              active={view}
              onChange={(k) => {
                setView(k);
                setCell(null);
              }}
            />
          }
        >
          <HeatMap cells={cells} threshold={data.appetite_threshold} onSelect={setCell} selected={cell} />
          {cell && (
            <div className="mt-4 border-t border-line pt-3" aria-live="polite">
              <div className="label-caps mb-2">
                L{cell.likelihood} × I{cell.impact} = {cell.score} · {cell.count} risk{cell.count === 1 ? "" : "s"} ({view})
              </div>
              <div className="flex flex-wrap gap-2">
                {cell.risk_codes.map((code) => (
                  <Link key={code} to={`/risks/${code}`} className="chip mono-data">
                    {code}
                  </Link>
                ))}
              </div>
            </div>
          )}
        </Card>

        <Card className="xl:col-span-2" title="Risks by band">
          <ul className="flex flex-col gap-2">
            {BANDS.slice()
              .reverse()
              .map((band) => {
                const count = (data.by_band as Record<string, number>)[band] ?? 0;
                const pct = totals.assessed ? (count / totals.assessed) * 100 : 0;
                return (
                  <li key={band}>
                    <Link to={`/risks?band=${band}`} className="block text-ink no-underline hover:no-underline">
                      <div className="flex justify-between text-sm">
                        <span>{titleCase(band)}</span>
                        <span className="mono-data">{count}</span>
                      </div>
                      <div className="mt-1 h-2 bg-container">
                        <div className={`h-2 bg-band-${band}`} style={{ width: `${pct}%` }} />
                      </div>
                    </Link>
                  </li>
                );
              })}
          </ul>
          <div className="label-caps mb-2 mt-6">By service</div>
          <table className="table-base">
            <thead>
              <tr>
                <th>Service</th>
                <th className="text-right">Risks</th>
                <th className="text-right">Above</th>
                <th className="text-right">Highest</th>
              </tr>
            </thead>
            <tbody>
              {byService.map((s) => (
                <tr key={s.code}>
                  <td>
                    <span className="mono-data">{s.code}</span> {s.name}
                  </td>
                  <td className="mono-data text-right">{s.risks}</td>
                  <td className="mono-data text-right">{s.above_appetite}</td>
                  <td className="mono-data text-right">{s.highest_score ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      </div>

      <div className="mt-6 grid grid-cols-1 gap-6 lg:grid-cols-2">
        <Card title={`Above appetite (${data.above_appetite.length})`} bodyClassName="p-0">
          {data.above_appetite.length === 0 ? (
            <div className="p-4">
              <EmptyState title="No risks above appetite" />
            </div>
          ) : (
            <ul className="divide-y divide-line">
              {data.above_appetite.map((r) => (
                <li key={r.id} className="flex flex-col gap-1 px-4 py-2 sm:flex-row sm:items-center sm:justify-between">
                  <Link to={`/risks/${r.risk_code}`} className="min-w-0">
                    <span className="mono-data mr-2">{r.risk_code}</span>
                    {r.title}
                  </Link>
                  <ScoreBadge score={r.current} />
                </li>
              ))}
            </ul>
          )}
        </Card>

        <div className="flex flex-col gap-6">
          <Card title={`Overdue actions (${data.overdue_actions.length})`} bodyClassName="p-0">
            {data.overdue_actions.length === 0 ? (
              <div className="p-4">
                <EmptyState title="Nothing overdue" />
              </div>
            ) : (
              <ul className="divide-y divide-line">
                {data.overdue_actions.map((a) => (
                  <li key={a.action_id} className="px-4 py-2">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="chip-strong">{a.days_overdue} days overdue</span>
                      <span className="mono-data">{a.action_code}</span>
                      <Link to={`/risks/${a.risk_code}`} className="mono-data">
                        {a.risk_code}
                      </Link>
                    </div>
                    <div className="mt-1">{a.title}</div>
                    <div className="text-xs text-muted">
                      {a.owner} · {deadlineHint(a.due_date)}
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </Card>

          <Card title="Risk acceptances" bodyClassName="p-0">
            {data.acceptances.length === 0 ? (
              <div className="p-4">
                <EmptyState title="No acceptances" />
              </div>
            ) : (
              <ul className="divide-y divide-line">
                {data.acceptances.map((a) => (
                  <li key={a.acceptance_id} className="flex flex-wrap items-center gap-2 px-4 py-2">
                    <StatusChip status={a.expired ? "expired" : a.status} />
                    <Link to={`/risks/${a.risk_code}`} className="mono-data">
                      {a.risk_code}
                    </Link>
                    <span className="min-w-0 flex-1 truncate">{a.risk_title}</span>
                    {a.expiry_date && (
                      <span className="text-xs text-muted">
                        {a.expired ? "Expired" : "Expires"} <DateOnly day={a.expiry_date} />
                      </span>
                    )}
                  </li>
                ))}
              </ul>
            )}
          </Card>
        </div>

        <Card title={`Reviews due soon (${data.upcoming_reviews.length})`} bodyClassName="p-0">
          {data.upcoming_reviews.length === 0 ? (
            <div className="p-4">
              <EmptyState title="No reviews due in the warning window" />
            </div>
          ) : (
            <ul className="divide-y divide-line">
              {data.upcoming_reviews.map((r) => (
                <li key={r.id} className="flex flex-wrap items-center justify-between gap-2 px-4 py-2">
                  <Link to={`/risks/${r.risk_code}`}>
                    <span className="mono-data mr-2">{r.risk_code}</span>
                    {r.title}
                  </Link>
                  <span className="text-xs text-muted">
                    Review due <DateOnly day={r.next_review_date} />
                  </span>
                </li>
              ))}
            </ul>
          )}
        </Card>

        <Card title="Regulatory exposure">
          <table className="table-base">
            <thead>
              <tr>
                <th>Regime</th>
                <th className="text-right">Linked risks</th>
                <th className="text-right">Above appetite</th>
              </tr>
            </thead>
            <tbody>
              {exposure.map((e) => (
                <tr key={e.regime}>
                  <td className="mono-data">{e.regime}</td>
                  <td className="mono-data text-right">{e.risks}</td>
                  <td className="mono-data text-right">{e.above_appetite}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <p className="mt-2 text-xs text-muted">
            Awaiting reassessment: {totals.awaiting_reassessment} risk
            {totals.awaiting_reassessment === 1 ? "" : "s"}.
          </p>
        </Card>
      </div>
    </>
  );
}
