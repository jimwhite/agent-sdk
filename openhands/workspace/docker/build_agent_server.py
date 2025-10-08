#!/usr/bin/env python3
"""Build script for agent-server Docker images.

This script replaces the build.sh bash script with a Python implementation
that uses the AgentServerBuildConfig and DockerRuntimeBuilder infrastructure.

Environment variables (with defaults):
    IMAGE: Image repository name (default: ghcr.io/all-hands-ai/agent-server)
    BASE_IMAGE: Base Docker image (default: nikolaik/python-nodejs:python3.12-nodejs22)
    VARIANT_NAME: Build variant (default: python)
    TARGET: Build target (default: binary, options: binary or source)
    PLATFORMS: Target platforms (default: linux/amd64,linux/arm64)
    CI: Set to 'true' in CI environments to enable push
    GITHUB_SHA: Git commit SHA (auto-detected if not set)
    GITHUB_REF: Git branch/ref (auto-detected if not set)
    GITHUB_OUTPUT: Path to GitHub Actions output file (CI only)
    GITHUB_ACTIONS: Set to 'true' by GitHub Actions
"""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

import docker


def get_git_info() -> dict[str, str]:
    """Get git information (SHA, branch)."""
    try:
        sha = subprocess.check_output(
            ["git", "rev-parse", "--verify", "HEAD"],
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip()
    except Exception:
        sha = os.getenv("GITHUB_SHA", "unknown")

    short_sha = sha[:7] if len(sha) >= 7 else sha

    try:
        ref = subprocess.check_output(
            ["git", "symbolic-ref", "-q", "--short", "HEAD"],
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip()
    except Exception:
        ref = os.getenv("GITHUB_REF", "unknown")

    return {"sha": sha, "short_sha": short_sha, "ref": ref}


def sanitize_branch(branch: str) -> str:
    """Sanitize branch name for use in cache tags."""
    # Remove refs/heads/ prefix
    sanitized = branch.replace("refs/heads/", "")
    # Replace non-alphanumeric characters with hyphens
    sanitized = "".join(c if c.isalnum() or c in ".-" else "-" for c in sanitized)
    # Convert to lowercase
    return sanitized.lower()


def get_cache_tags(variant: str, git_ref: str) -> tuple[str, list[str]]:
    """Generate cache tags for buildx caching strategy.
    
    Returns:
        Tuple of (primary_cache_tag, fallback_cache_tags)
    """
    cache_tag_base = f"buildcache-{variant}"
    
    # Determine primary cache tag based on branch
    if git_ref in ("main", "refs/heads/main"):
        cache_tag = f"{cache_tag_base}-main"
    elif git_ref != "unknown":
        sanitized_ref = sanitize_branch(git_ref)
        cache_tag = f"{cache_tag_base}-{sanitized_ref}"
    else:
        cache_tag = cache_tag_base
    
    # Fallback cache tags (try branch-specific first, then main)
    fallback_caches = [f"{cache_tag_base}-main"] if cache_tag != f"{cache_tag_base}-main" else []
    
    return cache_tag, fallback_caches


def build_image(
    image: str,
    base_image: str,
    variant: str,
    target: str,
    platforms: str,
    push: bool = False,
) -> dict[str, str]:
    """Build agent-server Docker image using AgentServerBuildConfig.
    
    Args:
        image: Image repository name
        base_image: Base Docker image
        variant: Build variant name
        target: Build target (source or binary)
        platforms: Comma-separated list of platforms
        push: Whether to push to registry (CI mode)
    
    Returns:
        Dict with build information (tags, sha, etc.)
    """
    from openhands.workspace.utils.builder import (
        AgentServerBuildConfig,
        get_sdk_version,
    )
    
    git_info = get_git_info()
    sdk_version = get_sdk_version()
    short_sha = git_info["short_sha"]
    git_ref = git_info["ref"]
    
    print(f"[build] Building target='{target}' image='{image}' variant='{variant}'")
    print(f"[build]   base='{base_image}' platforms='{platforms}'")
    print(f"[build] Git ref='{git_ref}' sha='{git_info['sha']}' version='{sdk_version}'")
    
    # Generate cache tags
    cache_tag, fallback_caches = get_cache_tags(variant, git_ref)
    print(f"[build] Cache tag: {cache_tag}")
    if fallback_caches:
        print(f"[build] Fallback caches: {', '.join(fallback_caches)}")
    
    # Create build config with hash-based tags
    config = AgentServerBuildConfig(
        base_image=base_image,
        variant=variant,
        target=target,
        registry_prefix=image,
    )
    
    # Get the tags that will be applied
    tags = config.tags
    print("[build] Tags:")
    for tag in tags:
        print(f"  - {tag}")
    
    # Get dockerfile and build context
    dockerfile = config.dockerfile
    build_context = config.build_context
    
    # In CI mode, use buildx directly with multi-arch and push
    # In local mode, use the builder which loads to local docker
    is_ci = os.getenv("CI") == "true" or os.getenv("GITHUB_ACTIONS") == "true"
    
    if is_ci and push:
        print("[build] Running in CI mode - using buildx with multi-arch push")
        
        # Create buildx builder if needed
        subprocess.run(
            ["docker", "buildx", "create", "--use", "--name", "agentserver-builder"],
            capture_output=True,
            check=False,
        )
        
        # Build command
        cmd = [
            "docker", "buildx", "build",
            "--platform", platforms,
            f"--build-arg=BASE_IMAGE={base_image}",
            f"--target={target}",
            f"--file={dockerfile}",
        ]
        
        # Add all tags
        for tag in tags:
            cmd.extend(["--tag", tag])
        
        # Add cache configuration
        cmd.extend([
            f"--cache-from=type=registry,ref={image}:{cache_tag}",
        ])
        for fallback in fallback_caches:
            cmd.extend([f"--cache-from=type=registry,ref={image}:{fallback}"])
        cmd.extend([
            f"--cache-to=type=registry,ref={image}:{cache_tag},mode=max",
            "--push",
            str(build_context),
        ])
        
        print(f"[build] Running: {' '.join(cmd)}")
        subprocess.run(cmd, check=True)
        
        primary_tag = tags[0]
    else:
        print("[build] Running in local mode - using builder with single-arch load")
        
        # For local builds, use single platform (first one from the list)
        platform = platforms.split(",")[0] if "," in platforms else platforms
        
        # Use DockerRuntimeBuilder
        from openhands.workspace.utils.builder import DockerRuntimeBuilder
        
        docker_client = docker.from_env()
        builder = DockerRuntimeBuilder(docker_client)
        
        # Check if image already exists
        for tag in tags:
            if builder.image_exists(tag, pull_from_repo=False):
                print(f"[build] Image {tag} already exists locally, skipping build")
                primary_tag = tag
                break
        else:
            # Build the image
            extra_build_args = [
                f"--build-arg=BASE_IMAGE={base_image}",
                f"--target={target}",
                f"--file={dockerfile}",
            ]
            
            # Add cache configuration (using local cache for non-CI builds)
            cmd_with_cache = [
                "docker", "buildx", "build",
                "--platform", platform,
                f"--build-arg=BASE_IMAGE={base_image}",
                f"--target={target}",
                f"--file={dockerfile}",
            ]
            
            # Add tags
            for tag in tags:
                cmd_with_cache.extend(["--tag", tag])
            
            # Add registry cache (try to pull from registry)
            cmd_with_cache.extend([
                f"--cache-from=type=registry,ref={image}:{cache_tag}",
            ])
            for fallback in fallback_caches:
                cmd_with_cache.extend([f"--cache-from=type=registry,ref={image}:{fallback}"])
            
            cmd_with_cache.extend([
                "--load",
                str(build_context),
            ])
            
            print(f"[build] Running: {' '.join(cmd_with_cache)}")
            subprocess.run(cmd_with_cache, check=True)
            
            primary_tag = tags[0]
    
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
        "variant": variant,
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
        "--variant",
        default=os.getenv("VARIANT_NAME", "python"),
        help="Build variant name",
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
    
    try:
        build_info = build_image(
            image=args.image,
            base_image=args.base_image,
            variant=args.variant,
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
