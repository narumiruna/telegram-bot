import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
from mcp.client.stdio import StdioServerParameters

from bot.config import AgentConfig


class TestAgentConfig:
    def test_agent_config_model_validation(self):
        """Test basic model validation"""
        mcp_servers = {"test_server": StdioServerParameters(command="test_command", args=["arg1", "arg2"])}
        config = AgentConfig(mcp_servers=mcp_servers)

        assert "test_server" in config.mcp_servers
        assert config.mcp_servers["test_server"].command == "test_command"
        assert config.mcp_servers["test_server"].args == ["arg1", "arg2"]

    def test_from_json_valid_config(self):
        """Test loading config from JSON file"""
        config_data = {
            "mcp_servers": {
                "firecrawl": {
                    "command": "npx",
                    "args": ["-y", "@firecrawl/mcp-server-firecrawl"],
                    "env": {"FIRECRAWL_API_KEY": "test_key"},
                }
            }
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            import json

            json.dump(config_data, f)
            temp_path = f.name

        try:
            config = AgentConfig.from_json(temp_path)

            assert "firecrawl" in config.mcp_servers
            server = config.mcp_servers["firecrawl"]
            assert server.command == "npx"
            assert server.args == ["-y", "@firecrawl/mcp-server-firecrawl"]
            assert (server.env or {})["FIRECRAWL_API_KEY"] == "test_key"
        finally:
            os.unlink(temp_path)

    def test_from_json_with_path_object(self):
        """Test loading config using Path object"""
        config_data = {"mcp_servers": {"test_server": {"command": "test_cmd", "args": []}}}

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            import json

            json.dump(config_data, f)
            temp_path = Path(f.name)

        try:
            config = AgentConfig.from_json(temp_path)
            assert "test_server" in config.mcp_servers
        finally:
            os.unlink(temp_path)

    @patch.dict(os.environ, {"TEST_API_KEY": "env_value"})
    def test_env_variable_substitution(self):
        """Test that empty env values are replaced with actual env vars"""
        config_data = {
            "mcp_servers": {
                "test_server": {
                    "command": "test_cmd",
                    "args": [],
                    "env": {
                        "TEST_API_KEY": ""  # Empty value should be replaced
                    },
                }
            }
        }

        config = AgentConfig.model_validate(config_data)

        # Should replace empty string with actual env var value
        assert (config.mcp_servers["test_server"].env or {}).get("TEST_API_KEY") == "env_value"

    @patch.dict(os.environ, {}, clear=True)
    def test_env_variable_substitution_missing_var(self):
        """Test behavior when env var doesn't exist"""
        config_data = {"mcp_servers": {"test_server": {"command": "test_cmd", "args": [], "env": {"MISSING_KEY": ""}}}}

        config = AgentConfig.model_validate(config_data)

        # Should use empty string when env var doesn't exist
        env = config.mcp_servers["test_server"].env or {}
        assert env.get("MISSING_KEY", "") == ""

    def test_env_variable_no_substitution_for_non_empty(self):
        """Test that non-empty env values are not replaced"""
        config_data = {
            "mcp_servers": {
                "test_server": {"command": "test_cmd", "args": [], "env": {"EXISTING_KEY": "existing_value"}}
            }
        }

        with patch.dict(os.environ, {"EXISTING_KEY": "env_value"}):
            config = AgentConfig.model_validate(config_data)

            # Should keep original value, not replace with env var
            assert (config.mcp_servers["test_server"].env or {}).get("EXISTING_KEY") == "existing_value"

    def test_multiple_servers_with_env_vars(self):
        """Test config with multiple servers and env variables"""
        with patch.dict(os.environ, {"API_KEY_1": "key1", "API_KEY_2": "key2"}):
            config_data = {
                "mcp_servers": {
                    "server1": {"command": "cmd1", "args": [], "env": {"API_KEY_1": ""}},
                    "server2": {"command": "cmd2", "args": [], "env": {"API_KEY_2": ""}},
                }
            }

            config = AgentConfig.model_validate(config_data)

            assert (config.mcp_servers["server1"].env or {}).get("API_KEY_1") == "key1"
            assert (config.mcp_servers["server2"].env or {}).get("API_KEY_2") == "key2"

    def test_server_without_env(self):
        """Test server configuration without env variables"""
        config_data = {"mcp_servers": {"simple_server": {"command": "simple_cmd", "args": ["--flag"]}}}

        config = AgentConfig.model_validate(config_data)

        assert config.mcp_servers["simple_server"].command == "simple_cmd"
        assert config.mcp_servers["simple_server"].args == ["--flag"]
        # env should be None or empty dict
        assert config.mcp_servers["simple_server"].env is None or config.mcp_servers["simple_server"].env == {}

    def test_invalid_json_file(self):
        """Test error handling for invalid JSON file"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("invalid json content")
            temp_path = f.name

        try:
            with pytest.raises((json.JSONDecodeError, ValueError)):
                AgentConfig.from_json(temp_path)
        finally:
            os.unlink(temp_path)

    def test_nonexistent_file(self):
        """Test error handling for nonexistent file"""
        with pytest.raises(FileNotFoundError):
            AgentConfig.from_json("nonexistent_file.json")
