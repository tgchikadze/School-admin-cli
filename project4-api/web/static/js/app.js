
const API = "";

async function fetchJSON(url) {
    const resp = await fetch(url);
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    return resp.json();
}

async function loadUniversities(page = 1) {
    const city = document.getElementById("filterCity")?.value || "";
    const search = document.getElementById("filterSearch")?.value || "";
    let url = `${API}/api/universities?page=${page}&size=20`;
    if (city) url += `&city=${encodeURIComponent(city)}`;
    if (search) url += `&search=${encodeURIComponent(search)}`;
    const data = await fetchJSON(url);
    renderUniversities(data);
}

function renderUniversities(data) {
    const c = document.getElementById("uniList");
    if (!c) return;
    c.innerHTML = data.items.map(u => `
        <div class="col-md-4 mb-3"><div class="card card-uni h-100"><div class="card-body">
            <h5 class="card-title">${u.name}</h5>
            <p class="card-text text-muted">${u.city}</p>
        </div></div></div>`).join("");
    renderPagination(data, "uniPagination", loadUniversities);
}

async function loadPrograms(page = 1) {
    const uni = document.getElementById("filterUni")?.value || "";
    const okso = document.getElementById("filterOkso")?.value || "";
    const search = document.getElementById("filterSearch")?.value || "";
    let url = `${API}/api/programs?page=${page}&size=20`;
    if (uni) url += `&university_id=${encodeURIComponent(uni)}`;
    if (okso) url += `&okso_code=${encodeURIComponent(okso)}`;
    if (search) url += `&search=${encodeURIComponent(search)}`;
    const data = await fetchJSON(url);
    renderPrograms(data);
}

function renderPrograms(data) {
    const tb = document.getElementById("programsBody");
    if (!tb) return;
    tb.innerHTML = data.items.map(p => `<tr>
        <td>${p.university_id}</td><td>${p.okso_code}</td><td>${p.program_name}</td>
        <td>${p.program_level}</td><td>${p.min_score || "-"}</td>
        <td>${p.budget_places || "-"}</td><td>${p.cost || "-"}</td>
        <td>${p.ege_subjects || "-"}</td></tr>`).join("");
    renderPagination(data, "programsPagination", loadPrograms);
}

async function loadOlympiads(page = 1) {
    const uni = document.getElementById("filterUni")?.value || "";
    const subject = document.getElementById("filterSubject")?.value || "";
    const benefit = document.getElementById("filterBenefit")?.value || "";
    let url = `${API}/api/olympiads?page=${page}&size=20`;
    if (uni) url += `&university_id=${encodeURIComponent(uni)}`;
    if (subject) url += `&subject=${encodeURIComponent(subject)}`;
    if (benefit) url += `&benefit_type=${encodeURIComponent(benefit)}`;
    const data = await fetchJSON(url);
    renderOlympiads(data);
}

function renderOlympiads(data) {
    const tb = document.getElementById("olympiadsBody");
    if (!tb) return;
    tb.innerHTML = data.items.map(o => `<tr>
        <td>${o.university_id}</td><td>${o.olympiad_name}</td>
        <td>${o.olympiad_level || "-"}</td><td>${o.subject}</td>
        <td><span class="badge ${o.benefit_type.includes("БВИ") ? "badge-bvi" : o.benefit_type.includes("100") ? "badge-100" : "badge-extra"}">${o.benefit_type || "-"}</span></td>
        <td>${o.benefit_detail ? o.benefit_detail.slice(0,120)+"..." : "-"}</td></tr>`).join("");
    renderPagination(data, "olympiadsPagination", loadOlympiads);
}

function renderPagination(data, containerId, loadFn) {
    const c = document.getElementById(containerId);
    if (!c || data.pages <= 1) { if (c) c.innerHTML = ""; return; }
    let html = "";
    for (let i = 1; i <= data.pages; i++) {
        html += `<li class="page-item ${i === data.page ? "active" : ""}">
            <a class="page-link" onclick="${loadFn.name}(${i})">${i}</a></li>`;
    }
    c.innerHTML = html;
}

async function loadStats() {
    const d = await fetchJSON(`${API}/api/stats`);
    const el = document.getElementById("statsBar");
    if (el) el.innerHTML = `<span class="badge bg-primary me-2">${d.universities} vuzov</span>
        <span class="badge bg-success me-2">${d.programs} programs</span>
        <span class="badge bg-info">${d.olympiads} olympiads</span>`;
}
