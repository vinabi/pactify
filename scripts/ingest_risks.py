# scripts/ingest_risks.py
import os, glob
from uuid import uuid4
from agents.tools_vector import get_chroma

CHROMA_DIR = os.environ.get("CHROMA_DIR", ".chroma")
KB_NAME = "risk_knowledge"

def load_md_texts():
    items = []
    for p in glob.glob("knowledge/**/*.md", recursive=True):
        with open(p, "r", encoding="utf-8") as f:
            items.append((p, f.read()))
    return items

def main():
    vect = get_chroma(CHROMA_DIR)
    try:
        coll = vect.get_collection(KB_NAME)
    except Exception:
        coll = vect.create_collection(KB_NAME)
    docs = load_md_texts()
    if not docs:
        print("No markdown files found under knowledge/")
        return
    ids, texts, metas = [], [], []
    for p, t in docs:
        ids.append(str(uuid4()))
        texts.append(t)
        metas.append({"source": p, "kind": "risk"})
    coll.add(ids=ids, documents=texts, metadatas=metas)
    print(f"Ingested {len(texts)} docs into '{KB_NAME}' at {CHROMA_DIR}")

if __name__ == "__main__":
    main()
