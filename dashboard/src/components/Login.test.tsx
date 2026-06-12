import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Login } from './Login';

describe('Login', () => {
  beforeEach(() => {
    sessionStorage.clear();
  });

  it('renders a secret key input and submit button', () => {
    render(<Login onLogin={() => {}} />);
    expect(screen.getByLabelText(/secret key/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /log in/i })).toBeInTheDocument();
  });

  it('stores key in sessionStorage and calls onLogin on submit', async () => {
    const onLogin = vi.fn();
    const user = userEvent.setup();
    render(<Login onLogin={onLogin} />);

    await user.type(screen.getByLabelText(/secret key/i), 'sk_test_abc');
    await user.click(screen.getByRole('button', { name: /log in/i }));

    expect(sessionStorage.getItem('sigil_secret_key')).toBe('sk_test_abc');
    expect(onLogin).toHaveBeenCalled();
  });

  it('does not submit with empty key', async () => {
    const onLogin = vi.fn();
    const user = userEvent.setup();
    render(<Login onLogin={onLogin} />);

    await user.click(screen.getByRole('button', { name: /log in/i }));

    expect(sessionStorage.getItem('sigil_secret_key')).toBeNull();
    expect(onLogin).not.toHaveBeenCalled();
  });
});
