import { useState, type FormEvent } from 'react';
import { useNavigate } from 'react-router-dom';

const IPV4_RE = /^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$/;

export function detectQueryType(query: string): { type: 'visitor' | 'ip' | 'account'; id: string } {
  if (query.startsWith('vis_')) return { type: 'visitor', id: query };
  if (IPV4_RE.test(query)) return { type: 'ip', id: query };
  return { type: 'account', id: query };
}

export function SearchBar() {
  const [query, setQuery] = useState('');
  const navigate = useNavigate();

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    const trimmed = query.trim();
    if (!trimmed) return;

    const { type, id } = detectQueryType(trimmed);
    switch (type) {
      case 'visitor':
        navigate(`/visitor/${id}`);
        break;
      case 'ip':
        navigate(`/ip/${id}`);
        break;
      case 'account':
        navigate(`/account/${id}`);
        break;
    }
  }

  return (
    <form onSubmit={handleSubmit} className="search-bar">
      <input
        type="text"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        placeholder="Search visitor ID, IP, or account ID…"
      />
      <button type="submit" aria-label="Search">Search</button>
    </form>
  );
}
