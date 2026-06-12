"""
GGUF LLM Execution Module
Leverages llama-cpp-python to run quantized 4-bit models locally.
Ideal for 4GB VRAM cards where standard HuggingFace models cause OOM.
"""
import logging
from typing import Iterator
from functools import lru_cache

from src.config import settings

logger = logging.getLogger(__name__)

@lru_cache(maxsize=1)
def get_llama_cpp():
    from huggingface_hub import hf_hub_download
    from llama_cpp import Llama
    
    repo_id = settings.gguf_model_repo
    filename = settings.gguf_model_file
    
    logger.info("Downloading/Loading GGUF model: %s / %s", repo_id, filename)
    
    model_path = hf_hub_download(repo_id=repo_id, filename=filename)
    
    logger.info("Initializing LlamaCpp from: %s", model_path)
    
    # n_gpu_layers=-1 means offload all layers to GPU
    # n_batch=2048 drastically speeds up prompt evaluation (Time-to-First-Token) for long RAG contexts
    llm = Llama(
        model_path=model_path,
        n_ctx=4096,
        n_batch=2048,
        n_gpu_layers=-1,
        chat_format="chatml",
        verbose=False
    )
    
    logger.info("LlamaCpp initialized successfully.")
    return llm

def invoke_gguf(messages: list) -> str:
    llm = get_llama_cpp()
    logger.info("Invoking GGUF model via create_chat_completion...")
    response = llm.create_chat_completion(
        messages=messages,
        max_tokens=settings.hf_max_new_tokens,
        temperature=max(0.4, settings.llm_temperature),
        repeat_penalty=1.15,
    )
    return response["choices"][0]["message"]["content"]

def stream_gguf(messages: list) -> Iterator[str]:
    llm = get_llama_cpp()
    logger.info("Streaming GGUF model via create_chat_completion...")
    stream = llm.create_chat_completion(
        messages=messages,
        max_tokens=settings.hf_max_new_tokens,
        temperature=max(0.4, settings.llm_temperature),
        repeat_penalty=1.15,
        stream=True
    )
    for chunk in stream:
        delta = chunk["choices"][0].get("delta", {})
        if "content" in delta:
            yield delta["content"]

class GGUFChatAdapter:
    """Adapter to make LlamaCpp act like a LangChain ChatModel."""
    def _convert(self, messages):
        if not isinstance(messages, list):
            messages = [messages]
        out = []
        for m in messages:
            role = "user"
            if getattr(m, "type", "") == "system": role = "system"
            elif getattr(m, "type", "") == "ai": role = "assistant"
            out.append({"role": role, "content": getattr(m, "content", str(m))})
        return out

    def invoke(self, messages):
        msgs = self._convert(messages)
        class Response:
            content = invoke_gguf(msgs)
        return Response()

    def stream(self, messages):
        msgs = self._convert(messages)
        class Chunk:
            def __init__(self, c):
                self.content = c
        for c in stream_gguf(msgs):
            yield Chunk(c)

@lru_cache(maxsize=1)
def get_gguf_llm():
    return GGUFChatAdapter()

# Force Uvicorn reload
