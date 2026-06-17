import { useEffect, useState } from 'react';
import { SigilCollector, type IdentificationResult, type IdentifyOptions } from '@sigil/collector';

const STORAGE_KEYS = {
  serverUrl: 'sigil_playground_server_url',
  publishableKey: 'sigil_playground_publishable_key',
  visitorId: 'sigil_playground_visitor_id',
};

const DEFAULT_SERVER_URL = 'http://localhost:8080';

function loadSetting(key: string, fallback: string): string {
  const value = localStorage.getItem(key);
  return value ?? fallback;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null;
}

function toStringList(value: unknown): string[] {
  if (!Array.isArray(value)) {
    return [];
  }
  return value.map((item) => String(item));
}

type StatusMode = 'connected' | 'degraded' | 'signals-only';

type RunHistoryEntry = {
  id: string;
  timestamp: string;
  statusMode: StatusMode;
  result: IdentificationResult;
};

function getStatusMessage(statusMode: StatusMode): string {
  if (statusMode === 'signals-only') {
    return 'Signals-only mode (no server call)';
  }
  if (statusMode === 'connected') {
    return 'Server reachable';
  }
  return 'Server unreachable';
}

function getStatusClassName(statusMode: StatusMode): string {
  if (statusMode === 'signals-only') {
    return 'status-signals-only';
  }
  if (statusMode === 'connected') {
    return 'status-connected';
  }
  return 'status-degraded';
}

function getHistoryStatusMessage(statusMode: StatusMode): string {
  if (statusMode === 'signals-only') {
    return 'Run type: Signals-only';
  }
  if (statusMode === 'connected') {
    return 'Run type: Connected';
  }
  return 'Run type: Degraded';
}

export function App() {
  const [statusMode, setStatusMode] = useState<StatusMode | null>(null);
  const [serverUrl, setServerUrl] = useState<string>(() =>
    loadSetting(STORAGE_KEYS.serverUrl, DEFAULT_SERVER_URL),
  );
  const [publishableKey, setPublishableKey] = useState<string>(() =>
    loadSetting(STORAGE_KEYS.publishableKey, ''),
  );
  const [accountId, setAccountId] = useState<string>('');
  const [validationMessage, setValidationMessage] = useState<string | null>(null);
  const [result, setResult] = useState<IdentificationResult | null>(null);
  const [runHistory, setRunHistory] = useState<RunHistoryEntry[]>([]);
  const [expandedEntryIds, setExpandedEntryIds] = useState<Set<string>>(new Set());

  useEffect(() => {
    localStorage.setItem(STORAGE_KEYS.serverUrl, serverUrl);
  }, [serverUrl]);

  useEffect(() => {
    localStorage.setItem(STORAGE_KEYS.publishableKey, publishableKey);
  }, [publishableKey]);

  async function handleIdentify() {
    if (!publishableKey.trim()) {
      setValidationMessage('Publishable key is required.');
      return;
    }

    setValidationMessage(null);
    const collector = new SigilCollector({
      apiKey: publishableKey,
      serverUrl,
    });
    const storedVisitorId = localStorage.getItem(STORAGE_KEYS.visitorId) ?? undefined;
    const identifyOptions: IdentifyOptions = {};
    const trimmedAccountId = accountId.trim();
    if (storedVisitorId) {
      identifyOptions.visitorId = storedVisitorId;
    }
    if (trimmedAccountId) {
      identifyOptions.accountId = trimmedAccountId;
    }
    const identifyResult =
      Object.keys(identifyOptions).length > 0
        ? await collector.identify(identifyOptions)
        : await collector.identify();
    if (identifyResult.serverReachable && identifyResult.visitorId) {
      localStorage.setItem(STORAGE_KEYS.visitorId, identifyResult.visitorId);
    }
    const nextStatusMode: StatusMode = identifyResult.serverReachable ? 'connected' : 'degraded';
    setStatusMode(nextStatusMode);
    setResult(identifyResult);
    setRunHistory((previous) => [
      {
        id: `${Date.now()}-${previous.length}`,
        timestamp: new Date().toISOString(),
        statusMode: nextStatusMode,
        result: identifyResult,
      },
      ...previous,
    ]);
  }

  async function handleCollectSignals() {
    const collector = new SigilCollector({
      apiKey: publishableKey,
      serverUrl,
    });
    const signals = await collector.collectSignals();

    setValidationMessage(null);
    setStatusMode('signals-only');
    const signalResult: IdentificationResult = {
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
    setResult(signalResult);
    setRunHistory((previous) => [
      {
        id: `${Date.now()}-${previous.length}`,
        timestamp: new Date().toISOString(),
        statusMode: 'signals-only',
        result: signalResult,
      },
      ...previous,
    ]);
  }

  function handleResetVisitor() {
    localStorage.removeItem(STORAGE_KEYS.visitorId);
  }

  function toggleEntry(entryId: string) {
    setExpandedEntryIds((previous) => {
      const next = new Set(previous);
      if (next.has(entryId)) {
        next.delete(entryId);
      } else {
        next.add(entryId);
      }
      return next;
    });
  }

  return (
    <main>
      <h1>Sigil Playground</h1>
      <section aria-label="Settings">
        <div>
          <label htmlFor="serverUrl">Server URL</label>
          <input
            id="serverUrl"
            name="serverUrl"
            value={serverUrl}
            onChange={(event) => setServerUrl(event.target.value)}
          />
        </div>
        <div>
          <label htmlFor="publishableKey">Publishable Key</label>
          <input
            id="publishableKey"
            name="publishableKey"
            value={publishableKey}
            onChange={(event) => setPublishableKey(event.target.value)}
          />
        </div>
        <div>
          <label htmlFor="accountId">Account ID</label>
          <input
            id="accountId"
            name="accountId"
            value={accountId}
            onChange={(event) => setAccountId(event.target.value)}
          />
        </div>
      </section>
      <button type="button" onClick={() => void handleIdentify()}>
        Identify
      </button>
      <button type="button" onClick={() => void handleCollectSignals()}>
        Signals only
      </button>
      <button type="button" onClick={handleResetVisitor}>
        Reset visitor
      </button>
      {validationMessage ? <p role="alert">{validationMessage}</p> : null}

      {result && statusMode ? (
        <>
          <section
            role="status"
            aria-label="Server status"
            data-status={statusMode}
            className={`status-banner ${getStatusClassName(statusMode)}`}
          >
            {getStatusMessage(statusMode)}
          </section>

          <section aria-label="Server summary">
            <h2>Server Summary</h2>
            <dl>
              <dt>Visitor ID</dt>
              <dd>{String(result.visitorId)}</dd>
              <dt>Fingerprint ID</dt>
              <dd>{String(result.fingerprintId)}</dd>
              <dt>Signal Validation</dt>
              <dd>{String(result.signalValidation)}</dd>
              <dt>Is New Visitor</dt>
              <dd>{String(result.isNewVisitor)}</dd>
            </dl>
          </section>

          {Array.isArray(result.similarVisitors) && result.similarVisitors.length > 0 ? (
            <section aria-label="Similar visitors">
              <h2>Similar Visitors</h2>
              {result.similarVisitors.map((visitor, index) => {
                const visitorRecord = isRecord(visitor) ? visitor : {};
                const matchingSignals = toStringList(visitorRecord.matchingSignals);
                const mismatchedSignals = toStringList(visitorRecord.mismatchedSignals);
                return (
                  <article key={`${String(visitorRecord.visitorId ?? 'unknown')}-${index}`}>
                    <dl>
                      <dt>Visitor ID</dt>
                      <dd>{String(visitorRecord.visitorId ?? null)}</dd>
                      <dt>Similarity Score</dt>
                      <dd>{String(visitorRecord.similarityScore ?? null)}</dd>
                      <dt>Matching Signals</dt>
                      <dd>{matchingSignals.length > 0 ? matchingSignals.join(', ') : 'none'}</dd>
                      <dt>Mismatched Signals</dt>
                      <dd>{mismatchedSignals.length > 0 ? mismatchedSignals.join(', ') : 'none'}</dd>
                    </dl>
                  </article>
                );
              })}
            </section>
          ) : null}

          {result.velocity ? (
            <section aria-label="Velocity">
              <h2>Velocity</h2>
              <dl>
                {Object.entries(result.velocity).map(([name, value]) => (
                  <div key={name}>
                    <dt>{name}</dt>
                    <dd>{String(value)}</dd>
                  </div>
                ))}
              </dl>
            </section>
          ) : null}

          {result.geolocation ? (
            <section aria-label="Geolocation">
              <h2>Geolocation</h2>
              <dl>
                {Object.entries(result.geolocation).map(([name, value]) => (
                  <div key={name}>
                    <dt>{name}</dt>
                    <dd>{String(value)}</dd>
                  </div>
                ))}
              </dl>
            </section>
          ) : null}

          {result.impossibleTravel ? (
            <section aria-label="Impossible travel">
              <h2>Impossible Travel</h2>
              <dl>
                {Object.entries(result.impossibleTravel).map(([name, value]) => (
                  <div key={name}>
                    <dt>{name}</dt>
                    <dd>{String(value)}</dd>
                  </div>
                ))}
              </dl>
            </section>
          ) : null}

          {result.accountHistory ? (
            <section aria-label="Account history">
              <h2>Account History</h2>
              <dl>
                {Object.entries(result.accountHistory).map(([name, value]) => (
                  <div key={name}>
                    <dt>{name}</dt>
                    <dd>{String(value)}</dd>
                  </div>
                ))}
              </dl>
            </section>
          ) : null}

          <section aria-label="Signals">
            <h2>Signals</h2>
            <table aria-label="Signals table">
              <thead>
                <tr>
                  <th scope="col">Signal</th>
                  <th scope="col">Value</th>
                </tr>
              </thead>
              <tbody>
                {Object.entries(result.signals ?? {}).map(([name, value]) => (
                  <tr key={name}>
                    <td>{name}</td>
                    <td>{String(value)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>

          <section aria-label="Run history" className="run-history">
            <h2>Run History</h2>
            {runHistory.map((entry) => (
              <article key={entry.id}>
                <p>{entry.timestamp}</p>
                <p className={`status-banner ${getStatusClassName(entry.statusMode)}`}>
                  {getHistoryStatusMessage(entry.statusMode)}
                </p>
                <dl>
                  <dt>Visitor ID</dt>
                  <dd>{String(entry.result.visitorId)}</dd>
                  <dt>Fingerprint ID</dt>
                  <dd>{String(entry.result.fingerprintId)}</dd>
                  <dt>Signal Validation</dt>
                  <dd>{String(entry.result.signalValidation)}</dd>
                  <dt>Server Reachable</dt>
                  <dd>{String(entry.result.serverReachable)}</dd>
                </dl>
                <button type="button" onClick={() => toggleEntry(entry.id)}>
                  {expandedEntryIds.has(entry.id) ? 'Hide details' : 'Show details'}
                </button>
                {expandedEntryIds.has(entry.id) ? (
                  <div>
                    <h3>Signals detail</h3>
                    <pre>{JSON.stringify(entry.result.signals ?? {}, null, 2)}</pre>
                    <h3>Server response detail</h3>
                    <pre>{JSON.stringify(entry.result, null, 2)}</pre>
                  </div>
                ) : null}
              </article>
            ))}
          </section>
        </>
      ) : null}
    </main>
  );
}
