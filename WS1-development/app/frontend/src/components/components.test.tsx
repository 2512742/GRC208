import { fireEvent, screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import type { AcceptanceOut } from "../api/types";
import { navFor } from "../layout/nav";
import { AcceptanceCard } from "../pages/RiskDetailPage";
import { person, renderAs } from "../test/render";
import { bandFor } from "../lib/format";
import { BandBadge, HeatMap, InherentResidual, ScoreBadge, residualSummary } from "./risk";
import { DateTime } from "./ui";

const ROLE_PERMS: Record<string, string[]> = {
  admin: ["view_all", "export_reports", "manage_users", "manage_settings", "manage_register", "import_csv", "view_audit"],
  analyst: ["view_all", "export_reports", "manage_register", "import_csv", "create_risk", "edit_risk", "assess_risk"],
  owner: ["view_all", "export_reports", "update_action", "request_acceptance"],
  approver: ["view_all", "export_reports", "decide_acceptance", "view_audit"],
  auditor: ["view_all", "export_reports", "view_audit"],
};

describe("role-based navigation (U1)", () => {
  const labels = (role: string) => navFor((p) => ROLE_PERMS[role].includes(p)).map((n) => n.label);
  it("shows each role only its menu", () => {
    expect(labels("auditor")).toContain("Audit log");
    expect(labels("auditor")).not.toContain("Users");
    expect(labels("owner")).not.toContain("Audit log");
    expect(labels("owner")).not.toContain("CSV import");
    expect(labels("analyst")).toContain("CSV import");
    expect(labels("admin")).toEqual(expect.arrayContaining(["Users", "Settings", "Audit log"]));
  });
});

describe("risk display", () => {
  it("always prints the band name, never colour alone", () => {
    renderAs(<BandBadge band="critical" />, null);
    expect(screen.getByText("Critical")).toBeInTheDocument();
  });

  it("shows score, band and the appetite flag", () => {
    renderAs(
      <ScoreBadge score={{ likelihood: 4, impact: 5, score: 20, band: "critical", above_appetite: true, explanation: "x" }} />,
      null,
    );
    expect(screen.getByText("4×5=20")).toBeInTheDocument();
    expect(screen.getByText("Above appetite")).toBeInTheDocument();
  });

  it("heat map lists counts and reports clicks", () => {
    const onSelect = vi.fn();
    renderAs(
      <HeatMap threshold={10} onSelect={onSelect} cells={[{ likelihood: 1, impact: 4, score: 4, count: 1, risk_codes: ["R-013"] }]} />,
      null,
    );
    const cell = screen.getByRole("button", { name: /Likelihood 1, impact 4, score 4 \(low\): 1 risk: R-013/ });
    fireEvent.click(cell);
    expect(onSelect).toHaveBeenCalledWith(expect.objectContaining({ risk_codes: ["R-013"] }));
    expect(screen.getByRole("button", { name: /Likelihood 5, impact 5/ })).toBeDisabled();
  });

  it("formats timestamps in the signed-in user's zone with UTC in the tooltip", () => {
    renderAs(<DateTime iso="2026-12-05T13:30:00Z" />, person("auditor", ROLE_PERMS.auditor));
    // Date and time are separate unbreakable pieces, so the text may wrap after the comma on phones.
    const el = screen.getByTitle("2026-12-05T13:30:00Z (UTC)");
    expect(el.tagName).toBe("TIME");
    expect(el).toHaveTextContent("5 Dec 2026, 14:30 WAT");
  });
});

describe("acceptance SoD (U3)", () => {
  const pending: AcceptanceOut = {
    id: 3,
    status: "pending",
    justification: "Compensating controls in place while the vendor fix ships next quarter.",
    proposed_expiry: "2027-02-01",
    requested_at: "2026-11-10T09:00:00Z",
    requested_by: { id: 6, full_name: "Adeola Bamigboye", role: "approver" },
    decided_by: null,
    decision_comment: null,
    decision_date: null,
    expiry_date: null,
    expired: false,
    current: null,
    risk: { id: 15, risk_code: "R-015", title: "Privileged insider manipulation" },
    can_decide: false,
    cannot_decide_reason: "You own this risk, so another approver must decide.",
  };

  it("disables the decision with the reason for the risk's own approver", () => {
    renderAs(<AcceptanceCard acceptance={pending} showRisk />, person("approver", ROLE_PERMS.approver, 6));
    const button = screen.getByRole("button", { name: "Approve or reject" });
    expect(button).toBeDisabled();
    expect(button).toHaveAccessibleDescription("You own this risk, so another approver must decide.");
  });

  it("lets another approver decide", () => {
    renderAs(<AcceptanceCard acceptance={{ ...pending, can_decide: true, cannot_decide_reason: null }} showRisk />, person("approver", ROLE_PERMS.approver, 7));
    expect(screen.getByRole("button", { name: "Approve or reject" })).toBeEnabled();
  });

  it("hides decisions from roles that can't decide", () => {
    renderAs(<AcceptanceCard acceptance={pending} showRisk />, person("auditor", ROLE_PERMS.auditor));
    const card = screen.getByText(/Compensating controls/).closest(".card") as HTMLElement;
    expect(within(card).queryByRole("button")).toBeNull();
  });
});

describe("inherent and residual risk", () => {
  const score = (s: number) => ({
    likelihood: 1,
    impact: s,
    score: s,
    band: bandFor(s),
    above_appetite: s >= 10,
    explanation: "x",
  });
  it("summarises the residual against the inherent score", () => {
    expect(residualSummary({ inherent: score(20), residual: null, original_score: 20 })).toBe(
      "Inherent 20, not yet reassessed.",
    );
    expect(residualSummary({ inherent: score(20), residual: score(8), original_score: 20 })).toBe(
      "Residual 8 (was 20 inherent), down 12.",
    );
    expect(residualSummary({ inherent: null, residual: null, original_score: null })).toBe("Not assessed yet.");
  });

  it("shows inherent then residual in the register", () => {
    renderAs(<InherentResidual risk={{ inherent: score(20), residual: score(8), original_score: 20 }} />, null);
    expect(screen.getByTitle("Inherent 20, residual 8")).toHaveTextContent("20 → 8");
  });

  it("offers the methodology page to every role", () => {
    for (const role of Object.keys(ROLE_PERMS)) {
      expect(navFor((p) => ROLE_PERMS[role].includes(p)).map((n) => n.label)).toContain("How scoring works");
    }
  });
});
