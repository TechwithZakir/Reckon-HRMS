// Monthly payroll payout: pay types, additions, deductions, basis and gross payable per employee,
// with checkbox selection and a bulk custom entry for the selected employees.
frappe.pages["reckon-hrms-payout"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({ parent: wrapper, title: "Monthly payroll payout", single_column: true });
	const root = $(`<div class="rhp"></div>`).appendTo(page.main);
	const today = frappe.datetime.get_today().slice(0, 7);
	root.html(`
		<style>
		.rhp{padding:8px 0 40px}
		.rhp .bar{display:flex;flex-wrap:wrap;gap:10px;align-items:flex-end;margin-bottom:12px}
		.rhp label{display:block;font-size:12px;color:var(--text-muted);margin-bottom:3px}
		.rhp input,.rhp select{height:32px;padding:0 8px;border:1px solid var(--border-color);border-radius:6px;background:var(--control-bg);color:var(--text-color)}
		.rhp button{height:32px;padding:0 14px;border:0;border-radius:6px;background:var(--primary);color:#fff;font-weight:600}
		.rhp .scroll{overflow-x:auto;border:1px solid var(--border-color);border-radius:10px}
		.rhp table{border-collapse:collapse;width:100%;font-size:13px;white-space:nowrap}
		.rhp th,.rhp td{padding:7px 9px;border-bottom:1px solid var(--border-color);text-align:right}
		.rhp th:first-child,.rhp td:first-child,.rhp th.l,.rhp td.l{text-align:left}
		.rhp thead th{background:var(--subtle-fg);position:sticky;top:0}
		.rhp tr.total td{font-weight:700}
		.rhp .muted{color:var(--text-muted);font-size:12px}
		.rhp .gen{color:var(--green-500)} .rhp .pending{color:var(--orange-500)}
		.rhp .note{margin:8px 0;font-size:13px}
		</style>
		<div class="bar">
			<div><label>Month</label><input type="month" id="month" value="${today}"></div>
			<div><button id="load" type="button">Load payout</button></div>
		</div>
		<div id="summary" class="muted"></div>
		<div class="bar" id="bulk" style="margin-top:10px;display:none">
			<div><label>Custom entry</label><select id="component"></select></div>
			<div><label>Amount</label><input type="number" id="amount" min="0" step="0.01" style="width:120px"></div>
			<div><label>Remarks</label><input type="text" id="remarks" style="width:220px"></div>
			<div><button id="apply" type="button">Apply to selected</button></div>
			<div class="muted" id="selcount"></div>
		</div>
		<div class="scroll" id="sheet"></div>`);

	const el = (id) => root.find("#" + id);
	let state = null;

	function money(v) {
		return Number(v || 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
	}

	function selected() {
		return root.find("input.rhp-pick:checked").map((_, i) => $(i).data("employee")).get();
	}

	function updateSelCount() {
		const n = selected().length;
		el("selcount").text(n ? `${n} selected` : "");
	}

	function render(data) {
		state = data;
		const comps = data.components || [];
		const earnOpts = comps.filter((c) => c.type === "Earning").map((c) => `<option value="${esc(c.name)}">${esc(c.name)} (earning)</option>`);
		const dedOpts = comps.filter((c) => c.type === "Deduction").map((c) => `<option value="${esc(c.name)}">${esc(c.name)} (deduction)</option>`);
		el("component").html(earnOpts.concat(dedOpts).join(""));
		el("bulk").show();

		const e = data.earning_names, d = data.deduction_names;
		const head = `<tr>
			<th class="l"><input type="checkbox" id="pick-all"></th>
			<th class="l">Employee</th><th>Base</th><th>Working days</th><th>Payment days</th>
			${e.map((n) => `<th>${esc(n)}</th>`).join("")}
			<th>Gross payable</th>
			${d.map((n) => `<th>${esc(n)}</th>`).join("")}
			<th>Total deduction</th><th>Net payable</th><th class="l">Status</th></tr>`;
		const body = data.rows.map((r) => `<tr>
			<td class="l"><input type="checkbox" class="rhp-pick" data-employee="${esc(r.employee)}"></td>
			<td class="l">${esc(r.employee_name)}<div class="muted">${esc(r.employee)}</div></td>
			<td>${money(r.base)}</td><td>${r.working_days || "–"}</td><td>${r.payment_days || "–"}</td>
			${e.map((n) => `<td>${money(r.earnings[n] || 0)}</td>`).join("")}
			<td><b>${money(r.gross)}</b></td>
			${d.map((n) => `<td>${money(r.deductions[n] || 0)}</td>`).join("")}
			<td>${money(r.total_deduction)}</td><td><b>${money(r.net)}</b></td>
			<td class="l ${r.status === "Generated" ? "gen" : "pending"}">${esc(r.status)}</td></tr>`).join("");
		const t = data.totals;
		const foot = `<tr class="total"><td class="l" colspan="2">Total</td><td>${money(t.base)}</td><td></td><td></td>
			${e.map(() => "<td></td>").join("")}<td>${money(t.gross)}</td>${d.map(() => "<td></td>").join("")}
			<td>${money(t.total_deduction)}</td><td>${money(t.net)}</td><td></td></tr>`;

		el("summary").text(`${data.company} · ${data.month} · ${data.rows.length} employees`);
		el("sheet").html(`<table><thead>${head}</thead><tbody>${body || `<tr><td class="l" colspan="8">No active employees.</td></tr>`}${foot}</tbody></table>`);
		el("pick-all").on("change", function () {
			root.find("input.rhp-pick").prop("checked", this.checked);
			updateSelCount();
		});
		root.find("input.rhp-pick").on("change", updateSelCount);
		updateSelCount();
	}

	function load() {
		const month = el("month").val();
		if (!month) return frappe.show_alert({ message: __("Choose a month."), indicator: "orange" });
		frappe.call({ method: "reckon_hrms.api.payout.payout_sheet", type: "GET", args: { month } })
			.then((r) => render(r.message));
	}

	el("load").on("click", load);

	el("apply").on("click", () => {
		const employees = selected();
		const component = el("component").val();
		const amount = parseFloat(el("amount").val());
		if (!employees.length) return frappe.show_alert({ message: __("Select employees first."), indicator: "orange" });
		if (!component || !(amount > 0)) return frappe.show_alert({ message: __("Choose a component and an amount above zero."), indicator: "orange" });
		frappe.confirm(
			__("Add {0} {1} for {2} employee(s) in {3}?", [amount, component, employees.length, el("month").val()]),
			() => frappe.call({
				method: "reckon_hrms.api.payout.bulk_custom_entry",
				args: { employees, month: el("month").val(), component, amount, remarks: el("remarks").val() },
			}).then((r) => {
				frappe.show_alert({ message: __("Added to {0} employees.", [r.message.created]), indicator: "green" });
				load();
			}));
	});

	load();
};

function esc(text) {
	return frappe.utils.escape_html(String(text == null ? "" : text));
}
