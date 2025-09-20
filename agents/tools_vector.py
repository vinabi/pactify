import os
from typing import List, Tuple
import chromadb
from chromadb.utils import embedding_functions

def get_chroma(persist_dir: str):
    client = chromadb.PersistentClient(path=persist_dir)
    return client


def ensure_precedent_collection(client, name="precedents"):
    ef = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name="all-MiniLM-L6-v2"
    )
    col = client.get_or_create_collection(name=name, embedding_function=ef)
    return col


def retrieve_precedents(client, query: str, k: int = 3) -> List[Tuple[str, str]]:
    col = ensure_precedent_collection(client)
    if not query.strip():
        return []
    res = col.query(query_texts=[query], n_results=k)
    out = []
    for doc, meta in zip(res.get("documents", [[]])[0], res.get("metadatas", [[]])[0]):
        out.append((meta.get("title", "Precedent"), doc))
    return out

def retrieve_snippets(vect_client, collection: str, query: str, k: int = 3):
    coll = vect_client.get_collection(collection)
    res = coll.query(query_texts=[query], n_results=k)
    docs = res.get("documents", [[]])[0]
    metas = res.get("metadatas", [[]])[0]
    return list(zip(metas, docs))
