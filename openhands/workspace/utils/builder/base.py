"""Base class for runtime image builders.

Adapted from OpenHands V0 openhands/runtime/builder/base.py
"""

import abc


class RuntimeBuilder(abc.ABC):
    """Abstract base class for building and managing runtime images."""

    @abc.abstractmethod
    def build(
        self,
        path: str,
        tags: list[str],
        platform: str | None = None,
        extra_build_args: list[str] | None = None,
        use_local_cache: bool = False,
        push: bool = False,
        registry_cache_from: list[str] | None = None,
        registry_cache_to: str | None = None,
        builder_name: str | None = None,
    ) -> str:
        """Build the runtime image.

        Args:
            path (str): The path to the runtime image's build directory.
            tags (list[str]): The tags to apply to the runtime image (e.g., ["repo:my-repo", "sha:my-sha"]).
            platform (str, optional): The target platform for the build. Defaults to None.
            extra_build_args (list[str], optional): Additional build arguments to pass to the builder. Defaults to None.
            use_local_cache (bool, optional): Whether to use and update the local build cache. Defaults to False.
            push (bool, optional): Whether to push the image to registry (CI mode). Defaults to False.
            registry_cache_from (list[str], optional): List of registry cache refs to pull from. Defaults to None.
            registry_cache_to (str, optional): Registry cache ref to push to. Defaults to None.
            builder_name (str, optional): Name of builder to create/use for multi-arch builds. Defaults to None.

        Returns:
            str: The name:tag of the runtime image after build (e.g., "repo:sha").
                This can be different from the tags input if the builder chooses to mutate the tags (e.g., adding a
                registry prefix). This should be used for subsequent use (e.g., `docker run`).

        Raises:
            AgentRuntimeBuildError: If the build failed.
        """
        pass

    @abc.abstractmethod
    def image_exists(self, image_name: str, pull_from_repo: bool = True) -> bool:
        """Check if the runtime image exists.

        Args:
            image_name (str): The name of the runtime image (e.g., "repo:sha").
            pull_from_repo (bool): Whether to pull from the remote repo if the image not present locally

        Returns:
            bool: Whether the runtime image exists.
        """
        pass
