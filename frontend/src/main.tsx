import { useCallback, useEffect, useRef, useState, type FormEvent } from "react";
import { createRoot } from "react-dom/client";
import { api, sessionExpired, type User } from "./api";
import { useAction } from "./resources";
import { Workspace } from "./workspace";
import "./style.css";

const EMAIL_PATTERN = /^[^@\s]+@[^@\s]+\.[^@\s]+$/;
const MIN_REGISTRATION_PASSWORD_LENGTH = 8;

function AuthScreen({ onLogin }: { onLogin: (user: User) => void }) {
  const [registering, setRegistering] = useState(false);
  const heading = useRef<HTMLHeadingElement>(null);

  useEffect(() => {
    heading.current?.focus();
  }, [registering]);

  return (
    <>
      <section className="intro">
        <h1>Проверка сайтов</h1>
        <p>Запускайте браузерные сценарии, изучайте найденные ошибки и скачивайте Playwright-тесты.</p>
      </section>
      <section className="card narrow" aria-labelledby="auth-heading">
        <h2 id="auth-heading" ref={heading} tabIndex={-1}>
          {registering ? "Регистрация в AI Tester" : "Вход в AI Tester"}
        </h2>
        <CredentialsForm
          key={registering ? "register" : "login"}
          registering={registering}
          onSwitch={() => setRegistering(!registering)}
          onLogin={onLogin}
        />
      </section>
    </>
  );
}

function CredentialsForm({ registering, onSwitch, onLogin }: {
  registering: boolean;
  onSwitch: () => void;
  onLogin: (user: User) => void;
}) {
  const action = useAction();
  const [emailError, setEmailError] = useState("");
  const [passwordError, setPasswordError] = useState("");

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const values = new FormData(form);
    const credentials = {
      email: String(values.get("email") ?? "").trim(),
      password: String(values.get("password") ?? ""),
    };
    const invalidEmail = !EMAIL_PATTERN.test(credentials.email);
    const invalidPassword = !credentials.password
      ? "Введите пароль."
      : registering && credentials.password.length < MIN_REGISTRATION_PASSWORD_LENGTH
        ? "Для регистрации нужен пароль от 8 символов."
        : "";
    setEmailError(invalidEmail ? "Введите email в формате name@example.com." : "");
    setPasswordError(invalidPassword);
    if (invalidEmail || invalidPassword) {
      form.querySelector<HTMLInputElement>(invalidEmail ? "[name=email]" : "[name=password]")?.focus();
      return;
    }

    void action.run(async () => {
      if (registering) await api.register(credentials);
      onLogin(await api.login(credentials));
    });
  }

  return (
    <>
      <form noValidate onSubmit={submit}>
        <fieldset disabled={action.busy}>
          <label>
            Email
            <input name="email" type="email" autoComplete="email" required maxLength={254}
              aria-invalid={Boolean(emailError)} aria-describedby={emailError ? "email-error" : undefined}
              onChange={() => setEmailError("")} />
          </label>
          {emailError && <p id="email-error" role="alert" className="field-error">{emailError}</p>}
          <label>
            Пароль
            <input name="password" type="password"
              autoComplete={registering ? "new-password" : "current-password"} required maxLength={128}
              aria-invalid={Boolean(passwordError)}
              aria-describedby={passwordError ? "password-error" : registering ? "password-hint" : undefined}
              onChange={() => setPasswordError("")} />
          </label>
          {passwordError ? (
            <p id="password-error" role="alert" className="field-error">{passwordError}</p>
          ) : registering && (
            <p id="password-hint" className="muted small">Минимум 8 символов.</p>
          )}
          <div className="actions">
            <button type="submit" className="primary">{registering ? "Зарегистрироваться" : "Войти"}</button>
            <button type="button" onClick={onSwitch}>
              {registering ? "Вернуться ко входу" : "Создать аккаунт"}
            </button>
          </div>
        </fieldset>
      </form>
      {action.busy && <p role="status" className="muted">Отправляем запрос…</p>}
      {action.error && !emailError && !passwordError && <p role="alert" className="error">{action.error}</p>}
    </>
  );
}

function App() {
  const [user, setUser] = useState<User | null>();
  const [expired, setExpired] = useState(false);
  const session = useAction();
  const { run } = session;

  const loadSession = useCallback(() => run(async () => setUser(await api.session())), [run]);

  useEffect(() => {
    function clearSession() {
      setExpired(true);
      setUser(null);
    }
    sessionExpired.addEventListener("expired", clearSession);
    void loadSession();
    return () => sessionExpired.removeEventListener("expired", clearSession);
  }, [loadSession]);

  return (
    <>
      <header>
        <a className="brand" href="/">AI Tester</a>
        <nav aria-label="Навигация" className="actions">
          <a href="/docs">REST API</a>
          {user && (
            <>
              <span className="identity">{user.email}</span>
              <button disabled={session.busy} onClick={() => void run(async () => {
                await api.logout();
                setUser(null);
              })}>Выйти</button>
            </>
          )}
        </nav>
      </header>
      <main>
        {session.error && <p role="alert" className="error">{session.error}</p>}
        {user === undefined ? (
          session.error ? <button onClick={() => void loadSession()}>Повторить</button> :
            <p role="status">Проверяем сессию…</p>
        ) : user ? (
          <Workspace key={user.id} />
        ) : (
          <>
            {expired && <p className="error" role="status">Сессия истекла. Войдите снова.</p>}
            <AuthScreen onLogin={next => { setExpired(false); setUser(next); }} />
          </>
        )}
      </main>
    </>
  );
}

createRoot(document.getElementById("root")!).render(<App />);
