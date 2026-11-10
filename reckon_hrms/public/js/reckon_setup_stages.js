window.ReckonSetupStages = window.ReckonSetupStages || {};

(function () {
// Page 1 (Your company): checklist and tap-to-add lists. Served at /desk/reckon-hrms/reckon-hrms-company.
window.ReckonSetupStages.company = function (parent) {
	const root = $(`<div class="rhc"></div>`).appendTo(parent);
	const company = frappe.defaults.get_user_default("Company") || "";

	const LISTS = [
		{ doctype: "Branch", title: "Offices and factories", map: "Branch",
			suggest: ["Gazipur Factory", "Dhaka Head Office", "Narayanganj Unit", "Chattogram Unit", "Khulna Depot"] },
		{ doctype: "Department", title: "Departments", map: "Department",
			suggest: ["Production", "Accounts", "HR & Admin", "Merchandising", "Quality", "Sales", "Store", "IT", "Maintenance", "Security"] },
		{ doctype: "Designation", title: "Job titles", map: "Designation",
			suggest: ["Operator", "Supervisor", "Officer", "Senior Officer", "Manager", "Executive", "Cleaner"] },
		{ doctype: "Employee Grade", title: "Levels", map: "Employee Grade",
			suggest: ["Worker", "Staff", "Management", "Trainee"] },
		{ doctype: "Employment Type", title: "Types of employee", map: "Employment Type",
			suggest: ["Permanent", "Probation", "Contract", "Daily wage", "Intern"] },
	];

	const esc = (t) => frappe.utils.escape_html(t == null ? "" : String(t));
	const showErr = (box, msg) => box.find("[data-err]").text(msg || "");
	const slug = (doctype) => "/app/" + doctype.toLowerCase().replace(/ /g, "-");

	function renderState(s) {
		root.find("#pct").text(s.percent);
		root.find("#bar").css("width", s.percent + "%");
		root.find("#doneCount").text(s.done);
		root.find("#totalCount").text(s.total);
		root.find("#checks").html(s.steps.map((st) =>
			`<li><span class="rhc-dot ${st.done ? "done" : ""}"></span>${esc(st.label)}</li>`).join(""));
	}
	const loadState = () => frappe.call({ method: "reckon_hrms.api.setup.get_state", type: "GET" }).then((r) => renderState(r.message));

	function stageIcon(name) {
			return frappe.utils && frappe.utils.icon ? frappe.utils.icon(name, "sm") : esc(name === "add" ? "+" : name);
		}

		function chipSection(list) {
		const box = $(`<section class="rhc-card">
			<h2>${esc(list.title)}<span class="rhc-map">${esc(list.map)}</span></h2>
			<div class="rhc-chips"></div>
			<div class="rhc-row"><input type="text" maxlength="140" placeholder="Type a name and press Enter" aria-label="Add ${esc(list.title)}">
			<span class="rhc-acts"><a class="rhc-ico" href="${slug(list.doctype)}" title="Open the ${esc(list.title)} list" aria-label="Open the ${esc(list.title)} list">${stageIcon("list")}</a><button type="button" class="rhc-ico" data-new title="Add new" aria-label="Add new ${esc(list.title)}">${stageIcon("add")}</button></span></div>
			<div class="rhc-row" data-suggest></div><div class="rhc-err" data-err></div></section>`);
		box.find("[data-new]").on("click", () => {
			// Full form in a quick-entry dialog, so the list reloads when a record is saved.
			const prefill = list.doctype === "Department" && company ? { company } : {};
			frappe.ui.form.make_quick_entry(list.doctype, () => { loadChips(list, box); loadState(); }, null, prefill);
		});
		const input = box.find("input");
		input.on("keydown", (e) => {
			if (e.key === "Enter" && input.val().trim()) {
				e.preventDefault();
				addItem(list, input.val().trim(), box);
				input.val("");
			}
		});
		list.suggest.forEach((name) => {
			$(`<button type="button" class="rhc-suggest">+ ${esc(name)}</button>`)
				.on("click", () => addItem(list, name, box)).appendTo(box.find("[data-suggest]"));
		});
		return box;
	}

	function loadChips(list, box) {
		const args = { doctype: list.doctype, start: 0, page_length: 100 };
		if (list.doctype === "Department" && company) args.company = company;
		return frappe.call({ method: "reckon_hrms.api.setup.list_items", args, type: "GET" }).then((r) => {
			const wrap = box.find(".rhc-chips").empty();
			if (!r.message.rows.length) wrap.append(`<span class="rhc-muted">Nothing added yet.</span>`);
			r.message.rows.forEach((row) => {
				const chip = $(`<span class="rhc-chip">${esc(row.name)} <span class="rhc-n">${row.employees} people</span>
					<button type="button" aria-label="Remove ${esc(row.name)}">×</button></span>`);
				chip.find("button").on("click", () => removeItem(list, row.name, box));
				wrap.append(chip);
			});
			showErr(box, "");
		});
	}

	function addItem(list, name, box) {
		const args = { doctype: list.doctype, name: name };
		if (list.doctype === "Department") args.company = company;
		frappe.call({ method: "reckon_hrms.api.setup.create_item", args })
			.then(() => loadChips(list, box))
			.then(loadState)
			.catch(() => showErr(box, "Could not add that. Check the name and try again."));
	}

	function removeItem(list, name, box) {
		frappe.confirm(`Remove ${name}?`, () => frappe.call({
			method: "reckon_hrms.api.setup.delete_item", args: { doctype: list.doctype, name: name },
		}).then(() => loadChips(list, box))
			.then(loadState)
			.catch(() => showErr(box, "This cannot be removed while employees use it.")));
	}

	root.html(`
		<style>${STYLE}</style>
		<div class="rhc-muted">Step 1 of 3</div>
		<div class="rhc-card"><h2>Progress</h2>
			<div class="rhc-muted"><span id="pct">0</span>% done · <span id="doneCount">0</span> of <span id="totalCount">0</span> steps</div>
			<div class="rhc-bar"><b id="bar" style="width:0%"></b></div>
			<ul class="rhc-checks" id="checks"></ul></div>
		<div class="rhc-card"><h2>Your industry <span class="rhc-map">Company · reckon_industry</span></h2>
			<div class="rhc-muted" id="indNow">Not chosen yet.</div>
			<div class="rhc-row"><select id="indSel" aria-label="Industry" style="height:34px;border:1px solid var(--border-color);border-radius:8px;background:var(--card-bg);color:var(--text-color);padding:0 8px;flex:1 1 260px"><option value="">Choose an industry</option></select>
			<button class="rhc-btn rhc-pri" id="indBtn" type="button">Set up for this industry</button></div>
			<div class="rhc-muted" id="indMsg" style="margin-top:8px">Adds starter job titles, departments, salary components and leave types for your industry. Nothing is paid, and salary amounts stay for you to set.</div></div>
		<div id="lists"></div>
		<div class="rhc-card"><h2>Add your people <span class="rhc-map">Employee · Data Import</span></h2>
			<div class="rhc-muted">Download the template, fill it in, then upload it. We check the file first; nothing is saved until you press Add.</div>
			<div class="rhc-row"><button class="rhc-btn" id="tplBtn" type="button">Download template</button>
			<button class="rhc-btn" id="pickBtn" type="button">Upload CSV file</button></div>
			<div id="impOut" class="rhc-muted" style="margin-top:10px"></div></div>
		<div class="rhc-card"><h2>Next</h2>
			<p class="rhc-muted">Holidays and leave, and attendance settings come next. Until then use the standard
			<a href="/app/employee">Employee list</a>.</p>
			<div class="rhc-row"><a class="rhc-btn rhc-pri" href="/desk/reckon-hrms/reckon-hrms-salary">Continue to salary rules</a></div></div>`);

	// Add your people: template, upload, dry-run check, then a background import with progress.
	const impOut = () => root.find("#impOut");
	root.find("#tplBtn").on("click", () => {
		frappe.call({ method: "reckon_hrms.api.people.employee_template", type: "GET" }).then((r) => {
			const blob = new Blob([r.message.csv], { type: "text/csv" });
			const a = document.createElement("a");
			a.href = URL.createObjectURL(blob);
			a.download = r.message.filename;
			a.click();
		});
	});
	root.find("#pickBtn").on("click", () => {
		new frappe.ui.FileUploader({
			allow_multiple: false,
			restrictions: { allowed_file_types: [".csv"] },
			on_success: (file) => checkFile(file.file_url),
		});
	});
	const checkFile = (fileUrl) => {
		impOut().text("Checking the file…");
		frappe.call({ method: "reckon_hrms.api.people.start_import", args: { file_url: fileUrl } }).then((r) => {
			const s = r.message;
			const rows = s.errors.map((e) => `<tr><td>${esc(e.row)}</td><td>${esc(e.name)}</td><td>${esc(e.problems.join(" "))}</td>
				<td>${e.suggestion ? `<span class="rhc-muted">Did you mean ${esc(e.suggestion)}?</span>` : ""}</td></tr>`).join("");
			impOut().html(`<div><b>${s.read}</b> rows read · <b>${s.ready}</b> ready · <b>${s.to_fix}</b> to fix</div>
				${s.ready ? `<div class="rhc-row"><button class="rhc-btn rhc-pri" id="addBtn" type="button">Add ${s.ready} people</button></div>` : ""}
				${rows ? `<table class="rhc-table" style="margin-top:8px"><tr><th>Row</th><th>Name</th><th>What to fix</th><th></th></tr>${rows}</table>` : ""}
				<div id="impProg" class="rhc-muted" style="margin-top:8px"></div>`);
			impOut().find("#addBtn").on("click", () => startImport(fileUrl));
		}).catch((e) => impOut().html(`<span class="rhc-err">${esc((e && e.message) || "Could not check the file.")}</span>`));
	};
	let impPoll = null;
	const startImport = (fileUrl) => {
		frappe.call({ method: "reckon_hrms.api.people.apply_import", args: { file_url: fileUrl } }).then((r) => {
			clearInterval(impPoll);
			impPoll = setInterval(() => frappe.call({ method: "reckon_hrms.api.people.get_import_progress", args: { job: r.message.job }, type: "GET" })
				.then((p) => {
					const s = p.message;
					impOut().find("#impProg").text(s.state === "done"
						? `Done: ${s.created} added, ${s.failed.length} could not be added.`
						: `Adding… ${s.done} of ${s.total}`);
					if (s.state === "done") { clearInterval(impPoll); loadState(); }
				}), 3000);
		});
	};

	const lists = root.find("#lists");
	const boxes = LISTS.map((list) => {
		const box = chipSection(list);
		lists.append(box);
		return { list, box };
	});
	// Industry: the admin picks a segment, and its starter masters are added to this company.
		const indSel = root.find("#indSel");
		const indMsg = (text) => root.find("#indMsg").text(text);
		frappe.call({ method: "reckon_hrms.api.industry.list_segments", type: "GET" }).then((r) => {
			indSel.append(r.message.map((s) => `<option value="${esc(s.key)}">${esc(s.label)} (${s.role_count} roles)</option>`).join(""));
		}).catch(() => indMsg("Choosing an industry needs the HR Manager role."));
		if (company) {
			frappe.call({ method: "frappe.client.get_value", args: { doctype: "Company", filters: { name: company }, fieldname: "reckon_industry" } })
				.then((r) => {
					const seg = r.message && r.message.reckon_industry;
					const found = seg && indSel.find(`option[value="${seg}"]`).text();
					if (found) root.find("#indNow").text(`Current industry: ${found}`);
				});
		}
		root.find("#indBtn").on("click", () => {
			const seg = indSel.val();
			if (!seg) return indMsg("Choose an industry first.");
			const label = indSel.find("option:selected").text();
			frappe.confirm(`Set up ${company || "your company"} for ${label}? This adds starter job titles, departments, salary components and leave types. Nothing is paid.`, () => {
				indMsg("Setting up…");
				frappe.call({ method: "reckon_hrms.api.industry.choose_segment", args: { segment: seg } }).then((r) => {
					const c = r.message.created;
					indMsg(`Added ${c.designations} job titles, ${c.departments} departments, ${c.components} salary components and ${c.leave_types} leave types.`
						+ (r.message.skipped_components.length ? ` Not added (code already used): ${r.message.skipped_components.join(", ")}.` : ""));
					root.find("#indNow").text(`Current industry: ${label}`);
					boxes.forEach((b) => loadChips(b.list, b.box));
					loadState();
				}).catch((e) => indMsg((e && e.message) || "Could not set up this industry."));
			});
		});
		loadState().catch(() => root.find("#checks").html(`<li class="rhc-err">Could not load the checklist.</li>`));
	boxes.forEach((b) => loadChips(b.list, b.box).catch(() => showErr(b.box, "Could not load this list.")));
};

const STYLE = `
.rhc{max-width:900px;padding:8px 0 40px}
.rhc-muted{color:var(--text-muted);font-size:13px}
.rhc-card{background:var(--card-bg);border:1px solid var(--border-color);border-radius:12px;padding:16px;margin-top:14px}
.rhc-card h2{font-size:15px;margin:0 0 8px;display:flex;gap:8px;align-items:center}
.rhc-map{font:500 11px monospace;background:var(--control-bg);color:var(--text-muted);padding:1px 6px;border-radius:4px;display:none}
body.map .rhc-map{display:inline-block}
.rhc-bar{height:8px;background:var(--control-bg);border-radius:99px;overflow:hidden;margin:8px 0}
.rhc-bar b{display:block;height:100%;background:var(--primary)}
.rhc-checks{list-style:none;padding:0;margin:8px 0 0;display:grid;gap:6px}
.rhc-checks li{display:flex;gap:8px;align-items:center}
.rhc-dot{width:14px;height:14px;border-radius:50%;border:2px solid var(--border-color);display:inline-block}
.rhc-dot.done{background:var(--green-500);border-color:var(--green-500)}
.rhc-chips{display:flex;flex-wrap:wrap;gap:6px;margin:8px 0}
.rhc-chip{display:inline-flex;gap:6px;align-items:center;background:var(--control-bg);border-radius:99px;padding:4px 10px;font-size:13px}
.rhc-chip button{border:0;background:none;color:var(--text-muted);cursor:pointer;font-size:15px;padding:0}
.rhc-n{color:var(--text-muted);font-size:11px}
.rhc-suggest{border:1px dashed var(--text-muted);background:none;color:var(--text-muted);border-radius:99px;padding:4px 10px;cursor:pointer;font-size:13px;margin:0 6px 6px 0}
.rhc-row{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin-top:8px}
.rhc-row input{flex:1 1 180px;min-width:0;height:34px;border:1px solid var(--border-color);border-radius:8px;background:var(--card-bg);color:var(--text-color);padding:0 10px}
.rhc-acts{display:inline-flex;gap:6px;flex:none}
.rhc-ico{display:inline-grid;place-items:center;width:34px;height:34px;border:1px solid var(--border-color);border-radius:8px;background:var(--card-bg);color:var(--text-color);cursor:pointer;text-decoration:none;padding:0}
.rhc-ico:hover{border-color:var(--primary);color:var(--primary)}
.rhc-btn{border:1px solid var(--border-color);background:var(--card-bg);color:var(--text-color);border-radius:8px;padding:6px 12px;cursor:pointer;text-decoration:none}
.rhc-pri{background:var(--primary);color:#fff;border-color:var(--primary)}
.rhc-table{width:100%;border-collapse:collapse;font-size:13px}
.rhc-table th,.rhc-table td{text-align:left;padding:6px 8px;border-bottom:1px solid var(--border-color)}
.rhc-err{color:var(--red-500);font-size:13px;margin-top:6px}
`;
})();

(function () {
// Page 2 (Salary rules), read side: tax slabs, pay items, structures and who lacks a structure.
// Served at /desk/reckon-hrms/reckon-hrms-salary. Editing and the payslip preview come next.
window.ReckonSetupStages.salary = function (parent) {
	const root = $(`<div class="rhs"></div>`).appendTo(parent);
	const company = frappe.defaults.get_user_default("Company") || "";
	const esc = (t) => frappe.utils.escape_html(t == null ? "" : String(t));

	root.html(`
		<style>${STYLE}</style>
		<div class="rhs-muted">Step 2 of 3</div>
		<div class="rhs-card" id="summary"><h2>Who has a salary structure</h2><div class="rhs-muted">Loading…</div></div>
		<div class="rhs-card"><h2>Tax years <span class="rhs-map">Income Tax Slab</span></h2>
			<table class="rhs-table"><tbody id="slabs"></tbody></table>
			<div class="rhs-row"><a class="rhc-ico" href="/app/income-tax-slab/new" title="Add new" aria-label="Add new tax year">${(frappe.utils && frappe.utils.icon ? frappe.utils.icon("add", "sm") : "+")}</a><a class="rhc-ico" href="/app/income-tax-slab" title="Open the list" aria-label="Open the tax years list">${(frappe.utils && frappe.utils.icon ? frappe.utils.icon("list", "sm") : "≡")}</a></div></div>
		<div class="rhs-card"><h2>What you pay and deduct <span class="rhs-map">Salary Component</span></h2>
			<table class="rhs-table"><thead><tr><th>Item</th><th>Kind</th><th>Cut for unpaid leave</th><th>Taxable</th></tr></thead><tbody id="comps"></tbody></table>
			<div class="rhs-row"><a class="rhc-ico" href="/app/salary-component/new" title="Add new" aria-label="Add new pay item">${(frappe.utils && frappe.utils.icon ? frappe.utils.icon("add", "sm") : "+")}</a><a class="rhc-ico" href="/app/salary-component" title="Open the list" aria-label="Open the pay items list">${(frappe.utils && frappe.utils.icon ? frappe.utils.icon("list", "sm") : "≡")}</a></div></div>
		<div class="rhs-card"><h2>Salary structures <span class="rhs-map">Salary Structure</span></h2>
			<table class="rhs-table"><thead><tr><th>Name</th><th>Pay</th><th>Active</th><th>People</th></tr></thead><tbody id="structs"></tbody></table>
			<div class="rhs-row"><a class="rhc-ico" href="/app/salary-structure/new" title="Add new" aria-label="Add new salary structure">${(frappe.utils && frappe.utils.icon ? frappe.utils.icon("add", "sm") : "+")}</a><a class="rhc-ico" href="/app/salary-structure" title="Open the list" aria-label="Open the salary structures list">${(frappe.utils && frappe.utils.icon ? frappe.utils.icon("list", "sm") : "≡")}</a></div></div>
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
			const rows = (list) => list.map((x) => `<tr><td>${esc(x.component)}<div class="rhs-muted" style="font-size:12px">${esc(x.how || "")}</div></td><td style="text-align:right">${money(x.amount)}</td></tr>`).join("");
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
.rhs-btn{border:1px solid var(--border-color);background:var(--card-bg);color:var(--text-color);border-radius:8px;padding:6px 12px;text-decoration:none}.rhc-ico{display:inline-grid;place-items:center;width:34px;height:34px;border:1px solid var(--border-color);border-radius:8px;background:var(--card-bg);color:var(--text-color);cursor:pointer;text-decoration:none;padding:0}.rhc-ico:hover{border-color:var(--primary);color:var(--primary)}
.rhs-pri{background:var(--primary);color:#fff;border-color:var(--primary)}
.rhs-err{color:var(--red-500);font-size:13px;margin-top:6px}
`;
})();

(function () {
// Page 3 (Run salary), five steps: choose month and people, check the list, make draft slips,
// review and approve, then pay. Served at /desk/reckon-hrms/reckon-hrms-run.
window.ReckonSetupStages.run = function (parent) {
	const root = $(`<div class="rhr"></div>`).appendTo(parent);
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
			<div class="rhr-row"><div class="checkbox"><label><input type="checkbox" id="incOt"> <span class="label-area">Include overtime (approved hours, HRMS overtime slips)</span></label></div><div class="checkbox"><label><input type="checkbox" id="incFest"> <span class="label-area">Include festival bonus (Additional Salary, for people on this run)</span></label></div></div>
				<div class="rhr-row"><button class="rhr-btn rhr-pri" id="findBtn" type="button">Find employees</button></div>
			<div class="rhr-err" id="err1"></div>
		</div>
		<div class="rhr-card" id="step2" style="display:none"><div>
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
				<th>ID</th><th>Name</th><th>Department</th><th>Job title</th><th class="rhr-num">Basic</th><th class="rhr-num">Total additions</th><th class="rhr-num">Total deductions</th><th class="rhr-num">Gross</th><th>Status</th></tr></thead>
				<tbody id="rows"></tbody></table>
			<div class="rhr-row"><span id="range" class="rhr-muted"></span>
				<span><button class="rhr-btn" id="prev" type="button">Previous</button> <button class="rhr-btn" id="next" type="button">Next</button></span></div>
			<div class="rhr-row"><span class="rhr-muted">Uncheck a person to leave them out of this run. Nothing is paid to anyone left out.</span></div>
			<div class="rhr-sub" id="reqs" style="display:none;margin-top:14px;border-top:1px solid var(--border-color);padding-top:12px"><h3>Changes waiting for approval</h3><div id="reqList" class="rhr-muted">None.</div></div>
				<div class="rhr-err" id="err2"></div>
			</div>
			<div class="rhr-sub" id="deds" style="display:none;margin-top:16px;border-top:1px solid var(--border-color);padding-top:12px">
				<h3>Late and early deductions <span class="rhr-map">Additional Salary</span></h3>
				<div class="rhr-muted">Late entries and early exits this month, under the company's rule. Nothing is deducted until you apply.</div>
				<div class="rhr-muted" id="dedPolicy" style="margin-top:6px"></div>
				<table class="rhr-table"><thead><tr><th><input type="checkbox" id="dedAll" aria-label="Select everyone shown"></th><th>ID</th><th>Name</th><th>Marks</th><th>Days</th><th>Base</th><th>Deduction</th><th>Status</th></tr></thead>
					<tbody id="dedRows"></tbody></table>
				<div class="rhr-row"><button class="rhr-btn rhr-pri" id="dedApply" type="button">Apply selected deductions</button></div>
				<div class="rhr-muted" id="dedMsg"></div>
				<div class="rhr-err" id="err2b"></div>
			</div>
			</div>
			<div class="rhr-card" id="step3" style="display:none">
				<h2>3 · Make draft slips <span class="rhr-map">Salary Slip (draft)</span></h2>
				<div class="rhr-muted">One draft pay slip for each person on the list. Nothing is paid yet.</div>
				<div class="rhr-row"><button class="rhr-btn rhr-pri" id="mkSlips" type="button">Create draft slips</button> <button class="rhr-btn" id="prevSlips" type="button">Preview draft slips</button></div>
				<div class="rhr-bar"><div id="slipBar"></div></div>
				<div class="rhr-muted" id="slipText"></div>
				<div id="slipPrev" style="margin-top:12px"></div>
				<div class="rhr-err" id="err3"></div>
			</div>
			<div class="rhr-card" id="step4" style="display:none">
				<h2>4 · Review and approve <span class="rhr-map">Submit Salary Slip</span></h2>
				<div class="rhr-sum" id="tot"></div>
				<div class="rhr-alert" id="totNote" style="display:none"></div>
				<div class="rhr-row"><button class="rhr-btn rhr-pri" id="approve" type="button">Submit slips</button></div>
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

	function bindTotals() {
			root.find("input.amt").on("change", function () {
				const cur = Number(this.dataset.cur) || 0;
				const next = Number(this.value) || 0;
				const emp = this.dataset.e;
				const kind = this.dataset.kind;
				const input = this;
				root.find("#err2").text("");
				if (next < cur) {
					input.value = cur;
					return root.find("#err2").text("A lower amount needs a change to the salary structure, on Salary rules.");
				}
				if (next === cur) return;
				frappe.prompt([{ fieldname: "reason", label: "Reason for the change", fieldtype: "Small Text", reqd: 1 }],
					(v) => {
						frappe.call({ method: "reckon_hrms.api.adjustments.request_increase",
							args: { name: state.run, employee: emp, kind, amount: next - cur, reason: v.reason } })
							.then(() => { input.value = cur; root.find("#dedMsg").text("Sent for approval. The total changes once a Payroll Manager approves it."); loadRequests(); })
							.catch((e) => { input.value = cur; root.find("#err2").text((e && e.message) || "Could not send the request."); });
					}, "Request an increase", "Send for approval");
			});
		}

		function loadRequests() {
			if (!state.run) return;
			frappe.call({ method: "reckon_hrms.api.adjustments.pending_requests", args: { name: state.run }, type: "GET" }).then((r) => {
				const rows = r.message || [];
				root.find("#reqs").toggle(rows.length > 0);
				const approver = (frappe.user_roles || []).some((x) => x === "Payroll Manager" || x === "System Manager");
				root.find("#reqList").html(rows.map((x) => `<div class="rhr-row" style="align-items:center">
					<span><b>${esc(x.employee_name)}</b> · ${x.kind === "additions" ? "additions" : "deductions"} +${money(x.amount)} · <span class="rhr-muted">${esc(x.notes)}</span></span>
					${approver && x.can_decide ? `<button class="rhr-btn rhr-pri" data-approve="${esc(x.name)}" type="button">Approve</button><button class="rhr-btn" data-reject="${esc(x.name)}" type="button">Reject</button>` : `<span class="rhr-muted">Waiting for a Payroll Manager</span>`}
					</div>`).join(""));
				root.find("#reqList [data-approve]").on("click", function () {
					frappe.call({ method: "reckon_hrms.api.adjustments.approve_request", args: { request: $(this).data("approve") } })
						.then(() => { loadRequests(); loadPeople(); })
						.catch((e) => root.find("#err2").text((e && e.message) || "Could not approve."));
				});
				root.find("#reqList [data-reject]").on("click", function () {
					frappe.prompt([{ fieldname: "reason", label: "Reason", fieldtype: "Small Text" }], (v) => {
						frappe.call({ method: "reckon_hrms.api.adjustments.reject_request", args: { request: $(this).data("reject"), reason: v.reason } })
							.then(() => loadRequests())
							.catch((e) => root.find("#err2").text((e && e.message) || "Could not reject."));
					}, "Reject request", "Reject");
				});
			});
		}

		function loadPeople() {
			loadRequests();
		call("list_people", { name: state.run, filter: state.filter, search: state.search, start: state.start, page_length: PAGE })
			.then((r) => {
				const p = r.message;
				root.find("#rows").html(p.rows.map((x) => `<tr>
					<td><input type="checkbox" class="pick" data-e="${esc(x.employee)}" ${x.included ? "checked" : ""}></td>
					<td>${esc(x.employee)}</td><td>${esc(x.employee_name)}</td><td>${esc(x.department || "")}</td>
					<td>${esc(x.designation || "")}</td>
						<td class="rhr-num">${money(x.basic)}</td>
						<td class="rhr-num"><input class="amt" type="number" min="0" step="1" data-kind="additions" data-e="${esc(x.employee)}" data-cur="${x.additions || 0}" value="${x.additions || 0}" aria-label="Total additions for ${esc(x.employee_name)}"></td>
						<td class="rhr-num"><input class="amt" type="number" min="0" step="1" data-kind="deductions" data-e="${esc(x.employee)}" data-cur="${x.deductions || 0}" value="${x.deductions || 0}" aria-label="Total deductions for ${esc(x.employee_name)}"></td>
						<td class="rhr-num rhr-gross">${money(x.gross)}</td>
					<td>${x.status === "no_structure" ? '<span class="rhr-chip warn">No salary structure</span>' : '<span class="rhr-chip good">Included</span>'}</td></tr>`).join("")
					|| `<tr><td colspan="10" class="rhr-muted">Nobody matches.</td></tr>`);
				const last = Math.min(p.start + PAGE, p.total);
				root.find("#range").text(p.total ? `Showing ${p.start + 1} to ${last} of ${p.total}` : "No results");
				root.find("#prev").prop("disabled", p.start === 0);
				root.find("#next").prop("disabled", p.start + PAGE >= p.total);
				bindTotals();
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
		function loadDeductions(run) {
			const card = root.find("#deds");
			if (run.step >= 3) { card.hide(); return; }
			card.show();
			frappe.call({ method: "reckon_hrms.api.deductions.attendance_deductions", args: { name: run.name }, type: "GET" }).then((r) => {
				const d = r.message;
				root.find("#dedPolicy").text(`Policy: every ${d.policy.marks_per_day} marks = 1 day. Daily pay = base ÷ ${d.policy.divisor}.` + (d.policy.cap ? ` Cap ${money(d.policy.cap)}.` : " No cap."));
				root.find("#dedRows").html(d.rows.map((x) => `<tr>
					<td><input type="checkbox" class="dpick" data-e="${esc(x.employee)}" ${x.already_applied ? "disabled" : "checked"}></td>
					<td>${esc(x.employee)}</td><td>${esc(x.employee_name)}</td><td>${x.marks}</td><td>${x.days}</td><td>${money(x.base)}</td>
					<td>${money(x.amount)}</td><td>${x.already_applied ? '<span class="rhr-chip good">Applied</span>' : '<span class="rhr-chip warn">Not applied</span>'}</td></tr>`).join("")
					|| `<tr><td colspan="8" class="rhr-muted">No late or early marks this month.</td></tr>`);
				root.find("#dedMsg").text("");
			}).catch((e) => root.find("#err2b").text((e && e.message) || "Could not load deductions."));
		}
		root.find("#dedAll").on("change", function () { root.find("input.dpick:not(:disabled)").prop("checked", this.checked); });
		root.find("#dedApply").on("click", () => {
			const chosen = root.find("input.dpick:checked").map((_, el) => $(el).data("e")).get();
			root.find("#err2b").text("");
			if (!chosen.length) return root.find("#err2b").text("Tick the people to apply.");
			frappe.confirm(`Apply deductions to ${chosen.length} people? They will show on this month's salary slips.`, () => {
				frappe.call({ method: "reckon_hrms.api.deductions.apply_attendance_deductions", args: { name: state.run, employees: chosen } })
					.then((r) => {
						root.find("#dedMsg").text(`${r.message.created} deduction(s) applied.`);
						call("get_run", { name: state.run }).then((x) => loadDeductions(x.message));
					})
					.catch((e) => root.find("#err2b").text((e && e.message) || "Could not apply the deductions."));
			});
		});

		function showSteps(run) {
			loadDeductions(run);
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
			post("create_slips", { name: state.run, include_overtime: root.find("#incOt").is(":checked") ? 1 : 0, include_festival: root.find("#incFest").is(":checked") ? 1 : 0 }).then((r) => poll("get_slip_progress", r.message.job,
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

		root.find("#prevSlips").on("click", () => {
			root.find("#err3").text("");
			frappe.call({ method: "frappe.client.get_list", args: { doctype: "Salary Slip", filters: { payroll_entry: state.run, docstatus: 0 },
				fields: ["employee", "employee_name", "gross_pay", "total_deduction", "net_pay"], order_by: "employee asc", limit_page_length: 500 } })
				.then((r) => {
					const rows = r.message || [];
					root.find("#slipPrev").html(rows.length
						? `<table class="rhr-table"><thead><tr><th>ID</th><th>Name</th><th class="rhr-num">Gross</th><th class="rhr-num">Deductions</th><th class="rhr-num">Net pay</th></tr></thead><tbody>${rows.map((x) => `<tr><td>${esc(x.employee)}</td><td>${esc(x.employee_name)}</td><td class="rhr-num">${money(x.gross_pay)}</td><td class="rhr-num">${money(x.total_deduction)}</td><td class="rhr-num">${money(x.net_pay)}</td></tr>`).join("")}</tbody></table>`
						: `<div class="rhr-muted">No draft slips yet. Create them first.</div>`);
				})
				.catch((e) => root.find("#err3").text((e && e.message) || "Could not load the draft slips."));
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
.rhr-row input[type=checkbox]{height:auto;width:auto;margin:0 6px 0 0;padding:0;flex:none}
.rhr-row label:has(input[type=checkbox]){display:flex;align-items:center;font-size:13px}
.rhr-sub h3{font-size:14px;margin:0 0 8px}
.rhr-num{text-align:right;white-space:nowrap}
.rhr-table input.amt{width:96px;height:30px;border:1px solid var(--border-color);border-radius:6px;background:var(--card-bg);color:var(--text-color);padding:0 6px;text-align:right}
.rhr-gross{font-weight:600}
.rhr-table th,.rhr-table td{text-align:left;padding:6px 8px;border-bottom:1px solid var(--border-color)}
.rhr-chip{border-radius:99px;padding:2px 8px;font-size:12px}
.rhr-chip.good{background:var(--control-bg)}
.rhr-chip.warn{color:var(--orange-500)}
.rhr-err{color:var(--red-500);font-size:13px;margin-top:6px}
.rhr-bar{height:8px;background:var(--control-bg);border-radius:4px;margin-top:10px;overflow:hidden}
.rhr-bar div{height:100%;width:0;background:var(--primary);transition:width .3s}
`;
})();
