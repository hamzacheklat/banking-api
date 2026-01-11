Parfait 👍
Je te fais **une solution COMPLÈTE, propre et prête à coller**, comme dans une vraie appli pro.

👉 Tu auras :

* ✅ **Modal stylée bleue**
* ✅ **Formatage intelligent du rapport ADDM**
* ✅ **Sections lisibles**
* ✅ **Table “Summary of Findings” bien alignée**
* ✅ **Monospace Oracle**
* ✅ **Scrollable**
* ✅ **Code Angular propre**

---

# 🧩 1️⃣ Composant Angular (TS)

📄 `addm-popup.component.ts`

```ts
import { Component, Input } from '@angular/core';
import { NgbActiveModal } from '@ng-bootstrap/ng-bootstrap';

@Component({
  selector: 'app-addm-popup',
  templateUrl: './addm-popup.component.html',
  styleUrls: ['./addm-popup.component.css']
})
export class AddmPopupComponent {

  @Input() report: string = '';

  constructor(public activeModal: NgbActiveModal) {}
}
```

---

# 🧱 2️⃣ HTML (Modal complète + formatée)

📄 `addm-popup.component.html`

```html
<div class="modal-header">
  <h5 class="modal-title">
    📊 ADDM Report
  </h5>

  <button
    type="button"
    class="close"
    aria-label="Close"
    (click)="activeModal.dismiss()">
    <span aria-hidden="true">&times;</span>
  </button>
</div>

<div class="modal-body">
  <div
    class="addm-report"
    [innerHTML]="report | addmFormat">
  </div>
</div>

<div class="modal-footer">
  <button
    type="button"
    class="btn btn-secondary"
    (click)="activeModal.close()">
    Close
  </button>
</div>
```

---

# 🎨 3️⃣ CSS (Modal + ADDM formatting – BLEU PRO)

📄 `addm-popup.component.css`

```css
/* ===================== */
/* Modal container       */
/* ===================== */
.modal-content {
  border-radius: 10px;
  box-shadow: 0 12px 30px rgba(0, 0, 0, 0.25);
  border: none;
  overflow: hidden;
  background-color: #ffffff;
}

/* ===================== */
/* Header                */
/* ===================== */
.modal-header {
  background: linear-gradient(135deg, #1e3c72, #2a5298);
  color: #ffffff;
  padding: 14px 20px;
  border-bottom: none;
}

.modal-title {
  font-size: 18px;
  font-weight: 600;
}

.modal-header .close {
  color: #ffffff;
  opacity: 0.9;
  font-size: 22px;
}

.modal-header .close:hover {
  opacity: 1;
}

/* ===================== */
/* Body                  */
/* ===================== */
.modal-body {
  padding: 20px;
  max-height: 65vh;
  overflow-y: auto;
  background-color: #f8faff;
}

/* ===================== */
/* ADDM Report           */
/* ===================== */
.addm-report {
  font-family: "Courier New", Consolas, monospace;
  font-size: 13px;
  line-height: 1.65;
  color: #1f2d3d;
}

/* Section titles */
.addm-report .section-title {
  font-weight: bold;
  font-size: 14px;
  color: #1e3c72;
  margin-top: 18px;
}

/* Separator */
.addm-report .separator {
  border-bottom: 1px dashed #c3d1ec;
  margin-bottom: 12px;
}

/* Numbers highlight */
.addm-report .number {
  color: #2a5298;
  font-weight: 600;
}

/* Summary rows */
.addm-report .row {
  display: flex;
  justify-content: space-between;
  padding: 4px 0;
}

.addm-report .row span:first-child {
  flex: 3;
}

.addm-report .row span:last-child {
  flex: 1;
  text-align: right;
  color: #2a5298;
  font-weight: 600;
}

/* ===================== */
/* Footer                */
/* ===================== */
.modal-footer {
  background-color: #f1f5fb;
  border-top: 1px solid #dce3f0;
  padding: 12px 20px;
}

/* ===================== */
/* Buttons               */
/* ===================== */
.btn-secondary {
  background-color: #2a5298;
  border-color: #2a5298;
  color: #ffffff;
  padding: 6px 18px;
  border-radius: 6px;
  font-weight: 500;
}

.btn-secondary:hover {
  background-color: #1e3c72;
  border-color: #1e3c72;
}

/* ===================== */
/* Scrollbar (Chrome)    */
/* ===================== */
.modal-body::-webkit-scrollbar {
  width: 8px;
}

.modal-body::-webkit-scrollbar-thumb {
  background-color: #b4c6e7;
  border-radius: 4px;
}

.modal-body::-webkit-scrollbar-track {
  background-color: #edf2fb;
}
```

---

# 🧠 4️⃣ Pipe Angular – Formatage intelligent ADDM 🔥

📄 `addm-format.pipe.ts`

```ts
import { Pipe, PipeTransform } from '@angular/core';

@Pipe({ name: 'addmFormat' })
export class AddmFormatPipe implements PipeTransform {

  transform(text: string): string {
    if (!text) return '';

    return text

      /* Section titles */
      .replace(
        /^([A-Z][A-Za-z\s]+)\n[-]{3,}/gm,
        `<div class="section-title">$1</div><div class="separator"></div>`
      )

      /* Summary of Findings rows */
      .replace(
        /^(\d+)\s+(.*?)\s+(\d+\.\d+)\s+\|\s+(\d+\.\d+)/gm,
        `
        <div class="row">
          <span>$1. $2</span>
          <span>$3 %</span>
        </div>
        `
      )

      /* Highlight numbers */
      .replace(
        /(\d+\.\d+|\b\d{5,}\b)/g,
        `<span class="number">$1</span>`
      )

      /* Line breaks */
      .replace(/\n/g, '<br>');
  }
}
```

---

# 🧩 5️⃣ Déclaration dans `app.module.ts`

```ts
import { AddmFormatPipe } from './addm-format.pipe';

@NgModule({
  declarations: [
    AddmPopupComponent,
    AddmFormatPipe
  ]
})
export class AppModule {}
```

---

# ✅ Résultat final

✔ Modal **pro, moderne, bleue**
✔ Rapport ADDM **lisible et structuré**
✔ Sections claires
✔ Tableau Summary aligné
✔ Parfait pour **DBA / Oracle / Monitoring**

---

## 🚀 Prochaines améliorations possibles (si tu veux)

* 📥 Export PDF
* 🌙 Dark mode Oracle
* 🔍 Highlight CPU / SQL / SGA / WAIT EVENTS
* ➖ Sections repliables
* 📊 Graph CPU auto

Dis-moi ce que tu veux next, ton outil est déjà niveau **pro prod** 💪
