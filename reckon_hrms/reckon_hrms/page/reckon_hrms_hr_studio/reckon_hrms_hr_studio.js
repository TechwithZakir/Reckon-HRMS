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
		const root = $(`<div class="rhh-card"><h2>Employee details</h2>
			<div class="rhh-row"><span class="rhh-muted">Everyone in the company, with branch, department, job title and joining date.</span>
			<span class="rhh-acts"><button type="button" class="rhh-ico" data-add title="Add employee" aria-label="Add employee">${icon("add")}</button></span></div>
			<div class="rhh-scroll" style="overflow-x:auto"><table class="rhr-table" style="width:100%;font-size:13px"><thead><tr>
			<th>ID</th><th>Name</th><th>Branch</th><th>Department</th><th>Job title</th><th>Joined</th><th>Status</th></tr></thead>
			<tbody data-rows><tr><td colspan="7" class="rhh-muted">Loading...</td></tr></tbody></table></div></div>`).appendTo(parent);
		const load = () => frappe.call({ method: "frappe.client.get_list", args: {
			doctype: "Employee", fields: ["name", "employee_name", "branch", "department", "designation", "date_of_joining", "status"],
			order_by: "employee_name asc", limit_page_length: 500 } }).then((r) => {
			const rows = r.message || [];
			root.find("[data-rows]").html(rows.length ? rows.map((x) => `<tr>
				<td><a href="/app/employee/${encodeURIComponent(x.name)}">${esc(x.name)}</a></td>
				<td>${esc(x.employee_name)}</td><td>${esc(x.branch || "")}</td><td>${esc(x.department || "")}</td>
				<td>${esc(x.designation || "")}</td><td>${esc(x.date_of_joining || "")}</td><td>${esc(x.status)}</td></tr>`).join("")
				: `<tr><td colspan="7" class="rhh-muted">No employees yet. Use the add icon to add one.</td></tr>`);
		});
		root.find("[data-add]").on("click", () => frappe.ui.form.make_quick_entry("Employee", () => load(), null, {}));
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
