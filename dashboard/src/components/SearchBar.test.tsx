import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { SearchBar } from './SearchBar';

function renderWithRouter() {
  const routes: string[] = [];
  return {
    routes,
    ...render(
      <MemoryRouter initialEntries={['/']}>
        <Routes>
          <Route
            path="/"
            element={<SearchBar />}
          />
          <Route path="/visitor/:id" element={<div>visitor-view</div>} />
          <Route path="/ip/:ip" element={<div>ip-view</div>} />
          <Route path="/account/:id" element={<div>account-view</div>} />
        </Routes>
      </MemoryRouter>,
    ),
  };
}

describe('SearchBar', () => {
  it('routes vis_ prefix to visitor detail', async () => {
    const user = userEvent.setup();
    renderWithRouter();
    const input = screen.getByPlaceholderText(/search/i);
    await user.type(input, 'vis_abc123');
    await user.click(screen.getByRole('button', { name: /search/i }));
    expect(screen.getByText('visitor-view')).toBeInTheDocument();
  });

  it('routes IPv4 address to IP detail', async () => {
    const user = userEvent.setup();
    renderWithRouter();
    const input = screen.getByPlaceholderText(/search/i);
    await user.type(input, '192.168.1.1');
    await user.click(screen.getByRole('button', { name: /search/i }));
    expect(screen.getByText('ip-view')).toBeInTheDocument();
  });

  it('routes other strings to account detail', async () => {
    const user = userEvent.setup();
    renderWithRouter();
    const input = screen.getByPlaceholderText(/search/i);
    await user.type(input, 'cust_123');
    await user.click(screen.getByRole('button', { name: /search/i }));
    expect(screen.getByText('account-view')).toBeInTheDocument();
  });

  it('does not navigate on empty input', async () => {
    const user = userEvent.setup();
    renderWithRouter();
    await user.click(screen.getByRole('button', { name: /search/i }));
    expect(screen.queryByText('visitor-view')).not.toBeInTheDocument();
    expect(screen.queryByText('ip-view')).not.toBeInTheDocument();
    expect(screen.queryByText('account-view')).not.toBeInTheDocument();
  });
});
