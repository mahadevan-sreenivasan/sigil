import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { apiFetch } from '../api';

interface Geolocation {
  country: string;
  city: string;
  latitude: number;
  longitude: number;
}

interface AccountBinding {
  accountId: string;
  status: 'observed' | 'verified';
  firstSeenAt: string;
  lastSeenAt: string;
}

interface SignalSet {
  capturedAt: string;
  signals: Record<string, string>;
  geolocation: Geolocation;
}

interface VisitorData {
  visitorId: string;
  firstSeenAt: string;
  lastSeenAt: string;
  accountBindings: AccountBinding[];
  recentSignalSets: SignalSet[];
}

export function VisitorDetail() {
  const { id } = useParams<{ id: string }>();
  const [data, setData] = useState<VisitorData | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    apiFetch<VisitorData>(`/visitors/${id}`)
      .then(setData)
      .catch((err) => setError(err.message));
  }, [id]);

  if (error) return <div className="error-message">Error: {error}</div>;
  if (!data) return <div className="loading">Loading…</div>;

  return (
    <div className="detail-view">
      <h2>{data.visitorId}</h2>
      <dl className="meta-grid">
        <dt>First Seen</dt>
        <dd>{data.firstSeenAt}</dd>
        <dt>Last Seen</dt>
        <dd>{data.lastSeenAt}</dd>
      </dl>

      <section>
        <h3>Account Bindings</h3>
        {data.accountBindings.length === 0 ? (
          <p className="empty-state">No account bindings.</p>
        ) : (
          <table className="data-table">
            <thead>
              <tr>
                <th>Account</th>
                <th>Status</th>
                <th>First Seen</th>
                <th>Last Seen</th>
              </tr>
            </thead>
            <tbody>
              {data.accountBindings.map((b) => (
                <tr key={b.accountId}>
                  <td>{b.accountId}</td>
                  <td>
                    <span className={`badge badge-${b.status}`}>
                      {b.status}
                    </span>
                  </td>
                  <td>{b.firstSeenAt}</td>
                  <td>{b.lastSeenAt}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>

      <section>
        <h3>Recent Signal Sets</h3>
        {data.recentSignalSets.map((ss, i) => (
          <div key={i} className="signal-set-card">
            <div className="signal-set-header">
              <strong>{ss.capturedAt}</strong>
              {ss.geolocation && (
                <span className="geo-tag">
                  {ss.geolocation.city}, {ss.geolocation.country}
                </span>
              )}
            </div>
            <dl className="signal-list">
              {Object.entries(ss.signals).map(([key, value]) => (
                <div key={key} className="signal-entry">
                  <dt>{key}</dt>
                  <dd>{value}</dd>
                </div>
              ))}
            </dl>
          </div>
        ))}
      </section>
    </div>
  );
}
