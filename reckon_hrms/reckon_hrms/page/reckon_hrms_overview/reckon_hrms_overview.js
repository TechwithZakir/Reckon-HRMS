// Home: numbers, get started, quick actions, recent items and reports, laid out like the Accounts home.
frappe.pages["reckon-hrms-overview"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({ parent: wrapper, title: __("Home"), single_column: true });
	page.add_inner_button(__("Refresh"), () => load());
	const $body = $('<div class="rhh-home"></div>').appendTo(page.main);
	const esc = (v) => frappe.utils.escape_html(v == null ? "" : String(v));

	const ACTIONS = [
		{ label: __("New Employee"), hint: __("Add a person"), icon: "user-plus", run: () => frappe.new_doc("Employee") },
		{ label: __("Check in / out"), hint: __("Record your attendance"), icon: "log-in", run: () => frappe.set_route("reckon-hrms-checkin") },
		{ label: __("Mark Attendance"), hint: __("For one day"), icon: "user-check", run: () => frappe.new_doc("Attendance") },
		{ label: __("Leave Application"), hint: __("Apply for leave"), icon: "calendar-days", run: () => frappe.new_doc("Leave Application") },
		{ label: __("Expense Claim"), hint: __("Claim an expense"), icon: "receipt", run: () => frappe.new_doc("Expense Claim") },
		{ label: __("Payroll Studio"), hint: __("Set up and run salary"), icon: "wallet", run: () => frappe.set_route("reckon-hrms-setup") },
		{ label: __("HR Studio"), hint: __("People, leave and calendar"), icon: "users", run: () => frappe.set_route("reckon-hrms-hr-studio") },
		{ label: __("Dashboard"), hint: __("Charts and trends"), icon: "gauge", run: () => frappe.set_route("reckon-hrms-home") },
	];

	function table(title, rows, columns, doctype, empty) {
		const body = rows.length
			? rows.map((row) => `<tr>${columns.map((col) => `<td>${col(row)}</td>`).join("")}</tr>`).join("")
			: `<tr><td class="rhh-muted" colspan="${columns.length}">${esc(empty)}</td></tr>`;
		return `<section class="rhh-card"><header><h4>${esc(title)}</h4><a href="/app/${frappe.router.slug(doctype)}">${esc(__("View all"))}</a></header>
			<table class="rhh-table"><tbody>${body}</tbody></table></section>`;
	}

	function render(d) {
		const pending = (d.checklist || []).filter((s) => !s.done);
		$body.html(`
			<div class="rhh-hello"><h3>${esc(d.company || __("Welcome"))}</h3><p>${esc(frappe.datetime.str_to_user(d.today))}</p></div>
			${(d.kpis || []).length ? `<div class="rhh-kpis">${d.kpis.map((k) => `<a class="rhh-kpi ${esc(k.tone)}" href="${esc(k.route)}"><span>${esc(k.label)}</span><strong>${esc(k.value)}</strong></a>`).join("")}</div>` : ""}
			${pending.length ? `<section class="rhh-card"><header><h4>${esc(__("Get started"))}</h4>
				<span class="rhh-muted">${esc(__("{0} of {1} done", [d.checklist.length - pending.length, d.checklist.length]))}</span></header>
				<div class="rhh-steps">${d.checklist.map((s) => `<a class="rhh-step ${s.done ? "is-done" : ""}" href="${esc(s.route)}"><span class="rhh-tick">${s.done ? "✓" : ""}</span>${esc(s.label)}</a>`).join("")}</div></section>` : ""}
			<section class="rhh-actions">${ACTIONS.map((a, i) => `<button class="rhh-action" data-action="${i}">
				<span class="rhh-action-icon">${frappe.utils.icon(a.icon, "md")}</span><span><strong>${esc(a.label)}</strong><small>${esc(a.hint)}</small></span></button>`).join("")}</section>
			${d.view === "self" ? "" : `<div class="rhh-grid">
				${table(__("Recent leave"), d.recent_leaves || [], [
					(r) => `<a href="/app/leave-application/${encodeURIComponent(r.name)}">${esc(r.employee_name)}</a>`, (r) => esc(r.leave_type),
					(r) => esc(`${r.from_date} → ${r.to_date}`), (r) => `<span class="indicator-pill ${r.status === "Approved" ? "green" : r.status === "Rejected" ? "red" : "orange"}">${esc(__(r.status))}</span>`,
				], "Leave Application", __("No leave applications yet."))}
				${table(__("New people"), d.recent_joiners || [], [
					(r) => `<a href="/app/employee/${encodeURIComponent(r.name)}">${esc(r.employee_name)}</a>`, (r) => esc(r.date_of_joining),
				], "Employee", __("Add your first employee."))}
				<section class="rhh-card"><header><h4>${esc(__("Reports"))}</h4></header>
					<div class="rhh-reports">${(d.reports || []).map((r) => `<a href="${esc(r.route)}">${esc(r.label)}</a>`).join("")}</div></section>
			</div>`}`);
	}

	$body.on("click", "[data-action]", function () { ACTIONS[Number($(this).attr("data-action"))].run(); });
	function load() { frappe.call({ method: "reckon_hrms.api.overview.get_overview", type: "GET" }).then((r) => render(r.message || {})); }

	$("<style>").text(`
		.rhh-home { padding: 4px 0 32px; }
		.rhh-hello h3 { margin: 0; font-size: 20px; }
		.rhh-hello p { margin: 2px 0 16px; color: var(--text-muted); }
		.rhh-kpis { display: grid; grid-template-columns: repeat(auto-fill, minmax(170px, 1fr)); gap: 12px; margin-bottom: 18px; }
		.rhh-kpi { display: block; padding: 14px 16px; border-radius: var(--border-radius-lg); background: var(--card-bg); border: 1px solid var(--border-color); color: var(--text-color); text-decoration: none; }
		.rhh-kpi:hover { border-color: var(--primary); text-decoration: none; }
		.rhh-kpi span { display: block; font-size: var(--text-sm); color: var(--text-muted); }
		.rhh-kpi strong { display: block; font-size: 22px; margin-top: 4px; }
		.rhh-kpi.is-green strong { color: var(--green-600, #2a9a00); }
		.rhh-kpi.is-blue strong { color: var(--blue-600, #0b78ab); }
		.rhh-kpi.is-amber strong { color: var(--orange-600, #b45309); }
		.rhh-actions { display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 10px; margin-bottom: 18px; }
		.rhh-action { display: flex; gap: 12px; align-items: center; text-align: left; padding: 12px 14px; border-radius: var(--border-radius-lg); border: 1px solid var(--border-color); background: var(--card-bg); cursor: pointer; }
		.rhh-action:hover { border-color: var(--primary); }
		.rhh-action-icon { width: 36px; height: 36px; border-radius: 10px; display: grid; place-items: center; background: var(--bg-light-gray, #f3f6fa); }
		.rhh-action strong { display: block; font-size: 14px; color: var(--text-color); }
		.rhh-action small { display: block; color: var(--text-muted); }
		.rhh-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 14px; }
		.rhh-card { border: 1px solid var(--border-color); border-radius: var(--border-radius-lg); background: var(--card-bg); padding: 14px 16px; margin-bottom: 14px; }
		.rhh-card header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
		.rhh-card h4 { margin: 0; font-size: 15px; }
		.rhh-table { width: 100%; font-size: 13px; }
		.rhh-table td { padding: 7px 4px; border-top: 1px solid var(--border-color); }
		.rhh-muted { color: var(--text-muted); }
		.rhh-reports { display: grid; grid-template-columns: repeat(2, 1fr); gap: 6px 12px; font-size: 13px; }
		.rhh-steps { display: flex; flex-wrap: wrap; gap: 8px; }
		.rhh-step { display: inline-flex; align-items: center; gap: 8px; padding: 8px 12px; border-radius: 999px; border: 1px dashed var(--border-color); background: var(--card-bg); font-size: 13px; color: var(--text-color); text-decoration: none; }
		.rhh-step.is-done { border-style: solid; color: var(--text-muted); text-decoration: line-through; }
		.rhh-tick { width: 18px; height: 18px; border-radius: 50%; border: 2px solid var(--border-color); display: grid; place-items: center; font-size: 11px; }
		.rhh-step.is-done .rhh-tick { background: var(--green-500, #3cd400); border-color: var(--green-500, #3cd400); color: #fff; }
	`).appendTo($body.parent());
	load();
};
