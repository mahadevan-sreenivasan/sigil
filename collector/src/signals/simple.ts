export function collectScreenResolution(): string | null {
  try {
    if (typeof screen === 'undefined' || !screen) return null;
    return `${screen.width}x${screen.height}`;
  } catch {
    return null;
  }
}

export function collectColorDepth(): number | null {
  try {
    if (typeof screen === 'undefined' || !screen) return null;
    return screen.colorDepth ?? null;
  } catch {
    return null;
  }
}

export function collectPlatform(): string | null {
  try {
    const platform = navigator?.platform;
    return platform || null;
  } catch {
    return null;
  }
}

export function collectHardwareConcurrency(): number | null {
  try {
    const cores = (navigator as Record<string, unknown>)?.hardwareConcurrency;
    return typeof cores === 'number' ? cores : null;
  } catch {
    return null;
  }
}

export function collectDeviceMemory(): number | null {
  try {
    const mem = (navigator as Record<string, unknown>)?.deviceMemory;
    return typeof mem === 'number' ? mem : null;
  } catch {
    return null;
  }
}

export function collectTouchSupport(): boolean {
  try {
    return (navigator?.maxTouchPoints ?? 0) > 0;
  } catch {
    return false;
  }
}

export function collectMaxTouchPoints(): number | null {
  try {
    const tp = (navigator as Record<string, unknown>)?.maxTouchPoints;
    return typeof tp === 'number' ? tp : null;
  } catch {
    return null;
  }
}

export function collectTimezone(): string | null {
  try {
    if (typeof Intl === 'undefined' || !Intl) return null;
    return new Intl.DateTimeFormat().resolvedOptions().timeZone ?? null;
  } catch {
    return null;
  }
}

export function collectUserAgent(): string | null {
  try {
    const ua = navigator?.userAgent;
    return ua || null;
  } catch {
    return null;
  }
}
