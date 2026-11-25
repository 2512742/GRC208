import { useMethodology } from "../api/queries";
import { BandList, ScaleList } from "../components/methodology";
import { Card, ErrorState, Loading, PageHeader } from "../components/ui";

const CONTROLS: [string, string][] = [
  [
    "Segregation of duties",
    "Nobody approves their own risk acceptance or their own request. The server enforces this, not only the screen.",
  ],
  [
    "Evidence before change",
    "A treatment action is completed only with an evidence file, and a reassessment needs evidence for the new scores.",
  ],
  [
    "History is never overwritten",
    "Assessments, decisions, approvals and evidence are insert-only. Every change is written to a hash-chained audit log that an auditor can verify.",
  ],
  [
    "Deadlines and expiry",
    "Remediation deadlines, review dates and acceptance expiry are worked out from the band and checked every day in Lagos time.",
  ],
];

/** "How scoring works": the documented method behind every score (brief feature 2). */
export default function MethodologyPage() {
  const q = useMethodology();
  if (q.isLoading) return <Loading />;
  if (q.error || !q.data) return <ErrorState error={q.error} retry={() => q.refetch()} />;
  const m = q.data;
  return (
    <>
      <PageHeader
        eyebrow="Methodology"
        title="How scoring works"
        description="The method the register uses to score, rate and govern every risk."
      />
      <div className="flex max-w-4xl flex-col gap-6">
        <Card title="1. Score">
          <p>{m.formula}</p>
          <p className="mt-2 text-sm text-muted">
            The analyst picks a likelihood and an impact level using the definitions below. The server calculates the
            score, band and appetite result and stores them with a plain-language explanation.
          </p>
          <div className="mt-4 grid grid-cols-1 gap-4 lg:grid-cols-2">
            <ScaleList title="Likelihood (12-month view)" levels={m.likelihood} />
            <ScaleList title="Impact" levels={m.impact} />
          </div>
        </Card>

        <Card title="2. Rating band and deadlines">
          <BandList bands={m.bands} threshold={m.appetite_threshold} />
          <p className="mt-3 text-sm text-muted">
            The remediation deadline is the due date for treatment actions. A review warning appears{" "}
            {m.review_warning_days} days before the next review date.
          </p>
        </Card>

        <Card title="3. Risk appetite">
          <p>{m.appetite_statement}</p>
        </Card>

        <Card title="4. Inherent and residual risk">
          <dl className="flex flex-col gap-3 text-sm">
            <div>
              <dt className="font-semibold">Inherent risk</dt>
              <dd className="text-muted">The first assessment, before treatment. It is kept unchanged for comparison.</dd>
            </div>
            <div>
              <dt className="font-semibold">Target risk</dt>
              <dd className="text-muted">The score the treatment decision aims for.</dd>
            </div>
            <div>
              <dt className="font-semibold">Residual risk</dt>
              <dd className="text-muted">
                The score after treatment. Once an owner completes an action with evidence, the risk waits for an
                analyst to reassess it; the reassessment records the new score, the evidence and the actions it
                followed. Until then the risk shows &ldquo;Inherent, not yet reassessed&rdquo;.
              </dd>
            </div>
          </dl>
        </Card>

        <Card title="5. Governance controls">
          <dl className="flex flex-col gap-3 text-sm">
            {CONTROLS.map(([title, text]) => (
              <div key={title}>
                <dt className="font-semibold">{title}</dt>
                <dd className="text-muted">{text}</dd>
              </div>
            ))}
          </dl>
          <p className="mt-3 text-xs text-muted">Business dates use {m.org_timezone}.</p>
        </Card>
      </div>
    </>
  );
}
