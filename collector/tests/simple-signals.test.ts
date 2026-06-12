import { describe, it, expect, vi } from 'vitest';
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
} from '../src/signals/simple';

describe('simple signal collectors', () => {
  describe('collectScreenResolution', () => {
    it('returns WxH string from window.screen', () => {
      vi.stubGlobal('screen', { width: 1920, height: 1080 });
      expect(collectScreenResolution()).toBe('1920x1080');
    });

    it('returns null when screen is unavailable', () => {
      vi.stubGlobal('screen', undefined);
      expect(collectScreenResolution()).toBeNull();
    });
  });

  describe('collectColorDepth', () => {
    it('returns color depth number', () => {
      vi.stubGlobal('screen', { colorDepth: 24 });
      expect(collectColorDepth()).toBe(24);
    });

    it('returns null when screen is unavailable', () => {
      vi.stubGlobal('screen', undefined);
      expect(collectColorDepth()).toBeNull();
    });
  });

  describe('collectPlatform', () => {
    it('returns navigator.platform', () => {
      vi.stubGlobal('navigator', { ...navigator, platform: 'Win32' });
      expect(collectPlatform()).toBe('Win32');
    });

    it('returns null when navigator.platform is empty', () => {
      vi.stubGlobal('navigator', { ...navigator, platform: '' });
      expect(collectPlatform()).toBeNull();
    });
  });

  describe('collectHardwareConcurrency', () => {
    it('returns number of logical processors', () => {
      vi.stubGlobal('navigator', { ...navigator, hardwareConcurrency: 8 });
      expect(collectHardwareConcurrency()).toBe(8);
    });

    it('returns null when hardwareConcurrency is undefined', () => {
      const nav = { ...navigator };
      delete (nav as Record<string, unknown>).hardwareConcurrency;
      vi.stubGlobal('navigator', nav);
      expect(collectHardwareConcurrency()).toBeNull();
    });
  });

  describe('collectDeviceMemory', () => {
    it('returns device memory in GB', () => {
      vi.stubGlobal('navigator', { ...navigator, deviceMemory: 16 });
      expect(collectDeviceMemory()).toBe(16);
    });

    it('returns null when deviceMemory is not available', () => {
      const nav = { ...navigator };
      delete (nav as Record<string, unknown>).deviceMemory;
      vi.stubGlobal('navigator', nav);
      expect(collectDeviceMemory()).toBeNull();
    });
  });

  describe('collectTouchSupport', () => {
    it('returns true when touch is supported', () => {
      vi.stubGlobal('navigator', { ...navigator, maxTouchPoints: 5 });
      expect(collectTouchSupport()).toBe(true);
    });

    it('returns false when no touch support', () => {
      vi.stubGlobal('navigator', { ...navigator, maxTouchPoints: 0 });
      expect(collectTouchSupport()).toBe(false);
    });
  });

  describe('collectMaxTouchPoints', () => {
    it('returns maxTouchPoints value', () => {
      vi.stubGlobal('navigator', { ...navigator, maxTouchPoints: 10 });
      expect(collectMaxTouchPoints()).toBe(10);
    });

    it('returns null when maxTouchPoints is undefined', () => {
      const nav = { ...navigator };
      delete (nav as Record<string, unknown>).maxTouchPoints;
      vi.stubGlobal('navigator', nav);
      expect(collectMaxTouchPoints()).toBeNull();
    });
  });

  describe('collectTimezone', () => {
    it('returns IANA timezone string', () => {
      const mockDateTimeFormat = vi.fn().mockImplementation(() => ({
        resolvedOptions: () => ({ timeZone: 'Asia/Kolkata' }),
      }));
      vi.stubGlobal('Intl', { DateTimeFormat: mockDateTimeFormat });
      expect(collectTimezone()).toBe('Asia/Kolkata');
    });

    it('returns null when Intl is unavailable', () => {
      vi.stubGlobal('Intl', undefined);
      expect(collectTimezone()).toBeNull();
    });
  });

  describe('collectUserAgent', () => {
    it('returns navigator.userAgent', () => {
      vi.stubGlobal('navigator', { ...navigator, userAgent: 'Mozilla/5.0 Test' });
      expect(collectUserAgent()).toBe('Mozilla/5.0 Test');
    });

    it('returns null when userAgent is empty', () => {
      vi.stubGlobal('navigator', { ...navigator, userAgent: '' });
      expect(collectUserAgent()).toBeNull();
    });
  });
});
