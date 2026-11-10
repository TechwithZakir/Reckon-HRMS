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
		const PAGE = 24;
		const state = { rows: [], view: "grid", page: 0, group: "", f: { q: "", status: "", missingOnly: false, branch: "", department: "" } };
		const root = $(`<div class="hrs-emp">
			<style>
			.hrs-emp .hrs-top{display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin:6px 0 14px}
			.hrs-emp .hrs-search{flex:1 1 260px;min-width:200px}
			.hrs-emp .hrs-cards{display:grid;grid-template-columns:repeat(auto-fill,minmax(240px,1fr));gap:14px}
			.hrs-emp .hrs-card{border:1px solid var(--border-color);border-radius:10px;background:var(--card-bg);display:flex;gap:12px;padding:12px;min-height:110px;text-decoration:none;color:inherit}
			.hrs-emp .hrs-card:hover{border-color:var(--primary)}
			.hrs-emp .hrs-av{width:64px;height:64px;border-radius:8px;flex:none;background:var(--control-bg);display:grid;place-items:center;font-weight:600;font-size:20px;color:var(--text-muted);overflow:hidden}
			.hrs-emp .hrs-av img{width:100%;height:100%;object-fit:cover}
			.hrs-emp .hrs-info{min-width:0;font-size:12.5px;color:var(--text-muted)}
			.hrs-emp .hrs-info b{display:block;color:var(--text-color);font-size:14px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
			.hrs-emp .hrs-group{font-weight:600;margin:16px 0 8px;font-size:13px;color:var(--text-muted)}
			.hrs-emp .hrs-pager{display:flex;justify-content:space-between;align-items:center;margin-top:14px;font-size:13px;color:var(--text-muted)}
			</style>
			<div class="hrs-top">
				<button type="button" class="btn btn-primary btn-sm" data-create>${frappe.utils.icon ? frappe.utils.icon("add", "sm") : "+"} Create</button>
				<input type="search" class="form-control hrs-search" data-f="q" placeholder="Search name, ID or job title" aria-label="Search">
				<select class="form-control" style="width:auto" data-f="branch" aria-label="Branch"><option value="">All branches</option></select>
				<select class="form-control" style="width:auto" data-f="department" aria-label="Department"><option value="">All departments</option></select>
				<select class="form-control" style="width:auto" data-f="status" aria-label="Status"><option value="">All statuses</option><option>Active</option><option>Inactive</option><option>Suspended</option><option>Left</option></select>
				<div class="checkbox" style="margin:0"><label><input type="checkbox" data-f="missingOnly"> <span class="label-area">Missing details</span></label></div>
				<select class="form-control" style="width:auto" data-group aria-label="Group by"><option value="">Group by: none</option><option value="department">Department</option><option value="branch">Branch</option><option value="designation">Job title</option></select>
				<span class="btn-group" role="group"><button type="button" class="btn btn-default btn-sm" data-view="grid" aria-pressed="true">Cards</button><button type="button" class="btn btn-default btn-sm" data-view="list" aria-pressed="false">List</button></span>
			</div>
			<div data-main></div>
			<div class="hrs-pager"><span data-count></span><span><button type="button" class="btn btn-default btn-sm" data-prev>Previous</button> <button type="button" class="btn btn-default btn-sm" data-next>Next</button></span></div>
		</div>`).appendTo(parent);

		const missing = (r) => [!r.branch && "branch", !r.department && "department", !r.designation && "job title"].filter(Boolean);
		const initials = (n) => (n || "?").split(" ").filter(Boolean).slice(0, 2).map((w) => w[0]).join("").toUpperCase();
		const matches = (r) => {
			const f = state.f;
			if (f.q && !`${r.name} ${r.employee_name} ${r.designation || ""}`.toLowerCase().includes(f.q.toLowerCase())) return false;
			if (f.status && r.status !== f.status) return false;
			if (f.branch && r.branch !== f.branch) return false;
			if (f.department && r.department !== f.department) return false;
			if (f.missingOnly && !missing(r).length) return false;
			return true;
		};
		const card = (r) => `<a class="hrs-card" href="/app/employee/${encodeURIComponent(r.name)}">
			<div class="hrs-av">${r.image ? `<img src="${esc(r.image)}" alt="">` : esc(initials(r.employee_name))}</div>
			<div class="hrs-info"><b>${esc(r.employee_name)}</b>${esc(r.designation || "No job title")}<br>${esc(r.department || "No department")}<br>${esc(r.branch || "No branch")}
			${missing(r).length ? `<br><span class="indicator-pill orange">Missing ${esc(missing(r).join(", "))}</span>` : ""}</div></a>`;
		const row = (r) => `<tr><td><a href="/app/employee/${encodeURIComponent(r.name)}">${esc(r.name)}</a></td><td>${esc(r.employee_name)}</td>
			<td>${esc(r.designation || "—")}</td><td>${esc(r.department || "—")}</td><td>${esc(r.branch || "—")}</td>
			<td>${esc(r.date_of_joining || "")}</td><td>${esc(r.status)}</td></tr>`;

		function main() {
			const list = state.rows.filter(matches);
			const pages = Math.max(1, Math.ceil(list.length / PAGE));
			state.page = Math.min(state.page, pages - 1);
			const slice = list.slice(state.page * PAGE, state.page * PAGE + PAGE);
			let html;
			if (state.view === "grid") {
				const key = state.group;
				const groups = key ? slice.reduce((m, r) => { const g = r[key] || "—"; (m[g] = m[g] || []).push(r); return m; }, {}) : { "": slice };
				html = Object.keys(groups).sort().map((g) => (g ? `<div class="hrs-group">${esc(g)}</div>` : "") +
					`<div class="hrs-cards">${groups[g].map(card).join("")}</div>`).join("");
				if (!slice.length) html = `<div class="text-muted" style="padding:20px">No employees match these filters.</div>`;
			} else {
				html = `<table class="table table-bordered" style="font-size:13px"><thead><tr><th>ID</th><th>Name</th><th>Job title</th><th>Department</th><th>Branch</th><th>Joined</th><th>Status</th></tr></thead>
					<tbody>${slice.map(row).join("") || `<tr><td colspan="7" class="text-muted">No employees match these filters.</td></tr>`}</tbody></table>`;
			}
			root.find("[data-main]").html(html);
			const from = list.length ? state.page * PAGE + 1 : 0;
			const to = from ? from + slice.length - 1 : 0;
			root.find("[data-count]").text(`${from}–${to} of ${list.length} employees`);
			root.find("[data-prev]").prop("disabled", state.page === 0);
			root.find("[data-next]").prop("disabled", state.page >= pages - 1);
		}

		root.on("input change", "[data-f]", function () {
			state.f[this.dataset.f] = this.type === "checkbox" ? this.checked : this.value.trim();
			state.page = 0; main();
		});
		root.on("change", "[data-group]", function () { state.group = this.value; main(); });
		root.on("click", "[data-view]", function () {
			state.view = this.dataset.view;
			root.find("[data-view]").attr("aria-pressed", "false");
			$(this).attr("aria-pressed", "true");
			main();
		});
		root.find("[data-prev]").on("click", () => { state.page--; main(); });
		root.find("[data-next]").on("click", () => { state.page++; main(); });
		root.find("[data-create]").on("click", () => frappe.ui.form.make_quick_entry("Employee", () => load(), null, {}));

		function fill(field, values) {
			root.find(`select[data-f="${field}"] option:not(:first-child)`).remove();
			root.find(`select[data-f="${field}"]`).append(values.map((v) => `<option>${esc(v)}</option>`).join(""));
		}

		function load() {
			frappe.call({ method: "frappe.client.get_list", args: {
				doctype: "Employee", fields: ["name", "employee_name", "branch", "department", "designation", "date_of_joining", "status", "image"],
				order_by: "employee_name asc", limit_page_length: 2000 } }).then((r) => {
				state.rows = r.message || [];
				const uniq = (k) => [...new Set(state.rows.map((x) => x[k]).filter(Boolean))].sort();
				fill("branch", uniq("branch"));
				fill("department", uniq("department"));
				main();
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
