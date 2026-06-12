import { describe, it, expect, vi } from 'vitest';
import { collectFontHash } from '../src/signals/fonts';

describe('collectFontHash', () => {
  it('returns a hex hash based on measured font widths', async () => {
    let callCount = 0;
    const baseFonts = ['monospace', 'sans-serif', 'serif'];
    const testFonts = [
      'Arial', 'Courier New', 'Georgia', 'Times New Roman', 'Verdana',
      'Trebuchet MS', 'Palatino Linotype', 'Lucida Console', 'Comic Sans MS',
      'Impact',
    ];

    const ctx = {
      font: '',
      measureText: vi.fn().mockImplementation(() => {
        callCount++;
        const baseWidth = 100;
        const fontStr = ctx.font;
        const isTestFont = testFonts.some((f) => fontStr.includes(f));
        if (isTestFont && fontStr.includes('Arial')) {
          return { width: baseWidth + 5 };
        }
        return { width: baseWidth };
      }),
    };

    const canvas = {
      getContext: vi.fn().mockReturnValue(ctx),
      width: 0,
      height: 0,
    };
    vi.spyOn(document, 'createElement').mockReturnValue(
      canvas as unknown as HTMLCanvasElement,
    );

    const hash = await collectFontHash();

    expect(hash).toBeTypeOf('string');
    expect(hash).toMatch(/^[a-f0-9]{64}$/);
  });

  it('returns null when canvas 2d context is unavailable', async () => {
    const canvas = {
      getContext: vi.fn().mockReturnValue(null),
      width: 0,
      height: 0,
    };
    vi.spyOn(document, 'createElement').mockReturnValue(
      canvas as unknown as HTMLCanvasElement,
    );

    const hash = await collectFontHash();
    expect(hash).toBeNull();
  });
});
