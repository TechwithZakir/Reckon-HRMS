// Reckon HRMS check-in: geo-tagged punch, rendered inside the Desk so the left nav is the Desk's.
frappe.pages["reckon-hrms-checkin"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({ parent: wrapper, title: "Check in / out", single_column: true });
	const root = $(`<div class="rhrms-checkin"></div>`).appendTo(page.main);
	root.html(`
		<style>
		.rhrms-checkin{max-width:420px;margin:24px auto;padding:0 12px}
		.rhrms-checkin .card{background:var(--card-bg);border:1px solid var(--border-color);border-radius:16px;padding:20px}
		.rhrms-checkin .muted{color:var(--text-muted);font-size:13px}
		.rhrms-checkin .status{margin:14px 0;font-size:15px}
		.rhrms-checkin button{width:100%;height:52px;border:0;border-radius:12px;font-size:16px;font-weight:600;color:#fff;background:var(--primary);margin-top:10px}
		.rhrms-checkin button.out{background:var(--gray-700)}
		.rhrms-checkin button:disabled{opacity:.5}
		.rhrms-checkin .msg{margin-top:12px;min-height:22px;font-size:13px}
		.rhrms-checkin .ok{color:var(--green-500)}
		.rhrms-checkin .bad{color:var(--red-500)}
		</style>
		<div class="card">
			<h3 style="margin:0 0 4px">Attendance</h3>
			<div class="muted" id="who">Checking your status…</div>
			<div class="status" id="state"></div>
			<button id="in" disabled>Check in</button>
			<button id="out" class="out" disabled>Check out</button>
			<div class="msg" id="msg" role="status" aria-live="polite"></div>
		</div>`);

	const el = (id) => root.find("#" + id);
	const say = (text, ok) => el("msg").text(text).attr("class", "msg " + (ok ? "ok" : "bad"));

	function here() {
		return new Promise((resolve) => {
			if (!navigator.geolocation) return resolve({});
			navigator.geolocation.getCurrentPosition(
				(p) => resolve({ latitude: p.coords.latitude, longitude: p.coords.longitude }),
				() => resolve({}),
				{ enableHighAccuracy: true, timeout: 15000, maximumAge: 0 });
		});
	}

	function refresh() {
		return frappe.call({ method: "reckon_hrms.api.attendance.my_status" }).then((r) => {
			const s = r.message;
			el("who").text(`${s.employee_name} (${s.employee})`);
			el("state").text(s.checked_in ? "You are checked in." : "You are checked out.");
			el("in").prop("disabled", s.checked_in);
			el("out").prop("disabled", !s.checked_in);
		});
	}

	function punch(type) {
		el("in").prop("disabled", true);
		el("out").prop("disabled", true);
		here()
			.then((pos) => frappe.call({ method: "reckon_hrms.api.attendance.punch", args: Object.assign({ log_type: type }, pos) }))
			.then((r) => {
				const m = r.message;
				const dist = m.distance_m !== undefined ? ` · ${m.distance_m} m from office` : "";
				say((type === "IN" ? "Checked in" : "Checked out") + dist, true);
			})
			.catch((e) => say((e && e.message) || "Could not record the punch.", false))
			.finally(() => refresh().catch(() => {}));
	}

	el("in").on("click", () => punch("IN"));
	el("out").on("click", () => punch("OUT"));
	refresh().catch((e) => say((e && e.message) || "Could not load your status.", false));
};
