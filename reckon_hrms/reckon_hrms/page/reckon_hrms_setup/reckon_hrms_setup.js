// Payroll Studio (one page): Salary rules and Run salary, each a step you can open at any time.
// Served at /desk/reckon-hrms/reckon-hrms-setup. Old stage URLs redirect here (see their page files).
frappe.pages["reckon-hrms-setup"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({ parent: wrapper, title: "Payroll Studio", single_column: true });
	const STAGES = [["salary", "Salary rules"], ["run", "Run salary"]];
	const shell = $(`<div class="rhs-shell" style="display:block"></div>`).appendTo(page.main);
	const nav = $(`<nav class="rhs-stages" role="tablist" aria-label="Setup stages" style="display:flex;gap:4px;flex-wrap:wrap;border-bottom:1px solid var(--border-color);margin:10px 0 14px"></nav>`).appendTo(shell);
	const body = $(`<div class="rhs-body" style="min-width:0"></div>`).appendTo(shell);
	const style = `<style>.rhs-stages button{border:0;border-bottom:2px solid transparent;background:none;color:var(--text-muted);padding:10px 16px;cursor:pointer;font-weight:500;font-size:14px}.rhs-stages button:hover{color:var(--text-color)}.rhs-stages button[aria-current="step"]{color:var(--primary);border-bottom-color:var(--primary);font-weight:600}.rhs-stages button:focus-visible{outline:2px solid var(--primary);outline-offset:2px}</style>`;
	nav.append(style);

	function go(key) {
		const stage = STAGES.find((s) => s[0] === key) ? key : "salary";
		nav.find("button").attr("aria-current", null);
		nav.find(`[data-stage="${stage}"]`).attr("aria-current", "step");
		body.empty();
		window.ReckonSetupStages[stage](body);
		history.replaceState(null, "", `#${stage}`);
	}

	STAGES.forEach(([key, label]) => {
		$(`<button type="button" role="tab" data-stage="${key}">${label}</button>`).on("click", () => go(key)).appendTo(nav);
	});

	const fromRoute = frappe.route_options && frappe.route_options.stage;
	const fromHash = (location.hash || "").replace("#", "");
	frappe.route_options = null;
	go(fromRoute || fromHash || "salary");
};
