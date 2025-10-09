Excellent, là tu clarifies parfaitement le contexte 👏

👉 Donc :

* Les **actions (`Start`, `Stop`, `Force Stop`) ne sont pas dans la grille**,
* Elles sont **en dehors** (par ex. des boutons globaux ou dans une toolbar),
* Et ces actions doivent s’appliquer **à la ligne sélectionnée** (ou à plusieurs lignes),
* Mais selon **l’état du `replicat` ou de l’`extract`** dans la table.

Autrement dit :
🧩 **La grille affiche l’état** (et peut-être une sélection ou un toggle visuel),
🧠 **Les boutons extérieurs déclenchent l’action** sur les lignes concernées.

C’est un pattern très courant dans les consoles d’administration (par ex. Oracle GoldenGate, Kafka Connect, etc.).

---

## ⚙️ Ton cas d’usage résumé

| Élément                | Rôle                                                                                  |
| ---------------------- | ------------------------------------------------------------------------------------- |
| AG Grid                | Affiche les serveurs et leurs statuts (extract / replicat)                            |
| Checkbox ou indicateur | Permet de “sélectionner” un extract ou un replicat spécifique                         |
| Boutons externes       | `Start`, `Stop`, `Force Stop` — déclenchent des actions sur les éléments sélectionnés |

---

## ✅ Solution propre : gestion de la sélection interne (sans `checkboxSelection` global)

Tu veux **deux sélections indépendantes** par ligne :

* une pour `Extract`,
* une pour `Replicat`.

### 💡 Donc :

→ Tu **gardes tes deux colonnes “Extract” et “Replicat”**,
→ Chacune a **son propre bouton de sélection (ou checkbox)**,
→ Tu **écoutes ces sélections** depuis AG Grid,
→ Tes **boutons globaux** agissent selon ces sélections.

---

## 🧩 Exemple clair

### 🔹 1. `rowData`

```ts
rowData = [
  {
    name: 'Server 1',
    extract: { status: 'RUNNING', selected: false },
    replicat: { status: 'STOPPED', selected: false },
  },
  {
    name: 'Server 2',
    extract: { status: 'STOPPED', selected: false },
    replicat: { status: 'RUNNING', selected: false },
  },
];
```

---

### 🔹 2. `columnDefs`

```ts
columnDefs = [
  { headerName: 'Name', field: 'name' },
  {
    headerName: 'Extract',
    field: 'extract',
    cellRenderer: 'statusRenderer',
  },
  {
    headerName: 'Replicat',
    field: 'replicat',
    cellRenderer: 'statusRenderer',
  },
];
```

---

### 🔹 3. `status-renderer.component.html`

```html
<div class="status-cell flex items-center gap-2">
  <!-- ✅ Checkbox pour sélectionner Extract ou Replicat -->
  <input
    type="checkbox"
    [checked]="params.value.selected"
    (change)="onSelect($event)"
  />

  <!-- 🔹 Statut -->
  <span
    [ngClass]="{
      'text-green-600': params.value.status === 'RUNNING',
      'text-red-600': params.value.status === 'STOPPED',
      'text-orange-600': params.value.status === 'ABENDED'
    }"
  >
    {{ params.value.status }}
  </span>
</div>
```

---

### 🔹 4. `status-renderer.component.ts`

```ts
import { Component } from '@angular/core';
import { ICellRendererAngularComp } from 'ag-grid-angular';

@Component({
  selector: 'app-status-renderer',
  templateUrl: './status-renderer.component.html',
})
export class StatusRendererComponent implements ICellRendererAngularComp {
  params: any;

  agInit(params: any): void {
    this.params = params;
  }

  refresh(): boolean {
    return false;
  }

  onSelect(event: Event) {
    const checked = (event.target as HTMLInputElement).checked;
    this.params.value.selected = checked;

    // ✅ On notifie la grille d'un changement de sélection
    this.params.api.dispatchEvent({
      type: 'customSelectionChanged',
      data: this.params.data,
    });
  }
}
```

---

### 🔹 5. Boutons extérieurs (dans ton `app.component.html`)

```html
<div class="toolbar">
  <button (click)="onStart()" class="btn btn-success">Start</button>
  <button (click)="onStop()" class="btn btn-warning">Stop</button>
  <button (click)="onForceStop()" class="btn btn-danger">Force Stop</button>
</div>

<ag-grid-angular
  class="ag-theme-alpine"
  style="width: 700px; height: 300px;"
  [rowData]="rowData"
  [columnDefs]="columnDefs"
  (gridReady)="onGridReady($event)"
></ag-grid-angular>
```

---

### 🔹 6. Logique dans `app.component.ts`

```ts
onGridReady(params: any) {
  this.gridApi = params.api;
}

getSelectedItems() {
  const selected: any[] = [];
  this.gridApi.forEachNode((node: any) => {
    if (node.data.extract.selected) {
      selected.push({ type: 'extract', name: node.data.name });
    }
    if (node.data.replicat.selected) {
      selected.push({ type: 'replicat', name: node.data.name });
    }
  });
  return selected;
}

onStart() {
  const items = this.getSelectedItems();
  console.log('🟢 Start sur :', items);
  // ici tu appelles ton service backend pour lancer les jobs
}

onStop() {
  const items = this.getSelectedItems();
  console.log('🟡 Stop sur :', items);
}

onForceStop() {
  const items = this.getSelectedItems();
  console.log('🔴 Force Stop sur :', items);
}
```

---

### ✅ Résultat

* Tu peux cocher les `Extract` et/ou `Replicat` à gérer
* Les boutons extérieurs (`Start`, `Stop`, `Force Stop`)
  agissent uniquement sur ceux sélectionnés
* Tu **n’utilises pas la sélection de ligne AG Grid**
* Tu **gardes ton `StatusRendererComponent`**
* C’est **clairement séparé entre affichage et actions**

---

Souhaites-tu que je te fasse la version **complète et propre** de ce scénario (avec tout le composant Angular + template + TS + exemple d’appel d’action) prête à coller dans ton projet ?
Ce serait la version **“AG Grid + sélections indépendantes + boutons extérieurs”** finale.
