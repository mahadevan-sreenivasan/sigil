import { describe, it, expect, vi } from 'vitest';
import { collectWebGL } from '../src/signals/webgl';

describe('collectWebGL', () => {
  it('returns renderer and vendor from WebGL debug info', () => {
    const ext = {
      UNMASKED_RENDERER_WEBGL: 0x9246,
      UNMASKED_VENDOR_WEBGL: 0x9245,
    };
    const gl = {
      getExtension: vi.fn().mockReturnValue(ext),
      getParameter: vi.fn((param: number) => {
        if (param === 0x9246) return 'ANGLE (NVIDIA GeForce GTX 1080)';
        if (param === 0x9245) return 'Google Inc. (NVIDIA)';
        return null;
      }),
    };
    const canvas = {
      getContext: vi.fn().mockReturnValue(gl),
      width: 0,
      height: 0,
    };
    vi.spyOn(document, 'createElement').mockReturnValue(
      canvas as unknown as HTMLCanvasElement,
    );

    const result = collectWebGL();

    expect(result).toEqual({
      renderer: 'ANGLE (NVIDIA GeForce GTX 1080)',
      vendor: 'Google Inc. (NVIDIA)',
    });
  });

  it('returns null when WebGL context is unavailable', () => {
    const canvas = {
      getContext: vi.fn().mockReturnValue(null),
      width: 0,
      height: 0,
    };
    vi.spyOn(document, 'createElement').mockReturnValue(
      canvas as unknown as HTMLCanvasElement,
    );

    const result = collectWebGL();
    expect(result).toBeNull();
  });

  it('returns null when debug extension is unavailable', () => {
    const gl = {
      getExtension: vi.fn().mockReturnValue(null),
      getParameter: vi.fn(),
    };
    const canvas = {
      getContext: vi.fn().mockReturnValue(gl),
      width: 0,
      height: 0,
    };
    vi.spyOn(document, 'createElement').mockReturnValue(
      canvas as unknown as HTMLCanvasElement,
    );

    const result = collectWebGL();
    expect(result).toBeNull();
  });
});
