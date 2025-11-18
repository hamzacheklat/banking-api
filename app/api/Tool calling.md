import os
from dotenv import load_dotenv
from openai import OpenAI
from awr_oracle import get_top_sqls_between_snaps, get_sql_plan, get_sql_text

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=OPENAI_API_KEY)

TOOLS = {}

def register_tools(dbid, inst, oracle_user, oracle_password, oracle_dsn):
    global TOOLS
    TOOLS = {
        "get_top_sqls": lambda snap_start, snap_end, limit=5: get_top_sqls_between_snaps(
            snap_start, snap_end, dbid, inst, oracle_user, oracle_password, oracle_dsn, limit=limit
        ),
        "get_sql_plan": lambda sql_id, limit=2000: get_sql_plan(
            sql_id, dbid, inst, oracle_user, oracle_password, oracle_dsn, limit=limit
        ),
        "get_sql_text": lambda sql_id: get_sql_text(
            sql_id, dbid, inst, oracle_user, oracle_password, oracle_dsn
        ),
    }

# -----------------------------
# Section-level tuning
# -----------------------------
def run_section_tuning(section_name: str, section_text: str, dbid: int, inst: int,
                       oracle_user: str, oracle_password: str, oracle_dsn: str) -> dict:
    register_tools(dbid, inst, oracle_user, oracle_password, oracle_dsn)

    prompt = f"""
You are a senior Oracle Database Performance Tuning expert.
Analyze this section: {section_name}
Include:
- Problem
- Cause
- Recommendations (precise)
- Snap range (if identifiable)
You may call backend tools: get_top_sqls, get_sql_plan, get_sql_text.
Keep concise and structured.
SECTION CONTENT:
{section_text}
"""

    functions = [
        {
            "name": "get_top_sqls",
            "description": "Retrieve top SQLs between snapshots",
            "parameters": {
                "type": "object",
                "properties": {
                    "snap_start": {"type": "integer"},
                    "snap_end": {"type": "integer"},
                    "limit": {"type": "integer", "default": 5}
                },
                "required": ["snap_start", "snap_end"]
            }
        },
        {
            "name": "get_sql_plan",
            "description": "Retrieve SQL plan for a SQL ID",
            "parameters": {
                "type": "object",
                "properties": {
                    "sql_id": {"type": "string"},
                    "limit": {"type": "integer", "default": 2000}
                },
                "required": ["sql_id"]
            }
        },
        {
            "name": "get_sql_text",
            "description": "Retrieve SQL text for a SQL ID",
            "parameters": {
                "type": "object",
                "properties": {
                    "sql_id": {"type": "string"}
                },
                "required": ["sql_id"]
            }
        }
    ]

    messages = [
        {"role": "system", "content": "You are an Oracle tuning expert."},
        {"role": "user", "content": prompt}
    ]

    try:
        resp = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=messages,
            functions=functions,
            temperature=0.05,
            max_tokens=2500
        )

        message = resp.choices[0].message
        result = {"content": message.get("content", ""), "functions_called": []}

        # Function call handling
        if message.get("function_call"):
            fn_call = message["function_call"]
            fn_name = fn_call["name"]
            arguments = eval(fn_call.get("arguments", "{}"))
            if fn_name in TOOLS:
                tool_result = TOOLS[fn_name](**arguments)
                result["functions_called"].append({
                    "function": fn_name,
                    "arguments": arguments,
                    "result": tool_result
                })
                # Continue conversation with LLM providing function result
                followup = client.chat.completions.create(
                    model="gpt-4.1-mini",
                    messages=[
                        *messages,
                        {"role": "assistant", "content": message.get("content") or ""},
                        {"role": "function", "name": fn_name, "content": str(tool_result)}
                    ],
                    temperature=0.05,
                    max_tokens=2500
                )
                result["content"] = followup.choices[0].message.get("content", "")

        return result
    except Exception as e:
        return {"content": f"[ERROR] OpenAI call failed: {e}", "functions_called": []}

# -----------------------------
# Final summary
# -----------------------------
def run_final_summary(section_results: dict, dbid: int, inst: int,
                      oracle_user: str, oracle_password: str, oracle_dsn: str) -> dict:
    register_tools(dbid, inst, oracle_user, oracle_password, oracle_dsn)

    combined_results = "\n\n".join([f"### Section: {k}\n{v['content']}" for k,v in section_results.items()])

    prompt = f"""
You are a senior Oracle Database Performance Tuning expert.
Produce a final summary of all detected problems from the sections below.
Include:
- Problem
- Cause
- Section
- Snap range (if identifiable)
You may call backend tools: get_top_sqls, get_sql_plan, get_sql_text.
Keep concise and structured.
SECTION RESULTS:
{combined_results}
"""

    functions = [
        {
            "name": "get_top_sqls",
            "description": "Retrieve top SQLs between snapshots",
            "parameters": {
                "type": "object",
                "properties": {
                    "snap_start": {"type": "integer"},
                    "snap_end": {"type": "integer"},
                    "limit": {"type": "integer", "default": 5}
                },
                "required": ["snap_start", "snap_end"]
            }
        },
        {
            "name": "get_sql_plan",
            "description": "Retrieve SQL plan for a SQL ID",
            "parameters": {
                "type": "object",
                "properties": {
                    "sql_id": {"type": "string"},
                    "limit": {"type": "integer", "default": 2000}
                },
                "required": ["sql_id"]
            }
        },
        {
            "name": "get_sql_text",
            "description": "Retrieve SQL text for a SQL ID",
            "parameters": {
                "type": "object",
                "properties": {
                    "sql_id": {"type": "string"}
                },
                "required": ["sql_id"]
            }
        }
    ]

    messages = [
        {"role": "system", "content": "You are an Oracle tuning expert."},
        {"role": "user", "content": prompt}
    ]

    try:
        resp = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=messages,
            functions=functions,
            temperature=0.05,
            max_tokens=3000
        )

        message = resp.choices[0].message
        result = {"content": message.get("content", ""), "functions_called": []}

        if message.get("function_call"):
            fn_call = message["function_call"]
            fn_name = fn_call["name"]
            arguments = eval(fn_call.get("arguments", "{}"))
            if fn_name in TOOLS:
                tool_result = TOOLS[fn_name](**arguments)
                result["functions_called"].append({
                    "function": fn_name,
                    "arguments": arguments,
                    "result": tool_result
                })
                followup = client.chat.completions.create(
                    model="gpt-4.1-mini",
                    messages=[
                        *messages,
                        {"role": "assistant", "content": message.get("content") or ""},
                        {"role": "function", "name": fn_name, "content": str(tool_result)}
                    ],
                    temperature=0.05,
                    max_tokens=3000
                )
                result["content"] = followup.choices[0].message.get("content", "")

        return result
    except Exception as e:
        return {"content": f"[ERROR] OpenAI call failed: {e}", "functions_called": []}
