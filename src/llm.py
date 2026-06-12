"""
LLM Factory Pattern — Tầng Tạo sinh
Supports 3 backends: vLLM (Production), HuggingFace (Dev), Gemini (Baseline).
Provides both synchronous invoke and async streaming interfaces.
"""
from functools import lru_cache
from typing import List, Optional, Any, Iterator
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_openai import ChatOpenAI
from src.config import settings


# ---------------------------------------------------------------------------
# LLM Factory — Build functions
# ---------------------------------------------------------------------------

def _build_hf_local():
    if settings.low_vram_mode:
        from src.llm_gguf import get_gguf_llm
        return get_gguf_llm()

    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline
    from langchain_huggingface import ChatHuggingFace, HuggingFacePipeline

    tokenizer = AutoTokenizer.from_pretrained(settings.hf_model)
    model = AutoModelForCausalLM.from_pretrained(
        settings.hf_model,
        dtype=torch.bfloat16,
        device_map=settings.hf_device
    )

    text_gen = pipeline(
        task="text-generation",
        model=model,
        tokenizer=tokenizer,
        return_full_text=False,
    )
    text_gen.generation_config.max_new_tokens = settings.hf_max_new_tokens
    text_gen.generation_config.do_sample = settings.llm_temperature > 0

    return ChatHuggingFace(llm=HuggingFacePipeline(pipeline=text_gen))


def _build_gemini():
    from langchain_google_genai import ChatGoogleGenerativeAI
    return ChatGoogleGenerativeAI(
        model=settings.gemini_model,
        temperature=settings.llm_temperature,
        google_api_key=settings.google_api_key,
    )


def _build_vllm():
    return ChatOpenAI(
        model=settings.hf_model,
        openai_api_key=settings.vllm_api_key,
        openai_api_base=settings.vllm_api_base,
        temperature=settings.llm_temperature,
    )


# ---------------------------------------------------------------------------
# LLM Factory — Public API
# ---------------------------------------------------------------------------

_BUILDERS = {
    "hf_local": _build_hf_local,
    "gemini": _build_gemini,
    "vllm": _build_vllm,
}


@lru_cache(maxsize=4)
def get_llm(provider=None) -> BaseChatModel:
    """
    LLM Factory Pattern.
    Returns the appropriate LLM instance based on provider config.
    """
    provider = provider or settings.llm_provider
    builder = _BUILDERS.get(provider)
    if builder is None:
        raise ValueError(f"Unknown llm_provider '{provider}'. Available: {list(_BUILDERS.keys())}")
    return builder()


def invoke_llm(prompt: str, provider=None) -> str:
    """Invoke LLM synchronously. Returns the full response text."""
    response = get_llm(provider=provider).invoke([HumanMessage(content=prompt)])
    return response.content if isinstance(response.content, str) else str(response.content)


def stream_llm(prompt: str, provider=None) -> Iterator[str]:
    """
    Stream LLM response token by token.
    Falls back to single-shot invoke if streaming is not supported.
    """
    llm = get_llm(provider=provider)

    # Use LangChain streaming interface for all providers
    if hasattr(llm, 'stream'):
        try:
            for chunk in llm.stream([HumanMessage(content=prompt)]):
                content = chunk.content if hasattr(chunk, 'content') else str(chunk)
                if content:
                    yield content
            return
        except Exception:
            pass  # Fall through to non-streaming

    # Fallback: invoke and yield all at once
    yield invoke_llm(prompt, provider=provider)
