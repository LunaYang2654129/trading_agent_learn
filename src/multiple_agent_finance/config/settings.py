"""Project settings."""

from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    project_root: Path = Path(__file__).resolve().parents[3]
    data_dir: Path = project_root / "data"
    checkpoint_dir: Path = project_root / "checkpoints"
    report_dir: Path = project_root / "outputs" / "reports"
    default_confidence_threshold: float = 0.75
    mysql_host: str = "127.0.0.1"
    mysql_port: int = 3306
    mysql_user: str = "maf_app"
    mysql_password: str = "maf_password_change_me"
    mysql_database: str = "multiple_agent_finance"
    llm_provider: str = "volcengine_ark"
    llm_model: str = "deepseek-v4-flash"
    llm_endpoint_id: str | None = None
    llm_base_url: str = "https://ark.cn-beijing.volces.com/api/v3"
    llm_api_key: str | None = None
    llm_temperature: float = 0.2
    llm_timeout: int = 60

    @property
    def mysql_url(self) -> str:
        return (
            f"mysql+pymysql://{self.mysql_user}:{self.mysql_password}"
            f"@{self.mysql_host}:{self.mysql_port}/{self.mysql_database}"
            "?charset=utf8mb4"
        )

    @property
    def llm_runtime_model(self) -> str:
        return self.llm_endpoint_id or self.llm_model

    model_config = SettingsConfigDict(
        env_prefix="MAF_",
        env_file=".env",
        extra="ignore",
    )


settings = Settings()
