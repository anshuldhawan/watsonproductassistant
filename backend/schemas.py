from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any
from datetime import datetime

class AnalysisDefinitionBase(BaseModel):
    key: str
    name: str
    description: Optional[str] = None
    group_key: str
    group_name: str
    agent_id: str
    default_config: Optional[Dict[str, Any]] = None

class AnalysisDefinitionSchema(AnalysisDefinitionBase):
    id: int

    class Config:
        from_attributes = True

class RunCreate(BaseModel):
    type: str # "single" or "group"
    target_id: str # key of analysis or group
    config: Optional[Dict[str, Any]] = None

class RunSchema(BaseModel):
    id: int
    run_id: str
    type: str
    target_id: str
    status: str
    logs: Optional[str] = None
    execution_mode: str = "local"
    gemini_interaction_ids: Optional[List[str]] = None
    gemini_environment_id: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class InsightBase(BaseModel):
    insight_id: str
    title: str
    summary: str
    group_key: str
    skill_key: str
    metric: Optional[str] = None
    direction: Optional[str] = None
    magnitude_value: Optional[float] = None
    magnitude_unit: Optional[str] = None
    magnitude_relative: Optional[float] = None
    confidence: Optional[float] = None
    stat_test: Optional[str] = None
    segment: Optional[str] = None
    business_impact_metric: Optional[str] = None
    business_impact_value: Optional[float] = None
    business_impact_horizon: Optional[str] = None
    recommended_actions: Optional[List[str]] = None
    artifacts: Optional[List[str]] = None
    data_window_start: Optional[str] = None
    data_window_end: Optional[str] = None
    attention_score: float = 0.0
    cluster_id: Optional[str] = None
    feedback_status: str = "pending"
    run_id: str
    source: str = "analysis"
    evidence_strength: Optional[float] = None
    citations: Optional[List[Dict[str, Any]]] = None
    playbook_id: Optional[str] = None
    research_job: Optional[str] = None
    report_id: Optional[str] = None
    research_job_id: Optional[str] = None
    origin_insight_id: Optional[str] = None

class InsightSchema(InsightBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True

class FeedbackUpdate(BaseModel):
    feedback_status: str # "useful", "not-useful", "acted-on", etc.
    user_id: Optional[str] = "user-1"
    team_id: Optional[str] = "team-1"
    signal_type: Optional[str] = None # "acted_on", "useful", "already_knew", "not_actionable", "not_important", "wrong_disagree", etc.
    user_comment: Optional[str] = None

class FeedbackEventSchema(BaseModel):
    id: int
    feedback_id: str
    insight_id: str
    user_id: str
    team_id: str
    signal_type: str
    is_explicit: bool
    timestamp: datetime

    class Config:
        from_attributes = True

class SurfacingRecordSchema(BaseModel):
    id: int
    insight_id: str
    team_id: str
    feed_position: int
    logged_propensity: float
    policy_version: str
    is_exploration: bool
    timestamp: datetime

    class Config:
        from_attributes = True

class RewardRecordSchema(BaseModel):
    id: int
    insight_id: str
    shaped_reward: float
    novelty_delta: float
    actionability_delta: float
    delayed_credits: float
    is_resolved: bool
    timestamp: datetime

    class Config:
        from_attributes = True

class PolicyVersionSchema(BaseModel):
    id: int
    version: str
    parameters: Dict[str, Any]
    ope_score: float
    valence_parity_score: float
    status: str
    created_at: datetime

    class Config:
        from_attributes = True

class ThresholdStateSchema(BaseModel):
    id: int
    skill_key: str
    current_magnitude_threshold: float
    current_confidence_threshold: float
    last_updated: datetime

    class Config:
        from_attributes = True

class BanditStateSchema(BaseModel):
    id: int
    team_id: str
    weights: Dict[str, Any]
    covariance: Any
    last_updated: datetime

    class Config:
        from_attributes = True

class MethodologyReviewSchema(BaseModel):
    id: int
    insight_id: str
    skill_key: str
    user_comment: Optional[str] = None
    is_reviewed: bool
    created_at: datetime

    class Config:
        from_attributes = True

class KPIDefinitionSchema(BaseModel):
    id: int
    metric: str
    name: str
    description: Optional[str] = None
    current_value: Optional[float] = None
    previous_value: Optional[float] = None
    status: str
    baseline_window: int
    threshold_warning: Optional[float] = None
    threshold_critical: Optional[float] = None
    schedule: str
    sparkline_data: Optional[List[float]] = None
    last_checked: Optional[datetime] = None

    class Config:
        from_attributes = True


class ResearchJobCreate(BaseModel):
    playbook_id: str
    focus: str
    context: Optional[Dict[str, Any]] = None
    origin_insight_id: Optional[str] = None
    schedule_id: Optional[str] = None


class ResearchJobRefine(BaseModel):
    refinement: str


class ResearchFollowUpCreate(BaseModel):
    question: str


class ResearchJobSchema(BaseModel):
    id: int
    job_id: str
    playbook_id: str
    research_job: str
    focus: str
    context: Optional[Dict[str, Any]] = None
    phase: str
    status: str
    plan_text: Optional[str] = None
    report_text: Optional[str] = None
    citations: Optional[List[Dict[str, Any]]] = None
    interaction_ids: Optional[List[str]] = None
    plan_interaction_id: Optional[str] = None
    report_interaction_id: Optional[str] = None
    last_event_id: Optional[str] = None
    event_log: Optional[List[Dict[str, Any]]] = None
    cost_ceiling_usd: Optional[float] = None
    estimated_cost_usd: Optional[float] = None
    error: Optional[str] = None
    extracted_insight_ids: Optional[List[str]] = None
    origin_insight_id: Optional[str] = None
    schedule_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ResearchCorpusCreate(BaseModel):
    name: str
    source_type: str
    file_search_store: Optional[str] = None
    sample_text: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class ResearchCorpusSchema(BaseModel):
    id: int
    corpus_id: str
    name: str
    source_type: str
    file_search_store: Optional[str] = None
    redaction_status: str
    pii_redaction_rules: Optional[Dict[str, Any]] = None
    metadata_json: Optional[Dict[str, Any]] = None
    created_at: datetime
    last_synced_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ResearchScheduleCreate(BaseModel):
    playbook_id: str
    cadence: str = "weekly"
    focus: str
    enabled: bool = True


class ResearchScheduleSchema(BaseModel):
    id: int
    schedule_id: str
    playbook_id: str
    cadence: str
    focus: str
    enabled: bool
    prior_summary: Optional[str] = None
    last_job_id: Optional[str] = None
    last_run_at: Optional[datetime] = None
    next_run_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True
