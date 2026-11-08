// Page 2 (Salary rules), read side: tax slabs, pay items, structures and who lacks a structure.
// Served at /desk/reckon-hrms/reckon-hrms-salary. Editing and the payslip preview come next.
frappe.pages["reckon-hrms-salary"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({ parent: wrapper, title: "Salary rules", single_column: true });
	const root = $(`<div class="rhs"></div>`).appendTo(page.main);
	const company = frappe.defaults.get_user_default("Company") || "";
	const esc = (t) => frappe.utils.escape_html(t == null ? "" : String(t));

	root.html(`
		<style>${STYLE}</style>
		<div class="rhs-muted">Step 2 of 3</div>
		<div class="rhs-card" id="summary"><h2>Who has a salary structure</h2><div class="rhs-muted">Loading…</div></div>
		<div class="rhs-card"><h2>Tax years <span class="rhs-map">Income Tax Slab</span></h2>
			<table class="rhs-table"><tbody id="slabs"></tbody></table>
			<div class="rhs-row"><a class="rhs-btn" href="/app/income-tax-slab/new">+ Add new</a><a class="rhs-btn" href="/app/income-tax-slab">List</a></div></div>
		<div class="rhs-card"><h2>What you pay and deduct <span class="rhs-map">Salary Component</span></h2>
			<table class="rhs-table"><thead><tr><th>Item</th><th>Kind</th><th>Cut for unpaid leave</th><th>Taxable</th></tr></thead><tbody id="comps"></tbody></table>
			<div class="rhs-row"><a class="rhs-btn" href="/app/salary-component/new">+ Add new</a><a class="rhs-btn" href="/app/salary-component">List</a></div></div>
		<div class="rhs-card"><h2>Salary structures <span class="rhs-map">Salary Structure</span></h2>
			<table class="rhs-table"><thead><tr><th>Name</th><th>Pay</th><th>Active</th><th>People</th></tr></thead><tbody id="structs"></tbody></table>
			<div class="rhs-row"><a class="rhs-btn" href="/app/salary-structure/new">+ Add new</a><a class="rhs-btn" href="/app/salary-structure">List</a></div></div>
		<div class="rhs-card"><h2>Give a salary structure to everyone without one <span class="rhs-map">Salary Structure Assignment</span></h2>
			<div class="rhs-muted">Each person without a structure gets the one you pick, from the date you choose. People who already have it are skipped.</div>
			<div class="rhs-row"><label>Salary structure <select id="bkStruct"></select></label>
			<label>Base salary (৳) <input id="bkBase" type="number" min="1" step="500" value="60000"></label>
			<label>From <input id="bkDate" type="date"></label></div>
			<div class="rhs-row"><button class="rhs-btn rhs-pri" id="bkGo" type="button">Assign to everyone without a structure</button></div>
			<div id="bkOut" class="rhs-muted" style="margin-top:10px"></div></div>
		<div class="rhs-card"><div class="rhs-row"><a class="rhs-btn rhs-pri" href="/desk/reckon-hrms/reckon-hrms-run">Continue to run salary</a></div></div>`);

		// Bulk assign: starts a background job, then polls its progress every 3 seconds.
		root.find("#bkDate").val(frappe.datetime.get_today());
		frappe.call({ method: "reckon_hrms.api.salary.list_structures", args: { company }, type: "GET" }).then((r) => {
			root.find("#bkStruct").html(r.message.rows.map((x) => `<option value="${esc(x.name)}">${esc(x.name)}</option>`).join(""));
		});
		let poll = null;
		const showProgress = (s) => {
			const line = s.state === "done"
				? `Done: ${s.created} given a structure, ${s.skipped} already had one.` + (s.failed.length ? ` ${s.failed.length} could not be done.` : "")
				: `Working… ${s.done} of ${s.total}, ${s.created} done so far.`;
			root.find("#bkOut").text(line);
			if (s.state === "done") clearInterval(poll);
		};
		root.find("#bkGo").on("click", () => {
			const args = { structure: root.find("#bkStruct").val(), base: root.find("#bkBase").val(),
				from_date: root.find("#bkDate").val(), company };
			frappe.call({ method: "reckon_hrms.api.salary.bulk_assign", args })
				.then((r) => {
					root.find("#bkOut").text("Starting…");
					clearInterval(poll);
					poll = setInterval(() => frappe.call({ method: "reckon_hrms.api.salary.get_bulk_progress", args: { job: r.message.job }, type: "GET" }).then((p) => showProgress(p.message)), 3000);
				})
				.catch((e) => root.find("#bkOut").html(`<span class="rhs-err">${esc((e && e.message) || "Could not start the assignment.")}</span>`));
		});

	const call = (method, args) => frappe.call({ method: "reckon_hrms.api." + method, args: args || {}, type: "GET" });
	const yesno = (v) => (v ? "Yes" : "No");
	const money = (n) => Number(n || 0).toLocaleString("en-IN", { maximumFractionDigits: 2 });

	// Payslip preview: same formula engine as Salary Slip, nothing saved. Debounced 300 ms.
	const preview = $(`<div class="rhs-card"><h2>Payslip preview</h2>
		<div class="rhs-row"><label>Salary structure <select id="pvStruct"></select></label>
		<label>Base salary per month (৳) <input id="pvBase" type="number" min="0" step="500" value="60000"></label></div>
		<div id="pvOut" class="rhs-muted" style="margin-top:10px"></div></div>`);
	root.find(".rhs-card").first().after(preview);
	let timer = null;
	const runPreview = () => {
		const structure = preview.find("#pvStruct").val();
		const base = preview.find("#pvBase").val();
		if (!structure) return;
		call("salary.preview_payslip", { structure, base }).then((r) => {
			const p = r.message;
			const rows = (list) => list.map((x) => `<tr><td>${esc(x.component)}</td><td style="text-align:right">${money(x.amount)}</td></tr>`).join("");
			preview.find("#pvOut").html(`<table class="rhs-table"><tbody>${rows(p.earnings)}
				<tr><th>Gross pay</th><th style="text-align:right">${money(p.gross)}</th></tr>${rows(p.deductions)}
				<tr><th>Take home before tax</th><th style="text-align:right">${money(p.take_home_before_tax)}</th></tr></tbody></table>
				<div class="rhs-muted" style="margin-top:6px">${esc(p.note)}</div>`);
		}).catch(() => preview.find("#pvOut").html(`<div class="rhs-err">Could not work out the preview for these values.</div>`));
	};
	preview.find("#pvBase").on("input", () => { clearTimeout(timer); timer = setTimeout(runPreview, 300); });
	preview.find("#pvStruct").on("change", runPreview);
	call("salary.list_structures", { company }).then((r) => {
		preview.find("#pvStruct").html(r.message.rows.map((x) => `<option value="${esc(x.name)}">${esc(x.name)}</option>`).join(""));
		runPreview();
	});

	call("salary.assignment_summary", { company }).then((r) => {
		const s = r.message;
		root.find("#summary").html(`<h2>Who has a salary structure</h2>
			<div class="rhs-sum"><div><span class="rhs-muted">Active people</span><b>${s.active}</b></div>
			<div><span class="rhs-muted">With a structure</span><b>${s.with_structure}</b></div>
			<div><span class="rhs-muted">Without a structure</span><b class="${s.without_structure ? "rhs-warn" : ""}">${s.without_structure}</b></div></div>
			${s.without_structure ? `<div class="rhs-alert">${s.without_structure} people have no salary structure and will be skipped in the salary run.
			<a href="${esc(s.filter_route)}">Open assignments</a></div>` : ""}`);
	}).catch(() => root.find("#summary").append(`<div class="rhs-err">Could not load the summary.</div>`));

	call("salary.list_tax_slabs", { company }).then((r) => {
		const rows = r.message.rows;
		root.find("#slabs").html(rows.length ? rows.map((x) =>
			`<tr><td><a href="/app/income-tax-slab/${esc(x.name)}">${esc(x.name)}</a></td><td>From ${esc(x.effective_from)}</td></tr>`).join("")
			: `<tr><td class="rhs-muted">No tax slab yet. Add one, or confirm your rates with your tax adviser.</td></tr>`);
	});

	call("salary.list_components", {}).then((r) => {
		const rows = r.message.rows;
		root.find("#comps").html(rows.map((x) =>
			`<tr><td><a href="/app/salary-component/${esc(x.name)}">${esc(x.name)}</a></td><td>${esc(x.type)}</td>
			<td>${yesno(x.depends_on_payment_days)}</td><td>${yesno(x.is_tax_applicable)}</td></tr>`).join("")
			|| `<tr><td class="rhs-muted" colspan="4">No pay items yet.</td></tr>`);
	});

	call("salary.list_structures", { company }).then((r) => {
		const rows = r.message.rows;
		root.find("#structs").html(rows.map((x) =>
			`<tr><td><a href="/app/salary-structure/${esc(x.name)}">${esc(x.name)}</a></td><td>${esc(x.payroll_frequency)}</td>
			<td>${yesno(x.is_active === "Yes" || x.is_active === 1)}</td><td>${x.people}</td></tr>`).join("")
			|| `<tr><td class="rhs-muted" colspan="4">No salary structure yet.</td></tr>`);
	});
};

const STYLE = `
.rhs{max-width:900px;padding:8px 0 40px}
.rhs-muted{color:var(--text-muted);font-size:13px}
.rhs-card{background:var(--card-bg);border:1px solid var(--border-color);border-radius:12px;padding:16px;margin-top:14px}
.rhs-card h2{font-size:15px;margin:0 0 10px;display:flex;gap:8px;align-items:center}
.rhs-map{font:500 11px monospace;background:var(--control-bg);color:var(--text-muted);padding:1px 6px;border-radius:4px;display:none}
body.map .rhs-map{display:inline-block}
.rhs-table{width:100%;border-collapse:collapse;font-size:13px}
.rhs-table th,.rhs-table td{text-align:left;padding:6px 8px;border-bottom:1px solid var(--border-color)}
.rhs-sum{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px}
.rhs-sum b{display:block;font-size:20px}
.rhs-warn{color:var(--orange-500)}
.rhs-alert{margin-top:10px;background:var(--control-bg);border-radius:8px;padding:10px;font-size:13px}
.rhs-row{display:flex;flex-wrap:wrap;gap:8px;margin-top:10px}
.rhs-btn{border:1px solid var(--border-color);background:var(--card-bg);color:var(--text-color);border-radius:8px;padding:6px 12px;text-decoration:none}
.rhs-pri{background:var(--primary);color:#fff;border-color:var(--primary)}
.rhs-err{color:var(--red-500);font-size:13px;margin-top:6px}
`;
