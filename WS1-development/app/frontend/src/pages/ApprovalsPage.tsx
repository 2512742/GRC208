import { ShieldCheckIcon } from "@heroicons/react/24/outline";
import { useQuery } from "@tanstack/react-query";
import { useSearchParams } from "react-router-dom";

import { api } from "../api/client";
import type { AcceptanceOut } from "../api/types";
import { useAuth } from "../auth/AuthContext";
import { EmptyState, ErrorState, Loading, PageHeader, Tabs } from "../components/ui";
import { AcceptanceCard } from "./RiskDetailPage";

type View = "pending" | "approved" | "expired" | "rejected" | "all";

export default function ApprovalsPage() {
  const { can } = useAuth();
  const [params, setParams] = useSearchParams();
  const active: View = params.get("expired") === "true" ? "expired" : ((params.get("view") as View) ?? "pending");

  const q = useQuery({
    queryKey: ["acceptances", active],
    queryFn: () =>
      api.get<AcceptanceOut[]>("/acceptances", {
        status: active === "pending" || active === "approved" || active === "rejected" ? active : undefined,
        expired: active === "expired" ? true : active === "approved" ? false : undefined,
      }),
  });

  return (
    <>
      <PageHeader
        eyebrow="Governance"
        title="Risk acceptances"
        description="Formal acceptance of risks above appetite, with expiry dates."
      />
      <div className="mb-4 flex items-start gap-3 border border-line bg-surface p-3">
        <ShieldCheckIcon className="h-6 w-6 shrink-0 text-accent" aria-hidden />
        <div>
          <div className="font-semibold">Segregation of duties</div>
          <p className="text-muted">
            Only an approver (CISO or CRO) can decide, and never on a risk they own or a request they made. When the
            CISO owns the risk, the CRO decides. These rules are enforced by the server; refused attempts are written
            to the audit log.
          </p>
          {!can("decide_acceptance") && <p className="mt-1 text-xs text-muted">Your role can view acceptances but not decide them.</p>}
        </div>
      </div>
      <Tabs<View>
        active={active}
        onChange={(k) => setParams(k === "pending" ? {} : { view: k }, { replace: true })}
        tabs={[
          { key: "pending", label: "Pending" },
          { key: "approved", label: "Approved, valid" },
          { key: "expired", label: "Expired" },
          { key: "rejected", label: "Rejected" },
          { key: "all", label: "All" },
        ]}
      />
      <div className="mt-4 flex flex-col gap-3">
        {q.isLoading ? (
          <Loading />
        ) : q.error ? (
          <ErrorState error={q.error} retry={() => q.refetch()} />
        ) : (q.data ?? []).length === 0 ? (
          <EmptyState title="Nothing here" />
        ) : (
          q.data!.map((a) => <AcceptanceCard key={a.id} acceptance={a} showRisk />)
        )}
      </div>
    </>
  );
}
