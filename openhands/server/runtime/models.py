from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class BuildSpec(BaseModel):
    base_image: str
    tag: str | None = None

    # Dockerfile templating (Jinja2)
    dockerfile_template_str: str | None = None  # Template content
    dockerfile_template_path: str | Path | None = None
    template_context: dict[str, Any] = Field(default_factory=dict)

    # Build context sources
    context_dir: str | Path | None = None  # Copy entire directory tree into context
    context_files: list[tuple[str | Path, str]] = Field(default_factory=list)
    # Each tuple is (src_path_on_host, dest_relative_path_in_context)

    # Optional artifact bundle (e.g., zip) to include in context
    artifact_zip: str | Path | None = None
    artifact_relpath: str = "artifact.zip"

    # Extra generated files (filename_in_context, binary_data)
    add_bytes: list[tuple[str, bytes]] = Field(default_factory=list)

    # Build args / platform
    build_args: dict[str, str] = Field(default_factory=dict)
    platform: str | None = (
        None  # e.g., "linux/amd64" (requires proper buildx/daemon support)
    )

    @classmethod
    def simple_server_copy(
        cls,
        base_image: str,
        server_executable: str | Path,
        tag: str | None = None,
        dockerfile_template: str | None = None,
    ) -> "BuildSpec":
        """
        Convenience factory: copies a server binary as 'server' into context and
        uses a simple default Dockerfile (or your template).
        """
        server_executable = str(Path(server_executable).resolve())
        if dockerfile_template is None:
            dockerfile_template = (
                "FROM {{ base_image }}\n"
                "WORKDIR /app\n"
                "COPY . /app\n"
                "RUN chmod +x /app/server || true\n"
                'CMD ["/app/server"]\n'
            )
        return cls(
            base_image=base_image,
            tag=tag,
            dockerfile_template_str=dockerfile_template,
            context_files=[(server_executable, "server")],
        )
