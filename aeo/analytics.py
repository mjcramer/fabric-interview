"""Core AEO metrics computed directly from the database."""
from datetime import datetime, timedelta
from sqlalchemy import func, case, and_, distinct, or_
from .models import Brand, Topic, Query, AIEngine, QueryRun, Citation, get_session


def _date_range(days: int):
    end = datetime.utcnow()
    start = end - timedelta(days=days)
    return start, end


# ── Public metrics ─────────────────────────────────────────────────────────────

def citation_rate(brand_id: int, days: int = 30, engine_id: int | None = None, topic_id: int | None = None) -> float:
    """Fraction of query runs where the brand was cited."""
    session = get_session()
    start, end = _date_range(days)

    runs_q = session.query(func.count(distinct(QueryRun.id))).filter(
        QueryRun.run_at.between(start, end)
    )
    cited_q = session.query(func.count(distinct(Citation.run_id))).join(QueryRun).filter(
        Citation.brand_id == brand_id,
        QueryRun.run_at.between(start, end),
    )

    if engine_id:
        runs_q  = runs_q.filter(QueryRun.engine_id == engine_id)
        cited_q = cited_q.filter(QueryRun.engine_id == engine_id)

    if topic_id:
        runs_q  = runs_q.join(Query).filter(Query.topic_id == topic_id)
        cited_q = cited_q.join(Citation.run).join(Query).filter(Query.topic_id == topic_id)

    total_runs = runs_q.scalar() or 0
    cited_runs = cited_q.scalar() or 0
    session.close()

    return round(cited_runs / total_runs, 4) if total_runs else 0.0


def share_of_voice(topic_id: int, days: int = 30, engine_id: int | None = None) -> list[dict]:
    """Citation count per brand in a topic, normalized to % of total citations."""
    session = get_session()
    start, end = _date_range(days)

    q = (
        session.query(Brand.name, func.count(Citation.id).label("citations"))
        .join(Citation, Citation.brand_id == Brand.id)
        .join(QueryRun, Citation.run_id == QueryRun.id)
        .join(Query, QueryRun.query_id == Query.id)
        .filter(Query.topic_id == topic_id, QueryRun.run_at.between(start, end))
    )
    if engine_id:
        q = q.filter(QueryRun.engine_id == engine_id)

    rows = q.group_by(Brand.name).order_by(func.count(Citation.id).desc()).all()
    session.close()

    total = sum(r.citations for r in rows) or 1
    return [
        {"brand": r.name, "citations": r.citations, "share": round(r.citations / total * 100, 1)}
        for r in rows
    ]


def sentiment_breakdown(brand_id: int, days: int = 30) -> dict:
    """Positive / neutral / negative citation counts for a brand."""
    session = get_session()
    start, end = _date_range(days)

    rows = (
        session.query(Citation.sentiment, func.count(Citation.id))
        .join(QueryRun)
        .filter(Citation.brand_id == brand_id, QueryRun.run_at.between(start, end))
        .group_by(Citation.sentiment)
        .all()
    )
    session.close()

    result = {"positive": 0, "neutral": 0, "negative": 0}
    for sentiment, count in rows:
        result[sentiment] = count
    return result


def avg_position(brand_id: int, days: int = 30, topic_id: int | None = None) -> float | None:
    """Average citation position (lower = more prominent)."""
    session = get_session()
    start, end = _date_range(days)

    q = (
        session.query(func.avg(Citation.position))
        .join(QueryRun)
        .filter(Citation.brand_id == brand_id, QueryRun.run_at.between(start, end))
    )
    if topic_id:
        q = q.join(Query, QueryRun.query_id == Query.id).filter(Query.topic_id == topic_id)

    result = q.scalar()
    session.close()
    return round(float(result), 2) if result else None


def citation_trend(brand_id: int, days: int = 30, engine_id: int | None = None) -> list[dict]:
    """Daily citation rate for a brand over the last N days."""
    session = get_session()
    start, end = _date_range(days)

    # Total runs per day
    runs_base = session.query(
        func.date(QueryRun.run_at).label("day"),
        func.count(distinct(QueryRun.id)).label("total_runs"),
    ).filter(QueryRun.run_at.between(start, end))

    # Cited runs per day for brand
    cited_base = (
        session.query(
            func.date(QueryRun.run_at).label("day"),
            func.count(distinct(Citation.run_id)).label("cited_runs"),
        )
        .join(Citation, Citation.run_id == QueryRun.id)
        .filter(Citation.brand_id == brand_id, QueryRun.run_at.between(start, end))
    )

    if engine_id:
        runs_base  = runs_base.filter(QueryRun.engine_id == engine_id)
        cited_base = cited_base.filter(QueryRun.engine_id == engine_id)

    runs_by_day  = {r.day: r.total_runs  for r in runs_base.group_by("day").all()}
    cited_by_day = {r.day: r.cited_runs  for r in cited_base.group_by("day").all()}
    session.close()

    result = []
    for day, total in sorted(runs_by_day.items()):
        cited = cited_by_day.get(day, 0)
        result.append({
            "date": day,
            "citation_rate": round(cited / total, 4) if total else 0.0,
            "citations": cited,
            "runs": total,
        })
    return result


def top_queries(brand_id: int, days: int = 30, limit: int = 10) -> list[dict]:
    """Queries where the brand is cited most frequently."""
    session = get_session()
    start, end = _date_range(days)

    rows = (
        session.query(
            Query.text,
            Topic.name.label("topic"),
            func.count(Citation.id).label("citations"),
            func.count(distinct(QueryRun.id)).label("runs"),
        )
        .join(Citation, Citation.run_id == QueryRun.id)
        .join(Query, QueryRun.query_id == Query.id)
        .join(Topic, Query.topic_id == Topic.id)
        .filter(Citation.brand_id == brand_id, QueryRun.run_at.between(start, end))
        .group_by(Query.id)
        .order_by(func.count(Citation.id).desc())
        .limit(limit)
        .all()
    )
    session.close()

    return [
        {
            "query": r.text,
            "topic": r.topic,
            "citations": r.citations,
            "runs": r.runs,
            "rate": round(r.citations / r.runs, 3) if r.runs else 0,
        }
        for r in rows
    ]


def engine_breakdown(brand_id: int, days: int = 30) -> list[dict]:
    """Citation rate per AI engine for a brand."""
    session = get_session()
    start, end = _date_range(days)

    engines = session.query(AIEngine).all()
    results = []

    for engine in engines:
        total_runs = (
            session.query(func.count(distinct(QueryRun.id)))
            .filter(QueryRun.engine_id == engine.id, QueryRun.run_at.between(start, end))
            .scalar() or 0
        )
        cited_runs = (
            session.query(func.count(distinct(Citation.run_id)))
            .join(QueryRun)
            .filter(
                Citation.brand_id == brand_id,
                QueryRun.engine_id == engine.id,
                QueryRun.run_at.between(start, end),
            )
            .scalar() or 0
        )
        results.append({
            "engine": engine.name,
            "provider": engine.provider,
            "citation_rate": round(cited_runs / total_runs, 4) if total_runs else 0.0,
            "citations": cited_runs,
            "runs": total_runs,
        })

    session.close()
    return sorted(results, key=lambda x: x["citation_rate"], reverse=True)


def top_pages(brand_id: int, days: int = 30, limit: int = 15) -> list[dict]:
    """URLs cited most often for a brand, with citation count, query coverage, and avg position."""
    session = get_session()
    start, end = _date_range(days)

    rows = (
        session.query(
            Citation.source_url,
            func.count(Citation.id).label("citations"),
            func.count(distinct(QueryRun.query_id)).label("query_count"),
            func.count(distinct(QueryRun.engine_id)).label("engine_count"),
            func.avg(Citation.position).label("avg_position"),
        )
        .join(QueryRun, Citation.run_id == QueryRun.id)
        .filter(
            Citation.brand_id == brand_id,
            Citation.source_url.isnot(None),
            QueryRun.run_at.between(start, end),
        )
        .group_by(Citation.source_url)
        .order_by(func.count(Citation.id).desc())
        .limit(limit)
        .all()
    )

    # Total citations with a URL (for share calculation)
    total = (
        session.query(func.count(Citation.id))
        .join(QueryRun)
        .filter(
            Citation.brand_id == brand_id,
            Citation.source_url.isnot(None),
            QueryRun.run_at.between(start, end),
        )
        .scalar() or 1
    )

    session.close()

    return [
        {
            "url": r.source_url,
            "citations": r.citations,
            "share": round(r.citations / total * 100, 1),
            "query_count": r.query_count,
            "engine_count": r.engine_count,
            "avg_position": round(float(r.avg_position), 2) if r.avg_position else None,
        }
        for r in rows
    ]


def brand_overview(brand_id: int, days: int = 30) -> dict:
    """Top-level summary card for a brand."""
    rate = citation_rate(brand_id, days)
    sentiment = sentiment_breakdown(brand_id, days)
    position = avg_position(brand_id, days)
    total_cit = sum(sentiment.values())

    pos_pct = round(sentiment["positive"] / total_cit * 100) if total_cit else 0

    return {
        "citation_rate": rate,
        "citation_rate_pct": round(rate * 100, 1),
        "avg_position": position,
        "total_citations": total_cit,
        "sentiment": sentiment,
        "positive_pct": pos_pct,
    }


# ── Feature 1: Visibility Score ────────────────────────────────────────────────

def visibility_score(brand_id: int, days: int = 30) -> dict:
    """
    Aggregate 0-100 AEO health score combining citation rate, position, sentiment,
    and query coverage. Weights reflect revenue impact ordering.
    """
    session = get_session()
    start, end = _date_range(days)

    cr   = citation_rate(brand_id, days)
    pos  = avg_position(brand_id, days)
    sent = sentiment_breakdown(brand_id, days)

    cr_score  = cr * 100
    pos_score = max(0.0, 100.0 - (pos - 1) * 30) if pos else 0.0
    sent_total = sum(sent.values())
    sent_score = (sent["positive"] / sent_total * 100) if sent_total else 0.0

    # Meaningful coverage: queries where the brand is cited in >15% of runs (not just noise)
    COVERAGE_THRESHOLD = 0.15
    all_queries = session.query(Query.id).all()
    total_queries = len(all_queries) or 1
    meaningful_covered = 0
    for (qid,) in all_queries:
        runs = (
            session.query(func.count(distinct(QueryRun.id)))
            .filter(QueryRun.query_id == qid, QueryRun.run_at.between(start, end))
            .scalar() or 0
        )
        cited = (
            session.query(func.count(distinct(Citation.run_id)))
            .join(QueryRun)
            .filter(Citation.brand_id == brand_id, QueryRun.query_id == qid, QueryRun.run_at.between(start, end))
            .scalar() or 0
        )
        if runs and cited / runs >= COVERAGE_THRESHOLD:
            meaningful_covered += 1
    session.close()

    coverage_score = meaningful_covered / total_queries * 100

    score = (
        cr_score       * 0.40 +
        pos_score      * 0.25 +
        sent_score     * 0.20 +
        coverage_score * 0.15
    )

    return {
        "score": round(score, 1),
        "grade": "A" if score >= 80 else "B" if score >= 65 else "C" if score >= 50 else "D",
        "components": {
            "citation_rate":   round(cr_score, 1),
            "position":        round(pos_score, 1),
            "sentiment":       round(sent_score, 1),
            "query_coverage":  round(coverage_score, 1),
        },
        "query_coverage_pct": round(meaningful_covered / total_queries * 100, 1),
        "queries_covered":    meaningful_covered,
        "total_queries":      total_queries,
    }


# ── Feature 2: Content Gap Analysis ───────────────────────────────────────────

def content_gaps(brand_id: int, days: int = 30, limit: int = 25) -> list[dict]:
    """
    Queries where the brand's citation rate is weak (< 15%) but competitors are
    strong (> 20%). Sorted by competitor strength — biggest missed opportunities first.
    """
    BRAND_MAX_RATE = 0.15    # brand must be below this to qualify as a gap
    COMP_MIN_RATE  = 0.20    # competitors must be above this to confirm opportunity

    session = get_session()
    start, end = _date_range(days)

    brand_cit = (
        session.query(
            QueryRun.query_id.label("qid"),
            func.count(Citation.id).label("brand_cit"),
        )
        .join(Citation, Citation.run_id == QueryRun.id)
        .filter(Citation.brand_id == brand_id, QueryRun.run_at.between(start, end))
        .group_by(QueryRun.query_id)
        .subquery()
    )

    comp_cit = (
        session.query(
            QueryRun.query_id.label("qid"),
            func.count(Citation.id).label("comp_cit"),
        )
        .join(Citation, Citation.run_id == QueryRun.id)
        .filter(Citation.brand_id != brand_id, QueryRun.run_at.between(start, end))
        .group_by(QueryRun.query_id)
        .subquery()
    )

    total_runs_sq = (
        session.query(
            QueryRun.query_id.label("qid"),
            func.count(QueryRun.id).label("runs"),
        )
        .filter(QueryRun.run_at.between(start, end))
        .group_by(QueryRun.query_id)
        .subquery()
    )

    rows = (
        session.query(
            Query.text,
            Query.intent,
            Topic.name.label("topic"),
            func.coalesce(brand_cit.c.brand_cit, 0).label("brand_citations"),
            func.coalesce(comp_cit.c.comp_cit,   0).label("competitor_citations"),
            total_runs_sq.c.runs,
        )
        .join(total_runs_sq, Query.id == total_runs_sq.c.qid)
        .outerjoin(brand_cit, Query.id == brand_cit.c.qid)
        .outerjoin(comp_cit,  Query.id == comp_cit.c.qid)
        .join(Topic, Query.topic_id == Topic.id)
        .all()
    )
    session.close()

    gaps = []
    for r in rows:
        if not r.runs:
            continue
        brand_rate = r.brand_citations / r.runs
        comp_rate  = r.competitor_citations / r.runs
        if brand_rate < BRAND_MAX_RATE and comp_rate > COMP_MIN_RATE:
            gaps.append({
                "query":                r.text,
                "intent":               r.intent,
                "topic":                r.topic,
                "brand_citations":      r.brand_citations,
                "brand_rate":           round(brand_rate * 100, 1),
                "competitor_citations": r.competitor_citations,
                "runs":                 r.runs,
                "gap_score":            round(comp_rate * 100, 1),
            })

    gaps.sort(key=lambda g: g["gap_score"], reverse=True)
    return gaps[:limit]


# ── Feature 3: Recommendations ────────────────────────────────────────────────

def recommendations(brand_id: int, days: int = 30) -> list[dict]:
    """Rule-based content recommendations derived from gaps, pages, and sentiment data."""
    recs = []

    pages = top_pages(brand_id, days, limit=10)
    gaps  = content_gaps(brand_id, days, limit=20)
    sent  = sentiment_breakdown(brand_id, days)
    score = visibility_score(brand_id, days)

    def _path(url: str) -> str:
        try:
            from urllib.parse import urlparse
            return urlparse(url).path or url
        except Exception:
            return url

    # Position opportunity: high-volume pages not yet at position 1
    for page in pages[:5]:
        if page["avg_position"] and page["avg_position"] > 2.0 and page["citations"] > 20:
            recs.append({
                "priority": "high",
                "type":     "position_opportunity",
                "title":    f"Improve position on {_path(page['url'])}",
                "body":     (
                    f"Cited {page['citations']} times across {page['query_count']} queries "
                    f"but avg position is {page['avg_position']}. Add a structured FAQ section "
                    f"with direct question-answer pairs to compete for position 1."
                ),
                "url": page["url"],
            })

    # Engine gap: top pages missing from any tracked engine
    for page in pages[:3]:
        if page["engine_count"] < 4:
            missing = 4 - page["engine_count"]
            recs.append({
                "priority": "medium",
                "type":     "engine_gap",
                "title":    f"Not indexed by {missing} engine(s): {_path(page['url'])}",
                "body":     (
                    f"This page is only cited by {page['engine_count']} of 4 tracked engines. "
                    f"Check robots.txt, add JSON-LD structured data, and ensure the page is "
                    f"accessible to crawlers without JavaScript rendering."
                ),
                "url": page["url"],
            })

    # Commercial intent gaps (highest revenue impact)
    commercial_gaps = [g for g in gaps if g["intent"] == "commercial"][:4]
    for gap in commercial_gaps:
        recs.append({
            "priority": "high",
            "type":     "content_gap",
            "title":    f"Zero presence: \"{gap['query'][:65]}\"",
            "body":     (
                f"Competitors are cited {gap['competitor_citations']} times for this "
                f"commercial-intent query — your brand never appears. Create a dedicated "
                f"landing page or blog post answering this question directly."
            ),
            "query":  gap["query"],
            "intent": gap["intent"],
        })

    # Informational gaps (brand awareness)
    info_gaps = [g for g in gaps if g["intent"] == "informational"][:2]
    for gap in info_gaps:
        recs.append({
            "priority": "medium",
            "type":     "content_gap",
            "title":    f"Missing from informational query: \"{gap['query'][:65]}\"",
            "body":     (
                f"Competitors appear {gap['competitor_citations']} times. "
                f"An informational guide or explainer page would capture this traffic "
                f"and build authority for related commercial queries."
            ),
            "query":  gap["query"],
            "intent": gap["intent"],
        })

    # Negative sentiment spike
    total_sent = sum(sent.values())
    if total_sent and sent["negative"] / total_sent > 0.15:
        neg_pct = round(sent["negative"] / total_sent * 100)
        recs.append({
            "priority": "medium",
            "type":     "sentiment",
            "title":    f"Negative citations at {neg_pct}% — above healthy threshold",
            "body":     (
                f"AI engines are surfacing unfavorable content in {sent['negative']} citations. "
                f"Review the excerpts in Top Pages to identify which content angles trigger "
                f"negative framing, then publish counter-narratives or updated comparison pages."
            ),
        })

    # Single-page concentration risk
    if pages and pages[0]["share"] > 20:
        recs.append({
            "priority": "low",
            "type":     "concentration_risk",
            "title":    f"Citation concentration risk: {pages[0]['share']}% on one page",
            "body":     (
                f"Your top page drives {pages[0]['share']}% of all URL citations. "
                f"A single content update or de-indexing event would collapse citation volume. "
                f"Invest in optimizing 3–5 additional pages as citation sources."
            ),
            "url": pages[0]["url"],
        })

    # Low meaningful query coverage
    if score["query_coverage_pct"] < 70:
        recs.append({
            "priority": "low",
            "type":     "coverage",
            "title":    f"Narrow query coverage: {score['query_coverage_pct']}% of tracked queries",
            "body":     (
                f"Your brand appears in only {score['queries_covered']} of {score['total_queries']} "
                f"tracked queries. Broaden content to address more of the query landscape "
                f"in your category."
            ),
        })

    priority_order = {"high": 0, "medium": 1, "low": 2}
    recs.sort(key=lambda r: priority_order[r["priority"]])
    return recs


# ── Feature 4: Prompts Explorer ───────────────────────────────────────────────

def explore_query(query_text: str, engine_id: int | None = None, days: int = 30) -> dict:
    """
    Find seeded queries that match the input text and return the most recent
    citation results for each match. Falls back to keyword matching if no
    direct substring match is found.
    """
    session = get_session()
    start, end = _date_range(days)
    search = f"%{query_text.strip().lower()}%"

    matches = session.query(Query).filter(func.lower(Query.text).like(search)).limit(5).all()

    if not matches:
        words = [w for w in query_text.lower().split() if len(w) > 3]
        if words:
            matches = (
                session.query(Query)
                .filter(or_(*[func.lower(Query.text).like(f"%{w}%") for w in words[:4]]))
                .limit(5)
                .all()
            )

    results = []
    for query in matches:
        runs_q = (
            session.query(QueryRun)
            .filter(QueryRun.query_id == query.id, QueryRun.run_at.between(start, end))
        )
        if engine_id:
            runs_q = runs_q.filter(QueryRun.engine_id == engine_id)

        # One result per engine for richer output
        runs = runs_q.order_by(QueryRun.run_at.desc()).limit(4).all()
        for run in runs:
            engine = session.get(AIEngine, run.engine_id)
            cit_rows = (
                session.query(Citation, Brand)
                .join(Brand, Citation.brand_id == Brand.id)
                .filter(Citation.run_id == run.id)
                .order_by(Citation.position)
                .all()
            )
            results.append({
                "matched_query": query.text,
                "topic": session.get(Query, query.id).topic.name if query.topic_id else None,
                "engine": engine.name,
                "run_date": run.run_at.strftime("%Y-%m-%d"),
                "citations": [
                    {
                        "position":   c.position,
                        "brand":      b.name,
                        "sentiment":  c.sentiment,
                        "excerpt":    c.excerpt,
                        "source_url": c.source_url,
                    }
                    for c, b in cit_rows
                ],
            })

    session.close()

    # Deduplicate to one run per (query, engine) — most recent
    seen: set[tuple] = set()
    deduped = []
    for r in results:
        key = (r["matched_query"], r["engine"])
        if key not in seen:
            seen.add(key)
            deduped.append(r)

    return {
        "query":   query_text,
        "matched": len(deduped) > 0,
        "results": deduped,
    }


# ── Feature 5: Intent-weighted breakdown ──────────────────────────────────────

def citation_by_intent(brand_id: int, days: int = 30) -> list[dict]:
    """Citation rate broken down by query intent: commercial, informational, navigational."""
    session = get_session()
    start, end = _date_range(days)

    results = []
    for intent in ("commercial", "informational", "navigational"):
        total_runs = (
            session.query(func.count(distinct(QueryRun.id)))
            .join(Query, QueryRun.query_id == Query.id)
            .filter(Query.intent == intent, QueryRun.run_at.between(start, end))
            .scalar() or 0
        )
        cited_runs = (
            session.query(func.count(distinct(Citation.run_id)))
            .join(QueryRun, Citation.run_id == QueryRun.id)
            .join(Query,    QueryRun.query_id == Query.id)
            .filter(
                Citation.brand_id == brand_id,
                Query.intent      == intent,
                QueryRun.run_at.between(start, end),
            )
            .scalar() or 0
        )
        results.append({
            "intent":           intent,
            "citation_rate":    round(cited_runs / total_runs, 4) if total_runs else 0.0,
            "citation_rate_pct": round(cited_runs / total_runs * 100, 1) if total_runs else 0.0,
            "citations":        cited_runs,
            "runs":             total_runs,
        })

    session.close()
    return results
