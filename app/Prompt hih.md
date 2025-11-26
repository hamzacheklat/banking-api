Voici exactement ce que tu demandes :

---

# ✅ **1) Les 3 tasks que tu veux automatiser**

### **Task 1 — Top SQL Increase**

Identifier les **3 SQL_ID** qui augmentent le plus dans l’intervalle FOCUS comparé au GLOBAL.

### **Task 2 — Wait Events Increase**

Identifier les **wait events** dont le temps d’attente ou le nombre de waits augmente fortement dans FOCUS vs GLOBAL.

### **Task 3 — Abnormal Sessions**

Identifier les **sessions** (SID) ayant une activité anormale (CPU, waits, activity spikes) dans FOCUS vs GLOBAL.

---

# ✅ **2) Traduction ENGLISH → Prompt SUMMARY (FOCUS or GLOBAL)**

```
You are an Oracle expert specialized in AWR report analysis.

Requested task: {{task}}

I will provide you with a large AWR section.  
Your mission is to produce a concise, normalized JSON summary containing only the elements that are relevant to the task "{{task}}".

Your summary must strictly follow this structure:

{
  "sql": [
    {
      "sql_id": "...",
      "elapsed_time": "...",
      "cpu_time": "...",
      "buffer_gets": "...",
      "disk_reads": "...",
      "executions": "...",
      "comment": "1-line summary"
    }
  ],
  "events": [
    {
      "event": "...",
      "wait_time": "...",
      "waits": "...",
      "comment": "1-line summary"
    }
  ],
  "sessions": [
    {
      "sid": "...",
      "cpu": "...",
      "wait_time": "...",
      "comment": "1-line summary"
    }
  ],
  "summary": "4-line global summary"
}

Rules:
- Do NOT invent any data.
- Only summarize what appears in the provided AWR section.
- Ignore everything that is not relevant to "{{task}}".
- Output must be STRICT JSON, compact, and without extra text.

Here is the AWR section:
{{awr_section}}
```

---

# ✅ **3) Traduction ENGLISH → Prompt COMPARISON**

```
You are an Oracle expert specialized in AWR comparative performance analysis.

Requested task: {{task}}

I will provide you with two JSON summaries:
- A GLOBAL summary
- A FOCUS summary

Your mission is to compare the FOCUS interval against the GLOBAL interval and detect variations, increases, or anomalies according to the task "{{task}}".

Expected work:

1. Identify the Top 3 SQL_IDs with the highest increase 
   (elapsed_time, cpu_time, buffer_gets, disk_reads, executions).

2. Identify wait events showing a significant increase in the FOCUS interval.

3. Identify sessions that show abnormal behavior 
   (CPU increase, unusual waits, activity spikes).

4. Explain all anomalies clearly.

5. Produce a final TABLE summarizing the comparison,
   followed by a structured JSON output:

{
  "sql_top_increase": [...],
  "events_anomalies": [...],
  "sessions_anomalies": [...],
  "summary": "...",
  "conclusion": "..."
}

Rules:
- Use ONLY the values found in the provided summaries.
- Do NOT invent or assume anything.
- An element is considered “increased” only if its metric is strictly higher in FOCUS.

Here are the summaries:

--- GLOBAL ---
{{summary_global}}

--- FOCUS ---
{{summary_focus}}
```

---

# ✅ **4) Format final demandé = a TABLE**

Voici le format attendu lors de la COMPARISON :

### **Final Output Table Example**

| Category        | Item             | Focus Value | Global Value | Delta | Comment            |
| --------------- | ---------------- | ----------- | ------------ | ----- | ------------------ |
| SQL Increase    | sql_id XXXXXX    | 120s CPU    | 20s CPU      | +100s | Spike in CPU time  |
| Wait Event      | db file seq read | 400s        | 90s          | +310s | Higher IO latency  |
| Session Anomaly | SID 123          | 70% CPU     | 5% CPU       | +65%  | Abnormal CPU usage |

Et **après cette table**, il doit retourner le JSON final.

---

# 🎯 Tu as maintenant :

✔ Les 3 tasks
✔ Les 2 prompts **traduits en anglais**
✔ Le format final demandé = **une table + JSON**

---

Si tu veux, je peux maintenant te fournir :
🔧 un **script Python complet** (summary + comparison)
📦 une **classe AWRAnalyzer**
⚙️ une **version plus condensée** optimisée pour les modèles plus petits

Souhaites-tu l’un de ces modules ?
