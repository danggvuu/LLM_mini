import sys, os, time
sys.path.append(os.getcwd())
from src.llm import get_llm
print("Loading model...")
start = time.time()
llm = get_llm("hf_local")
print(f"Loaded in {time.time()-start:.2f}s")
print("Invoking...")
start = time.time()
res = llm.invoke("hello world")
print(f"Invoked in {time.time()-start:.2f}s")
print("Result:", res)
