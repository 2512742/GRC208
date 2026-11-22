import { useQuery } from "@tanstack/react-query";
import { useSearchParams } from "react-router-dom";

import { api } from "../api/client";
import type { ActionOut } from "../api/types";
import { useAuth } from "../auth/AuthContext";
import { ErrorState, Loading, PageHeader, Tabs } from "../components/ui";
import { ActionCards } from "./RiskDetailPage";

type View = "mine" | "overdue" | "open" | "all";

export default function ActionsPage() {
  const { can, me } = useAuth();
  const [params, setParams] = useSearchParams();
  const ownerish = me?.role === "owner";
  const view = (params.get("overdue") === "true" ? "overdue" : params.get("view")) as View | null;
  const active: View = view ?? (ownerish ? "mine" : "open");

  const q = useQuery({
    queryKey: ["actions", active],
    queryFn: () =>
      api.get<ActionOut[]>("/actions", {
        mine: active === "mine" ? true : undefined,
        overdue: active === "overdue" ? true : undefined,
      }),
  });

  const rows = (q.data ?? [])
    .filter((a) => active !== "open" || (a.status !== "completed" && a.status !== "cancelled"))
    // Overdue first, then by due date (PLAN.md §5.1 U3).
    .sort((a, b) => Number(b.overdue) - Number(a.overdue) || a.due_date.localeCompare(b.due_date));

  return (
    <>
      <PageHeader
        eyebrow="Treatment"
        title="Treatment actions"
        description="Overdue actions first. Completing an action needs evidence and sends its risk for reassessment; the score never changes on completion alone."
      />
      <Tabs<View>
        active={active}
        onChange={(k) => setParams(k === "open" ? {} : { view: k }, { replace: true })}
        tabs={[
          ...(can("update_action") ? [{ key: "mine" as View, label: "My actions" }] : []),
          { key: "open", label: "Open" },
          { key: "overdue", label: "Overdue" },
          { key: "all", label: "All" },
        ]}
      />
      <div className="mt-4">
        {q.isLoading ? (
          <Loading />
        ) : q.error ? (
          <ErrorState error={q.error} retry={() => q.refetch()} />
        ) : (
          <ActionCards actions={rows} />
        )}
      </div>
    </>
  );
}
