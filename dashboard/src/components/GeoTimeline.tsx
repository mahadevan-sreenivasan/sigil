export interface GeoEntry {
  visitorId: string;
  ip: string;
  country: string;
  city: string;
  latitude: number;
  longitude: number;
  capturedAt: string;
}

interface GeoTimelineProps {
  entries: GeoEntry[];
  days: number;
  onDaysChange: (days: number) => void;
}

const TIME_RANGE_OPTIONS = [7, 30, 90, 180] as const;

function formatTimestamp(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleString(undefined, {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

export function GeoTimeline({ entries, days, onDaysChange }: GeoTimelineProps) {
  const sorted = [...entries].sort(
    (a, b) => new Date(b.capturedAt).getTime() - new Date(a.capturedAt).getTime(),
  );

  const timeRangeSelector = (
    <div className="geo-timeline-controls">
      <label htmlFor="geo-time-range">Time range</label>
      <select
        id="geo-time-range"
        value={days}
        onChange={(e) => onDaysChange(Number(e.target.value))}
      >
        {TIME_RANGE_OPTIONS.map((d) => (
          <option key={d} value={d}>{d} days</option>
        ))}
      </select>
    </div>
  );

  if (sorted.length === 0) {
    return (
      <div className="geo-timeline">
        {timeRangeSelector}
        <p className="empty-state">No geolocation history found.</p>
      </div>
    );
  }

  return (
    <div className="geo-timeline">
      {timeRangeSelector}
      <div className="geo-timeline-track">
        {sorted.map((entry, i) => {
          const isAnomaly = i > 0 && entry.country !== sorted[i - 1].country;
          const className = `geo-entry${isAnomaly ? ' geo-entry--anomaly' : ''}`;

          return (
            <div key={`${entry.visitorId}-${entry.capturedAt}-${i}`} className={className}>
              <div className="geo-entry-dot" />
              <div className="geo-entry-card">
                <time className="geo-entry-time">{formatTimestamp(entry.capturedAt)}</time>
                <span className="geo-entry-location">{entry.city}, {entry.country}</span>
                <span className="geo-entry-visitor">{entry.visitorId}</span>
                <span className="geo-entry-ip">{entry.ip}</span>
                {isAnomaly && (
                  <span className="geo-entry-badge">Location jump</span>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
