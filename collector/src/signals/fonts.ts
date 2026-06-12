const TEST_FONTS = [
  'Arial', 'Courier New', 'Georgia', 'Times New Roman', 'Verdana',
  'Trebuchet MS', 'Palatino Linotype', 'Lucida Console', 'Comic Sans MS',
  'Impact', 'Tahoma', 'Helvetica', 'Garamond', 'Bookman Old Style',
  'Lucida Sans Unicode', 'Century Gothic', 'MS Serif', 'MS Sans Serif',
  'Segoe UI', 'Calibri',
];

const BASE_FONTS = ['monospace', 'sans-serif', 'serif'] as const;
const TEST_STRING = 'mmmmmmmmmmlli';
const TEST_SIZE = '72px';

export async function collectFontHash(): Promise<string | null> {
  try {
    const canvas = document.createElement('canvas');
    const ctx = canvas.getContext('2d');
    if (!ctx) return null;

    const baseWidths: Record<string, number> = {};
    for (const base of BASE_FONTS) {
      ctx.font = `${TEST_SIZE} ${base}`;
      baseWidths[base] = ctx.measureText(TEST_STRING).width;
    }

    const detected: string[] = [];
    for (const font of TEST_FONTS) {
      for (const base of BASE_FONTS) {
        ctx.font = `${TEST_SIZE} '${font}', ${base}`;
        const width = ctx.measureText(TEST_STRING).width;
        if (width !== baseWidths[base]) {
          detected.push(font);
          break;
        }
      }
    }

    const fingerprint = detected.sort().join(',');
    const msgBuffer = new TextEncoder().encode(fingerprint);
    const hashBuffer = await crypto.subtle.digest('SHA-256', msgBuffer);
    const hashArray = Array.from(new Uint8Array(hashBuffer));
    return hashArray.map((b) => b.toString(16).padStart(2, '0')).join('');
  } catch {
    return null;
  }
}
