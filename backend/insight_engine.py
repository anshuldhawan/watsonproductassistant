import re
import datetime
import math
import numpy as np
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from .models import Insight
from .reinforcement_loop import extract_features, sigmoid, PRIOR_WEIGHTS, PolicyVersion

# Weight configurations for the Attention Score
WEIGHTS = {
    "w_magnitude": 0.25,
    "w_confidence": 0.20,
    "w_business_impact": 0.25,
    "w_novelty": 0.15,
    "w_actionability": 0.15,
    "w_staleness": 0.05 # subtracted
}

def calculate_attention_score(
    magnitude_relative: Optional[float],
    confidence: Optional[float],
    business_impact_usd: Optional[float],
    recommended_actions: Optional[List[str]],
    novelty: float,
    created_at: datetime.datetime
) -> float:
    """
    Calculate the attention score in [0.0, 1.0] for an insight.
    """
    # 1. Normalized Magnitude: relative change, clamped to [0.0, 1.0]
    # For example, a 50% change (0.50) is extremely high. We cap it at 1.0.
    mag_val = abs(magnitude_relative) if magnitude_relative is not None else 0.0
    magnitude_norm = min(1.0, mag_val / 0.5)

    # 2. Confidence: between 0.0 and 1.0
    conf_norm = min(1.0, max(0.0, confidence)) if confidence is not None else 0.8

    # 3. Normalized Business Impact: log scale over USD impact, e.g., $100k -> 5.0, cap at $1M -> 6.0
    impact_val = abs(business_impact_usd) if business_impact_usd is not None else 0.0
    if impact_val <= 1.0:
        impact_norm = 0.0
    else:
        # log10($1M) = 6.0
        impact_norm = min(1.0, math.log10(impact_val) / 6.0)

    # 4. Actionability: based on number of recommended actions
    actions_count = len(recommended_actions) if recommended_actions is not None else 0
    actionability_score = min(1.0, actions_count * 0.25) # 4+ actions = full score

    # 5. Staleness: decays by 5% per day
    days_old = (datetime.datetime.utcnow() - created_at).days
    staleness_decay = min(0.5, days_old * WEIGHTS["w_staleness"])

    # Core linear combination
    attention = (
        WEIGHTS["w_magnitude"] * magnitude_norm +
        WEIGHTS["w_confidence"] * conf_norm +
        WEIGHTS["w_business_impact"] * impact_norm +
        WEIGHTS["w_novelty"] * novelty +
        WEIGHTS["w_actionability"] * actionability_score -
        staleness_decay
    )

    return max(0.01, min(1.0, attention))


def tokenize_text(text: str) -> set:
    """Helper to lowercase and split words for simple Jaccard similarity."""
    words = re.findall(r'\w+', text.lower())
    # filter short or highly common words (stop words)
    stopwords = {"and", "the", "for", "with", "this", "that", "from", "down", "up", "than", "downby", "upby"}
    return {w for w in words if len(w) > 2 and w not in stopwords}


def calculate_jaccard_similarity(text1: str, text2: str) -> float:
    """Calculate token-based Jaccard similarity between two texts."""
    set1 = tokenize_text(text1)
    set2 = tokenize_text(text2)
    if not set1 or not set2:
        return 0.0
    intersection = set1.intersection(set2)
    union = set1.union(set2)
    return len(intersection) / len(union)


def cluster_and_score_insights(db: Session, new_insights: List[Dict[str, Any]], current_run_id: str) -> List[Insight]:
    """
    Ingest newly generated raw insights, calculate their attention scores,
    perform clustering (deduplication), and persist them to the database.
    """
    persisted_insights = []

    # Fetch existing active insights in the last 7 days to calculate novelty and clustering
    seven_days_ago = datetime.datetime.utcnow() - datetime.timedelta(days=7)
    recent_db_insights = db.query(Insight).filter(Insight.created_at >= seven_days_ago).all()

    for raw in new_insights:
        created_time = datetime.datetime.utcnow()

        # Check novelty against existing database insights
        max_similarity = 0.0
        matching_cluster_id = None

        for existing in recent_db_insights:
            # Check content similarity
            sim = calculate_jaccard_similarity(raw["title"] + " " + raw["summary"], existing.title + " " + existing.summary)
            # Check segment similarity
            if raw.get("segment") == existing.segment and raw.get("metric") == existing.metric:
                sim = max(sim, 0.8) # Strong weight if same metric and segment

            if sim > max_similarity:
                max_similarity = sim
                if sim >= 0.6: # High similarity threshold
                    matching_cluster_id = existing.cluster_id

        # Novelty is inversely proportional to similarity with existing insights
        novelty_score = max(0.1, 1.0 - max_similarity)

        # Generate unique IDs if not provided
        ins_id = raw.get("insight_id") or str(uuid_4_mock())
        cluster_id = matching_cluster_id or raw.get("cluster_id") or f"cluster-{ins_id[:8]}"

        # Calculate attention score using current policy parameters
        raw["novelty"] = novelty_score
        x_feat = extract_features(raw)

        # Get active policy parameters
        active_policy = db.query(PolicyVersion).filter(PolicyVersion.status == "active").first()
        policy_weights = active_policy.parameters.get("weights", PRIOR_WEIGHTS) if active_policy else PRIOR_WEIGHTS

        attention = max(0.01, min(1.0, sigmoid(float(np.dot(policy_weights, x_feat)))))

        # Build Database model
        db_insight = Insight(
            insight_id=ins_id,
            title=raw["title"],
            summary=raw["summary"],
            group_key=raw.get("group") or raw.get("group_key") or "product-user-research",
            skill_key=raw.get("skill") or raw.get("skill_key") or raw.get("playbook_id") or "research",
            metric=raw.get("metric"),
            direction=raw.get("direction"),
            magnitude_value=raw.get("magnitude", {}).get("value") if isinstance(raw.get("magnitude"), dict) else raw.get("magnitude_value"),
            magnitude_unit=raw.get("magnitude", {}).get("unit") if isinstance(raw.get("magnitude"), dict) else raw.get("magnitude_unit"),
            magnitude_relative=raw.get("magnitude", {}).get("relative") if isinstance(raw.get("magnitude"), dict) else raw.get("magnitude_relative"),
            confidence=raw.get("confidence"),
            stat_test=raw.get("stat_test"),
            segment=raw.get("segment"),
            business_impact_metric=raw.get("business_impact", {}).get("metric") if isinstance(raw.get("business_impact"), dict) else raw.get("business_impact_metric"),
            business_impact_value=raw.get("business_impact", {}).get("estimate_usd") if isinstance(raw.get("business_impact"), dict) else raw.get("business_impact_value"),
            business_impact_horizon=raw.get("business_impact", {}).get("horizon") if isinstance(raw.get("business_impact"), dict) else raw.get("business_impact_horizon"),
            recommended_actions=raw.get("recommended_actions"),
            artifacts=raw.get("artifacts"),
            data_window_start=raw.get("data_window", {}).get("start") if isinstance(raw.get("data_window"), dict) else raw.get("data_window_start"),
            data_window_end=raw.get("data_window", {}).get("end") if isinstance(raw.get("data_window"), dict) else raw.get("data_window_end"),
            attention_score=attention,
            cluster_id=cluster_id,
            feedback_status="pending",
            run_id=current_run_id,
            source=raw.get("source") or "analysis",
            evidence_strength=raw.get("evidence_strength"),
            citations=raw.get("citations"),
            playbook_id=raw.get("playbook_id"),
            research_job=raw.get("research_job"),
            report_id=raw.get("report_id"),
            research_job_id=raw.get("research_job_id"),
            origin_insight_id=raw.get("origin_insight_id"),
            created_at=created_time
        )

        db.add(db_insight)
        persisted_insights.append(db_insight)

    db.commit()
    for ins in persisted_insights:
        db.refresh(ins)

    return persisted_insights

def uuid_4_mock():
    import uuid
    return str(uuid.uuid4())
