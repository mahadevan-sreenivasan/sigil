import { describe, it, expect, vi, beforeEach } from 'vitest';
import { SigilCollector } from '../src/collector';

vi.mock('../src/signals/canvas', () => ({
  collectCanvasHash: vi.fn().mockResolvedValue('abc123canvas'),
}));

vi.mock('../src/signals/webgl', () => ({
  collectWebGL: vi.fn().mockReturnValue({
    renderer: 'ANGLE (NVIDIA GeForce GTX 1080)',
    vendor: 'Google Inc. (NVIDIA)',
  }),
}));

vi.mock('../src/signals/audio', () => ({
  collectAudioHash: vi.fn().mockResolvedValue('audio_hash_abc'),
}));

vi.mock('../src/signals/fonts', () => ({
  collectFontHash: vi.fn().mockResolvedValue('font_hash_def'),
}));

vi.mock('../src/signals/simple', () => ({
  collectScreenResolution: vi.fn().mockReturnValue('1920x1080'),
  collectColorDepth: vi.fn().mockReturnValue(24),
  collectPlatform: vi.fn().mockReturnValue('Win32'),
  collectHardwareConcurrency: vi.fn().mockReturnValue(8),
  collectDeviceMemory: vi.fn().mockReturnValue(16),
  collectTouchSupport: vi.fn().mockReturnValue(false),
  collectMaxTouchPoints: vi.fn().mockReturnValue(0),
  collectTimezone: vi.fn().mockReturnValue('Asia/Kolkata'),
  collectUserAgent: vi.fn().mockReturnValue('Mozilla/5.0 Test'),
}));

describe('SigilCollector.identify', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('POSTs all 13 signals to serverUrl and returns identification result', async () => {
    const serverResponse = {
      visitorId: 'vis_test123',
      isNewVisitor: true,
      fingerprintId: 'fp_abc123',
      signalValidation: 'new',
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
    expect(body.signals.webglRenderer).toBe('ANGLE (NVIDIA GeForce GTX 1080)');
    expect(body.signals.webglVendor).toBe('Google Inc. (NVIDIA)');
    expect(body.signals.audioHash).toBe('audio_hash_abc');
    expect(body.signals.fonts).toBe('font_hash_def');
    expect(body.signals.screenResolution).toBe('1920x1080');
    expect(body.signals.colorDepth).toBe(24);
    expect(body.signals.platform).toBe('Win32');
    expect(body.signals.hardwareConcurrency).toBe(8);
    expect(body.signals.deviceMemory).toBe(16);
    expect(body.signals.touchSupport).toBe(false);
    expect(body.signals.maxTouchPoints).toBe(0);
    expect(body.signals.timezone).toBe('Asia/Kolkata');
    expect(body.signals.userAgent).toBe('Mozilla/5.0 Test');

    expect(result.visitorId).toBe('vis_test123');
    expect(result.isNewVisitor).toBe(true);
    expect(result.fingerprintId).toBe('fp_abc123');
    expect(result.signalValidation).toBe('new');
    expect(result.serverReachable).toBe(true);
  });

  it('parses accountHistory from identify response', async () => {
    const serverResponse = {
      visitorId: 'vis_history_1',
      isNewVisitor: false,
      fingerprintId: 'fp_history_1',
      signalValidation: 'match',
      accountHistory: {
        accountId: 'acct_42',
        firstSeenAt: '2026-06-10T10:00:00Z',
        lastSeenAt: '2026-06-17T11:30:00Z',
        seenCount: 8,
      },
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

    expect(result.accountHistory).toEqual({
      accountId: 'acct_42',
      firstSeenAt: '2026-06-10T10:00:00Z',
      lastSeenAt: '2026-06-17T11:30:00Z',
      seenCount: 8,
    });
  });

  it('includes accountId in request body when provided', async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () =>
        Promise.resolve({
          visitorId: 'vis_acct_test',
          isNewVisitor: false,
          fingerprintId: 'fp_xyz',
          signalValidation: 'match',
          serverReachable: true,
        }),
    });
    vi.stubGlobal('fetch', mockFetch);

    const collector = new SigilCollector({
      apiKey: 'pk_live_test',
      serverUrl: 'https://fp.example.com',
    });

    await collector.identify({ accountId: 'cust_12345' });

    const body = JSON.parse(mockFetch.mock.calls[0][1].body);
    expect(body.accountId).toBe('cust_12345');
  });

  it('omits accountId from request body when not provided', async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () =>
        Promise.resolve({
          visitorId: 'vis_no_acct',
          isNewVisitor: true,
          fingerprintId: 'fp_abc',
          signalValidation: 'new',
          serverReachable: true,
        }),
    });
    vi.stubGlobal('fetch', mockFetch);

    const collector = new SigilCollector({
      apiKey: 'pk_live_test',
      serverUrl: 'https://fp.example.com',
    });

    await collector.identify();

    const body = JSON.parse(mockFetch.mock.calls[0][1].body);
    expect(body.accountId).toBeUndefined();
  });

  it('includes visitorId from localStorage when provided', async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () =>
        Promise.resolve({
          visitorId: 'vis_existing',
          isNewVisitor: false,
          fingerprintId: 'fp_xyz',
          signalValidation: 'match',
          serverReachable: true,
        }),
    });
    vi.stubGlobal('fetch', mockFetch);

    const collector = new SigilCollector({
      apiKey: 'pk_live_test',
      serverUrl: 'https://fp.example.com',
    });

    const result = await collector.identify({ visitorId: 'vis_existing' });

    const body = JSON.parse(mockFetch.mock.calls[0][1].body);
    expect(body.visitorId).toBe('vis_existing');
    expect(result.signalValidation).toBe('match');
  });

  it('returns degraded result on network error', async () => {
    const mockFetch = vi.fn().mockRejectedValue(new TypeError('fetch failed'));
    vi.stubGlobal('fetch', mockFetch);

    const collector = new SigilCollector({
      apiKey: 'pk_live_test',
      serverUrl: 'https://fp.example.com',
    });

    const result = await collector.identify();

    expect(result.serverReachable).toBe(false);
    expect(result.visitorId).toBeNull();
    expect(result.fingerprintId).toBeNull();
    expect(result.similarVisitors).toBeNull();
    expect(result.velocity).toBeNull();
    expect(result.geolocation).toBeNull();
    expect(result.impossibleTravel).toBeNull();
    expect(result.signals).toBeDefined();
    expect(result.signals!.canvas).toBe('abc123canvas');
  });

  it('returns degraded result on timeout', async () => {
    const mockFetch = vi.fn().mockImplementation(
      (_url: string, opts: { signal: AbortSignal }) =>
        new Promise((_resolve, reject) => {
          opts.signal.addEventListener('abort', () =>
            reject(new DOMException('The operation was aborted', 'AbortError')),
          );
        }),
    );
    vi.stubGlobal('fetch', mockFetch);

    const collector = new SigilCollector({
      apiKey: 'pk_live_test',
      serverUrl: 'https://fp.example.com',
      timeout: 50,
    });

    const result = await collector.identify();

    expect(result.serverReachable).toBe(false);
    expect(result.visitorId).toBeNull();
    expect(result.signals).toBeDefined();
  });

  it('returns degraded result on non-2xx response', async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 500,
      json: () => Promise.resolve({ detail: 'Internal Server Error' }),
    });
    vi.stubGlobal('fetch', mockFetch);

    const collector = new SigilCollector({
      apiKey: 'pk_live_test',
      serverUrl: 'https://fp.example.com',
    });

    const result = await collector.identify();

    expect(result.serverReachable).toBe(false);
    expect(result.visitorId).toBeNull();
    expect(result.velocity).toBeNull();
    expect(result.signals).toBeDefined();
    expect(result.signals!.audioHash).toBe('audio_hash_abc');
  });

  it('degraded result includes all locally-computed signals', async () => {
    const mockFetch = vi.fn().mockRejectedValue(new Error('connection refused'));
    vi.stubGlobal('fetch', mockFetch);

    const collector = new SigilCollector({
      apiKey: 'pk_live_test',
      serverUrl: 'https://fp.example.com',
    });

    const result = await collector.identify({ accountId: 'acct_999' });
    const s = result.signals!;

    expect(s.canvas).toBe('abc123canvas');
    expect(s.webglRenderer).toBe('ANGLE (NVIDIA GeForce GTX 1080)');
    expect(s.webglVendor).toBe('Google Inc. (NVIDIA)');
    expect(s.audioHash).toBe('audio_hash_abc');
    expect(s.fonts).toBe('font_hash_def');
    expect(s.screenResolution).toBe('1920x1080');
    expect(s.colorDepth).toBe(24);
    expect(s.platform).toBe('Win32');
    expect(s.hardwareConcurrency).toBe(8);
    expect(s.deviceMemory).toBe(16);
    expect(s.touchSupport).toBe(false);
    expect(s.maxTouchPoints).toBe(0);
    expect(s.timezone).toBe('Asia/Kolkata');
    expect(s.userAgent).toBe('Mozilla/5.0 Test');

    expect(result.isNewVisitor).toBeNull();
    expect(result.signalValidation).toBeNull();
  });

  it('collectSignals returns local signals without calling fetch', async () => {
    const mockFetch = vi.fn();
    vi.stubGlobal('fetch', mockFetch);

    const collector = new SigilCollector({
      apiKey: 'pk_live_test',
      serverUrl: 'https://fp.example.com',
    });

    const signals = await collector.collectSignals();

    expect(mockFetch).not.toHaveBeenCalled();
    expect(signals.canvas).toBe('abc123canvas');
    expect(signals.webglRenderer).toBe('ANGLE (NVIDIA GeForce GTX 1080)');
    expect(signals.webglVendor).toBe('Google Inc. (NVIDIA)');
    expect(signals.audioHash).toBe('audio_hash_abc');
    expect(signals.fonts).toBe('font_hash_def');
    expect(signals.screenResolution).toBe('1920x1080');
    expect(signals.colorDepth).toBe(24);
    expect(signals.platform).toBe('Win32');
    expect(signals.hardwareConcurrency).toBe(8);
    expect(signals.deviceMemory).toBe(16);
    expect(signals.touchSupport).toBe(false);
    expect(signals.maxTouchPoints).toBe(0);
    expect(signals.timezone).toBe('Asia/Kolkata');
    expect(signals.userAgent).toBe('Mozilla/5.0 Test');
  });
});
