export interface WebGLInfo {
  renderer: string;
  vendor: string;
}

export function collectWebGL(): WebGLInfo | null {
  try {
    const canvas = document.createElement('canvas');
    const gl = canvas.getContext('webgl') as WebGLRenderingContext | null;
    if (!gl) return null;

    const ext = gl.getExtension('WEBGL_debug_renderer_info');
    if (!ext) return null;

    const renderer = gl.getParameter(ext.UNMASKED_RENDERER_WEBGL);
    const vendor = gl.getParameter(ext.UNMASKED_VENDOR_WEBGL);

    if (typeof renderer !== 'string' || typeof vendor !== 'string') return null;

    return { renderer, vendor };
  } catch {
    return null;
  }
}
