export interface User {
  id: string;
  email: string;
}

export interface Project {
  id: string;
  name: string;
  base_url: string;
}

export interface Scenario {
  id: string;
  title: string;
  text: string;
}

export type RunStatus = "queued" | "running" | "passed" | "failed" | "error" | "cancelled";

export interface Run {
  id: string;
  scenario_id: string | null;
  status: RunStatus;
  tokens_used: number;
  created_at: string;
}

export interface RunDetails {
  run: Run;
  findings: {
    id: string;
    kind: string;
    title: string;
    details: string;
    reproduced: boolean;
  }[];
  steps: {
    index: number;
    action: string;
    ok: boolean;
    locator: string | null;
    value: string | null;
    error: string | null;
  }[];
  test: { code: string; verified: boolean } | null;
}

class ApiError extends Error {
  constructor(readonly status: number, message: string) {
    super(message);
  }
}

interface RequestOptions {
  method?: "GET" | "POST" | "DELETE";
  body?: Record<string, string | null>;
  signal?: AbortSignal;
}

export const sessionExpired = new EventTarget();
let refreshing: Promise<User> | undefined;

async function request<T>(path: string, options: RequestOptions = {}, retry = true): Promise<T> {
  const { method = "GET", body, signal } = options;
  const response = await fetch(`/api/v1${path}`, {
    method,
    credentials: "same-origin",
    signal,
    headers: body ? { "Content-Type": "application/json" } : undefined,
    body: body ? JSON.stringify(body) : undefined,
  });
  if (response.status === 401 && retry && !path.startsWith("/auth/")) {
    try {
      signal?.throwIfAborted();
      await refreshSession();
    } catch (error) {
      if (error instanceof ApiError && error.status === 401) {
        sessionExpired.dispatchEvent(new Event("expired"));
      }
      throw error;
    }
    return request<T>(path, options, false);
  }
  if (!response.ok) {
    const error = await response.json().catch(() => null);
    throw new ApiError(response.status, error?.message ?? "Запрос не выполнен");
  }
  return response.status === 204 ? (undefined as T) : response.json();
}

function refreshSession(): Promise<User> {
  refreshing ??= request<User>("/auth/refresh", { method: "POST" })
    .catch((error: unknown) => {
      if (error instanceof ApiError && error.status === 401) {
        throw new ApiError(401, "Сессия истекла. Войдите снова.");
      }
      throw error;
    })
    .finally(() => {
      refreshing = undefined;
    });
  return refreshing;
}

export const api = {
  session: async () => {
    try {
      return await request<User>("/auth/me");
    } catch (error) {
      if (!(error instanceof ApiError) || error.status !== 401) throw error;
      try {
        return await refreshSession();
      } catch (refreshError) {
        if (refreshError instanceof ApiError && refreshError.status === 401) return null;
        throw refreshError;
      }
    }
  },
  login: (body: { email: string; password: string }) =>
    request<User>("/auth/login", { method: "POST", body }),
  register: (body: { email: string; password: string }) =>
    request<User>("/auth/register", { method: "POST", body }),
  logout: async () => {
    await refreshing?.catch(() => undefined);
    await request<void>("/auth/logout", { method: "POST" });
  },
  get: <T>(path: string, signal: AbortSignal) => request<T>(path, { signal }),
  post: <T>(path: string, body?: RequestOptions["body"]) =>
    request<T>(path, { method: "POST", body }),
  remove: (path: string) => request<void>(path, { method: "DELETE" }),
};
