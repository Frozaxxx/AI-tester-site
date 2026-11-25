import { useState, type FormEvent } from "react";
import { api, type Project, type Run, type Scenario } from "./api";
import { RunReport, StatusBadge } from "./report";
import { useAction, useResource } from "./resources";

const POLL_MS = 4000;
const dateFormat = new Intl.DateTimeFormat("ru", { dateStyle: "medium", timeStyle: "short" });

export function Workspace() {
  const projects = useResource<Project[]>("/projects");
  const [selection, setSelection] = useState<{ project: Project; runId?: string }>();
  const action = useAction();

  function createProject(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const values = new FormData(form);
    void action.run(async () => {
      const project = await api.post<Project>("/projects", {
        name: String(values.get("name")),
        base_url: String(values.get("base_url")),
      });
      form.reset();
      setSelection({ project });
      projects.reload();
    });
  }

  function quickRun(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const rawUrl = String(new FormData(event.currentTarget).get("url")).trim();
    void action.run(async () => {
      const url = URL.parse(rawUrl);
      if (!url || !["http:", "https:"].includes(url.protocol) || url.username || url.password) {
        throw new Error("Вставьте ссылку http:// или https:// без логина и пароля.");
      }
      const existing = projects.data?.find(project => URL.parse(project.base_url)?.href === url.href);
      const project = existing ?? await api.post<Project>("/projects", {
        name: url.host.slice(0, 200),
        base_url: url.href,
      });
      if (!existing) {
        projects.reload();
        setSelection({ project });
      }
      const run = await api.post<Run>(`/projects/${project.id}/runs`, { scenario_id: null });
      setSelection({ project, runId: run.id });
    });
  }

  return (
    <div className="workspace">
      <section className="card" aria-labelledby="quick-run-heading">
        <h2 id="quick-run-heading">Проверить сайт</h2>
        <form onSubmit={quickRun}>
          <fieldset disabled={action.busy || (!projects.data && !projects.error)}>
            <label htmlFor="quick-site-url">Ссылка на страницу</label>
            <div className="actions quick-run">
              <input id="quick-site-url" name="url" type="url" inputMode="url" autoComplete="url"
                placeholder="https://example.com/page" required maxLength={2048} />
              <button type="submit" className="primary">Запустить</button>
            </div>
          </fieldset>
        </form>
        {action.busy && <p role="status" className="muted">Выполняем запрос…</p>}
        {action.error && <p role="alert" className="error">{action.error}</p>}
      </section>
      <div className="layout">
        <aside className="card" aria-labelledby="projects-heading">
          <div className="section-head">
            <h2 id="projects-heading">Проекты</h2>
            <button onClick={projects.reload}>Обновить</button>
          </div>
          {!projects.data && !projects.error && <p role="status" className="muted">Загружаем проекты…</p>}
          {projects.error && <p role="alert" className="error">{projects.error}</p>}
          {projects.data?.map(project => (
            <button
              key={project.id}
              disabled={action.busy}
              aria-pressed={selection?.project.id === project.id}
              className="project-item"
              onClick={() => setSelection(current => current?.project.id === project.id ? current : { project })}
            >{project.name}</button>
          ))}
          {projects.data?.length === 0 && <p className="muted">Пока нет проектов.</p>}
          <form className="divider" onSubmit={createProject}>
            <fieldset disabled={action.busy}>
              <legend>Новый проект</legend>
              <label>Название<input name="name" required maxLength={200} /></label>
              <label>Адрес сайта<input name="base_url" type="url" required maxLength={2048} placeholder="https://example.com" /></label>
              <button className="primary" type="submit">Добавить проект</button>
            </fieldset>
          </form>
        </aside>
        {selection ? (
          <ProjectPanel
            key={`${selection.project.id}:${selection.runId ?? ""}`}
            project={selection.project}
            initialRunId={selection.runId}
            locked={action.busy}
            onDelete={id => {
              setSelection(current => current?.project.id === id ? undefined : current);
              projects.reload();
            }}
          />
        ) : (
          <section className="card empty">
            <h1>Выберите проект</h1>
            <p>Новые прогоны и отчёты появятся здесь.</p>
          </section>
        )}
      </div>
    </div>
  );
}

function ProjectPanel({ project, initialRunId, locked, onDelete }: {
  project: Project;
  initialRunId?: string;
  locked: boolean;
  onDelete: (id: string) => void;
}) {
  const path = `/projects/${project.id}`;
  const scenarios = useResource<Scenario[]>(`${path}/scenarios`);
  const runs = useResource<Run[]>(`${path}/runs`, POLL_MS);
  const [scenarioId, setScenarioId] = useState("");
  const [runId, setRunId] = useState(initialRunId);
  const action = useAction();
  const busy = locked || action.busy;

  async function startRun() {
    const run = await api.post<Run>(`${path}/runs`, { scenario_id: scenarioId || null });
    setRunId(run.id);
    runs.reload();
  }

  function addScenario(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const values = new FormData(form);
    void action.run(async () => {
      await api.post<Scenario>(`${path}/scenarios`, {
        title: String(values.get("title")),
        text: String(values.get("text")),
      });
      form.reset();
      scenarios.reload();
    });
  }

  return (
    <section className="content" aria-label={project.name}>
      <div className="card">
        <h1>{project.name}</h1>
        <p className="muted">{project.base_url}</p>
        <div className="actions">
          <select value={scenarioId} disabled={busy} onChange={event => setScenarioId(event.target.value)} aria-label="Сценарий проверки">
            <option value="">Свободное исследование</option>
            {scenarios.data?.map(scenario => <option key={scenario.id} value={scenario.id}>{scenario.title}</option>)}
          </select>
          <button disabled={busy || Boolean(scenarioId && !scenarios.data)} className="primary" onClick={() => void action.run(startRun)}>Запустить проверку</button>
          <button disabled={busy} onClick={() => void action.run(async () => {
            if (!window.confirm("Удалить проект и его сценарии?")) return;
            await api.remove(path);
            onDelete(project.id);
          })}>Удалить проект</button>
        </div>
        <p className="muted small">Без LLM раннер проверяет загрузку указанной страницы.</p>
        <details>
          <summary>Сценарии проверки</summary>
          {scenarios.error && <p role="alert" className="error">{scenarios.error} <button onClick={scenarios.reload}>Повторить</button></p>}
          {scenarios.data?.map(scenario => (
            <article className="scenario" key={scenario.id}>
              <h3>{scenario.title}</h3>
              <p>{scenario.text}</p>
              <button disabled={busy} onClick={() => void action.run(async () => {
                await api.remove(`/scenarios/${scenario.id}`);
                setScenarioId(current => current === scenario.id ? "" : current);
                scenarios.reload();
              })}>Удалить сценарий</button>
            </article>
          ))}
          <form onSubmit={addScenario}>
            <fieldset disabled={busy}>
              <legend>Новый сценарий</legend>
              <label>Название<input name="title" required maxLength={200} /></label>
              <label>Задание агенту<textarea name="text" required maxLength={10000} /></label>
              <button type="submit">Сохранить сценарий</button>
            </fieldset>
          </form>
        </details>
        {action.error && <p role="alert" className="error">{action.error}</p>}
      </div>
      {runId && <RunReport key={runId} runId={runId} pollMs={POLL_MS} onChange={runs.reload} />}
      <section className="card" aria-labelledby="runs-heading">
        <div className="section-head">
          <h2 id="runs-heading">Прогоны</h2>
          <button onClick={runs.reload}>Обновить</button>
        </div>
        {runs.error && <p role="alert" className="error">{runs.error}</p>}
        {!runs.data && !runs.error && <p role="status" className="muted">Загружаем прогоны…</p>}
        {runs.data?.map(run => (
          <button key={run.id} className="run-row" aria-pressed={runId === run.id} onClick={() => setRunId(run.id)}>
            <span>{dateFormat.format(new Date(run.created_at))} · {run.id.slice(0, 8)}</span>
            <StatusBadge status={run.status} />
          </button>
        ))}
        {runs.data?.length === 0 && <p className="muted">Здесь появится первый прогон.</p>}
      </section>
    </section>
  );
}
