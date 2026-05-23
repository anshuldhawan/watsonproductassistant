import os
import uuid
import json
import asyncio
import datetime
from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional

from .env import load_project_env

load_project_env()

from .database import engine, Base, get_db, ensure_runtime_schema, SessionLocal
from .models import AnalysisDefinition, Run, Insight, KPIDefinition, ResearchJob, ResearchSchedule, ResearchCorpus
from .schemas import (
    RunCreate,
    RunSchema,
    InsightSchema,
    KPIDefinitionSchema,
    FeedbackUpdate,
    ResearchCorpusCreate,
    ResearchCorpusSchema,
    ResearchFollowUpCreate,
    ResearchJobCreate,
    ResearchJobRefine,
    ResearchJobSchema,
    ResearchScheduleCreate,
    ResearchScheduleSchema,
)
from .seed import seed_database
from .gemini_agents import resolve_gemini_mode
from .research_playbooks import list_playbooks, get_playbook
from .research_corpora import register_corpus
from .research_orchestrator import (
    active_research_streams,
    approve_and_run_research,
    create_research_followup,
    create_research_job,
    create_triggered_research_job,
    generate_research_plan,
    refine_research_plan,
)

# Create tables
Base.metadata.create_all(bind=engine)
ensure_runtime_schema()

app = FastAPI(title="Watson: Automated Product Analyst API", version="1.0.0")

# Mount static and templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Enable CORS for frontend development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

# Initialize database on startup
@app.on_event("startup")
def startup_event():
    db = next(get_db())
    seed_database(db)

@app.get("/api/catalog")
def get_catalog(db: Session = Depends(get_db)):
    definitions = db.query(AnalysisDefinition).all()
    # Group by group_key
    groups = {}
    for d in definitions:
        g_key = d.group_key
        if g_key not in groups:
            groups[g_key] = {
                "key": g_key,
                "name": d.group_name,
                "agent_id": d.agent_id,
                "analyses": []
            }
        groups[g_key]["analyses"].append({
            "key": d.key,
            "name": d.name,
            "description": d.description,
            "default_config": d.default_config
        })
    return list(groups.values())

# We will import these from corresponding modules in next tasks
from .orchestrator import run_orchestrator_task, active_streams

@app.post("/api/runs", response_model=RunSchema)
def create_run(run_data: RunCreate, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    new_run_id = str(uuid.uuid4())
    execution_mode = resolve_gemini_mode(run_data.config)
    db_run = Run(
        run_id=new_run_id,
        type=run_data.type,
        target_id=run_data.target_id,
        status="pending",
        execution_mode=execution_mode,
        logs="[System] Initializing run task...\n"
    )
    db.add(db_run)
    db.commit()
    db.refresh(db_run)
    
    # Run the orchestrator in the background
    background_tasks.add_task(run_orchestrator_task, new_run_id, run_data.type, run_data.target_id, run_data.config)
    
    return db_run

@app.get("/api/runs", response_model=List[RunSchema])
def list_runs(db: Session = Depends(get_db)):
    return db.query(Run).order_by(Run.created_at.desc()).all()

@app.get("/api/runs/{run_id}", response_model=RunSchema)
def get_run(run_id: str, db: Session = Depends(get_db)):
    db_run = db.query(Run).filter(Run.run_id == run_id).first()
    if not db_run:
        raise HTTPException(status_code=404, detail="Run not found")
    return db_run

@app.get("/api/runs/{run_id}/stream")
async def stream_run_logs(run_id: str):
    """
    Server-Sent Events (SSE) endpoint to stream live logs and reasoning steps from active runs.
    """
    async def log_generator():
        # Register a queue for this client stream
        queue = asyncio.Queue()
        if run_id not in active_streams:
            active_streams[run_id] = []
        active_streams[run_id].append(queue)
        
        try:
            # Send initial message
            yield f"data: [System] Connected to live run stream.\n\n"
            while True:
                # Get log updates
                log_msg = await queue.get()
                yield f"data: {log_msg}\n\n"
                if "RUN_COMPLETED" in log_msg or "RUN_FAILED" in log_msg:
                    break
        except asyncio.CancelledError:
            pass
        finally:
            if run_id in active_streams and queue in active_streams[run_id]:
                active_streams[run_id].remove(queue)
                if not active_streams[run_id]:
                    del active_streams[run_id]

    return StreamingResponse(log_generator(), media_type="text/event-stream")

@app.get("/api/insights")
def list_insights(team_id: str = "team-1", db: Session = Depends(get_db)):
    # Fetch insights and dynamically rank them using the Bandit policy
    from .reinforcement_loop import rank_feed
    candidates = db.query(Insight).all()
    ranked = rank_feed(candidates, team_id, db)
    return ranked

@app.post("/api/insights/{insight_id}/feedback", response_model=InsightSchema)
def submit_feedback(insight_id: str, feedback_data: FeedbackUpdate, db: Session = Depends(get_db)):
    db_insight = db.query(Insight).filter(Insight.insight_id == insight_id).first()
    if not db_insight:
        raise HTTPException(status_code=404, detail="Insight not found")
    
    # Map old binary UI feedback to the new taxonomy if needed
    signal = feedback_data.signal_type or feedback_data.feedback_status
    if signal == "not-useful":
        signal = "not_important"
    elif signal == "acted-on":
        signal = "acted_on"
        
    # Route the feedback through our learning system
    from .reinforcement_loop import handle_feedback_routing
    reward, is_review = handle_feedback_routing(
        db=db,
        insight_id=insight_id,
        signal_type=signal,
        user_id=feedback_data.user_id or "user-1",
        team_id=feedback_data.team_id or "team-1",
        user_comment=feedback_data.user_comment
    )
    
    db.commit()
    db.refresh(db_insight)
    return db_insight

@app.get("/api/kpis", response_model=List[KPIDefinitionSchema])
def list_kpis(db: Session = Depends(get_db)):
    return db.query(KPIDefinition).all()

@app.post("/api/kpis", response_model=KPIDefinitionSchema)
def create_or_update_kpi(kpi_data: Dict[str, Any], db: Session = Depends(get_db)):
    metric = kpi_data.get("metric")
    if not metric:
        raise HTTPException(status_code=400, detail="Metric identifier is required")
        
    db_kpi = db.query(KPIDefinition).filter(KPIDefinition.metric == metric).first()
    if db_kpi:
        # Update existing KPI
        for k, v in kpi_data.items():
            setattr(db_kpi, k, v)
    else:
        # Create new KPI
        db_kpi = KPIDefinition(**kpi_data)
        db.add(db_kpi)
        
    db.commit()
    db.refresh(db_kpi)
    return db_kpi


# ==========================================
# PRODUCT & USER RESEARCH
# ==========================================

@app.get("/api/research/playbooks")
def get_research_playbooks():
    return list_playbooks()


@app.get("/api/research/jobs", response_model=List[ResearchJobSchema])
def list_research_jobs(db: Session = Depends(get_db)):
    return db.query(ResearchJob).order_by(ResearchJob.created_at.desc()).all()


@app.post("/api/research/jobs", response_model=ResearchJobSchema)
def submit_research_job(
    payload: ResearchJobCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    try:
        job = create_research_job(
            db,
            playbook_id=payload.playbook_id,
            focus=payload.focus,
            context=payload.context,
            origin_insight_id=payload.origin_insight_id,
            schedule_id=payload.schedule_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    background_tasks.add_task(generate_research_plan, job.job_id)
    return job


@app.get("/api/research/jobs/{job_id}", response_model=ResearchJobSchema)
def get_research_job(job_id: str, db: Session = Depends(get_db)):
    job = db.query(ResearchJob).filter(ResearchJob.job_id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Research job not found")
    return job


@app.post("/api/research/jobs/{job_id}/refine", response_model=ResearchJobSchema)
def refine_research_job_plan(
    job_id: str,
    payload: ResearchJobRefine,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    job = db.query(ResearchJob).filter(ResearchJob.job_id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Research job not found")
    background_tasks.add_task(refine_research_plan, job_id, payload.refinement)
    db.refresh(job)
    return job


@app.post("/api/research/jobs/{job_id}/approve", response_model=ResearchJobSchema)
def approve_research_job(
    job_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    job = db.query(ResearchJob).filter(ResearchJob.job_id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Research job not found")
    background_tasks.add_task(approve_and_run_research, job_id)
    return job


@app.get("/api/research/jobs/{job_id}/report")
def get_research_report(job_id: str, db: Session = Depends(get_db)):
    job = db.query(ResearchJob).filter(ResearchJob.job_id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Research job not found")
    return {
        "job_id": job.job_id,
        "playbook_id": job.playbook_id,
        "report_text": job.report_text,
        "citations": job.citations or [],
        "extracted_insight_ids": job.extracted_insight_ids or [],
    }


@app.get("/api/research/jobs/{job_id}/stream")
async def stream_research_job(job_id: str, last_event_id: Optional[str] = None):
    async def event_generator():
        queue = asyncio.Queue()
        active_research_streams.setdefault(job_id, []).append(queue)
        try:
            yield "event: connected\ndata: {}\n\n"
            db = SessionLocal()
            try:
                job = db.query(ResearchJob).filter(ResearchJob.job_id == job_id).first()
                events = job.event_log if job else []
                replay = False if last_event_id else True
                for event in events or []:
                    if not replay and event.get("id") == last_event_id:
                        replay = True
                        continue
                    if replay:
                        yield f"id: {event.get('id')}\nevent: {event.get('type', 'message')}\ndata: {json.dumps(event)}\n\n"
            finally:
                db.close()

            while True:
                event = await queue.get()
                yield f"id: {event.get('id')}\nevent: {event.get('type', 'message')}\ndata: {json.dumps(event)}\n\n"
                if event.get("type") in {"completed", "failed"}:
                    break
        except asyncio.CancelledError:
            pass
        finally:
            queues = active_research_streams.get(job_id, [])
            if queue in queues:
                queues.remove(queue)
            if not queues and job_id in active_research_streams:
                del active_research_streams[job_id]

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.post("/api/research/jobs/{job_id}/followup")
async def create_research_job_followup(job_id: str, payload: ResearchFollowUpCreate):
    try:
        return await create_research_followup(job_id, payload.question)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@app.post("/api/insights/{insight_id}/research-why", response_model=ResearchJobSchema)
def trigger_research_why(
    insight_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    try:
        job = create_triggered_research_job(db, insight_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    background_tasks.add_task(generate_research_plan, job.job_id)
    return job


@app.get("/api/research/corpora", response_model=List[ResearchCorpusSchema])
def list_research_corpora(db: Session = Depends(get_db)):
    return db.query(ResearchCorpus).order_by(ResearchCorpus.created_at.desc()).all()


@app.post("/api/research/corpora", response_model=ResearchCorpusSchema)
def create_research_corpus(payload: ResearchCorpusCreate, db: Session = Depends(get_db)):
    return register_corpus(
        db,
        name=payload.name,
        source_type=payload.source_type,
        file_search_store=payload.file_search_store,
        sample_text=payload.sample_text,
        metadata=payload.metadata,
    )


@app.get("/api/research/schedules", response_model=List[ResearchScheduleSchema])
def list_research_schedules(db: Session = Depends(get_db)):
    return db.query(ResearchSchedule).order_by(ResearchSchedule.created_at.desc()).all()


@app.post("/api/research/schedules", response_model=ResearchScheduleSchema)
def create_research_schedule(payload: ResearchScheduleCreate, db: Session = Depends(get_db)):
    try:
        playbook = get_playbook(payload.playbook_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    now = datetime.datetime.utcnow()
    schedule = ResearchSchedule(
        schedule_id=str(uuid.uuid4()),
        playbook_id=playbook.playbook_id,
        cadence=payload.cadence,
        focus=payload.focus,
        enabled=payload.enabled,
        next_run_at=now + datetime.timedelta(days=30 if payload.cadence == "monthly" else 7),
    )
    db.add(schedule)
    db.commit()
    db.refresh(schedule)
    return schedule


@app.post("/api/research/schedules/{schedule_id}/run", response_model=ResearchJobSchema)
def run_research_schedule_now(
    schedule_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    schedule = db.query(ResearchSchedule).filter(ResearchSchedule.schedule_id == schedule_id).first()
    if not schedule:
        raise HTTPException(status_code=404, detail="Research schedule not found")
    context = {"prior_summary": schedule.prior_summary} if schedule.prior_summary else {}
    job = create_research_job(
        db,
        playbook_id=schedule.playbook_id,
        focus=schedule.focus,
        context=context,
        schedule_id=schedule.schedule_id,
    )
    background_tasks.add_task(generate_research_plan, job.job_id)
    return job


# ==========================================
# ADMIN & SYSTEM REINFORCEMENT CONTROLS
# ==========================================

import datetime
from .reinforcement_loop import (
    run_daily_batch_refit,
    run_weekly_l2_threshold_controller,
    run_valence_parity_audit,
    get_or_create_threshold_state,
    PRIOR_WEIGHTS,
    FEATURE_NAMES
)
from .models import PolicyVersion, ThresholdState, MethodologyReview, FeedbackEvent, SurfacingRecord

@app.get("/api/admin/status")
def get_admin_status(db: Session = Depends(get_db)):
    # 1. Active Policy
    active_policy = db.query(PolicyVersion).filter(PolicyVersion.status == "active").first()
    
    # 2. Total feedbacks and surfacing records
    feedback_count = db.query(FeedbackEvent).count()
    surfacing_count = db.query(SurfacingRecord).count()
    review_count = db.query(MethodologyReview).filter(MethodologyReview.is_reviewed == False).count()

    # 3. Valence parity
    valence_parity = run_valence_parity_audit(db)

    return {
        "active_policy_version": active_policy.version if active_policy else "v1_prior",
        "weights": active_policy.parameters.get("weights", PRIOR_WEIGHTS) if active_policy else PRIOR_WEIGHTS,
        "feature_names": FEATURE_NAMES,
        "ope_score": active_policy.ope_score if active_policy else 1.0,
        "valence_parity_score": valence_parity,
        "feedback_count": feedback_count,
        "surfacing_count": surfacing_count,
        "unreviewed_methodology_reviews_count": review_count
    }


@app.post("/api/admin/refit")
def trigger_policy_refit(db: Session = Depends(get_db)):
    policy = run_daily_batch_refit(db)
    return {
        "status": "success",
        "version": policy.version,
        "policy_status": policy.status,
        "ope_score": policy.ope_score,
        "valence_parity_score": policy.valence_parity_score
    }


@app.get("/api/admin/thresholds")
def list_skill_thresholds(db: Session = Depends(get_db)):
    # Ensure threshold records exist for seeded analysis keys
    from .seed import ANALYSIS_CATALOG
    for group in ANALYSIS_CATALOG:
        for skill in group["skills"]:
            get_or_create_threshold_state(db, skill["key"])
    
    return db.query(ThresholdState).all()


@app.post("/api/admin/thresholds/update")
def update_thresholds_manually(payload: Dict[str, Any], db: Session = Depends(get_db)):
    skill_key = payload.get("skill_key")
    mag_val = payload.get("current_magnitude_threshold")
    conf_val = payload.get("current_confidence_threshold")

    if not skill_key:
        raise HTTPException(status_code=400, detail="skill_key is required")

    state = db.query(ThresholdState).filter(ThresholdState.skill_key == skill_key).first()
    if not state:
        raise HTTPException(status_code=404, detail="Threshold state not found")

    if mag_val is not None:
        state.current_magnitude_threshold = float(mag_val)
    if conf_val is not None:
        state.current_confidence_threshold = float(conf_val)

    state.last_updated = datetime.datetime.utcnow()
    db.commit()
    db.refresh(state)
    return state


@app.post("/api/admin/thresholds/auto-adjust")
def trigger_l2_threshold_auto_adjust(db: Session = Depends(get_db)):
    run_weekly_l2_threshold_controller(db)
    return {"status": "success", "message": "L2 skill thresholds adjusted based on aggregate feedback statistics."}


@app.get("/api/admin/reviews")
def list_methodology_reviews(db: Session = Depends(get_db)):
    reviews = db.query(MethodologyReview).all()
    results = []
    for r in reviews:
        insight = db.query(Insight).filter(Insight.insight_id == r.insight_id).first()
        results.append({
            "id": r.id,
            "insight_id": r.insight_id,
            "skill_key": r.skill_key,
            "user_comment": r.user_comment,
            "is_reviewed": r.is_reviewed,
            "created_at": r.created_at,
            "insight_title": insight.title if insight else "Unknown Insight"
        })
    return results


@app.post("/api/admin/reviews/{review_id}/resolve")
def resolve_methodology_review(review_id: int, payload: Dict[str, Any], db: Session = Depends(get_db)):
    review = db.query(MethodologyReview).filter(MethodologyReview.id == review_id).first()
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")

    review.is_reviewed = True
    
    action = payload.get("action", "dismiss")  # 'dismiss' or 'correct'
    
    insight = db.query(Insight).filter(Insight.insight_id == review.insight_id).first()
    if insight and action == "correct":
        insight.feedback_status = "pending"  # Reset status

    db.commit()
    return {"status": "success", "message": f"Methodology disagreement resolved with action: {action}."}
