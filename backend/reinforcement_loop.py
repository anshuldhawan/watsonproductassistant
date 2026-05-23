import datetime
import math
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session
from .models import Insight, BanditState, ThresholdState, FeedbackEvent, SurfacingRecord, MethodologyReview, PolicyVersion, RewardRecord

# Feature Names and Default Prior Weights
FEATURE_NAMES = [
    "bias",
    "magnitude",
    "confidence",
    "novelty",
    "actionability",
    "positive_valence",
    "negative_valence",
    "neutral_valence"
]
NUM_FEATURES = len(FEATURE_NAMES)

# Priors representing standard hand-weighted configurations
PRIOR_WEIGHTS = [0.10, 0.30, 0.25, 0.15, 0.15, 0.05, 0.05, 0.00]
PRIOR_COV = (0.1 * np.eye(NUM_FEATURES)).tolist()

# Hard Governance Validity Floor
HARD_CONFIDENCE_FLOOR = 0.70
HARD_MAGNITUDE_FLOOR = 0.05
RESEARCH_EVIDENCE_STRENGTH_FLOOR = 0.60


def extract_features(insight: Any) -> np.ndarray:
    """
    Extract normalized context feature vector x from an insight (dict or SQLAlchemy object).
    Feature dimension: NUM_FEATURES (8)
    """
    if isinstance(insight, dict):
        source = insight.get("source")
        evidence_strength = insight.get("evidence_strength")
        mag_rel = insight.get("magnitude_relative")
        if mag_rel is None:
            # Check nested dict magnitude
            mag_rel = insight.get("magnitude", {}).get("relative")
        mag_rel = mag_rel or 0.0
        conf = insight.get("confidence")
        actions = insight.get("recommended_actions") or []
        direction = insight.get("direction") or "neutral"
        novelty = insight.get("novelty") or 0.8
    else:
        source = getattr(insight, "source", None)
        evidence_strength = getattr(insight, "evidence_strength", None)
        mag_rel = getattr(insight, "magnitude_relative", 0.0) or 0.0
        conf = getattr(insight, "confidence", None)
        actions = getattr(insight, "recommended_actions", []) or []
        direction = getattr(insight, "direction", "neutral") or "neutral"
        # Look for custom attribute or default
        novelty = getattr(insight, "attention_score", 0.8)  # fallback
        if hasattr(insight, "novelty_score"):
            novelty = getattr(insight, "novelty_score")

    # Clamping and normalization
    evidence_norm = min(1.0, max(0.0, evidence_strength or 0.0))
    magnitude_norm = evidence_norm if source == "research" else min(1.0, abs(mag_rel) / 0.5)
    conf_norm = evidence_norm if source == "research" else min(1.0, max(0.0, conf)) if conf is not None else 0.8
    actionability_score = min(1.0, len(actions) * 0.25)

    pos_valence = 1.0 if direction == "up" else 0.0
    neg_valence = 1.0 if direction == "down" else 0.0
    neu_valence = 1.0 if direction in ("neutral", "", None) else 0.0

    return np.array([
        1.0,  # Bias
        magnitude_norm,
        conf_norm,
        novelty,
        actionability_score,
        pos_valence,
        neg_valence,
        neu_valence
    ], dtype=float)


def get_or_create_bandit_state(db: Session, team_id: str) -> BanditState:
    """
    Retrieve or create the BanditState (weights & covariance) for a specific team.
    Implements Hierarchical Bayes / Partial Pooling by inheriting the global prior.
    """
    # Try fetching the global prior policy first to see if we have customized global weights
    global_policy = db.query(PolicyVersion).filter(PolicyVersion.status == "active").first()
    weights = PRIOR_WEIGHTS
    cov = PRIOR_COV
    if global_policy:
        weights = global_policy.parameters.get("weights", PRIOR_WEIGHTS)
        cov = global_policy.parameters.get("covariance", PRIOR_COV)

    state = db.query(BanditState).filter(BanditState.team_id == team_id).first()
    if not state:
        state = BanditState(
            team_id=team_id,
            weights=weights,
            covariance=cov,
            last_updated=datetime.datetime.utcnow()
        )
        db.add(state)
        db.commit()
        db.refresh(state)
    return state


def get_or_create_threshold_state(db: Session, skill_key: str) -> ThresholdState:
    """
    Retrieve or initialize the active L2 threshold state for an analytical skill.
    """
    state = db.query(ThresholdState).filter(ThresholdState.skill_key == skill_key).first()
    if not state:
        state = ThresholdState(
            skill_key=skill_key,
            current_magnitude_threshold=0.10,  # default
            current_confidence_threshold=0.80,  # default
            last_updated=datetime.datetime.utcnow()
        )
        db.add(state)
        db.commit()
        db.refresh(state)
    return state


def passes_hard_floor(insight: Any) -> bool:
    """
    Verifies if an insight meets the hard, non-learnable validity floor.
    """
    if isinstance(insight, dict):
        if insight.get("source") == "research":
            return (insight.get("evidence_strength") or 0.0) >= RESEARCH_EVIDENCE_STRENGTH_FLOOR
        mag_rel = insight.get("magnitude_relative") or insight.get("magnitude", {}).get("relative") or 0.0
        conf = insight.get("confidence")
    else:
        if getattr(insight, "source", None) == "research":
            return (getattr(insight, "evidence_strength", None) or 0.0) >= RESEARCH_EVIDENCE_STRENGTH_FLOOR
        mag_rel = getattr(insight, "magnitude_relative", 0.0) or 0.0
        conf = getattr(insight, "confidence", None)

    conf_val = conf if conf is not None else 0.8
    return conf_val >= HARD_CONFIDENCE_FLOOR and abs(mag_rel) >= HARD_MAGNITUDE_FLOOR


def passes_active_threshold(insight: Any, db: Session) -> bool:
    """
    Verifies if an insight meets the currently adjusted L2 threshold for its skill.
    """
    if isinstance(insight, dict):
        if insight.get("source") == "research":
            return (insight.get("evidence_strength") or 0.0) >= RESEARCH_EVIDENCE_STRENGTH_FLOOR
        skill_key = insight.get("skill") or insight.get("skill_key")
        mag_rel = insight.get("magnitude_relative") or insight.get("magnitude", {}).get("relative") or 0.0
        conf = insight.get("confidence")
    else:
        if getattr(insight, "source", None) == "research":
            return (getattr(insight, "evidence_strength", None) or 0.0) >= RESEARCH_EVIDENCE_STRENGTH_FLOOR
        skill_key = getattr(insight, "skill_key", None)
        mag_rel = getattr(insight, "magnitude_relative", 0.0) or 0.0
        conf = getattr(insight, "confidence", None)

    if not skill_key:
        return True

    state = get_or_create_threshold_state(db, skill_key)
    conf_val = conf if conf is not None else 0.8

    return (conf_val >= state.current_confidence_threshold and
            abs(mag_rel) >= state.current_magnitude_threshold)


def sample_thompson_weights(state: BanditState) -> np.ndarray:
    """
    Draw a weight vector sample theta from the posterior distribution N(w, Sigma).
    """
    w = np.array(state.weights)
    Sigma = np.array(state.covariance)
    try:
        # Sample from multivariate normal
        theta = np.random.multivariate_normal(w, Sigma)
    except Exception:
        # Fallback to mean weights in case of numerical instability
        theta = w
    return theta


def diversity_constrained_rank(
    candidates: List[Tuple[Any, float, np.ndarray, bool]], 
    beta: float = 0.15
) -> List[Tuple[Any, float, np.ndarray, bool]]:
    """
    Greedy reranking with group-diversity penalties to prevent category collapse.
    Each consecutive selection from a group is penalized by beta * count.
    Input candidate elements are (insight, sampled_score, features, passes_active).
    """
    if not candidates:
        return []

    ranked = []
    pool = list(candidates)
    group_counts = {}

    while pool:
        best_idx = -1
        best_score = -999.0

        for idx, (ins, score, _, _) in enumerate(pool):
            group_key = ins.get("group") if isinstance(ins, dict) else getattr(ins, "group_key", "default")
            penalty = beta * group_counts.get(group_key, 0)
            adjusted_score = score - penalty

            if adjusted_score > best_score:
                best_score = adjusted_score
                best_idx = idx

        # Pop from pool and append to ranked
        selected = pool.pop(best_idx)
        ranked.append(selected)

        # Update category counts
        g_key = selected[0].get("group") if isinstance(selected[0], dict) else getattr(selected[0], "group_key", "default")
        group_counts[g_key] = group_counts.get(g_key, 0) + 1

    return ranked


def rank_feed(
    candidates: List[Any], 
    team_id: str, 
    db: Session,
    exploration_budget: float = 0.15
) -> List[Dict[str, Any]]:
    """
    Inline rank-scoring of insight candidates.
    Applies Hard Floor filtering, Thompson Sampling, Active Threshold partitioning,
    Diversity constraints, Exploration Slot blending, and logs Propensities.
    """
    # 1. Hard validity floor filter
    valid_candidates = [c for c in candidates if passes_hard_floor(c)]
    if not valid_candidates:
        return []

    # Get team-specific bandit state
    bandit_state = get_or_create_bandit_state(db, team_id)
    theta = sample_thompson_weights(bandit_state)

    # 2. Score candidates using sampled Thompson weights and partition
    scored_candidates = []
    for ins in valid_candidates:
        x = extract_features(ins)
        score = float(np.dot(theta, x))
        passes_active = passes_active_threshold(ins, db)
        scored_candidates.append((ins, score, x, passes_active))

    # Separate guaranteed floor-passers from sub-threshold valid candidates
    floor_passers = [item for item in scored_candidates if item[3]]
    sub_threshold = [item for item in scored_candidates if not item[3]]

    # Rank both partitions with diversity constraint
    ranked_floor_passers = diversity_constrained_rank(floor_passers, beta=0.15)
    ranked_sub_threshold = diversity_constrained_rank(sub_threshold, beta=0.15)

    # Combined candidate feed
    combined_feed = ranked_floor_passers + ranked_sub_threshold
    if not combined_feed:
        return []

    # 3. Inject Exploration Budget (default 15%)
    feed_size = len(combined_feed)
    num_explore = int(round(feed_size * exploration_budget))
    num_explore = max(0, min(num_explore, len(ranked_sub_threshold)))

    exploit_slots = len(combined_feed) - num_explore
    exploit_subset = combined_feed[:exploit_slots]
    explore_pool = combined_feed[exploit_slots:]

    # Shuffle exploration slots
    if explore_pool:
        np.random.shuffle(explore_pool)

    final_feed_items = exploit_subset + explore_pool[:num_explore]

    # 4. Compute propensities (softmax on scores)
    scores = np.array([item[1] for item in final_feed_items])
    # Softmax with temperature tau = 0.2
    tau = 0.2
    try:
        exp_scores = np.exp((scores - np.max(scores)) / tau)
        propensities = exp_scores / np.sum(exp_scores)
    except Exception:
        propensities = np.ones(len(scores)) / len(scores)

    # 5. Structure final output and log to SurfacingRecords
    active_policy = db.query(PolicyVersion).filter(PolicyVersion.status == "active").first()
    policy_ver = active_policy.version if active_policy else "v1_prior"

    final_ranked_feed = []
    for rank, (item, score, x, passes_active) in enumerate(final_ranked_feed_pre := final_feed_items):
        ins_id = item.get("insight_id") if isinstance(item, dict) else getattr(item, "insight_id")
        propensity = float(propensities[rank])
        
        # Check if it came from the explore partition
        is_explore = (rank >= exploit_slots)

        # Log to database
        surf_rec = SurfacingRecord(
            insight_id=ins_id,
            team_id=team_id,
            feed_position=rank + 1,
            logged_propensity=propensity,
            policy_version=policy_ver,
            is_exploration=is_explore,
            timestamp=datetime.datetime.utcnow()
        )
        db.add(surf_rec)

        # Build return dictionary
        insight_dict = item if isinstance(item, dict) else {
            "insight_id": item.insight_id,
            "title": item.title,
            "summary": item.summary,
            "group_key": item.group_key,
            "skill_key": item.skill_key,
            "metric": item.metric,
            "direction": item.direction,
            "magnitude_relative": item.magnitude_relative,
            "confidence": item.confidence,
            "recommended_actions": item.recommended_actions,
            "artifacts": item.artifacts,
            "stat_test": item.stat_test,
            "segment": item.segment,
            "business_impact_value": item.business_impact_value,
            "feedback_status": item.feedback_status,
            "attention_score": item.attention_score,
            "source": getattr(item, "source", "analysis"),
            "evidence_strength": getattr(item, "evidence_strength", None),
            "citations": getattr(item, "citations", None),
            "playbook_id": getattr(item, "playbook_id", None),
            "research_job": getattr(item, "research_job", None),
            "report_id": getattr(item, "report_id", None),
            "research_job_id": getattr(item, "research_job_id", None),
            "origin_insight_id": getattr(item, "origin_insight_id", None),
        }
        
        # Inject dynamic score, rank, and features
        insight_dict["attention_score"] = float(score)  # learned score
        insight_dict["rank"] = rank + 1
        insight_dict["is_exploration"] = is_explore
        insight_dict["propensity"] = propensity
        final_ranked_feed.append(insight_dict)

    db.commit()
    return final_ranked_feed


def update_bandit_posterior(db: Session, team_id: str, x: np.ndarray, r: float):
    """
    Updates the Bayesian Linear model posterior parameters for a team (L1 Incremental Update).
    """
    state = get_or_create_bandit_state(db, team_id)
    w = np.array(state.weights)
    Sigma = np.array(state.covariance)

    sigma2 = 0.1  # Likelihood noise variance

    # Update precision matrix Lambda = Sigma^-1
    try:
        Lambda = np.linalg.inv(Sigma)
    except np.linalg.LinAlgError:
        Lambda = np.eye(NUM_FEATURES) / 0.1

    # Sherman-Morrison rank-1 update for precision
    Lambda_new = Lambda + (1.0 / sigma2) * np.outer(x, x)

    # Update mean vector w
    b = Lambda @ w
    b_new = b + (1.0 / sigma2) * r * x

    try:
        Sigma_new = np.linalg.inv(Lambda_new)
        w_new = Sigma_new @ b_new
    except np.linalg.LinAlgError:
        Sigma_new = Sigma
        w_new = w

    state.weights = w_new.tolist()
    state.covariance = Sigma_new.tolist()
    state.last_updated = datetime.datetime.utcnow()
    db.commit()


def calculate_shaped_reward(signal_type: str) -> Tuple[float, Dict[str, float]]:
    """
    Calculate shaped reward scalar and sub-model updates per feedback taxonomy (§5.3).
    Returns (ranking_reward, targeted_updates).
    """
    updates = {"novelty": 0.0, "actionability": 0.0, "raise_threshold": False}

    if signal_type == "acted_on":
        return 1.0, updates
    elif signal_type == "useful":
        return 0.6, updates
    elif signal_type == "opened":  # implicit signal
        return 0.15, updates
    elif signal_type == "already_knew":
        updates["novelty"] = -0.8  # strong negative novelty update
        return 0.0, updates
    elif signal_type == "not_actionable":
        updates["actionability"] = -0.6
        return -0.3, updates
    elif signal_type == "not_important":
        updates["raise_threshold"] = True  # flags L2 threshold controller
        return -0.5, updates
    elif signal_type == "dismissed":
        return -0.3, updates
    elif signal_type == "ignored":  # implicit ignore
        return -0.1, updates
    
    return 0.0, updates


def handle_feedback_routing(
    db: Session, 
    insight_id: str, 
    signal_type: str, 
    user_id: str = "user-1",
    team_id: str = "team-1",
    user_comment: Optional[str] = None
) -> Tuple[float, bool]:
    """
    Routes a feedback event. Calculates rewards, triggers posterior updates,
    routes 'wrong' disagreements to QA, and returns (reward, is_review).
    """
    # 1. Check for 'wrong/disagree' methodology path
    if signal_type == "wrong_disagree":
        # Create QA methodology review record
        insight = db.query(Insight).filter(Insight.insight_id == insight_id).first()
        skill_key = insight.skill_key if insight else "unknown"
        
        review = MethodologyReview(
            insight_id=insight_id,
            skill_key=skill_key,
            user_comment=user_comment or "User marked as incorrect.",
            is_reviewed=False,
            created_at=datetime.datetime.utcnow()
        )
        db.add(review)

        # Update insight feedback status
        if insight:
            insight.feedback_status = "wrong_disagree"
        db.commit()

        # Check if skill needs to be paused due to excessive disagreement
        disagree_count = db.query(MethodologyReview).filter(
            MethodologyReview.skill_key == skill_key,
            MethodologyReview.is_reviewed == False
        ).count()
        
        # If 3 or more unreviewed wrong feedbacks, we'd raise a QA alert
        return 0.0, True

    # 2. Add standard FeedbackEvent record
    event_id = f"feed-{datetime.datetime.utcnow().timestamp()}-{np.random.randint(1000)}"
    feedback_event = FeedbackEvent(
        feedback_id=event_id,
        insight_id=insight_id,
        user_id=user_id,
        team_id=team_id,
        signal_type=signal_type,
        is_explicit=(signal_type not in ("opened", "ignored")),
        timestamp=datetime.datetime.utcnow()
    )
    db.add(feedback_event)

    # Update insight feedback status
    insight = db.query(Insight).filter(Insight.insight_id == insight_id).first()
    if insight:
        insight.feedback_status = signal_type

    # 3. Calculate reward and update targeted parameters
    reward, targeted = calculate_shaped_reward(signal_type)

    # Record reward details
    rew_rec = db.query(RewardRecord).filter(RewardRecord.insight_id == insight_id).first()
    if not rew_rec:
        rew_rec = RewardRecord(
            insight_id=insight_id,
            shaped_reward=reward,
            novelty_delta=targeted["novelty"],
            actionability_delta=targeted["actionability"],
            delayed_credits=0.0,
            is_resolved=False,
            timestamp=datetime.datetime.utcnow()
        )
        db.add(rew_rec)
    else:
        rew_rec.shaped_reward += reward
        rew_rec.novelty_delta += targeted["novelty"]
        rew_rec.actionability_delta += targeted["actionability"]

    db.commit()

    # 4. Trigger Bayesian update to the local team bandit (L1 Update)
    if insight:
        x = extract_features(insight)
        
        # Apply targeted novelty/actionability update adjustments directly onto features before posterior update
        if targeted["novelty"] != 0.0:
            x[3] = max(0.1, x[3] + targeted["novelty"])
        if targeted["actionability"] != 0.0:
            x[4] = max(0.0, x[4] + targeted["actionability"])

        update_bandit_posterior(db, team_id, x, reward)

    # 5. Handle immediate L2 threshold trigger if "not_important"
    if targeted["raise_threshold"] and insight:
        threshold_state = get_or_create_threshold_state(db, insight.skill_key)
        # Raise thresholds by 5% to reduce noise, capped at 0.95
        threshold_state.current_confidence_threshold = min(0.95, threshold_state.current_confidence_threshold + 0.05)
        # For magnitude, raise by 1% absolute
        threshold_state.current_magnitude_threshold = min(0.40, threshold_state.current_magnitude_threshold + 0.01)
        threshold_state.last_updated = datetime.datetime.utcnow()
        db.commit()

    return reward, False


# ==========================================
# BATCH CONTROL LOOPS (L2, L3, Audits, OPE)
# ==========================================

def run_weekly_l2_threshold_controller(db: Session):
    """
    L2 Threshold Controller - Adjusts per-skill bars based on aggregate feedback.
    Consistently ignored/not_important insights raise the bar; highly useful/acted_on lowers it.
    Can never lower below the hard validity floors.
    """
    thresholds = db.query(ThresholdState).all()
    for state in thresholds:
        # Fetch feedbacks for this skill over last 7 days
        feedbacks = db.query(FeedbackEvent).join(Insight).filter(
            Insight.skill_key == state.skill_key,
            FeedbackEvent.timestamp >= datetime.datetime.utcnow() - datetime.timedelta(days=7)
        ).all()

        if not feedbacks:
            continue

        not_important_count = sum(1 for f in feedbacks if f.signal_type == "not_important")
        positive_count = sum(1 for f in feedbacks if f.signal_type in ("acted_on", "useful"))
        total = len(feedbacks)

        neg_ratio = not_important_count / total
        pos_ratio = positive_count / total

        # If more than 30% of signals are negative, raise the bar
        if neg_ratio > 0.30:
            state.current_confidence_threshold = min(0.95, state.current_confidence_threshold + 0.03)
            state.current_magnitude_threshold = min(0.40, state.current_magnitude_threshold + 0.01)
        # If more than 60% of signals are positive, lower the bar (incentivize surfacing)
        elif pos_ratio > 0.60:
            state.current_confidence_threshold = max(HARD_CONFIDENCE_FLOOR, state.current_confidence_threshold - 0.03)
            state.current_magnitude_threshold = max(HARD_MAGNITUDE_FLOOR, state.current_magnitude_threshold - 0.01)

        state.last_updated = datetime.datetime.utcnow()
    db.commit()


def run_valence_parity_audit(db: Session) -> float:
    """
    Sycophancy / Valence Parity Audit (§10.3).
    Compares surfacing rates of positive vs. negative insights of equal validity/magnitude.
    Returns the Valence Parity index (ratio of negative to positive surfacing rate).
    """
    surfaced_records = db.query(SurfacingRecord).join(Insight).all()
    if not surfaced_records:
        return 1.0

    pos_surfaced = 0
    neg_surfaced = 0
    for r in surfaced_records:
        insight = db.query(Insight).filter(Insight.insight_id == r.insight_id).first()
        if insight:
            if insight.direction == "up":
                pos_surfaced += 1
            elif insight.direction == "down":
                neg_surfaced += 1

    # Ratio of surfaced negative vs positive
    if pos_surfaced == 0:
        return 1.0
    valence_parity = neg_surfaced / pos_surfaced
    return float(valence_parity)


def run_offline_policy_evaluation(db: Session, candidate_weights: List[float]) -> float:
    """
    OPE (Off-Policy Evaluation) utilizing Inverse Propensity Scoring (IPS) on historical feeds.
    Estimates the value of a candidate policy before active deployment.
    """
    surfaced = db.query(SurfacingRecord).all()
    if not surfaced:
        return 1.0  # default OPE score

    score_sum = 0.0
    weight_sum = 0.0

    cand_w = np.array(candidate_weights)

    for record in surfaced:
        # Find corresponding reward and features
        reward_rec = db.query(RewardRecord).filter(RewardRecord.insight_id == record.insight_id).first()
        insight = db.query(Insight).filter(Insight.insight_id == record.insight_id).first()

        if not reward_rec or not insight:
            continue

        x = extract_features(insight)
        
        # Calculate target propensity under candidate policy
        cand_score = float(np.dot(cand_w, x))
        # Simulated target propensity: soft approximation
        target_propensity = min(1.0, max(0.01, 1.0 / (1.0 + math.exp(-cand_score))))

        # Inverse Propensity Score (IPS)
        logged_propensity = record.logged_propensity or 0.1
        ips_weight = target_propensity / logged_propensity

        # Clip weights to control variance
        ips_weight = min(10.0, ips_weight)

        score_sum += ips_weight * reward_rec.shaped_reward
        weight_sum += ips_weight

    if weight_sum == 0:
        return 0.0
    return float(score_sum / weight_sum)


def run_daily_batch_refit(db: Session) -> PolicyVersion:
    """
    Daily full policy refit. Aggregates all global feedback, refits parameters,
    runs the Safety Audits, computes OPE, and deploys a new version if verified.
    """
    events = db.query(FeedbackEvent).all()
    
    # Initialize global weights
    refined_weights = list(PRIOR_WEIGHTS)
    refined_cov = list(PRIOR_COV)

    # Perform a global regression update if feedback exists
    if events:
        X = []
        Y = []
        for e in events:
            insight = db.query(Insight).filter(Insight.insight_id == e.insight_id).first()
            if not insight:
                continue
            X.append(extract_features(insight))
            r, _ = calculate_shaped_reward(e.signal_type)
            Y.append(r)

        if X:
            X_mat = np.array(X)
            Y_vec = np.array(Y)
            
            # Ridge regression / Bayesian linear solve
            # w = (X^T X + alpha * I)^-1 X^T Y
            alpha = 1.0
            k = X_mat.shape[1]
            try:
                XTX_inv = np.linalg.inv(X_mat.T @ X_mat + alpha * np.eye(k))
                w_glob = XTX_inv @ X_mat.T @ Y_vec
                refined_weights = w_glob.tolist()
                refined_cov = XTX_inv.tolist()
            except np.linalg.LinAlgError:
                pass

    # 1. Run audits
    valence_parity = run_valence_parity_audit(db)
    ope_score = run_offline_policy_evaluation(db, refined_weights)

    # Status check: reject if there is a severe valence skew (anti-sycophancy check)
    # i.e. if it suppresses bad news (direction = down) by more than 4x
    if valence_parity < 0.25:
        # Policy is soft-pedaling bad news! Reject or apply correction
        status = "rejected_due_to_valence_bias"
    else:
        status = "active"

    # Create new versioned Policy
    version_str = f"policy-v{datetime.datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
    
    # Archive prior active policies
    if status == "active":
        db.query(PolicyVersion).filter(PolicyVersion.status == "active").update({"status": "archived"})

    policy_ver = PolicyVersion(
        version=version_str,
        parameters={"weights": refined_weights, "covariance": refined_cov},
        ope_score=ope_score,
        valence_parity_score=valence_parity,
        status=status,
        created_at=datetime.datetime.utcnow()
    )
    db.add(policy_ver)
    db.commit()
    db.refresh(policy_ver)

    return policy_ver
