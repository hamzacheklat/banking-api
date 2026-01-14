Perfect — I see the problem now. Thank you for the screenshot.

You are using:

```
sqlalchemy + pymssql + sybase
```

With this URI:

```python
sybase+pymssql://user:password@host:port/dbname
```

---

## ⚠️ This is the root cause

**pymssql is NOT reliably compatible with Sybase ASE.**
It is designed for **Microsoft SQL Server**, not Sybase.

Even if the port is open (which you proved), pymssql often fails with:

• TDS version mismatch
• Login packet mismatch
• Encryption mismatch
• Charset mismatch

Which produces exactly the errors you are seeing:

```
DB-Lib error 20018
DB-Lib error 20002
Adaptive Server connection failed
```

---

## ✅ The correct solution: use ODBC (pyodbc)

Sybase ASE works best with ODBC.

### Step 1 — Install pyodbc

```bash
pip uninstall pymssql
pip install pyodbc
```

---

### Step 2 — Change your SQLAlchemy URI

Replace:

```python
sybase+pymssql://...
```

With:

```python
sybase+pyodbc://user:password@host:port/dbname?driver=Adaptive+Server+Enterprise
```

Or if using FreeTDS:

```python
sybase+pyodbc://user:password@host:port/dbname?driver=FreeTDS
```

---

### Step 3 — If encryption is required (very common in banks)

Try:

```python
sybase+pyodbc://user:password@host:port/dbname?driver=Adaptive+Server+Enterprise&Encrypt=yes&TrustServerCertificate=yes
```

---

## I will generate the exact working config for you

Tell me:

1️⃣ Linux or Windows?
2️⃣ Do you have Sybase client installed?
3️⃣ Does `isql` work?

I will give you:

✅ Exact driver name
✅ Exact URI
✅ SQLAlchemy config
✅ SSL settings
✅ Charset settings

---

## Why pymssql fails here

pymssql uses **FreeTDS internally**, but:

* Wrong default TDS
* No SSL
* Poor Sybase support
* Unmaintained for ASE

In corporate Sybase environments → it breaks.

---

Reply with your OS and I’ll fix everything in one shot.
