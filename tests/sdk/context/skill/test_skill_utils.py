"""Tests for the skill system."""

import tempfile
from pathlib import Path

import pytest
from pydantic import ValidationError

from openhands.sdk.context import (
    KeywordTrigger,
    Skill,
    SkillValidationError,
    load_skills_from_dir,
)


CONTENT = "# dummy header\ndummy content\n## dummy subheader\ndummy subcontent\n"


def test_legacy_micro_agent_load(tmp_path):
    """Test loading of legacy skills."""
    legacy_file = tmp_path / ".openhands_instructions"
    legacy_file.write_text(CONTENT)

    # Pass skill_dir (tmp_path in this case) to load
    skill = Skill.load(legacy_file, tmp_path)
    assert skill.trigger is None
    assert skill.name == ".openhands_instructions"  # Name derived from filename
    # frontmatter.load() strips trailing newline
    assert skill.content == CONTENT.rstrip("\n")


@pytest.fixture
def temp_skills_dir():
    """Create a temporary directory with test skills."""
    with tempfile.TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)

        # Create test knowledge agent (type inferred from triggers)
        knowledge_agent = """---
# type: knowledge
version: 1.0.0
agent: CodeActAgent
triggers:
  - test
  - pytest
---

# Test Guidelines

Testing best practices and guidelines.
"""
        (root / "knowledge.md").write_text(knowledge_agent)

        # Create test repo agent (type inferred from lack of triggers)
        repo_agent = """---
# type: repo
version: 1.0.0
agent: CodeActAgent
---

# Test Repository Agent

Repository-specific test instructions.
"""
        (root / "repo.md").write_text(repo_agent)

        yield root


def test_knowledge_agent():
    """Test knowledge agent functionality."""
    # Create a knowledge agent with keyword triggers
    agent = Skill(
        name="test",
        content="Test content",
        source="test.md",
        trigger=KeywordTrigger(keywords=["testing", "pytest"]),
    )

    assert agent.match_trigger("running a testing") == "testing"
    assert agent.match_trigger("using pytest") == "pytest"
    assert agent.match_trigger("no match here") is None
    assert agent.trigger.keywords == ["testing", "pytest"]


def test_load_skills(temp_skills_dir):
    """Test loading skills from directory."""
    repo_agents, knowledge_agents = load_skills_from_dir(temp_skills_dir)

    # Check knowledge agents (name derived from filename: knowledge.md -> 'knowledge')
    assert len(knowledge_agents) == 1
    agent_k = knowledge_agents["knowledge"]
    assert isinstance(agent_k, Skill)
    assert isinstance(agent_k.trigger, KeywordTrigger)  # Check inferred type
    assert "test" in agent_k.trigger.keywords

    # Check repo agents (name derived from filename: repo.md -> 'repo')
    assert len(repo_agents) == 1
    agent_r = repo_agents["repo"]
    assert agent_r.trigger is None
    assert agent_r.trigger is None  # Check inferred type


def test_load_skills_with_nested_dirs(temp_skills_dir):
    """Test loading skills from nested directories."""
    # Create nested knowledge agent
    nested_dir = temp_skills_dir / "nested" / "dir"
    nested_dir.mkdir(parents=True)
    nested_agent = """---
# type: knowledge
version: 1.0.0
agent: CodeActAgent
triggers:
  - nested
---

# Nested Test Guidelines

Testing nested directory loading.
"""
    (nested_dir / "nested.md").write_text(nested_agent)

    repo_agents, knowledge_agents = load_skills_from_dir(temp_skills_dir)

    # Check that we can find the nested agent (name derived from
    # path: nested/dir/nested.md -> 'nested/dir/nested')
    assert (
        len(knowledge_agents) == 2
    )  # Original ('knowledge') + nested ('nested/dir/nested')
    agent_n = knowledge_agents["nested/dir/nested"]
    assert isinstance(agent_n, Skill)
    assert isinstance(agent_n.trigger, KeywordTrigger)  # Check inferred type
    assert "nested" in agent_n.trigger.keywords


def test_load_skills_with_trailing_slashes(temp_skills_dir):
    """Test loading skills when directory paths have trailing slashes."""
    # Create a directory with trailing slash
    knowledge_dir = temp_skills_dir / "test_knowledge/"
    knowledge_dir.mkdir(exist_ok=True)
    knowledge_agent = """---
# type: knowledge
version: 1.0.0
agent: CodeActAgent
triggers:
  - trailing
---

# Trailing Slash Test

Testing loading with trailing slashes.
"""
    (knowledge_dir / "trailing.md").write_text(knowledge_agent)

    repo_agents, knowledge_agents = load_skills_from_dir(
        str(temp_skills_dir) + "/"  # Add trailing slash to test
    )

    # Check that we can find the agent despite trailing slashes
    # (name derived from path: test_knowledge/trailing.md -> 'test_knowledge/trailing')
    assert (
        len(knowledge_agents) == 2
    )  # Original ('knowledge') + trailing ('test_knowledge/trailing')
    agent_t = knowledge_agents["test_knowledge/trailing"]
    assert isinstance(agent_t, Skill)
    assert isinstance(agent_t.trigger, KeywordTrigger)  # Check inferred type
    assert "trailing" in agent_t.trigger.keywords


def test_invalid_skill_type(temp_skills_dir):
    """Test loading a skill with invalid triggers field (not a list)."""
    # Create a skill with invalid triggers (should be a list, not a string)
    invalid_agent = """---
name: invalid_triggers_agent
version: 1.0.0
agent: CodeActAgent
triggers: not_a_list
---

# Invalid Triggers Test

This skill has invalid triggers format.
"""
    invalid_file = temp_skills_dir / "invalid_triggers.md"
    invalid_file.write_text(invalid_agent)

    with pytest.raises(SkillValidationError) as excinfo:
        load_skills_from_dir(temp_skills_dir)

    # Check that the error message contains helpful information
    error_msg = str(excinfo.value)
    assert "invalid_triggers.md" in error_msg
    assert "Triggers must be a list" in error_msg


def test_cursorrules_file_load():
    """Test loading .cursorrules file as a RepoSkill."""
    cursorrules_content = """Always use Python for new files.
Follow the existing code style.
Add proper error handling."""

    cursorrules_path = Path(".cursorrules")

    # Test loading .cursorrules file directly
    agent = Skill.load(cursorrules_path, file_content=cursorrules_content)

    # Verify it's loaded as a RepoSkill
    assert agent.trigger is None
    assert agent.name == "cursorrules"
    assert agent.content == cursorrules_content
    assert agent.trigger is None
    assert agent.source == str(cursorrules_path)


def test_skill_version_as_integer():
    """Test loading a skill with version as integer (reproduces the bug)."""
    # Create a skill with version as an unquoted integer
    # This should be parsed as an integer by YAML but converted to string by our code
    skill_content = """---
name: test_agent
type: knowledge
version: 2512312
agent: CodeActAgent
triggers:
  - test
---

# Test Agent

This is a test agent with integer version.
"""

    test_path = Path("test_agent.md")

    # This should not raise an error even though version is an integer in YAML
    agent = Skill.load(test_path, file_content=skill_content)

    # Verify the agent was loaded correctly
    assert isinstance(agent, Skill)
    assert agent.name == "test_agent"
    # .metadata was deprecated in V1. this test simply tests
    # that we are backward compatible
    # assert agent.metadata.version == '2512312'  # Should be converted to string
    assert isinstance(agent.trigger, KeywordTrigger)


def test_skill_version_as_float():
    """Test loading a skill with version as float."""
    # Create a skill with version as an unquoted float
    skill_content = """---
name: test_agent_float
type: knowledge
version: 1.5
agent: CodeActAgent
triggers:
  - test
---

# Test Agent Float

This is a test agent with float version.
"""

    test_path = Path("test_agent_float.md")

    # This should not raise an error even though version is a float in YAML
    agent = Skill.load(test_path, file_content=skill_content)

    # Verify the agent was loaded correctly
    assert isinstance(agent, Skill)
    assert agent.name == "test_agent_float"
    assert isinstance(agent.trigger, KeywordTrigger)


def test_skill_version_as_string_unchanged():
    """Test loading a skill with version as string (should remain unchanged)."""
    # Create a skill with version as a quoted string
    skill_content = """---
name: test_agent_string
type: knowledge
version: "1.0.0"
agent: CodeActAgent
triggers:
  - test
---

# Test Agent String

This is a test agent with string version.
"""

    test_path = Path("test_agent_string.md")

    # This should work normally
    agent = Skill.load(test_path, file_content=skill_content)

    # Verify the agent was loaded correctly
    assert isinstance(agent, Skill)
    assert agent.name == "test_agent_string"
    assert isinstance(agent.trigger, KeywordTrigger)


@pytest.fixture
def temp_skills_dir_with_cursorrules():
    """Create a temporary directory with test skills and .cursorrules file."""
    with tempfile.TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)

        # Create .openhands/skills directory structure
        skills_dir = root / ".openhands" / "skills"
        skills_dir.mkdir(parents=True, exist_ok=True)

        # Create .cursorrules file in repository root
        cursorrules_content = """Always use TypeScript for new files.
Follow the existing code style."""
        (root / ".cursorrules").write_text(cursorrules_content)

        # Create test repo agent
        repo_agent = """---
# type: repo
version: 1.0.0
agent: CodeActAgent
---

# Test Repository Agent

Repository-specific test instructions.
"""
        (skills_dir / "repo.md").write_text(repo_agent)

        yield root


def test_load_skills_with_cursorrules(temp_skills_dir_with_cursorrules):
    """Test loading skills when .cursorrules file exists."""
    skills_dir = temp_skills_dir_with_cursorrules / ".openhands" / "skills"

    repo_agents, knowledge_agents = load_skills_from_dir(skills_dir)

    # Verify that .cursorrules file was loaded as a RepoSkill
    assert len(repo_agents) == 2  # repo.md + .cursorrules
    assert "repo" in repo_agents
    assert "cursorrules" in repo_agents

    # Check .cursorrules agent
    cursorrules_agent = repo_agents["cursorrules"]
    assert cursorrules_agent.trigger is None
    assert cursorrules_agent.name == "cursorrules"
    assert "Always use TypeScript for new files" in cursorrules_agent.content
    assert cursorrules_agent.trigger is None


def test_repo_skill_with_mcp_tools():
    """Test loading a repo skill with mcp_tools configuration."""
    # Create a repo skill with mcp_tools in frontmatter
    skill_content = """---
name: default-tools
type: repo
version: 1.0.0
agent: CodeActAgent
mcp_tools:
  mcpServers:
    fetch:
      command: uvx
      args: ["mcp-server-fetch"]
---

# Default Tools

This is a repo skill that includes MCP tools.
"""

    test_path = Path("default-tools.md")

    # Load the skill
    agent = Skill.load(test_path, file_content=skill_content)

    # Verify it's loaded as a RepoSkill
    assert agent.trigger is None
    assert agent.name == "default-tools"
    assert agent.trigger is None
    assert agent.mcp_tools is not None

    # Verify the mcp_tools configuration is correctly loaded
    from fastmcp.mcp_config import MCPConfig

    assert isinstance(agent.mcp_tools, dict)
    config = MCPConfig.model_validate(agent.mcp_tools)
    assert "fetch" in config.mcpServers
    fetch_server = config.mcpServers["fetch"]
    assert hasattr(fetch_server, "command")
    assert hasattr(fetch_server, "args")
    assert getattr(fetch_server, "command") == "uvx"
    assert getattr(fetch_server, "args") == ["mcp-server-fetch"]


def test_repo_skill_with_mcp_tools_dict_format():
    """Test loading a repo skill with mcp_tools as dict (JSON-like format)."""
    # Create a repo skill with mcp_tools in JSON-like dict format
    skill_content = """---
name: default-tools-dict
type: repo
version: 1.0.0
agent: CodeActAgent
mcp_tools: {
  "mcpServers": {
    "fetch": {
      "command": "uvx",
      "args": ["mcp-server-fetch"]
    }
  }
}
---

# Default Tools Dict

This is a repo skill that includes MCP tools in dict format.
"""

    test_path = Path("default-tools-dict.md")

    # Load the skill
    agent = Skill.load(test_path, file_content=skill_content)

    # Verify it's loaded as a RepoSkill
    assert agent.trigger is None
    assert agent.name == "default-tools-dict"
    assert agent.trigger is None
    assert agent.mcp_tools is not None

    # Verify the mcp_tools configuration is correctly loaded
    from fastmcp.mcp_config import MCPConfig

    assert isinstance(agent.mcp_tools, dict)
    config = MCPConfig.model_validate(agent.mcp_tools)
    assert "fetch" in config.mcpServers
    fetch_server = config.mcpServers["fetch"]
    assert hasattr(fetch_server, "command")
    assert hasattr(fetch_server, "args")
    assert getattr(fetch_server, "command") == "uvx"
    assert getattr(fetch_server, "args") == ["mcp-server-fetch"]


def test_repo_skill_without_mcp_tools():
    """Test loading a repo skill without mcp_tools (should be None)."""
    # Create a repo skill without mcp_tools
    skill_content = """---
name: no-mcp-tools
type: repo
version: 1.0.0
agent: CodeActAgent
---

# No MCP Tools

This is a repo skill without MCP tools.
"""

    test_path = Path("no-mcp-tools.md")

    # Load the skill
    agent = Skill.load(test_path, file_content=skill_content)

    # Verify it's loaded as a RepoSkill
    assert agent.trigger is None
    assert agent.name == "no-mcp-tools"
    assert agent.trigger is None
    assert agent.mcp_tools is None


def test_repo_skill_with_invalid_mcp_tools():
    """Test loading a repo skill with invalid mcp_tools configuration."""
    # Create a repo skill with truly invalid mcp_tools (wrong type)
    skill_content = """---
name: invalid-mcp-tools
type: repo
version: 1.0.0
agent: CodeActAgent
mcp_tools: "this should be a dict or MCPConfig, not a string"
---

# Invalid MCP Tools

This is a repo skill with invalid MCP tools configuration.
"""

    test_path = Path("invalid-mcp-tools.md")

    # Loading should raise an error (either SkillValidationError or AttributeError)
    with pytest.raises(ValidationError) as excinfo:
        Skill.load(test_path, file_content=skill_content)

    # Check that the error message contains helpful information
    error_msg = str(excinfo.value)
    assert "Input should be a valid dictionary" in error_msg
