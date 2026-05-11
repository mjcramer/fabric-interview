from contextlib import asynccontextmanager
from fastapi import FastAPI, Query, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
import os

from .models import Brand, Topic, AIEngine, get_session, init_db
from . import analytics


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()  # creates tables if they don't exist; safe to call repeatedly
    yield


app = FastAPI(title="AEO Platform", version="0.1.0", lifespan=lifespan)

# ── Helpers ────────────────────────────────────────────────────────────────────

def _get_brand(session: Session, brand_id: int) -> Brand:
    brand = session.get(Brand, brand_id)
    if not brand:
        raise HTTPException(status_code=404, detail=f"Brand {brand_id} not found")
    return brand


# ── Reference data ─────────────────────────────────────────────────────────────

@app.get("/api/brands")
def list_brands():
    session = get_session()
    brands = session.query(Brand).order_by(Brand.name).all()
    result = [{"id": b.id, "name": b.name, "domain": b.domain, "category": b.category} for b in brands]
    session.close()
    return result


@app.get("/api/topics")
def list_topics():
    session = get_session()
    topics = session.query(Topic).order_by(Topic.name).all()
    result = [{"id": t.id, "name": t.name, "category": t.category} for t in topics]
    session.close()
    return result


@app.get("/api/engines")
def list_engines():
    session = get_session()
    engines = session.query(AIEngine).order_by(AIEngine.name).all()
    result = [{"id": e.id, "name": e.name, "provider": e.provider} for e in engines]
    session.close()
    return result


# ── Brand analytics ────────────────────────────────────────────────────────────

@app.get("/api/brands/{brand_id}/overview")
def brand_overview(
    brand_id: int,
    days: int = Query(default=30, ge=1, le=365),
):
    return analytics.brand_overview(brand_id, days)


@app.get("/api/brands/{brand_id}/trend")
def brand_trend(
    brand_id: int,
    days: int = Query(default=30, ge=7, le=365),
    engine_id: int | None = Query(default=None),
):
    return analytics.citation_trend(brand_id, days, engine_id)


@app.get("/api/brands/{brand_id}/engines")
def brand_engines(
    brand_id: int,
    days: int = Query(default=30, ge=1, le=365),
):
    return analytics.engine_breakdown(brand_id, days)


@app.get("/api/brands/{brand_id}/top-queries")
def brand_top_queries(
    brand_id: int,
    days: int = Query(default=30, ge=1, le=365),
    limit: int = Query(default=10, ge=1, le=50),
):
    return analytics.top_queries(brand_id, days, limit)


@app.get("/api/brands/{brand_id}/sentiment")
def brand_sentiment(
    brand_id: int,
    days: int = Query(default=30, ge=1, le=365),
):
    return analytics.sentiment_breakdown(brand_id, days)


@app.get("/api/brands/{brand_id}/top-pages")
def brand_top_pages(
    brand_id: int,
    days: int = Query(default=30, ge=1, le=365),
    limit: int = Query(default=15, ge=1, le=50),
):
    return analytics.top_pages(brand_id, days, limit)


@app.get("/api/brands/{brand_id}/visibility-score")
def brand_visibility_score(
    brand_id: int,
    days: int = Query(default=30, ge=1, le=365),
):
    return analytics.visibility_score(brand_id, days)


@app.get("/api/brands/{brand_id}/gaps")
def brand_gaps(
    brand_id: int,
    days: int = Query(default=30, ge=1, le=365),
    limit: int = Query(default=25, ge=1, le=100),
):
    return analytics.content_gaps(brand_id, days, limit)


@app.get("/api/brands/{brand_id}/recommendations")
def brand_recommendations(
    brand_id: int,
    days: int = Query(default=30, ge=1, le=365),
):
    return analytics.recommendations(brand_id, days)


@app.get("/api/brands/{brand_id}/by-intent")
def brand_by_intent(
    brand_id: int,
    days: int = Query(default=30, ge=1, le=365),
):
    return analytics.citation_by_intent(brand_id, days)


@app.get("/api/explore")
def explore(
    q: str = Query(..., min_length=2),
    engine_id: int | None = Query(default=None),
    days: int = Query(default=30, ge=1, le=365),
):
    return analytics.explore_query(q, engine_id, days)


# ── Topic analytics ────────────────────────────────────────────────────────────

@app.get("/api/topics/{topic_id}/share-of-voice")
def topic_share_of_voice(
    topic_id: int,
    days: int = Query(default=30, ge=1, le=365),
    engine_id: int | None = Query(default=None),
):
    return analytics.share_of_voice(topic_id, days, engine_id)


# ── Dashboard ──────────────────────────────────────────────────────────────────

static_dir = os.path.join(os.path.dirname(__file__), "static")
app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.get("/")
def dashboard():
    return FileResponse(os.path.join(static_dir, "index.html"))
