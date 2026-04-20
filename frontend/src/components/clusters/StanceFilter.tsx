type Stance = 'ALL' | 'SUPPORT' | 'OPPOSE' | 'MIXED' | 'NEUTRAL';

const STANCES: Stance[] = ['ALL', 'SUPPORT', 'OPPOSE', 'MIXED', 'NEUTRAL'];

const activeClass: Record<Stance, string> = {
    ALL: 'border-slate-300 text-slate-100',
    SUPPORT: 'border-green-400 text-green-400',
    OPPOSE: 'border-red-400 text-red-400',
    MIXED: 'border-amber-400 text-amber-400',
    NEUTRAL: 'border-slate-400 text-slate-400',
};

interface StanceFilterProps {
    value: Stance;
    onChange: (s: Stance) => void;
}

export default function StanceFilter({ value, onChange }: StanceFilterProps) {
    return (
        <div className="flex gap-1 flex-wrap">
            {STANCES.map((s) => (
                <button
                    key={s}
                    onClick={() => onChange(s)}
                    className={`px-3 py-1 rounded-full text-xs font-medium border transition-colors
            ${value === s
                            ? activeClass[s]
                            : 'border-slate-700 text-slate-500 hover:border-slate-500 hover:text-slate-300'
                        }`}
                >
                    {s}
                </button>
            ))}
        </div>
    );
}
