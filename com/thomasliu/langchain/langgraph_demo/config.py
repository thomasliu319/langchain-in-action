from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class DeepSeekConfig:
    """DeepSeek(OpenAI-compatible) config."""
    api_key: str
    base_url: str = "https://api.deepseek.com"
    model: str = "deepseek-v4-pro"

    @staticmethod
    def from_env() -> "DeepSeekConfig":
        api_key = os.getenv("DEEPSEEK_API_KEY", "").strip()
        base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com").strip()
        model = os.getenv("DEEPSEEK_MODEL", "deepseek-v4-pro").strip()
        if not api_key:
            raise RuntimeError(
                "Missing DEEPSEEK_API_KEY. Create a .env file (see .env.example) "
                "or export it in your shell."
            )
        return DeepSeekConfig(api_key=api_key, base_url=base_url, model=model)


@dataclass(frozen=True)
class CoursewareBuildConfig:
    """Courseware PDF build inputs."""
    # Prefer local HTML for reproducibility.
    html_path: str | None = None
    html_url: str | None = None

    # Output PDF path (relative to project root by default)
    output_pdf: str = "output/第六讲-Agent工作流编排与LangGraph实战.pdf"
