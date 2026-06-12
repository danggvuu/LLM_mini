import sys, os
sys.path.append(os.getcwd())
from src.llm import stream_llm
print("Starting...")
for c in stream_llm("hello", "hf_local"):
    print(repr(c))
print("Done")
