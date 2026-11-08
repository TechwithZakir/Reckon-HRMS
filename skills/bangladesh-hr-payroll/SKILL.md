---
name: bangladesh-hr-payroll
description: Domain knowledge for HR and payroll of Bangladeshi private-sector companies (Bangladesh Labour Act 2006 as amended by Act 43 of 2026, SRO 53-Law/2026, NBR income tax and withholding, sector minimum-wage gazettes). Use when designing, configuring, explaining or auditing HR, attendance, leave, salary structure, payroll run, deductions, tax or payslip behaviour for a Bangladesh employer, or when an agent must answer a Bangladesh payroll question.
metadata:
  research_cut_off: 2026-11-08
  basis: Bangladesh_Private_Sector_Payroll_Research_Report_2026.pdf and Bangladesh_Private_Sector_Payroll_Research_Datasheet_2026.xlsx
  status: research baseline, not legal advice
---

# Bangladesh private-sector HR and payroll

This skill is the research baseline for an agentic HR and payroll implementation for Bangladeshi companies. It separates four kinds of evidence. Keep them separate in every answer, every configuration and every log.

| Evidence type | What it is | How to use it |
|---|---|---|
| Statutory | Labour Act 2006 as amended, Act 43 of 2026, SRO 53-Law/2026, sector wage-board gazettes, Income Tax Act and NBR rules | Configure only after checking the current authentic text. Effective-dated. |
| Market estimate | Manpower.com.bd (S09), Paylab (S10) | Indicative only. Never a legal minimum. Never a salary offer without employer validation. |
| Company policy | Employer's own grades, allowances, incentives, leave above statute | Owned by the employer. Store with approval and effective date. |
| Research gap | Anything the sources did not resolve | Say so. Do not fill it with an estimate. |

## 1. Rules the agent must follow

1. **Never invent a number.** Quote a salary range or a legal rate only when a named source gives it, and label it with its source ID and confidence.
2. **Never hard-code legal rates that are unverified.** Annual, casual and sick leave, maternity leave, provident fund and gratuity formulas, and exact sector wage grades are not transcribed in the baseline. Make them effective-dated configuration, and flag them as "pending legal verification".
3. **Do not compute a statutory amount from this document alone.** Overtime base, divisor, eligibility and holiday pay need the current Act or gazette text before go-live.
4. **Propose, do not submit.** For any payroll action (creating a run, approving slips, recording payment, changing a salary or tax setting), prepare the change and wait for a named HR or payroll approver. Payment needs a second confirmation.
5. **Always state the legal caveat** when answering a compliance question: "Verify against authentic Bangla legislation, current gazettes and qualified Bangladesh labour or tax counsel before deployment."
6. **Never treat lateness or absence as an automatic wage fine.** Deductions need a legal or written policy basis, a reason, an approver, a cap and an audit trail.

## 2. Current legal position (as of 8 Nov 2026)

- **Bangladesh Labour (Amendment) Act 2026, Act No. 43 of 2026, dated 10 April 2026 (S02).** Changes leave, maternity, equal remuneration and festival holidays. Old templates may be stale.
- **Labour Rules amendment SRO 53-Law/2026, dated 16 February 2026 (S04).**
- **Income tax:** FY 2026/27 rates under the current Income Tax Act and rules, plus NBR Withholding Tax Rules 2026 with the 6 July 2026 amendment (S11, S12). Do not hard-code rates. Use an annual tax projection per employee and reconcile monthly TDS.
- **Minimum wages:** sector wage-board gazettes, not one national private-sector minimum (S05). Examples listed in the register: pharmaceuticals (26 Jan 2026), bakery and confectionery (26 Jan 2026), iron foundry and engineering workshop (7 Apr 2026), paint and chemical factories (9 Jul 2026), garments (20 Dec 2023), cotton textile (4 Apr 2024), construction and wood (17 Aug 2021), security services (1 Feb 2022). Amounts for most of these are not transcribed.
- **EPZ companies** fall under a separate regime with BEPZA notifications. Treat them as a separate employer class.

## 3. Payroll model

- **Gross cash earnings** = basic + fixed cash allowances + variable earnings + eligible overtime + arrears and adjustments.
- **Net pay** = gross cash earnings − authorized employee deductions.
- **Employer payroll cost** = gross cash earnings + employer-side contributions, benefits and taxes where applicable. Track it separately from net pay.
- **Employer PF or benefits** are not deducted from net pay.
- Worked arithmetic example in the source (illustrative, not a salary scale): basic 30,000 + house rent 15,000 + medical 1,500 + conveyance 2,000 + incentive 3,000 = gross 51,500 before overtime, arrears and deductions.

### Earnings

| Component | Type | Control |
|---|---|---|
| Basic salary | Fixed | Contract, grade or wage gazette. Base for overtime and some benefits only where law defines it. |
| House rent | Fixed or percentage | No universal percentage. Employer or sector structure decides. |
| Medical, conveyance, food, mobile | Fixed or reimbursement | Separate reimbursable expenses from taxable pay. Define taxable vs accountable treatment. |
| Attendance or production incentive | Variable | Must not reduce the statutory wage floor. Define thresholds and eligibility in writing. |
| Sales commission | Variable | Define booking, collection, return, cancellation and clawback rules. |
| Overtime | Hourly | Only for eligible workers. See section 4. |
| Night or shift allowance | Per shift or fixed | Sector order or company policy. Separate from statutory overtime unless the law includes it. |
| Festival bonus | Fixed or formula | Set by law, wage order, contract or policy. There is no universal private-sector formula. |
| Performance bonus | Annual or quarterly | KPI, proration and eligibility in policy. |
| Arrears and adjustments | Adjustment | Keep period, reason and approval. |
| Leave encashment | Daily rate × eligible days | Only eligible leave, correct wage base. |

### Deductions

| Deduction | Rule |
|---|---|
| Income tax (TDS) | Annual projection and monthly reconciliation. Never a fixed rate in code. |
| Employee PF | Only where the scheme applies. Keep separate from the employer contribution. |
| Salary advance and loan recovery | Signed agreement, schedule, outstanding balance, cap and consent review. Keep them separate. |
| Unpaid leave (LWP) and absence | Defined daily or hourly divisor. Exclude paid leave. Never deduct twice for the same absence. |
| Late or early | Track the occurrence. A wage deduction needs legal review. Separate time not worked from a disciplinary fine. |
| Notice-pay recovery | Only where the termination terms and law make it enforceable. |
| Other authorized | Written authorization, court order or law, with a reason and approval. |

## 4. Overtime, hours and holidays

- **Ordinary weekly working time:** normally 48 hours a week for an adult worker (Labour Act s.102). Set the threshold by establishment type and worker category.
- **Overtime:** the report states eligible overtime is generally paid at **twice the ordinary rate of basic wage plus applicable dearness, ad-hoc or interim allowances** (s.108). Confirm the exact wording and coverage in the current text before go-live. Do not calculate overtime on gross salary by default.
- **Weekly holiday (s.103):** factories and industrial establishments one day; shops and establishments one and a half days; road transport 24 continuous hours. Exemptions and compensatory rules need review. One weekly-off template does not fit every employer.
- **Festival holidays:** 13 paid festival holidays per calendar year after the 2026 amendment (s.118 as updated by Act 43). Holiday work triggers substitute or compensatory handling.
- **Wage payment deadline (s.123):** wages for a wage period are generally payable within 7 working days after the period ends. Termination wages have a different deadline. The payroll calendar must enforce the cut-off.

## 5. Attendance design

- Shift roster: general, rotating, night or split, with effective dates and swap approval.
- Net payable hours = elapsed time − unpaid breaks.
- Weekly hours: alert at the threshold. Do not silently convert every excess hour to overtime.
- Overtime requires an authorization record (pre-approved, emergency or post-approved), actual hours and the overtime wage base.
- Field, biometric and remote attendance: store the evidence (location accuracy, device, timestamp, offline sync). Biometric data needs privacy and data-governance controls with a manual correction path.
- Rounding (minute, 5 or 15 minutes) must not underpay a legal entitlement. Document the direction and the payroll impact.

## 6. Leave

| Leave | Status | Action |
|---|---|---|
| Annual or earned | Statutory. Accrual varies by worker category and amended law. Legacy 1:18 and 1:11 rules must not be used without checking the 2026 text. | Accrual ledger, carry-forward and encashment, effective-dated |
| Casual | Statutory. Current days and eligibility to be confirmed. | Annual entitlement and approval |
| Sick | Statutory. Days, certification and paid or unpaid status to be confirmed. | Medical certificate workflow |
| Festival | 13 paid days (2026 amendment) | Holiday calendar and substitute benefit |
| Maternity | Changed by 2026 amendment. Duration and eligibility not confirmed. Do not reuse the old 112-day assumption. | Eligibility, benefit base, documents, return to work |
| Company special leave | Employer policy above the statutory floor. Cannot undercut the floor. | Separate leave type and cost centre |

## 7. Market benchmarks (indicative, not statutory)

Quote only with the source ID and the note "indicative, not statutory, validate before use".

| Industry | Role | Low (BDT/month) | High (BDT/month) | Source |
|---|---|---|---|---|
| IT / Software | Junior software developer | 40,000 | 60,000 | S09 |
| IT / Software | Senior software engineer | 100,000 | 180,000+ | S09 |
| IT / Software | IT project manager | 120,000 | 200,000+ | S09 |
| Manufacturing / RMG | Skilled machine operator | 15,000 | 25,000 | S09 |
| Manufacturing / RMG | Production supervisor | 30,000 | 50,000 | S09 |
| Manufacturing / RMG | Factory manager | 80,000 | 150,000+ | S09 |
| Construction / Engineering | Civil engineer (mid-level) | 50,000 | 80,000 | S09 |
| Construction / Engineering | Site supervisor | 35,000 | 55,000 | S09 |
| Construction / Engineering | Skilled mason or electrician | 20,000 | 35,000 | S09 |
| Corporate / Finance | Accountant or finance executive | 40,000 | 70,000 | S09 |
| Corporate / Finance | HR manager | 70,000 | 120,000 | S09 |
| Corporate / Finance | Marketing manager | 60,000 | 110,000 | S09 |

Category averages from Paylab (S10) are survey averages, not grade scales. Use them only as low-confidence directional indicators: banking 29,604; telecom 29,076; pharmaceuticals 27,098; textile, leather and apparel 14,744; transport and logistics 21,148; IT 37,234; construction and real estate 32,436.

Minimum wage figures in public reporting: RMG entry level BDT 12,500 under the 2023 four-grade notification (S06, S07); textile lowest grade BDT 10,000 with location differences (S08). Both must be checked against the gazette before use.

## 8. Research gaps (do not fill these)

- Role-specific salary ranges for most industries: no validated source. Trading, FMCG, healthcare, education, NGO, retail, and most telecom and logistics roles have no robust range.
- Exact pharmaceutical, RMG and textile wage-grade tables: the gazettes exist but the amounts were not transcribed.
- Leave, maternity, provident fund and gratuity after the 2026 amendment.
- Employee annual tax calculation and withholding under the 2026 rules: needs the full NBR schedule, rebates and exemptions.
- Lateness and absence deduction legality.
- EPZ wage structure.
- Private compensation for NGO, education and hospital employers.

When a question hits a gap, answer: "Not established in the baseline. Next research action: <the action from the gaps list>." Do not offer a figure.

## 9. Using this in the Reckon HRMS product

- Model every legal value as an effective-dated setting with a source ID and a verified-by field. Show "pending verification" until a reviewer marks it verified.
- Salary structures per employer, with components typed as fixed, variable or reimbursable, and each deduction carrying its legal or policy basis, approval and cap.
- Overtime: an overtime rule per worker category that holds the wage base, multiplier and eligibility. Keep it switched off until verified.
- Holiday calendar: the 13 festival days and the weekly-off template per establishment class, with substitute-leave handling.
- Tax: annual projection and monthly TDS reconciliation, with rates loaded from the current NBR schedule rather than code.
- Payroll run: the agent prepares drafts and reconciliations. A human approves each stage, and payment requires a second confirmation.

## 10. Sources

| ID | Source | Status |
|---|---|---|
| S01 | Bangladesh Labour Act 2006, consolidated online text (bdlaws.minlaw.gov.bd/act-details-952.html) | Primary; check against 2026 amendment |
| S02 | Bangladesh Labour (Amendment) Act 2026, Act 43 (10 Apr 2026) | Primary |
| S03 | Ministry of Labour legislative information (mole.gov.bd) | Lists the 2026 Act and 2025 Ordinance |
| S04 | Labour Rules amendment SRO 53-Law/2026 (16 Feb 2026) | Primary |
| S05 | Minimum Wages Board final gazette listing (updated 18 Aug 2026) | Primary, register |
| S06 | RMG minimum wage gazette announcement (21 Dec 2023) | Primary |
| S07 | Dhaka Tribune, RMG minimum wage Tk 12,500 (26 Nov 2023) | Secondary |
| S08 | The Business Standard, textile minimum wage reporting (3 Mar 2024) | Secondary |
| S09 | Manpower.com.bd, Bangladesh Salary Benchmarks 2026 (Mar 2026) | Market estimate |
| S10 | Paylab, Bangladesh salary by category (live page) | Survey average, low confidence |
| S11 | PwC Tax Summaries, Bangladesh individual income tax (reviewed 31 Jul 2026) | Secondary |
| S12 | NBR Income Tax Rules, incl. Withholding Tax Rules 2026 and 6 Jul 2026 amendment | Primary |
| S13 | ILO note on the 2022 Rules amendment (SRO 284-Law/2022) | Background |
| S14 | ILO NATLEX English translation of the Labour Act | Older translation, navigation only |
| S15 | Labour Act s.103 weekly holiday, bdlaws | Primary |

Links are in the source files: `Bangladesh_Private_Sector_Payroll_Research_Report_2026.pdf` and `Bangladesh_Private_Sector_Payroll_Research_Datasheet_2026.xlsx`.
