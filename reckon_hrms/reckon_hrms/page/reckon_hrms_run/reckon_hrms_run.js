// Page 3 (Run salary), steps 1 and 2: choose month and people, then check the list.
// Steps 3 to 5 (slips, approval, payment) come later. Served at /desk/reckon-hrms/reckon-hrms-run.
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
`;
