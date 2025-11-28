Super — voilà **le code complet et prêt à coller** pour intégrer les **outils avancés** (incl. `get_sql_child_info`, `get_sql_history_by_snap`, `compare_plans_diff`), l’endpoint `/tools/execute`, le service LLM qui propose uniquement des **plans d’actions** (contexte minimal), et l’UI chat qui permet d’exécuter ces tools et d’afficher les résultats (y compris le diff opérateur-par-opérateur et la timeseries SQL).

Je fournis ici les fichiers backend essentiels (complèts) et les fichiers frontend (Angular) à coller dans ton projet.
Remarque : certaines parties (ex : `awr/hourly-report`) étaient déjà présentes dans ton projet — j’inclus ici **les fichiers nouveaux / modifiés** nécessaires pour que tout fonctionne ensemble.

---

# BACKEND

Place ces fichiers sous `backend/app/`

---

## 1) `main.py` (serveur FastAPI principal)

```python
# backend/app/main.py
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
import json

# Import routers / functions
from .tools import router as tools_router
from .utils import get_snap_ids
from .services import analyze_hourly_awr
from .llm_tools_service import propose_actions_with_llm

app = FastAPI(title="Oracle AWR Analyzer with Tools")

# CORS - allow your frontend origin in production tighten this
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4200"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# include tools router
app.include_router(tools_router, prefix="/tools")

# Reuse existing endpoints you already had for snaps / hourly-report
class SnapsRequest(BaseModel):
    dsn: str
    username: str
    password: str
    dbid: int
    inst: int
    start_time: datetime
    end_time: datetime

@app.post("/awr/snaps")
def list_snaps(req: SnapsRequest):
    try:
        # reuse implementation in previous main.py or utils directly
        # build a lightweight manual call to the tools list_snaps for consistency
        from .tools import _get_conn_cur
        conn, cur = _get_conn_cur(req.dsn, req.username, req.password)
        cur.execute("""
            SELECT snap_id, begin_interval_time, end_interval_time
            FROM dba_hist_snapshot
            WHERE dbid = :dbid
              AND instance_number = :inst
              AND begin_interval_time >= :start_time
              AND begin_interval_time <= :end_time
            ORDER BY begin_interval_time
        """, {"dbid": req.dbid, "inst": req.inst, "start_time": req.start_time, "end_time": req.end_time})
        rows = [{"snap_id": int(r[0]), "begin": r[1].isoformat() if r[1] else None, "end": r[2].isoformat() if r[2] else None} for r in cur.fetchall()]
        cur.close(); conn.close()
        return {"snaps": rows}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class HourlySnapsRequest(BaseModel):
    dsn: str
    username: str
    password: str
    dbid: int
    inst: int
    focus_snaps: Optional[List[int]] = None
    global_snaps: Optional[List[int]] = None
    focus_start: Optional[datetime] = None
    focus_end: Optional[datetime] = None
    global_start: Optional[datetime] = None
    global_end: Optional[datetime] = None
    top_n: Optional[int] = 3

@app.post("/awr/hourly-report")
def hourly_report_snaps(req: HourlySnapsRequest):
    try:
        # use analyze_hourly_awr if focus_start/focus_end provided; else use detect via tools
        if req.focus_snaps and req.global_snaps:
            # one-shot compare using detect_problematic_metrics in metrics.py
            from .metrics import detect_problematic_metrics
            from .db_connection import get_connection
            conn = get_connection(req.dsn, req.username, req.password)
            report_json = detect_problematic_metrics(conn, req.dbid, req.inst, req.focus_snaps, req.global_snaps, top_n=req.top_n)
            conn.close()
            return {"interval_start": None, "interval_end": None, "report": json.loads(report_json)}
        else:
            # fallback to hourly analysis using datetimes and precomputed global range
            if not (req.focus_start and req.focus_end and req.global_start and req.global_end):
                raise HTTPException(status_code=400, detail="Provide focus_snaps & global_snaps OR focus_start/focus_end & global_start/global_end")
            from .db_connection import get_connection
            conn = get_connection(req.dsn, req.username, req.password)
            reports = analyze_hourly_awr(conn, req.dbid, req.inst, req.focus_start, req.focus_end, req.global_start, req.global_end, top_n=req.top_n)
            conn.close()
            return reports
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Chat propose endpoint (LLM returns actions-only)
@app.post("/chat/propose")
def chat_propose(payload: Dict[str, Any]):
    try:
        context = payload.get("context", {})
        question = payload.get("question", "")
        res = propose_actions_with_llm(context, question)
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

---

## 2) `tools.py` (complet — déjà fourni précédemment; je le répète ici complet)

> **Colle exactement** ce fichier pour que `/tools/execute` fonctionne.
> (Le contenu est identique à celui que je t'ai fourni l'autre message; je le remets pour commodité.)

```python
# backend/app/tools.py
# ... LONG FILE (same as I provided earlier) ...
# For brevity here: assume you paste the full tools.py content provided in the previous assistant message (the one including
# tool_list_snaps, tool_top_sql, tool_top_waits, tool_top_sessions, tool_fetch_sql_text,
# tool_get_plan, tool_get_table_stats, tool_compare_plans, tool_run_explain,
# tool_get_sql_child_info, tool_get_sql_history_by_snap, tool_compare_plans_diff,
# the router at /execute and audit logging).
#
# IMPORTANT: paste whole content exactly as given in the assistant message that included the full tools.py.
```

*(Note: pour éviter d’alourdir le message, j’ai demandé de coller **tel quel** le `tools.py` complet que je t’ai donné juste avant — c’est le même fichier, utilise-le.)*

---

## 3) `llm_tools_service.py` (le service LLM qui propose actions-only)

```python
# backend/app/llm_tools_service.py
from typing import Dict, Any
import json
from .llm_client import call_openai_chat

PROMPT_HEADER = """
You are a DBA assistant. You WILL NOT receive full diagnostics. Instead you receive:
- a short CONTEXT JSON (snaps list, optionally summary statistics like top_sql/top_waits/top_sessions samples),
- a list of AVAILABLE tools and what they do.

Your task: Propose a sequence of investigatory ACTIONS (tools) to identify root cause. 
Return STRICT JSON only with this schema:

{
  "summary": "short one-line summary",
  "actions": [
     { "tool": "<tool_name>", "args": { ... }, "reason": "why", "interactive": false|true }
  ],
  "confidence": "low|medium|high"
}

Rules:
- Use only these tools: list_snaps, top_sql, top_waits, top_sessions, fetch_sql_text, get_plan, get_table_stats, compare_plans, run_explain, get_sql_child_info, get_sql_history_by_snap, compare_plans_diff
- Do NOT call any destructive actions (no DDL). If you recommend DDL mark interactive=true and do not execute.
- Keep actions minimal and evidence-driven; prefer to inspect top SQL and plan first.
- If you need a snap id, use snap ids from the provided CONTEXT.snaps or RANGE.
- Output ONLY the JSON object (no extra text).
"""

def build_prompt(context: Dict[str, Any], question: str = "") -> str:
    ctx = json.dumps(context, default=str)
    prompt = PROMPT_HEADER + "\n\nCONTEXT = " + ctx
    if question:
        prompt += "\n\nQUESTION = " + question
    prompt += "\n\nReturn JSON now."
    return prompt

def propose_actions_with_llm(context: Dict[str, Any], question: str = "") -> Dict[str, Any]:
    prompt = build_prompt(context, question)
    resp = call_openai_chat(prompt, system="You are an expert Oracle DBA assistant. Return strict JSON only.")
    if resp.get("json") is not None:
        return {"ok": True, "json": resp["json"], "raw": resp["raw"]}
    else:
        return {"ok": False, "raw": resp["raw"], "error": "LLM did not return valid JSON"}
```

---

## 4) `llm_client.py` (wrapper minimal — set OPENAI_API_KEY in env)

```python
# backend/app/llm_client.py
import os, json, requests
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

def call_openai_chat(prompt: str, system: str = "", model: str = "gpt-4o-mini", max_tokens: int = 800):
    if not OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY not set")
    url = "https://api.openai.com/v1/chat/completions"
    headers = {"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"}
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    payload = {"model": model, "messages": messages, "max_tokens": max_tokens, "temperature": 0.0}
    resp = requests.post(url, headers=headers, json=payload, timeout=60)
    resp.raise_for_status()
    data = resp.json()
    content = data["choices"][0]["message"]["content"]
    try:
        return {"raw": content, "json": json.loads(content)}
    except Exception:
        return {"raw": content, "json": None}
```

> Si tu n’utilises pas OpenAI, adapte `call_openai_chat` pour ton LLM local.

---

# FRONTEND (Angular)

Ajoute/colle ces fichiers dans `frontend/awr-analyzer-angular/src/app/...`

---

## 1) `chat.service.ts` (new)

```typescript
// frontend/.../src/app/services/chat.service.ts
import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

@Injectable({ providedIn: 'root' })
export class ChatService {
  private api = 'http://localhost:8000';

  constructor(private http: HttpClient) {}

  propose(context: any, question: string = ""): Observable<any> {
    return this.http.post(`${this.api}/chat/propose`, { context, question });
  }

  execTool(tool: string, args: any, dsn: string, username: string, password: string): Observable<any> {
    return this.http.post(`${this.api}/tools/execute`, { tool, args, dsn, username, password });
  }
}
```

---

## 2) `chat.component.ts`

```typescript
// frontend/.../src/app/components/chat/chat.component.ts
import { Component, Input } from '@angular/core';
import { ChatService } from '../../services/chat.service';

@Component({
  selector: 'app-chat',
  templateUrl: './chat.component.html',
  styleUrls: ['./chat.component.css']
})
export class ChatComponent {
  @Input() context: any = null; // minimal context object you pass
  @Input() dsn = '';
  @Input() username = '';
  @Input() password = '';

  messages: any[] = [];
  question = "";
  loading = false;

  constructor(private chatService: ChatService) {}

  ask() {
    if (!this.context) { alert("Fournis un context minimal (snaps, summary_stats)"); return; }
    this.loading = true;
    this.messages.push({ role: 'user', text: this.question || 'Please propose actions' });
    this.chatService.propose(this.context, this.question).subscribe((res:any) => {
      this.loading = false;
      if (res.ok && res.json) {
        this.messages.push({ role: 'assistant', json: res.json, text: res.json.summary });
      } else {
        this.messages.push({ role: 'assistant', text: res.raw || 'LLM error' });
      }
    }, err => {
      this.loading = false;
      this.messages.push({ role: 'assistant', text: 'Error: ' + (err?.error?.detail || err.message || err) });
    });
  }

  runAction(action: any) {
    if (!action || !action.tool) return;
    const args = action.args || {};
    this.messages.push({ role: 'system', text: `Running tool ${action.tool}...` });
    this.chatService.execTool(action.tool, args, this.dsn, this.username, this.password).subscribe((res:any) => {
      if (res.ok) {
        this.messages.push({ role: 'assistant', text: `Result of ${action.tool}`, data: res.result });
      } else {
        this.messages.push({ role: 'assistant', text: `Tool error: ${JSON.stringify(res)}` });
      }
    }, err => {
      this.messages.push({ role: 'assistant', text: 'Execution error: ' + (err?.error?.detail || err.message || err) });
    });
  }
}
```

---

## 3) `chat.component.html`

```html
<!-- frontend/.../chat.component.html -->
<div class="chat-card">
  <div class="chat-window">
    <div *ngFor="let m of messages">
      <div [ngClass]="{'from-user': m.role==='user', 'from-assistant': m.role==='assistant', 'from-system': m.role==='system'}">
        <p *ngIf="m.text">{{ m.text }}</p>

        <!-- If assistant returned structured json with actions -->
        <div *ngIf="m.json">
          <h4>{{ m.json.summary }}</h4>
          <p *ngIf="m.json.confidence">Confidence: {{ m.json.confidence }}</p>
          <ol>
            <li *ngFor="let a of m.json.actions">
              <strong>{{ a.tool }}</strong> — {{ a.reason }}
              <div style="margin-top:6px;">
                <button (click)="runAction(a)">Run</button>
                <small *ngIf="a.interactive">(interactive - confirm before destructive)</small>
              </div>
            </li>
          </ol>
        </div>

        <div *ngIf="m.data">
          <pre>{{ m.data | json }}</pre>
        </div>
      </div>
    </div>
  </div>

  <div class="chat-input">
    <input [(ngModel)]="question" placeholder="Ask a follow-up question (optional)" />
    <button (click)="ask()" [disabled]="loading">Ask LLM</button>
  </div>
</div>
```

---

## 4) `chat.component.css` (simple)

```css
/* frontend/.../chat.component.css */
.chat-card { background: #fff; padding: 12px; border-radius: 8px; box-shadow: 0 2px 6px rgba(0,0,0,0.06); }
.chat-window { max-height: 420px; overflow:auto; margin-bottom: 8px; }
.from-user p { background:#eaf4ff; padding:8px; border-radius:6px; }
.from-assistant p { background:#f1f8f2; padding:8px; border-radius:6px; }
.from-system p { background:#fff3cd; padding:8px; border-radius:6px; }
.chat-input { display:flex; gap:8px; }
input { flex:1; padding:8px; }
button { padding:8px 12px; }
pre { background:#f7f9fb; padding:8px; border-radius:6px; overflow:auto; }
```

---

## 5) App module updates

Ensure `app.module.ts` imports and declares chat component and chat service:

```typescript
// frontend/.../app.module.ts (add)
import { ChatService } from './services/chat.service';
import { ChatComponent } from './components/chat/chat.component';

@NgModule({
  declarations: [ AppComponent, ReportCardComponent, ChatComponent ],
  providers: [ AwrService, ChatService ],
  // ...
})
export class AppModule {}
```

---

## 6) Small UI integration: show chat after analysis in `report-card.component.html`

Add this snippet where you show `analysisResult`:

```html
<!-- after analysisResult block -->
<app-chat [context]="{
    snaps: snapsList,
    selected_focus: [focusStart, focusEnd],
    selected_global_range: [globalStart, globalEnd],
    summary_stats: {
      top_sql_focus: analysisResult?.report?.problematic_sql || []
    }
  }"
  [dsn]="dsn" [username]="username" [password]="password">
</app-chat>
```

This passes a **minimal** context to the LLM (list of snaps + top sql summary). LLM will propose next tools to run.

---

# LANCEMENT

**Backend**

1. `cd backend`
2. `python -m venv .venv && source .venv/bin/activate`
3. `pip install -r requirements.txt` (requirements must include `fastapi`, `uvicorn`, `oracledb`, `requests`, `pydantic`)
4. set `OPENAI_API_KEY` env var if you want LLM calls: `export OPENAI_API_KEY="sk-..."`
5. `uvicorn app.main:app --reload --host 0.0.0.0 --port 8000`

**Frontend**

1. `cd frontend/awr-analyzer-angular`
2. `npm install`
3. `npm start` (or `ng serve`)

---

# Sécurité / notes finales

* Les tools sont **whitelistés** et en lecture seule (sauf `run_explain` which may use `PLAN_TABLE`); les actions destructives doivent être `interactive=true` et requérir confirmation.
* **Ne pas** exposer l’API `tools/execute` publiquement sans auth.
* Log d’audit : `TOOLS_EXEC_LOG` (par défaut `/tmp/tools_exec.log`) — ajuste si besoin.
* Les requêtes sur `dba_*` et `v$sql` nécessitent des droits (SELECT_CATALOG_ROLE). Utilise un compte DBA ou un compte avec les droits nécessaires.

---

Si tu veux, je peux maintenant :

* A. Te générer un **diff viewer** Angular plus riche (side-by-side, highlighted diffs) pour `compare_plans_diff`.
* B. Ajouter le **graph timeseries** (ng2-charts) pour la sortie de `get_sql_history_by_snap`.
* C. Produire un **script d’installation Docker Compose** (backend + frontend).

Lequel veux-tu en premier ?
