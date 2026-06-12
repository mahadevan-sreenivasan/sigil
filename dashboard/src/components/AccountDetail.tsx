import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { apiFetch } from '../api';

interface Geolocation {
  country: string;
  city: string;
  latitude: number;
  longitude: number;
}

interface AccountVisitor {
  visitorId: string;
  bindingStatus: 'observed' | 'verified';
  firstSeenAt: string;
  lastSeenAt: string;
  lastGeolocation: Geolocation;
}

interface AccountData {
  accountId: string;
  visitors: AccountVisitor[];
}

export function AccountDetail() {
  const { id } = useParams<{ id: string }>();
  const [data, setData] = useState<AccountData | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    apiFetch<AccountData>(`/accounts/${id}/visitors`)
      .then(setData)
      .catch((err) => setError(err.message));
  }, [id]);

  if (error) return <div className="error-message">Error: {error}</div>;
  if (!data) return <div className="loading">Loading…</div>;

  return (
    <div className="detail-view">
      <h2>{data.accountId}</h2>

      <section>
        <h3>Devices</h3>
        {data.visitors.length === 0 ? (
          <p className="empty-state">No devices found for this account.</p>
        ) : (
          <table className="data-table">
            <thead>
              <tr>
                <th>Visitor ID</th>
                <th>Status</th>
                <th>First Seen</th>
                <th>Last Seen</th>
                <th>Last Location</th>
              </tr>
            </thead>
            <tbody>
              {data.visitors.map((v) => (
                <tr key={v.visitorId}>
                  <td>{v.visitorId}</td>
                  <td>
                    <span className={`badge badge-${v.bindingStatus}`}>
                      {v.bindingStatus}
                    </span>
                  </td>
                  <td>{v.firstSeenAt}</td>
                  <td>{v.lastSeenAt}</td>
                  <td>
                    {v.lastGeolocation
                      ? `${v.lastGeolocation.city}, ${v.lastGeolocation.country}`
                      : '—'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
    </div>
  );
}
