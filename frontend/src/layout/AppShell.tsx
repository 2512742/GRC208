/**
 * App shell, following Guardian's layout:
 * - solid teal top bar (brand, then theme toggle and user controls);
 * - desktop (lg+): side navigation;
 * - phones and tablets: app-style bottom tab bar with a "More" sheet, no website footer
 *   (Guardian `app-tabbar` / `_bottom_nav_style.html`).
 */
import {
  ArrowRightStartOnRectangleIcon,
  ShieldCheckIcon,
  XMarkIcon,
} from "@heroicons/react/24/outline";
import { useEffect, useState } from "react";
import { NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";

import { useAuth, useMe } from "../auth/AuthContext";
import { cx } from "../components/ui";
import { ROLE_LABELS } from "../lib/format";
import { ThemeToggle, TimezoneSelect } from "./TopBarControls";
import { MORE_ICON, TAB_ITEMS, navFor } from "./nav";

function Brand() {
  return (
    <span className="flex items-center gap-2 text-lg font-bold tracking-tight text-white">
      <ShieldCheckIcon className="h-6 w-6" aria-hidden />
      <span>RiskTrack</span>
      <span className="hidden border-l border-white/30 pl-2 text-xs font-medium text-white/70 sm:inline">
        The Alajo
      </span>
    </span>
  );
}

function roleLine(job: string | null, role: string): string {
  const label = ROLE_LABELS[role] ?? role;
  return job && job.toLowerCase() !== label.toLowerCase() ? `${job} · ${label}` : label;
}

function SideNav() {
  const { can } = useAuth();
  return (
    <nav aria-label="Main" className="flex flex-col gap-0.5 p-2">
      {navFor(can).map(({ to, label, icon: Icon }) => (
        <NavLink
          key={to}
          to={to}
          end={to === "/"}
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

function useSignOut() {
  const { signOut } = useAuth();
  const navigate = useNavigate();
  return async () => {
    await signOut();
    navigate("/login", { replace: true });
  };
}

function DesktopUser() {
  const me = useMe();
  const signOut = useSignOut();
  return (
    <div className="flex items-center gap-2">
      <div className="hidden text-right leading-tight xl:block">
        <div className="text-sm font-semibold text-white">{me.full_name}</div>
        <div className="text-[11px] text-white/70">{roleLine(me.job_title, me.role)}</div>
      </div>
      <button
        type="button"
        className="p-2 text-white/80 hover:text-white"
        aria-label="Sign out"
        title="Sign out"
        onClick={signOut}
      >
        <ArrowRightStartOnRectangleIcon className="h-5 w-5" aria-hidden />
      </button>
    </div>
  );
}

/** Bottom tab bar for phones and tablets (Guardian app-tabbar). */
function TabBar({ onMore, moreActive }: { onMore: () => void; moreActive: boolean }) {
  const base =
    "flex min-w-0 flex-col items-center gap-1 border-t-2 px-1 pb-1.5 pt-2 text-[11px] font-semibold no-underline hover:no-underline";
  const MoreIcon = MORE_ICON;
  return (
    <nav
      aria-label="Main"
      className="app-tabbar no-print fixed inset-x-0 bottom-0 z-40 grid grid-cols-5 border-t border-line bg-surface lg:hidden"
    >
      {TAB_ITEMS.map(({ to, label, icon: Icon }) => (
        <NavLink
          key={to}
          to={to}
          end={to === "/"}
          className={({ isActive }) =>
            cx(base, isActive && !moreActive ? "border-accent text-accent" : "border-transparent text-muted")
          }
        >
          <Icon className="h-[22px] w-[22px]" aria-hidden />
          <span className="truncate">{label}</span>
        </NavLink>
      ))}
      <button
        type="button"
        onClick={onMore}
        aria-haspopup="dialog"
        aria-expanded={moreActive}
        className={cx(base, moreActive ? "border-accent text-accent" : "border-transparent text-muted")}
      >
        <MoreIcon className="h-[22px] w-[22px]" aria-hidden />
        <span>More</span>
      </button>
    </nav>
  );
}

/** "More" sheet: the remaining screens, display time zone, who is signed in, sign out. */
function MoreSheet({ onClose }: { onClose: () => void }) {
  const me = useMe();
  const { can } = useAuth();
  const signOut = useSignOut();
  const tabPaths = new Set(TAB_ITEMS.map((t) => t.to));
  const rest = navFor(can).filter((n) => !tabPaths.has(n.to));

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    document.addEventListener("keydown", onKey);
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", onKey);
      document.body.style.overflow = "";
    };
  }, [onClose]);

  return (
    <div className="fixed inset-0 z-50 lg:hidden" role="dialog" aria-modal="true" aria-label="More">
      <div className="absolute inset-0 bg-black/50" onClick={onClose} />
      <div className="sheet-in absolute inset-x-0 bottom-0 max-h-[85vh] overflow-y-auto border-t border-line bg-surface pb-[env(safe-area-inset-bottom)]">
        <div className="flex items-center justify-between border-b border-line px-4 py-3">
          <div className="min-w-0">
            <div className="truncate text-sm font-semibold">{me.full_name}</div>
            <div className="truncate text-xs text-muted">{roleLine(me.job_title, me.role)}</div>
          </div>
          <button type="button" className="btn-ghost btn-sm px-2" aria-label="Close" onClick={onClose}>
            <XMarkIcon className="h-6 w-6" aria-hidden />
          </button>
        </div>
        {rest.length > 0 && (
          <ul className="grid grid-cols-3 gap-px border-b border-line bg-line">
            {rest.map(({ to, label, icon: Icon }) => (
              <li key={to} className="bg-surface">
                <NavLink
                  to={to}
                  onClick={onClose}
                  className={({ isActive }) =>
                    cx(
                      "flex flex-col items-center gap-1.5 px-2 py-4 text-center text-xs font-semibold no-underline hover:bg-hover hover:no-underline",
                      isActive ? "text-accent" : "text-ink",
                    )
                  }
                >
                  <Icon className="h-6 w-6" aria-hidden />
                  {label}
                </NavLink>
              </li>
            ))}
          </ul>
        )}
        <div className="flex flex-col gap-4 p-4">
          <div>
            <div className="label-caps mb-1">Show times in</div>
            <TimezoneSelect compact />
            <p className="mt-1 text-xs text-muted">Deadlines are always evaluated in WAT (Lagos).</p>
          </div>
          <button type="button" className="btn-secondary w-full" onClick={signOut}>
            <ArrowRightStartOnRectangleIcon className="h-5 w-5" aria-hidden /> Sign out
          </button>
        </div>
      </div>
    </div>
  );
}

export function AppShell() {
  const [more, setMore] = useState(false);
  const location = useLocation();
  useEffect(() => {
    setMore(false);
    window.scrollTo(0, 0); // each screen starts at the top, as in a native app
  }, [location.pathname]);

  return (
    <div className="flex min-h-screen flex-col">
      <a href="#main" className="sr-only focus:not-sr-only focus:absolute focus:z-50 focus:bg-surface focus:p-2">
        Skip to content
      </a>
      <header className="no-print sticky top-0 z-30 border-b border-outline bg-primary-container pt-[env(safe-area-inset-top)] text-white">
        <div className="flex h-14 items-center gap-2 px-4">
          <NavLink to="/" className="no-underline hover:no-underline" aria-label="RiskTrack home">
            <Brand />
          </NavLink>
          <div className="ml-auto flex items-center gap-1 sm:gap-2">
            <div className="hidden lg:block">
              <TimezoneSelect onDark />
            </div>
            <ThemeToggle onDark />
            <div className="hidden lg:block">
              <DesktopUser />
            </div>
          </div>
        </div>
      </header>

      <div className="flex flex-1">
        <aside className="no-print sticky top-14 hidden h-[calc(100vh-3.5rem)] w-60 shrink-0 overflow-y-auto border-r border-line bg-surface lg:block">
          <SideNav />
        </aside>
        <main id="main" className="app-main min-w-0 flex-1 px-4 py-5 md:px-6 md:py-6 lg:px-8">
          <Outlet />
        </main>
      </div>

      <footer className="no-print hidden bg-footer px-4 py-3 text-xs text-white/70 lg:block">
        RiskTrack · GRC208 Group 1 capstone · The Alajo is a fictional organisation. Deadlines are
        evaluated in WAT (Africa/Lagos).
      </footer>

      <TabBar onMore={() => setMore(true)} moreActive={more} />
      {more && <MoreSheet onClose={() => setMore(false)} />}
    </div>
  );
}
