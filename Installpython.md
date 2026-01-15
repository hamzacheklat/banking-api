Pour **supprimer une version de Python compilée/installée manuellement** (comme Python 3.14) sur **RHEL 8**, voici la méthode **propre et sûre**, selon la façon dont tu l’as installée.

---

## 🔍 1) Identifier comment Python a été installé

Si tu as suivi la méthode classique :

```bash
./configure --prefix=/usr/local
make altinstall
```

👉 alors **aucun gestionnaire de paquets (dnf)** n’est impliqué.
La suppression est **manuelle**.

Vérifie d’abord où est Python :

```bash
which python3.14
/usr/local/bin/python3.14 --version
```

---

## 🗑️ 2) Supprimer Python 3.14 installé depuis les sources

### A) Supprimer les binaires

```bash
sudo rm -f /usr/local/bin/python3.14
sudo rm -f /usr/local/bin/pip3.14
sudo rm -f /usr/local/bin/idle3.14
sudo rm -f /usr/local/bin/pydoc3.14
```

---

### B) Supprimer les bibliothèques Python

```bash
sudo rm -rf /usr/local/lib/python3.14
```

---

### C) Supprimer les headers (fichiers de dev)

```bash
sudo rm -rf /usr/local/include/python3.14
```

---

### D) Supprimer les pages man

```bash
sudo rm -rf /usr/local/share/man/man1/python3.14.1
```

---

## 🔗 3) Supprimer les liens symboliques (si créés)

Si tu avais fait des liens :

```bash
sudo rm -f /usr/bin/python3.14
sudo rm -f /usr/bin/pip3.14
```

Vérifie :

```bash
ls -l /usr/bin/python*
```

---

## 🧹 4) Nettoyage pip (optionnel)

Supprimer les paquets pip installés pour cette version :

```bash
rm -rf ~/.local/lib/python3.14
```

(Si tu avais utilisé `pip install --user`)

---

## ✅ 5) Vérification finale

```bash
/usr/local/bin/python3.14 --version
which python3.14
```

Si la commande répond **command not found**, la suppression est OK.

---

## ⚠️ IMPORTANT — Ce qu’il ne faut JAMAIS faire

❌ Ne supprime **PAS** :

```bash
/usr/bin/python3
/usr/lib64/python3*
```

👉 Ces fichiers sont utilisés par **dnf** et le système RHEL.

---

## 🧠 Astuce pour la prochaine installation

Pour éviter ce problème à l’avenir :

```bash
./configure --prefix=/usr/local/python-3.14.0
```

Ainsi, pour supprimer :

```bash
sudo rm -rf /usr/local/python-3.14.0
```

---

Si tu veux, dis-moi :

* **où Python est installé** (`which python3.14`)
* ou **l’erreur que tu avais**,
  et je t’aide à nettoyer **sans risque** 💪







__^^^_________


Voici **comment compiler et installer Python 3.14 sur Red Hat Enterprise Linux 8** (RHEL 8) étape par étape. Ces instructions fonctionnent aussi sur ses dérivés (CentOS 8, AlmaLinux 8, Rocky 8, etc.).

---

## 🧠 Préliminaire : versions & paquets

RHEL 8 est livré avec des outils et bibliothèques qui ne sont **pas forcément présents par défaut**. Pour compiler Python, il faut installer les dépendances de compilation, notamment celles pour SSL, bz2, zlib, sqlite, tk, etc.

---

## 1) Installer les *build tools* et dépendances

Ouvre un terminal et exécute :

```bash
sudo dnf groupinstall "Development Tools" -y
sudo dnf install \
    openssl-devel bzip2-devel libffi-devel zlib-devel \
    xz-devel readline-devel sqlite-devel tk-devel \
    gdbm-devel ncurses-devel uuid-devel -y
```

---

## 2) Télécharger Python 3.14

Va sur le site officiel et récupère la dernière archive source (ici *par exemple* 3.14.x) :

```bash
cd /usr/src
sudo curl -O https://www.python.org/ftp/python/3.14.0/Python-3.14.0.tgz
```

*(si une version 3.14.x plus récente existe, remplace l’URL)*

Ensuite :

```bash
sudo tar xf Python-3.14.0.tgz
cd Python-3.14.0
```

---

## 3) Configurer la compilation

Configure Python pour qu’il soit installé dans `/usr/local` (option recommandée pour ne pas écraser le Python système) :

```bash
sudo ./configure --enable-optimizations --with-ssl-default-suites=openssl --prefix=/usr/local
```

**Options importantes :**

* `--enable-optimizations` : active des optimisations (meilleur perf., compile plus long)
* `--with-ssl-default-suites=openssl` : s’assure que ssl fonctionne avec OpenSSL
* `--prefix=/usr/local` : installe Python dans `/usr/local` (sépare du système)

---

## 4) Compiler

Tu peux accélérer avec tous les cœurs du CPU (`-j` avec le nombre de cœurs) :

```bash
sudo make -j$(nproc)
```

---

## 5) Installer

Après compilation :

```bash
sudo make altinstall
```

👉 **Important** :
On utilise `altinstall` (et **pas** `install`) pour éviter d’écraser `/usr/bin/python3` du système.

---

## 6) Vérification

Vérifie la version installée :

```bash
/usr/local/bin/python3.14 --version
/usr/local/bin/pip3.14 --version
```

Tu devrais voir quelque chose comme :

```
Python 3.14.0
pip 23.x.x from ...
```

---

## 7) (Optionnel) Créer des alias

Si tu veux pouvoir appeler simplement `python3.14` :

```bash
sudo ln -s /usr/local/bin/python3.14 /usr/bin/python3.14
sudo ln -s /usr/local/bin/pip3.14 /usr/bin/pip3.14
```

⚠️ N’ajoute **pas** de lien `python3` → `python3.14` si tu comptes garder le Python système intact.

---

## 8) (Optionnel) Virtualenv

Pour isoler tes projets Python :

```bash
/usr/local/bin/python3.14 -m venv ~/monenv
source ~/monenv/bin/activate
pip install --upgrade pip
```

---

## 🛠️ Résolution d’erreurs courantes

### ➤ **Erreur SSL/openssl manquant**

Installe `openssl-devel` (déjà inclus ci-dessus) puis relance `configure`.

---

### ➤ **Module *bz2* ou *sqlite3* manquants**

Assure-toi que `bzip2-devel` et `sqlite-devel` sont installés avant de reconfigurer.

---

## 📌 Notes importantes

* RHEL 8 a un **Python système géré par dnf** ; ne tente pas de remplacer `/usr/bin/python3` → cela peut casser le système.
* En utilisant `/usr/local`, ta version 3.14 coexiste proprement avec la version fournie par Red Hat.

---

Si tu veux, je peux aussi te fournir un **script automatique** pour tout faire en une seule commande.


