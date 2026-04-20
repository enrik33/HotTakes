import type { Quote } from '../../types/api';

interface QuoteCardProps {
    quote: Quote;
}

export default function QuoteCard({ quote }: QuoteCardProps) {
    return (
        <blockquote className="rounded-lg border border-slate-700 bg-slate-900/60 px-4 py-3">
            <p className="text-sm text-slate-300 leading-relaxed line-clamp-4">
                {quote.body}
            </p>
            <footer className="mt-2 flex items-center justify-between text-xs text-slate-500">
                <span className="font-mono">{quote.author_hash.slice(0, 8)}</span>
                <span>score {quote.score}</span>
            </footer>
        </blockquote>
    );
}
