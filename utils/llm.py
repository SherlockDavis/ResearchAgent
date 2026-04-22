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
    """创建 LLM 实例

    支持的平台及对应模型名前缀：
      - openai    : gpt-4o / gpt-4o-mini / o1 ...
      - anthropic : claude-*
      - deepseek  : deepseek-*
      - aliyun    : qwen-*
      - google    : gemini-*
      - groq      : llama-* / mixtral-* / gemma-* （需显式传 provider='groq'）
      - mistral   : mistral-* / open-mistral-* / codestral-*
      - zhipu     : glm-*
      - moonshot  : moonshot-*
      - doubao    : doubao-*
      - minimax   : abab*

    Args:
        model: 模型名称，默认从配置读取
        temperature: 温度参数
        provider: 显式指定平台，优先级高于模型名称推断

    Returns:
        BaseChatModel实例
    """
    settings = get_settings()

    if temperature is None:
        temperature = settings.DEFAULT_TEMPERATURE

    if model is None:
        model = settings.DEFAULT_MODEL

    def _openai_compat(api_key: str, base_url: str) -> ChatOpenAI:
        """OpenAI 居合式通用构造"""
        if not api_key:
            raise ValueError(f"未配置 API 密钥，请检查 .env 文件")
        return ChatOpenAI(
            model=model,
            temperature=temperature,
            max_tokens=settings.MAX_TOKENS,
            api_key=api_key,
            base_url=base_url,
            timeout=settings.LLM_REQUEST_TIMEOUT,
        )

    # 显式指定 provider 或根据模型名首词自动识别
    p = (provider or "").lower()
    m = model.lower()

    if p == "anthropic" or m.startswith("claude"):
        if not settings.ANTHROPIC_API_KEY:
            raise ValueError("ANTHROPIC_API_KEY not set")
        return ChatAnthropic(
            model=model,
            temperature=temperature,
            max_tokens=settings.MAX_TOKENS,
            anthropic_api_key=settings.ANTHROPIC_API_KEY,
            anthropic_api_url=settings.ANTHROPIC_BASE_URL,
        )
    elif p == "deepseek" or m.startswith("deepseek"):
        return _openai_compat(settings.DEEPSEEK_API_KEY, settings.DEEPSEEK_BASE_URL)
    elif p == "aliyun" or m.startswith("qwen"):
        return _openai_compat(settings.ALIYUN_API_KEY, settings.ALIYUN_BASE_URL)
    elif p == "google" or m.startswith("gemini"):
        return _openai_compat(settings.GOOGLE_API_KEY, settings.GOOGLE_BASE_URL)
    elif p == "groq":
        return _openai_compat(settings.GROQ_API_KEY, settings.GROQ_BASE_URL)
    elif p == "mistral" or m.startswith(("mistral", "open-mistral", "codestral")):
        return _openai_compat(settings.MISTRAL_API_KEY, settings.MISTRAL_BASE_URL)
    elif p == "zhipu" or m.startswith("glm"):
        return _openai_compat(settings.ZHIPU_API_KEY, settings.ZHIPU_BASE_URL)
    elif p == "moonshot" or m.startswith("moonshot"):
        return _openai_compat(settings.MOONSHOT_API_KEY, settings.MOONSHOT_BASE_URL)
    elif p == "doubao" or m.startswith("doubao"):
        return _openai_compat(settings.DOUBAO_API_KEY, settings.DOUBAO_BASE_URL)
    elif p == "minimax" or m.startswith("abab"):
        return _openai_compat(settings.MINIMAX_API_KEY, settings.MINIMAX_BASE_URL)
    else:
        # 默认 OpenAI
        return _openai_compat(settings.OPENAI_API_KEY, settings.OPENAI_BASE_URL)
