const STORAGE_KEY = 'sigil_secret_key';

export class AuthError extends Error {
  constructor() {
    super('Unauthorized');
    this.name = 'AuthError';
  }
}

export function getSecretKey(): string | null {
  return sessionStorage.getItem(STORAGE_KEY);
}

export async function apiFetch<T = unknown>(path: string): Promise<T> {
  const key = getSecretKey();
  const resp = await fetch(path, {
    headers: {
      Authorization: `Bearer ${key ?? ''}`,
      'Content-Type': 'application/json',
    },
  });

  if (resp.status === 401) {
    throw new AuthError();
  }

  if (!resp.ok) {
    let message = `Request failed: ${resp.status}`;
    try {
      const body = await resp.json();
      if (body.detail) message = body.detail;
    } catch { /* use default message */ }
    throw new Error(message);
  }

  return resp.json();
}
