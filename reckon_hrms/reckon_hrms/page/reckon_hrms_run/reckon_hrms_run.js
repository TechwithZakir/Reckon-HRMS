// Page 3 (Run salary), five steps: choose month and people, check the list, make draft slips,
// review and approve, then pay. Served at /desk/reckon-hrms/reckon-hrms-run.
frappe.pages["reckon-hrms-run"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({ parent: wrapper, title: "Run salary", single_column: true });
	const root = $(`<div class="rhr"></div>`).appendTo(page.main);
	const esc = (t) => frappe.utils.escape_html(t == null ? "" : String(t));
	const PAGE = 25;
	const state = { run: null, filter: "all", search: "", start: 0 };

	root.html(`
		<style>${STYLE}</style>
		<div class="rhr-muted">Five steps. Nothing is paid until the last one.</div>
		<div class="rhr-card" id="step1">
			<h2>1 · Choose month and people <span class="rhr-map">Payroll Entry</span></h2>
			<div class="rhr-row">
				<label>Salary month <input type="month" id="month" value="${frappe.datetime.get_today().slice(0, 7)}"></label>
				<label>Pay date <input type="date" id="payDate" value="${frappe.datetime.get_today()}"></label>
				<label>Office or factory <select id="fBranch"><option value="">All offices</option></select></label>
				<label>Department <select id="fDept"><option value="">All departments</option></select></label>
				<label>Job title <select id="fDesig"><option value="">All job titles</option></select></label>
				<label>Level <select id="fGrade"><option value="">All levels</option></select></label>
			</div>
			<div class="rhr-row"><button class="rhr-btn rhr-pri" id="findBtn" type="button">Find employees</button></div>
			<div class="rhr-err" id="err1"></div>
		</div>
		<div class="rhr-card" id="step2" style="display:none">
			<h2>2 · Check the list <span class="rhr-map">Get Employees</span></h2>
			<div class="rhr-sum" id="sum"></div>
			<div class="rhr-alert" id="warn" style="display:none"></div>
			<div class="rhr-row">
				<div class="rhr-seg" id="flt">
					<button data-f="all" aria-pressed="true">All</button>
					<button data-f="ready" aria-pressed="false">Included</button>
					<button data-f="no_structure" aria-pressed="false">No salary structure</button>
				</div>
				<input type="search" id="q" placeholder="Search name or ID" aria-label="Search people">
				<button class="rhr-btn" id="fetchAgain" type="button">Refresh list</button>
			</div>
			<table class="rhr-table"><thead><tr>
				<th><input type="checkbox" id="all" aria-label="Include or leave out everyone shown"></th>
				<th>ID</th><th>Name</th><th>Department</th><th>Job title</th><th>Status</th></tr></thead>
				<tbody id="rows"></tbody></table>
			<div class="rhr-row"><span id="range" class="rhr-muted"></span>
				<span><button class="rhr-btn" id="prev" type="button">Previous</button> <button class="rhr-btn" id="next" type="button">Next</button></span></div>
			<div class="rhr-row"><span class="rhr-muted">Uncheck a person to leave them out of this run. Nothing is paid to anyone left out.</span></div>
			<div class="rhr-err" id="err2"></div>
			</div>
			<div class="rhr-card" id="step3" style="display:none">
				<h2>3 · Make draft slips <span class="rhr-map">Salary Slip (draft)</span></h2>
				<div class="rhr-muted">One draft pay slip for each person on the list. Nothing is paid yet.</div>
				<div class="rhr-row"><button class="rhr-btn rhr-pri" id="mkSlips" type="button">Create draft slips</button></div>
				<div class="rhr-bar"><div id="slipBar"></div></div>
				<div class="rhr-muted" id="slipText"></div>
				<div class="rhr-err" id="err3"></div>
			</div>
			<div class="rhr-card" id="step4" style="display:none">
				<h2>4 · Review and approve <span class="rhr-map">Submit Salary Slip</span></h2>
				<div class="rhr-sum" id="tot"></div>
				<div class="rhr-alert" id="totNote" style="display:none"></div>
				<div class="rhr-row"><button class="rhr-btn rhr-pri" id="approve" type="button">Approve all slips</button></div>
				<div class="rhr-bar"><div id="subBar"></div></div>
				<div class="rhr-muted" id="subText"></div>
				<div class="rhr-err" id="err4"></div>
			</div>
			<div class="rhr-card" id="step5" style="display:none">
				<h2>5 · Pay <span class="rhr-map">Journal Entry</span></h2>
				<div class="rhr-muted">Only approved slips are paid. People on hold are left out, and nothing is cancelled.</div>
				<div class="rhr-row">
					<label>Pay from account <select id="bank"><option value="">Choose an account</option></select></label>
					<label>Reference <input type="text" id="ref" placeholder="e.g. Salary November 2026"></label>
					<label>Reference date <input type="date" id="refDate" value="${frappe.datetime.get_today()}"></label>
					<button class="rhr-btn rhr-pri" id="pay" type="button" disabled>Record payment</button>
				</div>
				<div class="rhr-row">
					<button class="rhr-btn" id="dlBank" type="button">Bank sheet (CSV)</button>
					<button class="rhr-btn" id="dlWallet" type="button">bKash or Nagad sheet (CSV)</button>
					<span class="rhr-muted" id="fileInfo"></span>
				</div>
				<h3 style="font-size:14px;margin:14px 0 0">On hold</h3>
				<div class="rhr-row">
					<input type="text" id="holdEmp" placeholder="Employee ID" aria-label="Employee ID to hold">
					<input type="text" id="holdReason" placeholder="Reason" aria-label="Reason for hold">
					<button class="rhr-btn" id="holdBtn" type="button">Hold payment</button>
				</div>
				<table class="rhr-table"><tbody id="holds"></tbody></table>
				<div class="rhr-err" id="err5"></div>
		</div>`);

	const call = (method, args) => frappe.call({ method: "reckon_hrms.api.payroll_run." + method, args: args || {}, type: "GET" });
	const post = (method, args) => frappe.call({ method: "reckon_hrms.api.payroll_run." + method, args: args || {} });
	const fill = (sel, doctype) => frappe.call({ method: "frappe.client.get_list",
		args: { doctype, fields: ["name"], limit_page_length: 100, order_by: "name asc" } }).then((r) => {
		root.find(sel).append(r.message.map((x) => `<option value="${esc(x.name)}">${esc(x.name)}</option>`).join(""));
	});
	fill("#fBranch", "Branch");
	fill("#fDept", "Department");
	fill("#fDesig", "Designation");
	fill("#fGrade", "Employee Grade");

	root.find("#findBtn").on("click", () => {
		root.find("#err1").text("");
		post("start_run", {
			month: root.find("#month").val(), pay_date: root.find("#payDate").val(),
			branch: root.find("#fBranch").val(), department: root.find("#fDept").val(),
			designation: root.find("#fDesig").val(), grade: root.find("#fGrade").val(),
		}).then((r) => post("fetch_employees", { name: r.message.name }))
			.then((r) => { state.run = r.message.name; showStep2(r.message); })
			.catch((e) => root.find("#err1").text((e && e.message) || "Could not find employees."));
	});

	function showStep2(run) {
		root.find("#step2").show();
		root.find("#sum").html(`
			<div><span>People found</span><b>${run.included}</b></div>
			<div><span>Without a salary structure</span><b>${run.no_structure}</b></div>
			<div><span>Run</span><b>${esc(run.name)}</b></div>`);
		root.find("#warn").toggle(run.unmarked_attendance > 0).text(
			`${run.unmarked_attendance} people have no attendance marked yet for this month.`);
			showSteps(run);
		loadPeople();
	}

	function loadPeople() {
		call("list_people", { name: state.run, filter: state.filter, search: state.search, start: state.start, page_length: PAGE })
			.then((r) => {
				const p = r.message;
				root.find("#rows").html(p.rows.map((x) => `<tr>
					<td><input type="checkbox" class="pick" data-e="${esc(x.employee)}" ${x.included ? "checked" : ""}></td>
					<td>${esc(x.employee)}</td><td>${esc(x.employee_name)}</td><td>${esc(x.department || "")}</td>
					<td>${esc(x.designation || "")}</td>
					<td>${x.status === "no_structure" ? '<span class="rhr-chip warn">No salary structure</span>' : '<span class="rhr-chip good">Included</span>'}</td></tr>`).join("")
					|| `<tr><td colspan="6" class="rhr-muted">Nobody matches.</td></tr>`);
				const last = Math.min(p.start + PAGE, p.total);
				root.find("#range").text(p.total ? `Showing ${p.start + 1} to ${last} of ${p.total}` : "No results");
				root.find("#prev").prop("disabled", p.start === 0);
				root.find("#next").prop("disabled", p.start + PAGE >= p.total);
				root.find(".pick").on("change", function () {
					const emp = $(this).data("e");
					const action = this.checked ? "include_people" : "exclude_people";
					post(action, { name: state.run, employees: [emp] })
						.then(() => call("get_run", { name: state.run }))
						.then((r) => showStep2(r.message))
						.catch((e) => { this.checked = !this.checked; root.find("#err2").text((e && e.message) || "Could not change that."); });
				});
			});
	}

	root.find("#flt").on("click", "button", function () {
		root.find("#flt button").attr("aria-pressed", "false");
		$(this).attr("aria-pressed", "true");
		state.filter = $(this).data("f");
		state.start = 0;
		loadPeople();
	});
	let t = null;
	root.find("#q").on("input", function () {
		clearTimeout(t);
		t = setTimeout(() => { state.search = this.value.trim(); state.start = 0; loadPeople(); }, 300);
	});
	root.find("#prev").on("click", () => { state.start = Math.max(0, state.start - PAGE); loadPeople(); });
	root.find("#next").on("click", () => { state.start += PAGE; loadPeople(); });
	root.find("#fetchAgain").on("click", () => {
		if (!state.run) return;
		post("fetch_employees", { name: state.run }).then((r) => showStep2(r.message)).catch((e) => root.find("#err2").text(e.message));
	});
	const money = (x) => Number(x || 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
		const setBar = (sel, pct) => root.find(sel).css("width", Math.max(0, Math.min(100, pct)) + "%");
		const save = (text, file) => {
			const url = URL.createObjectURL(new Blob([text], { type: "text/csv" }));
			const a = document.createElement("a");
			a.href = url; a.download = file; document.body.appendChild(a); a.click(); a.remove();
			setTimeout(() => URL.revokeObjectURL(url), 1000);
		};
		// Background jobs report progress through a cache key; poll it until the job says done.
		function poll(method, job, onTick, onDone) {
			const timer = setInterval(() => {
				call(method, { job }).then((r) => {
					const s = r.message;
					onTick(s);
					if (s.state === "done" || s.state === "unknown") { clearInterval(timer); onDone(s); }
				}).catch(() => clearInterval(timer));
			}, 1500);
		}
		// Show each step once the run has reached it (step comes from get_run: 1 no people, 2 no slips, 3 slips).
		function showSteps(run) {
			root.find("#step3").show();
			root.find("#step4").toggle(run.step >= 3);
			root.find("#step5").toggle(run.step >= 3);
			if (run.step >= 3) { loadTotals(); loadPayment(run); }
		}
		function loadTotals() {
			call("review_totals", { name: state.run }).then((r) => {
				const t = r.message;
				root.find("#tot").html(`
					<div><span>Draft slips</span><b>${t.slips}</b></div>
					<div><span>Gross pay</span><b>${money(t.gross)}</b></div>
					<div><span>Deductions</span><b>${money(t.deductions)}</b></div>
					<div><span>Net pay</span><b>${money(t.net)}</b></div>`);
				const note = t.slips === 0 ? "Every slip in this run is approved."
					: t.change_percent === null ? "No approved salary last month to compare with."
					: `Net pay is ${Math.abs(t.change_percent)}% ${t.change_percent >= 0 ? "higher" : "lower"} than last month (${money(t.last_month_net)}).`;
				root.find("#totNote").show().text(note);
				root.find("#approve").prop("disabled", t.slips === 0);
			});
		}
		function loadPayment(run) {
			frappe.call({ method: "frappe.client.get_list", args: {
				doctype: "Account", fields: ["name"], limit_page_length: 200, order_by: "name asc",
				filters: { company: run.company, is_group: 0, account_type: ["in", ["Bank", "Cash"]] } } }).then((r) => {
				root.find("#bank").html(`<option value="">Choose an account</option>` +
					r.message.map((x) => `<option value="${esc(x.name)}">${esc(x.name)}</option>`).join(""));
			});
			refreshFiles();
		}
		function refreshFiles() {
			call("payment_files", { name: state.run }).then((r) => {
				const f = r.message;
				state.totalToPay = f.total_to_pay;
				root.find("#fileInfo").text(`${f.bank_count} bank, ${f.wallet_count} bKash or Nagad, ${f.hold_count} on hold. Total to pay ${money(f.total_to_pay)}.`);
				root.find("#holds").html(f.holds.map((h) => `<tr><td>${esc(h.employee)}</td><td>${esc(h.employee_name)}</td><td>${esc(h.reason)}</td>
					<td><button class="rhr-btn release" data-e="${esc(h.employee)}" type="button">Release</button></td></tr>`).join("")
					|| `<tr><td class="rhr-muted">Nobody is on hold.</td></tr>`);
			});
		}

		root.find("#mkSlips").on("click", () => {
			const $btn = root.find("#mkSlips");
			root.find("#err3").text("");
			$btn.prop("disabled", true);
			post("create_slips", { name: state.run }).then((r) => poll("get_slip_progress", r.message.job,
				(s) => {
					const done = Object.values(s.branches || {}).reduce((a, b) => a + b.done, 0);
					setBar("#slipBar", s.total ? (100 * done) / s.total : 0);
					root.find("#slipText").text(`${done} of ${s.total || 0} slips made`);
				},
				(s) => {
					$btn.prop("disabled", false);
					if (s.state !== "done") { root.find("#err3").text("Could not finish making the slips. Try again."); return; }
					root.find("#slipText").text(`${s.created} draft slips made.` + (s.missing ? ` ${s.missing} people did not get a slip.` : ""));
					call("get_run", { name: state.run }).then((x) => showSteps(x.message));
				}))
				.catch((e) => { $btn.prop("disabled", false); root.find("#err3").text((e && e.message) || "Could not make the slips."); });
		});

		root.find("#approve").on("click", () => {
			root.find("#err4").text("");
			frappe.confirm("Approve every draft slip in this run? Approved slips cannot be edited.", () => {
				const $btn = root.find("#approve");
				$btn.prop("disabled", true);
				post("approve_slips", { name: state.run }).then((r) => poll("get_submit_progress", r.message.job,
					(s) => {
						setBar("#subBar", s.total ? (100 * s.done) / s.total : 0);
						root.find("#subText").text(`${s.done} of ${s.total} approved`);
					},
					(s) => {
						if (s.failed && s.failed.length) {
							root.find("#err4").text(`${s.failed.length} slips were not approved. ${s.failed[0].reason}`);
							$btn.prop("disabled", false);
						} else {
							root.find("#subText").text("All slips approved.");
						}
						loadTotals();
						refreshFiles();
					}))
					.catch((e) => { $btn.prop("disabled", false); root.find("#err4").text((e && e.message) || "Could not approve."); });
			});
		});

		root.find("#bank").on("change", function () { root.find("#pay").prop("disabled", !this.value); });
		root.find("#pay").on("click", () => {
			const bank = root.find("#bank").val();
			const ref = root.find("#ref").val().trim();
			root.find("#err5").text("");
			if (!bank) return root.find("#err5").text("Choose the account to pay from.");
			if (!ref) return root.find("#err5").text("Type a reference, such as the month.");
			frappe.confirm(`Record payment of ${money(state.totalToPay)} from ${bank}? This posts one journal entry.`, () => {
				post("record_payment", { name: state.run, bank_account: bank, reference: ref, reference_date: root.find("#refDate").val() })
					.then((r) => {
						root.find("#pay").prop("disabled", true);
						frappe.show_alert({ message: `Paid ${money(r.message.total)} in ${r.message.journal_entry}.`, indicator: "green" });
						refreshFiles();
					})
					.catch((e) => root.find("#err5").text((e && e.message) || "Could not record the payment."));
			});
		});
		root.find("#dlBank").on("click", () => call("payment_files", { name: state.run, download: 1 })
			.then((r) => save(r.message.bank_csv, `${state.run}-bank.csv`)));
		root.find("#dlWallet").on("click", () => call("payment_files", { name: state.run, download: 1 })
			.then((r) => save(r.message.wallet_csv, `${state.run}-bkash-nagad.csv`)));
		root.find("#holdBtn").on("click", () => {
			const emp = root.find("#holdEmp").val().trim();
			root.find("#err5").text("");
			if (!emp) return root.find("#err5").text("Type the employee ID to hold.");
			post("set_payment_hold", { name: state.run, employees: [emp], hold: 1, reason: root.find("#holdReason").val() })
				.then((r) => {
					if (!r.message.changed) return root.find("#err5").text("No approved slip for that employee in this run.");
					root.find("#holdEmp, #holdReason").val("");
					refreshFiles();
				})
				.catch((e) => root.find("#err5").text((e && e.message) || "Could not hold that payment."));
		});
		root.find("#holds").on("click", ".release", function () {
			post("set_payment_hold", { name: state.run, employees: [$(this).data("e")], hold: 0 })
				.then(() => refreshFiles())
				.catch((e) => root.find("#err5").text((e && e.message) || "Could not release that payment."));
		});

		root.find("#all").on("change", function () {
		root.find("input.pick").prop("checked", this.checked).trigger("change");
	});
};

const STYLE = `
.rhr{max-width:1000px;padding:8px 0 40px}
.rhr-muted{color:var(--text-muted);font-size:13px}
.rhr-card{background:var(--card-bg);border:1px solid var(--border-color);border-radius:12px;padding:16px;margin-top:14px}
.rhr-card h2{font-size:15px;margin:0 0 10px;display:flex;gap:8px;align-items:center}
.rhr-map{font:500 11px monospace;background:var(--control-bg);color:var(--text-muted);padding:1px 6px;border-radius:4px;display:none}
body.map .rhr-map{display:inline-block}
.rhr-row{display:flex;flex-wrap:wrap;gap:10px;align-items:flex-end;margin-top:8px}
.rhr-row label{display:grid;gap:4px;font-size:13px}
.rhr-row select,.rhr-row input{height:34px;border:1px solid var(--border-color);border-radius:8px;background:var(--card-bg);color:var(--text-color);padding:0 8px}
.rhr-btn{border:1px solid var(--border-color);background:var(--card-bg);color:var(--text-color);border-radius:8px;padding:6px 12px;cursor:pointer}
.rhr-pri{background:var(--primary);color:#fff;border-color:var(--primary)}
.rhr-seg button{border:1px solid var(--border-color);background:var(--card-bg);padding:6px 10px;cursor:pointer}
.rhr-seg button[aria-pressed="true"]{background:var(--control-bg);font-weight:600}
.rhr-sum{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px;margin-bottom:10px}
.rhr-sum b{display:block;font-size:18px}
.rhr-sum span{color:var(--text-muted);font-size:12px}
.rhr-alert{background:var(--control-bg);border-radius:8px;padding:10px;font-size:13px;margin:8px 0}
.rhr-table{width:100%;border-collapse:collapse;font-size:13px;margin-top:10px}
.rhr-table th,.rhr-table td{text-align:left;padding:6px 8px;border-bottom:1px solid var(--border-color)}
.rhr-chip{border-radius:99px;padding:2px 8px;font-size:12px}
.rhr-chip.good{background:var(--control-bg)}
.rhr-chip.warn{color:var(--orange-500)}
.rhr-err{color:var(--red-500);font-size:13px;margin-top:6px}
.rhr-bar{height:8px;background:var(--control-bg);border-radius:4px;margin-top:10px;overflow:hidden}
.rhr-bar div{height:100%;width:0;background:var(--primary);transition:width .3s}
`;
