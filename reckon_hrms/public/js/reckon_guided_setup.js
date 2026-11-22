// Guided setup for HR Studio and Payroll Studio: the company's industry with a preview of what will be pre-loaded,
// and "Ask AI" buttons that open Ask Aura AI with the question already filled in (it answers from the HR industry guide).
// window.ReckonGuidedSetup(parent, "hr" | "payroll"); window.ReckonAskAi(question, studio) for the page header buttons.
(function () {
	const esc = (t) => frappe.utils.escape_html(t == null ? "" : String(t));
	const current = { label: "", segment: "" };

	function askAi(question) {
		const industry = current.label ? ` My industry is ${current.label}.` : "";
		if (window.aura && window.aura.ask_about) window.aura.ask_about(question + industry);
		else frappe.show_alert({ message: __("Ask AI is not available on this page."), indicator: "orange" });
	}
	window.ReckonAskAi = function (question) { askAi(question); };

	const STEPS = {
		hr: [
			["Choose your industry", "Guide me through choosing my industry in HR Studio and what it pre-loads."],
			["Departments and job titles", "Which departments and job titles should I keep or add for my company?"],
			["Holidays and leave", "Help me set up the holiday list and leave types for my company. Do not invent leave days."],
			["Shifts and attendance", "How should I set up shifts and attendance (devices or app check-in) for my company?"],
			["Add your people", "How do I add my employees and what must each one have before payroll?"],
		],
		payroll: [
			["Confirm pay items", "Which pay items did my industry load, and which should I use? Explain each one."],
			["Salary structure", "Help me design a salary structure from my pay items without guessing amounts."],
			["Give structures to people", "How do I give the salary structure to my employees, and what start date should it have?"],
			["Run salary", "Walk me through running salary for a month: draft, review, approve and pay."],
			["Before the first run", "What should I check before my first payroll run?"],
		],
	};
	const STUDIO_ASK = {
		hr: "Guide me through setting up HR Studio step by step for my company.",
		payroll: "Guide me through setting up Payroll Studio step by step for my company.",
	};
	window.ReckonStudioAsk = function (studio) { askAi(STUDIO_ASK[studio] || STUDIO_ASK.hr); };

	const STYLE = `<style>
	.rgs{max-width:900px;padding:8px 0 40px}
	.rgs-card{background:var(--card-bg);border:1px solid var(--border-color);border-radius:12px;padding:16px;margin-top:14px}
	.rgs-card h2{font-size:15px;margin:0 0 6px}
	.rgs-muted{color:var(--text-muted);font-size:13px}
	.rgs-row{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin-top:10px}
	.rgs-groups{display:grid;grid-template-columns:repeat(auto-fit,minmax(250px,1fr));gap:12px;margin-top:12px}
	.rgs-group{border:1px solid var(--border-color);border-radius:10px;padding:10px 12px}
	.rgs-group h3{font-size:13px;margin:0 0 6px;display:flex;justify-content:space-between;gap:8px}
	.rgs-chips{display:flex;flex-wrap:wrap;gap:5px}
	.rgs-chip{font-size:12px;border-radius:99px;padding:2px 9px;background:var(--control-bg);color:var(--text-muted)}
	.rgs-chip.new{background:var(--green-100,#e4f5e9);color:var(--green-700,#1e6b3a);font-weight:600}
	.rgs-chip.skipped{background:var(--orange-100,#fff1db);color:var(--orange-700,#8a5300)}
	.rgs-count{font-weight:600;color:var(--green-700,#1e6b3a);font-size:12px}
	.rgs-steps{list-style:none;margin:8px 0 0;padding:0;counter-reset:s}
	.rgs-steps li{display:flex;justify-content:space-between;align-items:center;gap:10px;padding:9px 0;border-bottom:1px dotted var(--border-color);counter-increment:s}
	.rgs-steps li:last-child{border-bottom:0}
	.rgs-steps li span::before{content:counter(s);display:inline-grid;place-items:center;width:22px;height:22px;border-radius:50%;background:var(--control-bg);margin-right:10px;font-size:12px;font-weight:600}
	.rgs-ask{display:inline-flex;gap:6px;align-items:center}
	.rgs-spark{color:var(--primary)}
	</style>`;

	window.ReckonGuidedSetup = function (parent, studio) {
		studio = studio === "payroll" ? "payroll" : "hr";
		const root = $(`<div class="rgs">${STYLE}
			<div class="rgs-card"><h2><span class="rgs-spark">✦</span> Guided setup with Ask AI</h2>
				<div class="rgs-muted">${studio === "payroll"
					? "Set up pay items and salary one step at a time. Ask AI knows your industry and explains each step in plain words. It never invents amounts."
					: "Set up your company one step at a time. Ask AI knows your industry and answers from the HR guide. Nothing changes until you press a button."}</div>
				<div class="rgs-row"><button type="button" class="btn btn-primary btn-sm" data-ask-main>✦ Ask AI to guide me</button></div></div>
			<div class="rgs-card"><h2>Your industry</h2>
				<div class="rgs-muted" data-now>Loading…</div>
				<div class="rgs-row"><select class="form-control" data-sel aria-label="Industry" style="flex:1 1 260px;max-width:420px"><option value="">Choose an industry</option></select>
					<button type="button" class="btn btn-default btn-sm" data-ask-industry>✦ Which one fits me?</button></div>
				<div data-preview></div></div>
			<div class="rgs-card"><h2>${studio === "payroll" ? "Payroll steps" : "Setup steps"}</h2>
				<ul class="rgs-steps" data-steps></ul></div></div>`).appendTo(parent);

		const $now = root.find("[data-now]");
		const $sel = root.find("[data-sel]");
		const $prev = root.find("[data-preview]");

		root.find("[data-ask-main]").on("click", () => window.ReckonStudioAsk(studio));
		root.find("[data-ask-industry]").on("click", () => askAi("Which industry should I choose for my company, and what will it pre-load? Ask me what my company does if you need to."));
		root.find("[data-steps]").html(STEPS[studio].map(([title, q], i) =>
			`<li><span>${esc(title)}</span><button type="button" class="btn btn-default btn-xs rgs-ask" data-q="${i}">✦ Ask AI</button></li>`).join(""));
		root.on("click", "[data-q]", function () { askAi(STEPS[studio][Number(this.dataset.q)][1]); });

		function showNow(label) {
			current.label = label || "";
			$now.html(label ? `Current industry: <b>${esc(label)}</b>` : "Not chosen yet. Choose one below to see what it pre-loads.");
		}

		frappe.call({ method: "reckon_hrms.api.industry.current_segment", type: "GET" }).then((r) => {
			const c = r.message || {};
			current.segment = c.segment || "";
			showNow(c.label);
			return frappe.call({ method: "reckon_hrms.api.industry.list_segments", type: "GET" }).then((s) => {
				$sel.append((s.message || []).map((x) => `<option value="${esc(x.key)}">${esc(x.label)} (${x.role_count} roles)</option>`).join(""));
				if (c.segment) { $sel.val(c.segment); showPreview(c.segment); }
			});
		}).catch(() => $now.text("Choosing an industry needs the HR Manager role."));

		function chips(items) {
			return items.map((i) => `<span class="rgs-chip ${esc(i.status)}" title="${i.status === "new" ? "Will be added" : i.status === "exists" ? "Already there" : "Not added: its short code is used by another item"}">${esc(i.name)}</span>`).join("");
		}

		function showPreview(segment) {
			if (!segment) { $prev.empty(); return; }
			$prev.html(`<div class="rgs-muted" style="margin-top:10px">Loading the preview…</div>`);
			frappe.call({ method: "reckon_hrms.api.industry.preview_segment", args: { segment }, type: "GET" }).then((r) => {
				const p = r.message;
				const wanted = studio === "payroll" ? ["components", "overtime"] : null;
				const groups = p.groups.filter((g) => !wanted || wanted.includes(g.key));
				const total = groups.reduce((n, g) => n + (p.will_add[g.key] || 0), 0);
				$prev.html(`<div style="margin-top:12px"><b>Preview: ${esc(p.label)}</b>
					<div class="rgs-muted">${total ? `${total} items will be added; the rest already exist.` : "Everything for this industry is already there."} Green items are new.</div>
					<div class="rgs-groups">${groups.map((g) => `<div class="rgs-group"><h3><span>${esc(g.title)}</span><span class="rgs-count">${p.will_add[g.key] ? `+${p.will_add[g.key]} new` : "all there"}</span></h3>
						<div class="rgs-chips">${chips(g.items)}</div></div>`).join("")}</div>
					<div class="rgs-muted" style="margin-top:10px"><b>Not loaded:</b> ${esc(p.not_loaded.join(" "))}</div>
					<div class="rgs-row"><button type="button" class="btn btn-primary btn-sm" data-apply>Set up for this industry</button>
						<button type="button" class="btn btn-default btn-sm" data-ask-preview>✦ Explain this preview</button></div>
					<div class="rgs-muted" data-msg style="margin-top:8px"></div></div>`);
				$prev.find("[data-ask-preview]").on("click", () => askAi(`Explain what choosing ${p.label} pre-loads and which items I should keep.`));
				$prev.find("[data-apply]").on("click", () => frappe.confirm(`Set up ${esc(p.company)} for ${esc(p.label)}? This adds the green items. Nothing is paid and no amounts are set.`, () => {
					$prev.find("[data-msg]").text("Setting up…");
					frappe.call({ method: "reckon_hrms.api.industry.choose_segment", args: { segment } }).then(() => {
						showNow(p.label);
						showPreview(segment);
						frappe.show_alert({ message: `${p.label} is set up.`, indicator: "green" });
					}).catch((e) => $prev.find("[data-msg]").text((e && e.message) || "Could not set up this industry."));
				}));
			}).catch(() => $prev.html(`<div class="rgs-muted" style="margin-top:10px">Could not load the preview.</div>`));
		}
		$sel.on("change", function () { showPreview(this.value); });
	};
})();
