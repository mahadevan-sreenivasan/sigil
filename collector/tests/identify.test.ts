import { describe, it, expect, vi, beforeEach } from 'vitest';
import { SigilCollector } from '../src/collector';

vi.mock('../src/signals/canvas', () => ({
  collectCanvasHash: vi.fn().mockResolvedValue('abc123canvas'),
}));

describe('SigilCollector.identify', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('POSTs collected signals to serverUrl and returns identification result', async () => {
    const serverResponse = {
      visitorId: 'vis_test123',
      isNewVisitor: true,
      serverReachable: true,
    };

    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(serverResponse),
    });
    vi.stubGlobal('fetch', mockFetch);

    const collector = new SigilCollector({
      apiKey: 'pk_live_test',
      serverUrl: 'https://fp.example.com',
    });

    const result = await collector.identify();

    expect(mockFetch).toHaveBeenCalledOnce();
    const [url, options] = mockFetch.mock.calls[0];
    expect(url).toBe('https://fp.example.com/identify');
    expect(options.method).toBe('POST');
    expect(options.headers['Authorization']).toBe('Bearer pk_live_test');

    const body = JSON.parse(options.body);
    expect(body.signals).toBeDefined();
    expect(body.signals.canvas).toBe('abc123canvas');

    expect(result.visitorId).toBe('vis_test123');
    expect(result.isNewVisitor).toBe(true);
    expect(result.serverReachable).toBe(true);
  });
});
