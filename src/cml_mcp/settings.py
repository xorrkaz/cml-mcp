from pydantic import AnyHttpUrl, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Settings for the CML MCP server."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    cml_url: AnyHttpUrl = Field(..., description="URL of the Cisco Modeling Labs server")
    cml_username: str = Field(..., description="Username for CML server authentication")
    cml_password: str = Field(..., description="Password for CML server authentication")


settings = Settings()
