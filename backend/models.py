import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, Text, JSON, Boolean, ForeignKey
from .database import Base

class AnalysisDefinition(Base):
    __tablename__ = "analysis_definitions"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    group_key = Column(String, index=True, nullable=False)
    group_name = Column(String, nullable=False)
    agent_id = Column(String, nullable=False)
    default_config = Column(JSON, nullable=True)

class Run(Base):
    __tablename__ = "runs"

    id = Column(Integer, primary_key=True, index=True)
    run_id = Column(String, unique=True, index=True, nullable=False)
    type = Column(String, nullable=False) # "single", "group", "monitoring"
    target_id = Column(String, nullable=False) # key of the analysis or group
    status = Column(String, default="pending", nullable=False) # "pending", "running", "completed", "failed"
    logs = Column(Text, default="", nullable=True)
    execution_mode = Column(String, default="local", nullable=False) # "local" or "gemini"
    gemini_interaction_ids = Column(JSON, nullable=True)
    gemini_environment_id = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    completed_at = Column(DateTime, nullable=True)

class Insight(Base):
    __tablename__ = "insights"

    id = Column(Integer, primary_key=True, index=True)
    insight_id = Column(String, unique=True, index=True, nullable=False)
    title = Column(String, nullable=False)
    summary = Column(Text, nullable=False)
    group_key = Column(String, index=True, nullable=False)
    skill_key = Column(String, index=True, nullable=False)
    metric = Column(String, nullable=True)
    direction = Column(String, nullable=True) # "up", "down", "neutral"
    magnitude_value = Column(Float, nullable=True)
    magnitude_unit = Column(String, nullable=True)
    magnitude_relative = Column(Float, nullable=True)
    confidence = Column(Float, nullable=True)
    stat_test = Column(String, nullable=True)
    segment = Column(String, nullable=True)
    business_impact_metric = Column(String, nullable=True)
    business_impact_value = Column(Float, nullable=True)
    business_impact_horizon = Column(String, nullable=True)
    recommended_actions = Column(JSON, nullable=True) # List[str]
    artifacts = Column(JSON, nullable=True) # List[str]
    data_window_start = Column(String, nullable=True)
    data_window_end = Column(String, nullable=True)
    attention_score = Column(Float, default=0.0, nullable=False)
    cluster_id = Column(String, index=True, nullable=True) # For clustering
    feedback_status = Column(String, default="pending", nullable=False) # "pending", "useful", "not-useful", "acted-on"
    run_id = Column(String, nullable=False)
    source = Column(String, default="analysis", nullable=False) # "analysis" or "research"
    evidence_strength = Column(Float, nullable=True)
    citations = Column(JSON, nullable=True)
    playbook_id = Column(String, index=True, nullable=True)
    research_job = Column(String, index=True, nullable=True)
    report_id = Column(String, index=True, nullable=True)
    research_job_id = Column(String, index=True, nullable=True)
    origin_insight_id = Column(String, index=True, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)

class ResearchJob(Base):
    __tablename__ = "research_jobs"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(String, unique=True, index=True, nullable=False)
    playbook_id = Column(String, index=True, nullable=False)
    research_job = Column(String, index=True, nullable=False)
    focus = Column(Text, nullable=False)
    context = Column(JSON, nullable=True)
    phase = Column(String, default="planning", nullable=False)
    status = Column(String, default="pending", nullable=False)
    plan_text = Column(Text, nullable=True)
    report_text = Column(Text, nullable=True)
    citations = Column(JSON, nullable=True)
    interaction_ids = Column(JSON, nullable=True)
    plan_interaction_id = Column(String, nullable=True)
    report_interaction_id = Column(String, nullable=True)
    last_event_id = Column(String, nullable=True)
    event_log = Column(JSON, nullable=True)
    cost_ceiling_usd = Column(Float, nullable=True)
    estimated_cost_usd = Column(Float, nullable=True)
    error = Column(Text, nullable=True)
    extracted_insight_ids = Column(JSON, nullable=True)
    origin_insight_id = Column(String, index=True, nullable=True)
    schedule_id = Column(String, index=True, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    completed_at = Column(DateTime, nullable=True)

class ResearchCorpus(Base):
    __tablename__ = "research_corpora"

    id = Column(Integer, primary_key=True, index=True)
    corpus_id = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    source_type = Column(String, nullable=False)
    file_search_store = Column(String, nullable=True)
    redaction_status = Column(String, default="pending", nullable=False)
    pii_redaction_rules = Column(JSON, nullable=True)
    metadata_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    last_synced_at = Column(DateTime, nullable=True)

class ResearchSchedule(Base):
    __tablename__ = "research_schedules"

    id = Column(Integer, primary_key=True, index=True)
    schedule_id = Column(String, unique=True, index=True, nullable=False)
    playbook_id = Column(String, index=True, nullable=False)
    cadence = Column(String, nullable=False)
    focus = Column(Text, nullable=False)
    enabled = Column(Boolean, default=True, nullable=False)
    prior_summary = Column(Text, nullable=True)
    last_job_id = Column(String, nullable=True)
    last_run_at = Column(DateTime, nullable=True)
    next_run_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)

class InsightLink(Base):
    __tablename__ = "insight_links"

    id = Column(Integer, primary_key=True, index=True)
    source_insight_id = Column(String, ForeignKey("insights.insight_id"), index=True, nullable=False)
    target_insight_id = Column(String, ForeignKey("insights.insight_id"), index=True, nullable=True)
    research_job_id = Column(String, ForeignKey("research_jobs.job_id"), index=True, nullable=True)
    relationship = Column(String, default="explains", nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)

class KPIDefinition(Base):
    __tablename__ = "kpi_definitions"

    id = Column(Integer, primary_key=True, index=True)
    metric = Column(String, unique=True, index=True, nullable=False) # e.g. "dau", "new_user_activation", "arpdau"
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    current_value = Column(Float, nullable=True)
    previous_value = Column(Float, nullable=True)
    status = Column(String, default="green", nullable=False) # "green", "warning", "critical"
    baseline_window = Column(Integer, default=7, nullable=False) # days to compare
    threshold_warning = Column(Float, nullable=True) # percentage deviation from baseline
    threshold_critical = Column(Float, nullable=True)
    schedule = Column(String, default="daily", nullable=False)
    sparkline_data = Column(JSON, nullable=True) # List[float]
    last_checked = Column(DateTime, nullable=True)


class FeedbackEvent(Base):
    __tablename__ = "feedback_events"

    id = Column(Integer, primary_key=True, index=True)
    feedback_id = Column(String, unique=True, index=True, nullable=False)
    insight_id = Column(String, ForeignKey("insights.insight_id"), index=True, nullable=False)
    user_id = Column(String, nullable=False)
    team_id = Column(String, index=True, nullable=False)
    signal_type = Column(String, nullable=False) # e.g. "acted_on", "useful", "already_knew", "not_actionable", "not_important", "wrong_disagree", "opened", "dismissed", "ignored"
    is_explicit = Column(Boolean, default=True, nullable=False)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)


class SurfacingRecord(Base):
    __tablename__ = "surfacing_records"

    id = Column(Integer, primary_key=True, index=True)
    insight_id = Column(String, ForeignKey("insights.insight_id"), index=True, nullable=False)
    team_id = Column(String, index=True, nullable=False)
    feed_position = Column(Integer, nullable=False)
    logged_propensity = Column(Float, nullable=False)
    policy_version = Column(String, nullable=False)
    is_exploration = Column(Boolean, default=False, nullable=False)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)


class RewardRecord(Base):
    __tablename__ = "reward_records"

    id = Column(Integer, primary_key=True, index=True)
    insight_id = Column(String, ForeignKey("insights.insight_id"), unique=True, index=True, nullable=False)
    shaped_reward = Column(Float, nullable=False)
    novelty_delta = Column(Float, default=0.0, nullable=False)
    actionability_delta = Column(Float, default=0.0, nullable=False)
    delayed_credits = Column(Float, default=0.0, nullable=False)
    is_resolved = Column(Boolean, default=False, nullable=False)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)


class PolicyVersion(Base):
    __tablename__ = "policy_versions"

    id = Column(Integer, primary_key=True, index=True)
    version = Column(String, unique=True, index=True, nullable=False)
    parameters = Column(JSON, nullable=False) # Store global policy weights, priors, covariance
    ope_score = Column(Float, default=0.0, nullable=False)
    valence_parity_score = Column(Float, default=1.0, nullable=False)
    status = Column(String, default="candidate", nullable=False) # "active", "candidate", "rolled_back"
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)


class ThresholdState(Base):
    __tablename__ = "threshold_states"

    id = Column(Integer, primary_key=True, index=True)
    skill_key = Column(String, unique=True, index=True, nullable=False)
    current_magnitude_threshold = Column(Float, nullable=False)
    current_confidence_threshold = Column(Float, nullable=False)
    last_updated = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)


class BanditState(Base):
    __tablename__ = "bandit_states"

    id = Column(Integer, primary_key=True, index=True)
    team_id = Column(String, unique=True, index=True, nullable=False)
    weights = Column(JSON, nullable=False) # JSON dictionary of weights per feature
    covariance = Column(JSON, nullable=False) # JSON 2D list representing covariance matrix
    last_updated = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)


class MethodologyReview(Base):
    __tablename__ = "methodology_reviews"

    id = Column(Integer, primary_key=True, index=True)
    insight_id = Column(String, ForeignKey("insights.insight_id"), index=True, nullable=False)
    skill_key = Column(String, index=True, nullable=False)
    user_comment = Column(Text, nullable=True)
    is_reviewed = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
