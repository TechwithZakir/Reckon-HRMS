// Setup (one page): Your company, Salary rules and Run salary, each a stage you can open at any time.
// Served at /desk/reckon-hrms/reckon-hrms-setup. Old stage URLs redirect here (see their page files).
frappe.pages["reckon-hrms-setup"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({ parent: wrapper, title: "Setup", single_column: true });
	const STAGES = [["company", "Your company"], ["salary", "Salary rules"], ["run", "Run salary"]];
	const shell = $(`<div class="rhs-shell" style="display:grid;grid-template-columns:190px minmax(0,1fr);gap:18px;align-items:start"></div>`).appendTo(page.main);
	const nav = $(`<nav class="rhs-stages" aria-label="Setup stages" style="display:grid;gap:4px;position:sticky;top:70px"></nav>`).appendTo(shell);
	const body = $(`<div class="rhs-body" style="min-width:0"></div>`).appendTo(shell);
	const style = `<style>.rhs-stages button{text-align:left;border:1px solid var(--border-color);background:var(--card-bg);color:var(--text-color);border-radius:8px;padding:8px 12px;cursor:pointer}.rhs-stages button[aria-current="step"]{background:var(--primary);color:#fff;border-color:var(--primary)}@media (max-width:760px){.rhs-shell{grid-template-columns:minmax(0,1fr)!important}.rhs-stages{position:static!important;grid-auto-flow:column;overflow-x:auto}}</style>`;
	nav.append(style);

	function go(key) {
		const stage = STAGES.find((s) => s[0] === key) ? key : "company";
		nav.find("button").attr("aria-current", null);
		nav.find(`[data-stage="${stage}"]`).attr("aria-current", "step");
		body.empty();
		window.ReckonSetupStages[stage](body);
		history.replaceState(null, "", `#${stage}`);
	}

	STAGES.forEach(([key, label]) => {
		$(`<button type="button" data-stage="${key}">${label}</button>`).on("click", () => go(key)).appendTo(nav);
	});

	const fromRoute = frappe.route_options && frappe.route_options.stage;
	const fromHash = (location.hash || "").replace("#", "");
	frappe.route_options = null;
	go(fromRoute || fromHash || "company");
};
