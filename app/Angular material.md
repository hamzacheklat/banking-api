Parfait, j’ai bien compris 👍
👉 Tu veux **supprimer `@ng-bootstrap/ng-bootstrap` (NgbActiveModal)** et utiliser **un autre package**, **plus moderne et standard Angular**.

Je te propose **Angular Material – MatDialog**
✅ stable
✅ maintenu par Google
✅ très utilisé en prod
✅ clean
✅ facile à customiser
✅ sans jQuery / Bootstrap JS

---

# 🧠 Choix du package (RECOMMANDÉ)

## ✅ **Angular Material – `MatDialog`**

👉 Alternative **pro** à `ng-bootstrap modal`
👉 Très utilisée en entreprise (banque, monitoring, outils internes)

---

# 📦 1️⃣ Installation Angular Material

```bash
ng add @angular/material
```

Choisis :

* Theme : **Custom** ou **Indigo/Pink**
* Typography : **Yes**
* Animations : **Yes**

Puis ajoute le module Dialog :

```ts
import { MatDialogModule } from '@angular/material/dialog';

@NgModule({
  imports: [
    MatDialogModule
  ]
})
export class AppModule {}
```

---

# 🧩 2️⃣ Composant Modal (TS) – **SANS Bootstrap**

📄 `addm-popup.component.ts`

```ts
import { Component, Inject } from '@angular/core';
import { MAT_DIALOG_DATA, MatDialogRef } from '@angular/material/dialog';

@Component({
  selector: 'app-addm-popup',
  templateUrl: './addm-popup.component.html',
  styleUrls: ['./addm-popup.component.css']
})
export class AddmPopupComponent {

  constructor(
    public dialogRef: MatDialogRef<AddmPopupComponent>,
    @Inject(MAT_DIALOG_DATA) public data: { report: string }
  ) {}

  close(): void {
    this.dialogRef.close();
  }
}
```

➡️ **Plus de `NgbActiveModal`**
➡️ Data injectée proprement (`MAT_DIALOG_DATA`)

---

# 🧱 3️⃣ HTML – Dialog Angular Material

📄 `addm-popup.component.html`

```html
<div class="addm-modal">

  <div class="modal-header">
    <h2>📊 ADDM Report</h2>

    <button class="close-btn" (click)="close()">✖</button>
  </div>

  <div class="modal-body">
    <div
      class="addm-report"
      [innerHTML]="data.report | addmFormat">
    </div>
  </div>

  <div class="modal-footer">
    <button class="btn-close" (click)="close()">Close</button>
  </div>

</div>
```

---

# 🎨 4️⃣ CSS – **Dialog stylée BLEU PRO**

📄 `addm-popup.component.css`

```css
.addm-modal {
  width: 100%;
  max-width: 900px;
}

/* ================= HEADER ================= */
.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: linear-gradient(135deg, #1e3c72, #2a5298);
  color: #fff;
  padding: 14px 20px;
}

.modal-header h2 {
  font-size: 18px;
  font-weight: 600;
  margin: 0;
}

.close-btn {
  background: none;
  border: none;
  color: #fff;
  font-size: 18px;
  cursor: pointer;
}

/* ================= BODY ================= */
.modal-body {
  background: #f8faff;
  padding: 20px;
  max-height: 65vh;
  overflow-y: auto;
}

/* ================= ADDM ================= */
.addm-report {
  font-family: Consolas, "Courier New", monospace;
  font-size: 13px;
  line-height: 1.6;
  color: #1f2d3d;
}

.section-title {
  font-weight: bold;
  color: #1e3c72;
  margin-top: 16px;
}

.separator {
  border-bottom: 1px dashed #c3d1ec;
  margin-bottom: 10px;
}

.number {
  color: #2a5298;
  font-weight: 600;
}

.row {
  display: flex;
  justify-content: space-between;
  padding: 3px 0;
}

/* ================= FOOTER ================= */
.modal-footer {
  background: #f1f5fb;
  padding: 12px 20px;
  display: flex;
  justify-content: flex-end;
}

.btn-close {
  background: #2a5298;
  color: #fff;
  border: none;
  padding: 6px 18px;
  border-radius: 6px;
  cursor: pointer;
}

.btn-close:hover {
  background: #1e3c72;
}
```

---

# 🧠 5️⃣ Pipe ADDM (IDENTIQUE – PAS TOUCHÉ)

📄 `addm-format.pipe.ts`
👉 **Tu peux garder exactement ton pipe**, il est déjà propre 🔥

---

# 🚀 6️⃣ Ouvrir la modal (depuis n’importe quel composant)

```ts
import { MatDialog } from '@angular/material/dialog';
import { AddmPopupComponent } from './addm-popup/addm-popup.component';

constructor(private dialog: MatDialog) {}

openAddm(report: string): void {
  this.dialog.open(AddmPopupComponent, {
    data: { report },
    width: '900px',
    maxHeight: '80vh',
    panelClass: 'addm-dialog'
  });
}
```

---

# 🎯 Résultat

✅ Plus de `ng-bootstrap`
✅ Modal **100% Angular**
✅ Pro, moderne, maintenable
✅ Parfait pour outils DBA / Monitoring
✅ Compatible Dark Mode / Animations
✅ Niveau **banque / prod**

---

## 🧠 Alternatives possibles (si tu veux comparer)

| Package                          | Avis                 |
| -------------------------------- | -------------------- |
| **Angular Material (MatDialog)** | ⭐⭐⭐⭐⭐ **RECOMMANDÉ** |
| PrimeNG Dialog                   | ⭐⭐⭐⭐                 |
| CDK Overlay (low-level)          | ⭐⭐⭐ (expert only)    |
| Bootstrap pur                    | ❌ JS externe         |

---

Si tu veux, je peux te faire ensuite :

* 🌙 **Dark mode Oracle**
* 📥 **Export PDF**
* 📊 **Graph CPU auto**
* ➖ **Sections repliables**
* 🔍 **Highlight SQL coûteux**

Dis-moi 💪
