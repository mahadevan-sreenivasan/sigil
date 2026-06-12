import { apiFetch } from './api';

describe('apiFetch', () => {
  const originalFetch = globalThis.fetch;

  beforeEach(() => {
    sessionStorage.clear();
    sessionStorage.setItem('sigil_secret_key', 'sk_test_key');
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
  });

  it('includes Bearer token from sessionStorage', async () => {
    let capturedInit: RequestInit | undefined;
    globalThis.fetch = vi.fn(async (_url: string | URL | Request, init?: RequestInit) => {
      capturedInit = init;
      return new Response(JSON.stringify({ ok: true }), { status: 200 });
    });

    await apiFetch('/visitors/vis_abc');

    expect(capturedInit?.headers).toEqual(
      expect.objectContaining({ Authorization: 'Bearer sk_test_key' }),
    );
  });

  it('returns parsed JSON for successful responses', async () => {
    globalThis.fetch = vi.fn(async () => {
      return new Response(JSON.stringify({ visitorId: 'vis_abc' }), { status: 200 });
    });

    const data = await apiFetch('/visitors/vis_abc');
    expect(data).toEqual({ visitorId: 'vis_abc' });
  });

  it('throws an AuthError on 401 response', async () => {
    globalThis.fetch = vi.fn(async () => {
      return new Response('Unauthorized', { status: 401 });
    });

    await expect(apiFetch('/visitors/vis_abc')).rejects.toThrow('Unauthorized');
  });

  it('throws on non-OK responses with detail message', async () => {
    globalThis.fetch = vi.fn(async () => {
      return new Response(JSON.stringify({ detail: 'Visitor not found' }), { status: 404 });
    });

    await expect(apiFetch('/visitors/vis_abc')).rejects.toThrow('Visitor not found');
  });
});
