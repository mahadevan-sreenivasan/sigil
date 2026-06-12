import { describe, it, expect, vi } from 'vitest';
import { collectAudioHash } from '../src/signals/audio';

describe('collectAudioHash', () => {
  it('returns a hex hash from rendered audio buffer', async () => {
    const channelData = new Float32Array([0.1, 0.2, 0.3, 0.4, 0.5]);
    const renderedBuffer = {
      getChannelData: vi.fn().mockReturnValue(channelData),
      length: 5,
    };

    const context = {
      createOscillator: vi.fn().mockReturnValue({
        type: '',
        frequency: { value: 0 },
        connect: vi.fn(),
        start: vi.fn(),
        stop: vi.fn(),
      }),
      createDynamicsCompressor: vi.fn().mockReturnValue({
        threshold: { value: 0 },
        knee: { value: 0 },
        ratio: { value: 0 },
        attack: { value: 0 },
        release: { value: 0 },
        connect: vi.fn(),
      }),
      destination: {},
      startRendering: vi.fn().mockResolvedValue(renderedBuffer),
    };

    vi.stubGlobal(
      'OfflineAudioContext',
      vi.fn().mockImplementation(() => context),
    );

    const hash = await collectAudioHash();

    expect(hash).toBeTypeOf('string');
    expect(hash).toMatch(/^[a-f0-9]{64}$/);
  });

  it('returns null when OfflineAudioContext is not available', async () => {
    vi.stubGlobal('OfflineAudioContext', undefined);

    const hash = await collectAudioHash();
    expect(hash).toBeNull();
  });
});
