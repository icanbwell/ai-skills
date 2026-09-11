"""Tests for PluginMcpServerEntry.visibility and coerce_mcp_visibility."""

from __future__ import annotations

from pathlib import Path

from langchain_ai_skills_framework.models.plugin_mcp_config import (
    PluginMcpServerEntry,
    coerce_mcp_visibility,
)


def _make_entry(**overrides: object) -> PluginMcpServerEntry:
    defaults: dict[str, object] = {
        "server_key": "my-server",
        "plugin_name": "test-plugin",
        "plugin_root": Path("/plugins/test-plugin"),
    }
    defaults.update(overrides)
    return PluginMcpServerEntry(**defaults)  # type: ignore[arg-type]


class TestPluginMcpServerEntryVisibility:
    """Backward-compatibility and explicit-value coverage for `visibility`."""

    def test_defaults_to_internal(self) -> None:
        """An entry constructed the way every existing caller already does
        (no `visibility` kwarg) must keep resolving to "internal"."""
        entry = _make_entry()

        assert entry.visibility == "internal"

    def test_explicit_internal(self) -> None:
        entry = _make_entry(visibility="internal")

        assert entry.visibility == "internal"

    def test_explicit_external(self) -> None:
        entry = _make_entry(visibility="external")

        assert entry.visibility == "external"

    def test_other_fields_unaffected(self) -> None:
        """Adding `visibility` must not disturb any other field's behavior."""
        entry = _make_entry(url="http://localhost:8080/mcp", auth="oauth2")

        assert entry.url == "http://localhost:8080/mcp"
        assert entry.auth == "oauth2"
        assert entry.visibility == "internal"
        assert entry.namespaced_key == "test-plugin__my-server"
        assert entry.is_http is True


class TestCoerceMcpVisibility:
    """`coerce_mcp_visibility` must never raise and must default to internal."""

    def test_external_string_passes_through(self) -> None:
        assert coerce_mcp_visibility("external") == "external"

    def test_internal_string_passes_through(self) -> None:
        assert coerce_mcp_visibility("internal") == "internal"

    def test_missing_value_defaults_to_internal(self) -> None:
        assert coerce_mcp_visibility(None) == "internal"

    def test_unrecognized_value_defaults_to_internal(self) -> None:
        """Forward compatibility: an unknown future value must not raise."""
        assert coerce_mcp_visibility("partner-only") == "internal"

    def test_wrong_type_defaults_to_internal(self) -> None:
        assert coerce_mcp_visibility(123) == "internal"
