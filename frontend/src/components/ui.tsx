/** Shared building blocks of the Guardian design system (U0). */
import { ExclamationTriangleIcon, InboxIcon } from "@heroicons/react/24/outline";
import { useId } from "react";
import type {
  InputHTMLAttributes,
  ReactNode,
  SelectHTMLAttributes,
  TextareaHTMLAttributes,
} from "react";

import { useAuth } from "../auth/AuthContext";
import { formatDate, formatDateTime, formatUtc } from "../lib/time";

export function cx(...parts: (string | false | null | undefined)[]): string {
  return parts.filter(Boolean).join(" ");
}

// ── Layout ────────────────────────────────────────────────────────────────────────────────

export function PageHeader({
  title,
  eyebrow,
  description,
  actions,
}: {
  title: ReactNode;
  eyebrow?: ReactNode;
  description?: ReactNode;
  actions?: ReactNode;
}) {
  return (
    <header className="mb-6 flex flex-col gap-3 border-b border-line pb-4 md:flex-row md:items-end md:justify-between">
      <div className="min-w-0">
        {eyebrow && <div className="label-caps mb-1">{eyebrow}</div>}
        <h1 className="break-words text-2xl md:text-h1">{title}</h1>
        {description && <p className="mt-1 max-w-3xl text-muted">{description}</p>}
      </div>
      {actions && <div className="no-print flex flex-wrap gap-2">{actions}</div>}
    </header>
  );
}

export function Card({
  title,
  actions,
  children,
  className,
  bodyClassName,
}: {
  title?: ReactNode;
  actions?: ReactNode;
  children: ReactNode;
  className?: string;
  bodyClassName?: string;
}) {
  return (
    <section className={cx("card", className)}>
      {(title || actions) && (
        <div className="card-header">
          {title && <h2 className="label-caps text-ink">{title}</h2>}
          {actions && <div className="flex flex-wrap gap-2">{actions}</div>}
        </div>
      )}
      <div className={bodyClassName ?? "p-4"}>{children}</div>
    </section>
  );
}

export function StatTile({
  label,
  value,
  hint,
  tone = "normal",
  onClick,
}: {
  label: string;
  value: ReactNode;
  hint?: ReactNode;
  tone?: "normal" | "alert";
  onClick?: () => void;
}) {
  const body = (
    <>
      <div className="label-caps">{label}</div>
      <div
        className={cx(
          "mono-data mt-2 text-3xl font-bold",
          tone === "alert" ? "text-danger" : "text-primary",
        )}
      >
        {value}
      </div>
      {hint && <div className="mt-1 text-xs text-muted">{hint}</div>}
    </>
  );
  return onClick ? (
    <button type="button" onClick={onClick} className="card p-4 text-left hover:bg-hover">
      {body}
    </button>
  ) : (
    <div className="card p-4">{body}</div>
  );
}

// ── Feedback states ───────────────────────────────────────────────────────────────────────

export function Loading({ label = "Loading…" }: { label?: string }) {
  return (
    <div role="status" className="flex items-center gap-3 p-6 text-muted">
      <span className="inline-block h-4 w-4 animate-spin border-2 border-line border-t-accent" />
      {label}
    </div>
  );
}

export function EmptyState({ title, children }: { title: string; children?: ReactNode }) {
  return (
    <div className="flex flex-col items-center gap-2 border border-dashed border-line p-8 text-center">
      <InboxIcon className="h-8 w-8 text-muted" aria-hidden />
      <div className="font-semibold">{title}</div>
      {children && <div className="text-muted">{children}</div>}
    </div>
  );
}

export function ErrorState({ error, retry }: { error: unknown; retry?: () => void }) {
  const message = error instanceof Error ? error.message : "Something went wrong.";
  return (
    <div role="alert" className="flex items-start gap-3 border border-danger/60 bg-danger/5 p-4">
      <ExclamationTriangleIcon className="mt-0.5 h-5 w-5 shrink-0 text-danger" aria-hidden />
      <div className="flex-1">
        <div className="font-semibold text-danger">Couldn't load this</div>
        <div className="text-muted">{message}</div>
      </div>
      {retry && (
        <button type="button" className="btn-secondary btn-sm" onClick={retry}>
          Try again
        </button>
      )}
    </div>
  );
}

export function Notice({
  tone = "info",
  title,
  children,
}: {
  tone?: "info" | "warning" | "danger";
  title?: ReactNode;
  children: ReactNode;
}) {
  const styles = {
    info: "border-accent/60 bg-accent/5",
    warning: "border-band-medium/70 bg-band-medium/10",
    danger: "border-danger/60 bg-danger/5",
  }[tone];
  return (
    <div role={tone === "info" ? "note" : "alert"} className={cx("border-l-4 p-3", styles)}>
      {title && <div className="font-semibold">{title}</div>}
      <div className={title ? "mt-0.5 text-muted" : ""}>{children}</div>
    </div>
  );
}

// ── Forms ─────────────────────────────────────────────────────────────────────────────────

function FieldShell({
  id,
  label,
  hint,
  error,
  required,
  children,
}: {
  id: string;
  label: ReactNode;
  hint?: ReactNode;
  error?: string;
  required?: boolean;
  children: ReactNode;
}) {
  return (
    <div className="flex flex-col gap-1">
      <label htmlFor={id} className="label-caps">
        {label}
        {required && <span className="text-danger"> *</span>}
      </label>
      {children}
      {hint && !error && (
        <div id={`${id}-hint`} className="text-xs text-muted">
          {hint}
        </div>
      )}
      {error && (
        <div id={`${id}-error`} className="text-xs font-semibold text-danger">
          {error}
        </div>
      )}
    </div>
  );
}

type Common = { label: ReactNode; hint?: ReactNode; error?: string };

export function TextField({ label, hint, error, ...props }: Common & InputHTMLAttributes<HTMLInputElement>) {
  const auto = useId();
  const id = props.id ?? auto;
  return (
    <FieldShell id={id} label={label} hint={hint} error={error} required={props.required}>
      <input
        {...props}
        id={id}
        className={cx("input", error && "border-danger", props.className)}
        aria-invalid={error ? true : undefined}
        aria-describedby={error ? `${id}-error` : hint ? `${id}-hint` : undefined}
      />
    </FieldShell>
  );
}

export function TextArea({
  label,
  hint,
  error,
  ...props
}: Common & TextareaHTMLAttributes<HTMLTextAreaElement>) {
  const auto = useId();
  const id = props.id ?? auto;
  return (
    <FieldShell id={id} label={label} hint={hint} error={error} required={props.required}>
      <textarea
        rows={3}
        {...props}
        id={id}
        className={cx("input", error && "border-danger", props.className)}
        aria-invalid={error ? true : undefined}
        aria-describedby={error ? `${id}-error` : hint ? `${id}-hint` : undefined}
      />
    </FieldShell>
  );
}

export function SelectField({
  label,
  hint,
  error,
  options,
  placeholder,
  ...props
}: Common &
  SelectHTMLAttributes<HTMLSelectElement> & {
    options: { value: string | number; label: string }[];
    placeholder?: string;
  }) {
  const auto = useId();
  const id = props.id ?? auto;
  return (
    <FieldShell id={id} label={label} hint={hint} error={error} required={props.required}>
      <select
        {...props}
        id={id}
        className={cx("input", error && "border-danger", props.className)}
        aria-invalid={error ? true : undefined}
      >
        {placeholder !== undefined && <option value="">{placeholder}</option>}
        {options.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
      </select>
    </FieldShell>
  );
}

// ── Data display ──────────────────────────────────────────────────────────────────────────

export function DateTime({ iso }: { iso: string | null | undefined }) {
  const { zone } = useAuth();
  if (!iso) return <span className="text-muted">—</span>;
  return (
    <time dateTime={iso} title={formatUtc(iso)} className="whitespace-nowrap">
      {formatDateTime(iso, zone)}
    </time>
  );
}

export function DateOnly({ day }: { day: string | null | undefined }) {
  if (!day) return <span className="text-muted">—</span>;
  return (
    <time dateTime={day} className="whitespace-nowrap">
      {formatDate(day)}
    </time>
  );
}

export function KeyValue({ items }: { items: [ReactNode, ReactNode][] }) {
  return (
    <dl className="grid grid-cols-1 gap-x-6 gap-y-3 sm:grid-cols-2">
      {items.map(([k, v], i) => (
        <div key={i} className="min-w-0">
          <dt className="label-caps">{k}</dt>
          <dd className="mt-0.5 break-words">{v}</dd>
        </div>
      ))}
    </dl>
  );
}

export interface Column<T> {
  key: string;
  header: ReactNode;
  render: (row: T) => ReactNode;
  className?: string;
  /** Hide in the stacked phone layout (e.g. redundant IDs). */
  hideOnMobile?: boolean;
}

/**
 * Table on wide screens; stacked cards with captions on phones (Guardian "mob-cards").
 */
export function DataTable<T>({
  rows,
  columns,
  rowKey,
  onRowClick,
  empty = "Nothing to show.",
  caption,
}: {
  rows: T[];
  columns: Column<T>[];
  rowKey: (row: T) => string | number;
  onRowClick?: (row: T) => void;
  empty?: ReactNode;
  caption?: string;
}) {
  if (rows.length === 0) return <EmptyState title={typeof empty === "string" ? empty : "Nothing to show."} />;
  return (
    <>
      <div className="hidden overflow-x-auto md:block">
        <table className="table-base">
          {caption && <caption className="sr-only">{caption}</caption>}
          <thead>
            <tr>
              {columns.map((c) => (
                <th key={c.key} scope="col" className={c.className}>
                  {c.header}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr
                key={rowKey(row)}
                onClick={onRowClick ? () => onRowClick(row) : undefined}
                className={onRowClick ? "cursor-pointer" : undefined}
              >
                {columns.map((c) => (
                  <td key={c.key} className={c.className}>
                    {c.render(row)}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <ul className="flex flex-col gap-2 md:hidden" aria-label={caption}>
        {rows.map((row) => (
          <li
            key={rowKey(row)}
            className={cx("card p-3", onRowClick && "cursor-pointer active:bg-hover")}
            onClick={onRowClick ? () => onRowClick(row) : undefined}
          >
            <dl className="grid grid-cols-[minmax(0,7.5rem)_1fr] gap-x-3 gap-y-1.5">
              {columns
                .filter((c) => !c.hideOnMobile)
                .map((c) => (
                  <div key={c.key} className="contents">
                    <dt className="label-caps pt-0.5">{c.header}</dt>
                    <dd className="min-w-0 break-words">{c.render(row)}</dd>
                  </div>
                ))}
            </dl>
          </li>
        ))}
      </ul>
    </>
  );
}

export function Pagination({
  page,
  pageSize,
  total,
  onPage,
}: {
  page: number;
  pageSize: number;
  total: number;
  onPage: (page: number) => void;
}) {
  const pages = Math.max(1, Math.ceil(total / pageSize));
  if (pages <= 1) return <div className="mt-3 text-xs text-muted">{total} in total</div>;
  return (
    <nav className="mt-3 flex items-center justify-between gap-2" aria-label="Pagination">
      <span className="text-xs text-muted">
        Page {page} of {pages} · {total} in total
      </span>
      <div className="flex gap-2">
        <button className="btn-secondary btn-sm" disabled={page <= 1} onClick={() => onPage(page - 1)}>
          Previous
        </button>
        <button
          className="btn-secondary btn-sm"
          disabled={page >= pages}
          onClick={() => onPage(page + 1)}
        >
          Next
        </button>
      </div>
    </nav>
  );
}

export function Tabs<K extends string>({
  tabs,
  active,
  onChange,
}: {
  tabs: { key: K; label: ReactNode }[];
  active: K;
  onChange: (key: K) => void;
}) {
  return (
    <div role="tablist" className="flex gap-1 overflow-x-auto border-b border-line">
      {tabs.map((t) => (
        <button
          key={t.key}
          role="tab"
          type="button"
          aria-selected={t.key === active}
          onClick={() => onChange(t.key)}
          className={cx(
            "-mb-px whitespace-nowrap border-b-2 px-3 py-2 text-sm font-semibold",
            t.key === active
              ? "border-accent text-accent"
              : "border-transparent text-muted hover:text-ink",
          )}
        >
          {t.label}
        </button>
      ))}
    </div>
  );
}
