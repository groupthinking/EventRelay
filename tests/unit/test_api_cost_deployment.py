"""Fail-closed checks for the API-cost PostgreSQL deployment substrate."""

from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
DEPLOY = ROOT / ".github/workflows/deploy-cloud-run.yml"
POSTGRES_CI = ROOT / ".github/workflows/api-cost-postgres.yml"


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_deployment_keeps_delivery_forcibly_disabled() -> None:
    text = _text(DEPLOY)
    assert "enable_api_cost_delivery" not in text
    assert "API_COST_DELIVERY_ENABLED=false" in text
    assert text.count("API_COST_TRACKING=true") >= 2
    assert "--remove-env-vars=API_COST_MONITOR_DB_PATH,API_COST_WEBHOOK_URL" in text
    assert "--remove-secrets=API_COST_WEBHOOK_URL" in text
    assert "API_COST_WEBHOOK_URL=" not in text


def test_runtime_database_secret_is_scoped_away_from_backend_database_url() -> None:
    text = _text(DEPLOY)
    assert (
        text.count(
            "API_COST_DATABASE_URL=EVENTRELAY_DATABASE_URL_DML:${{ steps.secret_versions.outputs.database_dml }}"
        )
        == 2
    )
    assert (
        text.count(
            "DATABASE_URL=EVENTRELAY_DATABASE_URL_DDL:${{ steps.secret_versions.outputs.database_ddl }}"
        )
        == 1
    )
    assert '--set-secrets="DATABASE_URL=EVENTRELAY_DATABASE_URL_DML' not in text
    assert ",DATABASE_URL=EVENTRELAY_DATABASE_URL_DML" not in text


def test_deployment_uses_wif_and_pinned_secret_versions() -> None:
    text = _text(DEPLOY)
    assert "workload_identity_provider:" in text
    assert "service_account:" in text
    assert "credentials_json:" not in text
    assert "GCP_SA_KEY" not in text
    assert ":latest" not in text
    assert "Resolve numeric secret versions" in text
    assert "^[0-9]+$" in text


def test_staging_builds_and_production_reuses_one_immutable_sha_image() -> None:
    text = _text(DEPLOY)
    assert "ARTIFACT_PROJECT_ID: ${{ vars.ARTIFACT_PROJECT_ID }}" in text
    assert "${REGION}-docker.pkg.dev/${ARTIFACT_PROJECT_ID}/${ARTIFACT_REPO}" in text
    assert '--project="${ARTIFACT_PROJECT_ID}"' in text
    assert "${{ github.sha }}" in text
    assert "docker build" in text
    assert text.count("docker build") == 1
    assert text.count("docker push") == 1
    assert "IMAGE_LATEST" not in text
    assert "image_summary.digest" in text
    assert 'IMMUTABLE_IMAGE="${IMAGE}@${DIGEST}"' in text
    assert text.count('--image="${{ steps.image.outputs.uri }}"') == 3
    assert "actions/upload-artifact@v7" in text
    assert "actions/download-artifact@v8" in text
    assert "overwrite: true" in text
    assert "api-cost-staging-${{ github.sha }}" in text
    assert "steps.release_gate.outputs.staging_run_id" in text
    build_step = text[text.index("Build and push staged immutable image") :]
    build_step = build_step[: build_step.index("Upload staged image manifest")]
    assert "inputs.environment == 'staging'" in build_step
    production_section = text[text.index("Download exact staged image manifest") :]
    production_section = production_section[
        : production_section.index("Select immutable image")
    ]
    assert "docker build" not in production_section
    assert "docker push" not in production_section


def test_migration_grant_job_precedes_worker_and_api() -> None:
    text = _text(DEPLOY)
    migration = text.index("youtube_extension.backend.api_cost_migrate")
    execute = text.index("gcloud run jobs execute")
    worker = text.index("Deploy disabled dedicated worker")
    api = text.index("Deploy API candidate without traffic")
    assert migration < execute < worker < api


def test_worker_has_singleton_always_on_cloud_run_contract() -> None:
    text = _text(DEPLOY)
    assert "--min=1" in text
    assert "--max=1" in text
    assert "--concurrency=1" in text
    assert "--no-cpu-throttling" in text
    assert "--startup-probe=httpGet.path=/readyz" in text
    assert "--liveness-probe=httpGet.path=/healthz" in text


def test_deployment_attaches_cloud_sql_and_uses_canonical_domain_service() -> None:
    text = _text(DEPLOY)
    mapping = _text(ROOT / "infrastructure/cloudrun/domain-mapping.yaml")
    assert "API_SERVICE: uvai-backend" in text
    assert "routeName: uvai-backend" in mapping
    assert "--set-cloudsql-instances" in text
    assert text.count("--set-cloudsql-instances") == 2
    assert text.count("--add-cloudsql-instances") == 1
    assert "CLOUD_SQL_INSTANCE_CONNECTION_NAME" in text
    assert text.count("API_COST_RUNTIME_DB_ROLE=${API_COST_RUNTIME_DB_ROLE}") == 3


def test_production_deploy_is_exact_main_sha_and_serialized() -> None:
    text = _text(DEPLOY)
    assert "commit_sha" in text
    assert "refs/heads/main" in text
    assert "origin/main" in text
    assert "cancel-in-progress: false" in text
    assert "PostgreSQL migration matrix" in text
    assert '"fresh"' in text
    assert '"from-002"' in text
    assert '"round-trip"' in text
    assert "deployments?sha=${REQUESTED_SHA}&environment=staging" in text
    assert "Latest staging deployment" in text
    assert "staging_run_id" in text
    assert "actions/runs/${staging_run_id}" in text
    assert ".head_sha == $sha" in text
    assert '.conclusion == "success"' in text
    assert '.path | split("@")[0]' in text
    assert '".github/workflows/deploy-cloud-run.yml"' in text
    assert "staging_deployment_ids" not in text
    assert "while IFS= read -r deployment_id" not in text


def test_runtime_identities_are_distinct_and_secret_access_is_partitioned() -> None:
    text = _text(DEPLOY)
    compact = " ".join(text.replace("\\", " ").split())
    assert (
        "API, worker, and migration service accounts must be pairwise distinct" in text
    )
    assert "assert_no_direct_secret_accessor" in text
    assert (
        'assert_no_direct_secret_accessor "${MIGRATION_SERVICE_ACCOUNT}" '
        "EVENTRELAY_DATABASE_URL_DML" in compact
    )
    assert (
        'assert_no_direct_secret_accessor "${WORKER_RUNTIME_SERVICE_ACCOUNT}" '
        "EVENTRELAY_DATABASE_URL_DDL" in compact
    )
    assert (
        'assert_no_direct_secret_accessor "${current_service_account}" '
        "EVENTRELAY_DATABASE_URL_DDL" in compact
    )
    for secret in (
        "GEMINI_API_KEY",
        "OPENAI_API_KEY",
        "YOUTUBE_API_KEY",
        "EVENTRELAY_API_KEY",
    ):
        assert secret in text
    assert "must not have direct accessor binding" in text


def test_migration_job_is_serial_and_staging_reconciles_twice() -> None:
    text = _text(DEPLOY)
    assert "--tasks=1" in text
    assert "--parallelism=1" in text
    assert "migration_execution_primary" in text
    assert "migration_execution_reconcile" in text
    assert "inputs.environment == 'staging'" in text


def test_existing_api_identity_and_attachments_are_preserved() -> None:
    text = _text(DEPLOY)
    assert "Inventory existing API service" in text
    assert "current_service_account" in text
    assert (
        'test "${current_service_account}" = "${API_RUNTIME_SERVICE_ACCOUNT}"' in text
    )
    api_section = text[text.index("Deploy API candidate without traffic") :]
    assert '--service-account="${API_RUNTIME_SERVICE_ACCOUNT}"' not in api_section
    assert "previous_cloudsql" in text
    assert "Candidate lost an existing Cloud SQL attachment" in text


def test_preflight_uses_untagged_current_serving_revision_and_rejects_legacy_webhook() -> (
    None
):
    text = _text(DEPLOY)
    assert "latestCreatedRevisionName" in text
    assert "latestReadyRevisionName" in text
    assert "must equal the sole 100-percent serving revision" in text
    assert "Pre-existing Cloud Run traffic tags are forbidden" in text
    assert "gcloud run revisions describe" in text
    assert "Serving revision still mounts API_COST_WEBHOOK_URL" in text
    rollback_probe = text.index("Verify known-good rollback target before mutation")
    assert text.index("Inventory existing API service") < rollback_probe
    assert rollback_probe < text.index("youtube_extension.backend.api_cost_migrate")
    rollback_section = text[
        rollback_probe : text.index("Resolve numeric secret versions")
    ]
    assert '"${service_url}/api/v1/health"' in rollback_section
    assert "--connect-timeout" in rollback_section
    assert "--max-time" in rollback_section


def test_candidate_tag_and_service_level_scaling_are_fail_closed() -> None:
    text = _text(DEPLOY)
    api_section = text[text.index("Deploy API candidate without traffic") :]
    assert "--min=1" in api_section
    assert "--max=10" in api_section
    assert "--min-instances=1" not in api_section
    assert "--max-instances=10" not in api_section
    assert "Remove candidate tag before promotion" in text
    assert "Remove candidate tag after failed rollout" in text
    assert text.count("--remove-tags") >= 2


def test_api_traffic_is_promoted_then_revision_and_domain_are_smoked() -> None:
    text = _text(DEPLOY)
    assert "gcloud run services update-traffic" in text
    assert "--to-revisions" in text
    assert "status.traffic" in text
    assert "https://api.uvai.io/readyz" in text
    assert "https://api.uvai.io/api/v1/health" in text
    assert "previous_revision" in text
    assert "Rollback API traffic after failed rollout" in text
    assert "failure()" in text
    assert "steps.promote.outcome" in text
    rollback = text[text.index("Rollback API traffic after failed rollout") :]
    rollback = rollback[: rollback.index("Remove candidate tag after failed rollout")]
    assert '"${service_url}/api/v1/health"' in rollback
    assert '"${service_url}/readyz"' not in rollback


def test_deploy_has_bounded_network_calls_and_complete_evidence() -> None:
    text = _text(DEPLOY)
    assert "timeout-minutes:" in text
    assert "--connect-timeout" in text
    assert "--max-time" in text
    assert "Migration execution (primary)" in text
    assert "Worker revision" in text
    assert "Gemini secret version" in text
    assert "OpenAI secret version" in text
    assert "YouTube secret version" in text
    assert "EventRelay secret version" in text


def test_legacy_cloud_run_entrypoints_fail_closed() -> None:
    deploy_sh = _text(ROOT / "infrastructure/cloudrun/deploy.sh")
    cloudbuild = _text(ROOT / "infrastructure/cloudrun/cloudbuild.yaml")
    service = _text(ROOT / "infrastructure/cloudrun/service.yaml")
    setup = _text(ROOT / "infrastructure/cloudrun/setup.sh")
    scripts_deploy = _text(ROOT / "scripts/deployment/deploy-cloud-run.sh")
    assert "RETIRED" in deploy_sh and "exit 1" in deploy_sh
    assert "RETIRED" in cloudbuild and "exit 1" in cloudbuild
    assert "RETIRED" in service and "retired: true" in service
    assert "RETIRED" in setup and "exit 1" in setup
    assert "RETIRED" in scripts_deploy and "exit 1" in scripts_deploy
    assert "gcloud " not in setup
    assert "gcloud " not in scripts_deploy


def test_postgres_ci_runs_real_migration_matrix_and_runtime_tests() -> None:
    text = _text(POSTGRES_CI)
    parsed = yaml.safe_load(text)
    assert parsed["jobs"]["migration-matrix"]["services"]["postgres"]
    assert "api_cost_ddl" in text
    assert "api_cost_runtime" in text
    assert "youtube_extension.backend.api_cost_migrate" in text
    assert "alembic downgrade" in text
    assert text.count("alembic upgrade head") >= 2
    assert "tests/integration/test_api_cost_postgres.py" in text
    assert 'API_COST_TEST_DISPOSABLE_DATABASE: "true"' in text
