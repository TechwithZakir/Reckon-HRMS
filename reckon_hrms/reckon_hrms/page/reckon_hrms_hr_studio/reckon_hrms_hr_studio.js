// HR Studio (one page): the employee lifecycle as steps, from hiring to exit. Each step opens at any time.
// Served at /desk/reckon-hrms/reckon-hrms-hr-studio. "Your company" is the shared company stage.
frappe.pages["reckon-hrms-hr-studio"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({ parent: wrapper, title: "HR Studio", single_column: true });
	const STAGES = [["hiring", "Hiring"], ["company", "Company and employee setup"], ["employees", "Employee details"], ["onboarding", "Onboarding"],
		["attendance", "Time and attendance"], ["leave", "Leave and holidays"], ["exit", "Exit"]];
	const shell = $(`<div class="rhs-shell" style="display:block"></div>`).appendTo(page.main);
	const nav = $(`<nav class="rhs-stages" role="tablist" aria-label="HR Studio steps" style="display:flex;gap:4px;flex-wrap:wrap;border-bottom:1px solid var(--border-color);margin:10px 0 14px"></nav>`).appendTo(shell);
	const body = $(`<div class="rhs-body" style="min-width:0"></div>`).appendTo(shell);
	const style = `<style>.rhs-stages button{border:0;border-bottom:2px solid transparent;background:none;color:var(--text-muted);padding:10px 16px;cursor:pointer;font-weight:500;font-size:14px}.rhs-stages button:hover{color:var(--text-color)}.rhs-stages button[aria-current="step"]{color:var(--primary);border-bottom-color:var(--primary);font-weight:600}.rhs-stages button:focus-visible{outline:2px solid var(--primary);outline-offset:2px}</style>`;
	nav.append(style);

	function go(key) {
		const stage = STAGES.find((s) => s[0] === key) ? key : "hiring";
		nav.find("button").attr("aria-current", null);
		nav.find(`[data-stage="${stage}"]`).attr("aria-current", "step");
		body.empty();
		if (stage === "company") window.ReckonSetupStages.company(body);
		else window.ReckonHrStages[stage](body);
		window.ReckonFormControls(body);
		history.replaceState(null, "", `#${stage}`);
	}

	STAGES.forEach(([key, label]) => {
		$(`<button type="button" role="tab" data-stage="${key}">${label}</button>`).on("click", () => go(key)).appendTo(nav);
	});

	const fromRoute = frappe.route_options && frappe.route_options.stage;
	const fromHash = (location.hash || "").replace("#", "");
	frappe.route_options = null;
	go(fromRoute || fromHash || "hiring");
};

// Steps that open the standard lists: an icon to open the list and an icon to add a record.
window.ReckonHrStages = window.ReckonHrStages || {};
(function () {
	const esc = (t) => frappe.utils.escape_html(t == null ? "" : String(t));
	const icon = (name) => (frappe.utils && frappe.utils.icon ? frappe.utils.icon(name, "sm") : (name === "add" ? "+" : "≡"));
	const slug = (doctype) => "/app/" + doctype.toLowerCase().replace(/ /g, "-");
	const CARD = `<style>.rhh-card{background:var(--card-bg);border:1px solid var(--border-color);border-radius:12px;padding:16px;margin-top:14px}.rhh-card h2{font-size:15px;margin:0 0 8px}.rhh-row{display:flex;justify-content:space-between;align-items:center;gap:10px;padding:8px 0;border-bottom:1px dotted var(--border-color)}.rhh-row:last-child{border-bottom:0}.rhh-acts{display:inline-flex;gap:6px}.rhh-ico{display:inline-grid;place-items:center;width:34px;height:34px;border:1px solid var(--border-color);border-radius:8px;background:var(--card-bg);color:var(--text-color);text-decoration:none;cursor:pointer;padding:0}.rhh-ico:hover{border-color:var(--primary);color:var(--primary)}.rhh-muted{color:var(--text-muted);font-size:13px}</style>`;

	function lists(parent, sections) {
		const root = $(`<div class="rhh">${CARD}</div>`).appendTo(parent);
		sections.forEach((sec) => {
			const card = $(`<section class="rhh-card"><h2>${esc(sec.title)}</h2>${sec.note ? `<div class="rhh-muted" style="margin-bottom:6px">${esc(sec.note)}</div>` : ""}</section>`).appendTo(root);
			sec.lists.forEach((l) => {
				$(`<div class="rhh-row"><span>${esc(l.title)}</span>
					<span class="rhh-acts"><a class="rhh-ico" href="${slug(l.doctype)}" title="Open the ${esc(l.title)} list" aria-label="Open the ${esc(l.title)} list">${icon("list")}</a>
					<a class="rhh-ico" href="${slug(l.doctype)}/new" title="Add new" aria-label="Add new ${esc(l.title)}">${icon("add")}</a></span></div>`).appendTo(card);
			});
		});
	}

	window.ReckonHrStages.employees = function (parent) {
		const esc = (t) => frappe.utils.escape_html(t == null ? "" : String(t));
		const COLS = [
			{ key: "name", label: "ID" }, { key: "employee_name", label: "Name" }, { key: "branch", label: "Branch" },
			{ key: "department", label: "Department" }, { key: "designation", label: "Job title" },
			{ key: "date_of_joining", label: "Joined" }, { key: "status", label: "Status" }, { key: "missing", label: "Missing details" },
		];
		const state = { rows: [], sort: { key: "employee_name", dir: 1 }, f: { q: "", branch: "", department: "", designation: "", status: "", missingOnly: false } };
		const root = $(`<div class="hrs-emp">
			<div class="rhh-card">
				<div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:10px">
					<div><h2 style="margin:0">Employee details</h2>
					<div class="rhh-muted">Everyone in the company. Filter by branch, department, job title or status.</div></div>
					<button type="button" class="btn btn-primary btn-sm" data-add>${frappe.utils.icon ? frappe.utils.icon("add", "sm") : "+"} Add employee</button>
				</div>
				<div class="hrs-filters" style="display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:10px;margin-top:14px">
					<input type="text" class="form-control" data-f="q" placeholder="Search name or ID" aria-label="Search">
					<select class="form-control" data-f="branch" aria-label="Branch"><option value="">All branches</option></select>
					<select class="form-control" data-f="department" aria-label="Department"><option value="">All departments</option></select>
					<select class="form-control" data-f="designation" aria-label="Job title"><option value="">All job titles</option></select>
					<select class="form-control" data-f="status" aria-label="Status"><option value="">All statuses</option><option>Active</option><option>Inactive</option><option>Suspended</option><option>Left</option></select>
					<div class="checkbox" style="margin:0;align-self:center"><label><input type="checkbox" data-f="missingOnly"> <span class="label-area">Missing details only</span></label></div>
				</div>
				<div class="rhh-muted" data-count style="margin-top:10px">Loading...</div>
			</div>
			<div class="rhh-card" style="padding:0;overflow:hidden">
				<div style="overflow-x:auto"><table class="table table-bordered" style="margin:0;font-size:13px">
					<thead data-head></thead><tbody data-rows></tbody></table></div>
			</div></div>`).appendTo(parent);

		const opts = (values) => values.map((v) => `<option>${esc(v)}</option>`).join("");
		const fill = (field, values) => root.find(`select[data-f="${field}"]`).append(opts(values));

		const missing = (r) => [!r.branch && "branch", !r.department && "department", !r.designation && "job title"].filter(Boolean);

		function view() {
			const f = state.f;
			let list = state.rows.filter((r) => {
				if (f.q && !`${r.name} ${r.employee_name}`.toLowerCase().includes(f.q.toLowerCase())) return false;
				if (f.branch && r.branch !== f.branch) return false;
				if (f.department && r.department !== f.department) return false;
				if (f.designation && r.designation !== f.designation) return false;
				if (f.status && r.status !== f.status) return false;
				if (f.missingOnly && !missing(r).length) return false;
				return true;
			});
			const { key, dir } = state.sort;
			list = list.slice().sort((a, b) => String(a[key] ?? "").localeCompare(String(b[key] ?? "")) * dir);
			root.find("[data-count]").text(`Showing ${list.length} of ${state.rows.length} employees`);
			root.find("[data-head]").html(`<tr>${COLS.map((c) => {
				const arrow = state.sort.key === c.key ? (dir > 0 ? " ▲" : " ▼") : "";
				return `<th style="cursor:pointer;white-space:nowrap" data-sort="${c.key}">${esc(c.label)}${arrow}</th>`;
			}).join("")}</tr>`);
			root.find("[data-rows]").html(list.length ? list.map((r) => {
				const miss = missing(r);
				return `<tr>
					<td><a href="/app/employee/${encodeURIComponent(r.name)}">${esc(r.name)}</a></td>
					<td>${esc(r.employee_name)}</td><td>${esc(r.branch || "—")}</td><td>${esc(r.department || "—")}</td>
					<td>${esc(r.designation || "—")}</td><td>${esc(r.date_of_joining || "")}</td>
					<td>${r.status === "Active" ? '<span class="indicator-pill green">Active</span>' : `<span class="indicator-pill gray">${esc(r.status)}</span>`}</td>
					<td>${miss.length ? `<span class="indicator-pill orange">${esc(miss.join(", "))}</span>` : ""}</td></tr>`;
			}).join("") : `<tr><td colspan="${COLS.length}" class="text-muted" style="padding:16px">No employees match these filters.</td></tr>`);
		}

		root.on("input change", "[data-f]", function () {
			const k = this.dataset.f;
			state.f[k] = this.type === "checkbox" ? this.checked : this.value.trim();
			view();
		});
		root.on("click", "[data-sort]", function () {
			const k = this.dataset.sort;
			state.sort = { key: k, dir: state.sort.key === k ? -state.sort.dir : 1 };
			view();
		});
		root.find("[data-add]").on("click", () => frappe.ui.form.make_quick_entry("Employee", () => load(), null, {}));

		function load() {
			frappe.call({ method: "frappe.client.get_list", args: {
				doctype: "Employee", fields: ["name", "employee_name", "branch", "department", "designation", "date_of_joining", "status"],
				order_by: "employee_name asc", limit_page_length: 1000 } }).then((r) => {
				state.rows = r.message || [];
				const uniq = (k) => [...new Set(state.rows.map((x) => x[k]).filter(Boolean))].sort();
				root.find('select[data-f="branch"] option:not(:first-child)').remove();
				root.find('select[data-f="department"] option:not(:first-child)').remove();
				root.find('select[data-f="designation"] option:not(:first-child)').remove();
				fill("branch", uniq("branch")); fill("department", uniq("department")); fill("designation", uniq("designation"));
				view();
			});
		}
		load();
	};

	window.ReckonHrStages.hiring = function (parent) {
		lists(parent, [
			{ title: "Recruitment", note: "From a vacancy to an accepted offer.", lists: [
				{ title: "Job openings", doctype: "Job Opening" }, { title: "Job applicants", doctype: "Job Applicant" },
				{ title: "Job offers", doctype: "Job Offer" }] },
		]);
	};

	window.ReckonHrStages.onboarding = function (parent) {
		lists(parent, [
			{ title: "New joiners", note: "Checklists for a new employee's first days.", lists: [
				{ title: "Employee onboarding", doctype: "Employee Onboarding" },
				{ title: "Onboarding templates", doctype: "Employee Onboarding Template" }] },
		]);
	};

	window.ReckonHrStages.exit = function (parent) {
		lists(parent, [
			{ title: "Leaving employees", note: "Separation, exit interview and final settlement.", lists: [
				{ title: "Employee separation", doctype: "Employee Separation" },
				{ title: "Separation templates", doctype: "Employee Separation Template" },
				{ title: "Exit interviews", doctype: "Exit Interview" }] },
		]);
	};

	window.ReckonHrStages.attendance = function (parent) {
		lists(parent, [
			{ title: "Working hours", note: "Shift timings used for late entry and early exit.", lists: [{ title: "Work shifts", doctype: "Shift Type" }, { title: "Shift assignments", doctype: "Shift Assignment" }] },
			{ title: "Attendance records", note: "Daily attendance, device punches and overtime.", lists: [{ title: "Attendance", doctype: "Attendance" }, { title: "Employee check-ins", doctype: "Employee Checkin" }] },
		]);
	};

	window.ReckonHrStages.leave = function (parent) {
		lists(parent, [
			{ title: "Leave", note: "Leave types and balances.", lists: [{ title: "Leave types", doctype: "Leave Type" }, { title: "Leave applications", doctype: "Leave Application" }, { title: "Leave allocations", doctype: "Leave Allocation" }] },
			{ title: "Holidays", note: "Company holiday calendars.", lists: [{ title: "Holiday lists", doctype: "Holiday List" }, { title: "Holiday list assignments", doctype: "Holiday List Assignment" }] },
		]);
	};
})();
