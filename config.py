from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    qwen_api_key: str
    qwen_base_url: str = "https://dashscope-intl.aliyuncs.com/compatible-mode/v1"
    orchestrator_model: str = "qwen3.7-plus"
    specialist_model: str = "qwen3.5-flash"
    moderator_model: str = "qwen3.7-plus"
    max_debate_rounds: int = 1
    conflict_line_window: int = 5

    model_config = {"env_file": ".env"}


settings = Settings()
