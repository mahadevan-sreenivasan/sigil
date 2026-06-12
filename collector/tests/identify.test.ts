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
});
