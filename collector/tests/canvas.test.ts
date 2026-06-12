import { describe, it, expect, vi } from 'vitest';
import { collectCanvasHash } from '../src/signals/canvas';

describe('collectCanvasHash', () => {
  it('returns a 64-char hex hash from canvas rendering', async () => {
    const ctx = {
      fillRect: vi.fn(),
      fillText: vi.fn(),
      beginPath: vi.fn(),
      arc: vi.fn(),
      fill: vi.fn(),
      closePath: vi.fn(),
      font: '',
      textBaseline: '',
      fillStyle: '',
    };

    const canvas = {
      getContext: vi.fn().mockReturnValue(ctx),
      toDataURL: vi.fn().mockReturnValue('data:image/png;base64,stablecanvasdata'),
      width: 0,
      height: 0,
    };

    vi.spyOn(document, 'createElement').mockReturnValue(
      canvas as unknown as HTMLCanvasElement,
    );

    const hash = await collectCanvasHash();

    expect(hash).toBeTypeOf('string');
    expect(hash).toMatch(/^[a-f0-9]{64}$/);
  });
});
