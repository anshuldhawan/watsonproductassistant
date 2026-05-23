import datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.database import Base
from backend.models import (
    BanditState,
    FeedbackEvent,
    Insight,
    MethodologyReview,
    RewardRecord,
    SurfacingRecord,
    ThresholdState,
)
from backend.reinforcement_loop import (
    HARD_CONFIDENCE_FLOOR,
    HARD_MAGNITUDE_FLOOR,
    handle_feedback_routing,
    rank_feed,
    run_valence_parity_audit,
    run_weekly_l2_threshold_controller,
)


def make_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)()


def make_insight(
    insight_id="insight-1",
    skill_key="cohort-retention-curves",
    direction="down",
    magnitude_relative=-0.2,
    confidence=0.95,
):
    return Insight(
        insight_id=insight_id,
        title=f"Insight {insight_id}",
        summary="A valid, material finding.",
        group_key="retention-churn",
        skill_key=skill_key,
        metric="retention",
        direction=direction,
        magnitude_relative=magnitude_relative,
        confidence=confidence,
        recommended_actions=["Investigate"],
        artifacts=[],
        attention_score=0.5,
        feedback_status="pending",
        run_id="run-1",
        created_at=datetime.datetime.utcnow(),
    )


def test_feedback_updates_posterior_and_reward_record():
    db = make_session()
    insight = make_insight()
    db.add(insight)
    db.commit()

    update = handle_feedback_routing(db, insight.insight_id, "useful", team_id="team-a")

    assert update["ranking_reward"] == 0.6
    assert update["posterior_updated"] is True
    assert update["posterior_update"]["delta_norm"] > 0
    assert db.query(FeedbackEvent).count() == 1
    assert db.query(RewardRecord).first().shaped_reward == 0.6
    assert db.query(BanditState).filter(BanditState.team_id == "team-a").first() is not None


def test_wrong_feedback_routes_to_review_without_reward_and_pauses_skill():
    db = make_session()
    insight = make_insight()
    db.add(insight)
    db.commit()

    for idx in range(3):
        update = handle_feedback_routing(
            db,
            insight.insight_id,
            "wrong_disagree",
            user_id=f"user-{idx}",
            team_id="team-a",
            user_comment="This calculation looks wrong.",
        )

    threshold = db.query(ThresholdState).filter(ThresholdState.skill_key == insight.skill_key).first()
    assert update["routed_to_review"] is True
    assert update["ranking_reward"] is None
    assert db.query(MethodologyReview).count() == 3
    assert db.query(FeedbackEvent).count() == 3
    assert db.query(RewardRecord).count() == 0
    assert threshold.skill_status == "paused"
    assert threshold.unreviewed_disagreement_count == 3


def test_l2_threshold_controller_adjusts_and_respects_floor():
    db = make_session()
    insight = make_insight()
    threshold = ThresholdState(
        skill_key=insight.skill_key,
        current_magnitude_threshold=0.10,
        current_confidence_threshold=0.80,
    )
    db.add_all([insight, threshold])
    db.commit()

    for idx in range(4):
        db.add(
            FeedbackEvent(
                feedback_id=f"negative-{idx}",
                insight_id=insight.insight_id,
                user_id=f"user-{idx}",
                team_id="team-a",
                signal_type="not_important",
                is_explicit=True,
            )
        )
    db.commit()

    run_weekly_l2_threshold_controller(db)
    db.refresh(threshold)
    assert threshold.current_confidence_threshold > 0.80
    assert threshold.current_magnitude_threshold > 0.10

    threshold.current_confidence_threshold = HARD_CONFIDENCE_FLOOR
    threshold.current_magnitude_threshold = HARD_MAGNITUDE_FLOOR
    db.query(FeedbackEvent).delete()
    for idx in range(4):
        db.add(
            FeedbackEvent(
                feedback_id=f"positive-{idx}",
                insight_id=insight.insight_id,
                user_id=f"user-{idx}",
                team_id="team-a",
                signal_type="acted_on",
                is_explicit=True,
            )
        )
    db.commit()

    run_weekly_l2_threshold_controller(db)
    db.refresh(threshold)
    assert threshold.current_confidence_threshold >= HARD_CONFIDENCE_FLOOR
    assert threshold.current_magnitude_threshold >= HARD_MAGNITUDE_FLOOR


def test_valence_parity_audit_flags_positive_only_surfacing():
    db = make_session()
    positive = make_insight("positive-1", direction="up", magnitude_relative=0.2)
    negative = make_insight("negative-1", direction="down", magnitude_relative=-0.2)
    db.add_all([positive, negative])
    db.commit()

    db.add(
        SurfacingRecord(
            insight_id=positive.insight_id,
            team_id="team-a",
            feed_position=1,
            logged_propensity=1.0,
            policy_version="v1_prior",
            is_exploration=False,
        )
    )
    db.commit()

    assert run_valence_parity_audit(db) == 0.0


def test_rank_feed_filters_invalid_insights_and_logs_propensity():
    db = make_session()
    valid = make_insight("valid", confidence=0.95, magnitude_relative=0.2)
    invalid = make_insight("invalid", confidence=0.30, magnitude_relative=0.01)
    db.add_all([valid, invalid])
    db.commit()

    ranked = rank_feed([valid, invalid], "team-a", db)

    assert [item["insight_id"] for item in ranked] == ["valid"]
    assert db.query(SurfacingRecord).count() == 1
    assert 0.0 < db.query(SurfacingRecord).first().logged_propensity <= 1.0
