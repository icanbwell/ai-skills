from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, Mock, patch

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from langchain_ai_skills_framework.github import (
    GitHubAppTokenProvider,
    GitHubTokenProvider,
    StaticTokenProvider,
)


def _generate_test_rsa_private_key() -> str:
    """Generate a throwaway RSA private key, PEM-encoded, for signing test JWTs only."""
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pem = key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    return pem.decode("utf-8")


TEST_RSA_PRIVATE_KEY = _generate_test_rsa_private_key()


class TestStaticTokenProvider:
    async def test_get_token_returns_configured_token(self) -> None:
        provider = StaticTokenProvider(token="ghp_test123")
        token = await provider.get_token()
        assert token == "ghp_test123"

    def test_get_token_sync_returns_configured_token(self) -> None:
        provider = StaticTokenProvider(token="ghp_test456")
        token = provider.get_token_sync()
        assert token == "ghp_test456"

    def test_satisfies_protocol(self) -> None:
        provider = StaticTokenProvider(token="ghp_test")
        assert isinstance(provider, GitHubTokenProvider)


class TestGitHubAppTokenProvider:
    async def test_mints_token_on_first_call(self) -> None:
        provider = GitHubAppTokenProvider(
            app_id="12345",
            private_key=TEST_RSA_PRIVATE_KEY,
            installation_id="67890",
        )

        mock_response = Mock()
        mock_response.json.return_value = {
            "token": "ghs_xxx",
            "expires_at": "2099-01-01T00:00:00Z",
        }
        mock_response.raise_for_status = Mock()

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.post.return_value = mock_response
            mock_client_class.return_value = mock_client

            token = await provider.get_token()

            assert token == "ghs_xxx"
            mock_client.post.assert_called_once()
            call_args = mock_client.post.call_args
            assert "/app/installations/67890/access_tokens" in call_args[0][0]
            assert call_args[1]["headers"]["Accept"] == "application/vnd.github+json"

    async def test_caches_token_within_expiry_window(self) -> None:
        provider = GitHubAppTokenProvider(
            app_id="12345",
            private_key=TEST_RSA_PRIVATE_KEY,
            installation_id="67890",
        )

        mock_response = Mock()
        mock_response.json.return_value = {
            "token": "ghs_cached",
            "expires_at": "2099-01-01T00:00:00Z",
        }
        mock_response.raise_for_status = Mock()

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.post.return_value = mock_response
            mock_client_class.return_value = mock_client

            token1 = await provider.get_token()
            token2 = await provider.get_token()

            assert token1 == "ghs_cached"
            assert token2 == "ghs_cached"
            mock_client.post.assert_called_once()

    async def test_refreshes_expired_token(self) -> None:
        provider = GitHubAppTokenProvider(
            app_id="12345",
            private_key=TEST_RSA_PRIVATE_KEY,
            installation_id="67890",
        )

        mock_response_expired = Mock()
        mock_response_expired.json.return_value = {
            "token": "ghs_expired",
            "expires_at": "2020-01-01T00:00:00Z",
        }
        mock_response_expired.raise_for_status = Mock()

        mock_response_fresh = Mock()
        mock_response_fresh.json.return_value = {
            "token": "ghs_fresh",
            "expires_at": "2099-01-01T00:00:00Z",
        }
        mock_response_fresh.raise_for_status = Mock()

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.post.side_effect = [mock_response_expired, mock_response_fresh]
            mock_client_class.return_value = mock_client

            token1 = await provider.get_token()
            assert token1 == "ghs_expired"

            token2 = await provider.get_token()
            assert token2 == "ghs_fresh"
            assert mock_client.post.call_count == 2

    def test_get_token_sync_works(self) -> None:
        provider = GitHubAppTokenProvider(
            app_id="12345",
            private_key=TEST_RSA_PRIVATE_KEY,
            installation_id="67890",
        )

        mock_response = Mock()
        mock_response.json.return_value = {
            "token": "ghs_sync",
            "expires_at": "2099-01-01T00:00:00Z",
        }
        mock_response.raise_for_status = Mock()

        with patch("httpx.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client.__enter__.return_value = mock_client
            mock_client.__exit__.return_value = None
            mock_client.post.return_value = mock_response
            mock_client_class.return_value = mock_client

            token = provider.get_token_sync()

            assert token == "ghs_sync"
            mock_client.post.assert_called_once()
            call_args = mock_client.post.call_args
            assert "/app/installations/67890/access_tokens" in call_args[0][0]
            assert call_args[1]["headers"]["Accept"] == "application/vnd.github+json"

    def test_satisfies_protocol(self) -> None:
        provider = GitHubAppTokenProvider(
            app_id="12345",
            private_key=TEST_RSA_PRIVATE_KEY,
            installation_id="67890",
        )
        assert isinstance(provider, GitHubTokenProvider)
