import { render, screen, waitFor, within } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { AccountDetail } from './AccountDetail';

const MOCK_ACCOUNT = {
  accountId: 'acct_100',
  visitors: [
    {
      visitorId: 'vis_aaa',
      bindingStatus: 'verified',
      firstSeenAt: '2025-01-10 09:00:00',
      lastSeenAt: '2025-06-01 12:00:00',
      lastGeolocation: { country: 'US', city: 'Chicago', latitude: 41.8, longitude: -87.6 },
    },
    {
      visitorId: 'vis_bbb',
      bindingStatus: 'observed',
      firstSeenAt: '2025-03-15 14:00:00',
      lastSeenAt: '2025-05-20 08:30:00',
      lastGeolocation: { country: 'GB', city: 'London', latitude: 51.5, longitude: -0.1 },
    },
  ],
};

const MOCK_GEOLOCATIONS = {
  accountId: 'acct_100',
  geolocations: [
    {
      visitorId: 'vis_aaa',
      ip: '203.0.113.1',
      country: 'US',
      city: 'Chicago',
      latitude: 41.8,
      longitude: -87.6,
      capturedAt: '2025-06-01T12:00:00Z',
    },
    {
      visitorId: 'vis_bbb',
      ip: '198.51.100.5',
      country: 'NG',
      city: 'Lagos',
      latitude: 6.5,
      longitude: 3.4,
      capturedAt: '2025-05-20T08:30:00Z',
    },
  ],
};

function renderAccountDetail() {
  globalThis.fetch = vi.fn(async (url: string | URL | Request) => {
    const path = typeof url === 'string' ? url : url.toString();
    if (path.includes('/geolocations')) {
      return new Response(JSON.stringify(MOCK_GEOLOCATIONS), { status: 200 });
    }
    return new Response(JSON.stringify(MOCK_ACCOUNT), { status: 200 });
  });
  sessionStorage.setItem('sigil_secret_key', 'sk_test');

  return render(
    <MemoryRouter initialEntries={['/account/acct_100']}>
      <Routes>
        <Route path="/account/:id" element={<AccountDetail />} />
      </Routes>
    </MemoryRouter>,
  );
}

function getDevicesTable() {
  return document.querySelector('.data-table') as HTMLTableElement;
}

describe('AccountDetail', () => {
  beforeEach(() => sessionStorage.clear());

  it('displays the account ID', async () => {
    renderAccountDetail();
    await waitFor(() => {
      expect(screen.getByText('acct_100')).toBeInTheDocument();
    });
  });

  it('lists visitors with their IDs', async () => {
    renderAccountDetail();
    await waitFor(() => {
      expect(within(getDevicesTable()).getByText('vis_aaa')).toBeInTheDocument();
    });
    expect(within(getDevicesTable()).getByText('vis_bbb')).toBeInTheDocument();
  });

  it('shows verified and observed badges with visual distinction', async () => {
    renderAccountDetail();
    await waitFor(() => {
      expect(within(getDevicesTable()).getByText('vis_aaa')).toBeInTheDocument();
    });

    const table = within(getDevicesTable());
    const verifiedBadge = table.getByText('verified');
    const observedBadge = table.getByText('observed');

    expect(verifiedBadge.className).toContain('badge-verified');
    expect(observedBadge.className).toContain('badge-observed');
  });

  it('shows last geolocation for each device', async () => {
    renderAccountDetail();
    await waitFor(() => {
      expect(within(getDevicesTable()).getByText(/Chicago/)).toBeInTheDocument();
    });
    expect(within(getDevicesTable()).getByText(/London/)).toBeInTheDocument();
  });

  it('renders a geolocation timeline section with entries', async () => {
    renderAccountDetail();
    await waitFor(() => {
      expect(screen.getByText('203.0.113.1')).toBeInTheDocument();
    });
    expect(screen.getByText('198.51.100.5')).toBeInTheDocument();
    expect(document.querySelector('.geo-timeline')).toBeInTheDocument();
  });
});
