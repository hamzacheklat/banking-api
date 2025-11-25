/* -------- TABLEAUX AWR AVEC BORDURES INTERNES -------- */

.markdown-container table {
  width: 100%;
  border-collapse: collapse; /* essentiel pour bordures internes fines */
  margin: 15px 0 25px 0;
  background: white;
  border: 1px solid #bfcde4; /* bordure externe */
}

.markdown-container th,
.markdown-container td {
  padding: 7px 9px;
  border: 1px solid #c9c9c9; /* bordures internes visibles */
}

.markdown-container th {
  background: #e8eef7; /* bleu clair Oracle */
  color: #003f82;
  font-weight: 600;
  text-align: left;
}

.markdown-container tr:nth-child(even) {
  background: #f5f5f5; /* gris léger pour alternance */
}
