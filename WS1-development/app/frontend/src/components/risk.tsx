/** Risk-specific display pieces: band badge, score, status chip, explanation, heat map. */
import type { Band, HeatCell, RiskSummary, ScoreSummary } from "../api/types";
import { IMPACT_LABELS, LIKELIHOOD_LABELS, bandFor, sentenceCase, titleCase } from "../lib/format";
import { cx } from "./ui";

const BAND_TEXT: Record<Band, string> = {
  low: "text-band-low border-band-low",
  medium: "text-band-medium border-band-medium",
  high: "text-band-high border-band-high",
  critical: "text-band-critical border-band-critical",
};

const BAND_TINT: Record<Band, string> = {
  low: "bg-band-low/15",
  medium: "bg-band-medium/15",
  high: "bg-band-high/15",
  critical: "bg-band-critical/15",
};

/** Colour is never the only signal: the band name is always printed. */
export function BandBadge({ band }: { band: Band }) {
  return (
    <span className={cx("chip whitespace-nowrap", BAND_TEXT[band], BAND_TINT[band])}>
      {titleCase(band)}
    </span>
  );
}

export function ScoreBadge({ score }: { score: ScoreSummary | null | undefined }) {
  if (!score) return <span className="chip text-muted">Not assessed</span>;
  return (
    <span className="inline-flex flex-wrap items-center gap-x-2 gap-y-1">
      <span className="mono-data text-base font-bold" title={score.explanation}>
        {score.likelihood}×{score.impact}={score.score}
      </span>
      <BandBadge band={score.band} />
      {score.above_appetite && (
        <span className="chip-strong whitespace-nowrap" title="Score at or above the appetite threshold">
          Above appetite
        </span>
      )}
    </span>
  );
}

/** "20 → 8" once reassessed, otherwise "20, not reassessed". */
export function InherentResidual({ risk }: { risk: Pick<RiskSummary, "inherent" | "residual" | "original_score"> }) {
  const inherent = risk.inherent?.score ?? risk.original_score;
  if (inherent == null) return <span className="text-muted">—</span>;
  return (
    <span className="text-sm" title={risk.residual ? `Inherent ${inherent}, residual ${risk.residual.score}` : `Inherent ${inherent}, not yet reassessed`}>
      <span className="mono-data font-semibold">{inherent}</span>
      {risk.residual ? (
        <>
          {"\u00a0→ "}
          <span className="mono-data font-semibold">{risk.residual.score}</span>
        </>
      ) : (
        <span className="text-xs text-muted">, not reassessed</span>
      )}
    </span>
  );
}

/** "Residual 8 (was 20), down 12" or "Inherent 20, not yet reassessed". */
export function residualSummary(risk: Pick<RiskSummary, "inherent" | "residual" | "original_score">): string {
  const inherent = risk.inherent?.score ?? risk.original_score;
  if (inherent == null) return "Not assessed yet.";
  if (!risk.residual) return `Inherent ${inherent}, not yet reassessed.`;
  const change = inherent - risk.residual.score;
  const trend = change > 0 ? `, down ${change}` : change < 0 ? `, up ${-change}` : ", unchanged";
  return `Residual ${risk.residual.score} (was ${inherent} inherent)${trend}.`;
}

const STRONG_STATUSES = new Set(["overdue", "expired", "acceptance_expired", "rejected", "blocked"]);

export function StatusChip({ status }: { status: string | null | undefined }) {
  if (!status) return <span className="text-muted">—</span>;
  return (
    <span className={STRONG_STATUSES.has(status) ? "chip-strong" : "chip"}>
      {sentenceCase(status)}
    </span>
  );
}

export function Explanation({ text }: { text: string }) {
  return (
    <p className="border-l-4 border-accent bg-accent/5 px-3 py-2 font-medium" data-testid="explanation">
      {text}
    </p>
  );
}

/**
 * 5×5 heat map: likelihood rows (5 at the top), impact columns. A dashed line marks the cells at
 * or above the appetite threshold. Clicking a cell with risks calls onSelect.
 */
export function HeatMap({
  cells,
  threshold,
  onSelect,
  selected,
}: {
  cells: HeatCell[];
  threshold: number;
  onSelect?: (cell: HeatCell) => void;
  selected?: { likelihood: number; impact: number } | null;
}) {
  const at = (l: number, i: number) =>
    cells.find((c) => c.likelihood === l && c.impact === i) ?? {
      likelihood: l,
      impact: i,
      score: l * i,
      count: 0,
      risk_codes: [],
    };
  return (
    <div>
      <div className="grid w-full grid-cols-[1.25rem_repeat(5,minmax(0,1fr))] gap-px lg:grid-cols-[auto_repeat(5,minmax(0,1fr))]">
        <div className="label-caps flex items-end justify-center pb-1 text-[10px]" title="Likelihood rows, impact columns">
          <span aria-hidden>L\I</span>
          <span className="sr-only">Likelihood rows, impact columns</span>
        </div>
        {[1, 2, 3, 4, 5].map((i) => (
          <div key={`h${i}`} className="label-caps truncate pb-1 text-center text-[10px]" title={IMPACT_LABELS[i]}>
            {i}
            <span className="hidden lg:inline"> {IMPACT_LABELS[i]}</span>
          </div>
        ))}
        {[5, 4, 3, 2, 1].map((l) => (
          <Row key={l} l={l} at={at} threshold={threshold} onSelect={onSelect} selected={selected} />
        ))}
      </div>
      <p className="mt-2 text-xs text-muted">
        Dashed outline: score {threshold} or more (above appetite). Click a cell to see its risks.
      </p>
    </div>
  );
}

function Row({
  l,
  at,
  threshold,
  onSelect,
  selected,
}: {
  l: number;
  at: (l: number, i: number) => HeatCell;
  threshold: number;
  onSelect?: (cell: HeatCell) => void;
  selected?: { likelihood: number; impact: number } | null;
}) {
  return (
    <>
      <div className="label-caps flex items-center justify-center text-[10px] lg:justify-start lg:pr-2" title={LIKELIHOOD_LABELS[l]}>
        {l}
        <span className="hidden lg:inline">&nbsp;{LIKELIHOOD_LABELS[l]}</span>
      </div>
      {[1, 2, 3, 4, 5].map((i) => {
        const cell = at(l, i);
        const band = bandFor(cell.score);
        const above = cell.score >= threshold;
        const isSelected = selected?.likelihood === l && selected?.impact === i;
        return (
          <button
            key={i}
            type="button"
            disabled={!onSelect || cell.count === 0}
            onClick={() => onSelect?.(cell)}
            aria-label={`Likelihood ${l}, impact ${i}, score ${cell.score} (${band}): ${cell.count} risk${cell.count === 1 ? "" : "s"}${cell.count ? `: ${cell.risk_codes.join(", ")}` : ""}`}
            title={cell.risk_codes.join(", ") || "No risks"}
            className={cx(
              "relative flex aspect-square min-w-0 flex-col items-center justify-center border sm:aspect-[4/3]",
              BAND_TINT[band],
              above ? "border-dashed border-ink/70" : "border-transparent",
              isSelected && "outline outline-2 outline-accent",
              cell.count > 0 && onSelect && "hover:brightness-95 dark:hover:brightness-125",
            )}
          >
            <span className={cx("mono-data text-base font-bold leading-none sm:text-lg", cell.count ? BAND_TEXT[band].split(" ")[0] : "text-muted/50")}>
              {cell.count || "·"}
            </span>
            <span className="mono-data mt-1 text-[10px] leading-none text-muted">{cell.score}</span>
          </button>
        );
      })}
    </>
  );
}
