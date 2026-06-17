import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { App } from './App';

const { identifyMock, collectSignalsMock, collectorConstructorMock } = vi.hoisted(() => {
  const identify = vi.fn();
  const collectSignals = vi.fn();
  const collectorConstructor = vi.fn(function Collector() {
    return {
      identify,
      collectSignals,
    };
  });
  return {
    identifyMock: identify,
    collectSignalsMock: collectSignals,
    collectorConstructorMock: collectorConstructor,
  };
});

vi.mock('@sigil/collector', () => ({
  SigilCollector: collectorConstructorMock,
}));

describe('Playground settings persistence', () => {
  const fifteenSignals = {
    canvas: 'canvas-hash',
    webglRenderer: 'renderer',
    webglVendor: 'vendor',
    audioHash: 'audio-hash',
    fonts: 'fonts-hash',
    screenResolution: '1920x1080',
    colorDepth: 24,
    platform: 'Win32',
    hardwareConcurrency: 8,
    deviceMemory: 16,
    touchSupport: false,
    maxTouchPoints: 0,
    timezone: 'UTC',
    userAgent: 'browser-agent',
    language: 'en-US',
  };

  beforeEach(() => {
    localStorage.clear();
    identifyMock.mockReset();
    collectSignalsMock.mockReset();
    collectorConstructorMock.mockClear();
  });

  it('loads defaults and persists server settings', async () => {
    const user = userEvent.setup();
    const { unmount } = render(<App />);

    const serverUrlInput = screen.getByLabelText(/server url/i);
    const keyInput = screen.getByLabelText(/publishable key/i);

    expect(serverUrlInput).toHaveValue('http://localhost:8080');
    expect(keyInput).toHaveValue('');

    await user.clear(serverUrlInput);
    await user.type(serverUrlInput, 'http://localhost:9000');
    await user.type(keyInput, 'pk_test_123');

    unmount();
    render(<App />);

    expect(screen.getByLabelText(/server url/i)).toHaveValue('http://localhost:9000');
    expect(screen.getByLabelText(/publishable key/i)).toHaveValue('pk_test_123');
  });

  it('shows validation feedback when identify is clicked without publishable key', async () => {
    const user = userEvent.setup();
    render(<App />);

    await user.click(screen.getByRole('button', { name: /identify/i }));

    expect(screen.getByText(/publishable key is required/i)).toBeInTheDocument();
    expect(collectorConstructorMock).not.toHaveBeenCalled();
  });

  it('identifies with configured settings and renders success summary with all signals', async () => {
    identifyMock.mockResolvedValueOnce({
      visitorId: 'visitor_123',
      fingerprintId: 'fingerprint_123',
      isNewVisitor: true,
      signalValidation: 'match',
      serverReachable: true,
      similarVisitors: null,
      velocity: null,
      geolocation: null,
      impossibleTravel: null,
      signals: fifteenSignals,
    });

    const user = userEvent.setup();
    render(<App />);

    await user.type(screen.getByLabelText(/publishable key/i), 'pk_live_123');
    await user.click(screen.getByRole('button', { name: /identify/i }));

    expect(collectorConstructorMock).toHaveBeenCalledWith({
      apiKey: 'pk_live_123',
      serverUrl: 'http://localhost:8080',
    });
    expect(identifyMock).toHaveBeenCalledTimes(1);
    expect(screen.getByRole('status', { name: /server status/i })).toHaveAttribute(
      'data-status',
      'connected',
    );
    expect(within(screen.getByRole('status', { name: /server status/i })).getByText(/server reachable/i)).toBeInTheDocument();
    const latestSummary = screen.getByRole('region', { name: /server summary/i });
    expect(within(latestSummary).getByText(/visitor_123/i)).toBeInTheDocument();
    expect(within(latestSummary).getByText(/fingerprint_123/i)).toBeInTheDocument();
    expect(within(latestSummary).getByText(/match/i)).toBeInTheDocument();
    expect(within(latestSummary).getByText(/true/i)).toBeInTheDocument();
    expect(screen.getByRole('table', { name: /signals table/i })).toBeInTheDocument();
    expect(screen.getAllByRole('row')).toHaveLength(16);
  });

  it('shows unreachable banner but still renders signals on degraded result', async () => {
    identifyMock.mockResolvedValueOnce({
      visitorId: null,
      fingerprintId: null,
      isNewVisitor: null,
      signalValidation: null,
      serverReachable: false,
      similarVisitors: null,
      velocity: null,
      geolocation: null,
      impossibleTravel: null,
      signals: fifteenSignals,
    });

    const user = userEvent.setup();
    render(<App />);

    await user.type(screen.getByLabelText(/publishable key/i), 'pk_live_123');
    await user.click(screen.getByRole('button', { name: /identify/i }));

    expect(screen.getByRole('status', { name: /server status/i })).toHaveAttribute(
      'data-status',
      'degraded',
    );
    expect(screen.getByText(/server unreachable/i)).toBeInTheDocument();
    expect(screen.getByRole('table', { name: /signals table/i })).toBeInTheDocument();
    expect(screen.getByText(/canvas-hash/i)).toBeInTheDocument();
  });

  it('renders structured identify response panels for enriched server payload', async () => {
    identifyMock.mockResolvedValueOnce({
      visitorId: 'visitor_999',
      fingerprintId: 'fingerprint_999',
      isNewVisitor: false,
      signalValidation: 'mismatch',
      serverReachable: true,
      similarVisitors: [
        {
          visitorId: 'visitor_123',
          similarityScore: 0.92,
          matchingSignals: ['canvas', 'audioHash'],
          mismatchedSignals: ['platform'],
        },
      ],
      velocity: {
        ip24h: 3,
        ip1h: 2,
      },
      geolocation: {
        ipCountry: 'IN',
        ipRegion: 'Karnataka',
        ipCity: 'Bengaluru',
      },
      impossibleTravel: {
        impossibleTravel: true,
        previousCountry: 'US',
        currentCountry: 'IN',
      },
      accountHistory: {
        accountId: 'acct_77',
        firstSeenAt: '2026-06-10T10:00:00Z',
        lastSeenAt: '2026-06-17T10:00:00Z',
        seenCount: 4,
      },
      signals: fifteenSignals,
    });

    const user = userEvent.setup();
    render(<App />);

    await user.type(screen.getByLabelText(/publishable key/i), 'pk_live_123');
    await user.click(screen.getByRole('button', { name: /identify/i }));

    const similarVisitorsSection = screen.getByRole('region', { name: /similar visitors/i });
    expect(within(similarVisitorsSection).getByRole('heading', { name: /similar visitors/i })).toBeInTheDocument();
    expect(within(similarVisitorsSection).getByText(/similarity score/i)).toBeInTheDocument();
    expect(within(similarVisitorsSection).getByText('0.92')).toBeInTheDocument();
    expect(within(similarVisitorsSection).getByText(/matching signals/i)).toBeInTheDocument();
    expect(within(similarVisitorsSection).getByText(/canvas, audioHash/i)).toBeInTheDocument();
    expect(within(similarVisitorsSection).getByText(/mismatched signals/i)).toBeInTheDocument();
    expect(within(similarVisitorsSection).getByText(/^platform$/i)).toBeInTheDocument();

    const velocitySection = screen.getByRole('region', { name: /velocity/i });
    expect(within(velocitySection).getByRole('heading', { name: /velocity/i })).toBeInTheDocument();
    expect(within(velocitySection).getByText(/ip24h/i)).toBeInTheDocument();
    expect(within(velocitySection).getByText('3')).toBeInTheDocument();
    expect(within(velocitySection).getByText(/ip1h/i)).toBeInTheDocument();
    expect(within(velocitySection).getByText('2')).toBeInTheDocument();

    const geolocationSection = screen.getByRole('region', { name: /geolocation/i });
    expect(within(geolocationSection).getByRole('heading', { name: /geolocation/i })).toBeInTheDocument();
    expect(within(geolocationSection).getByText(/ipCountry/i)).toBeInTheDocument();
    expect(within(geolocationSection).getByText('IN')).toBeInTheDocument();
    expect(within(geolocationSection).getByText(/ipRegion/i)).toBeInTheDocument();
    expect(within(geolocationSection).getByText(/Karnataka/i)).toBeInTheDocument();
    expect(within(geolocationSection).getByText(/ipCity/i)).toBeInTheDocument();
    expect(within(geolocationSection).getByText(/Bengaluru/i)).toBeInTheDocument();

    const impossibleTravelSection = screen.getByRole('region', { name: /impossible travel/i });
    expect(
      within(impossibleTravelSection).getByRole('heading', { name: /impossible travel/i }),
    ).toBeInTheDocument();
    expect(within(impossibleTravelSection).getByText(/previousCountry/i)).toBeInTheDocument();
    expect(within(impossibleTravelSection).getByText('US')).toBeInTheDocument();
    expect(within(impossibleTravelSection).getByText(/currentCountry/i)).toBeInTheDocument();

    const accountHistorySection = screen.getByRole('region', { name: /account history/i });
    expect(
      within(accountHistorySection).getByRole('heading', { name: /account history/i }),
    ).toBeInTheDocument();
    expect(within(accountHistorySection).getByText(/accountId/i)).toBeInTheDocument();
    expect(within(accountHistorySection).getByText(/acct_77/i)).toBeInTheDocument();
    expect(within(accountHistorySection).getByText(/seenCount/i)).toBeInTheDocument();
    expect(within(accountHistorySection).getByText('4')).toBeInTheDocument();
  });

  it('runs signals-only collection, shows yellow banner, and does not call identify', async () => {
    collectSignalsMock.mockResolvedValueOnce(fifteenSignals);

    const user = userEvent.setup();
    render(<App />);

    await user.type(screen.getByLabelText(/publishable key/i), 'pk_live_123');
    await user.click(screen.getByRole('button', { name: /signals only/i }));

    expect(collectSignalsMock).toHaveBeenCalledTimes(1);
    expect(identifyMock).not.toHaveBeenCalled();
    expect(screen.getByRole('status', { name: /server status/i })).toHaveAttribute(
      'data-status',
      'signals-only',
    );
    expect(screen.getByText(/signals-only mode/i)).toBeInTheDocument();
    expect(screen.getByRole('table', { name: /signals table/i })).toBeInTheDocument();
    expect(screen.getAllByRole('row')).toHaveLength(16);
  });

  it('appends a run history entry for each run while latest panel keeps updating', async () => {
    identifyMock
      .mockResolvedValueOnce({
        visitorId: 'visitor_first',
        fingerprintId: 'fingerprint_first',
        isNewVisitor: true,
        signalValidation: 'new',
        serverReachable: true,
        similarVisitors: null,
        velocity: null,
        geolocation: null,
        impossibleTravel: null,
        accountHistory: null,
        signals: fifteenSignals,
      })
      .mockResolvedValueOnce({
        visitorId: 'visitor_second',
        fingerprintId: 'fingerprint_second',
        isNewVisitor: false,
        signalValidation: 'match',
        serverReachable: true,
        similarVisitors: null,
        velocity: null,
        geolocation: null,
        impossibleTravel: null,
        accountHistory: null,
        signals: fifteenSignals,
      });

    const user = userEvent.setup();
    render(<App />);

    await user.type(screen.getByLabelText(/publishable key/i), 'pk_live_123');
    await user.click(screen.getByRole('button', { name: /identify/i }));
    await user.click(screen.getByRole('button', { name: /identify/i }));

    const latestSummary = screen.getByRole('region', { name: /server summary/i });
    expect(within(latestSummary).getByText(/visitor_second/i)).toBeInTheDocument();

    const historySection = screen.getByRole('region', { name: /run history/i });
    expect(within(historySection).getAllByRole('article')).toHaveLength(2);
    expect(within(historySection).getByText(/visitor_first/i)).toBeInTheDocument();
    expect(within(historySection).getByText(/visitor_second/i)).toBeInTheDocument();
  });

  it('orders run history newest first across identify and signals-only runs', async () => {
    identifyMock.mockResolvedValueOnce({
      visitorId: 'visitor_identify',
      fingerprintId: 'fingerprint_identify',
      isNewVisitor: true,
      signalValidation: 'new',
      serverReachable: true,
      similarVisitors: null,
      velocity: null,
      geolocation: null,
      impossibleTravel: null,
      accountHistory: null,
      signals: fifteenSignals,
    });
    collectSignalsMock.mockResolvedValueOnce(fifteenSignals);

    const user = userEvent.setup();
    render(<App />);

    await user.type(screen.getByLabelText(/publishable key/i), 'pk_live_123');
    await user.click(screen.getByRole('button', { name: /identify/i }));
    await user.click(screen.getByRole('button', { name: /signals only/i }));

    const historySection = screen.getByRole('region', { name: /run history/i });
    const entries = within(historySection).getAllByRole('article');

    expect(entries).toHaveLength(2);
    expect(within(entries[0]).getByText(/run type: signals-only/i)).toBeInTheDocument();
    expect(within(entries[1]).getByText(/run type: connected/i)).toBeInTheDocument();
    expect(within(entries[1]).getByText(/visitor_identify/i)).toBeInTheDocument();
  });

  it('expands and collapses details for a past run entry', async () => {
    const firstSignals = {
      ...fifteenSignals,
      canvas: 'canvas-old',
    };
    const secondSignals = {
      ...fifteenSignals,
      canvas: 'canvas-new',
    };

    identifyMock
      .mockResolvedValueOnce({
        visitorId: 'visitor_old',
        fingerprintId: 'fingerprint_old',
        isNewVisitor: true,
        signalValidation: 'new',
        serverReachable: true,
        similarVisitors: null,
        velocity: null,
        geolocation: null,
        impossibleTravel: null,
        accountHistory: null,
        signals: firstSignals,
      })
      .mockResolvedValueOnce({
        visitorId: 'visitor_new',
        fingerprintId: 'fingerprint_new',
        isNewVisitor: false,
        signalValidation: 'match',
        serverReachable: true,
        similarVisitors: null,
        velocity: null,
        geolocation: null,
        impossibleTravel: null,
        accountHistory: null,
        signals: secondSignals,
      });

    const user = userEvent.setup();
    render(<App />);

    await user.type(screen.getByLabelText(/publishable key/i), 'pk_live_123');
    await user.click(screen.getByRole('button', { name: /identify/i }));
    await user.click(screen.getByRole('button', { name: /identify/i }));

    const historySection = screen.getByRole('region', { name: /run history/i });
    const entries = within(historySection).getAllByRole('article');
    const pastEntry = entries[1];

    expect(within(pastEntry).queryByText(/canvas-old/i)).not.toBeInTheDocument();
    expect(within(pastEntry).queryByText(/visitor_old/i)).toBeInTheDocument();

    await user.click(within(pastEntry).getByRole('button', { name: /show details/i }));
    expect(within(pastEntry).getAllByText(/canvas-old/i).length).toBeGreaterThan(0);
    expect(within(pastEntry).getAllByText(/visitor_old/i).length).toBeGreaterThan(0);

    await user.click(within(pastEntry).getByRole('button', { name: /hide details/i }));
    expect(within(pastEntry).queryByText(/canvas-old/i)).not.toBeInTheDocument();
  });

  it('persists visitor id after connected identify and re-sends it on next identify', async () => {
    identifyMock
      .mockResolvedValueOnce({
        visitorId: 'visitor_saved',
        fingerprintId: 'fingerprint_1',
        isNewVisitor: true,
        signalValidation: 'new',
        serverReachable: true,
        similarVisitors: null,
        velocity: null,
        geolocation: null,
        impossibleTravel: null,
        signals: fifteenSignals,
      })
      .mockResolvedValueOnce({
        visitorId: 'visitor_saved',
        fingerprintId: 'fingerprint_2',
        isNewVisitor: false,
        signalValidation: 'match',
        serverReachable: true,
        similarVisitors: null,
        velocity: null,
        geolocation: null,
        impossibleTravel: null,
        signals: fifteenSignals,
      });

    const user = userEvent.setup();
    const { unmount } = render(<App />);

    await user.type(screen.getByLabelText(/publishable key/i), 'pk_live_123');
    await user.click(screen.getByRole('button', { name: /identify/i }));

    unmount();
    render(<App />);
    await user.click(screen.getByRole('button', { name: /identify/i }));

    expect(identifyMock).toHaveBeenNthCalledWith(1);
    expect(identifyMock).toHaveBeenNthCalledWith(2, { visitorId: 'visitor_saved' });
  });

  it('resets stored visitor id so next identify is first-visit style', async () => {
    identifyMock.mockResolvedValue({
      visitorId: 'visitor_saved',
      fingerprintId: 'fingerprint_1',
      isNewVisitor: true,
      signalValidation: 'new',
      serverReachable: true,
      similarVisitors: null,
      velocity: null,
      geolocation: null,
      impossibleTravel: null,
      signals: fifteenSignals,
    });

    const user = userEvent.setup();
    const { unmount } = render(<App />);

    await user.type(screen.getByLabelText(/publishable key/i), 'pk_live_123');
    await user.click(screen.getByRole('button', { name: /identify/i }));

    unmount();
    render(<App />);
    await user.click(screen.getByRole('button', { name: /reset visitor/i }));
    await user.click(screen.getByRole('button', { name: /identify/i }));

    expect(identifyMock).toHaveBeenNthCalledWith(1);
    expect(identifyMock).toHaveBeenNthCalledWith(2);
  });

  it('passes account id to identify when provided and does not persist it across reload', async () => {
    identifyMock.mockResolvedValue({
      visitorId: null,
      fingerprintId: null,
      isNewVisitor: null,
      signalValidation: null,
      serverReachable: false,
      similarVisitors: null,
      velocity: null,
      geolocation: null,
      impossibleTravel: null,
      signals: fifteenSignals,
    });

    const user = userEvent.setup();
    const { unmount } = render(<App />);

    await user.type(screen.getByLabelText(/publishable key/i), 'pk_live_123');
    await user.type(screen.getByLabelText(/account id/i), 'acct_123');
    await user.click(screen.getByRole('button', { name: /identify/i }));

    expect(identifyMock).toHaveBeenNthCalledWith(1, { accountId: 'acct_123' });

    unmount();
    render(<App />);

    expect(screen.getByLabelText(/account id/i)).toHaveValue('');
    await user.click(screen.getByRole('button', { name: /identify/i }));
    expect(identifyMock).toHaveBeenNthCalledWith(2);
  });
});
