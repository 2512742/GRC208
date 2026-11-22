"""Reference catalogue: framework controls and regulatory obligations.

Controls: framework IDs with **our own short titles** (ISO/IEC 27001 text is copyrighted, so
titles are paraphrased). NIST CSF 2.0 is listed at category level; CIS Controls v8.1 at control
level; ISO/IEC 27001:2022 Annex A as a subset relevant to The Alajo's risks.

Obligations: our own reference codes with plain-language summaries. The exact clause or section
of each source must be confirmed by WS2 (Maria Nalima) before the report cites it; until then
`source_note` says so. WS2 extends this file; `python -m app.cli load-reference` applies changes.
"""

from __future__ import annotations

from app.models.enums import Framework, Regime

TO_VERIFY = "Source clause to be confirmed by WS2 before citing"

CONTROLS: list[tuple[Framework, str, str]] = [
    # NIST Cybersecurity Framework 2.0, categories
    (Framework.NIST_CSF_2, "GV.OC", "Organizational context understood"),
    (Framework.NIST_CSF_2, "GV.RM", "Risk management strategy, appetite and tolerance"),
    (Framework.NIST_CSF_2, "GV.RR", "Cybersecurity roles, responsibilities and authorities"),
    (Framework.NIST_CSF_2, "GV.PO", "Cybersecurity policy"),
    (Framework.NIST_CSF_2, "GV.OV", "Oversight of the risk management strategy"),
    (Framework.NIST_CSF_2, "GV.SC", "Cybersecurity supply chain risk management"),
    (Framework.NIST_CSF_2, "ID.AM", "Asset management"),
    (Framework.NIST_CSF_2, "ID.RA", "Risk assessment"),
    (Framework.NIST_CSF_2, "ID.IM", "Improvement"),
    (Framework.NIST_CSF_2, "PR.AA", "Identity management, authentication and access control"),
    (Framework.NIST_CSF_2, "PR.AT", "Awareness and training"),
    (Framework.NIST_CSF_2, "PR.DS", "Data security"),
    (Framework.NIST_CSF_2, "PR.PS", "Platform security"),
    (Framework.NIST_CSF_2, "PR.IR", "Technology infrastructure resilience"),
    (Framework.NIST_CSF_2, "DE.CM", "Continuous monitoring"),
    (Framework.NIST_CSF_2, "DE.AE", "Adverse event analysis"),
    (Framework.NIST_CSF_2, "RS.MA", "Incident management"),
    (Framework.NIST_CSF_2, "RS.AN", "Incident analysis"),
    (Framework.NIST_CSF_2, "RS.CO", "Incident response reporting and communication"),
    (Framework.NIST_CSF_2, "RS.MI", "Incident mitigation"),
    (Framework.NIST_CSF_2, "RC.RP", "Incident recovery plan execution"),
    (Framework.NIST_CSF_2, "RC.CO", "Incident recovery communication"),
    # CIS Critical Security Controls v8.1
    (Framework.CIS_8_1, "CIS-01", "Inventory and control of enterprise assets"),
    (Framework.CIS_8_1, "CIS-02", "Inventory and control of software assets"),
    (Framework.CIS_8_1, "CIS-03", "Data protection"),
    (Framework.CIS_8_1, "CIS-04", "Secure configuration of assets and software"),
    (Framework.CIS_8_1, "CIS-05", "Account management"),
    (Framework.CIS_8_1, "CIS-06", "Access control management"),
    (Framework.CIS_8_1, "CIS-07", "Continuous vulnerability management"),
    (Framework.CIS_8_1, "CIS-08", "Audit log management"),
    (Framework.CIS_8_1, "CIS-09", "Email and web browser protections"),
    (Framework.CIS_8_1, "CIS-10", "Malware defenses"),
    (Framework.CIS_8_1, "CIS-11", "Data recovery"),
    (Framework.CIS_8_1, "CIS-12", "Network infrastructure management"),
    (Framework.CIS_8_1, "CIS-13", "Network monitoring and defense"),
    (Framework.CIS_8_1, "CIS-14", "Security awareness and skills training"),
    (Framework.CIS_8_1, "CIS-15", "Service provider management"),
    (Framework.CIS_8_1, "CIS-16", "Application software security"),
    (Framework.CIS_8_1, "CIS-17", "Incident response management"),
    (Framework.CIS_8_1, "CIS-18", "Penetration testing"),
    # ISO/IEC 27001:2022 Annex A (subset; titles paraphrased)
    (Framework.ISO_27001_2022, "A.5.3", "Separate conflicting duties"),
    (Framework.ISO_27001_2022, "A.5.7", "Collect and use threat intelligence"),
    (Framework.ISO_27001_2022, "A.5.9", "Keep an inventory of information assets"),
    (Framework.ISO_27001_2022, "A.5.15", "Control access to information and systems"),
    (Framework.ISO_27001_2022, "A.5.17", "Manage authentication secrets"),
    (Framework.ISO_27001_2022, "A.5.19", "Manage security in supplier relationships"),
    (Framework.ISO_27001_2022, "A.5.23", "Secure the use of cloud services"),
    (Framework.ISO_27001_2022, "A.5.24", "Plan and prepare for incident management"),
    (Framework.ISO_27001_2022, "A.5.30", "Keep ICT ready for business continuity"),
    (Framework.ISO_27001_2022, "A.5.34", "Protect privacy and personal data"),
    (Framework.ISO_27001_2022, "A.6.3", "Security awareness, education and training"),
    (Framework.ISO_27001_2022, "A.8.2", "Restrict and manage privileged access"),
    (Framework.ISO_27001_2022, "A.8.3", "Restrict access to information"),
    (Framework.ISO_27001_2022, "A.8.5", "Use secure authentication"),
    (Framework.ISO_27001_2022, "A.8.7", "Protect against malware"),
    (Framework.ISO_27001_2022, "A.8.8", "Manage technical vulnerabilities"),
    (Framework.ISO_27001_2022, "A.8.9", "Manage secure configurations"),
    (Framework.ISO_27001_2022, "A.8.11", "Mask sensitive data"),
    (Framework.ISO_27001_2022, "A.8.12", "Prevent data leakage"),
    (Framework.ISO_27001_2022, "A.8.13", "Back up information"),
    (Framework.ISO_27001_2022, "A.8.15", "Record security-relevant logs"),
    (Framework.ISO_27001_2022, "A.8.16", "Monitor for anomalous activity"),
    (Framework.ISO_27001_2022, "A.8.20", "Secure networks"),
    (Framework.ISO_27001_2022, "A.8.24", "Use cryptography effectively"),
    (Framework.ISO_27001_2022, "A.8.25", "Build security into the development life cycle"),
    (Framework.ISO_27001_2022, "A.8.26", "Define application security requirements"),
    (Framework.ISO_27001_2022, "A.8.28", "Apply secure coding practices"),
    (Framework.ISO_27001_2022, "A.8.32", "Control changes"),
]

OBLIGATIONS: list[tuple[Regime, str, str]] = [
    # Nigeria Data Protection Act 2023
    (Regime.NDPA_2023, "NDPA-01", "Process personal data lawfully and only for stated purposes"),
    (Regime.NDPA_2023, "NDPA-02", "Apply appropriate technical and organisational security"),
    (
        Regime.NDPA_2023,
        "NDPA-03",
        "Notify the regulator (NDPC) of qualifying personal data breaches",
    ),
    (Regime.NDPA_2023, "NDPA-04", "Honour data subject rights (access, correction, erasure)"),
    (Regime.NDPA_2023, "NDPA-05", "Bind data processors and vendors by written agreements"),
    # Central Bank of Nigeria cybersecurity requirements (via partner banks and PSPs)
    (Regime.CBN, "CBN-01", "Maintain board-overseen cybersecurity governance and a risk register"),
    (Regime.CBN, "CBN-02", "Manage third-party and payment-partner security risk"),
    (Regime.CBN, "CBN-03", "Report significant cyber incidents to the regulator"),
    (Regime.CBN, "CBN-04", "Run periodic vulnerability assessments and penetration tests"),
    (Regime.CBN, "CBN-05", "Secure customer authentication and transaction integrity"),
    # Securities and Exchange Commission Nigeria (investment products)
    (Regime.SEC_NG, "SEC-01", "Protect and segregate investor assets and client funds"),
    (Regime.SEC_NG, "SEC-02", "Keep pricing, valuation and investor records accurate"),
    (Regime.SEC_NG, "SEC-03", "Keep investment platforms and fund-manager links resilient"),
    # PCI DSS v4.0 (principal requirements)
    (Regime.PCI_DSS_4, "PCI-03", "Protect stored account data (Requirement 3)"),
    (Regime.PCI_DSS_4, "PCI-04", "Encrypt cardholder data over open networks (Requirement 4)"),
    (Regime.PCI_DSS_4, "PCI-06", "Develop and maintain secure systems and software (Req. 6)"),
    (Regime.PCI_DSS_4, "PCI-07", "Restrict access to cardholder data by need to know (Req. 7)"),
    (Regime.PCI_DSS_4, "PCI-08", "Identify users and authenticate access (Requirement 8)"),
    (Regime.PCI_DSS_4, "PCI-10", "Log and monitor access to system components (Requirement 10)"),
    (Regime.PCI_DSS_4, "PCI-11", "Test security of systems and networks regularly (Req. 11)"),
]
