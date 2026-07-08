from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_AGENT_CORE_ROOT = Path(__file__).resolve().parents[2]
_DESIGN_DATA = _AGENT_CORE_ROOT.parent / "design-data"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    ollama_base_url: str = "http://localhost:11434"
    ollama_text_model: str = "qwen2.5:14b"
    ollama_vlm_model: str = "qwen2.5vl"
    ollama_embedding_model: str = "bge-m3"

    # 智谱 AI (GLM) API 配置
    llm_provider: str = "zhipu"  # "zhipu" | "ollama"
    zhipu_api_key: str = ""
    zhipu_base_url: str = "https://open.bigmodel.cn/api/paas/v4"
    zhipu_model: str = "glm-4-flash"
    zhipu_vlm_model: str = "glm-4v-flash"
    zhipu_embedding_model: str = "embedding-3"
    zhipu_image_model: str = "cogview-3-plus"

    # SiliconFlow API 配置
    siliconflow_api_key: str = ""
    siliconflow_base_url: str = "https://api.siliconflow.com/v1"
    siliconflow_image_model: str = "black-forest-labs/FLUX.1-schnell"

    # 模型服务选择：zhipu | ollama
    vlm_provider: str = "zhipu"  # "zhipu" | "ollama"
    embedding_provider: str = "zhipu"  # "zhipu" | "ollama"

    milvus_host: str = "localhost"
    milvus_port: int = 19530
    milvus_collection_cases: str = "case_descriptions"
    milvus_collection_images: str = "image_descriptions"

    mysql_host: str = "localhost"
    mysql_port: int = 3306
    mysql_db: str = "meichen"
    mysql_username: str = "meichen"
    mysql_password: str = "meichen123"

    pollinations_base_url: str = "https://image.pollinations.ai"
    pollinations_timeout: int = 60
    comfyui_base_url: str = "http://localhost:8188"

    upload_dir: str = str(_DESIGN_DATA / "uploads")
    image_cache_dir: str = str(_DESIGN_DATA / "images")
    html_cache_dir: str = str(_DESIGN_DATA / "html")
    template_dir: str = str(_AGENT_CORE_ROOT / "app" / "templates")
    ppt_template_path: str = str(_DESIGN_DATA / "templates" / "template.pptx")

    idea_count: int = 3
    images_per_point: int = 1
    max_parallel_images: int = 8


settings = Settings()
