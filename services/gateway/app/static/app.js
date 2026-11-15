"use strict";
const $ = id => document.getElementById(id);
const state = {project: null, run: null, code: "", generation: 0};
let refreshing = null;
function message(text = "") { $("message").textContent = text; }
async function api(path, method = "GET", body, retry = true) {
  const response = await fetch(`/api/v1${path}`, {method, credentials: "same-origin", headers: body ? {"Content-Type": "application/json"} : {}, body: body ? JSON.stringify(body) : undefined});
  if (response.status === 401 && retry && !path.startsWith("/auth/")) {
    if (!refreshing) refreshing = api("/auth/refresh", "POST", undefined, false).finally(() => { refreshing = null; });
    try { await refreshing; } catch { showUser(null); throw new Error("Сессия истекла. Войдите снова."); }
    return api(path, method, body, false);
  }
  if (response.status === 204) return null;
  const data = await response.json();
  if (!response.ok) throw new Error(data.message || "Запрос не выполнен");
  return data;
}
function node(tag, text, cls) { const n = document.createElement(tag); n.textContent = text; if (cls) n.className = cls; return n; }
function button(text, handler, cls) { const n = node("button", text, cls); n.type = "button"; n.onclick = () => guard(handler, n); return n; }
async function guard(fn, trigger) { if (trigger) trigger.disabled = true; message(); try { await fn(); } catch (e) { message(e.message); } finally { if (trigger) trigger.disabled = false; } }
function showUser(user) {
  state.generation++; state.project = null; state.run = null; state.code = "";
  $("auth").hidden = !!user; $("workspace").hidden = !user; $("logout").hidden = !user;
  $("identity").textContent = user?.email || "";
  $("project").hidden = true; $("empty").hidden = false; $("report").hidden = true;
}
function form(id, handler) { $(id).onsubmit = e => { e.preventDefault(); const data = Object.fromEntries(new FormData(e.target)); guard(() => handler(data, e), e.submitter); }; }
form("auth-form", async (data, e) => {
  if (e.submitter?.name === "register") await api("/auth/register", "POST", data);
  const user = await api("/auth/login", "POST", data); showUser(user); $("auth-form").reset(); await loadProjects();
});
$("logout").onclick = () => guard(async () => { await api("/auth/logout", "POST"); showUser(null); });
async function loadProjects() {
  const generation = state.generation;
  const projects = await api("/projects");
  if (generation !== state.generation) return;
  $("project-count").textContent = projects.length;
  $("projects").replaceChildren(...projects.map(p => button(p.name, () => selectProject(p), `project-item ${state.project?.id === p.id ? "selected" : ""}`)));
  if (!projects.length) $("projects").append(node("p", "Пока нет проектов", "muted small"));
}
form("project-form", async data => { const p = await api("/projects", "POST", data); $("project-form").reset(); await selectProject(p); });
$("example").onclick = () => guard(async () => {
  const p = await api("/projects", "POST", {name: "The Internet", base_url: "https://the-internet.herokuapp.com"});
  const s = await api(`/projects/${p.id}/scenarios`, "POST", {title: "JavaScript error", text: "Открой /javascript_error и проверь ошибки JavaScript при загрузке. Затем заверши проверку."});
  await selectProject(p); $("scenario").value = s.id;
  message("Учебный проект добавлен. Для выполнения сценария подключите LLM; без неё проверяется только главная страница.");
}, $("example"));
async function selectProject(p) {
  state.generation++; state.project = p; state.run = null; state.code = "";
  $("empty").hidden = true; $("project").hidden = false; $("report").hidden = true;
  $("runs").replaceChildren(); $("scenarios").replaceChildren(); $("scenario").replaceChildren(new Option("Свободное исследование", ""));
  $("project-name").textContent = p.name; $("project-url").textContent = p.base_url;
  await Promise.all([loadProjects(), loadScenarios(), loadRuns()]);
}
async function loadScenarios() {
  const generation = state.generation;
  const rows = await api(`/projects/${state.project.id}/scenarios`);
  if (generation !== state.generation) return;
  $("scenario").replaceChildren(new Option("Свободное исследование", ""), ...rows.map(s => new Option(s.title, s.id)));
  $("scenarios").replaceChildren(...rows.map(s => { const n = node("p", `${s.title}: ${s.text} `); n.append(button("Удалить", async () => { await api(`/scenarios/${s.id}`, "DELETE"); await loadScenarios(); })); return n; }));
}
form("scenario-form", async data => { await api(`/projects/${state.project.id}/scenarios`, "POST", data); $("scenario-form").reset(); await loadScenarios(); });
$("delete-project").onclick = () => guard(async () => { if (!confirm("Удалить проект и его сценарии?")) return; await api(`/projects/${state.project.id}`, "DELETE"); state.generation++; state.project = null; state.run = null; $("project").hidden = true; $("empty").hidden = false; await loadProjects(); });
const statuses = {queued: "В очереди", running: "Выполняется", passed: "Без находок", failed: "Найдены ошибки", error: "Сбой раннера", cancelled: "Отменён"};
const active = status => ["queued", "running"].includes(status);
async function loadRuns() {
  if (!state.project) return;
  const generation = state.generation;
  const rows = await api(`/projects/${state.project.id}/runs`);
  if (generation !== state.generation) return;
  $("runs").replaceChildren(...rows.map(r => { const b = button(`${new Date(r.created_at).toLocaleString("ru")} · ${r.id.slice(0,8)}`, () => selectRun(r.id), "run-row"); b.append(node("span", statuses[r.status] || r.status, "badge")); return b; }));
  if (!rows.length) $("runs").append(node("p", "Здесь появится первая проверка.", "muted"));
}
$("start").onclick = () => guard(async () => { const r = await api(`/projects/${state.project.id}/runs`, "POST", {scenario_id: $("scenario").value || null}); await loadRuns(); await selectRun(r.id); }, $("start"));
async function selectRun(id) { state.run = id; await loadReport(); }
async function loadReport() {
  const id = state.run, generation = state.generation;
  if (!id) return;
  const d = await api(`/runs/${id}`);
  if (generation !== state.generation || id !== state.run) return;
  $("report").hidden = false; $("cancel").hidden = !active(d.run.status);
  $("run-meta").textContent = `${statuses[d.run.status] || d.run.status} · ${d.steps.length} шагов · ${d.findings.length} находок · ${d.run.tokens_used} токенов`;
  $("findings").replaceChildren(...d.findings.map(f => { const n = node("article", "", "finding"); n.append(node("strong", f.title), node("p", f.details), node("small", `${f.kind} · ${f.reproduced ? "Воспроизведён" : "Воспроизведение не подтверждено"}`)); return n; }));
  if (!d.findings.length) $("findings").append(node("p", active(d.run.status) ? "Агент собирает результаты…" : "В этом прогоне ошибки не зафиксированы.", "muted"));
  $("steps").replaceChildren(...d.steps.map(s => node("li", `${s.ok ? "✓" : "✕"} ${s.action} ${s.locator || ""} ${s.value || ""}${s.error ? ` — ${s.error}` : ""}`)));
  state.code = d.test?.code || ""; $("test-panel").hidden = !d.test; $("code").textContent = state.code;
  $("verification").textContent = d.test?.verified ? "Тест проверен повторным запуском." : "Тест сгенерирован. Повторный запуск не подтверждён.";
}
$("cancel").onclick = () => guard(async () => { await api(`/runs/${state.run}/cancel`, "POST"); await Promise.all([loadRuns(), loadReport()]); }, $("cancel"));
$("download").onclick = () => { const url = URL.createObjectURL(new Blob([state.code], {type: "text/x-python"})); const a = document.createElement("a"); a.href = url; a.download = `test_scout_${state.run}.py`; a.click(); setTimeout(() => URL.revokeObjectURL(url), 1000); };
async function refresh() { await loadProjects(); if (state.project) await Promise.all([loadRuns(), loadReport()]); }
$("refresh").onclick = () => guard(refresh, $("refresh"));
let polling = false;
setInterval(async () => { if (polling || document.hidden || $("workspace").hidden || !state.project) return; polling = true; try { await Promise.all([loadRuns(), loadReport()]); } catch (e) { message(e.message); } finally { polling = false; } }, 4000);
guard(async () => { let user; try { user = await api("/auth/me"); } catch { try { user = await api("/auth/refresh", "POST"); } catch { return; } } showUser(user); await loadProjects(); });
