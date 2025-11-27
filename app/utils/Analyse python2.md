Parfait ! On va ajouter une **visualisation graphique des tendances AWR** dans le frontend Angular avec `ng2-charts`. On affichera **SQL, Wait Events et Sessions problématiques par intervalle horaire**.

---

# **1️⃣ Installer ng2-charts**

Dans ton projet Angular :

```bash
npm install chart.js ng2-charts
```

---

# **2️⃣ Mettre à jour `app.module.ts`**

```typescript
import { NgModule } from '@angular/core';
import { BrowserModule } from '@angular/platform-browser';
import { FormsModule } from '@angular/forms';
import { HttpClientModule } from '@angular/common/http';
import { NgChartsModule } from 'ng2-charts';

import { AppComponent } from './app.component';
import { ReportComponent } from './components/report/report.component';

@NgModule({
  declarations: [
    AppComponent,
    ReportComponent
  ],
  imports: [
    BrowserModule,
    FormsModule,
    HttpClientModule,
    NgChartsModule
  ],
  providers: [],
  bootstrap: [AppComponent]
})
export class AppModule { }
```

---

# **3️⃣ Mettre à jour `report.component.ts`**

On va préparer les données pour les graphiques par catégorie (SQL, Waits, Sessions) :

```typescript
import { Component } from '@angular/core';
import { AwrService } from '../../services/awr.service';
import { ChartConfiguration, ChartOptions } from 'chart.js';

@Component({
  selector: 'app-report',
  templateUrl: './report.component.html',
  styleUrls: ['./report.component.css']
})
export class ReportComponent {
  dbid = 1;
  inst = 1;
  focusStart = '';
  focusEnd = '';
  globalStart = '';
  globalEnd = '';
  reports: any[] = [];

  // Chart data
  sqlChartData: ChartConfiguration<'bar'>['data'] = { labels: [], datasets: [] };
  waitChartData: ChartConfiguration<'bar'>['data'] = { labels: [], datasets: [] };
  sessionChartData: ChartConfiguration<'bar'>['data'] = { labels: [], datasets: [] };
  chartOptions: ChartOptions<'bar'> = { responsive: true };

  constructor(private awrService: AwrService) {}

  fetchReport() {
    const params = {
      dbid: this.dbid,
      inst: this.inst,
      focus_start: this.focusStart,
      focus_end: this.focusEnd,
      global_start: this.globalStart,
      global_end: this.globalEnd
    };
    this.awrService.getHourlyReport(params).subscribe(res => {
      this.reports = res;
      this.updateCharts();
    });
  }

  updateCharts() {
    const hours = this.reports.map(r => new Date(r.interval_start).getHours() + 'h');

    // SQL Chart
    const sqlKeys = Array.from(new Set(this.reports.flatMap(r => r.report.problematic_sql.map(s => s.key))));
    const sqlDatasets = sqlKeys.map(key => ({
      label: key,
      data: this.reports.map(r => {
        const item = r.report.problematic_sql.find(s => s.key === key);
        return item ? item.delta_percent : 0;
      }),
      backgroundColor: `#${Math.floor(Math.random()*16777215).toString(16)}`
    }));
    this.sqlChartData = { labels: hours, datasets: sqlDatasets };

    // Wait Chart
    const waitKeys = Array.from(new Set(this.reports.flatMap(r => r.report.problematic_waits.map(w => w.key))));
    const waitDatasets = waitKeys.map(key => ({
      label: key,
      data: this.reports.map(r => {
        const item = r.report.problematic_waits.find(w => w.key === key);
        return item ? item.delta_percent : 0;
      }),
      backgroundColor: `#${Math.floor(Math.random()*16777215).toString(16)}`
    }));
    this.waitChartData = { labels: hours, datasets: waitDatasets };

    // Session Chart
    const sessionKeys = Array.from(new Set(this.reports.flatMap(r => r.report.problematic_sessions.map(s => s.key))));
    const sessionDatasets = sessionKeys.map(key => ({
      label: key,
      data: this.reports.map(r => {
        const item = r.report.problematic_sessions.find(s => s.key === key);
        return item ? item.delta_percent : 0;
      }),
      backgroundColor: `#${Math.floor(Math.random()*16777215).toString(16)}`
    }));
    this.sessionChartData = { labels: hours, datasets: sessionDatasets };
  }
}
```

---

# **4️⃣ Mettre à jour `report.component.html`**

On ajoute les graphiques avec `<canvas baseChart>` :

```html
<div>
  <h1>Oracle AWR Analyzer</h1>

  <div>
    <label>DBID: <input [(ngModel)]="dbid" type="number" /></label>
    <label>Instance: <input [(ngModel)]="inst" type="number" /></label>
    <label>Focus Start: <input [(ngModel)]="focusStart" type="datetime-local" /></label>
    <label>Focus End: <input [(ngModel)]="focusEnd" type="datetime-local" /></label>
    <label>Global Start: <input [(ngModel)]="globalStart" type="datetime-local" /></label>
    <label>Global End: <input [(ngModel)]="globalEnd" type="datetime-local" /></label>
    <button (click)="fetchReport()">Charger le rapport</button>
  </div>

  <h2>SQL problématiques</h2>
  <canvas baseChart
          [data]="sqlChartData"
          [options]="chartOptions"
          chartType="bar">
  </canvas>

  <h2>Wait Events problématiques</h2>
  <canvas baseChart
          [data]="waitChartData"
          [options]="chartOptions"
          chartType="bar">
  </canvas>

  <h2>Sessions problématiques</h2>
  <canvas baseChart
          [data]="sessionChartData"
          [options]="chartOptions"
          chartType="bar">
  </canvas>
</div>
```

---

# ✅ Résultat

* Chaque intervalle horaire est comparé avec la période globale
* Les **top 3 SQL / Wait / Sessions problématiques** sont visualisés en **graphes par heure**
* Permet de voir les **tendances** et détecter les anomalies

---

Si tu veux, je peux te fournir **une version CSS améliorée pour rendre les graphiques plus lisibles et colorés** pour un vrai tableau de bord DBA.

Veux‑tu que je fasse ça ?
