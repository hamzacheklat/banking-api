Excellent — là tu viens de pointer **le vrai nœud du problème** 👀

➡️ Quand tu ouvres ou fermes un **groupe (Group Column)** dans AG Grid, la grille **recrée dynamiquement les colonnes virtuelles**, et donc **les définitions (`colDef`) sont clonées** — ce qui casse les références que tu modifies dynamiquement dans ton `onRowSelected()` (notamment `disableCheckbox`).

En gros, quand tu fais :

```ts
def.cellRendererParams.disableCheckbox = true;
this.gridApi.refreshCells({ force: true, columns: [colId] });
```

ça marche... **jusqu’à ce que tu ouvres ou fermes un groupe** 😅
Parce qu’AG Grid **recrée** cette colonne à partir du modèle initial (`columnDefs`), et donc **ta modification runtime disparaît**.

---

### 🧠 Pourquoi ça casse

AG Grid sépare :

* les **`columnDefs` originales** (ta configuration initiale)
* les **`Column` runtime objects** utilisés pour le rendu.

Quand tu regroupes/dégroupes, AG Grid :

1. reconstruit certaines colonnes (par ex. la group column),
2. recrée les `cellRendererParams` à partir des defs originales.

Donc si tu modifies `def.cellRendererParams` uniquement sur la version en mémoire (dans `columnApi.getColumn()`), ta modif est **perdue** au prochain re-render.

---

### ✅ Solution robuste

➡️ Il faut **synchroniser ta modification** sur les `columnDefs` originales **et** sur la colonne active dans la `columnApi`.

Voici comment faire :

```ts
onRowSelected(event: any): void {
  const colId = (event.node as any).colId;
  if (!colId) return;

  const checked = (event.node as any).checked;
  const column = this.columnApi.getColumn(colId);
  const def = column.getColDef();

  // Trouver la définition d’origine dans columnDefs
  const colDefOriginal = this.gridOptions.columnDefs.find(
    (c: any) => c.colId === colId || c.field === def.field
  );
  if (!colDefOriginal) return;

  // ⚙️ Vérifie si c’est une colonne de groupe
  if (def.cellRenderer === 'agGroupCellRenderer') {
    const params = { ...(def.cellRendererParams || {}) };
    if (!params.innerRendererParams) params.innerRendererParams = {};
    params.innerRendererParams.disableCheckbox = checked;
    def.cellRendererParams = params;
    colDefOriginal.cellRendererParams = params; // ✅ sync avec la source
  } else {
    const params = { ...(def.cellRendererParams || {}) };
    params.disableCheckbox = checked;
    def.cellRendererParams = params;
    colDefOriginal.cellRendererParams = params; // ✅ sync avec la source
  }

  this.gridApi.refreshCells({ force: true, columns: [colId] });
}
```

---

### 🧩 En résumé

| Problème                                            | Cause                      | Solution                                 |
| --------------------------------------------------- | -------------------------- | ---------------------------------------- |
| Le disableCheckbox “saute” après un expand/collapse | AG Grid recrée la colonne  | Met à jour aussi `columnDefs` originales |
| `onRowSelected` ne garde pas l’état                 | Changements runtime perdus | Synchroniser `colDef` et `columnDefs`    |

---

💡 **Option bonus :**
Si tu veux éviter ce genre de recréation trop fréquente, tu peux ajouter :

```ts
gridOptions: {
  suppressColumnVirtualisation: true
}
```

Cela garde toutes les colonnes en mémoire et évite les reconstructions (au prix d’un peu de performance).

---

Souhaites-tu que je t’écrive une version plus complète de `onRowSelected()` qui gère à la fois :

* le cas groupé (`agGroupCellRenderer`)
* la synchro avec `columnDefs`
* et la préservation après `onSeeAll()` ?
