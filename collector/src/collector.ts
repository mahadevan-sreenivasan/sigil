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
  similarVisitors: unknown[] | null;
  velocity: Record<string, unknown> | null;
  geolocation: Record<string, unknown> | null;
  impossibleTravel: Record<string, unknown> | null;
  accountHistory: Record<string, unknown> | null;
  signals: Record<string, unknown> | null;
}

export type CollectedSignals = Record<string, unknown>;

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

  async collectSignals(): Promise<CollectedSignals> {
    return this._collectSignals();
  }

  async identify(options?: IdentifyOptions): Promise<IdentificationResult> {
    const signals = await this.collectSignals();
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

      if (!response.ok) {
        return this._degradedResult(signals);
      }

      const data = await response.json();
      return {
        visitorId: data.visitorId ?? null,
        fingerprintId: data.fingerprintId ?? null,
        isNewVisitor: data.isNewVisitor ?? null,
        signalValidation: data.signalValidation ?? null,
        serverReachable: true,
        similarVisitors: data.similarVisitors ?? null,
        velocity: data.velocity ?? null,
        geolocation: data.geolocation ?? null,
        impossibleTravel: data.impossibleTravel ?? null,
        accountHistory: data.accountHistory ?? null,
        signals,
      };
    } catch {
      return this._degradedResult(signals);
    } finally {
      clearTimeout(timer);
    }
  }

  private async _collectSignals(): Promise<CollectedSignals> {
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

    return signals;
  }

  private _degradedResult(signals: CollectedSignals): IdentificationResult {
    return {
      visitorId: null,
      fingerprintId: null,
      isNewVisitor: null,
      signalValidation: null,
      serverReachable: false,
      similarVisitors: null,
      velocity: null,
      geolocation: null,
      impossibleTravel: null,
      accountHistory: null,
      signals,
    };
  }
}
