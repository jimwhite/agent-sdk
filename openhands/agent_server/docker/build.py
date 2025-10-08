#!/usr/bin/env python3
"""Build script for agent-server Docker images.

This script uses the AgentServerBuildConfig and DockerRuntimeBuilder infrastructure
to build agent-server images. All Docker buildx logic is encapsulated in the
workspace builder module.

Environment variables (with defaults):
    IMAGE: Image repository name (default: ghcr.io/all-hands-ai/agent-server)
    BASE_IMAGE: Base Docker image (default: nikolaik/python-nodejs:python3.12-nodejs22)
    CUSTOM_TAGS: Comma-separated additional tags (default: empty, e.g., "python,latest")
    TARGET: Build target (default: binary, options: binary or source)
    PLATFORMS: Target platforms (default: linux/amd64,linux/arm64)
    CI: Set to 'true' in CI environments to enable push
    GITHUB_OUTPUT: Path to GitHub Actions output file (CI only)
"""

from typing import Literal
import argparse
import os
import sys


def build_image(
    image: str,
    base_image: str,
    custom_tags: list[str] | None,
    target: Literal["source", "binary"],
    platforms: str,
    push: bool = False,
) -> dict[str, str]:
    """Build agent-server Docker image using AgentServerBuildConfig.
    
    Args:
        image: Image repository name
        base_image: Base Docker image
        custom_tags: Optional list of additional custom tags
        target: Build target (source or binary)
        platforms: Comma-separated list of platforms
        push: Whether to push to registry (CI mode)
    
    Returns:
        Dict with build information (tags, sha, etc.)
    """
    from openhands.workspace.docker.builder import DockerRuntimeBuilder
    from openhands.workspace.utils.builder import AgentServerBuildConfig
    
    # Create build config with hash-based tags
    config = AgentServerBuildConfig(
        base_image=base_image,
        target=target,
        registry_prefix=image,
        custom_tags=custom_tags,
    )
    
    # Access version and git info from config properties
    git_info = config.git_info
    sdk_version = config.version
    short_sha = git_info["short_sha"]
    git_ref = git_info["ref"]
    
    custom_tags_str = ", ".join(custom_tags) if custom_tags else "none"
    print(f"[build] Building target='{target}' image='{image}'")
    print(f"[build]   base='{base_image}' platforms='{platforms}'")
    print(f"[build]   custom_tags=[{custom_tags_str}]")
    print(f"[build] Git ref='{git_ref}' sha='{git_info['sha']}' version='{sdk_version}'")
    
    # Get the tags that will be applied
    tags = config.tags
    print("[build] Tags:")
    for tag in tags:
        print(f"  - {tag}")
    
    # Determine build mode
    is_ci = os.getenv("CI") == "true" or os.getenv("GITHUB_ACTIONS") == "true"
    
    if is_ci and push:
        print("[build] Running in CI mode - using buildx with multi-arch push")
        # Use all platforms for multi-arch build
        platform = platforms
        builder_name = "agentserver-builder"
        enable_cache = True
    else:
        print("[build] Running in local mode - using builder with single-arch load")
        # For local builds, use single platform (first one from the list)
        platform = platforms.split(",")[0] if "," in platforms else platforms
        builder_name = None
        # Try to use registry cache even for local builds
        enable_cache = True
    
    # Build the image
    builder = DockerRuntimeBuilder()
    primary_tag = config.build(
        builder=builder,
        platform=platform,
        push=push,
        enable_registry_cache=enable_cache,
        builder_name=builder_name,
    )
    
    print("[build] Done. Tags:")
    for tag in tags:
        print(f"  - {tag}")
    
    # Extract just the tags (without registry prefix) for output
    tags_without_prefix = [tag.split(":", 1)[1] if ":" in tag else tag for tag in tags]
    
    # Return build info
    return {
        "image": image,
        "short_sha": short_sha,
        "versioned_tag": tags_without_prefix[2] if len(tags_without_prefix) > 2 else tags_without_prefix[0],
        "tags": tags,
        "tags_csv": ",".join(tags),
        "custom_tags": custom_tags or [],
        "base_image": base_image,
    }


def write_github_output(build_info: dict) -> None:
    """Write build information to GitHub Actions output."""
    github_output = os.getenv("GITHUB_OUTPUT")
    if not github_output:
        return
    
    with open(github_output, "a") as f:
        f.write(f"image={build_info['image']}\n")
        f.write(f"short_sha={build_info['short_sha']}\n")
        f.write(f"versioned_tag={build_info['versioned_tag']}\n")
        f.write(f"tags_csv={build_info['tags_csv']}\n")
        f.write("tags<<EOF\n")
        for tag in build_info['tags']:
            f.write(f"{tag}\n")
        f.write("EOF\n")


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Build agent-server Docker images with hash-based caching"
    )
    parser.add_argument(
        "--image",
        default=os.getenv("IMAGE", "ghcr.io/all-hands-ai/agent-server"),
        help="Image repository name",
    )
    parser.add_argument(
        "--base-image",
        default=os.getenv("BASE_IMAGE", "nikolaik/python-nodejs:python3.12-nodejs22"),
        help="Base Docker image",
    )
    parser.add_argument(
        "--custom-tags",
        default=os.getenv("CUSTOM_TAGS", ""),
        help="Comma-separated custom tags (e.g., 'python,latest')",
    )
    parser.add_argument(
        "--target",
        default=os.getenv("TARGET", "binary"),
        choices=["source", "binary"],
        help="Build target (source=dev, binary=prod)",
    )
    parser.add_argument(
        "--platforms",
        default=os.getenv("PLATFORMS", "linux/amd64,linux/arm64"),
        help="Target platforms (comma-separated)",
    )
    parser.add_argument(
        "--push",
        action="store_true",
        default=os.getenv("CI") == "true" or os.getenv("GITHUB_ACTIONS") == "true",
        help="Push to registry (auto-enabled in CI)",
    )
    
    args = parser.parse_args()
    
    # Parse custom tags
    custom_tags = [tag.strip() for tag in args.custom_tags.split(",") if tag.strip()]
    
    try:
        build_info = build_image(
            image=args.image,
            base_image=args.base_image,
            custom_tags=custom_tags if custom_tags else None,
            target=args.target,
            platforms=args.platforms,
            push=args.push,
        )
        
        # Write GitHub Actions output if in CI
        write_github_output(build_info)
        
        return 0
    except Exception as e:
        print(f"[build] ERROR: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
