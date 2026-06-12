import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { apiFetch } from '../api';

interface IpVisitor {
  visitorId: string;
  accountIds: string[];
  firstSeenFromIp: string;
  lastSeenFromIp: string;
  requestCount: number;
}

interface IpData {
  ip: string;
  visitors: IpVisitor[];
}

export function IpDetail() {
  const { ip } = useParams<{ ip: string }>();
  const [data, setData] = useState<IpData | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!ip) return;
    apiFetch<IpData>(`/ip/${ip}/visitors`)
      .then(setData)
      .catch((err) => setError(err.message));
  }, [ip]);

  if (error) return <div className="error-message">Error: {error}</div>;
  if (!data) return <div className="loading">Loading…</div>;

  return (
    <div className="detail-view">
      <h2>{data.ip}</h2>

      <section>
        <h3>Visitors from this IP</h3>
        {data.visitors.length === 0 ? (
          <p className="empty-state">No visitors recorded from this IP.</p>
        ) : (
          <table className="data-table">
            <thead>
              <tr>
                <th>Visitor ID</th>
                <th>Accounts</th>
                <th>First Seen</th>
                <th>Last Seen</th>
                <th>Requests</th>
              </tr>
            </thead>
            <tbody>
              {data.visitors.map((v) => (
                <tr key={v.visitorId}>
                  <td>{v.visitorId}</td>
                  <td>{v.accountIds.length > 0 ? v.accountIds.join(', ') : '—'}</td>
                  <td>{v.firstSeenFromIp}</td>
                  <td>{v.lastSeenFromIp}</td>
                  <td>{v.requestCount}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
    </div>
  );
}
