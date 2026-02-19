$ErrorActionPreference = "Stop"

param(
    [switch]$Force
)

function Write-IfMissing {
    param(
        [string]$Path,
        [string]$Content
    )

    if ((Test-Path $Path) -and (-not $Force)) {
        Write-Host "[skip] $Path already exists"
        return
    }

    $parent = Split-Path -Parent $Path
    if ($parent -and -not (Test-Path $parent)) {
        New-Item -ItemType Directory -Path $parent -Force | Out-Null
    }

    Set-Content -Path $Path -Value $Content -Encoding UTF8
    Write-Host "[write] $Path"
}

Write-Host "Bootstrapping HotTakes MVP starter files..."

$dirs = @(
    "backend/app/services",
    "backend/app/tasks",
    "backend/tests"
)

foreach ($d in $dirs) {
    if (-not (Test-Path $d)) {
        New-Item -ItemType Directory -Path $d -Force | Out-Null
        Write-Host "[mkdir] $d"
    }
}

Write-IfMissing "backend/app/services/mvp_scope.py" @'
"""
HotTakes MVP scope constants.
"""

MVP_SUBREDDIT = "soccer"
MVP_TOPIC_DESCRIPTION = "Player performances + transfers in r/soccer"
MVP_HISTORY_DAYS = 30

TARGET_POSTS_MIN = 80
TARGET_POSTS_MAX = 200
TARGET_COMMENTS_MIN = 8000
TARGET_COMMENTS_MAX = 30000

FETCH_INTERVAL_MINUTES = 30

STANCE_LABELS = ("SUPPORT", "OPPOSE", "MIXED", "NEUTRAL")
SENTIMENT_LABELS = ("POSITIVE", "NEUTRAL", "NEGATIVE")

MAX_COMMENTS_PER_TOPIC = 25000
MAX_COMMENTS_PER_POST = 1000
MAX_COMMENTS_PER_FETCH = 2000

MIN_CLUSTER_SIZE = 8
MIN_QUOTE_LENGTH = 40
MIN_CLASSIFIED_FOR_CLUSTER_VIEW = 300
TARGET_CLUSTERS_PER_STANCE_MIN = 8
TARGET_CLUSTERS_PER_STANCE_MAX = 12

TOP_QUOTES_PER_CLUSTER = 3
MAX_UI_CLUSTERS = 10

TRANSFER_KEYWORDS = [
    "transfer",
    "transfers",
    "here we go",
    "hwg",
    "signed",
    "signing",
    "joins",
    "loan",
    "on loan",
    "fee",
    "release clause",
    "contract",
    "wages",
    "bid",
    "offer",
    "agreement",
    "medical",
    "rumour",
    "rumor",
    "reported",
    "linked",
    "interest",
    "deal",
    "announcement",
    "confirmed",
    "official",
]

PERFORMANCE_KEYWORDS = [
    "motm",
    "man of the match",
    "performance",
    "form",
    "bottled",
    "carry job",
    "tactics",
    "system",
    "lineup",
    "selection",
    "subs",
    "manager",
    "coach",
    "sacked",
]

DEFAULT_TOPIC_KEYWORDS = TRANSFER_KEYWORDS + PERFORMANCE_KEYWORDS
'@

Write-IfMissing "backend/app/services/targeting.py" @'
"""
Filtering and stance-target helper rules for HotTakes MVP.
"""

from app.services.mvp_scope import DEFAULT_TOPIC_KEYWORDS


def _normalize(text: str) -> str:
    return (text or "").strip().lower()


def post_matches_scope(title: str, selftext: str, extra_terms: list[str] | None = None) -> bool:
    """Case-insensitive keyword match for post intake."""
    haystack = f"{_normalize(title)} {_normalize(selftext)}"
    keywords = DEFAULT_TOPIC_KEYWORDS + (extra_terms or [])
    return any(term.lower() in haystack for term in keywords)


def comment_mentions_target(comment_text: str, target_terms: list[str]) -> bool:
    """Only comments referencing the post target get stance modeling in MVP."""
    haystack = _normalize(comment_text)
    return any(term.lower() in haystack for term in target_terms if term)


def default_stance_for_off_target_comment(comment_text: str, target_terms: list[str]) -> str:
    """
    Rule-based gating:
    - If target not mentioned, force NEUTRAL
    - Else leave to classifier
    """
    if not comment_mentions_target(comment_text, target_terms):
        return "NEUTRAL"
    return "MODEL"
'@

Write-IfMissing "backend/app/tasks/fetch_job.py" @'
"""
Periodic Reddit fetch job (MVP skeleton).
"""

from app.config import settings
from app.services.mvp_scope import MVP_SUBREDDIT


def run_fetch_job() -> None:
    # TODO: wire app.services.reddit_fetcher implementation
    print(
        f"[fetch_job] subreddit=r/{MVP_SUBREDDIT} "
        f"interval={settings.fetch_interval_minutes}m "
        f"history_days={settings.history_days}"
    )
'@

Write-IfMissing "backend/app/tasks/classify_job.py" @'
"""
Periodic classification job (MVP skeleton).
"""


def run_classify_job() -> None:
    # TODO: run stance/sentiment/toxicity for unclassified comments
    print("[classify_job] running classification batch")
'@

Write-IfMissing "backend/app/tasks/cluster_job.py" @'
"""
Periodic clustering job (MVP skeleton).
"""


def run_cluster_job() -> None:
    # TODO: compute embeddings and stance-bucket clustering
    print("[cluster_job] running clustering batch")
'@

Write-IfMissing "backend/.env.mvp.example" @'
# HotTakes MVP defaults

ENVIRONMENT=development
DEBUG=true

# Use PostgreSQL locally for MVP
DATABASE_URL=postgresql://debateuser:debatepass@localhost:5432/social_debate
DATABASE_ECHO=false

REDDIT_CLIENT_ID=replace_me
REDDIT_CLIENT_SECRET=replace_me
REDDIT_USER_AGENT=HotTakesBot/1.0 (by u/replace_me)

SCHEDULER_ENABLED=true
FETCH_INTERVAL_MINUTES=30
CLASSIFY_INTERVAL_HOURS=6
CLUSTER_INTERVAL_HOURS=12
STATS_JOB_INTERVAL_HOURS=1

HISTORY_DAYS=30
MAX_COMMENTS_PER_TOPIC=25000
MAX_COMMENTS_PER_POST=1000
MAX_COMMENTS_PER_FETCH=2000

N_CLUSTERS_PER_STANCE=10
MIN_CLUSTER_SIZE=8
MIN_QUOTE_LENGTH=40
'@

Write-IfMissing "backend/tests/test_mvp_scope.py" @'
from app.services import mvp_scope


def test_keyword_lists_not_empty():
    assert len(mvp_scope.TRANSFER_KEYWORDS) > 0
    assert len(mvp_scope.PERFORMANCE_KEYWORDS) > 0


def test_cluster_gates():
    assert mvp_scope.MIN_CLUSTER_SIZE >= 8
    assert mvp_scope.MIN_QUOTE_LENGTH >= 40
'@

Write-Host ""
Write-Host "Done. Next steps:"
Write-Host "1) Review generated files."
Write-Host "2) Copy backend/.env.mvp.example to backend/.env and set Reddit credentials."
Write-Host "3) Start API: cd backend; uvicorn app.main:app --reload"
Write-Host ""
Write-Host "Tip: pass -Force to overwrite generated files."
