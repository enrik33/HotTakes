type Variant = 'active' | 'paused' | 'default';

const variantClasses: Record<Variant, string> = {
  active: 'bg-green-900/50 text-green-400 border-green-700',
  paused: 'bg-slate-700 text-slate-400 border-slate-600',
  default: 'bg-slate-700 text-slate-400 border-slate-600',
};

interface BadgeProps {
  label: string;
  variant?: Variant;
}

export default function Badge({ label, variant = 'default' }: BadgeProps) {
  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium border ${variantClasses[variant]}`}
    >
      {label}
    </span>
  );
}
