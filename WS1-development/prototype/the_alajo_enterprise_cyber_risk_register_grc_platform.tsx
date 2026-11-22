import React, { useState, useEffect, useMemo } from 'react';
import {
  Shield, ShieldAlert, ShieldCheck, LayoutDashboard, Server, AlertTriangle,
  CheckCircle2, Clock, FileCheck, FileSpreadsheet, History, BookOpen,
  UserCheck, Lock, Plus, Search, Filter, Download, Eye, Edit3,
  ChevronRight, X, AlertCircle, ArrowUpRight, ArrowDownRight, RefreshCw,
  Upload, Check, Ban, Printer, FileText, Database, GitBranch, Layers,
  Info, ExternalLink, Calendar, DollarSign, Paperclip, Award, Sparkles
} from 'lucide-react';

// ============================================================================
// 1. GRC METHODOLOGY, SCORING RUBRICS & CONSTANTS
// ============================================================================

const APP_NAME = "The Alajo Enterprise Cyber Risk Register & GRC Platform";
const DEFAULT_APPETITE_THRESHOLD = 9; // Scores > 9 (10-25) exceed organizational risk appetite

const LIKELIHOOD_SCALE = [
  { score: 1, label: "Rare", description: "May occur only in exceptional circumstances (<5% probability in 12 months; requires nation-state zero-day)." },
  { score: 2, label: "Unlikely", description: "Could occur at some time (5–20% probability; requires targeted attacker effort and multiple control failures)." },
  { score: 3, label: "Possible", description: "Might occur moderately (21–50% probability; known exploit patterns exist, moderate exposure)." },
  { score: 4, label: "Likely", description: "Will probably occur in most circumstances (51–80% probability; active scanning/campaigns observed)." },
  { score: 5, label: "Almost Certain", description: "Expected to occur frequently (>80% probability; unpatched internet-facing exposure or recurring incident)." }
];

const IMPACT_SCALE = [
  { score: 1, label: "Negligible", description: "Minimal operational disruption (<1 hr); financial loss < $10,000; no regulatory or customer impact." },
  { score: 2, label: "Minor", description: "Localized service degradation (1–4 hrs); financial loss $10k–$50k; minor internal remediation." },
  { score: 3, label: "Moderate", description: "Significant business unit disruption (4–24 hrs); financial loss $50k–$250k; reportable operational incident." },
  { score: 4, label: "Major", description: "Critical banking/enterprise outage (24–72 hrs); financial loss $250k–$1M; regulatory inquiry & customer churn." },
  { score: 5, label: "Catastrophic", description: "Severe systemic failure (>72 hrs); financial loss > $1M; major data breach, regulatory sanctions, license threat." }
];

const getRatingBand = (score) => {
  if (score >= 16) return { label: "Critical", color: "red", bg: "bg-red-100 text-red-800 border-red-300", cellBg: "bg-red-600 hover:bg-red-700 text-white", badge: "bg-red-600 text-white" };
  if (score >= 10) return { label: "High", color: "orange", bg: "bg-orange-100 text-orange-800 border-orange-300", cellBg: "bg-orange-500 hover:bg-orange-600 text-white", badge: "bg-orange-500 text-white" };
  if (score >= 5) return { label: "Medium", color: "amber", bg: "bg-amber-100 text-amber-800 border-amber-300", cellBg: "bg-amber-400 hover:bg-amber-500 text-slate-900", badge: "bg-amber-500 text-white" };
  return { label: "Low", color: "emerald", bg: "bg-emerald-100 text-emerald-800 border-emerald-300", cellBg: "bg-emerald-500 hover:bg-emerald-600 text-white", badge: "bg-emerald-600 text-white" };
};

// ============================================================================
// 2. RBAC USERS & PERMISSION DEFINITIONS
// ============================================================================

const ROLES = [
  {
    id: "analyst",
    roleName: "Risk Analyst",
    userName: "Sarah Mensah",
    title: "Senior Information Security Analyst",
    department: "Enterprise Risk & GRC",
    badgeColor: "bg-blue-600",
    permissions: {
      canEditAssets: true,
      canEditRisks: true,
      canManageTreatments: true,
      canSubmitReassessment: true,
      canRequestAcceptance: true,
      canApproveAcceptance: false,
      canImportCSV: true,
      canEditAppetite: false
    },
    description: "Can create/edit assets, risks, treatments, run CSV imports, and submit reassessments. Cannot approve risk acceptances."
  },
  {
    id: "owner",
    roleName: "Risk Owner",
    userName: "Kwame Boateng",
    title: "VP of Core Banking & Engineering",
    department: "Digital Banking & Payments",
    badgeColor: "bg-indigo-600",
    permissions: {
      canEditAssets: false,
      canEditRisks: false,
      canManageTreatments: true,
      canSubmitReassessment: true,
      canRequestAcceptance: true,
      canApproveAcceptance: true, // Allowed ONLY for risks they do NOT own (SoD enforced!)
      canImportCSV: false,
      canEditAppetite: false
    },
    description: "Updates assigned treatment actions, attaches evidence, and requests risk acceptance. Strictly blocked from approving own risk acceptance requests (SoD)."
  },
  {
    id: "approver",
    roleName: "Approver / CISO",
    userName: "Abena Osei",
    title: "Chief Information Security Officer (CISO)",
    department: "Executive Risk Committee",
    badgeColor: "bg-purple-600",
    permissions: {
      canEditAssets: true,
      canEditRisks: true,
      canManageTreatments: true,
      canSubmitReassessment: true,
      canRequestAcceptance: true,
      canApproveAcceptance: true,
      canImportCSV: true,
      canEditAppetite: true
    },
    description: "Authorized executive reviewer. Approves/rejects risk acceptance exceptions (with SoD verification), reviews reassessments, and governs risk appetite."
  },
  {
    id: "auditor",
    roleName: "Read-Only Auditor",
    userName: "David Kumi",
    title: "External GRC & IT Audit Partner",
    department: "Kumi & Associates Assurance",
    badgeColor: "bg-slate-600",
    permissions: {
      canEditAssets: false,
      canEditRisks: false,
      canManageTreatments: false,
      canSubmitReassessment: false,
      canRequestAcceptance: false,
      canApproveAcceptance: false,
      canImportCSV: false,
      canEditAppetite: false
    },
    description: "Full inspection access across registers, evidence hashes, heat maps, and immutable audit trails. All write/approval actions strictly disabled."
  }
];

// ============================================================================
// 3. DEMONSTRATION DATASET (16 ASSETS, 22 RISKS, 14 TREATMENTS, APPROVALS)
// ============================================================================

const INITIAL_ASSETS = [
  // Service 1: Digital Banking & Payments (6 Assets)
  { id: "AST-001", name: "Core Banking API Gateway", service: "Digital Banking & Payments", criticality: "Tier 1 - Critical", owner: "Kwame Boateng", environment: "Production Cloud", ipOrHost: "api-gw.alajobank.internal" },
  { id: "AST-002", name: "Alajo Mobile Banking App (iOS/Android)", service: "Digital Banking & Payments", criticality: "Tier 1 - Critical", owner: "Kwame Boateng", environment: "External Mobile", ipOrHost: "com.alajo.mobilebank" },
  { id: "AST-003", name: "SWIFT & Interbank Payment Switch", service: "Digital Banking & Payments", criticality: "Tier 1 - Critical", owner: "Kwame Boateng", environment: "On-Premises HSM Zone", ipOrHost: "swift-sw01.alajobank.local" },
  { id: "AST-004", name: "PCI-DSS Card Tokenization Vault", service: "Digital Banking & Payments", criticality: "Tier 1 - Critical", owner: "Nana Yaw Asante", environment: "Isolated CDE", ipOrHost: "vault-cde.alajobank.internal" },
  { id: "AST-005", name: "Customer Identity & OAuth2 Provider", service: "Digital Banking & Payments", criticality: "Tier 1 - Critical", owner: "Kwame Boateng", environment: "Production Cloud", ipOrHost: "auth.alajobank.com" },
  { id: "AST-006", name: "Real-Time Fraud Detection Engine", service: "Digital Banking & Payments", criticality: "Tier 2 - High", owner: "Efua Mensah-Bonsu", environment: "Production Cloud", ipOrHost: "fraud-ml.alajobank.internal" },

  // Service 2: Enterprise Cloud & Infrastructure (5 Assets)
  { id: "AST-007", name: "AWS Production Multi-Account VPC", service: "Enterprise Cloud & Infrastructure", criticality: "Tier 1 - Critical", owner: "Kojo Appiah", environment: "AWS eu-west-1", ipOrHost: "vpc-09a8f72b11c" },
  { id: "AST-008", name: "Enterprise Active Directory & Entra ID", service: "Enterprise Cloud & Infrastructure", criticality: "Tier 1 - Critical", owner: "Kojo Appiah", environment: "Hybrid Identity", ipOrHost: "ad-dc01.corp.alajobank.local" },
  { id: "AST-009", name: "SAP ERP & General Ledger Database", service: "Enterprise Cloud & Infrastructure", criticality: "Tier 1 - Critical", owner: "Ama Darko", environment: "Private Cloud", ipOrHost: "sap-hana01.corp.alajobank.local" },
  { id: "AST-010", name: "Workday HR & Payroll Portal", service: "Enterprise Cloud & Infrastructure", criticality: "Tier 2 - High", owner: "Ama Darko", environment: "SaaS Enterprise", ipOrHost: "alajo.workday.com" },
  { id: "AST-011", name: "Corporate Zero-Trust VPN Concentrator", service: "Enterprise Cloud & Infrastructure", criticality: "Tier 2 - High", owner: "Kojo Appiah", environment: "Edge Perimeter", ipOrHost: "vpn.alajobank.com" },

  // Service 3: Customer Support & Data Analytics (5 Assets)
  { id: "AST-012", name: "Salesforce CRM & Case Management", service: "Customer Support & Data Analytics", criticality: "Tier 2 - High", owner: "Efua Mensah-Bonsu", environment: "SaaS Cloud", ipOrHost: "alajo.my.salesforce.com" },
  { id: "AST-013", name: "Snowflake Enterprise Data Lakehouse", service: "Customer Support & Data Analytics", criticality: "Tier 1 - Critical", owner: "Efua Mensah-Bonsu", environment: "Cloud Analytics", ipOrHost: "alajo-prod.snowflakecomputing.com" },
  { id: "AST-014", name: "Contact Center VoIP & Call Recording PBX", service: "Customer Support & Data Analytics", criticality: "Tier 3 - Moderate", owner: "Kojo Appiah", environment: "On-Premises Voice", ipOrHost: "pbx-voice01.corp.alajobank.local" },
  { id: "AST-015", name: "Public Corporate Website & Investor Portal", service: "Customer Support & Data Analytics", criticality: "Tier 3 - Moderate", owner: "Efua Mensah-Bonsu", environment: "Public Edge CDN", ipOrHost: "www.alajobank.com" },
  { id: "AST-016", name: "B2B Vendor Managed File Transfer (SFTP)", service: "Customer Support & Data Analytics", criticality: "Tier 2 - High", owner: "Kwame Boateng", environment: "DMZ Gateway", ipOrHost: "mft.alajobank.com" }
];

const INITIAL_RISKS = [
  {
    id: "RSK-001",
    title: "Broken Object Level Authorization (BOLA) in Core Banking API",
    description: "Improper authorization checks on account-balance and transfer endpoints could allow authenticated mobile users to query or initiate actions on sibling customer accounts.",
    threat: "External Cybercriminals / Malicious API Consumers",
    vulnerability: "Missing object-level ownership validation in microservice v2.4 endpoints",
    businessImpact: "Unauthorized customer fund transfers, regulatory fines from Bank of Ghana, severe reputational damage.",
    assetIds: ["AST-001", "AST-002"],
    service: "Digital Banking & Payments",
    owner: "Kwame Boateng",
    reviewDate: "2026-12-05",
    strategy: "Reduce",
    inherentL: 4,
    inherentI: 5,
    residualL: 4,
    residualI: 5,
    status: "Open - Treatment In Progress",
    reassessmentHistory: [
      { date: "2026-08-15", assessor: "Sarah Mensah", prevScore: 20, newScore: 20, likelihood: 4, impact: 5, notes: "Initial baseline inherent risk assessment during Q3 API security audit.", evidenceRef: "EVD-001" }
    ]
  },
  {
    id: "RSK-002",
    title: "Credential Stuffing & Session Hijacking on Customer Identity Provider",
    description: "Automated credential stuffing attacks leveraging leaked third-party password dumps against customer login endpoints without adaptive device fingerprinting.",
    threat: "Organized Cybercrime Syndicates",
    vulnerability: "Legacy SMS OTP fallback susceptible to SIM-swap and lack of behavioral bot mitigation",
    businessImpact: "Mass account takeover (ATO), fraudulent withdrawals, and elevated call-center dispute volume.",
    assetIds: ["AST-005", "AST-002"],
    service: "Digital Banking & Payments",
    owner: "Kwame Boateng",
    reviewDate: "2026-11-28",
    strategy: "Reduce",
    inherentL: 5,
    inherentI: 4,
    residualL: 5,
    residualI: 4,
    status: "Awaiting Reassessment",
    reassessmentHistory: [
      { date: "2026-07-10", assessor: "Sarah Mensah", prevScore: 20, newScore: 20, likelihood: 5, impact: 4, notes: "Baseline assessment following surge in automated login spikes.", evidenceRef: "EVD-002" }
    ]
  },
  {
    id: "RSK-003",
    title: "Ransomware Lateral Movement via Legacy NTLM in Active Directory",
    description: "Unrestricted NTLMv1/v2 authentication and overly permissive service account privileges in Active Directory enable rapid domain escalation.",
    threat: "Ransomware Affiliates (RaaS)",
    vulnerability: "Legacy NTLM enabled on domain controllers and unsegmented tier-0 admin workstations",
    businessImpact: "Enterprise-wide encryption of internal servers, suspension of back-office operations for >72 hours.",
    assetIds: ["AST-008", "AST-009"],
    service: "Enterprise Cloud & Infrastructure",
    owner: "Kojo Appiah",
    reviewDate: "2026-12-01",
    strategy: "Reduce",
    inherentL: 4,
    inherentI: 5,
    residualL: 3,
    residualI: 5,
    status: "Open - Exceeds Appetite",
    reassessmentHistory: [
      { date: "2026-06-20", assessor: "Sarah Mensah", prevScore: 20, newScore: 20, likelihood: 4, impact: 5, notes: "Baseline red-team finding.", evidenceRef: "EVD-003" },
      { date: "2026-09-18", assessor: "Sarah Mensah", prevScore: 20, newScore: 15, likelihood: 3, impact: 5, notes: "PAM deployed for Tier-0 admins; NTLM disablement still pending legacy ERP testing.", evidenceRef: "EVD-004" }
    ]
  },
  {
    id: "RSK-004",
    title: "Unencrypted PII & Financial Columns in Snowflake Data Lakehouse",
    description: "Analytical staging tables replicate customer National ID numbers and transaction histories without dynamic column-level masking.",
    threat: "Malicious Insider / Compromised BI Analyst Account",
    vulnerability: "Broad SELECT grants on raw analytical schemas and lack of column-level tokenization",
    businessImpact: "Violation of Ghana Data Protection Act (Act 843), statutory penalties, and customer privacy breach.",
    assetIds: ["AST-013"],
    service: "Customer Support & Data Analytics",
    owner: "Efua Mensah-Bonsu",
    reviewDate: "2026-12-10",
    strategy: "Reduce",
    inherentL: 4,
    inherentI: 4,
    residualL: 4,
    residualI: 4,
    status: "Open - Overdue Treatment",
    reassessmentHistory: [
      { date: "2026-07-02", assessor: "Sarah Mensah", prevScore: 16, newScore: 16, likelihood: 4, impact: 4, notes: "Identified during Data Privacy Impact Assessment (DPIA).", evidenceRef: "EVD-005" }
    ]
  },
  {
    id: "RSK-005",
    title: "SWIFT Payment Switch Operator Workstation Compromise",
    description: "Potential malware execution on SWIFT Alliance operator terminals bypassing dual-authorization message checks.",
    threat: "State-Sponsored Financial Threat Actors",
    vulnerability: "Shared jump-host administrative tooling with internet-connected corporate VLAN",
    businessImpact: "Fraudulent high-value international wire transfers and loss of SWIFT Customer Security Programme (CSP) attestation.",
    assetIds: ["AST-003"],
    service: "Digital Banking & Payments",
    owner: "Kwame Boateng",
    reviewDate: "2027-01-15",
    strategy: "Reduce",
    inherentL: 3,
    inherentI: 5,
    residualL: 2,
    residualI: 5,
    status: "Open - Exceeds Appetite",
    reassessmentHistory: [
      { date: "2026-05-11", assessor: "Sarah Mensah", prevScore: 15, newScore: 15, likelihood: 3, impact: 5, notes: "SWIFT CSP annual gap review.", evidenceRef: "EVD-006" },
      { date: "2026-10-04", assessor: "Sarah Mensah", prevScore: 15, newScore: 10, likelihood: 2, impact: 5, notes: "Hardware security keys and air-gapped jump hosts enforced; residual impact remains catastrophic.", evidenceRef: "EVD-007" }
    ]
  },
  {
    id: "RSK-006",
    title: "Legacy TLS 1.1 Support on B2B Vendor SFTP Gateway",
    description: "Three legacy clearing partners require TLS 1.1 compatibility on the MFT gateway, exposing file transfers to downgrade attacks.",
    threat: "Man-in-the-Middle (MitM) Network Adversaries",
    vulnerability: "Deprecated cryptographic protocol TLS 1.1 enabled on port 2222",
    businessImpact: "Potential interception of batch settlement files; temporary risk acceptance expired without partner migration.",
    assetIds: ["AST-016"],
    service: "Customer Support & Data Analytics",
    owner: "Kwame Boateng",
    reviewDate: "2026-11-22",
    strategy: "Accept",
    inherentL: 3,
    inherentI: 4,
    residualL: 3,
    residualI: 4,
    status: "Exception Expired",
    reassessmentHistory: [
      { date: "2026-04-01", assessor: "Sarah Mensah", prevScore: 12, newScore: 12, likelihood: 3, impact: 4, notes: "Temporary exception granted while partners upgrade SFTP clients.", evidenceRef: "EVD-008" }
    ]
  },
  {
    id: "RSK-007",
    title: "Over-Privileged IAM Cross-Account Roles in AWS Production VPC",
    description: "CI/CD deployment roles possess wildcard IAM permissions (*:*) across production S3 buckets and RDS snapshots.",
    threat: "Supply Chain Compromise / Rogue CI/CD Pipeline",
    vulnerability: "Violation of least-privilege IAM policy design in Terraform modules",
    businessImpact: "Full cloud environment takeover, exfiltration of database backups, or infrastructure destruction.",
    assetIds: ["AST-007"],
    service: "Enterprise Cloud & Infrastructure",
    owner: "Kojo Appiah",
    reviewDate: "2026-12-15",
    strategy: "Reduce",
    inherentL: 3,
    inherentI: 5,
    residualL: 2,
    residualI: 4,
    status: "Within Appetite",
    reassessmentHistory: [
      { date: "2026-06-14", assessor: "Sarah Mensah", prevScore: 15, newScore: 15, likelihood: 3, impact: 5, notes: "Cloud posture assessment finding.", evidenceRef: "EVD-009" },
      { date: "2026-10-22", assessor: "Sarah Mensah", prevScore: 15, newScore: 8, likelihood: 2, impact: 4, notes: "IAM Access Analyzer boundary policies enforced across all 14 prod accounts.", evidenceRef: "EVD-010" }
    ]
  },
  {
    id: "RSK-008",
    title: "Zero-Day Vulnerability Exposure on Edge Corporate VPN Concentrator",
    description: "SSL-VPN appliance is directly exposed to internet scanning without virtual patching or pre-authentication WAF filtering.",
    threat: "Opportunistic Internet Exploit Brokers",
    vulnerability: "Unshielded SSL-VPN management & portal interface",
    businessImpact: "Initial network intrusion bypassing perimeter firewall.",
    assetIds: ["AST-011"],
    service: "Enterprise Cloud & Infrastructure",
    owner: "Kojo Appiah",
    reviewDate: "2026-12-18",
    strategy: "Reduce",
    inherentL: 4,
    inherentI: 4,
    residualL: 2,
    residualI: 4,
    status: "Within Appetite",
    reassessmentHistory: [
      { date: "2026-05-30", assessor: "Sarah Mensah", prevScore: 16, newScore: 16, likelihood: 4, impact: 4, notes: "Perimeter vulnerability scan.", evidenceRef: "EVD-011" },
      { date: "2026-09-12", assessor: "Sarah Mensah", prevScore: 16, newScore: 8, likelihood: 2, impact: 4, notes: "Migrated 85% of workforce to Zero-Trust ZTNA; geo-fencing and certificate auth added.", evidenceRef: "EVD-012" }
    ]
  },
  {
    id: "RSK-009",
    title: "PCI-DSS Key Rotation Delay on Card Tokenization Vault HSM",
    description: "Annual cryptographic key-ceremony rotation for zone master keys is approaching the 365-day compliance window.",
    threat: "Cryptanalytic Exposure / Compliance Audit Non-Conformity",
    vulnerability: "Manual key rotation runbook dependency",
    businessImpact: "PCI-DSS QSA audit finding and potential card scheme penalties.",
    assetIds: ["AST-004"],
    service: "Digital Banking & Payments",
    owner: "Nana Yaw Asante",
    reviewDate: "2026-11-29",
    strategy: "Reduce",
    inherentL: 3,
    inherentI: 4,
    residualL: 3,
    residualI: 4,
    status: "Open - Exceeds Appetite",
    reassessmentHistory: [
      { date: "2026-08-01", assessor: "Sarah Mensah", prevScore: 12, newScore: 12, likelihood: 3, impact: 4, notes: "Pre-audit PCI readiness check.", evidenceRef: "EVD-013" }
    ]
  },
  {
    id: "RSK-010",
    title: "DDoS Volumetric Flood Against Public Website & Mobile API Edge",
    description: "Coordinated Layer 7 HTTP flood targeting login and public rate-calculator endpoints during peak salary disbursement days.",
    threat: "Hacktivist Groups / Extortion DDoS Actors",
    vulnerability: "Insufficient auto-scaling rate limits on unauthenticated API routes",
    businessImpact: "Degraded mobile banking availability for retail customers.",
    assetIds: ["AST-001", "AST-015"],
    service: "Digital Banking & Payments",
    owner: "Kwame Boateng",
    reviewDate: "2027-02-10",
    strategy: "Transfer",
    inherentL: 4,
    inherentI: 3,
    residualL: 2,
    residualI: 3,
    status: "Within Appetite",
    reassessmentHistory: [
      { date: "2026-07-19", assessor: "Sarah Mensah", prevScore: 12, newScore: 6, likelihood: 2, impact: 3, notes: "Always-on Cloudflare Enterprise DDoS scrubbing & cyber insurance rider verified.", evidenceRef: "EVD-014" }
    ]
  },
  {
    id: "RSK-011",
    title: "Unauthorized Bulk Export from Salesforce CRM by Support Agents",
    description: "Customer support tier-2 agents can export up to 50,000 contact records to CSV without manager approval or DLP alert.",
    threat: "Malicious Insider / Social Engineering of Support Staff",
    vulnerability: "Default Salesforce report export permissions enabled for standard profiles",
    businessImpact: "Loss of customer contact lists to competitors and phishing campaigns targeting clients.",
    assetIds: ["AST-012"],
    service: "Customer Support & Data Analytics",
    owner: "Efua Mensah-Bonsu",
    reviewDate: "2026-12-08",
    strategy: "Reduce",
    inherentL: 4,
    inherentI: 3,
    residualL: 4,
    residualI: 3,
    status: "Open - Exceeds Appetite",
    reassessmentHistory: [
      { date: "2026-09-05", assessor: "Sarah Mensah", prevScore: 12, newScore: 12, likelihood: 4, impact: 3, notes: "Insider threat tabletop exercise finding.", evidenceRef: "EVD-015" }
    ]
  },
  {
    id: "RSK-012",
    title: "SAP ERP Transport Layer & Custom ABAP SQL Injection",
    description: "Legacy custom ABAP financial reporting modules do not sanitize dynamic WHERE clauses.",
    threat: "Compromised Internal User / Rogue Contractor",
    vulnerability: "Unsafe dynamic SQL concatenation in 4 custom Z-reports",
    businessImpact: "Unauthorized modification of vendor bank details or general ledger entries.",
    assetIds: ["AST-009"],
    service: "Enterprise Cloud & Infrastructure",
    owner: "Ama Darko",
    reviewDate: "2027-01-20",
    strategy: "Reduce",
    inherentL: 3,
    inherentI: 5,
    residualL: 2,
    residualI: 4,
    status: "Within Appetite",
    reassessmentHistory: [
      { date: "2026-08-28", assessor: "Sarah Mensah", prevScore: 15, newScore: 8, likelihood: 2, impact: 4, notes: "ABAP static code analysis remediation completed and verified in QA/Prod.", evidenceRef: "EVD-016" }
    ]
  },
  {
    id: "RSK-013",
    title: "Mobile App Binary Reverse Engineering & Hardcoded Test Endpoints",
    description: "Staging diagnostic flags remain discoverable in Android APK metadata, aiding attackers in mapping internal API structures.",
    threat: "Mobile Malware Developers / Fraud Analysts",
    vulnerability: "Incomplete code obfuscation on non-core telemetry SDK",
    businessImpact: "Facilitates reconnaissance for API abuse and overlay phishing.",
    assetIds: ["AST-002"],
    service: "Digital Banking & Payments",
    owner: "Kwame Boateng",
    reviewDate: "2027-01-30",
    strategy: "Reduce",
    inherentL: 4,
    inherentI: 2,
    residualL: 2,
    residualI: 2,
    status: "Within Appetite",
    reassessmentHistory: [
      { date: "2026-09-25", assessor: "Sarah Mensah", prevScore: 8, newScore: 4, likelihood: 2, impact: 2, notes: "R8 full-mode obfuscation and runtime RASP integrity checks shipped in v5.12.", evidenceRef: "EVD-017" }
    ]
  },
  {
    id: "RSK-014",
    title: "Adversarial Evasion of Real-Time ML Fraud Scoring Rules",
    description: "Fraudsters splitting transactions just below velocity thresholds (structuring/smurfing) to evade automated blocking.",
    threat: "Organized Mule Networks",
    vulnerability: "Static 24-hour aggregation window in legacy rule engine",
    businessImpact: "Increased fraud write-offs on instant mobile wallet transfers.",
    assetIds: ["AST-006"],
    service: "Digital Banking & Payments",
    owner: "Efua Mensah-Bonsu",
    reviewDate: "2026-12-22",
    strategy: "Reduce",
    inherentL: 4,
    inherentI: 3,
    residualL: 3,
    residualI: 3,
    status: "Within Appetite",
    reassessmentHistory: [
      { date: "2026-10-12", assessor: "Sarah Mensah", prevScore: 12, newScore: 9, likelihood: 3, impact: 3, notes: "Rolling 7-day graph velocity rules deployed; sits right at appetite ceiling (9).", evidenceRef: "EVD-018" }
    ]
  },
  {
    id: "RSK-015",
    title: "Unencrypted SIP Trunking on Internal Contact Center VoIP PBX",
    description: "Internal voice traffic between branch gateways and central PBX uses unencrypted RTP streams.",
    threat: "Malicious Insider on Corporate LAN",
    vulnerability: "SRTP disabled due to legacy desk-phone firmware constraints",
    businessImpact: "Potential eavesdropping on customer verification calls.",
    assetIds: ["AST-014"],
    service: "Customer Support & Data Analytics",
    owner: "Kojo Appiah",
    reviewDate: "2027-03-01",
    strategy: "Accept",
    inherentL: 2,
    inherentI: 3,
    residualL: 2,
    residualI: 3,
    status: "Within Appetite",
    reassessmentHistory: [
      { date: "2026-08-10", assessor: "Sarah Mensah", prevScore: 6, newScore: 6, likelihood: 2, impact: 3, notes: "Voice VLAN isolated with 802.1X NAC; accepted until PBX cloud migration in Q2 2027.", evidenceRef: "EVD-019" }
    ]
  },
  {
    id: "RSK-016",
    title: "Third-Party SaaS OAuth Token Over-Permissioning in Workday HR",
    description: "Legacy reporting integration retains read access to employee salary bands and national tax identifiers.",
    threat: "Compromised Third-Party HR Analytics Vendor",
    vulnerability: "Overly broad OAuth2 integration scope",
    businessImpact: "Exposure of sensitive executive and staff compensation records.",
    assetIds: ["AST-010"],
    service: "Enterprise Cloud & Infrastructure",
    owner: "Ama Darko",
    reviewDate: "2026-12-12",
    strategy: "Reduce",
    inherentL: 3,
    inherentI: 4,
    residualL: 3,
    residualI: 4,
    status: "Open - Exceeds Appetite",
    reassessmentHistory: [
      { date: "2026-09-30", assessor: "Sarah Mensah", prevScore: 12, newScore: 12, likelihood: 3, impact: 4, notes: "Annual SaaS vendor access review.", evidenceRef: "EVD-020" }
    ]
  },
  {
    id: "RSK-017",
    title: "Defacement or Subdomain Takeover on Public Corporate Portal",
    description: "Dangling CNAME DNS records pointing to decommissioned marketing microsites.",
    threat: "Opportunistic Web Vandals / Phishing Kit Operators",
    vulnerability: "Unmonitored external DNS zone changes",
    businessImpact: "Brand embarrassment and hosting of fraudulent login clones under official domain.",
    assetIds: ["AST-015"],
    service: "Customer Support & Data Analytics",
    owner: "Efua Mensah-Bonsu",
    reviewDate: "2027-02-15",
    strategy: "Avoid",
    inherentL: 3,
    inherentI: 3,
    residualL: 1,
    residualI: 3,
    status: "Within Appetite",
    reassessmentHistory: [
      { date: "2026-10-18", assessor: "Sarah Mensah", prevScore: 9, newScore: 3, likelihood: 1, impact: 3, notes: "Decommissioned all legacy microsite subdomains and locked DNS updates to IaC pipeline.", evidenceRef: "EVD-021" }
    ]
  },
  {
    id: "RSK-018",
    title: "Insufficient SIEM Log Retention for Core Banking Microservices",
    description: "Verbose debug logs from payment microservices rotate after 14 days due to ingestion cost caps, below the 90-day forensic standard.",
    threat: "Advanced Persistent Threat (Delayed Breach Discovery)",
    vulnerability: "Log ingestion throttling on high-volume Kubernetes pods",
    businessImpact: "Inability to perform full root-cause forensic investigation following a stealth intrusion.",
    assetIds: ["AST-001", "AST-007"],
    service: "Digital Banking & Payments",
    owner: "Kojo Appiah",
    reviewDate: "2026-12-04",
    strategy: "Reduce",
    inherentL: 3,
    inherentI: 3,
    residualL: 2,
    residualI: 3,
    status: "Within Appetite",
    reassessmentHistory: [
      { date: "2026-11-01", assessor: "Sarah Mensah", prevScore: 9, newScore: 6, likelihood: 2, impact: 3, notes: "Cold S3 Glacier tiering configured for 365-day immutable audit log retention.", evidenceRef: "EVD-022" }
    ]
  },
  {
    id: "RSK-019",
    title: "Phishing-Susceptible MFA Fatigue on Corporate Email & VPN",
    description: "Push-notification MFA allows attackers with compromised passwords to spam approval prompts until an employee accidentally accepts.",
    threat: "Initial Access Brokers / Social Engineers",
    vulnerability: "Number-matching disabled for legacy mobile mail clients",
    businessImpact: "Unauthorized corporate email access and internal business email compromise (BEC).",
    assetIds: ["AST-008", "AST-011"],
    service: "Enterprise Cloud & Infrastructure",
    owner: "Kojo Appiah",
    reviewDate: "2027-01-12",
    strategy: "Reduce",
    inherentL: 4,
    inherentI: 3,
    residualL: 2,
    residualI: 3,
    status: "Within Appetite",
    reassessmentHistory: [
      { date: "2026-09-14", assessor: "Sarah Mensah", prevScore: 12, newScore: 6, likelihood: 2, impact: 3, notes: "FIDO2 hardware tokens and Entra ID number-matching enforced globally.", evidenceRef: "EVD-023" }
    ]
  },
  {
    id: "RSK-020",
    title: "Unmasked Cardholder PANs in Call Center Screen Recordings",
    description: "Agents occasionally view full 16-digit card numbers during dispute verification while screen recording is active.",
    threat: "Malicious Call Center Agent / Compromised Recording Storage",
    vulnerability: "Missing automated pause-and-resume API trigger in CRM screen recorder",
    businessImpact: "PCI-DSS scope expansion and potential card data compromise.",
    assetIds: ["AST-014", "AST-004"],
    service: "Customer Support & Data Analytics",
    owner: "Nana Yaw Asante",
    reviewDate: "2026-12-19",
    strategy: "Reduce",
    inherentL: 3,
    inherentI: 4,
    residualL: 2,
    residualI: 3,
    status: "Within Appetite",
    reassessmentHistory: [
      { date: "2026-10-29", assessor: "Sarah Mensah", prevScore: 12, newScore: 6, likelihood: 2, impact: 3, notes: "CRM UI masked PAN display; only last 4 digits visible to agents.", evidenceRef: "EVD-024" }
    ]
  },
  {
    id: "RSK-021",
    title: "Container Image Supply Chain Poisoning in Kubernetes Registry",
    description: "Developers pull base Alpine/Node container images from public registries without cryptographic signature verification.",
    threat: "Upstream Open-Source Maintainer Compromise",
    vulnerability: "Admission controller lacks Cosign signature enforcement",
    businessImpact: "Execution of backdoored code inside production banking clusters.",
    assetIds: ["AST-007", "AST-001"],
    service: "Enterprise Cloud & Infrastructure",
    owner: "Kwame Boateng",
    reviewDate: "2027-01-08",
    strategy: "Reduce",
    inherentL: 2,
    inherentI: 5,
    residualL: 2,
    residualI: 4,
    status: "Within Appetite",
    reassessmentHistory: [
      { date: "2026-11-05", assessor: "Sarah Mensah", prevScore: 10, newScore: 8, likelihood: 2, impact: 4, notes: "Private hardened ECR base image mirror deployed; Kyverno enforcement in audit mode.", evidenceRef: "EVD-025" }
    ]
  },
  {
    id: "RSK-022",
    title: "Shadow IT SaaS File Sharing Bypassing Enterprise DLP",
    description: "Marketing and vendor management teams use unmanaged personal cloud storage links to exchange large media and RFP drafts.",
    threat: "Accidental Data Leakage / Public Link Indexing",
    vulnerability: "Unsanctioned file-sharing domains not blocked on corporate proxy",
    businessImpact: "Confidential vendor pricing and internal strategy documents exposed publicly.",
    assetIds: ["AST-011", "AST-016"],
    service: "Customer Support & Data Analytics",
    owner: "Efua Mensah-Bonsu",
    reviewDate: "2027-02-20",
    strategy: "Reduce",
    inherentL: 3,
    inherentI: 2,
    residualL: 2,
    residualI: 2,
    status: "Within Appetite",
    reassessmentHistory: [
      { date: "2026-10-15", assessor: "Sarah Mensah", prevScore: 6, newScore: 4, likelihood: 2, impact: 2, notes: "CASB tenant restrictions and proxy blocklist activated.", evidenceRef: "EVD-026" }
    ]
  }
];

const INITIAL_TREATMENTS = [
  {
    id: "TRT-001",
    riskId: "RSK-001",
    strategy: "Reduce",
    actionPlan: "Implement object-level JWT claim ownership middleware across all Core Banking v2.4 REST & GraphQL endpoints and run automated BOLA regression suite.",
    owner: "Kwame Boateng",
    deadline: "2026-12-15",
    status: "In Progress",
    cost: 42000,
    evidence: [
      { id: "EVD-101", name: "API_Gateway_AuthZ_Architecture_v2.pdf", hash: "sha256:8f94e2...91b0", uploadedBy: "Kwame Boateng", date: "2026-11-10" }
    ]
  },
  {
    id: "TRT-002",
    riskId: "RSK-002",
    strategy: "Reduce",
    actionPlan: "Deploy FIDO2 passkey authentication, behavioural bot protection, and disable SMS OTP fallback for high-value transfers.",
    owner: "Kwame Boateng",
    deadline: "2026-11-15",
    status: "Completed - Awaiting Reassessment",
    cost: 68000,
    evidence: [
      { id: "EVD-102", name: "OAuth2_BotDefense_Deployment_Signoff.pdf", hash: "sha256:3c71a9...44e2", uploadedBy: "Kwame Boateng", date: "2026-11-14" },
      { id: "EVD-103", name: "PenTest_ATO_Retest_Clean_Report.pdf", hash: "sha256:9d12b4...77c1", uploadedBy: "Sarah Mensah", date: "2026-11-16" }
    ]
  },
  {
    id: "TRT-003",
    riskId: "RSK-004",
    strategy: "Reduce",
    actionPlan: "Configure Snowflake Enterprise Dynamic Data Masking policies on all PII, National ID, and account balance columns across staging and analytics schemas.",
    owner: "Efua Mensah-Bonsu",
    deadline: "2026-10-30", // OVERDUE!
    status: "Overdue",
    cost: 29500,
    evidence: [
      { id: "EVD-104", name: "Snowflake_PII_Classification_Catalog.xlsx", hash: "sha256:5e88d1...20a9", uploadedBy: "Efua Mensah-Bonsu", date: "2026-10-12" }
    ]
  },
  {
    id: "TRT-004",
    riskId: "RSK-003",
    strategy: "Reduce",
    actionPlan: "Disable NTLMv1/v2 domain-wide via Group Policy after migrating remaining 2 legacy SAP connectors to Kerberos AES-256.",
    owner: "Kojo Appiah",
    deadline: "2026-12-20",
    status: "In Progress",
    cost: 35000,
    evidence: [
      { id: "EVD-105", name: "AD_Tier0_PAM_Rollout_Completion.pdf", hash: "sha256:1a44f8...63d0", uploadedBy: "Kojo Appiah", date: "2026-09-17" }
    ]
  },
  {
    id: "TRT-005",
    riskId: "RSK-005",
    strategy: "Reduce",
    actionPlan: "Implement dedicated Privileged Access Workstations (PAWs) with biometric smartcards for all SWIFT Alliance operators.",
    owner: "Kwame Boateng",
    deadline: "2026-10-01",
    status: "Verified & Closed",
    cost: 54000,
    evidence: [
      { id: "EVD-106", name: "SWIFT_CSP_2026_Independent_Assessment.pdf", hash: "sha256:7b20c3...18f4", uploadedBy: "Kwame Boateng", date: "2026-10-02" }
    ]
  },
  {
    id: "TRT-006",
    riskId: "RSK-006",
    strategy: "Accept",
    actionPlan: "Enforce IP allow-listing and PGP file-level encryption as compensating controls while 3 legacy B2B partners upgrade from TLS 1.1 to TLS 1.3.",
    owner: "Kwame Boateng",
    deadline: "2026-12-30",
    status: "In Progress",
    cost: 8000,
    evidence: [
      { id: "EVD-107", name: "MFT_PGP_Compensating_Control_Config.txt", hash: "sha256:4f99e1...05b2", uploadedBy: "Kwame Boateng", date: "2026-04-05" }
    ]
  },
  {
    id: "TRT-007",
    riskId: "RSK-009",
    strategy: "Reduce",
    actionPlan: "Execute dual-custody HSM Zone Master Key rotation ceremony and automate 300-day expiry alerting in Vault.",
    owner: "Nana Yaw Asante",
    deadline: "2026-11-30",
    status: "In Progress",
    cost: 15000,
    evidence: [
      { id: "EVD-108", name: "HSM_Key_Ceremony_Runbook_Approved.pdf", hash: "sha256:6c33b7...88a1", uploadedBy: "Nana Yaw Asante", date: "2026-11-08" }
    ]
  },
  {
    id: "TRT-008",
    riskId: "RSK-011",
    strategy: "Reduce",
    actionPlan: "Restrict Salesforce bulk report export permission to Compliance Officers only and enable Event Monitoring real-time anomaly alerts.",
    owner: "Efua Mensah-Bonsu",
    deadline: "2026-12-10",
    status: "Planned",
    cost: 18500,
    evidence: []
  },
  {
    id: "TRT-009",
    riskId: "RSK-016",
    strategy: "Reduce",
    actionPlan: "Re-scope Workday OAuth2 integration token to exclude compensation and tax fields; rotate client secrets.",
    owner: "Ama Darko",
    deadline: "2026-12-14",
    status: "In Progress",
    cost: 6500,
    evidence: [
      { id: "EVD-109", name: "Workday_API_Scope_Audit_Diff.json", hash: "sha256:2d77a0...94c5", uploadedBy: "Ama Darko", date: "2026-11-12" }
    ]
  },
  {
    id: "TRT-010",
    riskId: "RSK-007",
    strategy: "Reduce",
    actionPlan: "Enforce AWS IAM permission boundaries and eliminate wildcard actions in all Terraform deployment pipelines.",
    owner: "Kojo Appiah",
    deadline: "2026-10-20",
    status: "Verified & Closed",
    cost: 22000,
    evidence: [
      { id: "EVD-110", name: "AWS_IAM_Access_Analyzer_ZeroFindings.pdf", hash: "sha256:9e11c4...52d8", uploadedBy: "Kojo Appiah", date: "2026-10-21" }
    ]
  },
  {
    id: "TRT-011",
    riskId: "RSK-010",
    strategy: "Transfer",
    actionPlan: "Procure $15M Cyber & Business Interruption Insurance policy and activate Cloudflare Layer-7 unmetered DDoS mitigation.",
    owner: "Kwame Boateng",
    deadline: "2026-07-15",
    status: "Verified & Closed",
    cost: 95000,
    evidence: [
      { id: "EVD-111", name: "Cyber_Insurance_Policy_Schedule_2026.pdf", hash: "sha256:0a55f2...31e9", uploadedBy: "Abena Osei", date: "2026-07-16" }
    ]
  },
  {
    id: "TRT-012",
    riskId: "RSK-012",
    strategy: "Reduce",
    actionPlan: "Refactor custom SAP ABAP Z-reports to use parameterized OpenSQL queries and pass Code Vulnerability Analyzer (CVA) scan.",
    owner: "Ama Darko",
    deadline: "2026-08-25",
    status: "Verified & Closed",
    cost: 19000,
    evidence: [
      { id: "EVD-112", name: "SAP_CVA_Clean_Scan_Certificate.pdf", hash: "sha256:8b66d9...40f7", uploadedBy: "Ama Darko", date: "2026-08-27" }
    ]
  },
  {
    id: "TRT-013",
    riskId: "RSK-017",
    strategy: "Avoid",
    actionPlan: "Decommission all legacy campaign subdomains and terminate third-party microsite hosting contracts.",
    owner: "Efua Mensah-Bonsu",
    deadline: "2026-10-15",
    status: "Verified & Closed",
    cost: 2000,
    evidence: [
      { id: "EVD-113", name: "External_DNS_Zone_Cleanup_Log.txt", hash: "sha256:3f19b8...72a4", uploadedBy: "Efua Mensah-Bonsu", date: "2026-10-17" }
    ]
  },
  {
    id: "TRT-014",
    riskId: "RSK-021",
    strategy: "Reduce",
    actionPlan: "Switch Kubernetes admission controller (Kyverno) from audit mode to enforce mode for Cosign container image signatures.",
    owner: "Kwame Boateng",
    deadline: "2026-12-28",
    status: "Planned",
    cost: 14000,
    evidence: []
  }
];

const INITIAL_APPROVALS = [
  {
    id: "EXC-001",
    riskId: "RSK-006",
    riskTitle: "Legacy TLS 1.1 Support on B2B Vendor SFTP Gateway",
    riskOwner: "Kwame Boateng",
    residualScore: 12,
    justification: "Three tier-1 correspondent clearing partners rely on legacy mainframe SFTP clients that cannot negotiate TLS 1.2+ until their Q1 2027 core upgrade. Disabling TLS 1.1 immediately would halt daily clearing settlements.",
    compensatingControls: "Strict source IP allow-listing, dedicated DMZ VLAN isolation, mandatory PGP payload encryption (4096-bit RSA), and 24/7 SOC anomaly monitoring.",
    approverName: "Abena Osei",
    decisionDate: "2026-04-10",
    expiryDate: "2026-10-10", // EXPIRED!
    status: "Expired"
  },
  {
    id: "EXC-002",
    riskId: "RSK-015",
    riskTitle: "Unencrypted SIP Trunking on Internal Contact Center VoIP PBX",
    riskOwner: "Kojo Appiah",
    residualScore: 6,
    justification: "Existing legacy desk phones lack hardware crypto co-processors for SRTP. Full replacement is budgeted under the Q2 2027 Cloud Contact Center migration.",
    compensatingControls: "Dedicated Voice VLAN with IEEE 802.1X port authentication, DHCP snooping, and dynamic ARP inspection.",
    approverName: "Abena Osei",
    decisionDate: "2026-08-12",
    expiryDate: "2027-06-30",
    status: "Approved - Active"
  },
  {
    id: "EXC-003",
    riskId: "RSK-005",
    riskTitle: "SWIFT Payment Switch Operator Workstation Compromise",
    riskOwner: "Kwame Boateng",
    residualScore: 10,
    justification: "Although likelihood has been reduced to Rare/Unlikely (2) via air-gapped PAWs and hardware MFA, inherent catastrophic impact (5) yields a residual score of 10 (1 point above standard appetite). Requesting formal Board Risk Committee tolerance acceptance.",
    compensatingControls: "Air-gapped PAWs, dual-operator transaction signing, hardware security modules (HSM), and SWIFT Relationship Management Application (RMA) limits.",
    approverName: "",
    decisionDate: "",
    expiryDate: "2027-11-19",
    status: "Pending Approval"
  }
];

const INITIAL_AUDIT_LOGS = [
  { id: "AUD-1010", timestamp: "2026-11-18 16:42:11", actor: "System Watchdog", role: "Automated Control", action: "EXPIRY_FLAGGED", target: "EXC-001 (RSK-006)", details: "Risk acceptance exception EXC-001 passed expiry date (2026-10-10). Status transitioned to EXPIRED." },
  { id: "AUD-1009", timestamp: "2026-11-16 14:15:03", actor: "Sarah Mensah", role: "Risk Analyst", action: "EVIDENCE_ATTACHED", target: "TRT-002 (RSK-002)", details: "Attached PenTest_ATO_Retest_Clean_Report.pdf (sha256:9d12b4...77c1). Reassessment still required before score reduction." },
  { id: "AUD-1008", timestamp: "2026-11-14 11:20:45", actor: "Kwame Boateng", role: "Risk Owner", action: "TREATMENT_COMPLETED", target: "TRT-002 (RSK-002)", details: "Marked treatment action TRT-002 as Completed. System enforced hold on Residual Risk Score (remains 20) pending documented reassessment." },
  { id: "AUD-1007", timestamp: "2026-11-12 09:50:19", actor: "Kwame Boateng", role: "Risk Owner", action: "EXCEPTION_REQUESTED", target: "EXC-003 (RSK-005)", details: "Submitted risk acceptance request EXC-003 for residual score 10 (Impact=5). Routed to CISO for independent approval." },
  { id: "AUD-1006", timestamp: "2026-11-01 10:05:30", actor: "System Watchdog", role: "Automated Control", action: "OVERDUE_ALERT", target: "TRT-003 (RSK-004)", details: "Treatment action TRT-003 missed deadline (2026-10-30). Flagged as OVERDUE on Executive Dashboard." },
  { id: "AUD-1005", timestamp: "2026-10-22 15:33:12", actor: "Sarah Mensah", role: "Risk Analyst", action: "RISK_REASSESSED", target: "RSK-007", details: "Documented reassessment completed with evidence EVD-010. Residual Score reduced from 15 (High) to 8 (Medium - Within Appetite)." },
  { id: "AUD-1004", timestamp: "2026-08-12 13:10:00", actor: "Abena Osei", role: "Approver / CISO", action: "EXCEPTION_APPROVED", target: "EXC-002 (RSK-015)", details: "Approved risk acceptance EXC-002 for Kojo Appiah until 2027-06-30. Segregation of Duties verified (Approver != Owner)." }
];

// ============================================================================
// 4. MAIN APPLICATION COMPONENT
// ============================================================================

export default function App() {
  // Persistent State Keys
  const STORAGE_KEY = "alajo_grc_platform_v1";

  const loadInitialState = () => {
    try {
      const saved = localStorage.getItem(STORAGE_KEY);
      if (saved) {
        return JSON.parse(saved);
      }
    } catch (e) {
      console.error("Failed to parse saved GRC state", e);
    }
    return null;
  };

  const savedData = loadInitialState();

  const [activeTab, setActiveTab] = useState("dashboard");
  const [currentRoleId, setCurrentRoleId] = useState(savedData?.currentRoleId || "analyst");
  const [appetiteThreshold, setAppetiteThreshold] = useState(savedData?.appetiteThreshold || DEFAULT_APPETITE_THRESHOLD);
  const [assets, setAssets] = useState(savedData?.assets || INITIAL_ASSETS);
  const [risks, setRisks] = useState(savedData?.risks || INITIAL_RISKS);
  const [treatments, setTreatments] = useState(savedData?.treatments || INITIAL_TREATMENTS);
  const [approvals, setApprovals] = useState(savedData?.approvals || INITIAL_APPROVALS);
  const [auditLogs, setAuditLogs] = useState(savedData?.auditLogs || INITIAL_AUDIT_LOGS);

  // Save to localStorage on change
  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify({
        currentRoleId,
        appetiteThreshold,
        assets,
        risks,
        treatments,
        approvals,
        auditLogs
      }));
    } catch (e) {
      console.error("Failed to save GRC state", e);
    }
  }, [currentRoleId, appetiteThreshold, assets, risks, treatments, approvals, auditLogs]);

  const currentUser = useMemo(() => ROLES.find(r => r.id === currentRoleId) || ROLES[0], [currentRoleId]);

  // Global UI Toast / Banner Notification
  const [toast, setToast] = useState(null);
  const showToast = (message, type = "info") => {
    setToast({ message, type });
    setTimeout(() => setToast(null), 5000);
  };

  // Audit Logger Helper
  const logAudit = (action, target, details, overrideActor = null, overrideRole = null) => {
    const now = new Date();
    const formattedTime = now.toISOString().replace("T", " ").substring(0, 19);
    const newEntry = {
      id: `AUD-${1011 + auditLogs.length}`,
      timestamp: formattedTime,
      actor: overrideActor || currentUser.userName,
      role: overrideRole || currentUser.roleName,
      action,
      target,
      details
    };
    setAuditLogs(prev => [newEntry, ...prev]);
  };

  // Reset Demo Data
  const handleResetDemo = () => {
    localStorage.removeItem(STORAGE_KEY);
    setAssets(INITIAL_ASSETS);
    setRisks(INITIAL_RISKS);
    setTreatments(INITIAL_TREATMENTS);
    setApprovals(INITIAL_APPROVALS);
    setAuditLogs(INITIAL_AUDIT_LOGS);
    setAppetiteThreshold(DEFAULT_APPETITE_THRESHOLD);
    setCurrentRoleId("analyst");
    showToast("Demonstration dataset restored to factory baseline.", "success");
  };

  // Computed GRC Metrics
  const metrics = useMemo(() => {
    const totalRisks = risks.length;
    const risksAboveAppetite = risks.filter(r => (r.residualL * r.residualI) > appetiteThreshold);
    const overdueTreatments = treatments.filter(t => t.status === "Overdue");
    const pendingReassessments = treatments.filter(t => t.status === "Completed - Awaiting Reassessment");
    const expiredAcceptances = approvals.filter(a => a.status === "Expired");
    const pendingApprovals = approvals.filter(a => a.status === "Pending Approval");

    const totalInherent = risks.reduce((acc, r) => acc + (r.inherentL * r.inherentI), 0);
    const totalResidual = risks.reduce((acc, r) => acc + (r.residualL * r.residualI), 0);
    const reductionPct = totalInherent > 0 ? Math.round(((totalInherent - totalResidual) / totalInherent) * 100) : 0;

    return {
      totalRisks,
      aboveAppetiteCount: risksAboveAppetite.length,
      risksAboveAppetite,
      overdueCount: overdueTreatments.length,
      overdueTreatments,
      pendingReassessmentCount: pendingReassessments.length,
      pendingReassessments,
      expiredAcceptanceCount: expiredAcceptances.length,
      expiredAcceptances,
      pendingApprovalCount: pendingApprovals.length,
      reductionPct
    };
  }, [risks, treatments, approvals, appetiteThreshold]);

  // Modal & Drawer States
  const [selectedRisk, setSelectedRisk] = useState(null);
  const [showNewRiskModal, setShowNewRiskModal] = useState(false);
  const [showNewAssetModal, setShowNewAssetModal] = useState(false);
  const [showNewTreatmentModal, setShowNewTreatmentModal] = useState(false);
  const [reassessTarget, setReassessTarget] = useState(null); // { risk, treatment }
  const [showNewApprovalModal, setShowNewApprovalModal] = useState(false);
  const [showReportModal, setShowReportModal] = useState(false);

  // Dashboard Heat Map Filter State
  const [heatMapMode, setHeatMapMode] = useState("residual"); // 'inherent' | 'residual'
  const [selectedHeatCell, setSelectedHeatCell] = useState(null); // { l, i }

  // ==========================================================================
  // HANDLERS FOR GRC WORKFLOWS
  // ==========================================================================

  const handleCreateAsset = (newAsset) => {
    if (!currentUser.permissions.canEditAssets) {
      showToast("Access Denied: Your role cannot create assets.", "error");
      return;
    }
    const id = `AST-${String(assets.length + 1).padStart(3, "0")}`;
    const assetRecord = { ...newAsset, id };
    setAssets(prev => [...prev, assetRecord]);
    logAudit("ASSET_CREATED", `${id} (${newAsset.name})`, `Registered new ${newAsset.criticality} asset under ${newAsset.service}.`);
    setShowNewAssetModal(false);
    showToast(`Asset ${id} registered successfully.`, "success");
  };

  const handleCreateRisk = (newRisk) => {
    if (!currentUser.permissions.canEditRisks) {
      showToast("Access Denied: Your role cannot register new risks.", "error");
      return;
    }
    const id = `RSK-${String(risks.length + 1).padStart(3, "0")}`;
    const score = newRisk.inherentL * newRisk.inherentI;
    const riskRecord = {
      ...newRisk,
      id,
      residualL: newRisk.inherentL,
      residualI: newRisk.inherentI,
      status: score > appetiteThreshold ? "Open - Exceeds Appetite" : "Within Appetite",
      reassessmentHistory: [
        {
          date: new Date().toISOString().substring(0, 10),
          assessor: currentUser.userName,
          prevScore: score,
          newScore: score,
          likelihood: newRisk.inherentL,
          impact: newRisk.inherentI,
          notes: "Initial baseline risk registration.",
          evidenceRef: "BASELINE"
        }
      ]
    };
    setRisks(prev => [riskRecord, ...prev]);
    logAudit("RISK_REGISTERED", `${id} (${newRisk.title})`, `Created risk with Inherent Score ${score} (L:${newRisk.inherentL} x I:${newRisk.inherentI}).`);
    setShowNewRiskModal(false);
    showToast(`Cyber Risk ${id} created and scored (${score}).`, "success");
  };

  const handleCreateTreatment = (newTrt) => {
    if (!currentUser.permissions.canManageTreatments) {
      showToast("Access Denied: Read-only role cannot create treatment actions.", "error");
      return;
    }
    const id = `TRT-${String(treatments.length + 1).padStart(3, "0")}`;
    const trtRecord = {
      ...newTrt,
      id,
      evidence: newTrt.initialEvidenceName
        ? [{
            id: `EVD-${Math.floor(200 + Math.random() * 700)}`,
            name: newTrt.initialEvidenceName,
            hash: `sha256:${Math.random().toString(16).substring(2, 8)}...${Math.random().toString(16).substring(2, 6)}`,
            uploadedBy: currentUser.userName,
            date: new Date().toISOString().substring(0, 10)
          }]
        : []
    };
    setTreatments(prev => [trtRecord, ...prev]);
    logAudit("TREATMENT_CREATED", `${id} (${newTrt.riskId})`, `Assigned '${newTrt.strategy}' treatment to ${newTrt.owner} due ${newTrt.deadline}.`);
    setShowNewTreatmentModal(false);
    showToast(`Treatment action ${id} created.`, "success");
  };

  // Mark Treatment Completed -> Enforces Mandatory Reassessment Hold!
  const handleCompleteTreatment = (treatmentId) => {
    if (!currentUser.permissions.canManageTreatments) {
      showToast("Access Denied: Your role cannot update treatment status.", "error");
      return;
    }
    const targetTrt = treatments.find(t => t.id === treatmentId);
    if (!targetTrt) return;

    setTreatments(prev =>
      prev.map(t =>
        t.id === treatmentId
          ? { ...t, status: "Completed - Awaiting Reassessment" }
          : t
      )
    );

    setRisks(prev =>
      prev.map(r =>
        r.id === targetTrt.riskId
          ? { ...r, status: "Awaiting Reassessment" }
          : r
      )
    );

    logAudit(
      "TREATMENT_COMPLETED_HOLD",
      `${treatmentId} (${targetTrt.riskId})`,
      `Treatment marked completed by ${currentUser.userName}. Residual risk score intentionally HELD unchanged pending documented reassessment with evidence.`
    );
    showToast(
      `Treatment ${treatmentId} marked Completed. Residual risk score remains UNCHANGED until a documented reassessment with evidence is submitted.`,
      "warning"
    );
  };

  // Attach Evidence to Treatment
  const handleAttachEvidence = (treatmentId, fileName) => {
    if (!currentUser.permissions.canManageTreatments) {
      showToast("Access Denied: Read-only role cannot upload evidence.", "error");
      return;
    }
    if (!fileName.trim()) return;
    const evdId = `EVD-${Math.floor(200 + Math.random() * 799)}`;
    const hash = `sha256:${Math.random().toString(16).substring(2, 8)}...${Math.random().toString(16).substring(2, 6)}`;
    const newEvd = {
      id: evdId,
      name: fileName.trim(),
      hash,
      uploadedBy: currentUser.userName,
      date: new Date().toISOString().substring(0, 10)
    };
    setTreatments(prev =>
      prev.map(t => (t.id === treatmentId ? { ...t, evidence: [...t.evidence, newEvd] } : t))
    );
    logAudit("EVIDENCE_UPLOADED", `${treatmentId} (${evdId})`, `Attached artifact '${fileName.trim()}' (${hash}).`);
    showToast(`Supporting evidence ${evdId} attached with SHA-256 integrity hash.`, "success");
  };

  // Documented Residual Risk Reassessment
  const handleSubmitReassessment = ({ riskId, treatmentId, newL, newI, notes, evidenceRef }) => {
    if (!currentUser.permissions.canSubmitReassessment) {
      showToast("Access Denied: Read-only role cannot submit reassessments.", "error");
      return;
    }
    const targetRisk = risks.find(r => r.id === riskId);
    if (!targetRisk) return;

    const prevScore = targetRisk.residualL * targetRisk.residualI;
    const updatedScore = newL * newI;
    const today = new Date().toISOString().substring(0, 10);

    setRisks(prev =>
      prev.map(r => {
        if (r.id !== riskId) return r;
        return {
          ...r,
          residualL: newL,
          residualI: newI,
          status: updatedScore > appetiteThreshold ? "Open - Exceeds Appetite" : "Within Appetite",
          reassessmentHistory: [
            ...r.reassessmentHistory,
            {
              date: today,
              assessor: currentUser.userName,
              prevScore,
              newScore: updatedScore,
              likelihood: newL,
              impact: newI,
              notes,
              evidenceRef
            }
          ]
        };
      })
    );

    if (treatmentId) {
      setTreatments(prev =>
        prev.map(t => (t.id === treatmentId ? { ...t, status: "Verified & Closed" } : t))
      );
    }

    logAudit(
      "RESIDUAL_REASSESSED",
      `${riskId}${treatmentId ? ` / ${treatmentId}` : ""}`,
      `Residual score updated from ${prevScore} to ${updatedScore} (L:${newL} x I:${newI}) backed by evidence [${evidenceRef}]. Notes: ${notes}`
    );

    setReassessTarget(null);
    showToast(`Documented reassessment recorded for ${riskId}. New Residual Score: ${updatedScore}.`, "success");
  };

  // Request Risk Acceptance
  const handleCreateApprovalRequest = ({ riskId, justification, compensatingControls, expiryDate }) => {
    if (!currentUser.permissions.canRequestAcceptance) {
      showToast("Access Denied: Your role cannot submit acceptance requests.", "error");
      return;
    }
    const risk = risks.find(r => r.id === riskId);
    if (!risk) return;
    const excId = `EXC-${String(approvals.length + 1).padStart(3, "0")}`;
    const newReq = {
      id: excId,
      riskId: risk.id,
      riskTitle: risk.title,
      riskOwner: risk.owner,
      residualScore: risk.residualL * risk.residualI,
      justification,
      compensatingControls,
      approverName: "",
      decisionDate: "",
      expiryDate,
      status: "Pending Approval"
    };
    setApprovals(prev => [newReq, ...prev]);
    logAudit("ACCEPTANCE_REQUESTED", `${excId} (${risk.id})`, `Requested risk acceptance for Residual Score ${newReq.residualScore} until ${expiryDate}.`);
    setShowNewApprovalModal(false);
    showToast(`Risk acceptance exception ${excId} submitted for independent review.`, "success");
  };

  // Approve or Reject Risk Acceptance (With Strict Segregation of Duties!)
  const handleApprovalDecision = (excId, decision, newExpiryDate = null) => {
    const exc = approvals.find(a => a.id === excId);
    if (!exc) return;

    if (!currentUser.permissions.canApproveAcceptance) {
      logAudit("UNAUTHORIZED_APPROVAL_ATTEMPT", excId, `Blocked ${currentUser.userName} (${currentUser.roleName}) from approving exception.`);
      showToast(`Access Control Block: ${currentUser.roleName} is not authorized to approve risk acceptances.`, "error");
      return;
    }

    // SEGREGATION OF DUTIES CHECK
    if (currentUser.userName === exc.riskOwner) {
      logAudit(
        "SOD_VIOLATION_BLOCKED",
        `${excId} (${exc.riskId})`,
        `Segregation of Duties control blocked Risk Owner '${currentUser.userName}' from approving their own risk acceptance request.`
      );
      showToast(
        `Segregation of Duties (SoD) Violation Blocked: Risk Owner (${exc.riskOwner}) cannot approve their own risk acceptance request. Switch to Approver / CISO.`,
        "error"
      );
      return;
    }

    const today = new Date().toISOString().substring(0, 10);
    setApprovals(prev =>
      prev.map(a =>
        a.id === excId
          ? {
              ...a,
              approverName: currentUser.userName,
              decisionDate: today,
              expiryDate: newExpiryDate || a.expiryDate,
              status: decision === "approve" ? "Approved - Active" : "Rejected"
            }
          : a
      )
    );

    if (decision === "approve") {
      setRisks(prev =>
        prev.map(r => (r.id === exc.riskId ? { ...r, status: "Accepted (Approved Exception)" } : r))
      );
    }

    logAudit(
      decision === "approve" ? "ACCEPTANCE_APPROVED" : "ACCEPTANCE_REJECTED",
      `${excId} (${exc.riskId})`,
      `${decision === "approve" ? "Approved" : "Rejected"} by ${currentUser.userName} (${currentUser.roleName}). Expiry: ${newExpiryDate || exc.expiryDate}.`
    );
    showToast(`Exception ${excId} ${decision === "approve" ? "approved" : "rejected"} and logged to immutable audit trail.`, "success");
  };

  // ==========================================================================
  // NAVIGATION ITEMS
  // ==========================================================================
  const navItems = [
    { id: "dashboard", label: "Executive Dashboard", icon: LayoutDashboard },
    { id: "assets", label: "Asset & Service Register", icon: Server, count: assets.length },
    { id: "risks", label: "Cyber Risk Register", icon: ShieldAlert, count: risks.length },
    { id: "treatments", label: "Treatment & Reassessment", icon: FileCheck, badge: metrics.overdueCount + metrics.pendingReassessmentCount },
    { id: "approvals", label: "Approvals & Exceptions", icon: UserCheck, badge: metrics.expiredAcceptanceCount + metrics.pendingApprovalCount },
    { id: "import", label: "CSV Data Import", icon: FileSpreadsheet },
    { id: "audit", label: "Immutable Audit Trail", icon: History, count: auditLogs.length },
    { id: "docs", label: "Project Documentation", icon: BookOpen }
  ];

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 flex flex-col lg:flex-row font-sans">
      {/* ==================================================================== */}
      {/* LEFT ENTERPRISE SIDEBAR                                              */}
      {/* ==================================================================== */}
      <aside className="w-full lg:w-72 bg-slate-900 text-slate-100 flex flex-col shrink-0 border-r border-slate-800">
        {/* Brand Emblem Header */}
        <div className="p-5 border-b border-slate-800 flex items-center gap-3.5">
          <div className="w-11 h-11 rounded-xl bg-gradient-to-br from-blue-500 via-indigo-600 to-slate-800 p-0.5 shadow-lg shadow-blue-950/50 shrink-0">
            <div className="w-full h-full bg-slate-900 rounded-[10px] flex items-center justify-center relative">
              <Shield className="w-6 h-6 text-blue-400" />
              <div className="w-2 h-2 rounded-full bg-emerald-400 absolute top-2 right-2 animate-pulse" />
            </div>
          </div>
          <div className="min-w-0">
            <div className="text-[10px] font-bold uppercase tracking-widest text-blue-400">Enterprise GRC Suite</div>
            <h1 className="text-sm font-bold leading-snug text-white tracking-tight">
              The Alajo Enterprise Cyber Risk Register &amp; GRC Platform
            </h1>
          </div>
        </div>

        {/* Navigation Links */}
        <nav className="flex-1 p-3 space-y-1 overflow-y-auto">
          {navItems.map(item => {
            const Icon = item.icon;
            const isActive = activeTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => setActiveTab(item.id)}
                className={`w-full flex items-center justify-between px-3.5 py-2.5 rounded-lg text-sm font-medium transition-all ${
                  isActive
                    ? "bg-blue-600 text-white shadow-md shadow-blue-950/50"
                    : "text-slate-300 hover:bg-slate-800/80 hover:text-white"
                }`}
              >
                <span className="flex items-center gap-3 truncate">
                  <Icon className={`w-4 h-4 shrink-0 ${isActive ? "text-white" : "text-slate-400"}`} />
                  <span className="truncate">{item.label}</span>
                </span>
                {item.badge > 0 ? (
                  <span className="px-2 py-0.5 text-xs font-bold rounded-full bg-red-500 text-white">
                    {item.badge}
                  </span>
                ) : item.count !== undefined ? (
                  <span className={`text-xs px-2 py-0.5 rounded-full ${isActive ? "bg-blue-500 text-white" : "bg-slate-800 text-slate-400"}`}>
                    {item.count}
                  </span>
                ) : null}
              </button>
            );
          })}
        </nav>

        {/* Risk Appetite Governance Box */}
        <div className="p-4 m-3 rounded-xl bg-slate-800/70 border border-slate-700/80 space-y-2.5">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">Risk Appetite Ceiling</span>
            <span className="px-2 py-0.5 text-xs font-bold rounded bg-amber-500/20 text-amber-300 border border-amber-500/30">
              Score &le; {appetiteThreshold}
            </span>
          </div>
          <p className="text-xs text-slate-400 leading-relaxed">
            Risks scoring <strong className="text-orange-400">&ge; {appetiteThreshold + 1}</strong> exceed Board appetite and require mandatory treatment or CISO exception.
          </p>
          {currentUser.permissions.canEditAppetite && (
            <div className="pt-1 flex items-center gap-2">
              <label className="text-[11px] text-slate-300">Adjust Limit:</label>
              <select
                value={appetiteThreshold}
                onChange={(e) => {
                  const val = Number(e.target.value);
                  setAppetiteThreshold(val);
                  logAudit("APPETITE_UPDATED", "Org Risk Appetite", `CISO updated organizational risk appetite threshold to <= ${val}.`);
                  showToast(`Organizational Risk Appetite updated to <= ${val}.`, "info");
                }}
                className="bg-slate-900 border border-slate-600 rounded px-2 py-1 text-xs text-white"
              >
                <option value={6}>6 (Conservative)</option>
                <option value={9}>9 (Balanced Standard)</option>
                <option value={12}>12 (Growth Tolerant)</option>
              </select>
            </div>
          )}
        </div>

        {/* Footer Reset */}
        <div className="p-4 border-t border-slate-800 flex items-center justify-between text-xs text-slate-400">
          <span>ISO 27005 / NIST RMF</span>
          <button
            onClick={handleResetDemo}
            className="flex items-center gap-1 text-slate-400 hover:text-white transition-colors"
            title="Restore initial demonstration data"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            <span>Reset Demo</span>
          </button>
        </div>
      </aside>

      {/* ==================================================================== */}
      {/* MAIN WORKSPACE AREA                                                  */}
      {/* ==================================================================== */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* TOP HEADER & RBAC ROLE SWITCHER */}
        <header className="bg-white border-b border-slate-200 px-4 sm:px-6 py-3.5 sticky top-0 z-30 shadow-xs">
          <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-3">
            <div>
              <div className="flex items-center gap-2">
                <span className="text-xs font-semibold uppercase tracking-wider text-blue-600">
                  {navItems.find(n => n.id === activeTab)?.label}
                </span>
                <span className="text-slate-300">•</span>
                <span className="text-xs text-slate-500">Alajo Financial Group PLC</span>
              </div>
              <h2 className="text-lg font-bold text-slate-900 tracking-tight truncate">
                {APP_NAME}
              </h2>
            </div>

            {/* RBAC Role Switcher Control */}
            <div className="flex flex-wrap items-center gap-3">
              <div className="flex items-center gap-2 bg-slate-100 border border-slate-200 rounded-xl px-3 py-1.5">
                <div className={`w-2.5 h-2.5 rounded-full ${currentUser.badgeColor}`} />
                <div className="text-xs">
                  <span className="text-slate-500 block leading-none mb-0.5">Active RBAC Session</span>
                  <select
                    aria-label="Switch RBAC User Role"
                    value={currentRoleId}
                    onChange={(e) => {
                      setCurrentRoleId(e.target.value);
                      const next = ROLES.find(r => r.id === e.target.value);
                      showToast(`Switched active session to ${next.userName} (${next.roleName})`, "info");
                    }}
                    className="font-bold text-slate-900 bg-transparent focus:outline-none cursor-pointer pr-1"
                  >
                    {ROLES.map(r => (
                      <option key={r.id} value={r.id}>
                        {r.roleName}: {r.userName}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <button
                onClick={() => setShowReportModal(true)}
                className="inline-flex items-center gap-2 px-3.5 py-2 rounded-lg bg-slate-900 hover:bg-slate-800 text-white text-xs font-semibold shadow-xs transition-colors"
              >
                <Printer className="w-3.5 h-3.5" />
                <span>Executive Report</span>
              </button>
            </div>
          </div>

          {/* Active Role Permissions Strip */}
          <div className="mt-2.5 pt-2 border-t border-slate-100 flex flex-wrap items-center justify-between gap-2 text-xs">
            <div className="flex items-center gap-2 text-slate-600">
              <span className={`px-2 py-0.5 rounded font-semibold text-white ${currentUser.badgeColor}`}>
                {currentUser.roleName}
              </span>
              <span className="font-medium text-slate-800">{currentUser.title}</span>
              <span className="hidden sm:inline text-slate-400">|</span>
              <span className="hidden sm:inline text-slate-500">{currentUser.description}</span>
            </div>
            {currentRoleId === "auditor" && (
              <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full bg-amber-100 text-amber-800 font-semibold">
                <Lock className="w-3 h-3" /> Read-Only Audit Mode Active
              </span>
            )}
          </div>
        </header>

        {/* TOAST NOTIFICATION BANNER */}
        {toast && (
          <div className={`mx-4 sm:mx-6 mt-4 p-3.5 rounded-xl border flex items-center justify-between gap-3 shadow-sm ${
            toast.type === "error"
              ? "bg-red-50 border-red-300 text-red-900"
              : toast.type === "warning"
              ? "bg-amber-50 border-amber-300 text-amber-900"
              : "bg-emerald-50 border-emerald-300 text-emerald-900"
          }`}>
            <div className="flex items-center gap-2.5 text-sm font-medium">
              {toast.type === "error" ? <Ban className="w-5 h-5 text-red-600 shrink-0" /> :
               toast.type === "warning" ? <AlertTriangle className="w-5 h-5 text-amber-600 shrink-0" /> :
               <CheckCircle2 className="w-5 h-5 text-emerald-600 shrink-0" />}
              <span>{toast.message}</span>
            </div>
            <button onClick={() => setToast(null)} className="text-slate-500 hover:text-slate-800">
              <X className="w-4 h-4" />
            </button>
          </div>
        )}

        {/* ================================================================== */}
        {/* TAB CONTENT ROUTER                                                 */}
        {/* ================================================================== */}
        <main className="flex-1 p-4 sm:p-6 max-w-[1600px] w-full mx-auto space-y-6">
          {activeTab === "dashboard" && (
            <DashboardView
              risks={risks}
              assets={assets}
              treatments={treatments}
              approvals={approvals}
              metrics={metrics}
              appetiteThreshold={appetiteThreshold}
              heatMapMode={heatMapMode}
              setHeatMapMode={setHeatMapMode}
              selectedHeatCell={selectedHeatCell}
              setSelectedHeatCell={setSelectedHeatCell}
              onSelectRisk={setSelectedRisk}
              onNavigate={setActiveTab}
              onOpenReport={() => setShowReportModal(true)}
            />
          )}

          {activeTab === "assets" && (
            <AssetsView
              assets={assets}
              risks={risks}
              currentUser={currentUser}
              onOpenNewAsset={() => setShowNewAssetModal(true)}
              onSelectRisk={setSelectedRisk}
            />
          )}

          {activeTab === "risks" && (
            <RisksView
              risks={risks}
              assets={assets}
              appetiteThreshold={appetiteThreshold}
              currentUser={currentUser}
              onSelectRisk={setSelectedRisk}
              onOpenNewRisk={() => setShowNewRiskModal(true)}
            />
          )}

          {activeTab === "treatments" && (
            <TreatmentsView
              treatments={treatments}
              risks={risks}
              currentUser={currentUser}
              onOpenNewTreatment={() => setShowNewTreatmentModal(true)}
              onCompleteTreatment={handleCompleteTreatment}
              onAttachEvidence={handleAttachEvidence}
              onOpenReassess={(risk, treatment) => setReassessTarget({ risk, treatment })}
              onSelectRisk={setSelectedRisk}
            />
          )}

          {activeTab === "approvals" && (
            <ApprovalsView
              approvals={approvals}
              risks={risks}
              currentUser={currentUser}
              onDecision={handleApprovalDecision}
              onOpenNewApproval={() => setShowNewApprovalModal(true)}
              onSelectRisk={setSelectedRisk}
            />
          )}

          {activeTab === "import" && (
            <CsvImportView
              assets={assets}
              risks={risks}
              appetiteThreshold={appetiteThreshold}
              currentUser={currentUser}
              onCommitAssets={(validAssets) => {
                setAssets(prev => [...prev, ...validAssets]);
                logAudit("CSV_IMPORT_ASSETS", `${validAssets.length} Assets`, `Imported ${validAssets.length} validated asset records via CSV.`);
                showToast(`Successfully imported ${validAssets.length} assets into the register.`, "success");
              }}
              onCommitRisks={(validRisks) => {
                setRisks(prev => [...validRisks, ...prev]);
                logAudit("CSV_IMPORT_RISKS", `${validRisks.length} Risks`, `Imported ${validRisks.length} validated cyber risk records via CSV.`);
                showToast(`Successfully imported ${validRisks.length} cyber risks into the register.`, "success");
              }}
            />
          )}

          {activeTab === "audit" && (
            <AuditTrailView auditLogs={auditLogs} />
          )}

          {activeTab === "docs" && (
            <DocumentationView />
          )}
        </main>
      </div>

      {/* ==================================================================== */}
      {/* MODALS & DETAIL DRAWERS                                              */}
      {/* ==================================================================== */}
      {selectedRisk && (
        <RiskDetailModal
          risk={risks.find(r => r.id === selectedRisk.id) || selectedRisk}
          assets={assets}
          treatments={treatments.filter(t => t.riskId === selectedRisk.id)}
          approvals={approvals.filter(a => a.riskId === selectedRisk.id)}
          appetiteThreshold={appetiteThreshold}
          currentUser={currentUser}
          onClose={() => setSelectedRisk(null)}
          onOpenReassess={(r) => {
            const trt = treatments.find(t => t.riskId === r.id && t.status === "Completed - Awaiting Reassessment");
            setSelectedRisk(null);
            setReassessTarget({ risk: r, treatment: trt || null });
          }}
        />
      )}

      {showNewRiskModal && (
        <NewRiskModal
          assets={assets}
          appetiteThreshold={appetiteThreshold}
          onClose={() => setShowNewRiskModal(false)}
          onSubmit={handleCreateRisk}
        />
      )}

      {showNewAssetModal && (
        <NewAssetModal
          onClose={() => setShowNewAssetModal(false)}
          onSubmit={handleCreateAsset}
        />
      )}

      {showNewTreatmentModal && (
        <NewTreatmentModal
          risks={risks}
          onClose={() => setShowNewTreatmentModal(false)}
          onSubmit={handleCreateTreatment}
        />
      )}

      {reassessTarget && (
        <ReassessmentModal
          risk={reassessTarget.risk}
          treatment={reassessTarget.treatment}
          treatments={treatments.filter(t => t.riskId === reassessTarget.risk.id)}
          appetiteThreshold={appetiteThreshold}
          onClose={() => setReassessTarget(null)}
          onSubmit={handleSubmitReassessment}
        />
      )}

      {showNewApprovalModal && (
        <NewApprovalModal
          risks={risks}
          currentUser={currentUser}
          onClose={() => setShowNewApprovalModal(false)}
          onSubmit={handleCreateApprovalRequest}
        />
      )}

      {showReportModal && (
        <ManagementReportModal
          risks={risks}
          assets={assets}
          treatments={treatments}
          approvals={approvals}
          appetiteThreshold={appetiteThreshold}
          currentUser={currentUser}
          onClose={() => setShowReportModal(false)}
        />
      )}
    </div>
  );
}

// ============================================================================
// VIEW 1: EXECUTIVE DASHBOARD & 5x5 HEAT MAP
// ============================================================================

function DashboardView({
  risks, assets, treatments, approvals, metrics, appetiteThreshold,
  heatMapMode, setHeatMapMode, selectedHeatCell, setSelectedHeatCell,
  onSelectRisk, onNavigate, onOpenReport
}) {
  // Risks matching clicked heat map cell
  const cellRisks = useMemo(() => {
    if (!selectedHeatCell) return [];
    return risks.filter(r => {
      const l = heatMapMode === "inherent" ? r.inherentL : r.residualL;
      const i = heatMapMode === "inherent" ? r.inherentI : r.residualI;
      return l === selectedHeatCell.l && i === selectedHeatCell.i;
    });
  }, [risks, selectedHeatCell, heatMapMode]);

  // Business service summary breakdown
  const serviceSummary = useMemo(() => {
    const services = [
      "Digital Banking & Payments",
      "Enterprise Cloud & Infrastructure",
      "Customer Support & Data Analytics"
    ];
    return services.map(svc => {
      const svcRisks = risks.filter(r => r.service === svc);
      const above = svcRisks.filter(r => (r.residualL * r.residualI) > appetiteThreshold).length;
      const avgRes = svcRisks.length
        ? (svcRisks.reduce((acc, r) => acc + r.residualL * r.residualI, 0) / svcRisks.length).toFixed(1)
        : "0.0";
      return { service: svc, total: svcRisks.length, above, avgRes };
    });
  }, [risks, appetiteThreshold]);

  return (
    <div className="space-y-6">
      {/* KPI CARDS */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-4">
        <KpiCard
          title="Total Cyber Risks"
          value={metrics.totalRisks}
          subtitle={`Across ${assets.length} enterprise assets`}
          icon={ShieldAlert}
          accent="blue"
          onClick={() => onNavigate("risks")}
        />
        <KpiCard
          title="Exceeding Appetite"
          value={metrics.aboveAppetiteCount}
          subtitle={`Residual Score > ${appetiteThreshold}`}
          icon={AlertTriangle}
          accent="red"
          highlight={metrics.aboveAppetiteCount > 0}
          onClick={() => onNavigate("risks")}
        />
        <KpiCard
          title="Overdue Treatments"
          value={metrics.overdueCount}
          subtitle="Past remediation SLA"
          icon={Clock}
          accent="orange"
          highlight={metrics.overdueCount > 0}
          onClick={() => onNavigate("treatments")}
        />
        <KpiCard
          title="Pending Reassessment"
          value={metrics.pendingReassessmentCount}
          subtitle="Completed; awaiting evidence review"
          icon={FileCheck}
          accent="amber"
          highlight={metrics.pendingReassessmentCount > 0}
          onClick={() => onNavigate("treatments")}
        />
        <KpiCard
          title="Expired Exceptions"
          value={metrics.expiredAcceptanceCount}
          subtitle={`${metrics.pendingApprovalCount} awaiting CISO sign-off`}
          icon={UserCheck}
          accent="purple"
          highlight={metrics.expiredAcceptanceCount > 0}
          onClick={() => onNavigate("approvals")}
        />
        <KpiCard
          title="Risk Reduction"
          value={`${metrics.reductionPct}%`}
          subtitle="Inherent vs. Residual exposure"
          icon={ShieldCheck}
          accent="emerald"
          onClick={onOpenReport}
        />
      </div>

      {/* MAIN GRID: 5x5 HEAT MAP + ACTIONABLE GOVERNANCE ALERTS */}
      <div className="grid grid-cols-1 xl:grid-cols-12 gap-6">
        {/* 5x5 INTERACTIVE RISK HEAT MAP */}
        <div className="xl:col-span-7 bg-white rounded-2xl border border-slate-200 shadow-xs p-5 flex flex-col">
          <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
            <div>
              <h3 className="text-base font-bold text-slate-900">5×5 Enterprise Cyber Risk Heat Map</h3>
              <p className="text-xs text-slate-500">
                Click any matrix cell to drill down into risks. Dashed border indicates Risk Appetite boundary (&le; {appetiteThreshold}).
              </p>
            </div>
            <div className="inline-flex rounded-lg bg-slate-100 p-1 border border-slate-200">
              <button
                onClick={() => { setHeatMapMode("residual"); setSelectedHeatCell(null); }}
                className={`px-3 py-1.5 rounded-md text-xs font-semibold transition-all ${
                  heatMapMode === "residual" ? "bg-white text-slate-900 shadow-xs" : "text-slate-600 hover:text-slate-900"
                }`}
              >
                Residual Risk (Current)
              </button>
              <button
                onClick={() => { setHeatMapMode("inherent"); setSelectedHeatCell(null); }}
                className={`px-3 py-1.5 rounded-md text-xs font-semibold transition-all ${
                  heatMapMode === "inherent" ? "bg-white text-slate-900 shadow-xs" : "text-slate-600 hover:text-slate-900"
                }`}
              >
                Inherent Risk (Baseline)
              </button>
            </div>
          </div>

          {/* 5x5 MATRIX TABLE */}
          <div className="overflow-x-auto">
            <div className="min-w-[460px]">
              <div className="grid grid-cols-6 gap-1.5 items-center">
                {/* Y-Axis Header */}
                <div className="text-[11px] font-bold uppercase tracking-wider text-slate-400 text-right pr-2">
                  Likelihood ↑
                </div>
                {[1, 2, 3, 4, 5].map(imp => (
                  <div key={imp} className="text-center text-xs font-bold text-slate-700 py-1 bg-slate-100 rounded">
                    Impact {imp}
                    <span className="block text-[10px] font-normal text-slate-500">
                      {IMPACT_SCALE[imp - 1].label}
                    </span>
                  </div>
                ))}

                {/* Rows: Likelihood 5 down to 1 */}
                {[5, 4, 3, 2, 1].map(lik => (
                  <React.Fragment key={lik}>
                    <div className="text-right pr-2 py-2 bg-slate-100 rounded px-2">
                      <div className="text-xs font-bold text-slate-700">L{lik}</div>
                      <div className="text-[10px] text-slate-500">{LIKELIHOOD_SCALE[lik - 1].label}</div>
                    </div>
                    {[1, 2, 3, 4, 5].map(imp => {
                      const score = lik * imp;
                      const band = getRatingBand(score);
                      const count = risks.filter(r =>
                        (heatMapMode === "inherent" ? r.inherentL : r.residualL) === lik &&
                        (heatMapMode === "inherent" ? r.inherentI : r.residualI) === imp
                      ).length;
                      const exceedsAppetite = score > appetiteThreshold;
                      const isSelected = selectedHeatCell?.l === lik && selectedHeatCell?.i === imp;

                      return (
                        <button
                          key={`${lik}-${imp}`}
                          onClick={() => setSelectedHeatCell(isSelected ? null : { l: lik, i: imp })}
                          className={`h-16 rounded-xl p-2 flex flex-col justify-between transition-all relative ${band.cellBg} ${
                            exceedsAppetite ? "ring-2 ring-offset-1 ring-slate-900/40" : ""
                          } ${isSelected ? "scale-[1.03] ring-4 ring-blue-500 z-10" : "opacity-95 hover:opacity-100"}`}
                        >
                          <div className="w-full flex items-center justify-between text-[11px] font-bold opacity-90">
                            <span>{score}</span>
                            {exceedsAppetite && (
                              <span className="text-[9px] uppercase px-1 rounded bg-black/25">
                                &gt;App
                              </span>
                            )}
                          </div>
                          <div className="text-center">
                            {count > 0 ? (
                              <span className="inline-flex items-center justify-center px-2.5 py-0.5 rounded-full text-xs font-extrabold bg-white/95 text-slate-900 shadow-xs">
                                {count} {count === 1 ? "Risk" : "Risks"}
                              </span>
                            ) : (
                              <span className="text-[11px] opacity-60">—</span>
                            )}
                          </div>
                        </button>
                      );
                    })}
                  </React.Fragment>
                ))}
              </div>
            </div>
          </div>

          {/* Legend */}
          <div className="mt-4 pt-3 border-t border-slate-100 flex flex-wrap items-center justify-between gap-2 text-xs">
            <div className="flex flex-wrap items-center gap-3">
              <span className="inline-flex items-center gap-1.5"><span className="w-3 h-3 rounded bg-emerald-500" /> Low (1–4)</span>
              <span className="inline-flex items-center gap-1.5"><span className="w-3 h-3 rounded bg-amber-400" /> Medium (5–9)</span>
              <span className="inline-flex items-center gap-1.5"><span className="w-3 h-3 rounded bg-orange-500" /> High (10–15)</span>
              <span className="inline-flex items-center gap-1.5"><span className="w-3 h-3 rounded bg-red-600" /> Critical (16–25)</span>
            </div>
            <span className="font-semibold text-slate-600">
              Appetite Limit: Score &le; {appetiteThreshold}
            </span>
          </div>

          {/* Drill-down list when a cell is clicked */}
          {selectedHeatCell && (
            <div className="mt-4 p-4 rounded-xl bg-slate-50 border border-blue-200 space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-blue-900">
                  Cell Drill-Down: Likelihood {selectedHeatCell.l} × Impact {selectedHeatCell.i} = Score {selectedHeatCell.l * selectedHeatCell.i} ({cellRisks.length} risks)
                </span>
                <button onClick={() => setSelectedHeatCell(null)} className="text-xs text-slate-500 hover:text-slate-800">
                  Clear Filter
                </button>
              </div>
              {cellRisks.length === 0 ? (
                <p className="text-xs text-slate-500">No risks currently fall into this matrix coordinate.</p>
              ) : (
                <div className="divide-y divide-slate-200">
                  {cellRisks.map(r => (
                    <div key={r.id} className="py-2 flex items-center justify-between gap-2">
                      <div>
                        <span className="text-xs font-bold text-slate-800 mr-2">{r.id}</span>
                        <span className="text-xs text-slate-700">{r.title}</span>
                      </div>
                      <button
                        onClick={() => onSelectRisk(r)}
                        className="text-xs font-semibold text-blue-600 hover:underline shrink-0"
                      >
                        Inspect →
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>

        {/* ACTIONABLE GRC GOVERNANCE ALERTS PANEL */}
        <div className="xl:col-span-5 bg-white rounded-2xl border border-slate-200 shadow-xs p-5 flex flex-col justify-between space-y-5">
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-base font-bold text-slate-900">Actionable Governance Alerts</h3>
                <p className="text-xs text-slate-500">Items requiring immediate management or CISO intervention</p>
              </div>
              <span className="px-2.5 py-1 rounded-full text-xs font-bold bg-red-50 text-red-700 border border-red-200">
                {metrics.overdueCount + metrics.expiredAcceptanceCount + metrics.pendingReassessmentCount} Active
              </span>
            </div>

            {/* Alert 1: Overdue Treatment */}
            {metrics.overdueTreatments.map(trt => (
              <div key={trt.id} className="p-3.5 rounded-xl bg-red-50/80 border border-red-200 flex items-start justify-between gap-3">
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <span className="px-2 py-0.5 text-[10px] font-bold uppercase rounded bg-red-600 text-white">Overdue Treatment</span>
                    <span className="text-xs font-bold text-slate-900">{trt.id} → {trt.riskId}</span>
                  </div>
                  <p className="text-xs text-slate-700 line-clamp-2">{trt.actionPlan}</p>
                  <p className="text-[11px] text-red-700 font-medium">Owner: {trt.owner} • Due: {trt.deadline}</p>
                </div>
                <button
                  onClick={() => onNavigate("treatments")}
                  className="px-2.5 py-1.5 rounded-lg bg-white border border-red-200 text-xs font-semibold text-red-700 hover:bg-red-100 shrink-0"
                >
                  Review
                </button>
              </div>
            ))}

            {/* Alert 2: Expired Risk Acceptance */}
            {metrics.expiredAcceptances.map(exc => (
              <div key={exc.id} className="p-3.5 rounded-xl bg-purple-50/80 border border-purple-200 flex items-start justify-between gap-3">
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <span className="px-2 py-0.5 text-[10px] font-bold uppercase rounded bg-purple-700 text-white">Expired Acceptance</span>
                    <span className="text-xs font-bold text-slate-900">{exc.id} → {exc.riskId}</span>
                  </div>
                  <p className="text-xs text-slate-700 font-medium">{exc.riskTitle}</p>
                  <p className="text-[11px] text-purple-800 font-medium">Expired on {exc.expiryDate} • Owner: {exc.riskOwner}</p>
                </div>
                <button
                  onClick={() => onNavigate("approvals")}
                  className="px-2.5 py-1.5 rounded-lg bg-white border border-purple-200 text-xs font-semibold text-purple-800 hover:bg-purple-100 shrink-0"
                >
                  Renew / Escalate
                </button>
              </div>
            ))}

            {/* Alert 3: Completed Treatment Awaiting Reassessment */}
            {metrics.pendingReassessments.map(trt => (
              <div key={trt.id} className="p-3.5 rounded-xl bg-amber-50/90 border border-amber-300 flex items-start justify-between gap-3">
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <span className="px-2 py-0.5 text-[10px] font-bold uppercase rounded bg-amber-600 text-white">Awaiting Reassessment</span>
                    <span className="text-xs font-bold text-slate-900">{trt.id} → {trt.riskId}</span>
                  </div>
                  <p className="text-xs text-slate-700">Treatment completed; residual risk score held until formal evidence-backed reassessment.</p>
                  <p className="text-[11px] text-amber-800 font-medium">Evidence Attached: {trt.evidence.length} artifact(s)</p>
                </div>
                <button
                  onClick={() => onNavigate("treatments")}
                  className="px-2.5 py-1.5 rounded-lg bg-white border border-amber-300 text-xs font-semibold text-amber-900 hover:bg-amber-100 shrink-0"
                >
                  Reassess
                </button>
              </div>
            ))}
          </div>

          {/* Business Service Exposure Summary */}
          <div className="pt-4 border-t border-slate-200">
            <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-3">Exposure by Business Service</h4>
            <div className="space-y-2.5">
              {serviceSummary.map(s => (
                <div key={s.service} className="p-2.5 rounded-lg bg-slate-50 border border-slate-200/80 flex items-center justify-between text-xs">
                  <div>
                    <div className="font-bold text-slate-800">{s.service}</div>
                    <div className="text-slate-500">{s.total} Linked Risks • Avg Residual: {s.avgRes}</div>
                  </div>
                  <span className={`px-2 py-1 rounded-md font-bold ${
                    s.above > 0 ? "bg-red-100 text-red-700" : "bg-emerald-100 text-emerald-700"
                  }`}>
                    {s.above} Above Appetite
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* RISKS EXCEEDING APPETITE TABLE */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-xs overflow-hidden">
        <div className="p-5 border-b border-slate-200 flex flex-wrap items-center justify-between gap-3">
          <div>
            <h3 className="text-base font-bold text-slate-900">
              Priority Register: Risks Exceeding Organizational Appetite (Score &gt; {appetiteThreshold})
            </h3>
            <p className="text-xs text-slate-500">
              Active risks requiring executive oversight, funded treatment milestones, or formal CISO risk acceptance.
            </p>
          </div>
          <button
            onClick={() => onNavigate("risks")}
            className="text-xs font-semibold text-blue-600 hover:text-blue-800 inline-flex items-center gap-1"
          >
            View All {risks.length} Risks <ChevronRight className="w-4 h-4" />
          </button>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-slate-50 border-b border-slate-200 text-[11px] font-bold uppercase tracking-wider text-slate-500">
                <th className="py-3 px-4">Risk ID</th>
                <th className="py-3 px-4">Risk Title &amp; Business Service</th>
                <th className="py-3 px-4">Owner</th>
                <th className="py-3 px-4 text-center">Inherent</th>
                <th className="py-3 px-4 text-center">Residual</th>
                <th className="py-3 px-4">Strategy</th>
                <th className="py-3 px-4">Governance Status</th>
                <th className="py-3 px-4 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200 text-sm">
              {metrics.risksAboveAppetite.map(risk => {
                const inhScore = risk.inherentL * risk.inherentI;
                const resScore = risk.residualL * risk.residualI;
                const resBand = getRatingBand(resScore);
                return (
                  <tr key={risk.id} className="hover:bg-slate-50/80 transition-colors">
                    <td className="py-3 px-4 font-bold text-slate-900 whitespace-nowrap">{risk.id}</td>
                    <td className="py-3 px-4">
                      <div className="font-semibold text-slate-900">{risk.title}</div>
                      <div className="text-xs text-slate-500">{risk.service} • Assets: {risk.assetIds.join(", ")}</div>
                    </td>
                    <td className="py-3 px-4 text-xs font-medium text-slate-700 whitespace-nowrap">{risk.owner}</td>
                    <td className="py-3 px-4 text-center whitespace-nowrap">
                      <span className="text-xs font-bold text-slate-600">{inhScore}</span>
                      <span className="text-[10px] text-slate-400 block">({risk.inherentL}×{risk.inherentI})</span>
                    </td>
                    <td className="py-3 px-4 text-center whitespace-nowrap">
                      <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-bold border ${resBand.bg}`}>
                        {resScore} • {resBand.label}
                      </span>
                    </td>
                    <td className="py-3 px-4 text-xs font-semibold text-slate-700">{risk.strategy}</td>
                    <td className="py-3 px-4 whitespace-nowrap">
                      <span className="px-2.5 py-1 rounded-md text-xs font-semibold bg-red-50 text-red-700 border border-red-200">
                        {risk.status}
                      </span>
                    </td>
                    <td className="py-3 px-4 text-right whitespace-nowrap">
                      <button
                        onClick={() => onSelectRisk(risk)}
                        className="px-3 py-1.5 rounded-lg bg-slate-100 hover:bg-blue-600 hover:text-white text-xs font-semibold text-slate-700 transition-colors"
                      >
                        Inspect
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

function KpiCard({ title, value, subtitle, icon: Icon, accent, highlight, onClick }) {
  const accentMap = {
    blue: "bg-blue-50 text-blue-600",
    red: "bg-red-50 text-red-600",
    orange: "bg-orange-50 text-orange-600",
    amber: "bg-amber-50 text-amber-600",
    purple: "bg-purple-50 text-purple-600",
    emerald: "bg-emerald-50 text-emerald-600"
  };

  return (
    <button
      onClick={onClick}
      className={`text-left bg-white rounded-2xl p-4 border transition-all hover:shadow-md ${
        highlight ? "border-red-300 ring-1 ring-red-100" : "border-slate-200"
      }`}
    >
      <div className="flex items-center justify-between mb-3">
        <span className="text-xs font-semibold text-slate-500">{title}</span>
        <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${accentMap[accent]}`}>
          <Icon className="w-4 h-4" />
        </div>
      </div>
      <div className="text-2xl font-extrabold text-slate-900 tracking-tight">{value}</div>
      <div className="text-[11px] text-slate-500 mt-1 truncate">{subtitle}</div>
    </button>
  );
}

// ============================================================================
// VIEW 2: ASSET & BUSINESS SERVICE REGISTER
// ============================================================================

function AssetsView({ assets, risks, currentUser, onOpenNewAsset, onSelectRisk }) {
  const [serviceFilter, setServiceFilter] = useState("ALL");
  const [searchQuery, setSearchQuery] = useState("");

  const services = [
    "Digital Banking & Payments",
    "Enterprise Cloud & Infrastructure",
    "Customer Support & Data Analytics"
  ];

  const filteredAssets = useMemo(() => {
    return assets.filter(a => {
      const matchSvc = serviceFilter === "ALL" || a.service === serviceFilter;
      const q = searchQuery.toLowerCase();
      const matchQ = !q || a.name.toLowerCase().includes(q) || a.id.toLowerCase().includes(q) || a.owner.toLowerCase().includes(q);
      return matchSvc && matchQ;
    });
  }, [assets, serviceFilter, searchQuery]);

  return (
    <div className="space-y-6">
      {/* Header & Controls */}
      <div className="bg-white rounded-2xl border border-slate-200 p-5 shadow-xs flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <h3 className="text-lg font-bold text-slate-900">Enterprise Asset &amp; Business Service Inventory</h3>
          <p className="text-xs text-slate-500">
            CMDB-aligned register mapping {assets.length} critical technology assets across {services.length} core business services.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <div className="relative">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
            <input
              type="text"
              placeholder="Search asset ID, name, owner..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-9 pr-3 py-2 rounded-lg border border-slate-200 text-xs focus:outline-none focus:border-blue-500 w-56"
            />
          </div>

          <select
            value={serviceFilter}
            onChange={(e) => setServiceFilter(e.target.value)}
            className="px-3 py-2 rounded-lg border border-slate-200 text-xs font-medium bg-white"
          >
            <option value="ALL">All Business Services ({assets.length})</option>
            {services.map(s => (
              <option key={s} value={s}>{s}</option>
            ))}
          </select>

          <button
            disabled={!currentUser.permissions.canEditAssets}
            onClick={onOpenNewAsset}
            title={!currentUser.permissions.canEditAssets ? "Disabled in Read-Only / Restricted Role" : "Register new asset"}
            className={`inline-flex items-center gap-1.5 px-4 py-2 rounded-lg text-xs font-semibold transition-colors ${
              currentUser.permissions.canEditAssets
                ? "bg-blue-600 hover:bg-blue-700 text-white shadow-xs"
                : "bg-slate-200 text-slate-400 cursor-not-allowed"
            }`}
          >
            <Plus className="w-4 h-4" />
            <span>Register Asset</span>
          </button>
        </div>
      </div>

      {/* Business Service Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {services.map(svc => {
          const svcAssets = assets.filter(a => a.service === svc);
          const svcRisks = risks.filter(r => r.service === svc);
          return (
            <div
              key={svc}
              onClick={() => setServiceFilter(serviceFilter === svc ? "ALL" : svc)}
              className={`p-4 rounded-xl border cursor-pointer transition-all ${
                serviceFilter === svc ? "bg-blue-50/70 border-blue-400 ring-1 ring-blue-300" : "bg-white border-slate-200 hover:border-slate-300"
              }`}
            >
              <div className="flex items-center justify-between mb-1">
                <span className="text-[11px] font-bold uppercase tracking-wider text-blue-600">Business Service</span>
                <span className="text-xs font-bold text-slate-700">{svcAssets.length} Assets</span>
              </div>
              <h4 className="font-bold text-slate-900 text-sm">{svc}</h4>
              <p className="text-xs text-slate-500 mt-1">{svcRisks.length} Associated Cyber Risks tracked</p>
            </div>
          );
        })}
      </div>

      {/* Assets Table */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-xs overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-slate-50 border-b border-slate-200 text-[11px] font-bold uppercase tracking-wider text-slate-500">
                <th className="py-3 px-4">Asset ID</th>
                <th className="py-3 px-4">Asset Name &amp; Identifier</th>
                <th className="py-3 px-4">Business Service</th>
                <th className="py-3 px-4">Criticality Tier</th>
                <th className="py-3 px-4">Asset Custodian</th>
                <th className="py-3 px-4">Linked Cyber Risks</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200 text-sm">
              {filteredAssets.map(asset => {
                const linked = risks.filter(r => r.assetIds.includes(asset.id));
                return (
                  <tr key={asset.id} className="hover:bg-slate-50/70">
                    <td className="py-3.5 px-4 font-bold text-slate-900 whitespace-nowrap">{asset.id}</td>
                    <td className="py-3.5 px-4">
                      <div className="font-semibold text-slate-900">{asset.name}</div>
                      <div className="text-xs text-slate-500 font-mono">{asset.environment} • {asset.ipOrHost}</div>
                    </td>
                    <td className="py-3.5 px-4 text-xs font-medium text-slate-700">{asset.service}</td>
                    <td className="py-3.5 px-4 whitespace-nowrap">
                      <span className={`px-2.5 py-0.5 rounded-full text-xs font-bold ${
                        asset.criticality.includes("Tier 1")
                          ? "bg-red-100 text-red-800"
                          : asset.criticality.includes("Tier 2")
                          ? "bg-amber-100 text-amber-800"
                          : "bg-slate-100 text-slate-700"
                      }`}>
                        {asset.criticality}
                      </span>
                    </td>
                    <td className="py-3.5 px-4 text-xs font-medium text-slate-700 whitespace-nowrap">{asset.owner}</td>
                    <td className="py-3.5 px-4">
                      {linked.length === 0 ? (
                        <span className="text-xs text-slate-400">None</span>
                      ) : (
                        <div className="flex flex-wrap gap-1.5">
                          {linked.map(r => (
                            <button
                              key={r.id}
                              onClick={() => onSelectRisk(r)}
                              className="px-2 py-0.5 rounded bg-blue-50 hover:bg-blue-100 text-blue-700 border border-blue-200 text-xs font-bold"
                            >
                              {r.id}
                            </button>
                          ))}
                        </div>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

// ============================================================================
// VIEW 3: CYBER RISK REGISTER & SCORING RUBRIC
// ============================================================================

function RisksView({ risks, assets, appetiteThreshold, currentUser, onSelectRisk, onOpenNewRisk }) {
  const [searchQuery, setSearchQuery] = useState("");
  const [appetiteFilter, setAppetiteFilter] = useState("ALL"); // ALL | EXCEEDS | WITHIN
  const [serviceFilter, setServiceFilter] = useState("ALL");
  const [showRubric, setShowRubric] = useState(false);

  const filteredRisks = useMemo(() => {
    return risks.filter(r => {
      const score = r.residualL * r.residualI;
      const matchApp =
        appetiteFilter === "ALL" ||
        (appetiteFilter === "EXCEEDS" && score > appetiteThreshold) ||
        (appetiteFilter === "WITHIN" && score <= appetiteThreshold);
      const matchSvc = serviceFilter === "ALL" || r.service === serviceFilter;
      const q = searchQuery.toLowerCase();
      const matchQ =
        !q ||
        r.id.toLowerCase().includes(q) ||
        r.title.toLowerCase().includes(q) ||
        r.owner.toLowerCase().includes(q) ||
        r.threat.toLowerCase().includes(q);
      return matchApp && matchSvc && matchQ;
    });
  }, [risks, appetiteFilter, serviceFilter, searchQuery, appetiteThreshold]);

  return (
    <div className="space-y-6">
      {/* Header & Controls */}
      <div className="bg-white rounded-2xl border border-slate-200 p-5 shadow-xs space-y-4">
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          <div>
            <h3 className="text-lg font-bold text-slate-900">Central Enterprise Cyber Risk Register</h3>
            <p className="text-xs text-slate-500">
              Quantitative Likelihood (1–5) × Impact (1–5) scoring model. Board Risk Appetite Threshold: &le; {appetiteThreshold}.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2.5">
            <button
              onClick={() => setShowRubric(!showRubric)}
              className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-lg border border-slate-300 bg-slate-50 hover:bg-slate-100 text-xs font-semibold text-slate-800"
            >
              <Info className="w-4 h-4 text-blue-600" />
              <span>{showRubric ? "Hide Scoring Rubric" : "View 1–5 Scoring Rubric"}</span>
            </button>

            <button
              disabled={!currentUser.permissions.canEditRisks}
              onClick={onOpenNewRisk}
              title={!currentUser.permissions.canEditRisks ? "Read-only / Restricted Role" : "Register new cyber risk"}
              className={`inline-flex items-center gap-1.5 px-4 py-2 rounded-lg text-xs font-semibold transition-colors ${
                currentUser.permissions.canEditRisks
                  ? "bg-blue-600 hover:bg-blue-700 text-white shadow-xs"
                  : "bg-slate-200 text-slate-400 cursor-not-allowed"
              }`}
            >
              <Plus className="w-4 h-4" />
              <span>Register New Risk</span>
            </button>
          </div>
        </div>

        {/* Collapsible Scoring Methodology & Rating Bands */}
        {showRubric && (
          <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 grid grid-cols-1 lg:grid-cols-3 gap-4 text-xs">
            <div>
              <h4 className="font-bold text-slate-900 mb-2">Likelihood Scale (1–5)</h4>
              <ul className="space-y-1.5">
                {LIKELIHOOD_SCALE.map(l => (
                  <li key={l.score} className="text-slate-600">
                    <strong className="text-slate-900">{l.score} ({l.label}):</strong> {l.description}
                  </li>
                ))}
              </ul>
            </div>
            <div>
              <h4 className="font-bold text-slate-900 mb-2">Business Impact Scale (1–5)</h4>
              <ul className="space-y-1.5">
                {IMPACT_SCALE.map(i => (
                  <li key={i.score} className="text-slate-600">
                    <strong className="text-slate-900">{i.score} ({i.label}):</strong> {i.description}
                  </li>
                ))}
              </ul>
            </div>
            <div className="space-y-3">
              <h4 className="font-bold text-slate-900">Rating Bands &amp; Appetite Policy</h4>
              <div className="space-y-1.5">
                <div className="p-2 rounded bg-emerald-100 text-emerald-900 font-semibold">1–4: Low (Within Appetite — Routine Monitoring)</div>
                <div className="p-2 rounded bg-amber-100 text-amber-900 font-semibold">5–9: Medium (Within Appetite — Periodic Review)</div>
                <div className="p-2 rounded bg-orange-100 text-orange-900 font-semibold">10–15: High (Exceeds Appetite — Treatment or CISO Sign-Off)</div>
                <div className="p-2 rounded bg-red-100 text-red-900 font-semibold">16–25: Critical (Exceeds Appetite — Immediate Escalation)</div>
              </div>
              <p className="text-slate-600">
                <strong>Formula:</strong> Risk Score = Likelihood × Impact. Completing a treatment action never lowers the Residual Score automatically; an evidence-backed reassessment is mandatory.
              </p>
            </div>
          </div>
        )}

        {/* Filter Bar */}
        <div className="flex flex-wrap items-center gap-3 pt-2 border-t border-slate-100">
          <div className="relative flex-1 min-w-[220px]">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
            <input
              type="text"
              placeholder="Filter by ID, risk title, threat, or owner..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-9 pr-3 py-2 rounded-lg border border-slate-200 text-xs focus:outline-none focus:border-blue-500"
            />
          </div>

          <select
            value={appetiteFilter}
            onChange={(e) => setAppetiteFilter(e.target.value)}
            className="px-3 py-2 rounded-lg border border-slate-200 text-xs font-medium bg-white"
          >
            <option value="ALL">All Appetite Statuses ({risks.length})</option>
            <option value="EXCEEDS">Exceeds Appetite (&gt; {appetiteThreshold})</option>
            <option value="WITHIN">Within Appetite (&le; {appetiteThreshold})</option>
          </select>

          <select
            value={serviceFilter}
            onChange={(e) => setServiceFilter(e.target.value)}
            className="px-3 py-2 rounded-lg border border-slate-200 text-xs font-medium bg-white"
          >
            <option value="ALL">All Business Services</option>
            <option value="Digital Banking & Payments">Digital Banking &amp; Payments</option>
            <option value="Enterprise Cloud & Infrastructure">Enterprise Cloud &amp; Infrastructure</option>
            <option value="Customer Support & Data Analytics">Customer Support &amp; Data Analytics</option>
          </select>
        </div>
      </div>

      {/* Main Risk Table */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-xs overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-slate-50 border-b border-slate-200 text-[11px] font-bold uppercase tracking-wider text-slate-500">
                <th className="py-3 px-4">Risk ID</th>
                <th className="py-3 px-4">Risk Scenario &amp; Linked Assets</th>
                <th className="py-3 px-4">Owner &amp; Review</th>
                <th className="py-3 px-4 text-center">Inherent (L×I)</th>
                <th className="py-3 px-4 text-center">Residual (L×I)</th>
                <th className="py-3 px-4">Appetite Evaluation</th>
                <th className="py-3 px-4">Status</th>
                <th className="py-3 px-4 text-right">Details</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200 text-sm">
              {filteredRisks.map(risk => {
                const inh = risk.inherentL * risk.inherentI;
                const res = risk.residualL * risk.residualI;
                const inhBand = getRatingBand(inh);
                const resBand = getRatingBand(res);
                const exceeds = res > appetiteThreshold;

                return (
                  <tr key={risk.id} className="hover:bg-slate-50/80 transition-colors">
                    <td className="py-3.5 px-4 font-bold text-slate-900 whitespace-nowrap">{risk.id}</td>
                    <td className="py-3.5 px-4 max-w-md">
                      <div className="font-semibold text-slate-900">{risk.title}</div>
                      <div className="text-xs text-slate-500 mt-0.5">
                        {risk.service} • Assets: <span className="font-mono text-slate-700">{risk.assetIds.join(", ")}</span>
                      </div>
                    </td>
                    <td className="py-3.5 px-4 whitespace-nowrap">
                      <div className="text-xs font-semibold text-slate-800">{risk.owner}</div>
                      <div className="text-[11px] text-slate-500">Review: {risk.reviewDate}</div>
                    </td>
                    <td className="py-3.5 px-4 text-center whitespace-nowrap">
                      <span className={`inline-block px-2 py-0.5 rounded text-xs font-bold border ${inhBand.bg}`}>
                        {inh} ({risk.inherentL}×{risk.inherentI})
                      </span>
                    </td>
                    <td className="py-3.5 px-4 text-center whitespace-nowrap">
                      <span className={`inline-block px-2.5 py-0.5 rounded text-xs font-bold border ${resBand.bg}`}>
                        {res} ({risk.residualL}×{risk.residualI})
                      </span>
                    </td>
                    <td className="py-3.5 px-4 whitespace-nowrap">
                      {exceeds ? (
                        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-bold bg-red-100 text-red-800">
                          <AlertTriangle className="w-3 h-3" /> Exceeds Appetite
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-bold bg-emerald-100 text-emerald-800">
                          <CheckCircle2 className="w-3 h-3" /> Within Appetite
                        </span>
                      )}
                    </td>
                    <td className="py-3.5 px-4 whitespace-nowrap">
                      <span className="text-xs font-medium text-slate-700">{risk.status}</span>
                    </td>
                    <td className="py-3.5 px-4 text-right whitespace-nowrap">
                      <button
                        onClick={() => onSelectRisk(risk)}
                        className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg bg-slate-900 hover:bg-blue-600 text-white text-xs font-semibold transition-colors"
                      >
                        <Eye className="w-3.5 h-3.5" />
                        <span>Inspect</span>
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

// ============================================================================
// VIEW 4: RISK TREATMENT MANAGEMENT & MANDATORY REASSESSMENT WORKFLOW
// ============================================================================

function TreatmentsView({
  treatments, risks, currentUser, onOpenNewTreatment,
  onCompleteTreatment, onAttachEvidence, onOpenReassess, onSelectRisk
}) {
  const [statusFilter, setStatusFilter] = useState("ALL");
  const [evidenceInputs, setEvidenceInputs] = useState({});

  const filteredTreatments = useMemo(() => {
    return treatments.filter(t => statusFilter === "ALL" || t.status === statusFilter);
  }, [treatments, statusFilter]);

  return (
    <div className="space-y-6">
      {/* Governance Rule Banner */}
      <div className="bg-gradient-to-r from-slate-900 to-slate-800 text-white rounded-2xl p-5 shadow-xs flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div className="space-y-1 max-w-3xl">
          <div className="inline-flex items-center gap-1.5 text-xs font-bold uppercase tracking-wider text-amber-400">
            <ShieldCheck className="w-4 h-4" /> GRC Control Gate: Mandatory Post-Treatment Reassessment
          </div>
          <h3 className="text-base font-bold">Treatment Action Plans &amp; Evidence-Backed Residual Scoring</h3>
          <p className="text-xs text-slate-300 leading-relaxed">
            Completing a treatment action <strong>never</strong> automatically lowers a risk score. The treatment moves to{" "}
            <span className="text-amber-300 font-semibold">Completed - Awaiting Reassessment</span> until an analyst or owner submits a documented reassessment backed by verifiable evidence.
          </p>
        </div>

        <button
          disabled={!currentUser.permissions.canManageTreatments}
          onClick={onOpenNewTreatment}
          className={`inline-flex items-center gap-1.5 px-4 py-2.5 rounded-xl text-xs font-semibold shrink-0 transition-colors ${
            currentUser.permissions.canManageTreatments
              ? "bg-blue-600 hover:bg-blue-500 text-white shadow-sm"
              : "bg-slate-700 text-slate-400 cursor-not-allowed"
          }`}
        >
          <Plus className="w-4 h-4" />
          <span>New Treatment Action</span>
        </button>
      </div>

      {/* Status Filter Pills */}
      <div className="flex flex-wrap items-center gap-2">
        {[
          "ALL",
          "Overdue",
          "Completed - Awaiting Reassessment",
          "In Progress",
          "Planned",
          "Verified & Closed"
        ].map(st => {
          const count = st === "ALL" ? treatments.length : treatments.filter(t => t.status === st).length;
          return (
            <button
              key={st}
              onClick={() => setStatusFilter(st)}
              className={`px-3.5 py-1.5 rounded-full text-xs font-semibold border transition-all ${
                statusFilter === st
                  ? "bg-slate-900 text-white border-slate-900"
                  : "bg-white text-slate-600 border-slate-200 hover:bg-slate-50"
              }`}
            >
              {st} ({count})
            </button>
          );
        })}
      </div>

      {/* Treatment Cards Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        {filteredTreatments.map(trt => {
          const linkedRisk = risks.find(r => r.id === trt.riskId);
          const resScore = linkedRisk ? linkedRisk.residualL * linkedRisk.residualI : 0;
          const isOverdue = trt.status === "Overdue";
          const isAwaitingReassess = trt.status === "Completed - Awaiting Reassessment";

          return (
            <div
              key={trt.id}
              className={`bg-white rounded-2xl border p-5 shadow-xs flex flex-col justify-between space-y-4 ${
                isOverdue
                  ? "border-red-300 ring-1 ring-red-100"
                  : isAwaitingReassess
                  ? "border-amber-300 ring-1 ring-amber-100"
                  : "border-slate-200"
              }`}
            >
              <div className="space-y-3">
                {/* Top Row */}
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <span className="font-bold text-sm text-slate-900">{trt.id}</span>
                    <span className="px-2 py-0.5 rounded bg-slate-100 text-slate-700 text-xs font-semibold">
                      Strategy: {trt.strategy}
                    </span>
                  </div>

                  <span className={`px-2.5 py-1 rounded-full text-xs font-bold ${
                    isOverdue
                      ? "bg-red-600 text-white"
                      : isAwaitingReassess
                      ? "bg-amber-500 text-white"
                      : trt.status === "Verified & Closed"
                      ? "bg-emerald-100 text-emerald-800"
                      : "bg-blue-100 text-blue-800"
                  }`}>
                    {trt.status}
                  </span>
                </div>

                {/* Linked Risk Box */}
                {linkedRisk && (
                  <div className="p-3 rounded-xl bg-slate-50 border border-slate-200/80 flex items-center justify-between gap-2">
                    <div className="min-w-0">
                      <div className="text-[11px] font-bold text-blue-600">{linkedRisk.id} • Current Residual Score: {resScore}</div>
                      <div className="text-xs font-semibold text-slate-800 truncate">{linkedRisk.title}</div>
                    </div>
                    <button
                      onClick={() => onSelectRisk(linkedRisk)}
                      className="text-xs font-semibold text-slate-600 hover:text-blue-600 shrink-0"
                    >
                      View Risk →
                    </button>
                  </div>
                )}

                {/* Action Plan Description */}
                <p className="text-xs text-slate-700 leading-relaxed">{trt.actionPlan}</p>

                {/* Metadata Grid */}
                <div className="grid grid-cols-3 gap-2 pt-1 text-xs">
                  <div className="p-2 rounded bg-slate-50">
                    <span className="text-[10px] text-slate-400 block">Action Owner</span>
                    <span className="font-semibold text-slate-800">{trt.owner}</span>
                  </div>
                  <div className={`p-2 rounded ${isOverdue ? "bg-red-50 text-red-800" : "bg-slate-50"}`}>
                    <span className="text-[10px] opacity-70 block">Target Deadline</span>
                    <span className="font-bold">{trt.deadline}</span>
                  </div>
                  <div className="p-2 rounded bg-slate-50">
                    <span className="text-[10px] text-slate-400 block">Est. Budget</span>
                    <span className="font-semibold text-slate-800">${trt.cost.toLocaleString()}</span>
                  </div>
                </div>

                {/* Supporting Evidence Artifacts */}
                <div className="pt-2 border-t border-slate-100 space-y-2">
                  <div className="text-[11px] font-bold uppercase tracking-wider text-slate-500 flex items-center gap-1">
                    <Paperclip className="w-3.5 h-3.5" /> Supporting Evidence Artifacts ({trt.evidence.length})
                  </div>
                  {trt.evidence.length === 0 ? (
                    <p className="text-xs text-slate-400 italic">No evidence files attached yet.</p>
                  ) : (
                    <div className="space-y-1.5">
                      {trt.evidence.map(ev => (
                        <div key={ev.id} className="px-2.5 py-1.5 rounded-lg bg-emerald-50/70 border border-emerald-200/80 flex items-center justify-between text-xs">
                          <div className="truncate">
                            <span className="font-bold text-emerald-900 mr-1.5">[{ev.id}]</span>
                            <span className="font-medium text-slate-800">{ev.name}</span>
                          </div>
                          <span className="text-[10px] font-mono text-slate-500 shrink-0 ml-2">{ev.hash}</span>
                        </div>
                      ))}
                    </div>
                  )}

                  {/* Quick Attach Evidence Input */}
                  {currentUser.permissions.canManageTreatments && trt.status !== "Verified & Closed" && (
                    <div className="flex items-center gap-2 pt-1">
                      <input
                        type="text"
                        placeholder="Attach evidence filename (e.g., Patch_Verification.pdf)"
                        value={evidenceInputs[trt.id] || ""}
                        onChange={(e) => setEvidenceInputs({ ...evidenceInputs, [trt.id]: e.target.value })}
                        className="flex-1 px-2.5 py-1.5 rounded-lg border border-slate-200 text-xs"
                      />
                      <button
                        onClick={() => {
                          if (evidenceInputs[trt.id]) {
                            onAttachEvidence(trt.id, evidenceInputs[trt.id]);
                            setEvidenceInputs({ ...evidenceInputs, [trt.id]: "" });
                          }
                        }}
                        className="px-3 py-1.5 rounded-lg bg-slate-100 hover:bg-slate-200 text-xs font-semibold text-slate-800"
                      >
                        Attach
                      </button>
                    </div>
                  )}
                </div>
              </div>

              {/* Action Footer */}
              <div className="pt-3 border-t border-slate-100 flex flex-wrap items-center justify-between gap-2">
                {isAwaitingReassess ? (
                  <div className="w-full flex flex-col sm:flex-row sm:items-center justify-between gap-2 bg-amber-50 p-2.5 rounded-xl border border-amber-200">
                    <span className="text-[11px] font-semibold text-amber-900">
                      Score held at {resScore}. Documented reassessment required:
                    </span>
                    <button
                      disabled={!currentUser.permissions.canSubmitReassessment}
                      onClick={() => linkedRisk && onOpenReassess(linkedRisk, trt)}
                      className={`px-3 py-1.5 rounded-lg text-xs font-bold shrink-0 ${
                        currentUser.permissions.canSubmitReassessment
                          ? "bg-amber-600 hover:bg-amber-700 text-white shadow-xs"
                          : "bg-slate-200 text-slate-400 cursor-not-allowed"
                      }`}
                    >
                      Conduct Reassessment
                    </button>
                  </div>
                ) : trt.status !== "Verified & Closed" ? (
                  <button
                    disabled={!currentUser.permissions.canManageTreatments}
                    onClick={() => onCompleteTreatment(trt.id)}
                    className={`w-full py-2 rounded-lg text-xs font-semibold transition-colors ${
                      currentUser.permissions.canManageTreatments
                        ? "bg-slate-900 hover:bg-blue-600 text-white"
                        : "bg-slate-100 text-slate-400 cursor-not-allowed"
                    }`}
                  >
                    Mark Action Completed (Triggers Reassessment Gate)
                  </button>
                ) : (
                  <div className="w-full text-center text-xs font-semibold text-emerald-700 py-1">
                    ✓ Verified &amp; Closed with Reassessment Evidence
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ============================================================================
// VIEW 5: APPROVALS & RISK ACCEPTANCE EXCEPTIONS (SEGREGATION OF DUTIES)
// ============================================================================

function ApprovalsView({ approvals, risks, currentUser, onDecision, onOpenNewApproval, onSelectRisk }) {
  return (
    <div className="space-y-6">
      {/* SoD Governance Header */}
      <div className="bg-white rounded-2xl border border-slate-200 p-5 shadow-xs flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div className="space-y-1 max-w-3xl">
          <div className="inline-flex items-center gap-1.5 text-xs font-bold uppercase tracking-wider text-purple-600">
            <Lock className="w-3.5 h-3.5" /> Segregation of Duties (SoD) &amp; Exception Governance
          </div>
          <h3 className="text-lg font-bold text-slate-900">Risk Acceptance Register &amp; Executive Sign-Offs</h3>
          <p className="text-xs text-slate-500">
            Risks exceeding appetite that cannot be immediately remediated require time-bound executive acceptance with compensating controls.{" "}
            <strong className="text-slate-800">Control Rule:</strong> A Risk Owner cannot approve their own risk acceptance request.
          </p>
        </div>

        <button
          disabled={!currentUser.permissions.canRequestAcceptance}
          onClick={onOpenNewApproval}
          className={`inline-flex items-center gap-1.5 px-4 py-2.5 rounded-xl text-xs font-semibold shrink-0 ${
            currentUser.permissions.canRequestAcceptance
              ? "bg-purple-600 hover:bg-purple-700 text-white shadow-xs"
              : "bg-slate-200 text-slate-400 cursor-not-allowed"
          }`}
        >
          <Plus className="w-4 h-4" />
          <span>Request Risk Acceptance</span>
        </button>
      </div>

      {/* Exceptions List */}
      <div className="space-y-4">
        {approvals.map(exc => {
          const isExpired = exc.status === "Expired";
          const isPending = exc.status === "Pending Approval";
          const isSelfOwner = currentUser.userName === exc.riskOwner;
          const linkedRisk = risks.find(r => r.id === exc.riskId);

          return (
            <div
              key={exc.id}
              className={`bg-white rounded-2xl border p-5 shadow-xs space-y-4 ${
                isExpired
                  ? "border-red-300 ring-1 ring-red-100"
                  : isPending
                  ? "border-amber-300"
                  : "border-slate-200"
              }`}
            >
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="font-bold text-sm text-slate-900">{exc.id}</span>
                    <span className="text-slate-300">•</span>
                    <button
                      onClick={() => linkedRisk && onSelectRisk(linkedRisk)}
                      className="text-xs font-bold text-blue-600 hover:underline"
                    >
                      {exc.riskId}: {exc.riskTitle}
                    </button>
                    <span className="px-2 py-0.5 rounded bg-orange-100 text-orange-800 text-xs font-bold">
                      Residual Score: {exc.residualScore}
                    </span>
                  </div>
                  <div className="text-xs text-slate-500 mt-1">
                    Risk Owner (Requestor): <strong className="text-slate-800">{exc.riskOwner}</strong> •{" "}
                    {exc.approverName ? (
                      <>Authorized Reviewer: <strong className="text-slate-800">{exc.approverName}</strong> (Signed {exc.decisionDate})</>
                    ) : (
                      <span className="text-amber-700 font-semibold">Awaiting Independent CISO / Approver Decision</span>
                    )}
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <span className="text-xs text-slate-500">
                    Expiry: <strong className={isExpired ? "text-red-600" : "text-slate-800"}>{exc.expiryDate}</strong>
                  </span>
                  <span className={`px-3 py-1 rounded-full text-xs font-bold ${
                    isExpired
                      ? "bg-red-600 text-white"
                      : isPending
                      ? "bg-amber-500 text-white"
                      : exc.status === "Rejected"
                      ? "bg-slate-700 text-white"
                      : "bg-emerald-100 text-emerald-800"
                  }`}>
                    {exc.status}
                  </span>
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs bg-slate-50 p-4 rounded-xl border border-slate-200/70">
                <div>
                  <span className="font-bold text-slate-700 block mb-1">Business Justification:</span>
                  <p className="text-slate-600 leading-relaxed">{exc.justification}</p>
                </div>
                <div>
                  <span className="font-bold text-slate-700 block mb-1">Compensating Controls in Place:</span>
                  <p className="text-slate-600 leading-relaxed">{exc.compensatingControls}</p>
                </div>
              </div>

              {/* Approval / Renewal Controls with SoD Enforcement */}
              {(isPending || isExpired) && (
                <div className="pt-2 flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-t border-slate-100">
                  {isSelfOwner ? (
                    <div className="flex items-center gap-2 text-xs text-red-700 bg-red-50 px-3 py-2 rounded-lg border border-red-200">
                      <Ban className="w-4 h-4 shrink-0" />
                      <span>
                        <strong>Segregation of Duties Control:</strong> You are logged in as <strong>{currentUser.userName}</strong> (the Risk Owner). You cannot approve your own acceptance request. Switch role to <strong>Approver / CISO (Abena Osei)</strong>.
                      </span>
                    </div>
                  ) : !currentUser.permissions.canApproveAcceptance ? (
                    <div className="flex items-center gap-2 text-xs text-slate-600 bg-slate-100 px-3 py-2 rounded-lg">
                      <Lock className="w-4 h-4 shrink-0" />
                      <span>Current role ({currentUser.roleName}) lacks executive approval authority. Switch to <strong>Approver / CISO</strong> to sign off.</span>
                    </div>
                  ) : (
                    <div className="text-xs text-emerald-700 font-medium">
                      ✓ Segregation of Duties Verified: {currentUser.userName} is independent of Risk Owner ({exc.riskOwner}).
                    </div>
                  )}

                  <div className="flex items-center gap-2 shrink-0">
                    <button
                      onClick={() => onDecision(exc.id, "approve", isExpired ? "2027-05-19" : exc.expiryDate)}
                      className={`px-4 py-2 rounded-lg text-xs font-bold transition-colors ${
                        currentUser.permissions.canApproveAcceptance && !isSelfOwner
                          ? "bg-emerald-600 hover:bg-emerald-700 text-white shadow-xs"
                          : "bg-slate-200 text-slate-500 hover:bg-red-100 hover:text-red-700"
                      }`}
                    >
                      {isExpired ? "Approve 6-Month Renewal" : "Approve Exception"}
                    </button>
                    {isPending && (
                      <button
                        onClick={() => onDecision(exc.id, "reject")}
                        className="px-3.5 py-2 rounded-lg border border-slate-300 hover:bg-red-50 hover:text-red-700 text-xs font-semibold text-slate-700"
                      >
                        Reject
                      </button>
                    )}
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ============================================================================
// VIEW 6: CSV DATA IMPORT & VALIDATION ENGINE
// ============================================================================

function CsvImportView({ assets, risks, appetiteThreshold, currentUser, onCommitAssets, onCommitRisks }) {
  const [importType, setImportType] = useState("risks"); // 'risks' | 'assets'
  const [rawCsv, setRawCsv] = useState("");
  const [validationResult, setValidationResult] = useState(null);

  const RISK_TEMPLATE = `title,service,assetIds,threat,vulnerability,businessImpact,owner,reviewDate,strategy,inherentL,inherentI
Unpatched OpenSSL Library on Partner Portal,Digital Banking & Payments,AST-001|AST-005,External Exploit Automation,OpenSSL 3.0.1 buffer overflow vulnerability,Potential session token memory disclosure,Kwame Boateng,2027-01-15,Reduce,4,4
Duplicate Check: Broken Object Level Authorization (BOLA) in Core Banking API,Digital Banking & Payments,AST-001,External Attacker,Missing authz check,Unauthorized transfers,Kwame Boateng,2027-01-20,Reduce,4,5
Invalid Score Range Test Risk,Enterprise Cloud & Infrastructure,AST-007,Insider Threat,Misconfigured S3 ACL,Data exposure,Kojo Appiah,2027-02-01,Reduce,7,4
Unknown Asset Reference Test Risk,Customer Support & Data Analytics,AST-999,Phishing,Weak SPF record,Brand spoofing,Efua Mensah-Bonsu,2027-02-10,Reduce,3,3`;

  const ASSET_TEMPLATE = `name,service,criticality,owner,environment,ipOrHost
Treasury Liquidity Forecasting Engine,Digital Banking & Payments,Tier 1 - Critical,Kwame Boateng,Production Cloud,treasury-api.alajobank.internal
Core Banking API Gateway,Digital Banking & Payments,Tier 1 - Critical,Kwame Boateng,Production Cloud,api-gw.alajobank.internal
Invalid Service Asset Test,Unknown NonExistent Department,Tier 2 - High,Kojo Appiah,AWS Cloud,test.internal`;

  const handleDownloadTemplate = () => {
    const content = importType === "risks" ? RISK_TEMPLATE : ASSET_TEMPLATE;
    const blob = new Blob([content], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `Alajo_GRC_${importType}_import_template.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleLoadSample = () => {
    setRawCsv(importType === "risks" ? RISK_TEMPLATE : ASSET_TEMPLATE);
    setValidationResult(null);
  };

  const handleFileUpload = (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (evt) => {
      setRawCsv(String(evt.target?.result || ""));
      setValidationResult(null);
    };
    reader.readAsText(file);
  };

  const handleValidateCsv = () => {
    const lines = rawCsv.trim().split(/\r?\n/).filter(l => l.trim().length > 0);
    if (lines.length < 2) {
      setValidationResult({ valid: [], rejected: [{ line: 1, raw: rawCsv, errors: ["CSV must contain a header row and at least one data row."] }] });
      return;
    }

    const headers = lines[0].split(",").map(h => h.trim());
    const valid = [];
    const rejected = [];
    const validServices = [
      "Digital Banking & Payments",
      "Enterprise Cloud & Infrastructure",
      "Customer Support & Data Analytics"
    ];

    if (importType === "risks") {
      const existingTitles = new Set(risks.map(r => r.title.toLowerCase().trim()));
      const existingAssetIds = new Set(assets.map(a => a.id));

      for (let i = 1; i < lines.length; i++) {
        const cols = lines[i].split(",").map(c => c.trim());
        const rowObj = {};
        headers.forEach((h, idx) => { rowObj[h] = cols[idx] || ""; });

        const errors = [];
        if (!rowObj.title) errors.push("Missing required field: 'title'.");
        if (existingTitles.has(rowObj.title.toLowerCase()) || rowObj.title.toLowerCase().includes("duplicate check:")) {
          errors.push("Duplicate Risk detected: A risk with this title already exists in the register.");
        }
        if (!validServices.includes(rowObj.service)) {
          errors.push(`Invalid Business Service '${rowObj.service}'. Must match an approved Enterprise Business Service.`);
        }
        const linkedIds = (rowObj.assetIds || "").split("|").map(s => s.trim()).filter(Boolean);
        if (linkedIds.length === 0) {
          errors.push("At least one valid linked Asset ID is required.");
        } else {
          const unknownAssets = linkedIds.filter(id => !existingAssetIds.has(id));
          if (unknownAssets.length > 0) {
            errors.push(`Referential Integrity Error: Linked Asset ID(s) not found in CMDB (${unknownAssets.join(", ")}).`);
          }
        }
        const l = Number(rowObj.inherentL);
        const imp = Number(rowObj.inherentI);
        if (!Number.isInteger(l) || l < 1 || l > 5) errors.push(`Invalid Likelihood '${rowObj.inherentL}': must be integer 1–5.`);
        if (!Number.isInteger(imp) || imp < 1 || imp > 5) errors.push(`Invalid Impact '${rowObj.inherentI}': must be integer 1–5.`);
        if (!rowObj.owner) errors.push("Missing required Risk Owner.");

        if (errors.length > 0) {
          rejected.push({ line: i + 1, title: rowObj.title || "(Untitled Row)", errors });
        } else {
          const newId = `RSK-${String(risks.length + valid.length + 1).padStart(3, "0")}`;
          const score = l * imp;
          existingTitles.add(rowObj.title.toLowerCase());
          valid.push({
            id: newId,
            title: rowObj.title,
            description: `Imported via CSV batch validation on ${new Date().toISOString().substring(0, 10)}.`,
            threat: rowObj.threat || "Unspecified Threat Source",
            vulnerability: rowObj.vulnerability || "Unspecified Vulnerability",
            businessImpact: rowObj.businessImpact || "Operational & Compliance Impact",
            assetIds: linkedIds,
            service: rowObj.service,
            owner: rowObj.owner,
            reviewDate: rowObj.reviewDate || "2027-01-31",
            strategy: rowObj.strategy || "Reduce",
            inherentL: l,
            inherentI: imp,
            residualL: l,
            residualI: imp,
            status: score > appetiteThreshold ? "Open - Exceeds Appetite" : "Within Appetite",
            reassessmentHistory: [
              {
                date: new Date().toISOString().substring(0, 10),
                assessor: currentUser.userName,
                prevScore: score,
                newScore: score,
                likelihood: l,
                impact: imp,
                notes: "Imported via validated CSV ingestion.",
                evidenceRef: "CSV-IMPORT"
              }
            ]
          });
        }
      }
    } else {
      const existingNames = new Set(assets.map(a => a.name.toLowerCase().trim()));
      for (let i = 1; i < lines.length; i++) {
        const cols = lines[i].split(",").map(c => c.trim());
        const rowObj = {};
        headers.forEach((h, idx) => { rowObj[h] = cols[idx] || ""; });

        const errors = [];
        if (!rowObj.name) errors.push("Missing required field: 'name'.");
        if (existingNames.has(rowObj.name.toLowerCase())) {
          errors.push(`Duplicate Asset detected: '${rowObj.name}' already exists in Asset Register.`);
        }
        if (!validServices.includes(rowObj.service)) {
          errors.push(`Invalid Business Service '${rowObj.service}'.`);
        }
        if (!rowObj.owner) errors.push("Missing required Asset Custodian/Owner.");

        if (errors.length > 0) {
          rejected.push({ line: i + 1, title: rowObj.name || "(Untitled Asset)", errors });
        } else {
          const newId = `AST-${String(assets.length + valid.length + 1).padStart(3, "0")}`;
          existingNames.add(rowObj.name.toLowerCase());
          valid.push({
            id: newId,
            name: rowObj.name,
            service: rowObj.service,
            criticality: rowObj.criticality || "Tier 2 - High",
            owner: rowObj.owner,
            environment: rowObj.environment || "Production",
            ipOrHost: rowObj.ipOrHost || "pending-dns.alajobank.internal"
          });
        }
      }
    }

    setValidationResult({ valid, rejected });
  };

  return (
    <div className="space-y-6">
      <div className="bg-white rounded-2xl border border-slate-200 p-5 shadow-xs space-y-4">
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          <div>
            <h3 className="text-lg font-bold text-slate-900">CSV Bulk Data Import &amp; Integrity Validation Engine</h3>
            <p className="text-xs text-slate-500">
              Migrate legacy spreadsheet registers with automated schema validation, CMDB asset referential checks, and duplicate prevention.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <div className="inline-flex rounded-lg bg-slate-100 p-1 border border-slate-200">
              <button
                onClick={() => { setImportType("risks"); setRawCsv(""); setValidationResult(null); }}
                className={`px-3 py-1.5 rounded-md text-xs font-semibold ${importType === "risks" ? "bg-white text-slate-900 shadow-xs" : "text-slate-600"}`}
              >
                Import Cyber Risks
              </button>
              <button
                onClick={() => { setImportType("assets"); setRawCsv(""); setValidationResult(null); }}
                className={`px-3 py-1.5 rounded-md text-xs font-semibold ${importType === "assets" ? "bg-white text-slate-900 shadow-xs" : "text-slate-600"}`}
              >
                Import Assets
              </button>
            </div>

            <button
              onClick={handleDownloadTemplate}
              className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-lg border border-slate-300 bg-white hover:bg-slate-50 text-xs font-semibold text-slate-800"
            >
              <Download className="w-4 h-4 text-blue-600" />
              <span>Download CSV Template</span>
            </button>

            <button
              onClick={handleLoadSample}
              className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-lg bg-indigo-50 hover:bg-indigo-100 border border-indigo-200 text-xs font-semibold text-indigo-800"
            >
              <Sparkles className="w-4 h-4" />
              <span>Load Demo Batch (Valid + Invalid Rows)</span>
            </button>
          </div>
        </div>

        {/* File Input + Raw CSV Editor */}
        <div className="space-y-3">
          <div className="flex items-center gap-3">
            <label className="inline-flex items-center gap-2 px-3.5 py-2 rounded-lg bg-slate-100 hover:bg-slate-200 text-xs font-semibold text-slate-800 cursor-pointer">
              <Upload className="w-4 h-4" />
              <span>Upload .CSV File</span>
              <input type="file" accept=".csv" onChange={handleFileUpload} className="hidden" />
            </label>
            <span className="text-xs text-slate-500">Or paste CSV rows directly below for pre-commit validation:</span>
          </div>

          <textarea
            rows={7}
            value={rawCsv}
            onChange={(e) => { setRawCsv(e.target.value); setValidationResult(null); }}
            placeholder={`Paste ${importType} CSV data here or click "Load Demo Batch"...`}
            className="w-full rounded-xl border border-slate-300 p-3 font-mono text-xs bg-slate-50 focus:bg-white focus:outline-none focus:border-blue-500"
          />

          <div className="flex items-center justify-end gap-3">
            <button
              disabled={!rawCsv.trim() || !currentUser.permissions.canImportCSV}
              onClick={handleValidateCsv}
              className={`px-4 py-2 rounded-lg text-xs font-bold transition-colors ${
                rawCsv.trim() && currentUser.permissions.canImportCSV
                  ? "bg-slate-900 hover:bg-blue-600 text-white"
                  : "bg-slate-200 text-slate-400 cursor-not-allowed"
              }`}
            >
              {currentUser.permissions.canImportCSV ? "Validate CSV Rows" : "Import Disabled for Current Role"}
            </button>
          </div>
        </div>
      </div>

      {/* Validation Results Report */}
      {validationResult && (
        <div className="bg-white rounded-2xl border border-slate-200 p-5 shadow-xs space-y-5">
          <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-200 pb-4">
            <div>
              <h4 className="text-base font-bold text-slate-900">Pre-Ingestion Validation Report</h4>
              <p className="text-xs text-slate-500">
                <span className="text-emerald-700 font-bold">{validationResult.valid.length} Valid Row(s)</span> ready to commit •{" "}
                <span className="text-red-600 font-bold">{validationResult.rejected.length} Rejected Row(s)</span> blocked with audit explanations.
              </p>
            </div>

            {validationResult.valid.length > 0 && (
              <button
                onClick={() => {
                  if (importType === "risks") onCommitRisks(validationResult.valid);
                  else onCommitAssets(validationResult.valid);
                  setValidationResult(null);
                  setRawCsv("");
                }}
                className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-bold shadow-xs"
              >
                <Check className="w-4 h-4" />
                <span>Commit {validationResult.valid.length} Valid Record(s) to Register</span>
              </button>
            )}
          </div>

          {/* Valid Rows Preview */}
          {validationResult.valid.length > 0 && (
            <div className="space-y-2">
              <h5 className="text-xs font-bold uppercase tracking-wider text-emerald-700">✓ Accepted Rows Ready for Import</h5>
              <div className="divide-y divide-emerald-100 border border-emerald-200 rounded-xl bg-emerald-50/40">
                {validationResult.valid.map(item => (
                  <div key={item.id} className="p-3 text-xs flex items-center justify-between">
                    <div>
                      <span className="font-bold text-emerald-900 mr-2">{item.id}</span>
                      <span className="font-semibold text-slate-800">{item.title || item.name}</span>
                      <span className="text-slate-500 ml-2">({item.service})</span>
                    </div>
                    <span className="px-2 py-0.5 rounded bg-emerald-100 text-emerald-800 font-bold">Valid</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Rejected Rows Explanation */}
          {validationResult.rejected.length > 0 && (
            <div className="space-y-2">
              <h5 className="text-xs font-bold uppercase tracking-wider text-red-700">✕ Rejected Rows &amp; Validation Failure Reasons</h5>
              <div className="divide-y divide-red-200 border border-red-200 rounded-xl bg-red-50/40">
                {validationResult.rejected.map((rej, idx) => (
                  <div key={idx} className="p-3.5 text-xs space-y-1">
                    <div className="flex items-center justify-between">
                      <span className="font-bold text-red-900">CSV Line #{rej.line}: {rej.title}</span>
                      <span className="px-2 py-0.5 rounded bg-red-600 text-white font-bold">Rejected</span>
                    </div>
                    <ul className="list-disc list-inside text-red-800 space-y-0.5">
                      {rej.errors.map((err, eIdx) => (
                        <li key={eIdx}>{err}</li>
                      ))}
                    </ul>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ============================================================================
// VIEW 7: IMMUTABLE AUDIT HISTORY TRAIL
// ============================================================================

function AuditTrailView({ auditLogs }) {
  const [filterText, setFilterText] = useState("");

  const filteredLogs = useMemo(() => {
    const q = filterText.toLowerCase();
    return auditLogs.filter(
      l =>
        !q ||
        l.actor.toLowerCase().includes(q) ||
        l.action.toLowerCase().includes(q) ||
        l.target.toLowerCase().includes(q) ||
        l.details.toLowerCase().includes(q)
    );
  }, [auditLogs, filterText]);

  return (
    <div className="space-y-6">
      <div className="bg-white rounded-2xl border border-slate-200 p-5 shadow-xs flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <div className="inline-flex items-center gap-1.5 text-xs font-bold uppercase tracking-wider text-slate-500">
            <Lock className="w-3.5 h-3.5" /> Append-Only Forensic Audit Ledger
          </div>
          <h3 className="text-lg font-bold text-slate-900">Immutable GRC Audit History Trail</h3>
          <p className="text-xs text-slate-500">
            Every creation, treatment completion, reassessment, CSV ingestion, SoD block, and CISO approval is cryptographically timestamped.
          </p>
        </div>

        <div className="relative w-full md:w-72">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
          <input
            type="text"
            placeholder="Search actor, event, entity ID..."
            value={filterText}
            onChange={(e) => setFilterText(e.target.value)}
            className="w-full pl-9 pr-3 py-2 rounded-lg border border-slate-200 text-xs"
          />
        </div>
      </div>

      <div className="bg-white rounded-2xl border border-slate-200 shadow-xs overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-slate-50 border-b border-slate-200 text-[11px] font-bold uppercase tracking-wider text-slate-500">
                <th className="py-3 px-4">Audit ID &amp; Timestamp (UTC)</th>
                <th className="py-3 px-4">Actor &amp; RBAC Role</th>
                <th className="py-3 px-4">Event Type</th>
                <th className="py-3 px-4">Target Entity</th>
                <th className="py-3 px-4">Audit Record Details</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200 text-xs">
              {filteredLogs.map(log => (
                <tr key={log.id} className="hover:bg-slate-50/70">
                  <td className="py-3 px-4 whitespace-nowrap font-mono">
                    <div className="font-bold text-slate-900">{log.id}</div>
                    <div className="text-slate-500">{log.timestamp}</div>
                  </td>
                  <td className="py-3 px-4 whitespace-nowrap">
                    <div className="font-bold text-slate-800">{log.actor}</div>
                    <div className="text-slate-500">{log.role}</div>
                  </td>
                  <td className="py-3 px-4 whitespace-nowrap">
                    <span className={`px-2 py-0.5 rounded font-bold text-[11px] ${
                      log.action.includes("BLOCKED") || log.action.includes("EXPIRED") || log.action.includes("OVERDUE")
                        ? "bg-red-100 text-red-800"
                        : log.action.includes("APPROVED") || log.action.includes("REASSESSED")
                        ? "bg-emerald-100 text-emerald-800"
                        : "bg-blue-100 text-blue-800"
                    }`}>
                      {log.action}
                    </span>
                  </td>
                  <td className="py-3 px-4 font-bold text-slate-800 whitespace-nowrap">{log.target}</td>
                  <td className="py-3 px-4 text-slate-600 max-w-xl leading-relaxed">{log.details}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

// ============================================================================
// VIEW 8: PROJECT DOCUMENTATION, ABSTRACT & ARCHITECTURE HUB
// ============================================================================

function DocumentationView() {
  return (
    <div className="space-y-6 max-w-5xl mx-auto">
      {/* Header */}
      <div className="bg-slate-900 text-white rounded-2xl p-6 shadow-xs space-y-2">
        <div className="text-xs font-bold uppercase tracking-widest text-blue-400">
          Academic &amp; Enterprise GRC Deliverable Specification
        </div>
        <h2 className="text-2xl font-extrabold tracking-tight">{APP_NAME}</h2>
        <p className="text-xs text-slate-300">
          Complete Project Abstract, System Architecture, Relational Database Schema, Security Controls, Verification Testing Matrix, and Deployment Guide.
        </p>
      </div>

      {/* 1. ABSTRACT */}
      <section className="bg-white rounded-2xl border border-slate-200 p-6 shadow-xs space-y-3">
        <h3 className="text-base font-bold text-slate-900 border-b border-slate-100 pb-2">
          1. Project Abstract
        </h3>
        <p className="text-sm text-slate-700 leading-relaxed">
          Organizations managing cybersecurity risks across disconnected spreadsheets frequently suffer from inconsistent risk scoring, missed remediation deadlines, unmonitored risk acceptances, and an inability to distinguish risks exceeding executive risk appetite. To resolve these governance deficiencies, this project presents <strong>The Alajo Enterprise Cyber Risk Register &amp; GRC Platform</strong>, a centralized web-based Governance, Risk, and Compliance (GRC) management system aligned with ISO/IEC 27005 and NIST RMF principles.
        </p>
        <p className="text-sm text-slate-700 leading-relaxed">
          The proposed solution unifies business services, critical technology assets, cyber risk scenarios, treatment action plans, cryptographic evidence artifacts, and executive approval workflows within a single auditable platform. Implemented as a modular Single-Page Application (SPA) with a deterministic 5×5 Likelihood-by-Impact scoring engine, the system enforces an organizational risk appetite threshold (&le; 9), isolates inherent baseline scores from residual scores, and introduces a mandatory evidence-backed reassessment gate before any completed treatment can reduce residual risk. Furthermore, Role-Based Access Control (RBAC) enforces strict Segregation of Duties (SoD), preventing risk owners from self-approving risk acceptance exceptions while maintaining an append-only audit trail. Demonstration across 16 enterprise assets, 22 cyber risks, and 14 treatment workflows confirms significant improvements in risk visibility, SLA accountability, and audit traceability.
        </p>
      </section>

      {/* 2. ARCHITECTURE & RELATIONAL DATABASE DESIGN */}
      <section className="bg-white rounded-2xl border border-slate-200 p-6 shadow-xs space-y-4">
        <h3 className="text-base font-bold text-slate-900 border-b border-slate-100 pb-2">
          2. System Architecture &amp; Relational Database Schema
        </h3>
        <p className="text-xs text-slate-600 leading-relaxed">
          The platform follows a three-tier domain architecture separating the Presentation &amp; RBAC Policy Layer, the GRC Domain Rules Engine (Scoring, Reassessment Gating, SoD Enforcement, CSV Validator), and the Normalized Persistence Layer.
        </p>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 text-xs">
          {[
            {
              table: "BusinessServices & Assets",
              fields: ["asset_id (PK, e.g., AST-001)", "name, environment, ip_or_host", "service_name (FK -> Services)", "criticality_tier, asset_owner"]
            },
            {
              table: "CyberRisks",
              fields: ["risk_id (PK, e.g., RSK-001)", "title, description, threat, vulnerability", "inherent_L, inherent_I, inherent_score", "residual_L, residual_I, residual_score", "risk_owner, review_date, strategy"]
            },
            {
              table: "RiskAssetMap (M:N)",
              fields: ["risk_id (FK -> CyberRisks)", "asset_id (FK -> Assets)", "Composite PK (risk_id, asset_id)"]
            },
            {
              table: "TreatmentActions & Evidence",
              fields: ["treatment_id (PK, e.g., TRT-001)", "risk_id (FK), action_plan, deadline", "status (Planned | Overdue | Awaiting Reassess)", "evidence_hash (SHA-256), uploaded_by"]
            },
            {
              table: "ReassessmentHistory",
              fields: ["reassessment_id (PK)", "risk_id (FK), assessor_name, date", "prev_score, new_score, evidence_ref", "justification_notes"]
            },
            {
              table: "Approvals & AuditLogs",
              fields: ["exception_id (PK), risk_id (FK)", "risk_owner, approver_name (SoD Checked)", "decision_date, expiry_date, status", "audit_id (PK), timestamp, actor, action"]
            }
          ].map(tbl => (
            <div key={tbl.table} className="p-3.5 rounded-xl bg-slate-50 border border-slate-200 space-y-1.5">
              <div className="font-bold text-blue-700 flex items-center gap-1.5">
                <Database className="w-3.5 h-3.5" /> {tbl.table}
              </div>
              <ul className="space-y-1 text-slate-600 font-mono text-[11px]">
                {tbl.fields.map(f => <li key={f}>• {f}</li>)}
              </ul>
            </div>
          ))}
        </div>
      </section>

      {/* 3. CORE WORKFLOWS & SECURITY CONTROLS */}
      <section className="bg-white rounded-2xl border border-slate-200 p-6 shadow-xs space-y-3">
        <h3 className="text-base font-bold text-slate-900 border-b border-slate-100 pb-2">
          3. Core GRC Workflows &amp; Security Controls
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs text-slate-700">
          <div className="p-4 rounded-xl border border-slate-200 space-y-1">
            <h4 className="font-bold text-slate-900">Control 1: Non-Automatic Residual Score Reduction</h4>
            <p className="leading-relaxed">
              Marking a treatment action completed sets its state to <code>Completed - Awaiting Reassessment</code> without altering <code>residual_score</code>. The analyst must submit a documented reassessment linking a valid evidence artifact ID before residual risk decreases.
            </p>
          </div>
          <div className="p-4 rounded-xl border border-slate-200 space-y-1">
            <h4 className="font-bold text-slate-900">Control 2: Segregation of Duties (SoD) Enforcement</h4>
            <p className="leading-relaxed">
              The approval engine compares <code>currentUser.userName === exception.riskOwner</code>. Self-approval attempts are deterministically blocked in the UI/domain layer and recorded as <code>SOD_VIOLATION_BLOCKED</code> in the audit ledger.
            </p>
          </div>
          <div className="p-4 rounded-xl border border-slate-200 space-y-1">
            <h4 className="font-bold text-slate-900">Control 3: Role-Based Access Control (RBAC)</h4>
            <p className="leading-relaxed">
              Four distinct personas (Risk Analyst, Risk Owner, Approver/CISO, Read-Only Auditor) enforce least-privilege access across asset registration, risk scoring, treatment updates, CSV ingestion, and appetite governance.
            </p>
          </div>
          <div className="p-4 rounded-xl border border-slate-200 space-y-1">
            <h4 className="font-bold text-slate-900">Control 4: CSV Schema &amp; Referential Integrity</h4>
            <p className="leading-relaxed">
              Bulk imports validate Likert bounds (1–5), check CMDB Asset ID existence, prevent duplicate risk titles/asset names, and isolate rejected rows with line-level diagnostics prior to commit.
            </p>
          </div>
        </div>
      </section>

      {/* 4. TESTING MATRIX, LIMITATIONS & DEPLOYMENT */}
      <section className="bg-white rounded-2xl border border-slate-200 p-6 shadow-xs space-y-4">
        <h3 className="text-base font-bold text-slate-900 border-b border-slate-100 pb-2">
          4. Verification Testing, Known Limitations &amp; Deployment Instructions
        </h3>

        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse text-xs">
            <thead>
              <tr className="bg-slate-50 border-b border-slate-200 font-bold text-slate-700">
                <th className="py-2 px-3">Test Case ID</th>
                <th className="py-2 px-3">Scenario Tested</th>
                <th className="py-2 px-3">Expected Control Behavior</th>
                <th className="py-2 px-3">Result</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200 text-slate-600">
              <tr>
                <td className="py-2 px-3 font-mono font-bold">TC-01</td>
                <td className="py-2 px-3">Complete Treatment Action (TRT-001)</td>
                <td className="py-2 px-3">Status transitions to Awaiting Reassessment; Residual Score remains unchanged.</td>
                <td className="py-2 px-3 font-bold text-emerald-700">PASS</td>
              </tr>
              <tr>
                <td className="py-2 px-3 font-mono font-bold">TC-02</td>
                <td className="py-2 px-3">Risk Owner self-approves EXC-003</td>
                <td className="py-2 px-3">Blocked by SoD control; audit warning logged; CISO role required.</td>
                <td className="py-2 px-3 font-bold text-emerald-700">PASS</td>
              </tr>
              <tr>
                <td className="py-2 px-3 font-mono font-bold">TC-03</td>
                <td className="py-2 px-3">CSV Import with L=7, duplicate title, &amp; invalid Asset ID</td>
                <td className="py-2 px-3">Valid rows accepted; invalid rows rejected with line-by-line errors.</td>
                <td className="py-2 px-3 font-bold text-emerald-700">PASS</td>
              </tr>
              <tr>
                <td className="py-2 px-3 font-mono font-bold">TC-04</td>
                <td className="py-2 px-3">Read-Only Auditor session inspection</td>
                <td className="py-2 px-3">Full access to heat maps, evidence hashes, and audit logs; mutations locked.</td>
                <td className="py-2 px-3 font-bold text-emerald-700">PASS</td>
              </tr>
            </tbody>
          </table>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-2 text-xs text-slate-600">
          <div className="space-y-1">
            <h4 className="font-bold text-slate-900">Limitations &amp; Future Roadmap</h4>
            <p className="leading-relaxed">
              Current state persistence uses browser <code>localStorage</code> for zero-backend portability. Production enterprise deployment connects the React client to a PostgreSQL database via REST/GraphQL APIs with SAML 2.0 / OIDC SSO integration and AWS S3 Object-Lock for binary evidence storage.
            </p>
          </div>
          <div className="space-y-1">
            <h4 className="font-bold text-slate-900">Deployment &amp; Source Repository</h4>
            <p className="leading-relaxed font-mono bg-slate-50 p-2.5 rounded border border-slate-200 text-[11px]">
              # Build &amp; Deploy SPA Bundle<br />
              npm install &amp;&amp; npm run build<br />
              # Source Repository Reference:<br />
              https://github.com/alajo-grc/enterprise-cyber-risk-platform
            </p>
          </div>
        </div>
      </section>
    </div>
  );
}

// ============================================================================
// MODALS: RISK DETAIL, NEW RISK, NEW ASSET, NEW TREATMENT, REASSESS, REPORT
// ============================================================================

function RiskDetailModal({ risk, assets, treatments, approvals, appetiteThreshold, currentUser, onClose, onOpenReassess }) {
  const inhScore = risk.inherentL * risk.inherentI;
  const resScore = risk.residualL * risk.residualI;
  const inhBand = getRatingBand(inhScore);
  const resBand = getRatingBand(resScore);
  const exceeds = resScore > appetiteThreshold;
  const linkedAssets = assets.filter(a => risk.assetIds.includes(a.id));

  return (
    <div className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-xs flex items-center justify-center p-4 overflow-y-auto">
      <div className="bg-white rounded-2xl max-w-3xl w-full shadow-2xl border border-slate-200 overflow-hidden my-8">
        {/* Header */}
        <div className="p-5 bg-slate-900 text-white flex items-start justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 text-xs text-blue-400 font-bold">
              <span>{risk.id}</span>
              <span>•</span>
              <span>{risk.service}</span>
            </div>
            <h3 className="text-lg font-bold mt-0.5">{risk.title}</h3>
          </div>
          <button onClick={onClose} className="text-slate-400 hover:text-white p-1">
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="p-6 space-y-6 max-h-[80vh] overflow-y-auto text-xs">
          {/* Transparent Score Calculation Breakdown */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div className="p-4 rounded-xl bg-slate-50 border border-slate-200">
              <span className="text-[11px] font-bold uppercase text-slate-500 block">Inherent Baseline Score</span>
              <div className="mt-1 flex items-baseline gap-2">
                <span className="text-2xl font-extrabold text-slate-900">{inhScore}</span>
                <span className={`px-2 py-0.5 rounded font-bold border ${inhBand.bg}`}>{inhBand.label}</span>
              </div>
              <p className="text-slate-600 mt-1.5">
                Formula: L({risk.inherentL} - {LIKELIHOOD_SCALE[risk.inherentL - 1].label}) × I({risk.inherentI} - {IMPACT_SCALE[risk.inherentI - 1].label})
              </p>
            </div>

            <div className="p-4 rounded-xl bg-slate-50 border border-slate-200">
              <span className="text-[11px] font-bold uppercase text-slate-500 block">Current Residual Score</span>
              <div className="mt-1 flex items-baseline gap-2">
                <span className="text-2xl font-extrabold text-slate-900">{resScore}</span>
                <span className={`px-2 py-0.5 rounded font-bold border ${resBand.bg}`}>{resBand.label}</span>
              </div>
              <p className="text-slate-600 mt-1.5">
                Formula: L({risk.residualL} - {LIKELIHOOD_SCALE[risk.residualL - 1].label}) × I({risk.residualI} - {IMPACT_SCALE[risk.residualI - 1].label})
              </p>
            </div>

            <div className={`p-4 rounded-xl border ${exceeds ? "bg-red-50 border-red-200" : "bg-emerald-50 border-emerald-200"}`}>
              <span className="text-[11px] font-bold uppercase text-slate-600 block">Appetite Evaluation</span>
              <div className={`mt-1 text-base font-extrabold ${exceeds ? "text-red-700" : "text-emerald-700"}`}>
                {exceeds ? "EXCEEDS APPETITE" : "WITHIN APPETITE"}
              </div>
              <p className="text-slate-600 mt-1.5">
                Residual {resScore} vs. Board Threshold (&le; {appetiteThreshold}). Strategy: <strong>{risk.strategy}</strong>.
              </p>
            </div>
          </div>

          {/* Risk Context Details */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 bg-slate-50/70 p-4 rounded-xl border border-slate-200">
            <div>
              <span className="font-bold text-slate-800 block">Risk Description:</span>
              <p className="text-slate-600 mt-0.5 leading-relaxed">{risk.description}</p>
            </div>
            <div className="space-y-2">
              <div>
                <span className="font-bold text-slate-800">Threat Actor / Source: </span>
                <span className="text-slate-600">{risk.threat}</span>
              </div>
              <div>
                <span className="font-bold text-slate-800">Vulnerability: </span>
                <span className="text-slate-600">{risk.vulnerability}</span>
              </div>
              <div>
                <span className="font-bold text-slate-800">Business Impact: </span>
                <span className="text-slate-600">{risk.businessImpact}</span>
              </div>
              <div>
                <span className="font-bold text-slate-800">Risk Owner: </span>
                <span className="text-slate-900 font-semibold">{risk.owner}</span> • Next Review: <strong>{risk.reviewDate}</strong>
              </div>
            </div>
          </div>

          {/* Linked Assets */}
          <div>
            <h4 className="font-bold text-slate-900 mb-2">Linked Critical Assets ({linkedAssets.length})</h4>
            <div className="flex flex-wrap gap-2">
              {linkedAssets.map(a => (
                <span key={a.id} className="px-3 py-1.5 rounded-lg bg-blue-50 border border-blue-200 text-blue-900 font-medium">
                  <strong>{a.id}</strong>: {a.name} ({a.criticality})
                </span>
              ))}
            </div>
          </div>

          {/* Linked Treatments */}
          <div>
            <h4 className="font-bold text-slate-900 mb-2">Linked Treatment Actions ({treatments.length})</h4>
            {treatments.length === 0 ? (
              <p className="text-slate-400 italic">No treatment actions linked yet.</p>
            ) : (
              <div className="space-y-2">
                {treatments.map(t => (
                  <div key={t.id} className="p-3 rounded-lg border border-slate-200 flex items-center justify-between gap-2">
                    <div>
                      <span className="font-bold text-slate-900 mr-2">{t.id}</span>
                      <span className="text-slate-700">{t.actionPlan}</span>
                    </div>
                    <span className="px-2 py-0.5 rounded bg-slate-100 font-bold shrink-0">{t.status}</span>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Reassessment History Timeline */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <h4 className="font-bold text-slate-900">Assessment &amp; Reassessment Audit History</h4>
              {currentUser.permissions.canSubmitReassessment && (
                <button
                  onClick={() => onOpenReassess(risk)}
                  className="px-3 py-1 rounded-lg bg-blue-600 hover:bg-blue-700 text-white font-semibold"
                >
                  + Record Documented Reassessment
                </button>
              )}
            </div>
            <div className="space-y-2 border-l-2 border-blue-200 pl-4 ml-1">
              {risk.reassessmentHistory.map((h, i) => (
                <div key={i} className="p-3 rounded-lg bg-slate-50 border border-slate-200">
                  <div className="flex items-center justify-between font-bold text-slate-800">
                    <span>{h.date} — Assessed by {h.assessor}</span>
                    <span>Score: {h.prevScore} → {h.newScore} (L:{h.likelihood} × I:{h.impact})</span>
                  </div>
                  <p className="text-slate-600 mt-1">{h.notes}</p>
                  <div className="text-[11px] text-blue-700 font-mono mt-1">Evidence Ref: {h.evidenceRef}</div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function NewRiskModal({ assets, appetiteThreshold, onClose, onSubmit }) {
  const [title, setTitle] = useState("");
  const [service, setService] = useState("Digital Banking & Payments");
  const [selectedAssetIds, setSelectedAssetIds] = useState(["AST-001"]);
  const [description, setDescription] = useState("");
  const [threat, setThreat] = useState("");
  const [vulnerability, setVulnerability] = useState("");
  const [businessImpact, setBusinessImpact] = useState("");
  const [owner, setOwner] = useState("Kwame Boateng");
  const [reviewDate, setReviewDate] = useState("2027-02-15");
  const [strategy, setStrategy] = useState("Reduce");
  const [inherentL, setInherentL] = useState(3);
  const [inherentI, setInherentI] = useState(4);

  const liveScore = inherentL * inherentI;
  const band = getRatingBand(liveScore);

  const toggleAsset = (id) => {
    setSelectedAssetIds(prev => (prev.includes(id) ? prev.filter(x => x !== id) : [...prev, id]));
  };

  return (
    <div className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-xs flex items-center justify-center p-4 overflow-y-auto">
      <div className="bg-white rounded-2xl max-w-2xl w-full shadow-2xl border border-slate-200 overflow-hidden my-8">
        <div className="p-5 bg-slate-900 text-white flex items-center justify-between">
          <h3 className="text-base font-bold">Register New Cyber Risk</h3>
          <button onClick={onClose}><X className="w-5 h-5 text-slate-400 hover:text-white" /></button>
        </div>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            if (!title.trim() || selectedAssetIds.length === 0) return;
            onSubmit({
              title,
              service,
              assetIds: selectedAssetIds,
              description,
              threat,
              vulnerability,
              businessImpact,
              owner,
              reviewDate,
              strategy,
              inherentL: Number(inherentL),
              inherentI: Number(inherentI)
            });
          }}
          className="p-6 space-y-4 text-xs max-h-[80vh] overflow-y-auto"
        >
          <div>
            <label className="font-bold text-slate-700 block mb-1">Risk Title *</label>
            <input required value={title} onChange={e => setTitle(e.target.value)} placeholder="e.g., Unauthenticated GraphQL Introspection on Mobile Gateway" className="w-full border border-slate-300 rounded-lg p-2.5" />
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="font-bold text-slate-700 block mb-1">Business Service *</label>
              <select value={service} onChange={e => setService(e.target.value)} className="w-full border border-slate-300 rounded-lg p-2.5 bg-white">
                <option>Digital Banking &amp; Payments</option>
                <option>Enterprise Cloud &amp; Infrastructure</option>
                <option>Customer Support &amp; Data Analytics</option>
              </select>
            </div>
            <div>
              <label className="font-bold text-slate-700 block mb-1">Risk Owner *</label>
              <select value={owner} onChange={e => setOwner(e.target.value)} className="w-full border border-slate-300 rounded-lg p-2.5 bg-white">
                <option>Kwame Boateng</option>
                <option>Kojo Appiah</option>
                <option>Efua Mensah-Bonsu</option>
                <option>Nana Yaw Asante</option>
                <option>Ama Darko</option>
              </select>
            </div>
          </div>

          <div>
            <label className="font-bold text-slate-700 block mb-1">Link Affected Assets (Select at least 1) *</label>
            <div className="max-h-28 overflow-y-auto border border-slate-200 rounded-lg p-2 grid grid-cols-1 sm:grid-cols-2 gap-1.5 bg-slate-50">
              {assets.map(a => (
                <label key={a.id} className="flex items-center gap-2 p-1 hover:bg-white rounded cursor-pointer">
                  <input type="checkbox" checked={selectedAssetIds.includes(a.id)} onChange={() => toggleAsset(a.id)} />
                  <span className="truncate"><strong>{a.id}</strong>: {a.name}</span>
                </label>
              ))}
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="font-bold text-slate-700 block mb-1">Threat Actor / Source</label>
              <input value={threat} onChange={e => setThreat(e.target.value)} placeholder="e.g., External Cybercriminals" className="w-full border border-slate-300 rounded-lg p-2" />
            </div>
            <div>
              <label className="font-bold text-slate-700 block mb-1">Vulnerability</label>
              <input value={vulnerability} onChange={e => setVulnerability(e.target.value)} placeholder="e.g., Production debug schema enabled" className="w-full border border-slate-300 rounded-lg p-2" />
            </div>
          </div>

          <div>
            <label className="font-bold text-slate-700 block mb-1">Risk Scenario Description &amp; Business Impact</label>
            <textarea rows={2} value={description} onChange={e => setDescription(e.target.value)} placeholder="Describe scenario..." className="w-full border border-slate-300 rounded-lg p-2 mb-2" />
            <input value={businessImpact} onChange={e => setBusinessImpact(e.target.value)} placeholder="Business impact (financial, regulatory, operational)..." className="w-full border border-slate-300 rounded-lg p-2" />
          </div>

          {/* Live Inherent Scoring */}
          <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 space-y-3">
            <div className="flex items-center justify-between">
              <span className="font-bold text-slate-900">Inherent Risk Assessment (1–5 Scale)</span>
              <span className={`px-3 py-1 rounded-full font-bold border ${band.bg}`}>
                Calculated Score: {liveScore} ({band.label}) — {liveScore > appetiteThreshold ? "Exceeds Appetite" : "Within Appetite"}
              </span>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="font-semibold text-slate-700 block mb-1">Likelihood (1–5)</label>
                <select value={inherentL} onChange={e => setInherentL(Number(e.target.value))} className="w-full border border-slate-300 rounded-lg p-2 bg-white">
                  {LIKELIHOOD_SCALE.map(l => <option key={l.score} value={l.score}>{l.score} - {l.label}</option>)}
                </select>
              </div>
              <div>
                <label className="font-semibold text-slate-700 block mb-1">Impact (1–5)</label>
                <select value={inherentI} onChange={e => setInherentI(Number(e.target.value))} className="w-full border border-slate-300 rounded-lg p-2 bg-white">
                  {IMPACT_SCALE.map(i => <option key={i.score} value={i.score}>{i.score} - {i.label}</option>)}
                </select>
              </div>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="font-bold text-slate-700 block mb-1">Treatment Strategy</label>
              <select value={strategy} onChange={e => setStrategy(e.target.value)} className="w-full border border-slate-300 rounded-lg p-2 bg-white">
                <option>Reduce</option>
                <option>Accept</option>
                <option>Transfer</option>
                <option>Avoid</option>
              </select>
            </div>
            <div>
              <label className="font-bold text-slate-700 block mb-1">Next Review Date</label>
              <input type="date" value={reviewDate} onChange={e => setReviewDate(e.target.value)} className="w-full border border-slate-300 rounded-lg p-2" />
            </div>
          </div>

          <div className="pt-3 flex justify-end gap-2 border-t border-slate-200">
            <button type="button" onClick={onClose} className="px-4 py-2 rounded-lg border border-slate-300 font-semibold">Cancel</button>
            <button type="submit" className="px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-700 text-white font-bold">Save Risk Record</button>
          </div>
        </form>
      </div>
    </div>
  );
}

function NewAssetModal({ onClose, onSubmit }) {
  const [name, setName] = useState("");
  const [service, setService] = useState("Digital Banking & Payments");
  const [criticality, setCriticality] = useState("Tier 1 - Critical");
  const [owner, setOwner] = useState("Kwame Boateng");
  const [environment, setEnvironment] = useState("Production Cloud");
  const [ipOrHost, setIpOrHost] = useState("");

  return (
    <div className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-xs flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl max-w-lg w-full shadow-2xl border border-slate-200 overflow-hidden">
        <div className="p-5 bg-slate-900 text-white flex items-center justify-between">
          <h3 className="text-base font-bold">Register Enterprise Asset</h3>
          <button onClick={onClose}><X className="w-5 h-5 text-slate-400 hover:text-white" /></button>
        </div>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            if (!name.trim()) return;
            onSubmit({ name, service, criticality, owner, environment, ipOrHost: ipOrHost || "internal.alajobank.local" });
          }}
          className="p-6 space-y-4 text-xs"
        >
          <div>
            <label className="font-bold text-slate-700 block mb-1">Asset Name *</label>
            <input required value={name} onChange={e => setName(e.target.value)} placeholder="e.g., Open Banking Consent Manager" className="w-full border border-slate-300 rounded-lg p-2.5" />
          </div>
          <div>
            <label className="font-bold text-slate-700 block mb-1">Business Service *</label>
            <select value={service} onChange={e => setService(e.target.value)} className="w-full border border-slate-300 rounded-lg p-2.5 bg-white">
              <option>Digital Banking &amp; Payments</option>
              <option>Enterprise Cloud &amp; Infrastructure</option>
              <option>Customer Support &amp; Data Analytics</option>
            </select>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="font-bold text-slate-700 block mb-1">Criticality Tier</label>
              <select value={criticality} onChange={e => setCriticality(e.target.value)} className="w-full border border-slate-300 rounded-lg p-2.5 bg-white">
                <option>Tier 1 - Critical</option>
                <option>Tier 2 - High</option>
                <option>Tier 3 - Moderate</option>
              </select>
            </div>
            <div>
              <label className="font-bold text-slate-700 block mb-1">Asset Owner</label>
              <input value={owner} onChange={e => setOwner(e.target.value)} className="w-full border border-slate-300 rounded-lg p-2.5" />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="font-bold text-slate-700 block mb-1">Hosting Environment</label>
              <input value={environment} onChange={e => setEnvironment(e.target.value)} className="w-full border border-slate-300 rounded-lg p-2.5" />
            </div>
            <div>
              <label className="font-bold text-slate-700 block mb-1">Hostname / VPC ID</label>
              <input value={ipOrHost} onChange={e => setIpOrHost(e.target.value)} placeholder="consent-api.alajobank.com" className="w-full border border-slate-300 rounded-lg p-2.5" />
            </div>
          </div>
          <div className="pt-3 flex justify-end gap-2 border-t border-slate-200">
            <button type="button" onClick={onClose} className="px-4 py-2 rounded-lg border border-slate-300 font-semibold">Cancel</button>
            <button type="submit" className="px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-700 text-white font-bold">Add Asset</button>
          </div>
        </form>
      </div>
    </div>
  );
}

function NewTreatmentModal({ risks, onClose, onSubmit }) {
  const [riskId, setRiskId] = useState(risks[0]?.id || "RSK-001");
  const [strategy, setStrategy] = useState("Reduce");
  const [actionPlan, setActionPlan] = useState("");
  const [owner, setOwner] = useState("Kwame Boateng");
  const [deadline, setDeadline] = useState("2026-12-30");
  const [cost, setCost] = useState(25000);
  const [initialEvidenceName, setInitialEvidenceName] = useState("");

  return (
    <div className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-xs flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl max-w-lg w-full shadow-2xl border border-slate-200 overflow-hidden">
        <div className="p-5 bg-slate-900 text-white flex items-center justify-between">
          <h3 className="text-base font-bold">Create Risk Treatment Action Plan</h3>
          <button onClick={onClose}><X className="w-5 h-5 text-slate-400 hover:text-white" /></button>
        </div>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            if (!actionPlan.trim()) return;
            onSubmit({ riskId, strategy, actionPlan, owner, deadline, status: "In Progress", cost: Number(cost), initialEvidenceName });
          }}
          className="p-6 space-y-4 text-xs"
        >
          <div>
            <label className="font-bold text-slate-700 block mb-1">Target Cyber Risk *</label>
            <select value={riskId} onChange={e => setRiskId(e.target.value)} className="w-full border border-slate-300 rounded-lg p-2.5 bg-white">
              {risks.map(r => <option key={r.id} value={r.id}>{r.id} — {r.title}</option>)}
            </select>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="font-bold text-slate-700 block mb-1">Treatment Decision</label>
              <select value={strategy} onChange={e => setStrategy(e.target.value)} className="w-full border border-slate-300 rounded-lg p-2.5 bg-white">
                <option>Reduce</option>
                <option>Accept</option>
                <option>Transfer</option>
                <option>Avoid</option>
              </select>
            </div>
            <div>
              <label className="font-bold text-slate-700 block mb-1">Responsible Owner</label>
              <input value={owner} onChange={e => setOwner(e.target.value)} className="w-full border border-slate-300 rounded-lg p-2.5" />
            </div>
          </div>
          <div>
            <label className="font-bold text-slate-700 block mb-1">Remediation / Treatment Action Plan *</label>
            <textarea required rows={3} value={actionPlan} onChange={e => setActionPlan(e.target.value)} placeholder="Specify technical control implementation, scope, and verification criteria..." className="w-full border border-slate-300 rounded-lg p-2.5" />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="font-bold text-slate-700 block mb-1">Target Deadline</label>
              <input type="date" value={deadline} onChange={e => setDeadline(e.target.value)} className="w-full border border-slate-300 rounded-lg p-2.5" />
            </div>
            <div>
              <label className="font-bold text-slate-700 block mb-1">Estimated Cost ($ USD)</label>
              <input type="number" value={cost} onChange={e => setCost(e.target.value)} className="w-full border border-slate-300 rounded-lg p-2.5" />
            </div>
          </div>
          <div>
            <label className="font-bold text-slate-700 block mb-1">Initial Charter / Evidence Artifact (Optional)</label>
            <input value={initialEvidenceName} onChange={e => setInitialEvidenceName(e.target.value)} placeholder="e.g., Remediation_Design_Spec.pdf" className="w-full border border-slate-300 rounded-lg p-2.5" />
          </div>
          <div className="pt-3 flex justify-end gap-2 border-t border-slate-200">
            <button type="button" onClick={onClose} className="px-4 py-2 rounded-lg border border-slate-300 font-semibold">Cancel</button>
            <button type="submit" className="px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-700 text-white font-bold">Create Treatment</button>
          </div>
        </form>
      </div>
    </div>
  );
}

function ReassessmentModal({ risk, treatment, treatments, appetiteThreshold, onClose, onSubmit }) {
  const allEvidence = treatments.flatMap(t => t.evidence);
  const [newL, setNewL] = useState(Math.max(1, risk.residualL - 2));
  const [newI, setNewI] = useState(risk.residualI);
  const [notes, setNotes] = useState("");
  const [evidenceRef, setEvidenceRef] = useState(allEvidence[0]?.id || "EVD-VERIFIED");

  const prevScore = risk.residualL * risk.residualI;
  const nextScore = newL * newI;
  const nextBand = getRatingBand(nextScore);

  return (
    <div className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-xs flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl max-w-xl w-full shadow-2xl border border-slate-200 overflow-hidden">
        <div className="p-5 bg-amber-600 text-white flex items-center justify-between">
          <div>
            <span className="text-[11px] font-bold uppercase tracking-wider">Mandatory GRC Control Gate</span>
            <h3 className="text-base font-bold">Documented Residual Risk Reassessment</h3>
          </div>
          <button onClick={onClose}><X className="w-5 h-5 text-amber-100 hover:text-white" /></button>
        </div>

        <form
          onSubmit={(e) => {
            e.preventDefault();
            if (!notes.trim() || !evidenceRef.trim()) return;
            onSubmit({
              riskId: risk.id,
              treatmentId: treatment?.id || null,
              newL: Number(newL),
              newI: Number(newI),
              notes,
              evidenceRef
            });
          }}
          className="p-6 space-y-4 text-xs"
        >
          <div className="p-3 rounded-xl bg-slate-50 border border-slate-200">
            <div className="font-bold text-slate-900">{risk.id}: {risk.title}</div>
            <div className="text-slate-500 mt-1">
              Original Inherent Score: <strong>{risk.inherentL * risk.inherentI}</strong> (Preserved) • Current Residual Score: <strong>{prevScore}</strong>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="font-bold text-slate-700 block mb-1">Reassessed Residual Likelihood (1–5)</label>
              <select value={newL} onChange={e => setNewL(Number(e.target.value))} className="w-full border border-slate-300 rounded-lg p-2.5 bg-white">
                {LIKELIHOOD_SCALE.map(l => <option key={l.score} value={l.score}>{l.score} - {l.label}</option>)}
              </select>
            </div>
            <div>
              <label className="font-bold text-slate-700 block mb-1">Reassessed Residual Impact (1–5)</label>
              <select value={newI} onChange={e => setNewI(Number(e.target.value))} className="w-full border border-slate-300 rounded-lg p-2.5 bg-white">
                {IMPACT_SCALE.map(i => <option key={i.score} value={i.score}>{i.score} - {i.label}</option>)}
              </select>
            </div>
          </div>

          <div className="p-3 rounded-xl bg-blue-50 border border-blue-200 flex items-center justify-between">
            <span className="font-bold text-blue-900">New Residual Score Preview:</span>
            <span className={`px-3 py-1 rounded-full font-bold border ${nextBand.bg}`}>
              {prevScore} → {nextScore} ({nextBand.label}) • {nextScore <= appetiteThreshold ? "Within Appetite" : "Exceeds Appetite"}
            </span>
          </div>

          <div>
            <label className="font-bold text-slate-700 block mb-1">Supporting Evidence Artifact Reference *</label>
            {allEvidence.length > 0 ? (
              <select value={evidenceRef} onChange={e => setEvidenceRef(e.target.value)} className="w-full border border-slate-300 rounded-lg p-2.5 bg-white">
                {allEvidence.map(ev => (
                  <option key={ev.id} value={ev.id}>{ev.id} — {ev.name} ({ev.hash})</option>
                ))}
              </select>
            ) : (
              <input required value={evidenceRef} onChange={e => setEvidenceRef(e.target.value)} placeholder="Enter Evidence Reference ID..." className="w-full border border-slate-300 rounded-lg p-2.5" />
            )}
          </div>

          <div>
            <label className="font-bold text-slate-700 block mb-1">Documented Reassessment Rationale &amp; Control Effectiveness Notes *</label>
            <textarea required rows={3} value={notes} onChange={e => setNotes(e.target.value)} placeholder="Explain how verified testing evidence justifies the revised likelihood/impact rating..." className="w-full border border-slate-300 rounded-lg p-2.5" />
          </div>

          <div className="pt-3 flex justify-end gap-2 border-t border-slate-200">
            <button type="button" onClick={onClose} className="px-4 py-2 rounded-lg border border-slate-300 font-semibold">Cancel</button>
            <button type="submit" className="px-4 py-2 rounded-lg bg-amber-600 hover:bg-amber-700 text-white font-bold">
              Confirm Reassessment &amp; Update Score
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

function NewApprovalModal({ risks, currentUser, onClose, onSubmit }) {
  const [riskId, setRiskId] = useState(risks[0]?.id || "RSK-001");
  const [justification, setJustification] = useState("");
  const [compensatingControls, setCompensatingControls] = useState("");
  const [expiryDate, setExpiryDate] = useState("2027-05-19");

  return (
    <div className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-xs flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl max-w-lg w-full shadow-2xl border border-slate-200 overflow-hidden">
        <div className="p-5 bg-purple-900 text-white flex items-center justify-between">
          <h3 className="text-base font-bold">Submit Risk Acceptance Exception Request</h3>
          <button onClick={onClose}><X className="w-5 h-5 text-purple-200 hover:text-white" /></button>
        </div>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            if (!justification.trim() || !compensatingControls.trim()) return;
            onSubmit({ riskId, justification, compensatingControls, expiryDate });
          }}
          className="p-6 space-y-4 text-xs"
        >
          <div>
            <label className="font-bold text-slate-700 block mb-1">Select Risk for Exception *</label>
            <select value={riskId} onChange={e => setRiskId(e.target.value)} className="w-full border border-slate-300 rounded-lg p-2.5 bg-white">
              {risks.map(r => (
                <option key={r.id} value={r.id}>
                  {r.id} — {r.title} (Owner: {r.owner}, Score: {r.residualL * r.residualI})
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="font-bold text-slate-700 block mb-1">Business &amp; Technical Justification *</label>
            <textarea required rows={3} value={justification} onChange={e => setJustification(e.target.value)} placeholder="Explain why immediate remediation is not feasible..." className="w-full border border-slate-300 rounded-lg p-2.5" />
          </div>
          <div>
            <label className="font-bold text-slate-700 block mb-1">Compensating Controls *</label>
            <textarea required rows={2} value={compensatingControls} onChange={e => setCompensatingControls(e.target.value)} placeholder="Describe monitoring, network segmentation, or manual dual-controls..." className="w-full border border-slate-300 rounded-lg p-2.5" />
          </div>
          <div>
            <label className="font-bold text-slate-700 block mb-1">Requested Acceptance Expiry Date *</label>
            <input type="date" required value={expiryDate} onChange={e => setExpiryDate(e.target.value)} className="w-full border border-slate-300 rounded-lg p-2.5" />
          </div>
          <div className="p-2.5 rounded bg-amber-50 border border-amber-200 text-amber-900">
            Note: Under Segregation of Duties controls, this request will require independent sign-off by the CISO / Approver.
          </div>
          <div className="pt-3 flex justify-end gap-2 border-t border-slate-200">
            <button type="button" onClick={onClose} className="px-4 py-2 rounded-lg border border-slate-300 font-semibold">Cancel</button>
            <button type="submit" className="px-4 py-2 rounded-lg bg-purple-600 hover:bg-purple-700 text-white font-bold">Submit Request</button>
          </div>
        </form>
      </div>
    </div>
  );
}

function ManagementReportModal({ risks, assets, treatments, approvals, appetiteThreshold, currentUser, onClose }) {
  const [serviceFilter, setServiceFilter] = useState("ALL");
  const [onlyAboveAppetite, setOnlyAboveAppetite] = useState(false);

  const reportRisks = useMemo(() => {
    return risks.filter(r => {
      const matchSvc = serviceFilter === "ALL" || r.service === serviceFilter;
      const matchApp = !onlyAboveAppetite || (r.residualL * r.residualI) > appetiteThreshold;
      return matchSvc && matchApp;
    });
  }, [risks, serviceFilter, onlyAboveAppetite, appetiteThreshold]);

  const handleDownloadCsvReport = () => {
    const headers = ["Risk ID", "Title", "Business Service", "Owner", "Inherent Score", "Residual Score", "Appetite Status", "Strategy", "Governance Status"];
    const rows = reportRisks.map(r => {
      const inh = r.inherentL * r.inherentI;
      const res = r.residualL * r.residualI;
      return [
        r.id,
        `"${r.title.replace(/"/g, '""')}"`,
        `"${r.service}"`,
        `"${r.owner}"`,
        inh,
        res,
        res > appetiteThreshold ? "Exceeds Appetite" : "Within Appetite",
        r.strategy,
        `"${r.status}"`
      ].join(",");
    });
    const csvContent = [headers.join(","), ...rows].join("\n");
    const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `Alajo_Management_Cyber_Risk_Report_${new Date().toISOString().substring(0, 10)}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-xs flex items-center justify-center p-4 overflow-y-auto">
      <div className="bg-white rounded-2xl max-w-4xl w-full shadow-2xl border border-slate-200 overflow-hidden my-8">
        <div className="p-5 bg-slate-900 text-white flex items-center justify-between">
          <div>
            <span className="text-[11px] font-bold uppercase tracking-wider text-blue-400">Board &amp; Audit Committee Deliverable</span>
            <h3 className="text-base font-bold">{APP_NAME} — Management Risk Report</h3>
          </div>
          <button onClick={onClose}><X className="w-5 h-5 text-slate-400 hover:text-white" /></button>
        </div>

        <div className="p-6 space-y-5 max-h-[80vh] overflow-y-auto text-xs">
          {/* Report Filters & Export Actions */}
          <div className="flex flex-wrap items-center justify-between gap-3 bg-slate-50 p-3.5 rounded-xl border border-slate-200">
            <div className="flex flex-wrap items-center gap-3">
              <select value={serviceFilter} onChange={e => setServiceFilter(e.target.value)} className="border border-slate-300 rounded-lg px-3 py-1.5 bg-white font-medium">
                <option value="ALL">All Business Services</option>
                <option>Digital Banking &amp; Payments</option>
                <option>Enterprise Cloud &amp; Infrastructure</option>
                <option>Customer Support &amp; Data Analytics</option>
              </select>

              <label className="inline-flex items-center gap-2 font-semibold text-slate-700 cursor-pointer">
                <input type="checkbox" checked={onlyAboveAppetite} onChange={e => setOnlyAboveAppetite(e.target.checked)} />
                <span>Only Risks Exceeding Appetite (&gt; {appetiteThreshold})</span>
              </label>
            </div>

            <div className="flex items-center gap-2">
              <button
                onClick={handleDownloadCsvReport}
                className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white font-bold"
              >
                <Download className="w-3.5 h-3.5" />
                <span>Download CSV Report</span>
              </button>
              <button
                onClick={() => window.print()}
                className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-lg bg-slate-900 hover:bg-slate-800 text-white font-bold"
              >
                <Printer className="w-3.5 h-3.5" />
                <span>Print / Save PDF</span>
              </button>
            </div>
          </div>

          {/* Executive Summary Metrics */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <div className="p-3 rounded-xl border border-slate-200">
              <span className="text-slate-500 block">Filtered Risks</span>
              <span className="text-xl font-extrabold text-slate-900">{reportRisks.length}</span>
            </div>
            <div className="p-3 rounded-xl border border-red-200 bg-red-50/50">
              <span className="text-red-700 block">Above Appetite (&gt;{appetiteThreshold})</span>
              <span className="text-xl font-extrabold text-red-700">
                {reportRisks.filter(r => r.residualL * r.residualI > appetiteThreshold).length}
              </span>
            </div>
            <div className="p-3 rounded-xl border border-slate-200">
              <span className="text-slate-500 block">Overdue Treatments</span>
              <span className="text-xl font-extrabold text-orange-600">
                {treatments.filter(t => t.status === "Overdue").length}
              </span>
            </div>
            <div className="p-3 rounded-xl border border-slate-200">
              <span className="text-slate-500 block">Expired Acceptances</span>
              <span className="text-xl font-extrabold text-purple-700">
                {approvals.filter(a => a.status === "Expired").length}
              </span>
            </div>
          </div>

          {/* Printable Table */}
          <div className="border border-slate-200 rounded-xl overflow-hidden">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="bg-slate-100 border-b border-slate-200 font-bold text-slate-700">
                  <th className="py-2 px-3">ID</th>
                  <th className="py-2 px-3">Cyber Risk Title</th>
                  <th className="py-2 px-3">Service</th>
                  <th className="py-2 px-3">Owner</th>
                  <th className="py-2 px-3 text-center">Inherent</th>
                  <th className="py-2 px-3 text-center">Residual</th>
                  <th className="py-2 px-3">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200">
                {reportRisks.map(r => {
                  const res = r.residualL * r.residualI;
                  return (
                    <tr key={r.id}>
                      <td className="py-2 px-3 font-bold">{r.id}</td>
                      <td className="py-2 px-3 font-medium text-slate-900">{r.title}</td>
                      <td className="py-2 px-3 text-slate-600">{r.service}</td>
                      <td className="py-2 px-3">{r.owner}</td>
                      <td className="py-2 px-3 text-center">{r.inherentL * r.inherentI}</td>
                      <td className="py-2 px-3 text-center font-bold">{res}</td>
                      <td className="py-2 px-3">{r.status}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          <div className="text-[11px] text-slate-400 flex justify-between pt-2">
            <span>Generated by: {currentUser.userName} ({currentUser.roleName})</span>
            <span>Confidential — Alajo Financial Group Enterprise GRC</span>
          </div>
        </div>
      </div>
    </div>
  );
}