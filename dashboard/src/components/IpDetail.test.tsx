import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { IpDetail } from './IpDetail';

const MOCK_IP = {
  ip: '9.10.11.12',
  visitors: [
    {
      visitorId: 'vis_x1',
      accountIds: ['acct_ip1'],
      firstSeenFromIp: '2025-02-01 10:00:00',
      lastSeenFromIp: '2025-06-01 16:00:00',
      requestCount: 5,
    },
    {
      visitorId: 'vis_x2',
      accountIds: [],
      firstSeenFromIp: '2025-04-10 12:00:00',
      lastSeenFromIp: '2025-04-10 12:00:00',
      requestCount: 1,
    },
  ],
};

function renderIpDetail() {
  globalThis.fetch = vi.fn(async () =>
    new Response(JSON.stringify(MOCK_IP), { status: 200 }),
  );
  sessionStorage.setItem('sigil_secret_key', 'sk_test');

  return render(
    <MemoryRouter initialEntries={['/ip/9.10.11.12']}>
      <Routes>
        <Route path="/ip/:ip" element={<IpDetail />} />
      </Routes>
    </MemoryRouter>,
  );
}

describe('IpDetail', () => {
  beforeEach(() => sessionStorage.clear());

  it('displays the IP address', async () => {
    renderIpDetail();
    await waitFor(() => {
      expect(screen.getByText('9.10.11.12')).toBeInTheDocument();
    });
  });

  it('lists visitors with request counts', async () => {
    renderIpDetail();
    await waitFor(() => {
      expect(screen.getByText('vis_x1')).toBeInTheDocument();
    });
    expect(screen.getByText('vis_x2')).toBeInTheDocument();
    expect(screen.getByText('5')).toBeInTheDocument();
    expect(screen.getByText('1')).toBeInTheDocument();
  });

  it('shows associated account IDs', async () => {
    renderIpDetail();
    await waitFor(() => {
      expect(screen.getByText('acct_ip1')).toBeInTheDocument();
    });
  });

  it('shows dash for visitors with no accounts', async () => {
    renderIpDetail();
    await waitFor(() => {
      expect(screen.getByText('vis_x2')).toBeInTheDocument();
    });
    const row = screen.getByText('vis_x2').closest('tr')!;
    expect(row.textContent).toContain('—');
  });
});
