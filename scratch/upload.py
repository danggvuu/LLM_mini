import requests
import json

filename = "data/[Description]-Building-Simple-NotebookLM.pdf"
notebook_id = "57f47e76"
url = f"http://127.0.0.1:8000/upload/{notebook_id}"

with open(filename, "rb") as f:
    res = requests.post(
        url,
        files={"file": ("[Description]-Building-Simple-NotebookLM.pdf", f, "application/pdf")}
    )

print("Upload response:", res.text)
