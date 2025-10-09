✅ Excellente question — et c’est *exactement* le bon réflexe 👏

Oui 👉 **tu dois ajouter les propriétés `selected` dans ta datasource**,
**soit côté front**, **soit dynamiquement dans le composant Angular**.

---

### 💡 Pourquoi ?

AG Grid affiche seulement ce que contient ton `rowData`.
Si tu veux pouvoir “cocher” un extract ou un replicat **indépendamment**,
il faut un champ pour mémoriser cet état (`selected`).

Sinon, quand tu coches la case, il n’y a nulle part où stocker la valeur.

---

### 🧩 Deux façons possibles :

#### **Option 1 – Modifier ta data source (recommandée)**

Si ta data vient du backend, tu peux juste **ajouter les propriétés côté front avant de la passer à AG Grid**.

Exemple :

```ts
this.rowData = backendData.map(server => ({
  ...server,
  extract: {
    ...server.extract,
    selected: false,   // ajout
  },
  replicat: {
    ...server.replicat,
    selected: false,   // ajout
  },
}));
```

💡 Ainsi, tu ne modifies pas ton API backend, juste la structure utilisée dans la grille.

---

#### **Option 2 – L’ajouter “à la volée” avant de l’afficher**

Si tu ne veux pas toucher à ta donnée d’origine :

```ts
this.rowData = backendData;
this.rowData.forEach(row => {
  if (!row.extract.selected) row.extract.selected = false;
  if (!row.replicat.selected) row.replicat.selected = false;
});
```

---

### 🚀 Recommandation

✔️ **Toujours initialiser** `selected: false` pour `extract` et `replicat`.
C’est plus sûr et plus lisible pour Angular + AG Grid.

Tu pourras ensuite :

* cocher/décocher sans erreur `undefined`,
* parcourir la grille et savoir précisément ce qui a été sélectionné.

---

### 📘 Exemple final de structure conseillée

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

Souhaites-tu que je te montre comment **ajouter dynamiquement le champ `selected`** dans ton code Angular existant, sans toucher à ton backend (ex. si ta data vient d’un service HTTP) ?
