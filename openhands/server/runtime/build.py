from __future__ import annotations

import io
import shutil
import tarfile
import tempfile
from pathlib import Path

from jinja2 import Template

from .models import BuildSpec


DEFAULT_DOCKERFILE = """\
FROM {{ base_image }}
WORKDIR /app
COPY . /app
# Customize as needed, for example to unpack an artifact:
# RUN apt-get update && apt-get install -y unzip && \
#     unzip /app/{{ artifact_filename }} -d /app/server \
#     && rm -f /app/{{ artifact_filename }}
# CMD ["/usr/local/bin/server"]
"""


def render_dockerfile(spec: BuildSpec) -> str:
    if spec.dockerfile_template_str:
        tmpl_text = spec.dockerfile_template_str
    elif spec.dockerfile_template_path:
        tmpl_text = Path(spec.dockerfile_template_path).read_text()
    else:
        tmpl_text = DEFAULT_DOCKERFILE

    ctx = dict(spec.template_context)
    ctx.setdefault("base_image", spec.base_image)
    if spec.artifact_zip:
        ctx.setdefault("artifact_relpath", spec.artifact_relpath)
        ctx.setdefault("artifact_filename", Path(spec.artifact_relpath).name)

    return Template(tmpl_text).render(**ctx)


def assemble_context_dir(spec: BuildSpec) -> Path:
    """
    Build a temporary directory as docker build context:
      - Copy context_dir (if provided)
      - Copy each listed context file
      - Copy artifact_zip to artifact_relpath
      - Write add_bytes payloads
      - Render Dockerfile to 'Dockerfile'
    Returns the path to the temp directory. Caller is responsible for cleanup.
    """
    tmp = Path(tempfile.mkdtemp(prefix="ctx-"))

    def _cleanup_on_error():
        shutil.rmtree(tmp, ignore_errors=True)

    try:
        # Copy context_dir
        if spec.context_dir:
            src_dir = Path(spec.context_dir)
            if not src_dir.is_dir():
                raise FileNotFoundError(
                    f"context_dir not found or not a directory: {src_dir}"
                )
            for p in src_dir.rglob("*"):
                rel = p.relative_to(src_dir)
                dest = tmp / rel
                if p.is_dir():
                    dest.mkdir(parents=True, exist_ok=True)
                else:
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(p, dest)

        # Copy explicit files
        for src, rel_dest in spec.context_files:
            src_path = Path(src)
            if not src_path.exists():
                raise FileNotFoundError(f"context file not found: {src_path}")
            dest_path = tmp / rel_dest
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src_path, dest_path)

        # Copy artifact zip
        if spec.artifact_zip:
            src_zip = Path(spec.artifact_zip)
            if not src_zip.is_file():
                raise FileNotFoundError(f"artifact_zip not found: {src_zip}")
            dest_zip = tmp / spec.artifact_relpath
            dest_zip.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src_zip, dest_zip)

        # Write add_bytes
        for filename, data in spec.add_bytes:
            dest = tmp / filename
            dest.parent.mkdir(parents=True, exist_ok=True)
            with open(dest, "wb") as f:
                f.write(data)

        # Write Dockerfile
        dockerfile_text = render_dockerfile(spec)
        (tmp / "Dockerfile").write_text(dockerfile_text)

        return tmp
    except Exception:
        _cleanup_on_error()
        raise


def tar_gz_dir(dir_path: Path) -> bytes:
    buf = io.BytesIO()
    with tarfile.open(mode="w:gz", fileobj=buf) as tf:
        for p in dir_path.rglob("*"):
            tf.add(p, arcname=str(p.relative_to(dir_path)))
    return buf.getvalue()
