Oui, **c’est totalement possible (et même préférable)** d’utiliser **`oracledb`** au lieu de **`cx_Oracle`**.
`oracledb` est la **nouvelle bibliothèque officielle d’Oracle**, 100% compatible avec cx_Oracle mais plus moderne.

Et tu vas pouvoir l'utiliser **en mode Thin (pas besoin d’Oracle Instant Client)** ou **mode Thick** si tu veux.

---

# ✅ Voici exactement ce que tu dois changer dans **TON BACKEND FastAPI**

---

## 1️⃣ Installation

```bash
pip install oracledb
```

Si tu veux le mode thick (Instant Client), tu rajoutes :

```python
import oracledb
oracledb.init_oracle_client(lib_dir="/opt/oracle/instantclient")
```

---

## 2️⃣ Connexion Oracle via `oracledb`

### 🔵 AVANT (cx_Oracle)

```python
import cx_Oracle

conn = cx_Oracle.connect(user, password, dsn)
```

### 🟢 APRÈS (oracledb)

```python
import oracledb

conn = oracledb.connect(user=user, password=password, dsn=dsn)
```

C’est **compatible à 100%**, aucune autre ligne ne change.

---

# ✅ Backend : version complète du fichier `database.py` compatible oracledb

```python
# backend/app/db/database.py

import oracledb

def init_db_client():
    """
    Optional: only if you want thick mode
    """
    try:
        oracledb.init_oracle_client()
    except Exception:
        # Already initialized or using Thin mode (fine)
        pass


def get_connection(user: str, password: str, dsn: str):
    """
    Returns an OracleDB connection using the modern oracledb library.
    """
    conn = oracledb.connect(
        user=user,
        password=password,
        dsn=dsn
    )
    return conn
```

---

# 🟢 Backend : Adapter ton endpoint FastAPI

### AVANT

```python
conn = cx_Oracle.connect(cfg.user, cfg.password, cfg.dsn)
```

### APRÈS

```python
from app.db.database import get_connection

conn = get_connection(cfg.user, cfg.password, cfg.dsn)
```

---

# 🟢 Exemple complet : backend route avec DB credentials

```python
# backend/app/api/routes/awr.py

from fastapi import APIRouter
from pydantic import BaseModel
from app.db.database import get_connection
from app.db.metrics import compute_metrics

router = APIRouter()

class AWRRequest(BaseModel):
    user: str
    password: str
    dsn: str
    start_snap: int
    end_snap: int

@router.post("/awr/compute")
def compute_awr(req: AWRRequest):
    conn = get_connection(req.user, req.password, req.dsn)
    result = compute_metrics(conn, req.start_snap, req.end_snap)
    conn.close()
    return result
```

---

# 🟢 Frontend Angular : formulaire pour user/password/dsn

`src/app/app.component.html`

```html
<div class="container">
  <h2>Analyse AWR Multi-Databases</h2>

  <form (ngSubmit)="runAnalysis()">

    <label>Username</label>
    <input type="text" [(ngModel)]="form.user" name="user" required>

    <label>Password</label>
    <input type="password" [(ngModel)]="form.password" name="password" required>

    <label>DSN</label>
    <input type="text" [(ngModel)]="form.dsn" name="dsn" required>

    <label>Start Snap</label>
    <input type="number" [(ngModel)]="form.start_snap" name="start_snap" required>

    <label>End Snap</label>
    <input type="number" [(ngModel)]="form.end_snap" name="end_snap" required>

    <button type="submit">Analyser</button>
  </form>

  <pre>{{ result | json }}</pre>
</div>
```

---

# 🟢 Front logic Angular : `app.component.ts`

```ts
import { Component } from '@angular/core';
import { HttpClient } from '@angular/common/http';

@Component({
  selector: 'app-root',
  templateUrl: './app.component.html'
})
export class AppComponent {

  form = {
    user: "",
    password: "",
    dsn: "",
    start_snap: 0,
    end_snap: 0
  };

  result: any = null;

  constructor(private http: HttpClient) {}

  runAnalysis() {
    this.http.post("http://localhost:8000/awr/compute", this.form)
      .subscribe(res => {
        this.result = res;
      });
  }
}
```

---

# 🟢 Angular: module (important pour forms)

`app.module.ts`

```ts
import { NgModule } from '@angular/core';
import { BrowserModule } from '@angular/platform-browser';
import { FormsModule } from '@angular/forms';
import { HttpClientModule } from '@angular/common/http';
import { AppComponent } from './app.component';

@NgModule({
  declarations: [AppComponent],
  imports: [BrowserModule, FormsModule, HttpClientModule],
  bootstrap: [AppComponent]
})
export class AppModule {}
```

---

# 🟢 CSS minimal

`styles.css`

```css
.container {
  width: 500px;
  margin: 20px auto;
  font-family: Arial;
}

input, button {
  width: 100%;
  margin-bottom: 10px;
  padding: 6px;
}
```

---

# 🎯 Résultat

Tu as maintenant :

### ✅ Un backend FastAPI complet

* avec `oracledb`
* endpoints pour AWR
* support multi-databases (user/password/dsn envoyés depuis frontend)

### ✅ Un frontend Angular complet

* formulaire de login DB
* sélection des snapshots
* appel API
* affichage JSON

---

# 🌟 Si tu veux, je peux aussi te générer :

✔ Un service Angular séparé (clean architecture)
✔ Une page de login DB dédiée
✔ Sauvegarde des credentials localStorage
✔ Un écran Dashboard avec graphiques (Top SQL, Top Waits, etc.)
✔ Un système multi-environnements (DEV/TEST/PROD)
✔ Une version Docker Compose pour tout déployer

Dis-moi simplement **“Oui je veux tout”** et je te génère **100% du projet complet**.
