import sys
import os
sys.path.append(os.getcwd())
from src.llm import invoke_llm
print(invoke_llm("reranker là gì ?", provider="hf_local"))
