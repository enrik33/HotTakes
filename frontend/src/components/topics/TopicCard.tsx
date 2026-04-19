import { useNavigate } from 'react-router-dom';
import type { Topic } from '../../types/api';
import Card from '../ui/Card';
import Badge from '../ui/Badge';

interface TopicCardProps {
  topic: Topic;
}

export default function TopicCard({ topic }: TopicCardProps) {
  const navigate = useNavigate();

  return (
    <button
      onClick={() => navigate(`/topics/${topic.id}`)}
      className="w-full text-left focus:outline-none focus-visible:ring-2 focus-visible:ring-slate-400 rounded-xl"
    >
      <Card className="hover:border-slate-500 transition-colors cursor-pointer">
        <div className="flex items-start justify-between gap-3">
          <h2 className="font-semibold text-slate-100 leading-snug">
            {topic.name}
          </h2>
          <Badge
            label={topic.status}
            variant={topic.status === 'active' ? 'active' : 'paused'}
          />
        </div>
        {topic.description && (
          <p className="mt-2 text-sm text-slate-400 line-clamp-2">
            {topic.description}
          </p>
        )}
        <div className="mt-4 flex gap-4 text-xs text-slate-500">
          <span>{topic.post_count.toLocaleString()} posts</span>
          <span>{topic.comment_count.toLocaleString()} comments</span>
        </div>
      </Card>
    </button>
  );
}
