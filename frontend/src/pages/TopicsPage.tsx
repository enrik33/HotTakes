import { useState } from 'react';
import AppShell from '../components/layout/AppShell';
import TopicCard from '../components/topics/TopicCard';
import CreateTopicForm from '../components/topics/CreateTopicForm';
import LoadingSpinner from '../components/ui/LoadingSpinner';
import ErrorMessage from '../components/ui/ErrorMessage';
import EmptyState from '../components/ui/EmptyState';
import Card from '../components/ui/Card';
import { useTopics } from '../hooks/useTopics';

export default function TopicsPage() {
  const [showForm, setShowForm] = useState(false);
  const { data: topics, isLoading, error } = useTopics();

  return (
    <AppShell>
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Topics</h1>
          <p className="text-slate-400 text-sm mt-1">
            Track opinion clusters across Hacker News threads
          </p>
        </div>
        <button
          onClick={() => setShowForm(true)}
          className="rounded-lg bg-slate-100 px-4 py-2 text-sm font-medium text-slate-900 hover:bg-white transition-colors"
        >
          + New topic
        </button>
      </div>

      {showForm && (
        <div className="mb-8">
          <Card>
            <h2 className="text-base font-semibold mb-4">New topic</h2>
            <CreateTopicForm onClose={() => setShowForm(false)} />
          </Card>
        </div>
      )}

      {isLoading && <LoadingSpinner />}
      {error && <ErrorMessage message={(error as Error).message} />}
      {!isLoading && !error && topics?.length === 0 && (
        <EmptyState
          title="No topics yet"
          description="Create your first topic to start tracking opinion clusters."
        />
      )}

      {topics && topics.length > 0 && (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {topics.map((topic) => (
            <TopicCard key={topic.id} topic={topic} />
          ))}
        </div>
      )}
    </AppShell>
  );
}
