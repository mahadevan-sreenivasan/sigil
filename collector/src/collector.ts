import { collectCanvasHash } from './signals/canvas';
import { collectWebGL } from './signals/webgl';
import { collectAudioHash } from './signals/audio';
import { collectFontHash } from './signals/fonts';
import {
  collectScreenResolution,
  collectColorDepth,
  collectPlatform,
  collectHardwareConcurrency,
  collectDeviceMemory,
  collectTouchSupport,
  collectMaxTouchPoints,
  collectTimezone,
  collectUserAgent,
} from './signals/simple';

export interface SigilCollectorOptions {
  apiKey: string;
  serverUrl: string;
  timeout?: number;
}

export interface IdentifyOptions {
  accountId?: string;
  visitorId?: string;
}

export interface IdentificationResult {
  visitorId: string | null;
  fingerprintId: string | null;
  isNewVisitor: boolean | null;
  signalValidation: 'new' | 'match' | 'mismatch' | null;
  serverReachable: boolean;
}

const DEFAULT_TIMEOUT = 5000;

export class SigilCollector {
  private apiKey: string;
  private serverUrl: string;
  private timeout: number;

  constructor(options: SigilCollectorOptions) {
    this.apiKey = options.apiKey;
    this.serverUrl = options.serverUrl.replace(/\/$/, '');
    this.timeout = options.timeout ?? DEFAULT_TIMEOUT;
  }

  async identify(options?: IdentifyOptions): Promise<IdentificationResult> {
    const [canvas, webgl, audioHash, fonts] = await Promise.all([
      collectCanvasHash(),
      Promise.resolve(collectWebGL()),
      collectAudioHash(),
      collectFontHash(),
    ]);

    const signals: Record<string, unknown> = {
      canvas,
      webglRenderer: webgl?.renderer ?? null,
      webglVendor: webgl?.vendor ?? null,
      audioHash,
      fonts,
      screenResolution: collectScreenResolution(),
      colorDepth: collectColorDepth(),
      platform: collectPlatform(),
      hardwareConcurrency: collectHardwareConcurrency(),
      deviceMemory: collectDeviceMemory(),
      touchSupport: collectTouchSupport(),
      maxTouchPoints: collectMaxTouchPoints(),
      timezone: collectTimezone(),
      userAgent: collectUserAgent(),
    };

    const body: Record<string, unknown> = { signals };
    if (options?.visitorId) {
      body.visitorId = options.visitorId;
    }
    if (options?.accountId) {
      body.accountId = options.accountId;
    }

    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), this.timeout);

    try {
      const response = await fetch(`${this.serverUrl}/identify`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${this.apiKey}`,
        },
        body: JSON.stringify(body),
        signal: controller.signal,
      });

      const data = await response.json();
      return {
        visitorId: data.visitorId ?? null,
        fingerprintId: data.fingerprintId ?? null,
        isNewVisitor: data.isNewVisitor ?? null,
        signalValidation: data.signalValidation ?? null,
        serverReachable: true,
      };
    } finally {
      clearTimeout(timer);
    }
  }
}
