Parfait — je vais te générer un **thème complet Oracle AWR**, fidèle au style utilisé dans les rapports Oracle (AWR, ASH, ADDM) :

* 📘 Couleurs bleu-Oracle
* 📊 Tableaux avec bordures fines et alternance gris clair
* 🟦 Titres encadrés façon sections AWR
* 🧱 Code / pre formatés style rapport Oracle
* ✨ Style *propre, lisible, très “Oracle DBA”*

Voici le **CSS Oracle AWR complet**, prêt à coller dans ton `chat.component.css` ou `app.component.css`.

---

# 🎨 **CSS complet — Thème Oracle AWR**

```css
/* ================================
   ORACLE AWR STYLE MARKDOWN
   ================================ */

.markdown-container {
  padding: 20px;
  background: #fafafa;
  color: #222;
  font-family: "Segoe UI", Arial, sans-serif;
  line-height: 1.55;
  font-size: 14px;
  border: 1px solid #d4d4d4;
  border-radius: 6px;
}

/* -------- TITRES -------- */

.markdown-container h1,
.markdown-container h2,
.markdown-container h3 {
  margin-top: 25px;
  margin-bottom: 10px;
  font-weight: 600;
  padding-bottom: 4px;
  border-bottom: 2px solid #0057b8; /* bleu Oracle */
  color: #003f82;
}

.markdown-container h1 { font-size: 1.9rem; }
.markdown-container h2 { font-size: 1.55rem; }
.markdown-container h3 { font-size: 1.25rem; }

/* Petit label type AWR */
.markdown-container .section-label {
  font-size: 12px;
  color: #666;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

/* -------- PARAGRAPHES -------- */
.markdown-container p {
  margin-bottom: 12px;
  color: #333;
}

/* -------- LIENS -------- */
.markdown-container a {
  color: #0057b8;
  font-weight: 600;
  text-decoration: none;
}
.markdown-container a:hover {
  text-decoration: underline;
}

/* -------- LISTES -------- */
.markdown-container li {
  margin-bottom: 5px;
}

/* -------- TABLEAUX AWR -------- */

.markdown-container table {
  width: 100%;
  border-collapse: collapse;
  margin: 15px 0 25px 0;
  background: white;
}

.markdown-container th {
  background: #e8eef7; /* bleu clair Oracle */
  color: #003f82;
  padding: 8px;
  font-weight: 600;
  border: 1px solid #bfcde4;
  text-align: left;
}

.markdown-container td {
  padding: 7px;
  border: 1px solid #d3d3d3;
}

.markdown-container tr:nth-child(even) {
  background: #f7f7f7;
}

/* -------- CODE INLINE -------- */

.markdown-container code {
  background: #f0f0f0;
  color: #b30000; /* rouge Oracle pour SQL */
  padding: 2px 5px;
  border-radius: 4px;
  font-family: Consolas, monospace;
  font-size: 13px;
}

/* -------- BLOCS DE CODE -------- */

.markdown-container pre {
  background: #f3f3f3;
  border: 1px solid #dcdcdc;
  padding: 12px;
  border-radius: 6px;
  white-space: pre-wrap;
  font-family: Consolas, monospace;
  color: #333;
}

/* -------- BLOCKQUOTE -------- */

.markdown-container blockquote {
  margin: 15px 0;
  padding: 10px 15px;
  border-left: 4px solid #0057b8;
  background: #eef3fb;
  color: #333;
}

/* -------- TITRE "AWR REPORT SECTION" -------- */

.markdown-container .awr-section {
  background: #003f82;
  color: white;
  padding: 6px 10px;
  margin-top: 30px;
  margin-bottom: 15px;
  font-weight: bold;
  font-size: 14px;
  letter-spacing: 0.5px;
  border-radius: 4px;
}
```

---

# 📌 Exemple d’utilisation dans ton HTML

```html
<div class="markdown-container">
  <markdown [data]="analysisResult.advisor_report"></markdown>
</div>
```

---

# 🔥 Tu veux que j’ajoute en plus :

* style **AWR "Top WAITS"** avec couleurs rouge/orange selon le % ?
* style spécial pour **SQL IDs** ?
* tableaux avec **alignement numérique Oracle** ?
* thèmes clair + sombre auto-switch ?

Je peux te générer aussi la **version DARK Oracle AWR**, très utilisée par les DBA.
