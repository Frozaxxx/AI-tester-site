import { useCallback, useEffect, useState } from "react";
import { api } from "./api";

export function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : "Запрос не выполнен";
}

export function useResource<T>(path: string, pollMs?: number) {
  const [data, setData] = useState<T>();
  const [error, setError] = useState("");
  const [revision, setRevision] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    let timer: ReturnType<typeof setTimeout>;

    async function load() {
      try {
        const next = await api.get<T>(path, controller.signal);
        if (controller.signal.aborted) return;
        setData(next);
        setError("");
      } catch (error) {
        if (!controller.signal.aborted) setError(errorMessage(error));
      } finally {
        scheduleNext();
      }
    }

    function scheduleNext() {
      if (!pollMs || controller.signal.aborted) return;
      timer = setTimeout(() => {
        if (document.hidden) scheduleNext();
        else void load();
      }, pollMs);
    }

    void load();
    return () => {
      controller.abort();
      clearTimeout(timer);
    };
  }, [path, pollMs, revision]);

  return { data, error, reload: () => setRevision(value => value + 1) };
}

export function useAction() {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const run = useCallback(async (action: () => Promise<void>) => {
    setBusy(true);
    setError("");
    try {
      await action();
    } catch (error) {
      setError(errorMessage(error));
    } finally {
      setBusy(false);
    }
  }, []);

  return { busy, error, run };
}
