from pathlib import Path

from openhands.sdk.context import Skill


def test_load_markdown_without_frontmatter():
    """Test loading a markdown file without frontmatter."""
    content = "# Test Content\nThis is a test markdown file without frontmatter."
    path = Path("test.md")

    # Load the skill from content using keyword argument
    skill = Skill.load(path=path, file_content=content)

    # Verify it's loaded as a repo skill with default values
    assert skill.trigger is None
    assert skill.name == "test"  # Name comes from path.stem
    assert skill.content == content


def test_load_markdown_with_empty_frontmatter():
    """Test loading a markdown file with empty frontmatter."""
    content = (
        "---\n---\n# Test Content\nThis is a test markdown file with empty frontmatter."
    )
    path = Path("test.md")

    # Load the skill from content using keyword argument
    skill = Skill.load(path=path, file_content=content)

    # Verify it's loaded as a repo skill with default values
    assert skill.trigger is None
    assert skill.name == "test"  # Name comes from path.stem
    assert (
        skill.content
        == "# Test Content\nThis is a test markdown file with empty frontmatter."
    )


def test_load_markdown_with_partial_frontmatter():
    """Test loading a markdown file with partial frontmatter."""
    content = """---
name: custom_name
---
# Test Content
This is a test markdown file with partial frontmatter."""
    path = Path("test.md")

    # Load the skill from content using keyword argument
    skill = Skill.load(path=path, file_content=content)

    # Verify it uses provided name but default values for other fields
    assert skill.trigger is None
    assert skill.name == "custom_name"
    assert (
        skill.content
        == "# Test Content\nThis is a test markdown file with partial frontmatter."
    )


def test_load_markdown_with_full_frontmatter():
    """Test loading a markdown file with full frontmatter still works."""
    content = """---
name: test_agent
type: repo
agent: CustomAgent
version: 2.0.0
---
# Test Content
This is a test markdown file with full frontmatter."""
    path = Path("test.md")

    # Load the skill from content using keyword argument
    skill = Skill.load(path=path, file_content=content)

    # Verify all provided values are used
    assert skill.trigger is None
    assert skill.name == "test_agent"
    assert (
        skill.content
        == "# Test Content\nThis is a test markdown file with full frontmatter."
    )
