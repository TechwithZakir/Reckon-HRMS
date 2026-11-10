// Dashboard page: KPI overview, HR, Payroll and Analytics tabs with tiles and charts.
// Tabs shown depend on the role: managers see all four, payroll managers see KPI, Payroll and Analytics,
// and employees see the KPI overview.
frappe.pages["reckon-hrms-home"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({ parent: wrapper, title: "Dashboard", single_column: true });
	const root = $(`<div class="rhd"></div>`).appendTo(page.main);
	root.html(`<style>${STYLE}</style><div class="rhd-muted">Loading the dashboard…</div>`);
	frappe.call({ method: "reckon_hrms.api.home.get_home", type: "GET" })
		.then((r) => build(root, r.message))
		.catch(() => root.html(`<style>${STYLE}</style><div class="rhd-err">Could not load the dashboard.</div>`));
};

const STYLE = `
.rhd{padding:8px 0 40px}
.rhd-muted{color:var(--text-muted);font-size:13px}
.rhd-err{color:var(--red-500);padding:16px}
.rhd-head{display:flex;justify-content:space-between;align-items:flex-end;flex-wrap:wrap;gap:8px;margin-bottom:12px}
.rhd-title{font-size:20px;font-weight:600;margin:0}
.rhd-tabs{display:flex;gap:6px;flex-wrap:wrap;margin:8px 0 16px;border-bottom:1px solid var(--border-color)}
.rhd-tab{background:none;border:0;border-bottom:2px solid transparent;padding:8px 12px;color:var(--text-muted);font-weight:600;cursor:pointer}
.rhd-tab.active{color:var(--text-color);border-bottom-color:var(--primary)}
.rhd-section{margin-bottom:22px}
.rhd-section-title{font-size:14px;font-weight:700;text-transform:uppercase;letter-spacing:.05em;color:var(--text-muted);margin:0 0 10px;padding-bottom:6px;border-bottom:1px solid var(--border-color)}
.rhd-tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:12px;margin-bottom:14px}
.rhd-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(340px,1fr));gap:14px}
.rhd-wide{grid-column:1/-1}
.rhd-card{background:var(--card-bg);border:1px solid var(--border-color);border-radius:12px;padding:14px}
.rhd h4{font-size:12px;text-transform:uppercase;letter-spacing:.04em;color:var(--text-muted);margin:0 0 10px}
.rhd .tile{cursor:pointer}
.rhd .tile .v{font-size:22px;font-weight:700}
.rhd .tile .l{font-size:12px;color:var(--text-muted)}
.rhd .tile.warn .v{color:var(--orange-500)}
.rhd .tile.good .v{color:var(--green-500)}
.rhd .list{list-style:none;margin:0;padding:0}
.rhd .list li{display:flex;justify-content:space-between;gap:10px;align-items:center;padding:8px 0;border-bottom:1px solid var(--border-color);font-size:13px}
.rhd .list li:last-child{border-bottom:0}
.rhd .tag{font-size:12px;padding:2px 8px;border-radius:999px;background:var(--control-bg);white-space:nowrap}
.rhd .tag.warn{color:var(--orange-500)}
.rhd .tag.good{color:var(--green-500)}
.rhd .table{width:100%;border-collapse:collapse;font-size:13px}
.rhd .table th,.rhd .table td{text-align:right;padding:6px;border-bottom:1px solid var(--border-color)}
.rhd .table th:first-child,.rhd .table td:first-child{text-align:left}
.rhd .bar{height:8px;background:var(--control-bg);border-radius:999px;overflow:hidden;margin:8px 0 12px}
.rhd .bar>span{display:block;height:100%;background:var(--primary)}
.rhd .check{display:inline-block;width:14px;height:14px;border-radius:50%;border:2px solid var(--border-color);margin-right:8px;vertical-align:middle}
.rhd .check.done{background:var(--green-500);border-color:var(--green-500)}
`;

const TABS = {
	kpi: "KPI overview",
	hr: "HR",
	payroll: "Payroll",
	analytics: "HR analytics",
};

function esc(text) {
	return frappe.utils.escape_html(String(text == null ? "" : text));
}

function money(v) {
	return Number(v || 0).toLocaleString(undefined, { maximumFractionDigits: 0 });
}

function tile(k) {
	const route = k.route ? ` data-route="${esc(k.route)}"` : "";
	return `<div class="rhd-card tile ${esc(k.tone || "")}"${route}><div class="v">${esc(k.value)}</div><div class="l">${esc(k.label)}</div></div>`;
}

function tabs_for(d) {
	if (d.view === "manager") return ["kpi", "hr", "payroll", "analytics"];
	if (d.view === "payroll") return ["kpi", "payroll", "analytics"];
	return ["kpi"];
}

// One page: every section available to the role, stacked under its heading.
function build(root, d) {
	const available = tabs_for(d);
	const title = d.view === "self" ? `Hi, ${esc(d.employee_name || "there")}` : `${esc(d.company)} · ${d.view === "payroll" ? "Payroll dashboard" : "HR dashboard"}`;
	const section = (key, body) => `<section class="rhd-section"><h3 class="rhd-section-title">${TABS[key]}</h3>${body}</section>`;
	root.html(`<style>${STYLE}</style>
		<div class="rhd-head"><div><h2 class="rhd-title">${title}</h2><div class="rhd-muted">${esc(d.greeting_date)}</div></div></div>
		${available.includes("analytics") ? section("analytics", panel_analytics(d)) : ""}
		${available.includes("hr") ? section("hr", panel_hr(d)) : ""}
		${section("kpi", panel_kpi(d))}
		${available.includes("payroll") ? section("payroll", panel_payroll(d)) : ""}`);

	root.find("[data-route]").on("click", function () {
		window.location.href = $(this).attr("data-route");
	});
	available.forEach((key) => draw_charts(root, d, key));
}

function panel_kpi(d) {
	const todos = d.todos.length
		? d.todos.map((t) => `<li><span>${esc(t.label)}</span><span class="tag ${esc(t.tone || "")}">${esc(t.value)}</span></li>`).join("")
		: `<li class="rhd-muted">Nothing waiting for you.</li>`;
	const pending = d.pending.length
		? d.pending.map((p) => `<li><span>${esc(p.title)}<div class="rhd-muted">${esc(p.detail)}</div></span><a href="${esc(p.route)}">${esc(p.type)}</a></li>`).join("")
		: `<li class="rhd-muted">No pending items.</li>`;
	const sugg = d.suggestions.map((s) => `<li>${esc(s)}</li>`).join("");
	return `<div class="rhd-tiles">${d.kpis.map(tile).join("")}</div>
		<div class="rhd-grid">
		</div>`;
}

function onboarding(o) {
	const pct = Math.round((100 * o.done) / o.total);
	const rows = o.steps.map((s) => `<li><span><span class="check ${s.done ? "done" : ""}"></span>${esc(s.label)}</span>
		${s.done ? `<span class="tag good">Done</span>` : `<a href="${esc(s.route)}">Set up</a>`}</li>`).join("");
	return `<div class="rhd-card"><h4>Setup and onboarding</h4><div class="rhd-muted">${o.done} of ${o.total} steps done</div>
		<div class="bar"><span style="width:${pct}%"></span></div><ul class="list">${rows}</ul></div>`;
}

function panel_hr(d) {
	const dep = d.detailed.departments || [];
	const emp = d.detailed.employees || [];
	const rows = emp.map((r) => `<tr><td>${esc(r.employee_name)}</td><td>${esc(r.department || "")}</td><td>${r.present}</td><td>${r.leave}</td><td>${r.absent}</td></tr>`).join("");
	return `<div class="rhd-grid">
		<div class="rhd-card"><h4>Headcount by department</h4><div id="chart-dept"></div></div>
		<div class="rhd-card"><h4>New joiners, last 6 months</h4><div id="chart-joiners"></div></div>
		<div class="rhd-card"><h4>Attendance status, last 30 days</h4><div id="chart-att-mix"></div></div>
		<div class="rhd-card"><h4>Department detail</h4><table class="table"><tr><th>Department</th><th>Headcount</th><th>Present today</th></tr>
			${dep.map((r) => `<tr><td>${esc(r.department)}</td><td>${r.headcount}</td><td>${r.present_today}</td></tr>`).join("")}</table></div>
		<div class="rhd-card rhd-wide"><h4>Employee KPIs, last 30 days</h4><div class="scroll"><table class="table">
			<tr><th>Employee</th><th>Department</th><th>Present</th><th>Leave</th><th>Absent</th></tr>${rows}</table></div></div>
	</div>`;
}

function panel_payroll(d) {
	const a = d.analytics || {};
	const unassigned = (d.detailed.unassigned_employees || []).map((e) => `<li>${esc(e)}</li>`).join("");
	return `<div class="rhd-grid">
		<div class="rhd-card rhd-wide"><h4>Gross, deductions and net pay, last 6 months</h4><div id="chart-payroll"></div></div>
		<div class="rhd-card"><h4>Deduction split this month</h4>${(a.deduction_mix || []).length
			? `<div id="chart-deductions"></div>` : `<div class="rhd-muted">No payroll run this month yet.</div>`}</div>
		<div class="rhd-card"><h4>Employees without a salary structure</h4>${unassigned
			? `<ul class="list">${unassigned}</ul>` : `<div class="rhd-muted">Everyone has a salary structure.</div>`}</div>
	</div>`;
}

function panel_analytics(d) {
	const a = d.analytics || {};
	return `<div class="rhd-grid">
		<div class="rhd-card rhd-wide"><h4>Attendance, last 14 days</h4><div id="chart-trend"></div></div>
		<div class="rhd-card"><h4>Leave taken this month, by type</h4>${(a.leave_mix || []).length
			? `<div id="chart-leave"></div>` : `<div class="rhd-muted">No approved leave this month.</div>`}</div>
		<div class="rhd-card"><h4>Attendance status, last 30 days</h4>${(a.attendance_mix || []).length
			? `<div id="chart-att-mix-a"></div>` : `<div class="rhd-muted">No attendance recorded yet.</div>`}</div>
		<div class="rhd-card rhd-wide"><h4>Net pay trend, last 6 months</h4>${(a.payroll_trend || []).length
			? `<div id="chart-net"></div>` : `<div class="rhd-muted">No payroll history yet.</div>`}</div>
	</div>`;
}

function chart(root, sel, opts) {
	const el = root.find(sel)[0];
	if (!el || !frappe.Chart) return;
	el.innerHTML = "";
	new frappe.Chart(el, Object.assign({ height: 240 }, opts));
}

// Charts draw once their tab is visible, so widths are right.
function draw_charts(root, d, key) {
	const a = d.analytics || {};
	if (key === "kpi") return;
	if (key === "hr" && d.detailed.departments) {
		const dep = d.detailed.departments;
		chart(root, "#chart-dept", { data: { labels: dep.map((r) => r.department), datasets: [{ name: "Headcount", values: dep.map((r) => r.headcount) }] }, type: "bar", colors: ["#6d4cff"] });
		chart(root, "#chart-joiners", { data: { labels: (a.joiners_trend || []).map((j) => j.month), datasets: [{ name: "Joiners", values: (a.joiners_trend || []).map((j) => j.joiners) }] }, type: "bar", colors: ["#2e9d6b"] });
		const mix = a.attendance_mix || [];
		if (mix.length) chart(root, "#chart-att-mix", { data: { labels: mix.map((m) => m.status), datasets: [{ name: "Days", values: mix.map((m) => m.count) }] }, type: "pie" });
	}
	if (key === "payroll") {
		const t = a.payroll_trend || [];
		if (t.length) chart(root, "#chart-payroll", { data: { labels: t.map((x) => x.month), datasets: [{ name: "Gross", values: t.map((x) => x.gross) }, { name: "Deductions", values: t.map((x) => x.deductions) }, { name: "Net", values: t.map((x) => x.net) }] }, type: "line", colors: ["#6d4cff", "#d24b4b", "#2e9d6b"] });
		const dm = a.deduction_mix || [];
		if (dm.length) chart(root, "#chart-deductions", { data: { labels: dm.map((x) => x.component), datasets: [{ name: "Amount", values: dm.map((x) => x.amount) }] }, type: "pie" });
	}
	if (key === "analytics") {
		const tr = a.attendance_trend || [];
		if (tr.length) chart(root, "#chart-trend", { data: { labels: tr.map((t) => t.date.slice(5)), datasets: [{ name: "Present", values: tr.map((t) => t.present) }, { name: "Absent", values: tr.map((t) => t.absent) }, { name: "On leave", values: tr.map((t) => t.leave) }] }, type: "line", colors: ["#2e9d6b", "#d24b4b", "#6d4cff"] });
		const lm = a.leave_mix || [];
		if (lm.length) chart(root, "#chart-leave", { data: { labels: lm.map((x) => x.leave_type), datasets: [{ name: "Days", values: lm.map((x) => x.days) }] }, type: "pie" });
		const am = a.attendance_mix || [];
		if (am.length) chart(root, "#chart-att-mix-a", { data: { labels: am.map((x) => x.status), datasets: [{ name: "Days", values: am.map((x) => x.count) }] }, type: "pie" });
		const nt = a.payroll_trend || [];
		if (nt.length) chart(root, "#chart-net", { data: { labels: nt.map((x) => x.month), datasets: [{ name: "Net pay", values: nt.map((x) => x.net) }] }, type: "bar", colors: ["#2e9d6b"] });
	}
}
