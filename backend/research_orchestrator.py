import asyncio
import datetime
import uuid
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from .database import SessionLocal
from .deep_research import DeepResearchClient
from .insight_engine import cluster_and_score_insights
from .models import Insight, InsightLink, ResearchJob, ResearchSchedule
from .research_playbooks import get_playbook


active_research_streams: Dict[str, List[asyncio.Queue]] = {}


def create_research_job(
    db: Session,
    *,
    playbook_id: str,
    focus: str,
    context: Optional[Dict[str, Any]] = None,
    origin_insight_id: Optional[str] = None,
    schedule_id: Optional[str] = None,
) -> ResearchJob:
    playbook = get_playbook(playbook_id)
    job = ResearchJob(
        job_id=str(uuid.uuid4()),
        playbook_id=playbook.playbook_id,
        research_job=playbook.research_job,
        focus=focus,
        context=context or {},
        phase="planning",
        status="pending",
        cost_ceiling_usd=playbook.cost_ceiling_usd,
        interaction_ids=[],
        citations=[],
        event_log=[],
        origin_insight_id=origin_insight_id,
        schedule_id=schedule_id,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


async def notify_research_event(job_id: str, event_type: str, message: str, payload: Optional[Dict[str, Any]] = None):
    timestamp = datetime.datetime.utcnow().isoformat()
    event = {
        "id": f"{timestamp}-{event_type}",
        "type": event_type,
        "message": message,
        "payload": payload or {},
        "timestamp": timestamp,
    }

    db = SessionLocal()
    try:
        job = db.query(ResearchJob).filter(ResearchJob.job_id == job_id).first()
        if job:
            log = list(job.event_log or [])
            log.append(event)
            job.event_log = log[-250:]
            job.last_event_id = event["id"]
            job.updated_at = datetime.datetime.utcnow()
            db.commit()
    finally:
        db.close()

    for queue in active_research_streams.get(job_id, []):
        await queue.put(event)


async def generate_research_plan(job_id: str):
    db = SessionLocal()
    try:
        job = db.query(ResearchJob).filter(ResearchJob.job_id == job_id).first()
        if not job:
            return
        job.status = "running"
        job.phase = "planning"
        job.updated_at = datetime.datetime.utcnow()
        db.commit()

        await notify_research_event(job_id, "status", "Creating collaborative research plan.")
        playbook = get_playbook(job.playbook_id)
        record = await DeepResearchClient().create_plan(playbook, job.focus, job.context)

        job = db.query(ResearchJob).filter(ResearchJob.job_id == job_id).first()
        job.plan_text = record.output_text
        job.plan_interaction_id = record.interaction_id
        job.interaction_ids = _append_id(job.interaction_ids, record.interaction_id)
        job.phase = "awaiting_approval"
        job.status = "awaiting_approval"
        job.updated_at = datetime.datetime.utcnow()
        db.commit()
        await notify_research_event(job_id, "plan", "Research plan is ready for review.", {"plan_text": record.output_text})
    except Exception as exc:
        await _fail_job(job_id, exc)
    finally:
        db.close()


async def refine_research_plan(job_id: str, refinement: str):
    db = SessionLocal()
    try:
        job = db.query(ResearchJob).filter(ResearchJob.job_id == job_id).first()
        if not job:
            return
        if not job.plan_interaction_id:
            raise ValueError("Research job has no plan interaction to refine.")

        job.status = "running"
        job.phase = "planning"
        db.commit()

        await notify_research_event(job_id, "status", "Refining collaborative research plan.")
        playbook = get_playbook(job.playbook_id)
        record = await DeepResearchClient().refine_plan(playbook, job.plan_interaction_id, refinement)

        job = db.query(ResearchJob).filter(ResearchJob.job_id == job_id).first()
        job.plan_text = record.output_text
        job.plan_interaction_id = record.interaction_id
        job.interaction_ids = _append_id(job.interaction_ids, record.interaction_id)
        job.phase = "awaiting_approval"
        job.status = "awaiting_approval"
        job.updated_at = datetime.datetime.utcnow()
        db.commit()
        await notify_research_event(job_id, "plan", "Refined research plan is ready.", {"plan_text": record.output_text})
    except Exception as exc:
        await _fail_job(job_id, exc)
    finally:
        db.close()


async def approve_and_run_research(job_id: str):
    db = SessionLocal()
    try:
        job = db.query(ResearchJob).filter(ResearchJob.job_id == job_id).first()
        if not job:
            return
        if not job.plan_interaction_id:
            raise ValueError("Research job must have an approved plan before execution.")

        job.status = "running"
        job.phase = "running"
        job.updated_at = datetime.datetime.utcnow()
        db.commit()

        await notify_research_event(job_id, "status", "Running approved Deep Research job.")
        playbook = get_playbook(job.playbook_id)
        record = await DeepResearchClient().approve_and_run(playbook, job.plan_interaction_id)
        if record.status == "in_progress":
            record = await DeepResearchClient().poll_until_complete(record.interaction_id)

        job = db.query(ResearchJob).filter(ResearchJob.job_id == job_id).first()
        job.report_text = record.output_text or job.report_text
        job.report_interaction_id = record.interaction_id
        job.interaction_ids = _append_id(job.interaction_ids, record.interaction_id)
        job.citations = record.citations
        job.phase = "extracting"
        job.updated_at = datetime.datetime.utcnow()
        db.commit()
        await notify_research_event(job_id, "report", "Research report completed. Extracting insights.", {"citations": record.citations})

        insights = await DeepResearchClient().extract_insights(
            playbook,
            job.report_interaction_id,
            job.report_text or "",
            report_id=job.job_id,
        )
        for insight in insights:
            insight["research_job_id"] = job.job_id
            insight["origin_insight_id"] = job.origin_insight_id

        persisted = cluster_and_score_insights(db, insights, job.job_id)
        extracted_ids = [ins.insight_id for ins in persisted]

        if job.origin_insight_id:
            for target_id in extracted_ids:
                db.add(
                    InsightLink(
                        source_insight_id=job.origin_insight_id,
                        target_insight_id=target_id,
                        research_job_id=job.job_id,
                        relationship="explains",
                    )
                )

        job = db.query(ResearchJob).filter(ResearchJob.job_id == job_id).first()
        job.extracted_insight_ids = extracted_ids
        job.phase = "completed"
        job.status = "completed"
        job.completed_at = datetime.datetime.utcnow()
        job.updated_at = datetime.datetime.utcnow()
        db.commit()

        if job.schedule_id:
            _update_schedule_after_run(db, job)

        await notify_research_event(job_id, "completed", "RESEARCH_COMPLETED", {"insight_ids": extracted_ids})
    except Exception as exc:
        await _fail_job(job_id, exc)
    finally:
        db.close()


async def create_research_followup(job_id: str, question: str) -> Dict[str, Any]:
    db = SessionLocal()
    try:
        job = db.query(ResearchJob).filter(ResearchJob.job_id == job_id).first()
        if not job:
            raise ValueError("Research job not found.")
        record = await DeepResearchClient().follow_up(job.report_interaction_id, question)
        job.interaction_ids = _append_id(job.interaction_ids, record.interaction_id)
        job.updated_at = datetime.datetime.utcnow()
        db.commit()
        await notify_research_event(job_id, "followup", "Follow-up response received.", {"response": record.output_text})
        return {"interaction_id": record.interaction_id, "response": record.output_text}
    finally:
        db.close()


def create_triggered_research_job(db: Session, insight_id: str) -> ResearchJob:
    insight = db.query(Insight).filter(Insight.insight_id == insight_id).first()
    if not insight:
        raise ValueError("Insight not found.")
    focus = (
        f"Investigate likely qualitative causes for this product insight: {insight.title}. "
        f"Summary: {insight.summary}. Segment: {insight.segment or 'all users'}. "
        f"Metric: {insight.metric or 'unknown'}."
    )
    context = {
        "origin_title": insight.title,
        "origin_summary": insight.summary,
        "segment": insight.segment,
        "metric": insight.metric,
        "data_window_start": insight.data_window_start,
        "data_window_end": insight.data_window_end,
    }
    return create_research_job(
        db,
        playbook_id="voice-of-customer",
        focus=focus,
        context=context,
        origin_insight_id=insight_id,
    )


def _append_id(existing: Optional[List[str]], value: Optional[str]) -> List[str]:
    values = list(existing or [])
    if value:
        values.append(value)
    return values


async def _fail_job(job_id: str, exc: Exception):
    db = SessionLocal()
    try:
        job = db.query(ResearchJob).filter(ResearchJob.job_id == job_id).first()
        if job:
            job.status = "failed"
            job.phase = "failed"
            job.error = str(exc)
            job.completed_at = datetime.datetime.utcnow()
            job.updated_at = datetime.datetime.utcnow()
            db.commit()
    finally:
        db.close()
    await notify_research_event(job_id, "failed", f"RESEARCH_FAILED: {exc}")


def _update_schedule_after_run(db: Session, job: ResearchJob):
    schedule = db.query(ResearchSchedule).filter(ResearchSchedule.schedule_id == job.schedule_id).first()
    if not schedule:
        return
    schedule.last_job_id = job.job_id
    schedule.last_run_at = datetime.datetime.utcnow()
    schedule.prior_summary = (job.report_text or "")[:4000]
    if schedule.cadence == "monthly":
        schedule.next_run_at = datetime.datetime.utcnow() + datetime.timedelta(days=30)
    else:
        schedule.next_run_at = datetime.datetime.utcnow() + datetime.timedelta(days=7)
    db.commit()
