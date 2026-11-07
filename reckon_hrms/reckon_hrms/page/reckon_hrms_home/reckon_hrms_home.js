// Reckon HRMS home: role-specific dashboard, rendered inside the Desk so the left nav is the Desk's.
frappe.pages["reckon-hrms-home"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({ parent: wrapper, title: "My home", single_column: true });
	const root = $(`<div class="rhrms-home"></div>`).appendTo(page.main);
	root.html(`<style>${STYLE}</style><div class="rhrms-muted">Loading your home…</div>`);

	frappe.call({ method: "reckon_hrms.api.home.get_home", type: "GET" })
		.then((r) => render(root, r.message))
		.catch(() => root.append(`<div class="rhrms-err">Could not load your home page.</div>`));
};

const VIEW_TITLES = { manager: "HR dashboard", payroll: "Payroll dashboard", self: "My workspace" };

function esc(text) {
	return frappe.utils.escape_html(String(text == null ? "" : text));
}

function kpi(k) {
	const route = k.route ? ` data-route="${esc(k.route)}"` : "";
	return `<div class="rhrms-card rhrms-kpi ${esc(k.tone || "")}"${route}>
		<div class="v">${esc(k.value)}</div><div class="l">${esc(k.label)}</div></div>`;
}

function listRows(items, empty, render_row) {
	if (!items.length) return `<li class="rhrms-muted">${esc(empty)}</li>`;
	return items.map(render_row).join("");
}

function onboarding_html(o) {
	if (!o.total) return "";
	const pct = Math.round((100 * o.done) / o.total);
	const rows = o.steps.map((s) => `<li>
		<span><span class="rhrms-check ${s.done ? "done" : ""}"></span>${esc(s.label)}</span>
		${s.done ? `<span class="rhrms-tag good">Done</span>` : `<a href="${esc(s.route)}">Set up</a>`}</li>`).join("");
	return `<div class="rhrms-card"><h4>Setup and onboarding</h4>
		<div class="rhrms-muted">${o.done} of ${o.total} steps done</div>
		<div class="rhrms-bar"><span style="width:${pct}%"></span></div>
		<ul class="rhrms-list">${rows}</ul></div>`;
}

function detail(d) {
	if (d.view === "manager") {
		const dep = d.detailed.departments.map((r) => `<tr><td>${esc(r.department)}</td><td>${r.headcount}</td><td>${r.present_today}</td></tr>`).join("");
		const emp = d.detailed.employees.map((r) => `<tr><td>${esc(r.employee_name)}</td><td>${esc(r.department || "")}</td><td>${r.present}</td><td>${r.leave}</td><td>${r.absent}</td></tr>`).join("");
		return `<table class="rhrms-table"><tr><th>Department</th><th>Headcount</th><th>Present today</th></tr>${dep}</table>
			<table class="rhrms-table" style="margin-top:12px"><tr><th>Employee</th><th>Department</th><th>Present</th><th>Leave</th><th>Absent</th></tr>${emp}</table>`;
	}
	if (d.view === "payroll") {
		return d.detailed.unassigned_employees.length
			? `<ul class="rhrms-list">${d.detailed.unassigned_employees.map((e) => `<li>${esc(e)}</li>`).join("")}</ul>`
			: `<div class="rhrms-muted">Everyone has a salary structure.</div>`;
	}
	return d.detailed.upcoming_holidays.length
		? `<ul class="rhrms-list">${d.detailed.upcoming_holidays.map((h) => `<li>${esc(h.date)} · ${esc(h.name || "Holiday")}</li>`).join("")}</ul>`
		: `<div class="rhrms-muted">No upcoming holidays in your calendar.</div>`;
}

// Analytics charts use Frappe's bundled frappe.Chart when it is available on the page.
function draw_analytics(root, d) {
	if (!d.analytics || !window.frappe || !frappe.Chart) return;
	const trend = d.analytics.attendance_trend;
	const trendEl = root.find("#rhrms-trend")[0];
	if (trendEl) {
		new frappe.Chart(trendEl, {
			data: {
				labels: trend.map((t) => t.date.slice(5)),
				datasets: [
					{ name: "Present", values: trend.map((t) => t.present) },
					{ name: "Absent", values: trend.map((t) => t.absent) },
					{ name: "On leave", values: trend.map((t) => t.leave) },
				],
			},
			type: "line",
			height: 220,
			colors: ["#2e9d6b", "#d24b4b", "#6d4cff"],
		});
	}
	const mix = d.analytics.leave_mix;
	const mixEl = root.find("#rhrms-mix")[0];
	if (mixEl && mix.length) {
		new frappe.Chart(mixEl, {
			data: { labels: mix.map((m) => m.leave_type), datasets: [{ name: "Days", values: mix.map((m) => m.days) }] },
			type: "pie",
			height: 220,
		});
	}
}

function detail_title(view) {
	if (view === "manager") return "Departments and employee KPIs (last 30 days)";
	if (view === "payroll") return "Employees without a salary structure";
	return "Upcoming holidays";
}

function render(root, d) {
	const title = d.view === "self" ? `Hi, ${esc(d.employee_name || "there")}` : `${esc(d.company)} · ${VIEW_TITLES[d.view]}`;
	root.html(`
		<style>${STYLE}</style>
		<div class="rhrms-muted">${esc(d.greeting_date)}</div>
		<h2 class="rhrms-title">${title}</h2>
		<div class="rhrms-kpis">${d.kpis.map(kpi).join("")}</div>
		<div class="rhrms-grid">
			${onboarding_html(d.onboarding)}
			<div class="rhrms-card"><h4>To do</h4><ul class="rhrms-list">${listRows(d.todos, "Nothing waiting for you.",
				(t) => `<li><span>${esc(t.label)}</span>${t.route
					? `<a href="${esc(t.route)}"><span class="rhrms-tag ${esc(t.tone || "")}">${esc(t.value)}</span></a>`
					: `<span class="rhrms-tag ${esc(t.tone || "")}">${esc(t.value)}</span>`}</li>`)}</ul></div>
			<div class="rhrms-card"><h4>Pending items</h4><ul class="rhrms-list">${listRows(d.pending, "No pending items.",
				(p) => `<li><span>${esc(p.title)}<div class="rhrms-muted">${esc(p.detail)}</div></span><a href="${esc(p.route)}">${esc(p.type)}</a></li>`)}</ul></div>
			<div class="rhrms-card"><h4>Suggestions</h4><ul class="rhrms-list">${listRows(d.suggestions, "No suggestions right now.",
				(s) => `<li>${esc(s)}</li>`)}</ul></div>
			<div class="rhrms-card rhrms-wide"><h4>${detail_title(d.view)}</h4>${detail(d)}</div>
			${d.analytics ? `<div class="rhrms-card rhrms-wide"><h4>Attendance, last 14 days</h4><div id="rhrms-trend"></div></div>
				<div class="rhrms-card"><h4>Leave taken this month, by type</h4>${d.analytics.leave_mix.length
					? `<div id="rhrms-mix"></div>` : `<div class="rhrms-muted">No approved leave this month.</div>`}</div>` : ""}
				<div class="rhrms-card rhrms-wide"><h4>Reports</h4><ul class="rhrms-list">${listRows(d.reports, "No reports.",
				(r) => `<li><a href="${esc(r.route)}">${esc(r.label)}</a></li>`)}</ul></div>
		</div>`);
	draw_analytics(root, d);
	root.find("[data-route]").on("click", function () {
		window.location.href = $(this).attr("data-route");
	});
}

const STYLE = `
.rhrms-home{padding:8px 0 40px}
.rhrms-home .rhrms-muted{color:var(--text-muted);font-size:13px}
.rhrms-home .rhrms-err{color:var(--red-500);padding:16px}
.rhrms-home .rhrms-title{font-size:20px;margin:4px 0 14px;font-weight:600}
.rhrms-home .rhrms-kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:12px;margin-bottom:14px}
.rhrms-home .rhrms-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(340px,1fr));gap:14px}
.rhrms-home .rhrms-wide{grid-column:1/-1}
.rhrms-home .rhrms-card{background:var(--card-bg);border:1px solid var(--border-color);border-radius:12px;padding:14px}
.rhrms-home h4{font-size:12px;text-transform:uppercase;letter-spacing:.04em;color:var(--text-muted);margin:0 0 10px}
.rhrms-home .rhrms-kpi{cursor:pointer}
.rhrms-home .rhrms-kpi .v{font-size:22px;font-weight:700}
.rhrms-home .rhrms-kpi .l{font-size:12px;color:var(--text-muted)}
.rhrms-home .rhrms-kpi.warn .v{color:var(--orange-500)}
.rhrms-home .rhrms-list{list-style:none;margin:0;padding:0}
.rhrms-home .rhrms-list li{display:flex;justify-content:space-between;gap:10px;align-items:center;padding:8px 0;border-bottom:1px solid var(--border-color);font-size:13px}
.rhrms-home .rhrms-list li:last-child{border-bottom:0}
.rhrms-home .rhrms-tag{font-size:12px;padding:2px 8px;border-radius:999px;background:var(--control-bg);white-space:nowrap}
.rhrms-home .rhrms-tag.warn{color:var(--orange-500)}
.rhrms-home .rhrms-tag.good{color:var(--green-500)}
.rhrms-home .rhrms-bar{height:8px;background:var(--control-bg);border-radius:999px;overflow:hidden;margin:8px 0 12px}
.rhrms-home .rhrms-bar>span{display:block;height:100%;background:var(--primary)}
.rhrms-home .rhrms-check{display:inline-block;width:14px;height:14px;border-radius:50%;border:2px solid var(--border-color);margin-right:8px;vertical-align:middle}
.rhrms-home .rhrms-check.done{background:var(--green-500);border-color:var(--green-500)}
.rhrms-home .rhrms-table{width:100%;border-collapse:collapse;font-size:13px}
.rhrms-home .rhrms-table th,.rhrms-home .rhrms-table td{text-align:left;padding:6px;border-bottom:1px solid var(--border-color)}
`;
