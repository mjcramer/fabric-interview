"""Synthetic data generation for AEO MVP demo."""
import random
from datetime import datetime, timedelta
from faker import Faker
from .models import Brand, Topic, Query, AIEngine, QueryRun, Citation, get_session, init_db

fake = Faker()
random.seed(42)

# ── Static fixtures ────────────────────────────────────────────────────────────

BRANDS = [
    {"name": "Salesforce", "domain": "salesforce.com", "category": "CRM"},
    {"name": "HubSpot",    "domain": "hubspot.com",    "category": "CRM"},
    {"name": "Pipedrive",  "domain": "pipedrive.com",  "category": "CRM"},
    {"name": "Notion",     "domain": "notion.so",      "category": "Productivity"},
    {"name": "Monday.com", "domain": "monday.com",     "category": "Productivity"},
    {"name": "Asana",      "domain": "asana.com",      "category": "Productivity"},
    {"name": "Confluence", "domain": "confluence.com", "category": "Productivity"},
    {"name": "Linear",     "domain": "linear.app",     "category": "Productivity"},
]

TOPICS = [
    {"name": "CRM Software",          "category": "CRM"},
    {"name": "Sales Pipeline Tools",  "category": "CRM"},
    {"name": "Project Management",    "category": "Productivity"},
    {"name": "Team Collaboration",    "category": "Productivity"},
    {"name": "Knowledge Management",  "category": "Productivity"},
]

QUERIES = {
    "CRM Software": [
        ("What is the best CRM for small businesses?",      "commercial"),
        ("How does Salesforce compare to HubSpot?",         "informational"),
        ("Which CRM integrates best with Gmail?",           "commercial"),
        ("What CRM do startups use?",                       "informational"),
        ("Best CRM for B2B sales teams",                    "commercial"),
        ("Free CRM software for nonprofits",                "commercial"),
        ("What is CRM software?",                           "informational"),
        ("CRM vs spreadsheets: which is better?",          "informational"),
        ("How to choose a CRM for your business",           "informational"),
        ("What features should a CRM have?",               "informational"),
    ],
    "Sales Pipeline Tools": [
        ("Best tools for managing a sales pipeline",        "commercial"),
        ("How to track deals in a sales pipeline",          "informational"),
        ("What is the best sales pipeline software?",       "commercial"),
        ("Sales pipeline vs sales funnel",                  "informational"),
        ("How to build a B2B sales pipeline",               "informational"),
        ("Pipeline management software for small teams",    "commercial"),
        ("How does Pipedrive work?",                        "navigational"),
        ("Sales forecasting tools compared",                "commercial"),
    ],
    "Project Management": [
        ("What is the best project management software?",   "commercial"),
        ("Asana vs Monday.com: which is better?",          "informational"),
        ("Best free project management tools",              "commercial"),
        ("How to manage remote teams effectively",          "informational"),
        ("Agile project management tools for engineers",    "commercial"),
        ("What project management method should I use?",    "informational"),
        ("How does Monday.com pricing work?",               "navigational"),
        ("Best tools for Kanban boards",                    "commercial"),
        ("Project management software for agencies",        "commercial"),
        ("Jira vs Linear for software teams",               "informational"),
    ],
    "Team Collaboration": [
        ("Best collaboration tools for remote teams",       "commercial"),
        ("How do teams share documents online?",            "informational"),
        ("Notion vs Confluence for teams",                  "informational"),
        ("What is the best wiki software?",                 "commercial"),
        ("How to improve team communication",               "informational"),
        ("Real-time collaboration tools for design teams",  "commercial"),
        ("Best internal knowledge base tools",              "commercial"),
    ],
    "Knowledge Management": [
        ("What is the best knowledge base software?",       "commercial"),
        ("How to build a company wiki",                     "informational"),
        ("Notion vs Confluence: which is better?",          "informational"),
        ("Best tools for storing company knowledge",        "commercial"),
        ("How does Notion work?",                           "navigational"),
        ("Knowledge management software for startups",      "commercial"),
        ("How to organize team documentation",              "informational"),
    ],
}

AI_ENGINES = [
    {"name": "ChatGPT",              "provider": "OpenAI"},
    {"name": "Perplexity",           "provider": "Perplexity AI"},
    {"name": "Google AI Overview",   "provider": "Google"},
    {"name": "Claude",               "provider": "Anthropic"},
]

# Brand citation affinity: brand → topic → base citation probability (0-1)
CITATION_AFFINITY: dict[str, dict[str, float]] = {
    "Salesforce":  {"CRM Software": 0.92, "Sales Pipeline Tools": 0.80, "Project Management": 0.15, "Team Collaboration": 0.10, "Knowledge Management": 0.05},
    "HubSpot":     {"CRM Software": 0.85, "Sales Pipeline Tools": 0.70, "Project Management": 0.20, "Team Collaboration": 0.15, "Knowledge Management": 0.05},
    "Pipedrive":   {"CRM Software": 0.60, "Sales Pipeline Tools": 0.75, "Project Management": 0.05, "Team Collaboration": 0.05, "Knowledge Management": 0.02},
    "Notion":      {"CRM Software": 0.08, "Sales Pipeline Tools": 0.05, "Project Management": 0.65, "Team Collaboration": 0.75, "Knowledge Management": 0.90},
    "Monday.com":  {"CRM Software": 0.20, "Sales Pipeline Tools": 0.25, "Project Management": 0.80, "Team Collaboration": 0.55, "Knowledge Management": 0.25},
    "Asana":       {"CRM Software": 0.10, "Sales Pipeline Tools": 0.10, "Project Management": 0.75, "Team Collaboration": 0.50, "Knowledge Management": 0.20},
    "Confluence":  {"CRM Software": 0.05, "Sales Pipeline Tools": 0.05, "Project Management": 0.45, "Team Collaboration": 0.60, "Knowledge Management": 0.80},
    "Linear":      {"CRM Software": 0.02, "Sales Pipeline Tools": 0.05, "Project Management": 0.55, "Team Collaboration": 0.30, "Knowledge Management": 0.15},
}

# Engines that expose source URLs, with probability of including a URL per citation
ENGINE_URL_PROBABILITY: dict[str, float] = {
    "ChatGPT":            0.25,   # browsing mode, not always on
    "Perplexity":         0.95,   # almost always cites sources
    "Google AI Overview": 0.85,   # usually shows source links
    "Claude":             0.10,   # tool use is rare in practice
}

# Per-brand URL pools. A small number of pages drive most citations (power law).
# Each entry: (path, weight) — higher weight = cited more often.
BRAND_URLS: dict[str, list[tuple[str, float]]] = {
    "Salesforce": [
        ("/crm/what-is-crm/",                           10.0),
        ("/blog/sales/best-crm-small-business/",         8.0),
        ("/products/sales/crm/",                         7.0),
        ("/blog/sales/crm-vs-spreadsheets/",             5.0),
        ("/solutions/small-business-crm/",               4.0),
        ("/blog/sales/sales-pipeline-management/",       3.0),
        ("/resources/crm-buyers-guide/",                 2.5),
        ("/blog/sales/crm-features/",                    2.0),
    ],
    "HubSpot": [
        ("/products/crm/",                               10.0),
        ("/blog/sales/best-crm-tools/",                   8.0),
        ("/blog/sales/free-crm-software/",                6.0),
        ("/marketing/free-crm-software/",                 5.0),
        ("/blog/sales/pipeline-management/",              4.0),
        ("/blog/sales/crm-vs-excel/",                     3.0),
        ("/resources/what-is-crm/",                       2.5),
        ("/blog/marketing/collaboration-tools/",          2.0),
    ],
    "Pipedrive": [
        ("/crm-system/",                                 10.0),
        ("/blog/sales-pipeline/",                         8.0),
        ("/features/",                                    6.0),
        ("/blog/crm-software-for-small-business/",        5.0),
        ("/blog/sales-pipeline-management-guide/",        4.0),
        ("/alternatives/salesforce-alternative/",         3.0),
        ("/blog/crm-vs-spreadsheet/",                     2.0),
    ],
    "Notion": [
        ("/product/",                                    10.0),
        ("/blog/what-is-a-knowledge-base/",               8.0),
        ("/blog/team-wiki/",                              7.0),
        ("/blog/project-management-tool/",                6.0),
        ("/templates/project-management/",               5.0),
        ("/blog/notion-vs-confluence/",                   4.5),
        ("/blog/collaboration-tools/",                    3.0),
        ("/help/what-is-notion/",                         2.0),
    ],
    "Monday.com": [
        ("/project-management/",                         10.0),
        ("/blog/project-management-tools/",               8.0),
        ("/blog/best-project-management-software/",       7.0),
        ("/blog/remote-work-tools/",                      5.0),
        ("/blog/asana-vs-monday/",                        4.5),
        ("/features/",                                    4.0),
        ("/blog/kanban-board/",                           3.0),
        ("/blog/crm/",                                    2.0),
    ],
    "Asana": [
        ("/uses/project-management/",                    10.0),
        ("/resources/project-management-tools/",          8.0),
        ("/resources/best-collaboration-tools/",          7.0),
        ("/resources/remote-work-tools/",                 5.0),
        ("/resources/what-is-asana/",                     4.0),
        ("/blog/asana-vs-monday/",                        4.0),
        ("/resources/agile-project-management/",          3.0),
        ("/resources/team-productivity/",                 2.0),
    ],
    "Confluence": [
        ("/software/confluence/",                        10.0),
        ("/software/confluence/guides/team-wiki/",        8.0),
        ("/software/confluence/knowledge-base/",          7.0),
        ("/blog/teamwork/confluence-vs-notion/",          6.0),
        ("/blog/teamwork/best-wiki-software/",            4.0),
        ("/software/confluence/features/",                3.5),
        ("/blog/teamwork/knowledge-management/",          3.0),
    ],
    "Linear": [
        ("/",                                            10.0),
        ("/blog/linear-vs-jira/",                         9.0),
        ("/features/",                                    7.0),
        ("/blog/project-management-for-engineers/",       6.0),
        ("/blog/issue-tracking/",                         4.0),
        ("/blog/agile-tools/",                            3.0),
        ("/blog/software-team-workflow/",                 2.5),
    ],
}

SENTIMENT_WEIGHTS = {
    "Salesforce":  [0.55, 0.35, 0.10],
    "HubSpot":     [0.65, 0.28, 0.07],
    "Pipedrive":   [0.60, 0.32, 0.08],
    "Notion":      [0.70, 0.25, 0.05],
    "Monday.com":  [0.50, 0.38, 0.12],
    "Asana":       [0.55, 0.35, 0.10],
    "Confluence":  [0.45, 0.40, 0.15],
    "Linear":      [0.75, 0.22, 0.03],
}

EXCERPT_TEMPLATES = {
    "positive": [
        "{brand} is widely regarded as one of the best options for {topic_lower}, offering robust features and deep integrations.",
        "Many experts recommend {brand} for {topic_lower} due to its intuitive interface and strong ecosystem.",
        "{brand} stands out in {topic_lower} with its powerful automation and enterprise-grade reliability.",
        "For teams scaling quickly, {brand} provides the flexibility needed in {topic_lower}.",
    ],
    "neutral": [
        "{brand} is a popular choice for {topic_lower}, though it may be overkill for smaller teams.",
        "{brand} offers a comprehensive {topic_lower} solution with pricing that varies by team size.",
        "While {brand} is feature-rich, teams should evaluate whether its {topic_lower} capabilities match their specific needs.",
    ],
    "negative": [
        "Some users find {brand} overly complex for {topic_lower}, especially for smaller organizations.",
        "{brand} can be expensive relative to alternatives for {topic_lower}, particularly at scale.",
        "Teams have reported a steep learning curve with {brand} for {topic_lower} use cases.",
    ],
}


def _make_excerpt(brand_name: str, topic_name: str, sentiment: str) -> str:
    templates = EXCERPT_TEMPLATES[sentiment]
    return random.choice(templates).format(
        brand=brand_name,
        topic_lower=topic_name.lower(),
    )


def _pick_url(brand_name: str, domain: str, engine_name: str) -> str | None:
    """Return a source URL for this citation, or None if the engine doesn't expose sources."""
    p = ENGINE_URL_PROBABILITY.get(engine_name, 0.0)
    if random.random() > p:
        return None
    pool = BRAND_URLS.get(brand_name, [])
    if not pool:
        return None
    paths, weights = zip(*pool)
    path = random.choices(paths, weights=weights)[0]
    return f"https://{domain}{path}"


def seed(days: int = 90):
    """Populate the database with synthetic AEO data for the last `days` days."""
    init_db()
    session = get_session()

    # ── Insert static fixtures ─────────────────────────────────────────────────
    brand_map: dict[str, Brand] = {}
    for b in BRANDS:
        brand = Brand(**b)
        session.add(brand)
        brand_map[b["name"]] = brand

    topic_map: dict[str, Topic] = {}
    for t in TOPICS:
        topic = Topic(**t)
        session.add(topic)
        topic_map[t["name"]] = topic

    query_map: dict[str, list[Query]] = {}
    for topic_name, qs in QUERIES.items():
        topic = topic_map[topic_name]
        query_map[topic_name] = []
        for text, intent in qs:
            q = Query(text=text, topic=topic, intent=intent)
            session.add(q)
            query_map[topic_name].append(q)

    engine_map: dict[str, AIEngine] = {}
    for e in AI_ENGINES:
        ae = AIEngine(**e)
        session.add(ae)
        engine_map[e["name"]] = ae

    session.flush()

    # ── Generate query runs and citations ──────────────────────────────────────
    end_date   = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    start_date = end_date - timedelta(days=days)

    all_brands = list(brand_map.values())

    for day_offset in range(days):
        run_date = start_date + timedelta(days=day_offset)

        for topic_name, queries in query_map.items():
            for query in queries:
                # Not every query runs every day against every engine
                for engine_name, engine in engine_map.items():
                    if random.random() > 0.85:  # ~85% of query/engine pairs run per day
                        continue

                    # Determine which brands get cited in this run
                    cited_brands = []
                    for brand in all_brands:
                        affinity = CITATION_AFFINITY.get(brand.name, {}).get(topic_name, 0.0)
                        # Add small random noise to simulate variability
                        p = min(1.0, affinity + random.gauss(0, 0.05))
                        if random.random() < p:
                            cited_brands.append(brand)

                    # Randomize citation order (position)
                    random.shuffle(cited_brands)

                    run = QueryRun(
                        query=query,
                        engine=engine,
                        run_at=run_date,
                        total_citations=len(cited_brands),
                    )
                    session.add(run)
                    session.flush()

                    for pos, brand in enumerate(cited_brands, start=1):
                        weights = SENTIMENT_WEIGHTS.get(brand.name, [0.6, 0.3, 0.1])
                        sentiment = random.choices(["positive", "neutral", "negative"], weights=weights)[0]
                        citation = Citation(
                            run=run,
                            brand=brand,
                            position=pos,
                            sentiment=sentiment,
                            excerpt=_make_excerpt(brand.name, topic_name, sentiment),
                            source_url=_pick_url(brand.name, brand.domain, engine_name),
                        )
                        session.add(citation)

    session.commit()
    session.close()
    print(f"Seeded {days} days of synthetic AEO data.")
