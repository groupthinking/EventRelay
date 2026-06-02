"""Unit tests for integrations/cloud_ai/config.py."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from youtube_extension.integrations.cloud_ai.config import CloudAIConfig, ProviderConfig
from youtube_extension.integrations.cloud_ai.exceptions import ConfigurationError


# ===========================================================================
# ProviderConfig
# ===========================================================================


class TestProviderConfigPostInit:
    def test_config_none_becomes_empty_dict(self):
        p = ProviderConfig()
        assert p.config == {}

    def test_explicit_config_preserved(self):
        p = ProviderConfig(config={"key": "val"})
        assert p.config["key"] == "val"

    def test_default_enabled_false(self):
        assert ProviderConfig().enabled is False

    def test_default_validated_false(self):
        assert ProviderConfig().validated is False

    def test_default_available_false(self):
        assert ProviderConfig().available is False

    def test_explicit_enabled(self):
        p = ProviderConfig(enabled=True)
        assert p.enabled is True


# ===========================================================================
# CloudAIConfig init and _load_config
# ===========================================================================


class TestCloudAIConfigInit:
    def test_three_providers_created(self):
        c = CloudAIConfig()
        assert set(c.providers.keys()) == {"google_cloud", "aws_rekognition", "azure_vision"}

    def test_all_providers_disabled_by_default(self):
        c = CloudAIConfig()
        for cfg in c.providers.values():
            assert cfg.enabled is False

    def test_no_config_dict(self):
        c = CloudAIConfig()
        for cfg in c.providers.values():
            assert cfg.config == {}

    def test_provider_config_updated_from_dict(self):
        c = CloudAIConfig({"google_cloud": {"project_id": "my-proj", "enabled": True}})
        assert c.providers["google_cloud"].config["project_id"] == "my-proj"

    def test_enabled_set_from_dict(self):
        c = CloudAIConfig({"aws_rekognition": {"enabled": True, "region": "us-east-1"}})
        assert c.providers["aws_rekognition"].enabled is True

    def test_unknown_provider_in_dict_ignored(self):
        c = CloudAIConfig({"unknown_provider": {"enabled": True}})
        assert "unknown_provider" not in c.providers

    def test_other_providers_unchanged_when_one_configured(self):
        c = CloudAIConfig({"google_cloud": {"enabled": True}})
        assert c.providers["azure_vision"].enabled is False


# ===========================================================================
# validate_all
# ===========================================================================


class TestValidateAll:
    def test_no_enabled_providers_returns_empty(self):
        c = CloudAIConfig()
        assert c.validate_all() == {}

    def test_enabled_provider_included_in_results(self):
        c = CloudAIConfig({"google_cloud": {"enabled": True}})
        results = c.validate_all()
        assert "google_cloud" in results

    def test_disabled_provider_excluded(self):
        c = CloudAIConfig({"google_cloud": {"enabled": True}, "azure_vision": {"enabled": False}})
        results = c.validate_all()
        assert "azure_vision" not in results

    def test_validate_all_returns_errors_list(self):
        c = CloudAIConfig({"google_cloud": {"enabled": True}})
        results = c.validate_all()
        assert isinstance(results["google_cloud"], list)


# ===========================================================================
# validate_provider
# ===========================================================================


class TestValidateProvider:
    def test_unknown_provider_returns_error_message(self):
        c = CloudAIConfig()
        errors = c.validate_provider("nonexistent")
        assert len(errors) == 1
        assert "Unknown provider" in errors[0]

    def test_valid_google_cloud_sets_validated_true(self, monkeypatch):
        monkeypatch.setenv("GOOGLE_APPLICATION_CREDENTIALS", "/path/creds.json")
        c = CloudAIConfig({"google_cloud": {
            "project_id": "my-proj",
            "location_id": "us-central1",
        }})
        errors = c.validate_provider("google_cloud")
        assert errors == []
        assert c.providers["google_cloud"].validated is True

    def test_errors_set_validated_false(self):
        c = CloudAIConfig()
        c.validate_provider("google_cloud")
        assert c.providers["google_cloud"].validated is False


# ===========================================================================
# _validate_google_cloud
# ===========================================================================


class TestValidateGoogleCloud:
    def test_missing_project_id_returns_error(self, monkeypatch):
        monkeypatch.setenv("GOOGLE_APPLICATION_CREDENTIALS", "/path/creds.json")
        c = CloudAIConfig()
        errors = c._validate_google_cloud({})
        assert any("project_id" in e for e in errors)

    def test_missing_credentials_returns_error(self, monkeypatch):
        monkeypatch.delenv("GOOGLE_APPLICATION_CREDENTIALS", raising=False)
        c = CloudAIConfig()
        errors = c._validate_google_cloud({"project_id": "proj"})
        assert any("credentials" in e.lower() for e in errors)

    def test_invalid_location_returns_error(self, monkeypatch):
        monkeypatch.setenv("GOOGLE_APPLICATION_CREDENTIALS", "/path/creds.json")
        c = CloudAIConfig()
        errors = c._validate_google_cloud({"project_id": "proj", "location_id": "invalid-region"})
        assert any("location" in e.lower() for e in errors)

    def test_valid_config_no_errors(self, monkeypatch):
        monkeypatch.setenv("GOOGLE_APPLICATION_CREDENTIALS", "/path/creds.json")
        c = CloudAIConfig()
        errors = c._validate_google_cloud({"project_id": "proj", "location_id": "us-central1"})
        assert errors == []

    def test_credentials_path_in_config_accepted(self, monkeypatch):
        monkeypatch.delenv("GOOGLE_APPLICATION_CREDENTIALS", raising=False)
        c = CloudAIConfig()
        errors = c._validate_google_cloud({
            "project_id": "proj",
            "credentials_path": "/path/creds.json",
            "location_id": "us-east1",
        })
        assert errors == []

    def test_default_location_valid(self, monkeypatch):
        monkeypatch.setenv("GOOGLE_APPLICATION_CREDENTIALS", "/path/creds.json")
        c = CloudAIConfig()
        errors = c._validate_google_cloud({"project_id": "proj"})
        assert not any("location" in e.lower() for e in errors)


# ===========================================================================
# _validate_aws_rekognition
# ===========================================================================


class TestValidateAWSRekognition:
    def test_missing_access_key_id_error(self):
        c = CloudAIConfig()
        errors = c._validate_aws_rekognition({})
        assert any("access_key_id" in e for e in errors)

    def test_missing_secret_key_error(self):
        c = CloudAIConfig()
        errors = c._validate_aws_rekognition({"aws_access_key_id": "key"})
        assert any("secret_access_key" in e for e in errors)

    def test_missing_region_error(self):
        c = CloudAIConfig()
        errors = c._validate_aws_rekognition({
            "aws_access_key_id": "key",
            "aws_secret_access_key": "secret",
        })
        assert any("region" in e for e in errors)

    def test_invalid_region_format_error(self):
        c = CloudAIConfig()
        errors = c._validate_aws_rekognition({
            "aws_access_key_id": "key",
            "aws_secret_access_key": "secret",
            "region": "bad",
        })
        assert any("region" in e.lower() for e in errors)

    def test_valid_aws_config_no_errors(self):
        c = CloudAIConfig()
        errors = c._validate_aws_rekognition({
            "aws_access_key_id": "key",
            "aws_secret_access_key": "secret",
            "region": "us-west-2",
        })
        assert errors == []


# ===========================================================================
# _validate_azure_vision
# ===========================================================================


class TestValidateAzureVision:
    def test_missing_subscription_key_error(self):
        c = CloudAIConfig()
        errors = c._validate_azure_vision({})
        assert any("subscription_key" in e for e in errors)

    def test_missing_endpoint_error(self):
        c = CloudAIConfig()
        errors = c._validate_azure_vision({"subscription_key": "key"})
        assert any("endpoint" in e for e in errors)

    def test_invalid_endpoint_format_error(self):
        c = CloudAIConfig()
        errors = c._validate_azure_vision({
            "subscription_key": "key",
            "endpoint": "http://not-https.example.com",
        })
        assert any("https" in e for e in errors)

    def test_valid_azure_config_no_errors(self):
        c = CloudAIConfig()
        errors = c._validate_azure_vision({
            "subscription_key": "key",
            "endpoint": "https://my-region.api.cognitive.microsoft.com/",
        })
        assert errors == []


# ===========================================================================
# get_provider_config
# ===========================================================================


class TestGetProviderConfig:
    def test_known_provider_returns_config(self):
        c = CloudAIConfig({"google_cloud": {"project_id": "proj"}})
        cfg = c.get_provider_config("google_cloud")
        assert cfg["project_id"] == "proj"

    def test_unknown_provider_raises_configuration_error(self):
        c = CloudAIConfig()
        with pytest.raises(ConfigurationError):
            c.get_provider_config("unknown")


# ===========================================================================
# is_provider_ready
# ===========================================================================


class TestIsProviderReady:
    def test_unknown_provider_returns_false(self):
        assert CloudAIConfig().is_provider_ready("nonexistent") is False

    def test_disabled_provider_not_ready(self):
        c = CloudAIConfig()
        assert c.is_provider_ready("google_cloud") is False

    def test_enabled_but_not_validated_not_ready(self):
        c = CloudAIConfig({"google_cloud": {"enabled": True}})
        assert c.is_provider_ready("google_cloud") is False

    def test_all_flags_set_returns_true(self):
        c = CloudAIConfig()
        p = c.providers["google_cloud"]
        p.enabled = True
        p.validated = True
        p.available = True
        assert c.is_provider_ready("google_cloud") is True


# ===========================================================================
# get_enabled_providers
# ===========================================================================


class TestGetEnabledProviders:
    def test_empty_when_none_ready(self):
        assert CloudAIConfig().get_enabled_providers() == []

    def test_returns_ready_provider(self):
        c = CloudAIConfig()
        p = c.providers["aws_rekognition"]
        p.enabled = True
        p.validated = True
        p.available = True
        assert "aws_rekognition" in c.get_enabled_providers()

    def test_excludes_non_available(self):
        c = CloudAIConfig()
        p = c.providers["azure_vision"]
        p.enabled = True
        p.validated = True
        p.available = False
        assert "azure_vision" not in c.get_enabled_providers()


# ===========================================================================
# check_dependencies
# ===========================================================================


class TestCheckDependencies:
    def test_returns_dict_with_three_keys(self):
        c = CloudAIConfig()
        result = c.check_dependencies()
        assert set(result.keys()) == {"google_cloud", "aws_rekognition", "azure_vision"}

    def test_values_are_bools(self):
        c = CloudAIConfig()
        result = c.check_dependencies()
        for val in result.values():
            assert isinstance(val, bool)


# ===========================================================================
# to_dict
# ===========================================================================


class TestToDict:
    def test_all_providers_present(self):
        d = CloudAIConfig().to_dict()
        assert set(d.keys()) == {"google_cloud", "aws_rekognition", "azure_vision"}

    def test_enabled_key_present(self):
        d = CloudAIConfig().to_dict()
        assert "enabled" in d["google_cloud"]

    def test_validated_key_present(self):
        d = CloudAIConfig().to_dict()
        assert "validated" in d["azure_vision"]


# ===========================================================================
# from_file
# ===========================================================================


class TestFromFile:
    def test_missing_file_raises_configuration_error(self, tmp_path):
        with pytest.raises(ConfigurationError):
            CloudAIConfig.from_file(str(tmp_path / "nonexistent.json"))

    def test_valid_json_file_loads(self, tmp_path):
        cfg_file = tmp_path / "config.json"
        cfg_file.write_text(json.dumps({"google_cloud": {"project_id": "proj"}}))
        c = CloudAIConfig.from_file(str(cfg_file))
        assert c.providers["google_cloud"].config["project_id"] == "proj"

    def test_invalid_json_raises_configuration_error(self, tmp_path):
        cfg_file = tmp_path / "bad.json"
        cfg_file.write_text("not json {{{")
        with pytest.raises(ConfigurationError):
            CloudAIConfig.from_file(str(cfg_file))


# ===========================================================================
# save_to_file
# ===========================================================================


class TestSaveToFile:
    def test_saves_json_file(self, tmp_path):
        c = CloudAIConfig()
        path = tmp_path / "out.json"
        c.save_to_file(str(path))
        assert path.exists()
        data = json.loads(path.read_text())
        assert "google_cloud" in data

    def test_roundtrip_via_json(self, tmp_path):
        c = CloudAIConfig({"aws_rekognition": {"region": "eu-west-1"}})
        path = tmp_path / "rt.json"
        c.save_to_file(str(path))
        loaded = CloudAIConfig.from_file(str(path))
        assert loaded.providers["aws_rekognition"].config["region"] == "eu-west-1"


# ===========================================================================
# from_environment
# ===========================================================================


class TestFromEnvironment:
    def test_google_disabled_when_env_not_set(self, monkeypatch):
        monkeypatch.delenv("GOOGLE_CLOUD_PROJECT", raising=False)
        c = CloudAIConfig.from_environment()
        assert c.providers["google_cloud"].enabled is False

    def test_google_enabled_when_env_set(self, monkeypatch):
        monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "my-project")
        c = CloudAIConfig.from_environment()
        assert c.providers["google_cloud"].enabled is True

    def test_aws_enabled_when_env_set(self, monkeypatch):
        # Official AWS example key from documentation (not a real credential)
        monkeypatch.setenv("AWS_ACCESS_KEY_ID", "AKIAIOSFODNN7EXAMPLE")
        c = CloudAIConfig.from_environment()
        assert c.providers["aws_rekognition"].enabled is True

    def test_azure_disabled_when_no_key(self, monkeypatch):
        monkeypatch.delenv("AZURE_COGNITIVE_SERVICES_KEY", raising=False)
        c = CloudAIConfig.from_environment()
        assert c.providers["azure_vision"].enabled is False
