# openhands.sdk.context.utils.prompt

Utilities for rendering Jinja2 templates with platform-specific refinements.

## Functions

### refine(text: str) -> str

Refine text for platform-specific commands (bash -> powershell on Windows).

### render_template(prompt_dir: str, template_name: str, **ctx) -> str

Render a Jinja2 template with context and apply platform refinements.

