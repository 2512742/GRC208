/** Scoring rubric (level definitions and bands), shown inline on forms and on the methodology page. */
import { BookOpenIcon } from "@heroicons/react/24/outline";
import { useId, useState } from "react";
import { Link } from "react-router-dom";

import { useMethodology } from "../api/queries";
import type { Band, BandRule, ScaleLevel } from "../api/types";
import { BandBadge } from "./risk";
import { ErrorState, Loading } from "./ui";

/** One scale as a list (not a table) so it never scrolls sideways on a phone. */
export function ScaleList({ title, levels, highlight }: { title: string; levels: ScaleLevel[]; highlight?: number }) {
  return (
    <div>
      <div className="label-caps mb-2">{title}</div>
      <ol className="flex flex-col divide-y divide-line border border-line">
        {[...levels].reverse().map((lv) => (
          <li
            key={lv.level}
            className={`flex gap-3 px-3 py-2 text-sm ${highlight === lv.level ? "bg-accent-tint" : ""}`}
            aria-current={highlight === lv.level ? "true" : undefined}
          >
            <span className="mono-data w-5 shrink-0 font-bold">{lv.level}</span>
            <span>
              <span className="font-semibold">{lv.label}.</span> <span className="text-muted">{lv.definition}</span>
            </span>
          </li>
        ))}
      </ol>
    </div>
  );
}

export function BandList({ bands, threshold }: { bands: BandRule[]; threshold: number }) {
  return (
    <ul className="flex flex-col divide-y divide-line border border-line">
      {bands.map((b) => (
        <li key={b.band} className="flex flex-wrap items-center gap-x-3 gap-y-1 px-3 py-2 text-sm">
          <span className="w-20">
            <BandBadge band={b.band as Band} />
          </span>
          <span className="mono-data w-14 font-semibold">
            {b.min_score}–{b.max_score}
          </span>
          <span className="flex-1 text-muted">
            {b.remediation_days ? `Treat within ${b.remediation_days} days` : "Managed by the owner"}; review every{" "}
            {b.review_days} days
            {b.above_appetite ? ` · above appetite (${threshold}+)` : ""}
          </span>
        </li>
      ))}
    </ul>
  );
}

/** "View scoring rubric" button that opens the rubric in place (no nested dialog inside forms). */
export function RubricToggle({ likelihood, impact }: { likelihood?: number; impact?: number }) {
  const [open, setOpen] = useState(false);
  const id = useId();
  return (
    <div>
      <button
        type="button"
        className="btn-ghost btn-sm"
        aria-expanded={open}
        aria-controls={id}
        onClick={() => setOpen((o) => !o)}
      >
        <BookOpenIcon className="h-4 w-4" aria-hidden /> {open ? "Hide scoring rubric" : "View scoring rubric"}
      </button>
      {open && (
        <div id={id} className="mt-2">
          <Rubric likelihood={likelihood} impact={impact} />
        </div>
      )}
    </div>
  );
}

function Rubric({ likelihood, impact }: { likelihood?: number; impact?: number }) {
  const q = useMethodology();
  if (q.isLoading) return <Loading label="Loading the rubric…" />;
  if (q.error || !q.data) return <ErrorState error={q.error} />;
  const m = q.data;
  return (
    <div className="flex flex-col gap-4 border border-line bg-surface p-3">
      <p className="text-sm">{m.formula}</p>
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <ScaleList title="Likelihood (12-month view)" levels={m.likelihood} highlight={likelihood} />
        <ScaleList title="Impact" levels={m.impact} highlight={impact} />
      </div>
      <div>
        <div className="label-caps mb-2">Rating bands</div>
        <BandList bands={m.bands} threshold={m.appetite_threshold} />
      </div>
      <Link to="/methodology" className="text-sm">
        How scoring works: the full method
      </Link>
    </div>
  );
}
