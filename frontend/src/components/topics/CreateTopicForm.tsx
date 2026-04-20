import { useState } from 'react';
import { useCreateTopic } from '../../hooks/useTopics';
import { ApiError } from '../../api/client';
import ErrorMessage from '../ui/ErrorMessage';

interface CreateTopicFormProps {
    onClose: () => void;
}

export default function CreateTopicForm({ onClose }: CreateTopicFormProps) {
    const [name, setName] = useState('');
    const [description, setDescription] = useState('');
    const { mutate, isPending, error } = useCreateTopic();

    const errorMsg =
        error instanceof ApiError && error.status === 400
            ? 'A topic with that name already exists.'
            : error
                ? (error as Error).message
                : null;

    function handleSubmit(e: React.FormEvent) {
        e.preventDefault();
        if (!name.trim()) return;
        mutate(
            { name: name.trim(), description: description.trim() || undefined },
            { onSuccess: onClose },
        );
    }

    return (
        <form onSubmit={handleSubmit} className="space-y-4">
            {errorMsg && <ErrorMessage message={errorMsg} />}
            <div>
                <label className="block text-sm font-medium text-slate-300 mb-1">
                    Name <span className="text-red-400">*</span>
                </label>
                <input
                    type="text"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    placeholder="e.g. AI safety concerns"
                    className="w-full rounded-lg border border-slate-600 bg-slate-900 px-3 py-2 text-sm text-slate-100 placeholder-slate-500 focus:border-slate-400 focus:outline-none"
                    required
                />
            </div>
            <div>
                <label className="block text-sm font-medium text-slate-300 mb-1">
                    Description
                </label>
                <textarea
                    value={description}
                    onChange={(e) => setDescription(e.target.value)}
                    rows={3}
                    placeholder="Optional description"
                    className="w-full rounded-lg border border-slate-600 bg-slate-900 px-3 py-2 text-sm text-slate-100 placeholder-slate-500 focus:border-slate-400 focus:outline-none resize-none"
                />
            </div>
            <div className="flex justify-end gap-3 pt-1">
                <button
                    type="button"
                    onClick={onClose}
                    className="px-4 py-2 text-sm text-slate-400 hover:text-slate-200 transition-colors"
                >
                    Cancel
                </button>
                <button
                    type="submit"
                    disabled={isPending || !name.trim()}
                    className="rounded-lg bg-slate-100 px-4 py-2 text-sm font-medium text-slate-900 hover:bg-white disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                    {isPending ? 'Creating…' : 'Create topic'}
                </button>
            </div>
        </form>
    );
}
