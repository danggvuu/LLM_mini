import sys, os
sys.path.append(os.getcwd())
from src.interfaces.ui import _api_stream
print("Starting stream...")
for chunk in _api_stream("/ask/stream", {"question":"hello", "k":3, "filters":{"notebook_id":"526863bb"}}):
    print(repr(chunk))
print("Done")
