import { BrowserRouter, Routes, Route, Navigate, useNavigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './auth';
import { Login } from './components/Login';
import { SearchBar } from './components/SearchBar';
import { VisitorDetail } from './components/VisitorDetail';
import { AccountDetail } from './components/AccountDetail';
import { IpDetail } from './components/IpDetail';
import { AuthError } from './api';
import { useEffect } from 'react';
import './styles.css';

function ErrorBoundaryRedirect() {
  const { logout } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    const handler = (event: PromiseRejectionEvent) => {
      if (event.reason instanceof AuthError) {
        event.preventDefault();
        logout();
        navigate('/login');
      }
    };
    window.addEventListener('unhandledrejection', handler);
    return () => window.removeEventListener('unhandledrejection', handler);
  }, [logout, navigate]);

  return null;
}

function DashboardLayout() {
  const { logout } = useAuth();
  const navigate = useNavigate();

  return (
    <div className="dashboard">
      <header className="app-header">
        <h1 onClick={() => navigate('/')} style={{ cursor: 'pointer' }}>
          Sigil
        </h1>
        <SearchBar />
        <button className="btn-logout" onClick={logout}>
          Log out
        </button>
      </header>
      <main className="app-main">
        <Routes>
          <Route
            index
            element={
              <div className="welcome">
                <h2>Investigation Dashboard</h2>
                <p>Search for a visitor ID, account ID, or IP address to begin.</p>
              </div>
            }
          />
          <Route path="visitor/:id" element={<VisitorDetail />} />
          <Route path="account/:id" element={<AccountDetail />} />
          <Route path="ip/:ip" element={<IpDetail />} />
        </Routes>
      </main>
    </div>
  );
}

function AuthGate() {
  const { isAuthenticated, login } = useAuth();

  if (!isAuthenticated) {
    return <Login onLogin={login} />;
  }

  return (
    <>
      <ErrorBoundaryRedirect />
      <DashboardLayout />
    </>
  );
}

export function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<AuthGate />} />
          <Route path="/*" element={<AuthGate />} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  );
}
