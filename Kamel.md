
Parfait ! On peut mettre à jour ton frontend Angular 17 pour s’adapter à ce nouveau backend multi-snaps / sections. Je vais te fournir une **version prête à mettre en prod**, avec :

* Formulaire pour sélectionner les snaps Global et Focus (start/end).
* Affichage des **sections avec le résultat LLM** pour chaque section.
* Résumé final consolidé.
* Style simple et propre.

---

## 1️⃣ `app.module.ts`

```ts
import { NgModule } from '@angular/core';
import { BrowserModule } from '@angular/platform-browser';
import { HttpClientModule } from '@angular/common/http';
import { FormsModule, ReactiveFormsModule } from '@angular/forms';

import { AppComponent } from './app.component';

@NgModule({
  declarations: [AppComponent],
  imports: [BrowserModule, HttpClientModule, FormsModule, ReactiveFormsModule],
  providers: [],
  bootstrap: [AppComponent],
})
export class AppModule {}
```

---

## 2️⃣ `app.component.ts`

```ts
import { Component, OnInit } from '@angular/core';
import { FormBuilder, FormGroup } from '@angular/forms';
import { HttpClient } from '@angular/common/http';

interface SectionResult {
  content: string;
  functions_called: any[];
}

interface FinalSummary {
  content: string;
  functions_called: any[];
}

@Component({
  selector: 'app-root',
  templateUrl: './app.component.html',
  styleUrls: ['./app.component.css'],
})
export class AppComponent implements OnInit {
  form: FormGroup;
  sections: string[] = [];
  results: { [key: string]: SectionResult } = {};
  finalSummary: FinalSummary | null = null;
  loading: boolean = false;
  error: string = '';

  constructor(private fb: FormBuilder, private http: HttpClient) {
    this.form = this.fb.group({
      oracle_user: [''],
      oracle_password: [''],
      oracle_dsn: [''],
      global_start_snap: [1],
      global_end_snap: [1],
      focus_start_snap: [1],
      focus_end_snap: [1],
      top_n_sql: [5],
    });

    this.sections = [
      'SQL ordered by Elapsed Time',
      'SQL ordered by CPU Time',
      'SQL ordered by Gets',
      'SQL ordered by Reads',
      'Top Wait Events',
      'Instance Efficiency Stats',
      'IO Stats',
      'System Statistics',
      'Time Model Stats',
      'Advisory Statistics',
      'Latch Activity',
      'Segment Statistics',
      'Memory Statistics'
    ];
  }

  ngOnInit(): void {}

  analyze() {
    this.loading = true;
    this.error = '';
    this.results = {};
    this.finalSummary = null;

    this.http.post<any>('http://localhost:8000/analyze-intervals', this.form.value)
      .subscribe({
        next: (res) => {
          this.results = res.sections || {};
          this.finalSummary = res.final_summary || null;
          this.loading = false;
        },
        error: (err) => {
          this.error = err.message || 'Error';
          this.loading = false;
        }
      });
  }
}
```

---

## 3️⃣ `app.component.html`

```html
<div class="container">
  <h1>Oracle Tuning Advisor</h1>

  <form [formGroup]="form" (ngSubmit)="analyze()">
    <div class="form-group">
      <label>Oracle User</label>
      <input formControlName="oracle_user" class="form-control"/>
    </div>
    <div class="form-group">
      <label>Oracle Password</label>
      <input type="password" formControlName="oracle_password" class="form-control"/>
    </div>
    <div class="form-group">
      <label>Oracle DSN</label>
      <input formControlName="oracle_dsn" class="form-control"/>
    </div>

    <div class="snap-section">
      <h3>Global Interval</h3>
      <label>Start Snap</label>
      <input type="number" formControlName="global_start_snap" class="form-control"/>
      <label>End Snap</label>
      <input type="number" formControlName="global_end_snap" class="form-control"/>
    </div>

    <div class="snap-section">
      <h3>Focus Interval</h3>
      <label>Start Snap</label>
      <input type="number" formControlName="focus_start_snap" class="form-control"/>
      <label>End Snap</label>
      <input type="number" formControlName="focus_end_snap" class="form-control"/>
    </div>

    <div class="form-group">
      <label>Top N SQLs</label>
      <input type="number" formControlName="top_n_sql" class="form-control"/>
    </div>

    <button type="submit" class="btn btn-primary" [disabled]="loading">Analyze</button>
  </form>

  <div *ngIf="loading" class="loading">Running analysis...</div>
  <div *ngIf="error" class="alert alert-danger">{{ error }}</div>

  <div *ngIf="results && !loading">
    <h2>Section Results</h2>
    <div *ngFor="let section of sections">
      <h4>{{ section }}</h4>
      <pre>{{ results[section]?.content }}</pre>
      <details *ngIf="results[section]?.functions_called?.length">
        <summary>Functions Called</summary>
        <pre>{{ results[section]?.functions_called | json }}</pre>
      </details>
    </div>
  </div>

  <div *ngIf="finalSummary">
    <h2>Final Summary</h2>
    <pre>{{ finalSummary.content }}</pre>
    <details *ngIf="finalSummary.functions_called?.length">
      <summary>Functions Called</summary>
      <pre>{{ finalSummary.functions_called | json }}</pre>
    </details>
  </div>
</div>
```

---

## 4️⃣ `app.component.css`

```css
.container {
  max-width: 900px;
  margin: auto;
  padding: 20px;
  font-family: Arial, sans-serif;
}

h1, h2, h3, h4 {
  margin-top: 20px;
}

.form-group {
  margin-bottom: 10px;
}

input.form-control {
  width: 100%;
  padding: 6px;
  margin-bottom: 5px;
}

button.btn {
  margin-top: 10px;
}

.snap-section {
  border: 1px solid #ccc;
  padding: 10px;
  margin-bottom: 15px;
  border-radius: 6px;
  background: #f9f9f9;
}

.loading {
  margin-top: 10px;
  font-weight: bold;
}
```

---

✅ Avec ce frontend :

* Tu peux envoyer les **intervals Global et Focus** avec start/end différents.
* Chaque section est affichée avec le **contenu LLM et les functions called**.
* Le résumé final consolidé est affiché avec les mêmes informations.
* Simple à mettre en production, responsive et clair.

---

Si tu veux, je peux maintenant te fournir **un docker-compose complet backend+frontend+Oracle XE** pour lancer tout ça directement.

Veux‑tu que je fasse ça ?
