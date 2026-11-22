import {
  ArrowUpTrayIcon,
  ChartBarSquareIcon,
  CheckBadgeIcon,
  ClipboardDocumentCheckIcon,
  Cog6ToothIcon,
  DocumentChartBarIcon,
  EllipsisHorizontalCircleIcon,
  HomeIcon,
  FingerPrintIcon,
  ServerStackIcon,
  ShieldExclamationIcon,
  UserCircleIcon,
  UsersIcon,
} from "@heroicons/react/24/outline";
import type { ComponentType, SVGProps } from "react";

export interface NavItem {
  to: string;
  label: string;
  icon: ComponentType<SVGProps<SVGSVGElement>>;
  /** Shown only when the signed-in user holds this permission (the server enforces it too). */
  permission?: string;
}

export const NAV: NavItem[] = [
  { to: "/", label: "Dashboard", icon: ChartBarSquareIcon },
  { to: "/risks", label: "Risk register", icon: ShieldExclamationIcon },
  { to: "/actions", label: "Treatment actions", icon: ClipboardDocumentCheckIcon },
  { to: "/approvals", label: "Acceptances", icon: CheckBadgeIcon },
  { to: "/assets", label: "Assets", icon: ServerStackIcon },
  { to: "/reports", label: "Reports", icon: DocumentChartBarIcon, permission: "export_reports" },
  { to: "/imports", label: "CSV import", icon: ArrowUpTrayIcon, permission: "import_csv" },
  { to: "/audit", label: "Audit log", icon: FingerPrintIcon, permission: "view_audit" },
  { to: "/users", label: "Users", icon: UsersIcon, permission: "manage_users" },
  { to: "/settings", label: "Settings", icon: Cog6ToothIcon, permission: "manage_settings" },
  { to: "/account", label: "My account", icon: UserCircleIcon },
];

/** Phone/tablet bottom tab bar: four everyday screens, the rest under "More". */
export const TAB_ITEMS: NavItem[] = [
  { to: "/", label: "Home", icon: HomeIcon },
  { to: "/risks", label: "Risks", icon: ShieldExclamationIcon },
  { to: "/actions", label: "Actions", icon: ClipboardDocumentCheckIcon },
  { to: "/approvals", label: "Approvals", icon: CheckBadgeIcon },
];

export const MORE_ICON = EllipsisHorizontalCircleIcon;

export function navFor(can: (p: string) => boolean): NavItem[] {
  return NAV.filter((item) => !item.permission || can(item.permission));
}
