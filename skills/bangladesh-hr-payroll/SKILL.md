---
name: bangladesh-hr-payroll
description: Company payroll benchmark for Bangladeshi private employers, from the ReckonERP Bangladesh Company Payroll Benchmark 2026 (role salary bands, salary components, deductions, attendance events, leave practices, synthetic payroll examples and AI skill guardrails). Use when suggesting salary bands, designing salary templates, explaining a payslip, reconciling attendance to payroll, flagging payroll anomalies, answering leave-balance questions or forecasting payroll cost for a Bangladesh company.
metadata:
  baseline: 2026-11-08
  basis: ReckonERP_Bangladesh_Company_Payroll_Guide_2026.pdf and ReckonERP_Bangladesh_Company_Payroll_Benchmark_2026.xlsx
  currency: BDT per month, gross
  status: indicative market data for product configuration, not a national average and not a legal reference
---

# Bangladesh company payroll benchmark (ReckonERP)

Use this skill for HR and payroll on Bangladeshi private companies. The figures are indicative market ranges that seed demos, templates and AI explanations. Each customer must calibrate them with its own payroll data.

## 1. Rules for the agent

1. **Ranges, not averages.** Always give range, midpoint and confidence together. Never present a figure as a guaranteed salary or as a national average.
2. **Keep confidence visible.** Medium means several current market sources agree. Low means a sparse sample or broad estimate. Say which one applies.
3. **Synthetic data is fiction.** Sample payroll records in this dataset are test data. Never present them as a real employee or employer record.
4. **Explain, don't change pay.** Anomaly flags and reconciliation results recommend an action. They never deduct, alter or pay anything. Payroll changes need human approval.
5. **Use current records only.** A payslip explanation uses only the current payroll period's salary, attendance, leave, approved variable pay and deductions.
6. **Respect data access.** Share salary and bank details only with users whose role allows it.
7. **Not a legal reference.** This dataset does not give statutory minimums, overtime formulas, leave entitlements or tax rates. Do not derive compliance settings from it. Route those questions to the company's own legal or tax adviser.

## 2. Role salary bands (monthly gross, BDT)

Source basis is in the workbook's Role Benchmarks sheet. Midpoint = (min + max) ÷ 2.

| Industry | Role | Level | Min | Max | Mid | Confidence |
|---|---|---|---|---|---|---|
| IT / Software | Help Desk / IT Support | Entry | 18,000 | 30,000 | 24,000 | Low |
| IT / Software | Junior Software Developer | Entry | 35,000 | 60,000 | 47,500 | Medium |
| IT / Software | Software Engineer | Mid | 50,000 | 130,000 | 90,000 | Medium |
| IT / Software | Senior Software Engineer | Senior | 100,000 | 180,000 | 140,000 | Medium |
| IT / Software | AI / Data Engineer | Mid | 50,000 | 120,000 | 85,000 | Low |
| IT / Software | DevOps / Cloud Engineer | Mid | 80,000 | 160,000 | 120,000 | Low |
| IT / Software | IT Project Manager | Senior | 120,000 | 200,000 | 160,000 | Medium |
| IT / Software | QA / Test Engineer | Mid | 30,000 | 80,000 | 55,000 | Low |
| Manufacturing / RMG / Textile | Machine Operator (skilled) | Operational | 15,000 | 25,000 | 20,000 | Low |
| Manufacturing / RMG / Textile | Production Supervisor | Mid | 30,000 | 50,000 | 40,000 | Medium |
| Manufacturing / RMG / Textile | Factory Manager | Senior | 80,000 | 150,000 | 115,000 | Medium |
| Manufacturing / RMG / Textile | Quality / QA Executive | Entry-Mid | 25,000 | 50,000 | 37,500 | Low |
| Construction / Engineering | Civil Engineer | Mid | 50,000 | 80,000 | 65,000 | Medium |
| Construction / Engineering | Site Supervisor | Mid | 35,000 | 55,000 | 45,000 | Medium |
| Construction / Engineering | Skilled Technician | Operational | 20,000 | 35,000 | 27,500 | Medium |
| Corporate / Finance | Accountant / Finance Executive | Mid | 25,000 | 70,000 | 47,500 | Medium |
| Corporate / Finance | HR Executive | Entry-Mid | 25,000 | 50,000 | 37,500 | Low |
| Corporate / Finance | HR Manager | Senior | 70,000 | 120,000 | 95,000 | Medium |
| Sales / Marketing | Sales Executive | Entry-Mid | 19,000 | 40,000 | 29,500 | Medium |
| Sales / Marketing | Marketing Manager | Senior | 60,000 | 110,000 | 85,000 | Medium |
| Pharmaceuticals | Medical / Product Sales Representative | Entry-Mid | 25,000 | 50,000 | 37,500 | Low |
| Pharmaceuticals | Production / QA Executive | Mid | 30,000 | 65,000 | 47,500 | Low |
| Trading / Distribution | Sales / Territory Officer | Entry-Mid | 22,000 | 45,000 | 33,500 | Low |
| Trading / Distribution | Warehouse / Inventory Executive | Entry-Mid | 20,000 | 40,000 | 30,000 | Low |
| Healthcare | Hospital Admin Executive | Mid | 25,000 | 55,000 | 40,000 | Low |
| Healthcare | Accounts / Billing Executive | Entry-Mid | 22,000 | 45,000 | 33,500 | Low |
| Education / NGO / Services | Program / Admin Officer | Mid | 30,000 | 70,000 | 50,000 | Low |
| Retail / Logistics | Store / Operations Supervisor | Mid | 25,000 | 50,000 | 37,500 | Low |

Role notes that change the range (keep them when quoting):
- Software roles: experience and delivery scope; higher-paying firms can exceed the band.
- DevOps and AI/Data: small samples, employer-sensitive.
- Sales and sales-executive roles: commission is usually additional to the band.
- Pharmaceutical and healthcare roles: transport allowance, TA/DA, shift pattern and hospital size change pay.
- Donor-funded roles (NGO and programme): may differ from market.

## 3. Salary components

| Component | Type | Frequency | Company method | ReckonERP configuration |
|---|---|---|---|---|
| Basic salary | Fixed | Monthly | Core contract amount, company-defined proportion | Effective-dated; the calculation base |
| House rent | Fixed | Monthly | Flat or percentage of basic | Company formula. Do not assume a universal percentage. |
| Medical | Fixed | Monthly | Flat allowance | Company amount or eligibility |
| Transport / conveyance | Fixed or conditional | Monthly | Flat, actual reimbursement or attendance-linked | Support fixed, per-day and claim methods |
| Meal / lunch | Fixed or attendance-linked | Monthly or per day | Flat, meal card or payable days × rate | Prorate by payable days |
| Mobile / internet | Fixed or reimbursement | Monthly | Role allowance or submitted claim | Cap and receipt workflow |
| Attendance incentive | Variable | Monthly | Paid when attendance criteria are met | Configurable eligibility and threshold |
| Shift / night allowance | Variable | Per shift or monthly | Rate × eligible shifts | Use roster and approved shift records |
| Project / site allowance | Variable | Per day or monthly | Rate × eligible project or site days | Link to project, site and cost centre |
| Sales commission | Variable | Monthly or quarterly | Target achievement × plan | Slab, target, collection or margin basis; approval |
| Performance bonus | Variable | Quarterly or annual | KPI score or approved amount | Store period, rating and approval |
| Festival or occasion bonus | Variable | Event-based | Amount or salary multiple | Event schedule and eligibility configurable |
| Overtime | Variable | Hourly | Approved hours × configured rate | Configured formula, time event and approval |
| Reimbursement | Expense claim | As approved | Approved eligible expense | Kept outside fixed gross where appropriate |

## 4. Deductions and adjustments

Model every deduction as a named, auditable transaction. Store the source event, calculation base, amount, reason, approver and payroll period.

| Deduction | Category | Example calculation | Audit handling |
|---|---|---|---|
| Unpaid absence | Attendance-linked | Absent days × configured daily rate, only where policy marks the day unpaid | Keep the source attendance event and calculation trace |
| Late or early departure | Attendance-linked | Threshold, grace and penalty set by the company | Never hard-code a universal deduction |
| Employee loan | Recovery | Approved instalment per payroll | Opening balance, instalment, closing balance |
| Salary advance | Recovery | Approved amount or instalment | Request, approval, outstanding balance |
| Benefit contribution | Voluntary or company plan | Fixed or percentage | Employee and employer portions kept separate |
| Meal or transport recovery | Recovery | Actual usage or agreed amount | Cap and exception handling |
| Damage or asset recovery | Recovery | Approved amount | Reason, approval and evidence |
| Other adjustment | Manual | Positive or negative | Mandatory reason, approver and audit trail |

## 5. Attendance events

Keep raw punches separate from corrected and approved attendance.

| Event | Granularity | Configurable treatment | Data to keep |
|---|---|---|---|
| Present | Daily | Payable day | Timesheet, device or mobile check-in |
| Late in | Daily | Compared with shift start plus grace; may affect incentive | Minutes late, approved exception |
| Early out | Daily | Compared with scheduled end; may affect incentive | Approved early departure, kept separate |
| Absent | Daily | Full or half day by company code; paid, unpaid or leave-adjusted | Reason and linked leave request |
| Half day | Daily | Configured fraction | Half-day attendance and leave link |
| Overtime | Time | Approved hours × configured rate | Requested, approved and payable hours, separately |
| Shift / roster | Schedule | Planned work window and rest day | Rotating, split and night shifts |
| Remote or field work | Location | Approved day or geotagged visit | Offline capture and manager validation |
| Holiday / weekly off | Calendar | Company calendar classification | Company calendar, not hard-coded national rules |
| Payroll cut-off | Period | Attendance locked at cut-off | Late corrections go through the adjustment workflow |

## 6. Leave

Keep leave as a ledger: opening balance + accrual + adjustment − used = closing balance.

| Leave type | Unit | Configuration | Workflow |
|---|---|---|---|
| Annual / earned | Days or hours | Company plan | Balance and planned-usage answers |
| Casual / personal | Days or hours | Fixed or accrued | Full day, half day and hourly requests |
| Sick | Days or hours | Balance or tracking | Attachment or approval where the employer requires |
| Unpaid | Days or hours | Reduces payable amount if configured | Explain the salary impact before approval |
| Maternity, parental or special | Days or hours | Separate type and pay treatment | Type and pay treatment configurable |
| Compensatory off | Hours or days | Earned from approved extra work | Link to approved overtime or work event |
| Encashment | Days × rate | Configured rate and eligibility | Kept separate from monthly salary |

Note: the benchmark does not set statutory leave entitlements. Use the company's approved policy.

## 7. Synthetic payroll examples (fictional)

| ID | Designation | Gross | Deductions | Net | Check |
|---|---|---|---|---|---|
| SYN-001 | Software Engineer (Mid) | 105,000 | Loan 1,500 | 103,500 | Reconciles |
| SYN-002 | Accountant (Mid) | 67,000 | Loan 2,000 | 65,000 | Reconciles |
| SYN-003 | Production Supervisor (Mid) | 58,000 | None | 58,000 | Reconciles |
| SYN-004 | Sales Executive (Entry-Mid) | 52,000 | None | 52,000 | Reconciles (includes 8,000 commission) |
| SYN-005 | Site Supervisor (Mid) | 68,000 | None | 68,000 | Reconciles (includes 6,000 site allowance) |
| SYN-006 | Territory Officer (Entry-Mid) | Blank | Other 1,000 | Blank | Incomplete. Inputs give 52,000 gross and 51,000 net; do not fill without confirmation. |

The guide's worked example is also fictional: basic 28,000 + house rent 12,000 + medical 2,000 + transport 3,000 + meal 1,500 + attendance incentive 1,000 + commission 4,500 = 52,000 gross; less loan recovery 1,000 = 51,000 net.

## 8. AI skills and guardrails

| Skill | Purpose | Required data | Guardrail |
|---|---|---|---|
| Salary Benchmark Assistant | Suggest a band by role, experience and location | Role, industry, location, experience, skills, employer size | Range, midpoint, confidence and source notes. Never a guaranteed salary. |
| Payroll Explanation Copilot | Explain each payslip line in plain Bangla or English | Salary structure, attendance, leave, approved variable pay, deductions | Current period records only; line-by-line gross to net |
| Attendance Reconciliation Agent | Find missing punches, late patterns, roster and payroll mismatches | Roster, raw punches, approved corrections, leave | Exception list with evidence; human approval before any payroll change |
| Payroll Anomaly Detection | Flag salary changes, duplicate payments, outlier allowances, negative net | Current and historical payroll, grade, department, peers | Explain only; never auto-deduct or alter pay |
| Leave Balance Assistant | Balance, pending request and projected balance | Leave ledger, requests, accrual settings | Respect role-based access |
| Compensation Structure Designer | Company templates by role and grade | Policy, budget, benchmark bands | Customer administrator approves the template |
| Payroll Forecasting | Cost, headcount and variable pay scenarios | Employee master, salary changes, hiring plan, roster | Keep actual, committed and forecast values separate |
| HR Data Quality Agent | Missing bank details, duplicate IDs, missing components, invalid dates | Employee master, salary assignments, payroll history | Never expose sensitive data to unauthorised users |

## 9. Data model

Keep these entities separate: Employee Master; Salary Assignment (effective-dated); Salary Component Catalogue; Attendance Events; Shift or Roster; Leave Ledger; Payroll Run; Payroll Line; Commission or Bonus Plan; Loan or Advance Ledger; Expense Reimbursement; Approval Workflow; Audit Event; Benchmark Record.

Each payroll line keeps its calculation base, rate, quantity, source transaction and explanation.

Benchmark Record fields: industry, role, level, min, max, midpoint, source, date, confidence.

## 10. Rollout guidance

- Store the source date, geography, sample size where available, gross or net basis, confidence and limitations for every figure.
- At onboarding, import the customer's actual salary register and anonymised payroll history. Build company-specific bands from that data.
- Do not use one nationwide average for every role.
- Refresh market ranges periodically and validate them against customer payroll before any compensation decision.

## 11. Sources

| ID | Source | Date or access | Useful data | Caveat |
|---|---|---|---|---|
| S1 | Bangladesh Bureau of Statistics, Labour Force Survey 2024, reported by The Business Standard | 2025-09-17 | National employee average BDT 15,554/month | Broad context, not a professional benchmark |
| S2 | Paylab Bangladesh salary survey | Accessed 2026-11-08 | Survey gross averages by working area | Check sample and methodology |
| S3 | Manpower.com.bd Bangladesh Salary Benchmarks 2026 | Accessed 2026-11-08 | Role-level gross ranges, IT, manufacturing, construction, corporate | Recruitment vendor content; indicative |
| S4 | Mimu Jobs Bangladesh Salary Guide 2026 | Accessed 2026-11-08 | Dhaka role ranges, software, finance, data, DevOps, design, product | Methodology and coverage vary |
| S5 | Jobiglo Bangladesh Salary Guide | Accessed 2026-11-08 | Active-offer averages and medians | Small sample; directional only |
| S6 | Chakri AI Bangladesh Salary Guide 2026 | Accessed 2026-11-08 | Indicative ranges, software engineer and accountant | Aggregated; not a formal survey |
| S7 | SME Foundation, Study on Software Industry in Bangladesh | Accessed 2026-11-08 | Software salary bands, historical | Older survey; not current offers |
| S8 | JobFair.bd Software Engineer Salary Guide | Accessed 2026-11-08 | 2025–2026 software ranges | Estimates from postings and recruiter conversations |

Links are in the source workbook's Sources sheet and the guide's source register.
