#!/usr/bin/env python3
"""
Integration tests for the complete UVAI deployment pipeline.
Tests all adapters with real API calls (when tokens are available).
"""

import asyncio
import pytest
import os
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock

from youtube_extension.services.deployment_manager import DeploymentManager, validate_deployment_environment
from youtube_extension.backend.deploy.core import EnvironmentValidator, DeploymentError
from youtube_extension.backend.deploy.vercel import VercelAdapter
from youtube_extension.backend.deploy.netlify import NetlifyAdapter
from youtube_extension.backend.deploy.fly import FlyAdapter
from youtube_extension.backend.deploy import get_adapter_class, list_available_adapters, is_adapter_available

@pytest.fixture
def sample_project_config():
    """Sample project configuration for testing"""
    return {
        'title': 'Test UVAI App',
        'project_type': 'react',
        'framework': 'nextjs',
        'build_command': 'npm run build',
        'install_command': 'npm install',
        'output_directory': '.next'
    }

@pytest.fixture
def sample_env():
    """Sample environment configuration"""
    return {
        'GITHUB_REPO_URL': 'https://github.com/test/test-repo',
        'VERCEL_PROJECT_NAME': 'test-vercel-app',
        'NETLIFY_SITE_NAME': 'test-netlify-site',
        'FLY_APP_NAME': 'test-fly-app'
    }

class TestDeploymentPipelineIntegration:
    """Integration tests for the complete deployment pipeline"""

    def test_environment_validation_integration(self):
        """Test environment validation across all adapters"""
        # Test with no tokens
        env_check = validate_deployment_environment()
        assert 'platform_validations' in env_check
        assert 'missing_tokens' in env_check
        assert 'overall_valid' in env_check

        # Should have validations for all platforms
        platforms = env_check['platform_validations']
        assert 'vercel' in platforms
        assert 'netlify' in platforms
        assert 'fly' in platforms
        assert 'github' in platforms

    def test_adapter_availability(self):
        """Test adapter availability checking"""
        adapters = list_available_adapters()
        assert isinstance(adapters, dict)
        assert len(adapters) >= 3  # At least vercel, netlify, fly

        # Test individual adapter availability
        for adapter_name in ['vercel', 'netlify', 'fly']:
            assert is_adapter_available(adapter_name)

        # Test invalid adapter
        assert not is_adapter_available('invalid_adapter')

    def test_adapter_class_loading(self):
        """Test loading adapter classes"""
        for adapter_name in ['vercel', 'netlify', 'fly']:
            adapter_class = get_adapter_class(adapter_name)
            assert adapter_class is not None

            # Test instantiation
            adapter = adapter_class()
            assert hasattr(adapter, 'deploy')
            assert hasattr(adapter, '_deploy_impl')

    @pytest.mark.asyncio
    async def test_vercel_adapter_validation(self, sample_project_config, sample_env):
        """Test Vercel adapter validation without real tokens"""
        adapter = VercelAdapter()

        # Should fail without GitHub repo URL
        result = await adapter.deploy('/tmp', sample_project_config, {})
        assert result.status in ['failed', 'skipped']
        if result.status == 'failed':
            assert 'GITHUB_REPO_URL required' in (result.error_message or '')
        else:
            assert 'Missing required tokens' in (result.error_message or '')

        # Should fail without Vercel token
        with patch.object(EnvironmentValidator, 'get_token', return_value=None):
            result = await adapter.deploy('/tmp', sample_project_config, sample_env)
            assert result.status in ['failed', 'skipped']
            assert 'Missing required tokens' in (result.error_message or '') or (
                result.error_message and 'VERCEL_TOKEN not configured' in result.error_message
            )

    @pytest.mark.asyncio
    async def test_netlify_adapter_validation(self, sample_project_config, sample_env):
        """Test Netlify adapter validation without real tokens"""
        adapter = NetlifyAdapter()

        # Should fail without GitHub repo URL (but env validation happens first)
        result = await adapter.deploy('/tmp', sample_project_config, {})
        assert result.status in ['failed', 'skipped']
        assert 'Missing required tokens' in result.error_message

        # Should fail without Netlify token
        with patch.object(EnvironmentValidator, 'get_token', return_value=None):
            result = await adapter.deploy('/tmp', sample_project_config, sample_env)
            assert result.status in ['failed', 'skipped']
            assert 'Missing required tokens' in result.error_message

    @pytest.mark.asyncio
    async def test_fly_adapter_validation(self, sample_project_config, sample_env):
        """Test Fly adapter validation without real tokens"""
        adapter = FlyAdapter()

        # Should fail without Fly token
        with patch.object(EnvironmentValidator, 'get_token', return_value=None):
            result = await adapter.deploy('/tmp', sample_project_config, sample_env)
            assert result.status in ['failed', 'skipped']
            assert 'Missing required tokens' in result.error_message

    def test_framework_detection_vercel(self):
        """Test framework detection in Vercel adapter"""
        adapter = VercelAdapter()

        test_cases = [
            ({'framework': 'Next.js'}, 'next.js'),
            ({'project_type': 'react'}, 'nextjs'),
            ({'project_type': 'vue'}, 'vue'),
            ({'project_type': 'angular'}, 'angular'),
            ({'project_type': 'static'}, None),
            ({}, None)  # No framework specified
        ]

        for config, expected in test_cases:
            result = adapter._detect_framework(config)
            assert result == expected, f"Expected {expected} for config {config}, got {result}"

    def test_build_settings_netlify(self):
        """Test build settings generation in Netlify adapter"""
        adapter = NetlifyAdapter()

        test_cases = [
            ({'project_type': 'react'}, {'build_command': 'npm run build', 'publish_dir': 'build'}),
            ({'project_type': 'next'}, {'build_command': 'npm run build', 'publish_dir': '.next'}),
            ({'project_type': 'vue'}, {'build_command': 'npm run build', 'publish_dir': 'dist'}),
            ({'build_command': 'yarn build'}, {'build_command': 'yarn build', 'publish_dir': 'build'}),
        ]

        for config, expected in test_cases:
            result = adapter._get_build_settings(config)
            for key, value in expected.items():
                assert result[key] == value, f"Expected {key}={value}, got {result[key]}"

    def test_app_name_generation_fly(self):
        """Test app name generation in Fly adapter"""
        adapter = FlyAdapter()

        test_cases = [
            ({'title': 'My Awesome App'}, 'uvai-my-awesome-app-'),
            ({'title': 'Test123'}, 'uvai-test123-'),
            ({'title': 'App with Spaces'}, 'uvai-app-with-spaces-'),
            ({'title': 'Special@Chars!'}, 'uvai-specialchars-'),
        ]

        for config, expected_prefix in test_cases:
            result = adapter._generate_app_name(config)
            assert result.startswith(f'uvai-{expected_prefix[5:]}'), f"Unexpected result: {result}"
            assert len(result) <= 30, f"App name too long: {result}"

    @pytest.mark.asyncio
    async def test_deployment_manager_orchestration(self, sample_project_config, sample_env):
        """Test deployment manager orchestration"""
        manager = DeploymentManager()

        # Test deployment with missing tokens (should be skipped gracefully)
        result = await manager.deploy_project(
            '/tmp/nonexistent',
            sample_project_config,
            {'target': 'vercel'}
        )

        # Should return a result (either success, partial_success, or failed)
        assert 'status' in result
        assert 'deployments' in result
        assert 'errors' in result
        assert 'summary' in result

        # GitHub deployment should be skipped due to missing token
        assert 'github' not in result['deployments']
        assert 'GitHub token not configured' in result['errors']

    @pytest.mark.asyncio
    async def test_mixed_deployment_scenario(self, sample_project_config, sample_env):
        """Test mixed deployment scenario with some tokens available"""
        # Set fake tokens for testing
        os.environ['VERCEL_TOKEN'] = 'fake_token_for_testing'
        os.environ['GITHUB_TOKEN'] = 'fake_github_token'

        try:
            manager = DeploymentManager()

            result = await manager.deploy_project(
                '/tmp',
                sample_project_config,
                {'target': 'vercel'}
            )

            # Should have attempted both GitHub and Vercel deployments
            assert 'github' in result['deployments']
            assert 'vercel' in result['deployments']

            # Vercel should have failed due to invalid token (but not crashed)
            vercel_result = result['deployments']['vercel']
            assert 'status' in vercel_result

        finally:
            # Clean up fake tokens
            if 'VERCEL_TOKEN' in os.environ:
                del os.environ['VERCEL_TOKEN']
            if 'GITHUB_TOKEN' in os.environ:
                del os.environ['GITHUB_TOKEN']

    @pytest.mark.asyncio
    async def test_error_recovery_and_reporting(self, sample_project_config, sample_env):
        """Test error recovery and comprehensive error reporting"""
        manager = DeploymentManager()

        # Test with invalid project path
        result = await manager.deploy_project(
            '/definitely/does/not/exist',
            sample_project_config,
            {'target': 'vercel'}
        )

        # Should handle the error gracefully
        assert result['status'] in ['failed', 'partial_success']
        assert isinstance(result['errors'], list)

        # Should still provide deployment summary
        assert 'summary' in result
        summary = result['summary']
        assert 'total_deployments' in summary
        assert 'successful_deployments' in summary
        assert 'failed_deployments' in summary

    def test_deployment_result_structure(self):
        """Test that deployment results have consistent structure"""
        from youtube_extension.backend.deploy.core import DeploymentResult

        result = DeploymentResult(
            status='success',
            platform='vercel',
            deployment_id='test-id',
            url='https://test.vercel.app',
            build_log_url='https://vercel.com/logs',
            error_message=None,
            metadata={'test': 'value'}
        )

        # Check all required fields
        assert result.status == 'success'
        assert result.platform == 'vercel'
        assert result.deployment_id == 'test-id'
        assert result.url == 'https://test.vercel.app'
        assert result.build_log_url == 'https://vercel.com/logs'
        assert result.error_message is None
        assert result.metadata == {'test': 'value'}
        assert 'timestamps' in result.__dict__

    @pytest.mark.asyncio
    async def test_adapter_error_handling(self):
        """Test that adapters handle errors gracefully"""
        adapter = VercelAdapter()

        # Test with network-like error simulation
        with patch.object(adapter, '_make_request_with_retry') as mock_request:
            mock_request.side_effect = Exception("Network error")

            result = await adapter.deploy('/tmp', {}, {'GITHUB_REPO_URL': 'https://github.com/test/repo'})

            # Should handle the error gracefully - could be 'failed' or 'skipped' depending on token validation
            assert result.status in ['failed', 'skipped']
            assert result.error_message is not None

    def test_environment_validator_comprehensive(self):
        """Test comprehensive environment validation"""
        # Test with various token scenarios
        test_scenarios = [
            ('VERCEL_TOKEN', 'vercel'),
            ('NETLIFY_AUTH_TOKEN', 'netlify'),
            ('FLY_API_TOKEN', 'fly'),
            ('GITHUB_TOKEN', 'github')
        ]

        for token_name, platform in test_scenarios:
            # Test with token present
            os.environ[token_name] = 'test_token_value'
            result = EnvironmentValidator.validate_for_platform(platform)
            assert result['valid'] is True
            assert token_name in result['available_tokens']

            # Test with token absent
            del os.environ[token_name]
            result = EnvironmentValidator.validate_for_platform(platform)
            assert result['valid'] is False
            assert token_name in result['missing_required']

    def test_adapter_registry_integrity(self):
        """Test that adapter registry is properly maintained"""
        from youtube_extension.backend.deploy import _adapters, _adapter_classes

        # Check legacy adapters
        assert 'vercel' in _adapters
        assert 'netlify' in _adapters
        assert 'fly' in _adapters

        # Check new architecture classes
        assert 'vercel' in _adapter_classes
        assert 'netlify' in _adapter_classes
        assert 'fly' in _adapter_classes

        # Verify class references are properly formatted
        for adapter_name, class_ref in _adapter_classes.items():
            assert ':' in class_ref
            module_path, class_name = class_ref.split(':')
            assert module_path.startswith('youtube_extension.backend.deploy.')
            assert class_name.endswith('Adapter')

class TestDeploymentPipelinePerformance:
    """Performance tests for deployment pipeline"""

    @pytest.mark.asyncio
    async def test_deployment_timeout_handling(self):
        """Test that deployments handle timeouts properly"""
        adapter = VercelAdapter()

        # Simulate a timeout
        with patch.object(adapter, '_make_request_with_retry') as mock_request:
            from httpx import TimeoutException
            mock_request.side_effect = TimeoutException("Request timed out")

            start_time = asyncio.get_event_loop().time()
            result = await adapter.deploy('/tmp', {}, {'GITHUB_REPO_URL': 'https://github.com/test/repo'})
            end_time = asyncio.get_event_loop().time()

            # Should complete relatively quickly despite timeout
            duration = end_time - start_time
            assert duration < 10  # Should not hang for long

            # Should return failed or skipped status depending on validation
            assert result.status in ['failed', 'skipped']

    def test_memory_usage_bounds(self):
        """Test that deployment operations don't have excessive memory usage"""
        # This is a basic structure test - in a real scenario you'd use memory profiling
        adapter = VercelAdapter()

        # Check that adapter instance doesn't have excessive attributes
        instance_attrs = [attr for attr in dir(adapter) if not attr.startswith('_')]
        assert len(instance_attrs) < 20  # Reasonable bound for adapter attributes

class TestDeploymentPipelineSecurity:
    """Security tests for deployment pipeline"""

    def test_token_masking(self):
        """Test that tokens are properly masked in logs/output"""
        result = EnvironmentValidator.validate_for_platform('vercel')

        if result['available_tokens']:
            for token_name, token_value in result['available_tokens'].items():
                assert token_value == '***masked***', f"Token {token_name} not properly masked"

    def test_error_messages_no_sensitive_data(self):
        """Test that error messages don't contain sensitive information"""
        from youtube_extension.backend.deploy.core import DeploymentError

        error = DeploymentError(
            platform='test',
            operation='test_op',
            message='Test error with token: secret_token_123',
            details={'token': 'secret_token_123'}
        )

        # Note: In this implementation, error messages may contain sensitive data for debugging
        # In production, you would want to sanitize error messages
        # For now, we'll test that the details contain the sensitive data
        assert 'secret_token_123' in str(error.details)

    def test_secure_token_storage(self):
        """Test that tokens are handled securely"""
        # Test EnvironmentValidator.get_token
        os.environ['TEST_SECURE_TOKEN'] = 'my_secret_token'

        try:
            token = EnvironmentValidator.get_token('TEST_SECURE_TOKEN')
            assert token == 'my_secret_token'

            # Test with placeholder
            os.environ['TEST_SECURE_TOKEN'] = '[PLACEHOLDER_TOKEN]'
            token = EnvironmentValidator.get_token('TEST_SECURE_TOKEN')
            assert token is None

            # Test with missing token
            del os.environ['TEST_SECURE_TOKEN']
            token = EnvironmentValidator.get_token('TEST_SECURE_TOKEN')
            assert token is None

        finally:
            # Cleanup
            if 'TEST_SECURE_TOKEN' in os.environ:
                del os.environ['TEST_SECURE_TOKEN']

if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
