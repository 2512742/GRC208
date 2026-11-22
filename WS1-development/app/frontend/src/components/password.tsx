/** Password fields with a live checklist that mirrors the server's policy (core/security.py). */
import { EyeIcon, EyeSlashIcon } from "@heroicons/react/24/outline";
import { useId, useState } from "react";

import { cx } from "./ui";

export const PASSWORD_MIN = 10;

export function passwordChecks(password: string, username: string, current?: string) {
  return [
    { ok: password.length >= PASSWORD_MIN, text: `At least ${PASSWORD_MIN} characters` },
    { ok: new Set(password).size >= 5, text: "At least 5 different characters" },
    { ok: !!password && !password.toLowerCase().includes(username.toLowerCase()), text: "Doesn't contain your username" },
    { ok: !!password && password.trim() === password, text: "No spaces at the start or end" },
    ...(current !== undefined ? [{ ok: !!password && password !== current, text: "Different from the current password" }] : []),
  ];
}

export function PasswordInput({
  label,
  value,
  onChange,
  autoComplete,
  required = true,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  autoComplete: "current-password" | "new-password";
  required?: boolean;
}) {
  const id = useId();
  const [shown, setShown] = useState(false);
  return (
    <div className="flex flex-col gap-1">
      <label htmlFor={id} className="label-caps">
        {label}
        {required && <span className="text-danger"> *</span>}
      </label>
      <div className="relative">
        <input
          id={id}
          type={shown ? "text" : "password"}
          className="input pr-11"
          autoComplete={autoComplete}
          autoCapitalize="none"
          spellCheck={false}
          required={required}
          value={value}
          onChange={(e) => onChange(e.target.value)}
        />
        <button
          type="button"
          className="absolute inset-y-0 right-0 flex w-10 items-center justify-center text-muted hover:text-ink"
          aria-label={shown ? "Hide the characters" : "Show the characters"}
          aria-pressed={shown}
          onClick={() => setShown((s) => !s)}
        >
          {shown ? <EyeSlashIcon className="h-5 w-5" aria-hidden /> : <EyeIcon className="h-5 w-5" aria-hidden />}
        </button>
      </div>
    </div>
  );
}

export function PasswordChecklist({ checks }: { checks: { ok: boolean; text: string }[] }) {
  return (
    <ul className="grid grid-cols-1 gap-1 text-xs sm:grid-cols-2" aria-label="Password requirements">
      {checks.map((c) => (
        <li key={c.text} className={cx("flex items-center gap-1.5", c.ok ? "text-band-low" : "text-muted")}>
          <span aria-hidden className="mono-data w-3">{c.ok ? "✓" : "·"}</span>
          {c.text}
          <span className="sr-only">{c.ok ? "(met)" : "(not met yet)"}</span>
        </li>
      ))}
    </ul>
  );
}

/** New password + confirmation + checklist; `valid` tells the form whether it may submit. */
export function NewPasswordFields({
  username,
  current,
  value,
  confirm,
  onValue,
  onConfirm,
}: {
  username: string;
  current?: string;
  value: string;
  confirm: string;
  onValue: (v: string) => void;
  onConfirm: (v: string) => void;
}) {
  const checks = passwordChecks(value, username, current);
  return (
    <div className="flex flex-col gap-3">
      <PasswordInput label="New password" autoComplete="new-password" value={value} onChange={onValue} />
      <PasswordChecklist checks={checks} />
      <PasswordInput label="Confirm new password" autoComplete="new-password" value={confirm} onChange={onConfirm} />
      {confirm && confirm !== value && <div className="text-xs font-semibold text-danger">The two passwords don't match.</div>}
    </div>
  );
}

export function newPasswordValid(value: string, confirm: string, username: string, current?: string): boolean {
  return value === confirm && passwordChecks(value, username, current).every((c) => c.ok);
}
