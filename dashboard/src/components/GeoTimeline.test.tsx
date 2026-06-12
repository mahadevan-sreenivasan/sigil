import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { GeoTimeline, type GeoEntry } from './GeoTimeline';

const ENTRIES: GeoEntry[] = [
  {
    visitorId: 'vis_001',
    ip: '203.0.113.1',
    country: 'IN',
    city: 'Mumbai',
    latitude: 19.076,
    longitude: 72.877,
    capturedAt: '2026-06-10T14:30:00Z',
  },
  {
    visitorId: 'vis_002',
    ip: '198.51.100.5',
    country: 'NG',
    city: 'Lagos',
    latitude: 6.524,
    longitude: 3.379,
    capturedAt: '2026-06-09T10:00:00Z',
  },
];

describe('GeoTimeline', () => {
  it('renders entries with timestamp, visitorId, IP, city, and country', () => {
    render(<GeoTimeline entries={ENTRIES} days={30} onDaysChange={() => {}} />);

    for (const entry of ENTRIES) {
      expect(screen.getByText(entry.visitorId)).toBeInTheDocument();
      expect(screen.getByText(entry.ip)).toBeInTheDocument();
      expect(screen.getByText(new RegExp(entry.city))).toBeInTheDocument();
      expect(screen.getByText(new RegExp(entry.country))).toBeInTheDocument();
    }
  });

  it('highlights entries where country differs from previous entry', () => {
    render(<GeoTimeline entries={ENTRIES} days={30} onDaysChange={() => {}} />);

    const entryElements = document.querySelectorAll('.geo-entry');
    // Sorted newest-first: vis_001 (IN) then vis_002 (NG)
    // First entry is never anomalous (no prior to compare)
    expect(entryElements[0]).not.toHaveClass('geo-entry--anomaly');
    // Second entry differs in country from the first → anomaly
    expect(entryElements[1]).toHaveClass('geo-entry--anomaly');
  });

  it('shows an empty-state message when there are no entries', () => {
    render(<GeoTimeline entries={[]} days={30} onDaysChange={() => {}} />);
    expect(screen.getByText(/no geolocation history/i)).toBeInTheDocument();
    expect(document.querySelectorAll('.geo-entry')).toHaveLength(0);
  });

  it('calls onDaysChange when the time range selector changes', async () => {
    const onDaysChange = vi.fn();
    const user = userEvent.setup();
    render(<GeoTimeline entries={ENTRIES} days={30} onDaysChange={onDaysChange} />);

    const select = screen.getByRole('combobox', { name: /time range/i });
    expect(select).toHaveValue('30');

    await user.selectOptions(select, '90');
    expect(onDaysChange).toHaveBeenCalledWith(90);
  });
});
