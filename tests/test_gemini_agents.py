import asyncio
import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.database import Base
from backend.dataset_environment import (
    DatasetEnvironmentError,
    get_baked_environment_id,
    get_dataset_profile,
    resolve_analysis_environment,
)
from backend.env import load_project_env
from backend.gemini_agents import (
    GeminiAgentClient,
    GeminiAgentResult,
    GeminiInteractionRecord,
    extract_json_payload,
    normalize_insights,
    resolve_gemini_mode,
)
from backend.models import AnalysisDefinition
from backend import orchestrator
from scripts.bake_gemini_environment import (
    INLINE_SOURCE_REPO,
    build_bake_prompt,
    compute_source_hash,
    update_manifest,
    validate_bake_result,
)
from scripts.bake_gemini_demo_environment import (
    build_demo_bake_prompt,
    compute_source_hash as compute_demo_source_hash,
    update_demo_manifest,
)


def test_extract_json_payload_accepts_fenced_object():
    payload = extract_json_payload(
        """Here are the findings:
        ```json
        {"insights": [{"title": "D7 retention fell", "summary": "Paid cohorts fell materially."}]}
        ```
        """
    )

    insights = normalize_insights(
        payload,
        default_group="retention-churn",
        default_skill="cohort-retention-curves",
    )

    assert insights[0]["group"] == "retention-churn"
    assert insights[0]["skill"] == "cohort-retention-curves"
    assert insights[0]["magnitude"]["unit"] == "index"


def test_extract_json_payload_accepts_surrounded_array():
    payload = extract_json_payload(
        'Agent notes before JSON [{"title": "ARPDAU warning", "summary": "Free tier ad yield is weak."}] done.'
    )

    insights = normalize_insights(
        payload,
        default_group="monetization-revenue",
        default_skill="arpu-arppu-arpdau",
    )

    assert len(insights) == 1
    assert insights[0]["confidence"] == 0.8
    assert insights[0]["business_impact"]["estimate_usd"] == 0.0


def test_resolve_gemini_mode_defaults_to_local_without_key(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_AGENT_MODE", raising=False)

    assert resolve_gemini_mode({}) == "local"
    assert resolve_gemini_mode({"execution_mode": "gemini"}) == "gemini"


def test_load_project_env_reads_temp_env_file(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text(
        "GEMINI_API_KEY=test-key\nGEMINI_AGENT_MODE=gemini\n",
        encoding="utf-8",
    )
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_AGENT_MODE", raising=False)

    loaded = load_project_env(env_file)

    assert loaded is True
    assert resolve_gemini_mode({}) == "gemini"
    assert os.getenv("GEMINI_API_KEY") == "test-key"


def test_load_project_env_preserves_existing_environment(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text("GEMINI_AGENT_MODE=gemini\n", encoding="utf-8")
    monkeypatch.setenv("GEMINI_AGENT_MODE", "local")

    load_project_env(env_file)

    assert os.getenv("GEMINI_AGENT_MODE") == "local"


def test_manifest_guard_accepts_baked_environment(tmp_path):
    manifest = tmp_path / "dataset-manifest.json"
    manifest.write_text(
        '{"environment_id": "env-abc123", "environment_status": "baked"}',
        encoding="utf-8",
    )

    assert get_baked_environment_id(manifest) == "env-abc123"


def test_manifest_guard_rejects_local_placeholder(tmp_path):
    manifest = tmp_path / "dataset-manifest.json"
    manifest.write_text(
        '{"environment_id": "local-baked-env", "environment_status": "baked"}',
        encoding="utf-8",
    )

    try:
        get_baked_environment_id(manifest)
    except DatasetEnvironmentError as exc:
        assert "local placeholder" in str(exc)
    else:
        raise AssertionError("Expected DatasetEnvironmentError")


def test_demo_manifest_resolution_accepts_demo_baked_environment(tmp_path):
    manifest = tmp_path / "demo-dataset-manifest.json"
    manifest.write_text(
        '{"environment_id": "env-demo123", "environment_status": "demo-baked"}',
        encoding="utf-8",
    )

    assert get_baked_environment_id(manifest, profile="demo") == "env-demo123"


def test_dataset_profile_from_config_and_env(monkeypatch):
    monkeypatch.setenv("GEMINI_DATASET_PROFILE", "demo")

    assert get_dataset_profile({}) == "demo"
    assert get_dataset_profile({"dataset_profile": "full"}) == "full"


def test_resolve_analysis_environment_uses_explicit_override(monkeypatch):
    monkeypatch.setenv("GEMINI_DATASET_PROFILE", "demo")

    assert resolve_analysis_environment({"environment": "env-debug"}) == "env-debug"


def test_bake_manifest_update_keeps_existing_dataset_metadata():
    original = {
        "dataset_version": "spotify-v1",
        "schema_hash": "hash-123",
        "row_counts": {"events": 1},
    }

    updated = update_manifest(
        original,
        environment_id="env-verified",
        generator_repo="https://example.test/repo.git",
        generator_sha="abc123",
        interaction_id="interaction-1",
    )

    assert updated["dataset_version"] == "spotify-v1"
    assert updated["row_counts"] == {"events": 1}
    assert updated["environment_id"] == "env-verified"
    assert updated["environment_status"] == "baked"
    assert updated["baked_interaction_id"] == "interaction-1"


def test_bake_manifest_update_records_inline_source_hash():
    updated = update_manifest(
        {"dataset_version": "spotify-v1"},
        environment_id="env-verified",
        generator_repo=INLINE_SOURCE_REPO,
        generator_sha="source-hash-123",
        interaction_id="interaction-1",
        generator_source_hash="source-hash-123",
    )

    assert updated["generator_repo"] == INLINE_SOURCE_REPO
    assert updated["generator_sha"] == "source-hash-123"
    assert updated["generator_source_hash"] == "source-hash-123"


def test_compute_source_hash_changes_with_source_content():
    first = compute_source_hash({"scripts/generate_data.py": "print('a')"})
    second = compute_source_hash({"scripts/generate_data.py": "print('b')"})

    assert first != second


def test_bake_prompt_embeds_local_source_bundle():
    prompt = build_bake_prompt(
        source_bundle={
            "scripts/generate_data.py": "print('generate')",
            "scripts/verify_data.py": "print('verify')",
            "requirements.txt": "pandas>=2.0.0\n",
        },
        generator_source_hash="source-hash-123",
        expected_schema_hash="schema-hash-123",
        seed=42,
    )

    assert "SOURCE_BUNDLE_BASE64_JSON" in prompt
    assert "Do not clone any repository" in prompt
    assert "python scripts/generate_data.py" in prompt
    assert "EXPECTED_SCHEMA_HASH=schema-hash-123" in prompt
    assert "GENERATOR_SOURCE_HASH=source-hash-123" in prompt


def test_demo_bake_prompt_uses_small_demo_source():
    prompt = build_demo_bake_prompt(
        {
            "scripts/generate_demo_data.py": "print('demo generate')",
            "scripts/verify_demo_data.py": "print('demo verify')",
            "requirements.txt": "pandas>=2.0.0\n",
        },
        "demo-source-hash",
    )

    assert "SOURCE_BUNDLE_BASE64_JSON" in prompt
    assert "generate_demo_data.py" in prompt
    assert "DEMO_VERIFICATION_PASSED" in prompt
    assert "DEMO_GENERATOR_SOURCE_HASH=demo-source-hash" in prompt


def test_demo_manifest_update_records_demo_status():
    updated = update_demo_manifest(
        {"dataset_version": "spotify-demo-v1"},
        environment_id="env-demo",
        source_hash="demo-hash",
        interaction_id="interaction-demo",
    )

    assert updated["dataset_profile"] == "demo"
    assert updated["environment_status"] == "demo-baked"
    assert updated["generator_repo"] == "inline-demo-source"
    assert updated["generator_source_hash"] == "demo-hash"


def test_demo_source_hash_changes_with_content():
    assert compute_demo_source_hash({"a": "1"}) != compute_demo_source_hash({"a": "2"})


def test_bake_result_validation_requires_hash_and_environment():
    validate_bake_result("Computed Schema Hash: hash-123", "hash-123", "env-1")

    try:
        validate_bake_result("Computed Schema Hash: other", "hash-123", "env-1")
    except RuntimeError as exc:
        assert "expected schema hash" in str(exc)
    else:
        raise AssertionError("Expected RuntimeError")


def test_gemini_client_uses_manifest_environment(monkeypatch):
    captured = {}

    async def fake_create_interaction(**kwargs):
        captured.update(kwargs)
        return GeminiInteractionRecord(
            interaction_id="interaction-1",
            environment_id="env-run",
            output_text='[{"title": "Finding", "summary": "A useful insight."}]',
        )

    monkeypatch.setattr(
        "backend.gemini_agents.resolve_analysis_environment",
        lambda config: config.get("environment") or "env-baked",
    )

    client = object.__new__(GeminiAgentClient)
    client._create_interaction = fake_create_interaction
    definition = AnalysisDefinition(
        key="cohort-retention-curves",
        name="Cohort Retention Curves",
        description="Retention by cohort.",
        group_key="retention-churn",
        group_name="Retention & Churn",
        agent_id="retention-analyst",
        default_config={"date_range": "30d"},
    )

    asyncio.run(client.run_single_analysis(definition, {}))

    assert captured["environment"] == "env-baked"


def test_gemini_client_allows_explicit_environment_override(monkeypatch):
    captured = {}

    async def fake_create_interaction(**kwargs):
        captured.update(kwargs)
        return GeminiInteractionRecord(
            interaction_id="interaction-1",
            environment_id="env-run",
            output_text='[{"title": "Finding", "summary": "A useful insight."}]',
        )

    monkeypatch.setattr(
        "backend.gemini_agents.resolve_analysis_environment",
        lambda config: config.get("environment") or "env-baked",
    )

    client = object.__new__(GeminiAgentClient)
    client._create_interaction = fake_create_interaction
    definition = AnalysisDefinition(
        key="cohort-retention-curves",
        name="Cohort Retention Curves",
        description="Retention by cohort.",
        group_key="retention-churn",
        group_name="Retention & Churn",
        agent_id="retention-analyst",
        default_config={"date_range": "30d"},
    )

    asyncio.run(client.run_single_analysis(definition, {"environment": "env-debug"}))

    assert captured["environment"] == "env-debug"


def test_gemini_demo_agent_override_still_uses_interactions(monkeypatch):
    captured = {}

    async def fake_create_interaction(**kwargs):
        captured.update(kwargs)
        return GeminiInteractionRecord(
            interaction_id="interaction-demo",
            environment_id="env-demo-run",
            output_text='[{"title": "Demo finding", "summary": "A demo insight."}]',
        )

    monkeypatch.setenv("GEMINI_DATASET_PROFILE", "demo")
    monkeypatch.setenv("GEMINI_DEMO_AGENT_ID", "antigravity-preview-05-2026")
    monkeypatch.setattr(
        "backend.gemini_agents.resolve_analysis_environment",
        lambda config: "env-demo-baked",
    )

    client = object.__new__(GeminiAgentClient)
    client._create_interaction = fake_create_interaction
    definition = AnalysisDefinition(
        key="cohort-retention-curves",
        name="Cohort Retention Curves",
        description="Retention by cohort.",
        group_key="retention-churn",
        group_name="Retention & Churn",
        agent_id="retention-analyst",
        default_config={"date_range": "30d"},
    )

    asyncio.run(client.run_single_analysis(definition, {}))

    assert captured["agent"] == "antigravity-preview-05-2026"
    assert captured["environment"] == "env-demo-baked"
    assert "small fake Spotify" in captured["input"]


def test_execute_gemini_run_routes_single_analysis(monkeypatch):
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(bind=engine)
    db = session_factory()
    db.add(
        AnalysisDefinition(
            key="cohort-retention-curves",
            name="Cohort Retention Curves",
            description="Retention by cohort.",
            group_key="retention-churn",
            group_name="Retention & Churn",
            agent_id="retention-analyst",
            default_config={"date_range": "30d"},
        )
    )
    db.commit()

    class FakeGeminiClient:
        async def run_single_analysis(self, definition, config):
            return GeminiAgentResult(
                insights=[
                    {
                        "title": "Cohort drop detected",
                        "summary": "D7 retention declined for paid cohorts.",
                        "group": definition.group_key,
                        "skill": definition.key,
                    }
                ],
                interaction_ids=["interaction-123"],
                environment_id="env-123",
            )

    async def noop_notify(*args, **kwargs):
        return None

    monkeypatch.setattr(orchestrator, "GeminiAgentClient", lambda: FakeGeminiClient())
    monkeypatch.setattr(orchestrator, "notify_log", noop_notify)

    result = asyncio.run(
        orchestrator.execute_gemini_run(
            db,
            "run-123",
            "single",
            "cohort-retention-curves",
            {},
        )
    )

    assert result.interaction_ids == ["interaction-123"]
    assert result.environment_id == "env-123"
    assert result.insights[0]["skill"] == "cohort-retention-curves"

    db.close()
