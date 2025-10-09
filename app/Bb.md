Oui, bien sûr 👍

Ton problème est classique avec **AG Grid + Angular** : quand tu coches une checkbox dans une colonne, l’autre colonne se coche aussi, probablement parce que les deux colonnes partagent la **même propriété (field)** ou le même **binding** dans la `rowData`.

---

### 🔍 Pourquoi ça arrive

AG Grid affiche les données à partir du tableau `rowData`, par exemple :

```ts
this.rowData = [
  { name: 'Alice', col1: true, col2: true },
  { name: 'Bob', col1: false, col2: false }
];
```

Et tu as des colonnes comme :

```ts
this.columnDefs = [
  { headerName: 'Colonne 1', field: 'checked', checkboxSelection: true },
  { headerName: 'Colonne 2', field: 'checked', checkboxSelection: true }
];
```

👉 Ici, **les deux colonnes utilisent le même champ `checked`** — donc quand tu coches une, ça met à jour la même propriété `checked` dans la ligne, ce qui fait que l’autre colonne se coche aussi.

---

### ✅ Solution

Il faut que chaque colonne ait **sa propre propriété** dans les données (`rowData`).

Exemple corrigé :

```ts
this.rowData = [
  { name: 'Alice', col1Checked: true, col2Checked: false },
  { name: 'Bob', col1Checked: false, col2Checked: true }
];
```

Et les colonnes :

```ts
this.columnDefs = [
  { headerName: 'Colonne 1', field: 'col1Checked', cellRenderer: 'agCheckboxCellRenderer' },
  { headerName: 'Colonne 2', field: 'col2Checked', cellRenderer: 'agCheckboxCellRenderer' }
];
```

---

### ⚙️ Autre cas possible

Si tu utilises un **cellRenderer custom** avec une checkbox Angular, par exemple :

```html
<input type="checkbox" [(ngModel)]="params.data.checked">
```

et que tu réutilises `checked` pour les deux colonnes, le même problème apparaîtra.

➡️ Il faut plutôt lier à :

```html
<input type="checkbox" [(ngModel)]="params.data.col1Checked">
```

et dans l’autre colonne :

```html
<input type="checkbox" [(ngModel)]="params.data.col2Checked">
```

---

### 🧩 En résumé

* ✅ Vérifie que chaque colonne a un `field` différent (ex: `col1Checked`, `col2Checked`).
* ❌ Ne pas utiliser la même clé (`checked`) pour plusieurs colonnes.
* 🔁 Si tu utilises un renderer personnalisé, lie chaque colonne à la bonne propriété.

---

Si tu veux, tu peux me montrer ton code des `columnDefs` et ton `rowData`, et je te dirai exactement où corriger — ça ira vite.
Tu veux me le coller ici ?
