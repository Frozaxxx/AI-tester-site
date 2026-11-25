import { api, type RunDetails, type RunStatus } from "./api";
import { useAction, useResource } from "./resources";

const statusLabels: Record<RunStatus, string> = {
  queued: "В очереди",
  running: "Выполняется",
  passed: "Без находок",
  failed: "Найдены ошибки",
  error: "Сбой раннера",
  cancelled: "Отменён",
};

export function StatusBadge({ status }: { status: RunStatus }) {
  return <span className={`badge badge-${status}`}>{statusLabels[status] ?? status}</span>;
}

function downloadTest(runId: string, code: string) {
  const url = URL.createObjectURL(new Blob([code], { type: "text/x-python" }));
  const link = document.createElement("a");
  link.href = url;
  link.download = `test_scout_${runId}.py`;
  link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

export function RunReport({ runId, pollMs, onChange }: {
  runId: string;
  pollMs: number;
  onChange: () => void;
}) {
  const path = `/runs/${runId}`;
  const report = useResource<RunDetails>(path, pollMs);
  const action = useAction();
  const result = report.data;
  const active = result?.run.status === "queued" || result?.run.status === "running";

  return (
    <section className="card" aria-labelledby="report-heading">
      <div className="section-head">
        <h2 id="report-heading">Отчёт · {runId.slice(0, 8)}</h2>
        {active && (
          <button disabled={action.busy} onClick={() => void action.run(async () => {
            await api.post<void>(`${path}/cancel`);
            report.reload();
            onChange();
          })}>Отменить прогон</button>
        )}
      </div>
      {(report.error || action.error) && <p role="alert" className="error">{report.error || action.error}</p>}
      {!result && !report.error && <p role="status">Загружаем отчёт…</p>}
      {result && (
        <>
          <div className="actions report-meta">
            <StatusBadge status={result.run.status} />
            <span className="muted small">Шаги {result.steps.length} · Находки {result.findings.length} · Токены {result.run.tokens_used}</span>
          </div>
          <h3>Находки</h3>
          {result.findings.length === 0 && (
            <p className="muted">{active ? "Агент собирает результаты…" : "В этом прогоне ошибки не зафиксированы."}</p>
          )}
          {result.findings.map(finding => (
            <article className="finding" key={finding.id}>
              <strong>{finding.title}</strong>
              <p>{finding.details}</p>
              <small>{finding.kind} · {finding.reproduced ? "Воспроизведён" : "Воспроизведение не подтверждено"}</small>
            </article>
          ))}
          <details>
            <summary>Шаги агента ({result.steps.length})</summary>
            <ol>
              {result.steps.map(step => (
                <li key={step.index}>
                  {step.ok ? "Успешно" : "Ошибка"} · {step.action} {step.locator} {step.value}
                  {step.error && <div>{step.error}</div>}
                </li>
              ))}
            </ol>
          </details>
          {result.test && <GeneratedTest runId={runId} test={result.test} />}
        </>
      )}
    </section>
  );
}

function GeneratedTest({ runId, test }: { runId: string; test: NonNullable<RunDetails["test"]> }) {
  return (
    <details>
      <summary>Playwright-тест</summary>
      <p className="muted">{test.verified ? "Тест проверен повторным запуском." : "Тест ожидает подтверждения повторным запуском."}</p>
      <button onClick={() => downloadTest(runId, test.code)}>Скачать .py</button>
      <pre tabIndex={0}><code>{test.code}</code></pre>
    </details>
  );
}
