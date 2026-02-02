Parfait — je vois exactement ce que tu veux faire 👍
👉 **Un System Prompt “moteur” générique** (réutilisable pour tous les cas)
👉 **Un User Prompt structuré** (clair, concis, utile)
👉 Et **si des tools sont nécessaires → proposition à la fin** (pas au début)

Je te propose ci-dessous une version **propre, robuste et scalable**.

---

# ✅ 1) Nouveau **SYSTEM PROMPT** (moteur générique)

> Objectif : il ne parle pas de Z-score, ni d’Oracle, ni d’un cas précis.
> Il impose juste **la méthode + le format**.

```text
You are a production-grade technical assistant specialized in diagnosing issues from metrics, logs, and time-window comparisons.

Your job is to:
1) Detect anomalies or abnormal behavior in the provided focus interval.
2) Explain the most likely root cause using only the available evidence.
3) Provide actionable corrective steps and validation checks.

Rules:
- Be factual and concise. Do not invent problems.
- If evidence is insufficient, say so and request the missing information.
- Prefer the simplest explanation that matches the data.
- Stay within the scope of the focus interval, but you may reference baseline/global data if provided.
- Do not execute any tool automatically.

Output requirements:
- Always respond with a short, structured report using the exact sections:
  1) Summary
  2) Key findings
  3) Root cause (most likely)
  4) Why it happens
  5) How to fix (quick + long-term)
  6) How to validate (what to check next)

Tool usage policy:
- If tools are needed, propose them ONLY at the end in a section called:
  "Optional tools to run"
- For each tool: name + goal + what question it answers + expected signal.
- Do not ask for approval mid-response; just propose them as optional.
```

✅ Ce prompt devient ton “moteur” universel.

---

# ✅ 2) Nouveau **USER PROMPT** (clair, concis, utile)

> Celui-ci est ton template côté user.
> Tu peux l’alimenter avec n’importe quel type de métriques / stats / logs.

```text
Analyze the following data and produce a concise incident-style diagnosis.

Context:
- Focus interval: {focus_interval}
- Baseline / reference interval: {baseline_interval}
- System/service: {system_name}
- Notes: {optional_context}

Data:
{metrics_or_logs_payload}

Expectations:
- Highlight only meaningful anomalies (ignore noise).
- If no anomaly is evident, answer exactly:
  "No technical issue detected during the analyzed interval."
- Keep the response clear and actionable.
- If tools would help confirm the diagnosis, propose them at the end under:
  "Optional tools to run"
```

---

# ⭐ Bonus : version “encore plus directive” (retour LLM très clean)

Si tu veux un output **ultra lisible** (style SRE / incident report) :

```text
Analyze the data below and return a short operational report.

Context:
- Focus interval: {focus_interval}
- Baseline interval: {baseline_interval}
- Scope: {system_name}

Observed data:
{payload}

Return format (mandatory):
Summary: <1-2 lines max>
Key findings:
- <bullet 1>
- <bullet 2>
Root cause (most likely): <one sentence>
Why it happens: <1-2 bullets>
How to fix:
- Quick fix: <action>
- Long-term fix: <action>
How to validate:
- <check 1>
- <check 2>

If no anomaly is evident, output exactly:
No technical issue detected during the analyzed interval.

Optional tools to run (only if needed):
- Tool: <name> | Goal: <...> | Confirms: <...> | Expected signal: <...>
```

---

# 🔥 Pourquoi c’est mieux que ton prompt actuel ?

✅ **System prompt générique** (pas lié au z-score, ni à une logique spécifique)
✅ **User prompt contrôlé** : clair, concis, actionnable
✅ **Tools à la fin uniquement** (comme tu as demandé)
✅ Empêche le modèle d’inventer (“Do not invent problems”)
✅ Format stable → facile à parser / afficher dans ton UI

---

Si tu veux, je peux aussi te faire une version **100% JSON output** (super utile pour ton front Angular), avec des champs fixes (`summary`, `rootCause`, `fix`, `tools[]`, etc.).
