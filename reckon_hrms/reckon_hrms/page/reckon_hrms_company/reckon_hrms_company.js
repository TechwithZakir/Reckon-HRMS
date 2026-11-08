// Page 1 (Your company): checklist and tap-to-add lists. Served at /desk/reckon-hrms/reckon-hrms-company.
frappe.pages["reckon-hrms-company"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({ parent: wrapper, title: "Your company", single_column: true });
	const root = $(`<div class="rhc"></div>`).appendTo(page.main);
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

	function chipSection(list) {
		const box = $(`<section class="rhc-card">
			<h2>${esc(list.title)}<span class="rhc-map">${esc(list.map)}</span></h2>
			<div class="rhc-chips"></div>
			<div class="rhc-row"><input type="text" maxlength="140" placeholder="Type a name and press Enter" aria-label="Add ${esc(list.title)}">
			<a class="rhc-btn" href="${slug(list.doctype)}">List</a></div>
			<div class="rhc-row" data-suggest></div><div class="rhc-err" data-err></div></section>`);
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
		<div id="lists"></div>
		<div class="rhc-card"><h2>Next</h2>
			<p class="rhc-muted">Adding your people, holidays and leave, and attendance settings come next. Until then use the standard
			<a href="/app/employee">Employee list</a>.</p>
			<div class="rhc-row"><a class="rhc-btn rhc-pri" href="/desk/reckon-hrms/salary">Continue to salary rules</a></div></div>`);

	const lists = root.find("#lists");
	const boxes = LISTS.map((list) => {
		const box = chipSection(list);
		lists.append(box);
		return { list, box };
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
.rhc-btn{border:1px solid var(--border-color);background:var(--card-bg);color:var(--text-color);border-radius:8px;padding:6px 12px;cursor:pointer;text-decoration:none}
.rhc-pri{background:var(--primary);color:#fff;border-color:var(--primary)}
.rhc-err{color:var(--red-500);font-size:13px;margin-top:6px}
`;
