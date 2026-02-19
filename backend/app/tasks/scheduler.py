"""
Scheduler for background tasks using APScheduler.
"""
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from app.config import settings

scheduler = BackgroundScheduler()


def start_scheduler():
    """Start the background scheduler."""
    if not scheduler.running:
        # Add jobs
        scheduler.add_job(
            fetch_reddit_data,
            trigger=IntervalTrigger(minutes=settings.fetch_interval_minutes),
            id="fetch_reddit",
            name="Fetch Reddit data",
            replace_existing=True,
        )
        scheduler.add_job(
            classify_comments,
            trigger=IntervalTrigger(hours=settings.classify_interval_hours),
            id="classify",
            name="Classify comments",
            replace_existing=True,
        )
        scheduler.add_job(
            cluster_arguments,
            trigger=IntervalTrigger(hours=settings.cluster_interval_hours),
            id="cluster",
            name="Cluster arguments",
            replace_existing=True,
        )
        scheduler.add_job(
            compute_daily_stats,
            trigger=IntervalTrigger(hours=settings.stats_job_interval_hours),
            id="stats",
            name="Compute daily stats",
            replace_existing=True,
        )
        
        scheduler.start()


def stop_scheduler():
    """Stop the background scheduler."""
    if scheduler.running:
        scheduler.shutdown()


# Task functions (to be implemented)
def fetch_reddit_data():
    """Fetch new posts and comments from Reddit."""
    # TODO: Implement reddit_fetcher.py
    print("Fetching Reddit data...")


def classify_comments():
    """Classify unclassified comments."""
    # TODO: Implement classifier.py
    print("Classifying comments...")


def cluster_arguments():
    """Generate argument clusters."""
    # TODO: Implement clusterer.py
    print("Clustering arguments...")


def compute_daily_stats():
    """Compute daily statistics."""
    # TODO: Implement analytics.py
    print("Computing daily stats...")
