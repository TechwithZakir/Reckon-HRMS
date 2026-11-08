# Reckon HRMS setup pages: instructions, mock and ideas

Status: design only. The Page 1 back end is built and deployed (`reckon_hrms/api/setup.py`,
`reckon_hrms/api/shortcuts.py`, `reckon_hrms/paging.py`). Pages 2 and 3 and all front ends are not built yet.

Routes: `/reckon/company` (Page 1), `/reckon/salary` (Page 2), `/reckon/run` (Page 3).
Visual reference: the Reckon HRMS Onboarding mock (three tabs, numbered sections, right rail).

## Rules for every page

- Plain words first. "Offices and factories", not Branch. Turn on "Show Frappe HR mapping" to see doctype names as small tags.
- Each section that maps to a doctype has three buttons on its heading: **+ Add new**, **List**, **Standard page**.
  The paths come from `shortcuts.route(doctype, action)`. A menu is used when a section covers several doctypes.
- Lists load 25 rows at a time and never more than 100 (`paging.page_bounds`).
- Saving writes real records. There is no draft store. Progress comes from record counts (`setup.get_state`).
- Long jobs run in the background in batches of 200, grouped by office, and report progress by realtime event
  and by a polling method. They are safe to run twice.
- Works from 360 px. No horizontal page scroll. Every input has a label. Colour is never the only signal.

## Page 1: Your company (`/reckon/company`)

| # | Section | User does | Records | API |
|---|---|---|---|---|
| 1 | About your company | Confirms name, licence, TIN, country BDT, financial year July to June | Company, Fiscal Year | update the existing Company (do not create a second) |
| 2 | Organisation | Adds chips: offices, departments, job titles, levels, employee types | Branch, Department, Designation, Employee Grade, Employment Type | `setup.list_items`, `setup.create_item`, `setup.delete_item` |
| 3 | Add your people | Downloads template, uploads Excel, fixes errors, adds valid rows | Employee via Data Import | to build: `setup.employee_template`, `setup.start_import`, `setup.import_status`, `setup.apply_import` |
| 4 | Holidays and leave | Reviews Bangladesh 2026 holidays, edits leave days | Holiday List, Leave Type, Leave Policy | to build: `setup.apply_country_template` |
| 5 | Attendance | Picks fingerprint, mobile or Excel; sets shifts and lock date | Shift Type, Employee Checkin | to build: `setup.save_attendance` |

Mock (text wireframe):

```
[1 Your company]  [2 Salary rules]  [3 Run salary]          [ ] Show Frappe HR mapping
Welcome, Nasrin. Set up Rahman Textiles.        Step 1 of 3  ████░░░░ 35%
1 About your company                  [+ Add new] [List] [Standard page]
  Company name [______]  Trade licence [______]  TIN [______]
2 Offices and departments             [+ Add new] [List] [Standard page v]
  Offices: (Gazipur Factory x) (Dhaka Head Office x) [+ Chattogram Unit] [type + Enter]
  Departments: (Production x) (Accounts x) [+ Sales] ...
3 Add your people                     [Download template] [Upload .xlsx]
  Summary: 2,480 read · 2,451 ready · 29 to fix     [Add 2,451 people]
  Row 1,203  Jahid Hasan  "Department Prodction not found. Did you mean Production?" [Use Production]
4 Holidays and leave                  Casual 10 · Sick 14 · Annual 18 · Maternity 112
5 Working hours and attendance        (o) Fingerprint  ( ) Mobile app  ( ) Excel
Rail: checklist (from setup.get_state) · Book a 15 minute call · Chat on WhatsApp
Footer: Skip for now · Save and set up salary
```

Instructions for building:
1. Render the checklist and progress from `setup.get_state`. Refresh after every save.
2. Chips: a suggestion tap calls `create_item`; Enter on typed text calls it too. Removing calls `delete_item`
   and shows the employee count if refused.
3. Import: generate the template from Employee meta, so the department, job title and type columns use the names
   created in section 2. Run the dry-run in the background, then show the summary and first errors.
   Show "Add N people" only after the dry-run passes. Import valid rows only; never half-save.

## Page 2: Salary rules (`/reckon/salary`)

| # | Section | User does | Records | API |
|---|---|---|---|---|
| 1 | Tax year and income tax | Picks year July to June and a rate template | Payroll Period, Income Tax Slab (fixture) | to build: `salary.save_tax_setup` |
| 2 | Pay and deductions | Switches items, sets percent or fixed value, taxable, cut for unpaid leave | Salary Component | to build: `salary.get_components`, `salary.save_component` |
| 3 | Salary structures | Worker, Staff, Management: name, frequency | Salary Structure | to build: `salary.list_structures`, `salary.save_structure` |
| 4 | Person to structure | Assigns structure and base; single or bulk from a sheet | Salary Structure Assignment | to build: `salary.list_assignments`, `salary.bulk_assign` |

Right rail: payslip preview. Base salary in, real calculation out, debounced 300 ms
(`salary.preview_payslip`). The preview must build an unsaved Salary Slip and call its own calculation,
so preview and payslip never disagree.

Mock:

```
2 Salary rules
Tax year [July 2026 to June 2027 v]   Rates [Bangladesh standard v]
What you pay and deduct
  Basic salary        Pay       % of gross   55 %   Taxable Yes   Cut for unpaid leave [x]
  House rent          Pay       % of gross   25 %   Partly        [x]
  Provident fund      Deduction % of basic   10 %   No            [ ]
Salary structures:  (o) Worker  ( ) Staff  ( ) Management
4 Assign       29 people have no structure  [Show them]
Right rail:  Base ৳ [45,000]   Basic 24,750 · House 11,000 · Medical 4,500 ...
             Take home ৳ 40,xxx   (warning if pay items do not total 100 %)
```

Instructions for building:
1. Store tax slabs and festival bonus as fixture data, never as code constants. Label them "confirm with your tax adviser".
2. Toggling "Cut for unpaid leave" changes the component's Depends on Leave Without Pay flag.
3. Bulk assign runs in the background and reports created and skipped with reasons. Editing a structure never changes a submitted slip.

## Page 3: Run salary (`/reckon/run`)

Five steps, each a stage of a Payroll Entry. The current step is derived from data, so a closed browser loses nothing.

| Step | User sees | API | Record |
|---|---|---|---|
| 1 Choose month and people | Month, pay date, filters, three toggles | `payroll.start_run` | Payroll Entry (draft) |
| 2 Check the list | Found / included / joined / left; warnings; people table | `payroll.fetch_employees`, `payroll.list_people` | Payroll Entry employees |
| 3 Create slips | Batch progress per office | `payroll.create_slips`, `payroll.progress` | Salary Slip (draft) |
| 4 Review and approve | Totals, comparison with last month, approve | `payroll.submit_slips` | Salary Slip (submitted) |
| 5 Pay | Bank account, BEFTN file, bKash/Nagad sheet, hold list, record payment | `payroll.export_payment_files`, `payroll.record_payment` | Journal Entry |

Leaving people out:
- Step 2: remove the person from the Payroll Entry employee table. No slip.
- Steps 3 and 4: delete that person's draft slip. Checking again creates it.
- Step 5: never cancel. Set `reckon_payment_hold` with a reason. Drop them from the files and the Journal Entry.
- "Leave out all shown" and "Include all shown" act on the whole filtered set on the server, not the visible page.

Mock:

```
3 Run salary for October 2026   Five steps. Nothing is paid until step 5.
 1 Choose month   [Oct 2026 v]  Pay date [7 Nov 2026]  Office [All v] Dept [All v] ...
 2 Check the list   Found 2,480   Included 2,451   Joined 38   Left 9
                    ! 29 have no salary structure  [Fix in Salary rules]
   [search] [All | Included | Left out | Hold payment] [office v]   [Leave out all shown] [Include all shown]
   [x] E1001 Rahim Hossain   Gazipur Factory   30   ৳56,500   ৳4,100   ৳52,400   Included
 3 Create slips   Gazipur ████████ 100%   Dhaka ███░░ 42%   "2,451 slips ready as drafts"
 4 Review         Total pay ৳..  Deductions ৳..  To pay out ৳..   [Approve 2,451 slips]
 5 Pay            Bank account [Dutch-Bangla v]  [Download bank file] [Download bKash/Nagad sheet]
                  Hold: 6 people with no account   [I have paid. Record it]
```

Instructions for building:
1. Batches of 200, grouped by office. One failed office does not stop the others; offer "Retry failed".
2. Idempotent: re-running skips people who already have a slip for the period.
3. Totals refresh from the server after every change (one debounced bulk call).
4. The Journal Entry total must equal the sum of net pay of submitted, non-held slips.
5. Payment files are generated from submitted slips, aggregated in SQL, never by loading each slip.
6. After "I have paid", lock every checkbox and bulk button.

## Ideas (not committed)

- A "first run" checklist that opens the next incomplete page.
- A 10-second test payslip for a new tenant, using a fake employee that is deleted afterwards.
- Compare this month with last month at step 4, flagging any person whose pay moved by more than 30 per cent.
- Keep a list of saved filters ("Gazipur operators") for the people table.
- One-click "copy last month's inclusions" at step 2.
- A bank file preview that checks account numbers before download.
- Mobile-first summary card on the run page for approving from a phone.

## Open decisions (from the brief)

- Salary split and provident fund: the mock uses basic 55 %, house rent 25 %, medical 10 %, conveyance 10 %, provident fund 10 %; the current code uses basic 60 % of base, house rent 50 % of basic, provident fund 5 %. Choose one before building Page 2.
- Tax relief: the mock deducts up to 4,50,000 of relief; the current code uses a 3,50,000 exemption and PF only.
- Approval chain, bank file layout, wallet payout API, and who updates holidays and tax slabs each year (see the brief, section 11).
