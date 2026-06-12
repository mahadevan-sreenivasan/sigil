import { collectCanvasHash } from './signals/canvas';

export interface SigilCollectorOptions {
  apiKey: string;
  serverUrl: string;
  timeout?: number;
}

export interface IdentifyOptions {
  accountId?: string;
}

export interface IdentificationResult {
  visitorId: string | null;
  isNewVisitor: boolean | null;
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
    const canvas = await collectCanvasHash();
    const signals = { canvas };

    const body: Record<string, unknown> = { signals };
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
        isNewVisitor: data.isNewVisitor ?? null,
        serverReachable: true,
      };
    } finally {
      clearTimeout(timer);
    }
  }
}
