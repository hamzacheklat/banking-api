# llm_client.py
from openai import AsyncOpenAI

client: AsyncOpenAI | None = None

def get_client() -> AsyncOpenAI:
    global client
    if client is None:
        client = AsyncOpenAI(
            api_key="XXX",
            base_url="https://core-infrasty-ll-dev.xnp.net.intra/v1"
        )
    return client
