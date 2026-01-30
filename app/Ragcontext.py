from core.llm import call_llm

class FinalAnswerAgent:

    def refine(self, assistant_first_answer: str, rag_context: str) -> str:
        prompt = f"""
You are a senior Oracle performance tuning expert.

TASK:
Refine and validate the initial assistant answer using ONLY the RAG context.

RULES:
- Use RAG_CONTEXT as the only source of truth
- Keep what is correct in FIRST_ASSISTANT_ANSWER
- Correct anything unsupported by RAG_CONTEXT
- Add missing technical details ONLY if present in RAG_CONTEXT
- Do NOT add generic Oracle advice
- If RAG_CONTEXT is insufficient, explicitly say it
- Be precise, technical, concise

FIRST_ASSISTANT_ANSWER:
{assistant_first_answer}

RAG_CONTEXT:
{rag_context}

OUTPUT:
Return the final improved answer (no JSON).
"""
        return call_llm(prompt).strip()
