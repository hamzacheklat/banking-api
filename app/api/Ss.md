/* ----------- CONTAINER GLOBAL ----------- */
.markdown-container {
  padding: 20px;
  font-size: 15px;
  line-height: 1.6;
  color: #e0e0e0;
  background: #1e1e1e;
}

/* ----------- TITRES (H1, H2, H3...) ----------- */
.markdown-container h1,
.markdown-container h2,
.markdown-container h3,
.markdown-container h4 {
  font-weight: 600;
  margin-top: 25px;
  margin-bottom: 10px;
  color: #4fc3f7; /* bleu clair */
}

.markdown-container h1 { font-size: 1.9rem; }
.markdown-container h2 { font-size: 1.6rem; }
.markdown-container h3 { font-size: 1.3rem; }

/* ----------- PARAGRAPHES ----------- */
.markdown-container p {
  margin-bottom: 14px;
  color: #ddd;
}

/* ----------- LIENS ----------- */
.markdown-container a {
  color: #81d4fa;
  text-decoration: underline;
}

/* ----------- LISTES ----------- */
.markdown-container ul li,
.markdown-container ol li {
  margin-bottom: 6px;
}

/* ----------- CODE INLINE ----------- */
.markdown-container code {
  background: #333;
  color: #ffcc80;
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 0.95em;
}

/* ----------- BLOCS DE CODE ----------- */
.markdown-container pre {
  background: #2b2b2b;
  padding: 12px;
  border-radius: 6px;
  color: #f8f8f2;
  white-space: pre-wrap;
  border: 1px solid #444;
}

/* ----------- TABLEAUX ----------- */
.markdown-container table {
  width: 100%;
  border-collapse: collapse;
  margin: 20px 0;
}

.markdown-container th,
.markdown-container td {
  border: 1px solid #555;
  padding: 10px;
  text-align: left;
}

.markdown-container th {
  background: #37474f;
  color: #fff;
}

.markdown-container tr:nth-child(even) {
  background: #263238;
}

.markdown-container tr:nth-child(odd) {
  background: #2f3b3e;
}

/* ----------- CITATIONS (blockquotes) ----------- */
.markdown-container blockquote {
  border-left: 4px solid #4fc3f7;
  padding: 8px 15px;
  margin: 15px 0;
  background: #263238;
  color: #cfd8dc;
  border-radius: 4px;
}
