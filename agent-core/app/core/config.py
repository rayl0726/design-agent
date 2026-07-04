from pydantic_settings import BaseSettings, SettingsConfigDict


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

    upload_dir: str = "../design-data/uploads"
    image_cache_dir: str = "../design-data/images"
    template_dir: str = "app/templates"
    ppt_template_path: str = "../design-data/templates/template.pptx"


settings = Settings()
