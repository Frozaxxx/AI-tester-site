import { useCallback, useEffect, useState, type FormEvent } from "react";
import { createRoot } from "react-dom/client";
import { api, sessionExpired, type User } from "./api";
import { useAction } from "./resources";
import { Workspace } from "./workspace";
import "./style.css";

function SignIn({ onLogin }: { onLogin: (user: User) => void }) {
  const action = useAction();

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const values = new FormData(event.currentTarget);
    const credentials = {
      email: String(values.get("email")),
      password: String(values.get("password")),
    };
    const submitter = (event.nativeEvent as SubmitEvent).submitter;
    void action.run(async () => {
      if (submitter?.getAttribute("name") === "register") await api.register(credentials);
      onLogin(await api.login(credentials));
    });
  }

  return (
    <>
      <section className="intro">
        <h1>Проверка сайтов</h1>
        <p>Запускайте браузерные сценарии, изучайте найденные ошибки и скачивайте Playwright-тесты.</p>
      </section>
      <section className="card narrow" aria-labelledby="sign-in">
        <h2 id="sign-in">Вход в Scout</h2>
        <form onSubmit={submit}>
          <fieldset disabled={action.busy}>
            <label>Email<input name="email" type="email" autoComplete="email" required maxLength={254} /></label>
            <label>Пароль<input name="password" type="password" autoComplete="current-password" required minLength={8} maxLength={128} /></label>
            <div className="actions">
              <button type="submit" className="primary">Войти</button>
              <button type="submit" name="register">Создать аккаунт</button>
            </div>
          </fieldset>
        </form>
        {action.error && <p role="alert" className="error">{action.error}</p>}
      </section>
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
        <a className="brand" href="/">Scout</a>
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
            <SignIn onLogin={next => { setExpired(false); setUser(next); }} />
          </>
        )}
      </main>
    </>
  );
}

createRoot(document.getElementById("root")!).render(<App />);
