import asyncio

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.database import Base
from backend.deep_research import DeepResearchClient
from backend.insight_engine import cluster_and_score_insights
from backend.models import Insight
from backend.reinforcement_loop import passes_hard_floor, rank_feed
from backend.research_corpora import redact_pii, register_corpus
from backend.research_orchestrator import create_research_job, create_triggered_research_job
from backend.research_playbooks import get_playbook, list_playbooks


def make_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine)()


def test_research_playbooks_include_core_jobs():
    playbooks = {item["playbook_id"] for item in list_playbooks()}

    assert {"user-wants", "voice-of-customer", "competitor-switching"}.issubset(playbooks)
    assert get_playbook("competitor-switching").cost_ceiling_usd == 7.0


def test_local_deep_research_plan_and_extraction():
    playbook = get_playbook("voice-of-customer")
    client = DeepResearchClient(force_local=True)

    plan = asyncio.run(client.create_plan(playbook, "mobile onboarding complaints"))
    report = asyncio.run(client.approve_and_run(playbook, plan.interaction_id))
    insights = asyncio.run(client.extract_insights(playbook, report.interaction_id, report.output_text, "job-1"))

    assert "Research plan" in plan.output_text
    assert report.citations
    assert insights[0]["source"] == "research"
    assert insights[0]["evidence_strength"] >= 0.6
    assert insights[0]["report_id"] == "job-1"


def test_research_job_creation_uses_playbook_metadata():
    db = make_db()

    job = create_research_job(db, playbook_id="user-wants", focus="playlist collaboration")

    assert job.playbook_id == "user-wants"
    assert job.research_job == "user_wants"
    assert job.status == "pending"
    assert job.cost_ceiling_usd == 3.0


def test_research_insight_passes_evidence_floor_and_ranks():
    db = make_db()
    raw = [
        {
            "title": "Users cite unclear pricing",
            "summary": "Multiple cited sources mention pricing confusion.",
            "group": "product-user-research",
            "skill": "competitor-switching",
            "source": "research",
            "evidence_strength": 0.82,
            "citations": [{"title": "Source", "url": "https://example.com"}],
            "recommended_actions": ["Review pricing comparison copy."],
            "direction": "neutral",
            "confidence": 0.8,
            "magnitude": {"value": 0.82, "unit": "evidence", "relative": 0.0},
            "business_impact": {"metric": "research_priority", "estimate_usd": 0.0, "horizon": "unknown"},
            "playbook_id": "competitor-switching",
            "research_job": "competitor_switching",
            "report_id": "job-1",
        }
    ]

    persisted = cluster_and_score_insights(db, raw, "job-1")
    assert persisted[0].source == "research"
    assert passes_hard_floor(persisted[0])

    feed = rank_feed(db.query(Insight).all(), "team-1", db, exploration_budget=0.0)
    assert feed[0]["source"] == "research"
    assert feed[0]["citations"][0]["url"] == "https://example.com"


def test_corpus_registration_redacts_pii():
    db = make_db()

    corpus = register_corpus(
        db,
        name="Support tickets",
        source_type="support_tickets",
        sample_text="Email user@example.com or call 415-555-1212",
    )

    assert corpus.redaction_status == "redacted"
    preview = corpus.metadata_json["sample_preview_redacted"]
    assert "user@example.com" not in preview
    assert "415-555-1212" not in preview
    assert "[REDACTED_EMAIL]" in redact_pii("user@example.com")


def test_triggered_research_job_links_origin_context():
    db = make_db()
    db.add(
        Insight(
            insight_id="ins-1",
            title="D7 retention dropped",
            summary="Paid cohort retention fell.",
            group_key="retention-churn",
            skill_key="cohort-retention-curves",
            run_id="run-1",
        )
    )
    db.commit()

    job = create_triggered_research_job(db, "ins-1")

    assert job.origin_insight_id == "ins-1"
    assert job.playbook_id == "voice-of-customer"
    assert "D7 retention dropped" in job.focus
