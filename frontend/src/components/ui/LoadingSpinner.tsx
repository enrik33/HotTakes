export default function LoadingSpinner() {
    return (
        <div className="flex items-center justify-center py-16">
            <div className="h-8 w-8 animate-spin rounded-full border-4 border-slate-600 border-t-slate-300" />
        </div>
    );
}
