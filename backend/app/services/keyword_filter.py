"""
Keyword filtering for HN story ingestion.

Determines whether a story title falls within the platform's debate scope
(tech / AI / engineering discourse) and extracts target entities for
downstream stance-gating.
"""

import re

# ---------------------------------------------------------------------------
# Keyword lists
# ---------------------------------------------------------------------------

AI_ML_KEYWORDS: list[str] = [
    # Core AI/ML concepts
    "ai",
    "artificial intelligence",
    "machine learning",
    "deep learning",
    "neural network",
    "large language model",
    "llm",
    "generative ai",
    "agi",
    "gpt",
    "transformer",
    "diffusion model",
    "fine-tuning",
    "rag",
    "embedding",
    "inference",
    # Products & models
    "chatgpt",
    "gpt-4",
    "gpt-5",
    "claude",
    "gemini",
    "llama",
    "mistral",
    "copilot",
    "dall-e",
    "stable diffusion",
    "midjourney",
    "sora",
    "grok",
    # Companies in the AI space
    "openai",
    "anthropic",
    "deepmind",
    "hugging face",
    "cohere",
    "inflection",
]

INDUSTRY_KEYWORDS: list[str] = [
    # Business events
    "startup",
    "vc",
    "venture capital",
    "layoff",
    "acquisition",
    "ipo",
    "funding",
    "valuation",
    "y combinator",
    "ycombinator",
    "saas",
    "open source",
    "big tech",
    # Major tech companies (debate catalysts)
    "microsoft",
    "google",
    "apple",
    "amazon",
    "meta",
    "nvidia",
    "tesla",
    "twitter",
    "x.com",
    "tiktok",
    "bytedance",
    "samsung",
    "intel",
    "amd",
    # Industry topics
    "privacy",
    "regulation",
    "antitrust",
    "copyright",
    "misinformation",
    "censorship",
    "surveillance",
    "data breach",
    "security vulnerability",
]

ENGINEERING_KEYWORDS: list[str] = [
    # Languages
    "rust",
    "golang",
    "python",
    "javascript",
    "typescript",
    "kotlin",
    "swift",
    "c++",
    "java",
    "ruby",
    # Web frameworks
    "react",
    "vue",
    "angular",
    "next.js",
    "svelte",
    "htmx",
    "django",
    "fastapi",
    "flask",
    # Databases & infra
    "postgres",
    "postgresql",
    "mysql",
    "mongodb",
    "redis",
    "sqlite",
    "kafka",
    "kubernetes",
    "docker",
    "terraform",
    "aws",
    "gcp",
    "azure",
    "cloudflare",
    "vercel",
    # Platform / tools
    "linux",
    "git",
    "github",
    "gitlab",
    "stack overflow",
    "devops",
    "microservices",
    "monolith",
    "serverless",
    "web assembly",
    "wasm",
]

DEFAULT_TOPIC_KEYWORDS: list[str] = (
    AI_ML_KEYWORDS + INDUSTRY_KEYWORDS + ENGINEERING_KEYWORDS
)

# ---------------------------------------------------------------------------
# Known tech entities for target extraction
# ---------------------------------------------------------------------------

_KNOWN_TECH_ENTITIES: frozenset[str] = frozenset(
    kw.lower()
    for kw in [
        # AI products
        "ChatGPT",
        "GPT-4",
        "GPT-5",
        "Claude",
        "Gemini",
        "LLaMA",
        "Mistral",
        "Copilot",
        "Grok",
        "Sora",
        # AI companies
        "OpenAI",
        "Anthropic",
        "DeepMind",
        "Nvidia",
        "HuggingFace",
        # Big tech
        "Google",
        "Microsoft",
        "Apple",
        "Amazon",
        "Meta",
        "Tesla",
        "Twitter",
        "Intel",
        "AMD",
        # Languages / runtimes
        "Rust",
        "Python",
        "JavaScript",
        "TypeScript",
        "Go",
        "Golang",
        "Kotlin",
        "Swift",
        "Java",
        "Ruby",
        # Frameworks
        "React",
        "Vue",
        "Angular",
        "Svelte",
        "Django",
        "FastAPI",
        "Flask",
        "Rails",
        # Infra / cloud
        "Kubernetes",
        "Docker",
        "AWS",
        "GCP",
        "Azure",
        "Cloudflare",
        "Vercel",
        "Linux",
        "GitHub",
        "GitLab",
        # Databases
        "PostgreSQL",
        "Postgres",
        "MySQL",
        "MongoDB",
        "Redis",
        "SQLite",
        "Kafka",
    ]
)

_STOP_WORDS: frozenset[str] = frozenset(
    [
        "a",
        "an",
        "the",
        "and",
        "or",
        "but",
        "in",
        "on",
        "at",
        "to",
        "for",
        "of",
        "with",
        "by",
        "from",
        "is",
        "are",
        "was",
        "were",
        "be",
        "been",
        "has",
        "have",
        "had",
        "do",
        "does",
        "did",
        "will",
        "would",
        "could",
        "should",
        "may",
        "might",
        "can",
        "it",
        "its",
        "this",
        "that",
        "these",
        "those",
        "my",
        "your",
        "our",
        "their",
        "how",
        "why",
        "what",
        "when",
        "where",
        "who",
        "which",
        "ask",
        "show",
        "tell",
        "hn",
        "new",
        "old",
        "just",
        "now",
        "not",
        "no",
        "yes",
        "after",
        "before",
        "more",
        "less",
        "than",
        "up",
        "out",
        "if",
        "so",
        "as",
        "we",
        "us",
        "you",
        "he",
        "she",
        "they",
        "his",
        "her",
        "I",
    ]
)

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def story_matches_scope(title: str, extra_terms: list[str] | None = None) -> bool:
    """
    Return True if the story title is within the platform's debate scope.

    Ask HN / Show HN stories are always included regardless of keywords because
    they represent direct community debate.  All other stories must contain at
    least one keyword from DEFAULT_TOPIC_KEYWORDS (or the optional extra_terms).

    Single-word keywords are matched on word boundaries to avoid false positives
    (e.g. "ai" inside "raises" or "paint").  Multi-word keywords use substring
    matching since their specificity is already high.
    """
    stripped = title.strip()
    lower = stripped.lower()

    # Ask HN / Show HN → always in scope
    if lower.startswith(("ask hn:", "show hn:")):
        return True

    keywords = DEFAULT_TOPIC_KEYWORDS + (extra_terms or [])
    for kw in keywords:
        kw_lower = kw.lower()
        if " " in kw_lower:
            # Multi-word phrase: simple substring is specific enough
            if kw_lower in lower:
                return True
        else:
            # Single word: require word boundary to avoid partial matches
            if re.search(r"\b" + re.escape(kw_lower) + r"\b", lower):
                return True
    return False


def extract_target_entities(title: str) -> list[str]:
    """
    Extract potential tech entities from a story title.

    Used for downstream stance-gating: knowing which products/companies
    a story is about lets the classifier anchor the SUPPORT/OPPOSE stance.

    Strategy:
    1. Match known tech entity names (case-insensitive).
    2. Include capitalised tokens that are not common stop-words and not the
       first word of the title (the first word is capitalised by convention).

    Returns at most 10 unique entities preserving original capitalisation.
    """
    tokens = re.findall(r"[A-Za-z][\w.+#-]*", title)
    entities: list[str] = []
    seen: set[str] = set()

    for i, token in enumerate(tokens):
        lower = token.lower()

        if lower in seen:
            continue

        # Match against known tech entity list
        if lower in _KNOWN_TECH_ENTITIES:
            entities.append(token)
            seen.add(lower)
            continue

        # Capitalised word that isn't the first word and isn't a stop-word
        if i > 0 and token[0].isupper() and len(token) > 2 and lower not in _STOP_WORDS:
            entities.append(token)
            seen.add(lower)

        if len(entities) >= 10:
            break

    return entities
