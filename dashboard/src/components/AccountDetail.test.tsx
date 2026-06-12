import { render, screen, waitFor } from '@testing-library/react';
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

function renderAccountDetail() {
  globalThis.fetch = vi.fn(async () =>
    new Response(JSON.stringify(MOCK_ACCOUNT), { status: 200 }),
  );
  sessionStorage.setItem('sigil_secret_key', 'sk_test');

  return render(
    <MemoryRouter initialEntries={['/account/acct_100']}>
      <Routes>
        <Route path="/account/:id" element={<AccountDetail />} />
      </Routes>
    </MemoryRouter>,
  );
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
      expect(screen.getByText('vis_aaa')).toBeInTheDocument();
    });
    expect(screen.getByText('vis_bbb')).toBeInTheDocument();
  });

  it('shows verified and observed badges with visual distinction', async () => {
    renderAccountDetail();
    await waitFor(() => {
      expect(screen.getByText('vis_aaa')).toBeInTheDocument();
    });

    const verifiedBadge = screen.getByText('verified');
    const observedBadge = screen.getByText('observed');

    expect(verifiedBadge.className).toContain('badge-verified');
    expect(observedBadge.className).toContain('badge-observed');
  });

  it('shows last geolocation for each device', async () => {
    renderAccountDetail();
    await waitFor(() => {
      expect(screen.getByText(/Chicago/)).toBeInTheDocument();
    });
    expect(screen.getByText(/London/)).toBeInTheDocument();
  });
});
