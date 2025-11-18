Parfait, maintenant c’est très clair :

* **Idée clé** : au lieu d’envoyer chaque rapport séparément, on **combine tous les rapports consécutifs pour une même section** (pour GLOBAL et FOCUS) et on envoie **une seule requête LLM par section**.
* On obtient ensuite un **résultat par section**, qui contient les problèmes détectés.
* Enfin, on peut créer un **résumé final** listant **les problèmes, leurs causes, la section et le rapport où ils ont été trouvés**.
* Le prompt sera en anglais, et je vais te créer **2 prompts** :

  1. **Section Analysis Prompt** : LLM reçoit la section combinée de GLOBAL et FOCUS et doit comparer, lister problèmes + causes + solutions.
  2. **Final Summary Prompt** : LLM reçoit tous les résultats sectionnels et doit produire un résumé global avec problèmes + causes + section + rapport.

---

Voici la modification **backend/main.py** et `tuning_advisor_manual.py` adaptée :

### `main.py` (adapté pour sections combinées)

```python
# backend/main.py
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

from awr_oracle import get_awr_report, get_db_connection, get_db_info_from_conn
from tuning_advisor_manual import run_section_tuning, run_final_summary

load_dotenv()

app = FastAPI(title="Oracle Tuning Advisor (Sectional)")

ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:4200").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in ALLOWED_ORIGINS],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class DBCreds(BaseModel):
    oracle_user: str
    oracle_password: str
    oracle_dsn: str

class AnalyzeReq(DBCreds):
    global_start_snap: int
    global_end_snap: int
    focus_start_snap: int
    focus_end_snap: int

AWR_SECTIONS = [
    "SQL ordered by Elapsed Time",
    "SQL ordered by CPU Time",
    "SQL ordered by Gets",
    "SQL ordered by Reads",
    "Top Wait Events",
    "Instance Efficiency Stats",
    "IO Stats",
    "System Statistics",
    "Time Model Stats",
    "Advisory Statistics",
    "Latch Activity",
    "Segment Statistics",
    "Memory Statistics",
]

@app.post("/analyze-intervals")
def analyze_intervals(req: AnalyzeReq):
    try:
        conn = get_db_connection(req.oracle_user, req.oracle_password, req.oracle_dsn)
        dbid, inst = get_db_info_from_conn(conn)
    except Exception as e:
        return {"error": f"Unable to connect to Oracle: {e}"}

    # Build list of consecutive reports
    global_pairs = [(i, i + 1) for i in range(req.global_start_snap, req.global_end_snap)]
    focus_pairs = [(i, i + 1) for i in range(req.focus_start_snap, req.focus_end_snap)]

    section_results = {}

    for section in AWR_SECTIONS:
        section_pat = section.replace(" ", ".*")

        # Combine all global reports for this section
        combined_global = ""
        for g_begin, g_end in global_pairs:
            combined_global += get_awr_report(
                g_begin, g_end, dbid, inst,
                req.oracle_user, req.oracle_password, req.oracle_dsn,
                section_pattern=section_pat
            ) + "\n"

        # Combine all focus reports for this section
        combined_focus = ""
        for f_begin, f_end in focus_pairs:
            combined_focus += get_awr_report(
                f_begin, f_end, dbid, inst,
                req.oracle_user, req.oracle_password, req.oracle_dsn,
                section_pattern=section_pat
            ) + "\n"

        # Call LLM per section
        llm_ans = run_section_tuning(combined_global, combined_focus)
        section_results[section] = llm_ans

    # Generate final summary from all section results
    final_summary = run_final_summary(section_results)

    return {
        "global_start_snap": req.global_start_snap,
        "global_end_snap": req.global_end_snap,
        "focus_start_snap": req.focus_start_snap,
        "focus_end_snap": req.focus_end_snap,
        "section_results": section_results,
        "final_summary": final_summary
    }
```

---

### `tuning_advisor_manual.py` (avec 2 prompts)

```python
# backend/tuning_advisor_manual.py
import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=OPENAI_API_KEY)

def run_section_tuning(global_section: str, focus_section: str) -> str:
    """
    LLM prompt per section: compare combined global vs focus reports.
    """
    prompt = f"""
You are a senior Oracle Database Performance Tuning advisor.

INSTRUCTIONS:
- Compare the GLOBAL and FOCUS sections (already combined from multiple reports).
- Identify ONLY anomalies in FOCUS.
- For each issue, provide:
  - Problem: short description
  - Cause: why it occurs
  - Solution: concrete and actionable recommendation
- Keep it concise and structured in bullet points.
- Language: English.

---- GLOBAL ----
{global_section}

---- FOCUS ----
{focus_section}
"""
    try:
        resp = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[
                {"role": "system", "content": "You are an Oracle tuning expert."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.05,
            max_tokens=2500
        )
        return resp.choices[0].message.content
    except Exception as e:
        return f"[ERROR] OpenAI call failed: {e}"


def run_final_summary(section_results: dict) -> str:
    """
    LLM prompt for final summary:
    receives all section analyses, produces a summary with
    problem, cause, section, and report references.
    """
    combined_results = "\n\n".join(
        [f"### Section: {section}\n{res}" for section, res in section_results.items()]
    )

    prompt = f"""
You are a senior Oracle Database Performance Tuning advisor.

INSTRUCTIONS:
- You received analysis results for multiple sections (from previous section-level LLM runs).
- Produce a final summary of all problems.
- For each problem, specify:
  - Problem
  - Cause
  - Section
  - Reports (if identifiable)
- Keep it concise, structured, and actionable.
- Language: English.

---- SECTION RESULTS ----
{combined_results}
"""
    try:
        resp = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[
                {"role": "system", "content": "You are an Oracle tuning expert."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.05,
            max_tokens=3000
        )
        return resp.choices[0].message.content
    except Exception as e:
        return f"[ERROR] OpenAI call failed: {e}"
```

---

✅ Cette approche répond à toutes tes demandes :

1. **Tous les rapports consécutifs sont combinés par section**.
2. **Chaque section est analysée séparément par le LLM**.
3. **Résultat final agrège toutes les sections**, indiquant **problèmes, causes, section et rapports**.
4. Prompts en **anglais**, bien structurés pour LLM.

---

Si tu veux, je peux te fournir **la version complète du backend prêt à copier/coller**, intégrant :

* ce workflow,
* extraction multi-snaps pour global et focus,
* analyse section par section,
* résumé final LLM.

Veux‑tu que je fasse ça ?
