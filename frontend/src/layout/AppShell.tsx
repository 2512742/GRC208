import { ArrowRightStartOnRectangleIcon, Bars3Icon, XMarkIcon } from "@heroicons/react/24/outline";
import { useEffect, useState } from "react";
import { NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";

import { useAuth, useMe } from "../auth/AuthContext";
import { cx } from "../components/ui";
import { ROLE_LABELS } from "../lib/format";
import { ThemeToggle, TimezoneSelect } from "./TopBarControls";
import { navFor } from "./nav";

function Brand() {
  return (
    <div className="flex items-center gap-2">
      <span className="flex h-8 w-8 items-center justify-center bg-primary-container text-sm font-bold text-white">
        RT
      </span>
      <span className="leading-tight">
        <span className="block text-sm font-bold text-primary">RiskTrack</span>
        <span className="block text-[11px] text-muted">The Alajo · cyber risk</span>
      </span>
    </div>
  );
}

function SideNav({ onNavigate }: { onNavigate?: () => void }) {
  const { can } = useAuth();
  return (
    <nav aria-label="Main" className="flex flex-col gap-0.5 p-2">
      {navFor(can).map(({ to, label, icon: Icon }) => (
        <NavLink
          key={to}
          to={to}
          end={to === "/"}
          onClick={onNavigate}
          className={({ isActive }) =>
            cx(
              "flex items-center gap-3 border-l-2 px-3 py-2 text-sm font-medium no-underline hover:bg-hover hover:no-underline",
              isActive ? "border-accent bg-accent/10 text-accent" : "border-transparent text-ink",
            )
          }
        >
          <Icon className="h-5 w-5 shrink-0" aria-hidden />
          {label}
        </NavLink>
      ))}
    </nav>
  );
}

function UserMenu() {
  const me = useMe();
  const { signOut } = useAuth();
  const navigate = useNavigate();
  return (
    <div className="flex items-center gap-2">
      <div className="hidden text-right leading-tight sm:block">
        <div className="text-sm font-semibold">{me.full_name}</div>
        <div className="text-[11px] text-muted">
          {me.job_title && me.job_title.toLowerCase() !== ROLE_LABELS[me.role].toLowerCase()
            ? `${me.job_title} · ${ROLE_LABELS[me.role]}`
            : ROLE_LABELS[me.role]}
        </div>
      </div>
      <button
        type="button"
        className="btn-ghost btn-sm px-2"
        aria-label="Sign out"
        title="Sign out"
        onClick={async () => {
          await signOut();
          navigate("/login", { replace: true });
        }}
      >
        <ArrowRightStartOnRectangleIcon className="h-5 w-5" aria-hidden />
      </button>
    </div>
  );
}

export function AppShell() {
  const [open, setOpen] = useState(false);
  const location = useLocation();
  useEffect(() => setOpen(false), [location.pathname]);

  return (
    <div className="flex min-h-screen flex-col">
      <a href="#main" className="sr-only focus:not-sr-only focus:absolute focus:z-50 focus:bg-surface focus:p-2">
        Skip to content
      </a>
      <header className="no-print sticky top-0 z-30 flex h-14 items-center gap-2 border-b border-line bg-surface px-3 md:px-4">
        <button
          type="button"
          className="btn-ghost btn-sm px-2 lg:hidden"
          aria-label="Open menu"
          aria-expanded={open}
          onClick={() => setOpen(true)}
        >
          <Bars3Icon className="h-6 w-6" aria-hidden />
        </button>
        <Brand />
        <div className="ml-auto flex items-center gap-1 sm:gap-2">
          <TimezoneSelect />
          <ThemeToggle />
          <UserMenu />
        </div>
      </header>

      <div className="flex flex-1">
        <aside className="no-print sticky top-14 hidden h-[calc(100vh-3.5rem)] w-60 shrink-0 overflow-y-auto border-r border-line bg-surface lg:block">
          <SideNav />
        </aside>

        {open && (
          <div className="fixed inset-0 z-40 lg:hidden" role="dialog" aria-modal="true" aria-label="Menu">
            <div className="absolute inset-0 bg-black/50" onClick={() => setOpen(false)} />
            <div className="absolute inset-y-0 left-0 flex w-72 max-w-[85vw] flex-col border-r border-line bg-surface">
              <div className="flex h-14 items-center justify-between border-b border-line px-3">
                <Brand />
                <button type="button" className="btn-ghost btn-sm px-2" aria-label="Close menu" onClick={() => setOpen(false)}>
                  <XMarkIcon className="h-6 w-6" aria-hidden />
                </button>
              </div>
              <SideNav onNavigate={() => setOpen(false)} />
            </div>
          </div>
        )}

        <main id="main" className="min-w-0 flex-1 px-4 py-6 md:px-8">
          <Outlet />
        </main>
      </div>

      <footer className="no-print bg-footer px-4 py-3 text-xs text-white/70">
        RiskTrack · GRC208 Group 1 capstone · The Alajo is a fictional organisation. Deadlines are
        evaluated in WAT (Africa/Lagos).
      </footer>
    </div>
  );
}
