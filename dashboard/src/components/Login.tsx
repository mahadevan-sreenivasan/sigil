import { useState, type FormEvent } from 'react';

const STORAGE_KEY = 'sigil_secret_key';

export function Login({ onLogin }: { onLogin: () => void }) {
  const [key, setKey] = useState('');

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    const trimmed = key.trim();
    if (!trimmed) return;
    sessionStorage.setItem(STORAGE_KEY, trimmed);
    onLogin();
  }

  return (
    <div className="login-container">
      <div className="login-card">
        <h1>Sigil Dashboard</h1>
        <p>Enter your secret key to continue.</p>
        <form onSubmit={handleSubmit}>
          <label htmlFor="secret-key">Secret Key</label>
          <input
            id="secret-key"
            type="password"
            value={key}
            onChange={(e) => setKey(e.target.value)}
            placeholder="sk_live_…"
            autoFocus
          />
          <button type="submit">Log in</button>
        </form>
      </div>
    </div>
  );
}
