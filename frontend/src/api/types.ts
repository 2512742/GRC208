/** Friendly aliases over the generated OpenAPI types (npm run gen:api regenerates schema.d.ts). */
import type { components } from "./schema";

type S = components["schemas"];

export type Me = S["Me"];
export type Role = S["Role"];
export type Band = S["Band"];
export type RiskStatus = S["RiskStatus"];
export type Strategy = S["Strategy"];
export type ScoreSummary = S["ScoreSummary"];
export type PersonRef = S["PersonRef"];
export type RiskSummary = S["RiskSummary"];
export type RiskDetail = S["RiskDetail"];
export type RiskCreate = S["RiskCreate"];
export type RiskUpdate = S["RiskUpdate"];
export type RiskPage = S["Page_RiskSummary_"];
export type AssessmentOut = S["AssessmentOut"];
export type AssetOut = S["AssetOut"];
export type AssetCreate = S["AssetCreate"];
export type AssetType = S["AssetType"];
export type Classification = S["Classification"];
export type ServiceOut = S["ServiceOut"];
export type ObligationOut = S["ObligationOut"];
export type ControlOut = S["ControlOut"];
export type DecisionOut = S["DecisionOut"];
export type ActionOut = S["ActionOut"];
export type ActionStatus = S["ActionStatus"];
export type AcceptanceOut = S["AcceptanceOut"];
export type EvidenceOut = S["EvidenceOut"];
export type EvidenceTarget = S["EvidenceTarget"];
export type ReassessmentOut = S["ReassessmentOut"];
export type Overview = S["Overview"];
export type HeatCell = S["HeatCell"];
export type OverdueAction = S["OverdueAction"];
export type AcceptanceLine = S["AcceptanceLine"];
export type ImportBatchOut = S["ImportBatchOut"];
export type ImportType = S["ImportType"];
export type AuditEntryOut = S["AuditEntryOut"];
export type AuditPage = S["AuditPage"];
export type AuditAction = S["AuditAction"];
export type ChainReportOut = S["ChainReportOut"];
export type SettingsOut = S["SettingsOut"];
export type SettingsUpdate = S["SettingsUpdate"];
export type UserSummary = S["UserSummary"];
export type UserDetail = S["UserDetail"];
export type UserCreate = S["UserCreate"];
export type UserUpdate = S["UserUpdate"];
export type TimezoneOption = S["TimezoneOption"];

/** The nested `risk` object on actions and acceptances. */
export interface RiskRef {
  id: number;
  risk_code: string;
  title: string;
  owner_id?: number;
}

export type Totals = {
  risks: number;
  assessed: number;
  above_appetite: number;
  open_actions: number;
  overdue_actions: number;
  pending_acceptances: number;
  expired_acceptances: number;
  awaiting_reassessment: number;
  reviews_due: number;
};

export type ServiceLine = {
  service_id: number;
  code: string;
  name: string;
  risks: number;
  above_appetite: number;
  highest_score: number | null;
};

export type ExposureLine = { regime: string; risks: number; above_appetite: number };

export type SecurityOverview = S["SecurityOverview"];
export type SessionOut = S["SessionOut"];
export type ActivityOut = S["ActivityOut"];
export type RecoveryCodeOut = S["RecoveryCodeOut"];
export type SignedOut = S["SignedOut"];
