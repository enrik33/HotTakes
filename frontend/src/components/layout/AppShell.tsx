import type { ReactNode } from 'react';
import { Link } from 'react-router-dom';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { getHealth } from '../../api/health';

interface AppShellProps {
  children: ReactNode;
}

export default function AppShell({ children }: AppShellProps) {
  const qc = useQueryClient();
  const { data: health } = useQuery({
    queryKey: ['health'],
    queryFn: getHealth,
    staleTime: 30_000,
  });

  const ok = health?.status === 'ok';

  function handleRefresh() {
    qc.invalidateQueries();
  }

  return (
    <div className="min-h-screen bg-slate-900 text-slate-100">
      <header className="sticky top-0 z-10 border-b border-slate-800 bg-slate-900/95 backdrop-blur">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
          <Link
            to="/"
            className="text-xl font-bold tracking-tight hover:text-slate-300 transition-colors"
          >
            HotTakes
          </Link>
          <div className="flex items-center gap-4">
            <button
              onClick={handleRefresh}
              className="text-xs text-slate-500 hover:text-slate-300 transition-colors"
              title="Refresh all data"
            >
              ↻ Refresh
            </button>
            {health && (
              <span
                className={`flex items-center gap-1.5 text-xs ${ok ? 'text-green-400' : 'text-amber-400'}`}
              >
                <span
                  className={`h-1.5 w-1.5 rounded-full ${ok ? 'bg-green-400' : 'bg-amber-400'}`}
                />
                {health.status}
              </span>
            )}
          </div>
        </div>
      </header>
      <main className="mx-auto max-w-6xl px-6 py-10">{children}</main>
    </div>
  );
}
