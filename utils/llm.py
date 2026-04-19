"""LLM工具函数"""
from typing import Optional
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_core.language_models import BaseChatModel
from config import get_settings


def create_llm(
    model: Optional[str] = None,
    temperature: Optional[float] = None,
    provider: Optional[str] = None,
) -> BaseChatModel:
    """创建LLM实例

    Args:
        model: 模型名称，默认从配置读取
        temperature: 温度参数
        provider: 提供商 ('openai', 'anthropic', 'deepseek')

    Returns:
        BaseChatModel实例
    """
    settings = get_settings()

    if temperature is None:
        temperature = settings.DEFAULT_TEMPERATURE

    if model is None:
        model = settings.DEFAULT_MODEL

    # 根据provider或模型名称选择
    if provider == "anthropic" or model.startswith("claude"):
        if not settings.ANTHROPIC_API_KEY:
            raise ValueError("ANTHROPIC_API_KEY not set")
        return ChatAnthropic(
            model=model,
            temperature=temperature,
            max_tokens=settings.MAX_TOKENS,
            anthropic_api_key=settings.ANTHROPIC_API_KEY,
            anthropic_api_url=settings.ANTHROPIC_BASE_URL,
        )
    elif provider == "deepseek" or model.startswith("deepseek"):
        if not settings.DEEPSEEK_API_KEY:
            raise ValueError("DEEPSEEK_API_KEY not set")
        return ChatOpenAI(
            model=model,
            temperature=temperature,
            max_tokens=settings.MAX_TOKENS,
            api_key=settings.DEEPSEEK_API_KEY,
            base_url=settings.DEEPSEEK_BASE_URL,
            timeout=settings.LLM_REQUEST_TIMEOUT,
        )
    elif provider == "aliyun" or model.startswith("qwen"):
        if not settings.ALIYUN_API_KEY:
            raise ValueError("ALIYUN_API_KEY not set")
        return ChatOpenAI(
            model=model,
            temperature=temperature,
            max_tokens=settings.MAX_TOKENS,
            api_key=settings.ALIYUN_API_KEY,
            base_url=settings.ALIYUN_BASE_URL,
            timeout=settings.LLM_REQUEST_TIMEOUT,
        )
    else:
        # OpenAI 或兼容 OpenAI 格式的 API
        api_key = settings.OPENAI_API_KEY
        base_url = settings.OPENAI_BASE_URL
        
        if not api_key:
            raise ValueError("OPENAI_API_KEY not set")
        return ChatOpenAI(
            model=model,
            temperature=temperature,
            max_tokens=settings.MAX_TOKENS,
            api_key=api_key,
            base_url=base_url,
            timeout=settings.LLM_REQUEST_TIMEOUT,
        )
