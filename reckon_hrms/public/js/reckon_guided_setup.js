// Guided setup for HR Studio and Payroll Studio: the company's industry with a preview of what will be pre-loaded,
// and "Ask AI" buttons that open Ask Aura AI with the question already filled in (it answers from the HR industry guide).
// window.ReckonGuidedSetup(parent, "hr" | "payroll"); window.ReckonAskAi(question, studio) for the page header buttons.
(function () {
	const esc = (t) => frappe.utils.escape_html(t == null ? "" : String(t));
	const current = { label: "", segment: "", lang: "" };

	function askAi(question) {
		const industry = current.label ? ` My industry is ${current.label}.` : "";
		const lang = current.lang === "bn" ? " Please answer in Bangla." : "";
		if (window.aura && window.aura.ask_about) window.aura.ask_about(question + industry + lang);
		else frappe.show_alert({ message: __("Ask AI is not available on this page."), indicator: "orange" });
	}
	window.ReckonAskAi = function (question) { askAi(question); };

	const STUDIO_ASK = {
		hr: "Guide me through setting up HR Studio step by step for my company.",
		payroll: "Guide me through setting up Payroll Studio step by step for my company.",
	};
	// "Ask AI" starts the setup agent in the chat: it asks the questions there and sets everything up itself.
	window.ReckonStudioAsk = function (studio) {
		if (window.aura && window.aura.start_agent) window.aura.start_agent("hrms_setup");
		else askAi(STUDIO_ASK[studio] || STUDIO_ASK.hr);
	};

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
	.rgs-sum{cursor:pointer;color:var(--text-muted);font-size:13px;margin-top:14px;padding:6px 0}
	.rgs-rev{display:flex;justify-content:space-between;align-items:center;gap:10px;padding:10px 0;border-bottom:1px dotted var(--border-color)}
	.rgs-rev:last-child{border-bottom:0}
	.rgs-rev .rgs-d{color:var(--text-muted);font-size:13px}
	.rgs-tick{display:inline-grid;place-items:center;width:20px;height:20px;border-radius:50%;margin-right:10px;font-size:12px;font-weight:700;background:var(--control-bg);color:var(--text-muted)}
	.rgs-tick.on{background:var(--green-100,#e4f5e9);color:var(--green-700,#1e6b3a)}
	.rgs-spark{color:var(--primary)}
	</style>`;

	// ---- the setup interview: one question at a time, then one plan to review, then one apply
	function interview(root, studio, $sel) {
		const KEY = "reckon_setup_answers";
		let answers = {};
		try { answers = JSON.parse(sessionStorage.getItem(KEY) || "{}"); } catch (e) { answers = {}; }
		const save = () => { try { sessionStorage.setItem(KEY, JSON.stringify(answers)); } catch (e) { /* private window */ } };
		const $step = root.find("[data-stepper]");
		const $plan = root.find("[data-plan]");
		const val = (k) => (answers[k] == null ? "" : answers[k]);
		const field = (k, label, extra = "") => `<label class="rgs-f"><span>${esc(label)}</span><input class="form-control input-sm" data-a="${k}" value="${esc(val(k))}" ${extra}></label>`;
		let Q = null, idx = 0, planned = false, LINKS = {};
		const EDIT = (key) => ({
			country: ["Company", LINKS.company], language: ["User", LINKS.user], locations: ["Branch"], extra_departments: ["Department"],
			extra_titles: ["Designation"], weekly_off: ["Holiday List", LINKS.holiday_list], holidays: ["Holiday List", LINKS.holiday_list],
			shift: ["Shift Type"], leave: ["Leave Policy"], structure_name: ["Salary Structure", LINKS.structure], rules: ["Company", LINKS.company],
		})[key];

		const STYLE2 = `<style>.rgs-bar{height:6px;background:var(--control-bg);border-radius:99px;overflow:hidden;margin:8px 0 14px}.rgs-bar b{display:block;height:100%;background:var(--primary)}.rgs-q{padding:4px 0 8px}.rgs-qh{display:flex;justify-content:space-between;gap:10px;align-items:center;margin-bottom:2px}.rgs-q h3{font-size:16px;margin:0}.rgs-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:10px;margin-top:10px}.rgs-f span{display:block;font-size:12px;color:var(--text-muted);margin-bottom:2px}.rgs-days{display:flex;flex-wrap:wrap;gap:12px;margin-top:10px}.rgs-days label{display:inline-flex;gap:5px;align-items:center;margin:0;font-weight:400}.rgs-st{display:inline-block;font-size:11px;font-weight:700;border-radius:99px;padding:1px 8px;margin-left:8px}.rgs-st.ready,.rgs-st.done{background:var(--green-100,#e4f5e9);color:var(--green-700,#1e6b3a)}.rgs-st.skipped{background:var(--control-bg);color:var(--text-muted)}.rgs-st.attention,.rgs-st.failed{background:var(--orange-100,#fff1db);color:var(--orange-700,#8a5300)}.rgs-nav{display:flex;justify-content:space-between;gap:8px;margin-top:14px;flex-wrap:wrap}.rgs-dots{display:flex;gap:5px;flex-wrap:wrap;margin-top:12px}.rgs-dots button{width:10px;height:10px;border-radius:50%;border:0;padding:0;background:var(--border-color);cursor:pointer}.rgs-dots button.on{background:var(--primary)}.rgs-dots button.done{background:var(--green-500,#3a9a5b)}</style>`;

		const days = () => (Array.isArray(answers.weekly_off) ? answers.weekly_off : (Q.weekly_off_by_country[val("country")] || Q.default_weekly_off));
		const total = () => Q.questions.length;
		const answered = (x) => {
			const keys = { country: ["country"], language: ["language"], list: [x.key], text: [x.key], days: ["weekly_off"], shift: ["shift_name"], leave: ["leave_casual", "leave_sick", "leave_earned", "leave_maternity"], structure: ["structure_name"], rules: ["rule_marks"] }[x.kind] || [x.key];
			return keys.some((k) => (Array.isArray(answers[k]) ? answers[k].length : String(val(k)).trim()));
		};

		function draw() {
			const n = total();
			if (idx >= n) return drawReview();
			const x = Q.questions[idx];
			let body = "";
			if (x.kind === "country") body = `<select class="form-control" data-a="country" style="max-width:360px"><option value="">Choose a country</option>${Q.countries.map((c) => `<option ${c === val("country") ? "selected" : ""}>${esc(c)}</option>`).join("")}</select>`;
			else if (x.kind === "language") body = `<select class="form-control" data-a="language" style="max-width:360px"><option value="">Keep as it is</option>${Object.keys(Q.languages).map((k) => `<option value="${k}" ${k === val("language") ? "selected" : ""}>${esc(Q.languages[k])}</option>`).join("")}</select>`;
			else if (x.kind === "list") body = `<textarea class="form-control" rows="3" data-a="${x.key}">${esc(val(x.key))}</textarea>`;
			else if (x.kind === "text") {
				if (answers.holidays_country === undefined && val("country")) { answers.holidays_country = "1"; save(); }
				body = `<label class="rgs-days" style="display:flex;gap:6px;align-items:center;margin:10px 0 6px;font-weight:400"><input type="checkbox" data-hc ${answers.holidays_country === "1" ? "checked" : ""}> Add the public holidays of ${esc(val("country") || "my country")} from the ReckonERP holiday calendar</label>
					<div class="rgs-muted">Your own holidays, if any (one per line, date first):</div>
					<textarea class="form-control" rows="4" data-a="${x.key}" placeholder="${esc(Q.year)}-03-26 Independence Day">${esc(val(x.key))}</textarea>`;
			}
			else if (x.kind === "days") { const picked = days(); body = `<div class="rgs-days">${Q.weekdays.map((d) => `<label><input type="checkbox" data-day="${d}" ${picked.includes(d) ? "checked" : ""}> ${d}</label>`).join("")}</div>`; }
			else if (x.kind === "shift") body = `<div class="rgs-grid">${field("shift_name", "Shift name", 'placeholder="General Shift"')}${field("shift_start", "Starts", 'placeholder="09:00"')}${field("shift_end", "Ends", 'placeholder="17:00"')}${field("late_grace", "Late entry grace (minutes)", 'inputmode="numeric"')}</div>`;
			else if (x.kind === "leave") body = `<div class="rgs-grid">${field("leave_casual", "Casual Leave", 'inputmode="decimal"')}${field("leave_sick", "Sick Leave", 'inputmode="decimal"')}${field("leave_earned", "Earned Leave", 'inputmode="decimal"')}${field("leave_maternity", "Maternity Leave", 'inputmode="decimal"')}</div>`;
			else if (x.kind === "rules") body = `<div class="rgs-grid">${field("rule_marks", "Marks that equal one day", 'inputmode="numeric" placeholder="3"')}${field("rule_divisor", "Day's pay = base salary / this", 'inputmode="numeric" placeholder="30"')}${field("rule_cap", "Monthly cap (0 = none)", 'inputmode="decimal" placeholder="0"')}</div>
				<div style="margin-top:8px"><button type="button" class="btn btn-default btn-xs" data-standard-rule>Use the standard rule: 3 marks, pay / 30, no cap</button></div>`;
			else if (x.kind === "structure") body = `<div class="rgs-grid">${field("structure_name", "Structure name", 'placeholder="Standard Structure"')}${field("basic_pct", "Basic, % of gross", 'inputmode="decimal"')}${field("hra_pct", "House rent, % of gross", 'inputmode="decimal"')}${field("medical_amount", "Medical, fixed per month", 'inputmode="decimal"')}${field("conveyance_amount", "Conveyance, fixed per month", 'inputmode="decimal"')}</div>`;
			const ek = ({ structure: "structure_name", text: "holidays", days: "weekly_off", shift: "shift", leave: "leave", rules: "rules" })[x.kind] || x.key;
			const last = idx === n - 1;
			$step.html(`${STYLE2}<div class="rgs-muted">Step ${idx + 1} of ${n}</div>
				<div class="rgs-bar"><b style="width:${Math.round((idx / n) * 100)}%"></b></div>
				<div class="rgs-q"><div class="rgs-qh"><h3>${esc(x.label)}</h3></div>
					<div class="rgs-muted">${esc(x.help)}</div>${EDIT(ek) ? `<div style="margin-top:4px"><a href="#" class="rgs-edit" data-edit="${ek}">Open ${esc(EDIT(ek)[0])} to review or edit</a></div>` : ""}${body}</div>
				<div class="rgs-nav"><button type="button" class="btn btn-default btn-sm" data-back ${idx ? "" : "disabled"}>Back</button>
					<span><button type="button" class="btn btn-default btn-sm" data-skip>Skip</button>
					<button type="button" class="btn btn-primary btn-sm" data-next>${last ? "✦ Review my plan" : "Next"}</button></span></div>
				<div class="rgs-dots">${Q.questions.map((q, i) => `<button type="button" data-go="${i}" class="${i === idx ? "on" : answered(q) ? "done" : ""}" aria-label="Step ${i + 1}: ${esc(q.label)}"></button>`).join("")}</div>`);
		}

		function drawReview() {
			$step.html(`${STYLE2}<div class="rgs-muted">All ${total()} steps</div><div class="rgs-bar"><b style="width:100%"></b></div>
				<div class="rgs-nav"><button type="button" class="btn btn-default btn-sm" data-back>Back to the questions</button></div>`);
			prepare();
		}

		const PAYROLL_KEYS = ["structure_name", "basic_pct", "hra_pct", "medical_amount", "conveyance_amount", "rule_marks", "rule_divisor", "rule_cap"];
		const gather = () => (studio === "payroll"
			? Object.fromEntries(PAYROLL_KEYS.filter((k) => answers[k] != null && answers[k] !== "").map((k) => [k, answers[k]]))
			: Object.assign({}, answers, { industry: $sel.val() || "", weekly_off: days() }));
		const badge = (st) => `<span class="rgs-st ${esc(st)}">${esc(({ ready: "will be added", skipped: "skipped", attention: "needs your attention", done: "done", failed: "failed" })[st] || st)}</span>`;

		function prepare() {
			$plan.html(`<div class="rgs-muted" style="margin-top:10px">✦ Ask AI is reading your answers…</div>`);
			frappe.call({ method: "reckon_hrms.api.ai_setup.prepare", args: { answers: JSON.stringify(gather()) } }).then((r) => {
				const p = r.message;
				if (studio === "payroll") {
					p.steps = p.steps.filter((st) => st.key === "structure" || st.key === "rules");
					p.ready = p.steps.filter((st) => st.status === "ready").length;
					p.attention = p.steps.filter((st) => st.status === "attention").length;
				}
				$plan.html(`<div style="margin-top:14px"><b>Your setup plan for ${esc(p.company)}</b>
					<div class="rgs-muted">${p.ready} steps will run${p.attention ? `, ${p.attention} need your attention (go back, fix them and review again)` : ""}.${p.ai_used ? " Ask AI read your holiday text." : ""} Nothing has been created yet.</div>
					${p.steps.map((st) => `<div class="rgs-group" style="margin-top:10px"><b>${esc(st.title)}</b>${badge(st.status)}
						${st.items.length ? `<ul style="margin:6px 0 0 18px;padding:0">${st.items.map((i) => `<li>${esc(i)}</li>`).join("")}</ul>` : ""}
						${st.note ? `<div class="rgs-muted" style="margin-top:4px">${esc(st.note)}</div>` : ""}</div>`).join("")}
					<div class="rgs-row"><button type="button" class="btn btn-primary btn-sm" data-apply-all ${p.ready ? "" : "disabled"}>Set everything up</button>
						</div>
					<div data-result></div></div>`);
				$plan.find("[data-apply-all]").on("click", function () {
					frappe.confirm(`Set up ${esc(p.company)} with this plan? Nothing is paid and no one's salary is set.`, () => {
						const $a = $(this).prop("disabled", true);
						$plan.find("[data-result]").html(`<div class="rgs-muted" style="margin-top:10px">Setting up…</div>`);
						frappe.call({ method: "reckon_hrms.api.ai_setup.apply", args: { answers: JSON.stringify(gather()) } }).then((a) => {
							const res = a.message;
							$plan.find("[data-result]").html(`<div style="margin-top:12px"><b>${res.done} steps done${res.failed ? `, ${res.failed} failed` : ""}</b>
								<ul style="margin:6px 0 0 18px;padding:0">${res.results.map((x) => `<li>${esc(x.label)} ${badge(x.result)} <span class="rgs-muted">${esc(x.message)}</span></li>`).join("")}</ul></div>`);
							try { sessionStorage.removeItem(KEY); } catch (e) { /* ignore */ }
							frappe.show_alert({ message: res.failed ? "Some steps failed. See the list." : "Setup finished.", indicator: res.failed ? "orange" : "green" });
							$sel.trigger("change");
							root.trigger("rgs:refresh");
						}).catch((e) => { $a.prop("disabled", false); $plan.find("[data-result]").html(`<div class="rgs-muted">${esc((e && e.message) || "Could not run the setup.")}</div>`); });
					});
				});
			}).catch((e) => $plan.html(`<div class="rgs-muted" style="margin-top:10px">${esc((e && e.message) || "Could not prepare the plan.")}</div>`));
		}

		const go = (i) => { $plan.empty(); idx = Math.max(0, Math.min(i, total())); draw(); };
		$step.on("input change", "[data-a]", function () {
			answers[this.dataset.a] = this.value; save();
			if (this.dataset.a === "language") current.lang = this.value;
			// A country gives the usual weekly off, unless the person already chose days.
			if (this.dataset.a === "country" && !answers.__daysChosen) delete answers.weekly_off;
		});
		$step.on("change", "[data-hc]", function () { answers.holidays_country = this.checked ? "1" : ""; save(); });
		$step.on("change", "[data-day]", function () {
			answers.weekly_off = $step.find("[data-day]:checked").map((_i, el) => el.dataset.day).get();
			answers.__daysChosen = true; save();
		});
		$step.on("click", "[data-standard-rule]", () => { Object.assign(answers, { rule_marks: "3", rule_divisor: "30", rule_cap: "0" }); save(); draw(); });
		$step.on("click", "[data-next]", () => go(idx + 1));
		$step.on("click", "[data-skip]", () => go(idx + 1));
		$step.on("click", "[data-back]", () => go(idx - 1));
		$step.on("click", "[data-go]", function () { go(Number(this.dataset.go)); });

		$step.on("click", "a[data-edit]", (e) => e.preventDefault());
		$step.on("click", "[data-edit]", function () {
			const e = EDIT(this.dataset.edit);
			if (!e) return;
			const slug = frappe.router.slug(e[0]);
			if (e[1]) frappe.set_route(slug, e[1]); else frappe.set_route(slug);
		});

		Promise.all([
			frappe.call({ method: "reckon_hrms.api.ai_setup.questions", type: "GET" }),
			frappe.call({ method: "reckon_hrms.api.ai_setup.current_answers", type: "GET" }),
		]).then(([r, c]) => {
			Q = r.message;
			// Payroll Studio asks the payroll questions, HR Studio the HR ones: nothing is asked twice.
			Q.questions = Q.questions.filter((x) => (studio === "payroll" ? x.studio === "payroll" : x.studio !== "payroll"));
			if (studio === "payroll") Q.questions.sort((a, b) => (a.kind === "structure" ? -1 : 1) - (b.kind === "structure" ? -1 : 1));
			const have = (c.message && c.message.answers) || {};
			LINKS = (c.message && c.message.links) || {};
			// What the company already has fills the answers; only what was typed this session overrides it.
			answers = Object.assign({}, have, answers);
			if (have.weekly_off) answers.__daysChosen = true;
			current.lang = answers.language || "";
			draw();
		}).catch(() => $step.html(`<div class="rgs-muted">The interview needs the HR Manager role.</div>`));
	}

	// ---- Payroll Studio: the salary process in the order HRMS needs it. What HR Studio owns is shown as a status with a link.
	function payrollPanel(parent) {
		const root = $(`<div class="rgs">${STYLE}
			<div class="rgs-card"><h2><span class="rgs-spark">✦</span> Guided setup with Ask AI</h2>
				<div class="rgs-muted">Ask AI asks you the questions in the chat, one at a time (the salary structure, then the late and early deduction rule), and then sets everything up for you. Nothing is created until you confirm. You can also answer the same questions below. People, places, holidays, working hours and leave belong to HR Studio, so they are only shown, never asked again.</div>
				<div class="rgs-row"><button type="button" class="btn btn-primary btn-sm" data-ask>✦ Ask AI to set it up for me</button></div></div>
			<div class="rgs-card" data-interview hidden><h2>Setup interview</h2>
				<div class="rgs-muted">Ask AI asks one question at a time, from the salary structure to the late and early deduction rule. Answer what you know, skip the rest, then review one plan before anything is created. Your existing structure and rule are filled in, and each question links to the page that edits them.</div>
				<div data-stepper></div><div data-plan></div></div>
			<div data-groups></div></div>`).appendTo(parent);
		const $groups = root.find("[data-groups]");
		let data = null;
		const slug = (dt) => frappe.router.slug(dt);

		function draw() {
			const blocked = !data.hr_ready;
			const banner = blocked ? `<div class="rgs-card" style="border-color:var(--orange-500,#d98200)"><h2>Finish HR setup first</h2>
				<div class="rgs-muted">Payroll builds on your people, holiday calendar, working hours and leave. Still to do in HR Studio:</div>
				<ul style="margin:8px 0 0 18px;padding:0">${data.hr_pending.map((x) => `<li><b>${esc(x.label)}</b> <span class="rgs-muted">${esc(x.detail)}</span></li>`).join("")}</ul>
				<div class="rgs-row"><button type="button" class="btn btn-primary btn-sm" data-hr-first>Complete HR setup</button></div></div>` : "";
			$groups.html(banner + `<div ${blocked ? 'style="opacity:.55"' : ""}>` + data.groups.map((g) => `<div class="rgs-card"><h2>${esc(g.title)}</h2>
				${g.rows.map((r) => `<div class="rgs-rev"><div><span class="rgs-tick ${r.done ? "on" : ""}">${r.done ? "✓" : "–"}</span><b>${esc(r.label)}</b>
					<div class="rgs-d" style="margin-left:30px">${esc(r.detail)}</div>
					${r.key === "rules" ? `<div data-rules hidden style="margin:8px 0 0 30px" class="rgs-grid">
						<label class="rgs-f"><span>Marks that equal one day</span><input class="form-control input-sm" data-r="marks" value="${esc(data.rules.marks_per_day)}" inputmode="numeric"></label>
						<label class="rgs-f"><span>Day's pay = base / this</span><input class="form-control input-sm" data-r="divisor" value="${esc(data.rules.divisor)}" inputmode="numeric"></label>
						<label class="rgs-f"><span>Monthly cap (0 = none)</span><input class="form-control input-sm" data-r="cap" value="${esc(data.rules.cap)}" inputmode="decimal"></label>
						<div style="align-self:end"><button type="button" class="btn btn-primary btn-xs" data-save-rules>Save</button> <span class="rgs-muted" data-rmsg></span></div></div>` : ""}
					</div><span>${r.actions.map((a, i) => `<button type="button" class="btn ${a.kind === "agent" || a.kind === "fix" ? "btn-primary" : "btn-default"} btn-xs" data-act="${esc(r.key)}:${i}">${esc(a.label)}</button>`).join(" ")}</span></div>`).join("")}</div>`).join("") + "</div>");
			if (blocked) root.find("[data-groups] [data-act]").each(function () { if (!/^(employees|holidays|attendance|leave):/.test(this.dataset.act)) $(this).prop("disabled", true); });
		}

		let started = false;
		function load() {
			frappe.call({ method: "reckon_hrms.api.ai_setup.payroll_readiness", type: "GET" }).then((r) => {
				data = r.message;
				draw();
				// The interview opens once HR setup is done; until then the box above says what to finish first.
				root.find("[data-interview]").prop("hidden", !data.hr_ready);
				if (data.hr_ready && !started) { started = true; interview(root, "payroll", $()); }
			})
				.catch(() => $groups.html(`<div class="rgs-card rgs-muted">Payroll setup needs the HR Manager or Payroll Manager role.</div>`));
		}
		load();
		root.on("click", "[data-refresh]", load);
		root.on("rgs:refresh", load);
		root.on("click", "[data-hr-first]", () => { frappe.route_options = { stage: "guided" }; frappe.set_route("reckon-hrms-hr-studio"); });
		root.on("click", "[data-ask]", () => window.ReckonStudioAsk("payroll"));
		root.on("click", "[data-act]", function () {
			const [key, i] = this.dataset.act.split(":");
			const action = data.groups.flatMap((g) => g.rows).find((r) => r.key === key).actions[Number(i)];
			if (action.kind === "open") {
				const dt = frappe.router.slug(action.doctype);
				if (action.name) frappe.set_route(dt, action.name); else frappe.set_route(dt);
			} else if (action.kind === "hr") {
				frappe.route_options = { stage: action.stage };
				frappe.set_route("reckon-hrms-hr-studio");
			} else if (action.kind === "stage") {
				$(`.rhs-stages [data-stage="${action.stage}"]`).trigger("click");
			} else if (action.kind === "agent") {
				if (window.aura && window.aura.start_agent) window.aura.start_agent("hrms_setup", "start payroll");
			} else if (action.kind === "rules") {
				root.find("[data-rules]").prop("hidden", (_i, v) => !v);
			} else if (action.kind === "fix") {
				frappe.call({ method: "reckon_hrms.api.ai_setup.ensure_payroll_account" }).then(() => { frappe.show_alert({ message: "Payroll payable account is set up.", indicator: "green" }); load(); })
					.catch((e) => frappe.show_alert({ message: (e && e.message) || "Could not set it up.", indicator: "orange" }));
			}
		});
		root.on("click", "[data-save-rules]", function () {
			const v = (k) => root.find(`[data-r="${k}"]`).val();
			frappe.call({ method: "reckon_hrms.api.ai_setup.save_payroll_rules", args: { marks_per_day: v("marks"), divisor: v("divisor"), cap: v("cap") || 0 } })
				.then(() => { root.find("[data-rmsg]").text("Saved."); load(); })
				.catch((e) => root.find("[data-rmsg]").text((e && e.message) || "Could not save."));
		});
	}

	window.ReckonGuidedSetup = function (parent, studio) {
		studio = studio === "payroll" ? "payroll" : "hr";
		if (studio === "payroll") { payrollPanel(parent); return; }
		const root = $(`<div class="rgs">${STYLE}
			<div class="rgs-card"><h2><span class="rgs-spark">✦</span> Guided setup with Ask AI</h2>
				<div class="rgs-muted">${studio === "payroll"
					? "Ask AI asks you the questions in the chat, one at a time, and then sets up your pay items and salary structure for you. It never invents amounts."
					: "Ask AI asks you the questions in the chat, one at a time (country, language, locations, departments and more), and then sets everything up for you. Nothing is created until you confirm."} You can also answer the same questions below.</div>
				<div class="rgs-row"><button type="button" class="btn btn-primary btn-sm" data-ask-main>✦ Ask AI to set it up for me</button></div></div>
			<div class="rgs-card" data-interview><h2>Setup interview</h2>
				<div class="rgs-muted">Ask AI asks one question at a time, from your country to your leave days. Answer what you know, skip the rest, then review one plan before anything is created. Ask AI never makes up amounts, dates or leave days.</div>
				<div data-stepper></div>
				<div data-plan></div></div>
			<div data-review></div>
			<details data-more open class="rgs-more"><summary class="rgs-sum">Choose or change your industry template</summary>
			<div class="rgs-card"><h2>Your industry</h2>
				<div class="rgs-muted" data-now>Loading…</div>
				<div class="rgs-row"><select class="form-control" data-sel aria-label="Industry" style="flex:1 1 260px;max-width:420px"><option value="">Choose an industry</option></select>
					<button type="button" class="btn btn-default btn-sm" data-ask-industry>✦ Which one fits me?</button></div>
				<div data-preview></div></div></details></div>`).appendTo(parent);

		const $now = root.find("[data-now]");
		const $sel = root.find("[data-sel]");
		const $prev = root.find("[data-preview]");

		root.find("[data-ask-main]").on("click", () => window.ReckonStudioAsk(studio));
		// The agent asks what the company does, picks the industry from the answer and shows what it pre-loads.
		root.find("[data-ask-industry]").on("click", () => {
			if (window.aura && window.aura.start_agent) window.aura.start_agent("hrms_setup", "start industry");
			else askAi("Which industry should I choose for my company, and what will it pre-load?");
		});
		const $review = root.find("[data-review]");
		function review() {
			frappe.call({ method: "reckon_hrms.api.ai_setup.review_state", args: { studio }, type: "GET" }).then((r) => {
				const d = r.message;
				if (!d || !d.rows) return;
				root.find("[data-more]").prop("open", !d.finished);
				$review.html(`<div class="rgs-card"><h2>Your setup for ${esc(d.company)}</h2>
					<div class="rgs-muted">${d.finished ? "Setup is done. " : ""}Open any step to review or edit it. A step that is still empty can be set up with Ask AI.</div>
					${d.rows.map((x, i) => `<div class="rgs-rev"><div><span class="rgs-tick ${x.done ? "on" : ""}">${x.done ? "✓" : "–"}</span><b>${esc(x.label)}</b>
						<div class="rgs-d" style="margin-left:30px">${esc(x.detail)}</div></div>
						<span>${x.key === "industry"
							? `${x.done ? "" : `<button type="button" class="btn btn-primary btn-xs" data-fill="${i}">✦ Set up now</button> `}<button type="button" class="btn btn-default btn-xs" data-pick-industry>${x.done ? "Change" : "Choose"}</button>`
							: x.done || !x.chat ? `<button type="button" class="btn btn-default btn-xs" data-open="${i}">Review / edit</button>` : `<button type="button" class="btn btn-primary btn-xs" data-fill="${i}">✦ Set up now</button> <button type="button" class="btn btn-default btn-xs" data-open="${i}">Open</button>`}</span></div>`).join("")}
					</div>`);
				$review.off("click").on("click", "[data-open]", function () {
					const x = d.rows[Number(this.dataset.open)];
					const slug = frappe.router.slug(x.doctype);
					if (x.name) frappe.set_route(slug, x.name); else frappe.set_route(slug);
				});
				// The industry is a template, not a page: its picker is in the section below.
				$review.on("click", "[data-pick-industry]", () => {
					root.find("[data-more]").prop("open", true);
					const sel = root.find("[data-sel]")[0];
					if (sel) { sel.scrollIntoView({ behavior: "smooth", block: "center" }); sel.focus(); }
				});
				$review.on("click", "[data-fill]", function () {
					const x = d.rows[Number(this.dataset.fill)];
					if (window.aura && window.aura.start_agent) window.aura.start_agent("hrms_setup", `start ${x.chat}`);
				});
			});
		}
		review();
		root.on("rgs:refresh", review);

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
						</div>
					<div class="rgs-muted" data-msg style="margin-top:8px"></div></div>`);
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
		interview(root, studio, $sel);
	};
})();
