import { useState, type FormEvent } from "react";
import { api, type Project, type Run, type Scenario } from "./api";
import { RunReport, StatusBadge } from "./report";
import { useAction, useResource } from "./resources";

const POLL_MS = 4000;
const dateFormat = new Intl.DateTimeFormat("ru", { dateStyle: "medium", timeStyle: "short" });

export function Workspace() {
  const projects = useResource<Project[]>("/projects");
  const [selection, setSelection] = useState<{ project: Project; scenario?: string }>();
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

  async function addExample() {
    const project = await api.post<Project>("/projects", {
      name: "The Internet",
      base_url: "https://the-internet.herokuapp.com",
    });
    setSelection({ project });
    projects.reload();
    const scenario = await api.post<Scenario>(`/projects/${project.id}/scenarios`, {
      title: "JavaScript error",
      text: "Открой /javascript_error и проверь ошибки JavaScript при загрузке. Затем заверши проверку.",
    });
    setSelection({ project, scenario: scenario.id });
  }

  return (
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
            onClick={() => setSelection({ project })}
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
        <button className="example" disabled={action.busy} onClick={() => void action.run(addExample)}>
          Добавить учебный проект
        </button>
        {action.error && <p role="alert" className="error">{action.error}</p>}
      </aside>
      {selection ? (
        <ProjectPanel
          key={`${selection.project.id}:${selection.scenario ?? ""}`}
          project={selection.project}
          initialScenario={selection.scenario ?? ""}
          locked={action.busy}
          onDelete={id => {
            setSelection(current => current?.project.id === id ? undefined : current);
            projects.reload();
          }}
        />
      ) : (
        <section className="card empty">
          <h1>Выберите проект</h1>
          <p>Добавьте свой сайт или учебный проект, чтобы запустить проверку.</p>
        </section>
      )}
    </div>
  );
}

function ProjectPanel({ project, initialScenario, locked, onDelete }: {
  project: Project;
  initialScenario: string;
  locked: boolean;
  onDelete: (id: string) => void;
}) {
  const path = `/projects/${project.id}`;
  const scenarios = useResource<Scenario[]>(`${path}/scenarios`);
  const runs = useResource<Run[]>(`${path}/runs`, POLL_MS);
  const [scenarioId, setScenarioId] = useState(initialScenario);
  const [runId, setRunId] = useState<string>();
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
        <p className="muted small">Без LLM агент проверяет загрузку главной страницы.</p>
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
      {runId && <RunReport key={runId} runId={runId} pollMs={POLL_MS} onChange={runs.reload} />}
    </section>
  );
}
