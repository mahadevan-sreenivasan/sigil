import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { VisitorDetail } from './VisitorDetail';

const MOCK_VISITOR = {
  visitorId: 'vis_abc123',
  firstSeenAt: '2025-01-15 10:30:00',
  lastSeenAt: '2025-06-10 14:20:00',
  accountBindings: [
    {
      accountId: 'acct_1',
      status: 'verified',
      firstSeenAt: '2025-01-15 10:30:00',
      lastSeenAt: '2025-06-10 14:20:00',
    },
    {
      accountId: 'acct_2',
      status: 'observed',
      firstSeenAt: '2025-03-01 08:00:00',
      lastSeenAt: '2025-03-01 08:00:00',
    },
  ],
  recentSignalSets: [
    {
      capturedAt: '2025-06-10 14:20:00',
      signals: { canvas: 'canvas_a', platform: 'Win32' },
      geolocation: { country: 'US', city: 'New York', latitude: 40.7, longitude: -74.0 },
    },
  ],
};

function renderVisitorDetail() {
  globalThis.fetch = vi.fn(async () =>
    new Response(JSON.stringify(MOCK_VISITOR), { status: 200 }),
  );
  sessionStorage.setItem('sigil_secret_key', 'sk_test');

  return render(
    <MemoryRouter initialEntries={['/visitor/vis_abc123']}>
      <Routes>
        <Route path="/visitor/:id" element={<VisitorDetail />} />
      </Routes>
    </MemoryRouter>,
  );
}

describe('VisitorDetail', () => {
  beforeEach(() => sessionStorage.clear());

  it('displays visitor ID and timestamps', async () => {
    renderVisitorDetail();
    await waitFor(() => {
      expect(screen.getByText('vis_abc123')).toBeInTheDocument();
    });
    const metaGrid = document.querySelector('.meta-grid')!;
    expect(metaGrid.textContent).toContain('2025-01-15');
    expect(metaGrid.textContent).toContain('2025-06-10');
  });

  it('renders account bindings with status badges', async () => {
    renderVisitorDetail();
    await waitFor(() => {
      expect(screen.getByText('acct_1')).toBeInTheDocument();
    });
    expect(screen.getByText('acct_2')).toBeInTheDocument();

    const badges = screen.getAllByText(/verified|observed/i);
    const texts = badges.map((b) => b.textContent!.toLowerCase());
    expect(texts).toContain('verified');
    expect(texts).toContain('observed');
  });

  it('renders signal sets with geolocation', async () => {
    renderVisitorDetail();
    await waitFor(() => {
      expect(screen.getByText('canvas_a')).toBeInTheDocument();
    });
    expect(screen.getByText(/New York/)).toBeInTheDocument();
  });
});
