/** Every shared component on static mock data, in the current theme (U0 "done when"). */
import { useState } from "react";
import { Link } from "react-router-dom";

import type { HeatCell, RiskSummary } from "../api/types";
import { ConfirmDialog, Modal } from "../components/Modal";
import { BandBadge, Explanation, HeatMap, ScoreBadge, StatusChip } from "../components/risk";
import { useToast } from "../components/Toast";
import {
  Card,
  DataTable,
  DateOnly,
  DateTime,
  EmptyState,
  ErrorState,
  KeyValue,
  Loading,
  Notice,
  PageHeader,
  Pagination,
  SelectField,
  StatTile,
  Tabs,
  TextArea,
  TextField,
} from "../components/ui";
import { BANDS, bandFor } from "../lib/format";
import { ThemeToggle, TimezoneSelect } from "../layout/TopBarControls";

const MOCK_RISKS: RiskSummary[] = [
  {
    id: 1,
    risk_code: "R-001",
    title: "Wallet ledger race condition allowing double-spend",
    category: "Fraud",
    current: { likelihood: 4, impact: 5, score: 20, band: "critical", above_appetite: true, explanation: "Likelihood 4 (Likely) × Impact 5 (Severe) = 20 → Critical. Above appetite (threshold 10). Remediation due within 30 days." },
    original_score: 20,
    owner: { id: 3, full_name: "Emmanuel Teye Adjei", role: "owner" },
    status: "treatment_in_progress",
    display_status: "treatment_in_progress",
    services: ["S1"],
    assets: [],
    next_review_date: "2026-12-19",
    review_due_soon: true,
    strategy: "reduce",
    overdue_actions: 0,
    open_actions: 2,
  },
  {
    id: 13,
    risk_code: "R-013",
    title: "Phishing of support staff leading to account takeover",
    category: "People",
    current: { likelihood: 1, impact: 4, score: 4, band: "low", above_appetite: false, explanation: "Likelihood 1 (Rare) × Impact 4 (Major) = 4 → Low. Within appetite (threshold 10)." },
    original_score: 12,
    owner: { id: 5, full_name: "Gilbert Obichere", role: "owner" },
    status: "open",
    display_status: "open",
    services: ["S3"],
    assets: [],
    next_review_date: "2027-11-19",
    review_due_soon: false,
    strategy: "reduce",
    overdue_actions: 0,
    open_actions: 0,
  },
];

const MOCK_CELLS: HeatCell[] = [
  { likelihood: 4, impact: 5, score: 20, count: 3, risk_codes: ["R-001", "R-004", "R-007"] },
  { likelihood: 3, impact: 4, score: 12, count: 2, risk_codes: ["R-002", "R-009"] },
  { likelihood: 2, impact: 3, score: 6, count: 4, risk_codes: ["R-011", "R-016", "R-018", "R-020"] },
  { likelihood: 1, impact: 4, score: 4, count: 1, risk_codes: ["R-013"] },
];

export default function KitchenSinkPage() {
  const toast = useToast();
  const [tab, setTab] = useState<"a" | "b">("a");
  const [modal, setModal] = useState(false);
  const [confirm, setConfirm] = useState(false);
  return (
    <div className="mx-auto max-w-6xl p-4 md:p-8">
      <div className="mb-4 flex flex-wrap items-center justify-end gap-2">
        <TimezoneSelect />
        <ThemeToggle />
        <Link to="/">Open the app</Link>
      </div>
      <PageHeader eyebrow="Design system" title="Kitchen sink" description="Guardian Deep Intel components on mock data. Toggle the theme and narrow the window to check both themes and the phone layout." actions={<button className="btn-primary">Primary action</button>} />

      <section className="mb-8 flex flex-col gap-3">
        <h2 className="label-caps text-ink">Type</h2>
        <div className="text-display text-primary">Display 48</div>
        <h1>Heading 1 · 32</h1>
        <h2>Heading 2 · 24</h2>
        <h3>Heading 3 · 20</h3>
        <p className="text-base">Body large 16. The quick brown fox jumps over the lazy dog.</p>
        <p>Body 14. The quick brown fox jumps over the lazy dog.</p>
        <div className="label-caps">Label caps 12</div>
        <div className="mono-data">mono-data 13 · R-013 · 4×5=20 · 9f2c…e1a0</div>
      </section>

      <section className="mb-8 flex flex-col gap-3">
        <h2 className="label-caps text-ink">Buttons and chips</h2>
        <div className="flex flex-wrap gap-2">
          <button className="btn-primary">Primary</button>
          <button className="btn-secondary">Secondary</button>
          <button className="btn-ghost">Ghost</button>
          <button className="btn-danger">Danger</button>
          <button className="btn-primary" disabled>
            Disabled
          </button>
          <button className="btn-secondary btn-sm">Small</button>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {BANDS.map((b) => (
            <BandBadge key={b} band={b} />
          ))}
          <StatusChip status="open" />
          <StatusChip status="overdue" />
          <StatusChip status="acceptance_expired" />
          <span className="chip">Normal chip</span>
          <span className="chip-strong">Strong chip</span>
        </div>
        <div className="flex flex-wrap gap-4">
          <ScoreBadge score={MOCK_RISKS[0].current} />
          <ScoreBadge score={MOCK_RISKS[1].current} />
          <ScoreBadge score={null} />
        </div>
        <Explanation text={MOCK_RISKS[0].current!.explanation} />
      </section>

      <section className="mb-8 grid grid-cols-2 gap-3 md:grid-cols-4">
        <StatTile label="Risks" value={22} hint="22 assessed" />
        <StatTile label="Above appetite" value={14} tone="alert" hint="Score ≥ 10" />
        <StatTile label="Overdue actions" value={1} tone="alert" />
        <StatTile label="Open cost" value="₦30.65m" />
      </section>

      <section className="mb-8 grid grid-cols-1 gap-6 lg:grid-cols-2">
        <Card title="Form controls">
          <div className="flex flex-col gap-4">
            <TextField label="Title" required placeholder="Risk title" />
            <TextField label="With error" defaultValue="abc" error="Title must be at least 5 characters." />
            <SelectField label="Likelihood" options={[1, 2, 3, 4, 5].map((n) => ({ value: n, label: String(n) }))} hint="1 Rare to 5 Almost certain" />
            <TextArea label="Rationale" />
            <label className="flex items-center gap-2">
              <input type="checkbox" defaultChecked /> Checkbox
            </label>
          </div>
        </Card>
        <Card title="Heat map">
          <HeatMap cells={MOCK_CELLS} threshold={10} onSelect={(c) => toast.success(`${c.risk_codes.join(", ")} (score ${c.score}, ${bandFor(c.score)})`)} />
        </Card>
      </section>

      <section className="mb-8 flex flex-col gap-3">
        <h2 className="label-caps text-ink">Data table (stacked cards below 768 px)</h2>
        <DataTable
          caption="Mock risks"
          rows={MOCK_RISKS}
          rowKey={(r) => r.id}
          columns={[
            { key: "id", header: "ID", render: (r) => <span className="mono-data">{r.risk_code}</span> },
            { key: "title", header: "Risk", render: (r) => r.title },
            { key: "score", header: "Score", render: (r) => <ScoreBadge score={r.current} /> },
            { key: "status", header: "Status", render: (r) => <StatusChip status={r.display_status} /> },
            { key: "review", header: "Next review", render: (r) => <DateOnly day={r.next_review_date} /> },
          ]}
        />
        <Pagination page={1} pageSize={25} total={60} onPage={() => undefined} />
      </section>

      <section className="mb-8 grid grid-cols-1 gap-6 lg:grid-cols-2">
        <Card title="Tabs and key values">
          <Tabs tabs={[{ key: "a", label: "First" }, { key: "b", label: "Second" }]} active={tab} onChange={setTab} />
          <div className="mt-4">
            <KeyValue items={[["Owner", "Emmanuel Teye Adjei"], ["Created", <DateTime iso="2026-11-19T13:30:00Z" />], ["Due", <DateOnly day="2026-12-05" />], ["Band", <BandBadge band="high" />]]} />
          </div>
        </Card>
        <Card title="Feedback">
          <div className="flex flex-col gap-3">
            <Notice title="Information">Deadlines are evaluated in WAT.</Notice>
            <Notice tone="warning" title="Awaiting reassessment">The score stays until an analyst reassesses.</Notice>
            <Notice tone="danger">You own this risk, so you can't approve its acceptance.</Notice>
            <div className="flex flex-wrap gap-2">
              <button className="btn-secondary btn-sm" onClick={() => toast.success("Saved.")}>
                Success toast
              </button>
              <button className="btn-secondary btn-sm" onClick={() => toast.error("Something failed.")}>
                Error toast
              </button>
              <button className="btn-secondary btn-sm" onClick={() => setModal(true)}>
                Modal
              </button>
              <button className="btn-secondary btn-sm" onClick={() => setConfirm(true)}>
                Confirm dialog
              </button>
            </div>
          </div>
        </Card>
      </section>

      <section className="mb-8 grid grid-cols-1 gap-6 lg:grid-cols-3">
        <EmptyState title="Nothing here">Empty state</EmptyState>
        <ErrorState error={new Error("The server could not be reached.")} retry={() => undefined} />
        <div className="card">
          <Loading />
        </div>
      </section>

      <Modal open={modal} title="Example modal" onClose={() => setModal(false)} footer={<button className="btn-primary" onClick={() => setModal(false)}>Done</button>}>
        <p>Focus is trapped here; Escape closes.</p>
      </Modal>
      <ConfirmDialog open={confirm} title="Commit this import?" message="3 valid rows will be created." onConfirm={() => toast.success("Confirmed.")} onClose={() => setConfirm(false)} />
    </div>
  );
}
