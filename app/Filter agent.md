from core.llm import call_llm
import json

class TextFilterAgent:

    def should_ingest(self, text: str) -> dict:
        prompt = f"""
You are a document ingestion filter for an Oracle RAG system.

Decide if the following text contains useful Oracle technical knowledge.

Rules:
- Accept only if technical and factual
- Reject intros, images, marketing, TOC
- Return JSON only

TEXT:
{text}

OUTPUT:
{{"decision":"INGEST|SKIP","reason":""}}
"""
        return json.loads(call_llm(prompt))
