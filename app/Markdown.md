Of course 👍 here’s the same documentation, formatted in **clean Markdown** — perfect for GitHub, API docs, or Confluence pages that support Markdown rendering.
All sections are concise, structured, and fully in English.

---

# 🧭 API Product Action Available

**Version 1.0 — October 2025**

## 1. Context

These endpoints are used to **open or close product actions** based on different criteria:

* **Environment:** `dev`, `stg`, `prd`
* **Region:** `emea`, `amer`, `apac`
* **Ecosystem:** `database`, `iv2producers`, etc.

They allow dynamic control of a product’s operational availability (e.g., `create`, `delete`, etc.) for a specific scope.

---

## 2. Main Attributes

| Field                 | Example                       | Description                     |
| --------------------- | ----------------------------- | ------------------------------- |
| `status`              | `open` / `close`              | Current state of the action     |
| `env`                 | `prd`                         | Target environment              |
| `region`              | `emea`                        | Target region                   |
| `ecosystem_exception` | `["database","iv2producers"]` | Ecosystem exceptions (optional) |

---

## 3. Endpoints

| Method     | URL                                                           | Description                                      | Example                                                    |
| ---------- | ------------------------------------------------------------- | ------------------------------------------------ | ---------------------------------------------------------- |
| **GET**    | `/product_action`                                             | List or filter product actions                   | `?product_name=oracle_cluster&status=open&env=prd`         |
| **POST**   | `/product_action`                                             | Create a new product action                      | See note below                                             |
| **PATCH**  | `/product_action/<product_name>/<status>`                     | Open or close an action                          | `/product_action/oracle_cluster/open`                      |
| **PATCH**  | `/product_action/<product_name>/ecosystem_exception/<status>` | Manage ecosystem exceptions                      | `/product_action/oracle_cluster/ecosystem_exception/close` |
| **DELETE** | `/product_action/<product_name>`                              | Delete one or more actions                       | `/product_action/oracle_cluster`                           |
| **PATCH**  | `/product_action/<product_name>/api_access`                   | ⚠️ *Inactive – will be replaced by alert system* | -                                                          |

> **Note:**
> The `/api_access` endpoint is currently inactive.
> On the *robotic* side, API and marketplace requests cannot yet be differentiated.

---

## 4. Usage Scenarios

### 🔹 Open an action for a specific environment / region

```json
PATCH /product_action/oracle_cluster/open
{
  "action_name": "create",
  "env": "prd",
  "region": "emea",
  "reason": "maintenance completed"
}
```

➡ The `create` action is set to **open** for product `oracle_cluster` in **prd / emea**.

---

### 🔹 Close all actions of a product

```json
PATCH /product_action/oracle_cluster/close
{
  "reason": "planned maintenance"
}
```

➡ All actions for product `oracle_cluster` are set to **close**.

---

### 🔹 List only open actions in production

```bash
GET /product_action?product_name=oracle_cluster&status=open&env=prd
```

➡ Returns all **open** actions for `oracle_cluster` in the **prd** environment.

---

## 5. Automatic Creation & CLI Option

When creating a **new product** or a **new action**, there are two options:

### Option 1 — Using the API

```json
POST /product_action
{
  "product_name": "oracle_cluster",
  "action_name": "create"
}
```

### Option 2 — Using the internal CLI

```bash
python manage_actions.py create_all
```

➡ In both cases, the system automatically creates all combinations for:

* **3 environments:** `dev`, `stg`, `prd`
* **3 regions:** `emea`, `amer`, `apac`

This ensures every product has all related actions initialized across every environment and region.

---

Would you like me to add a **short “Best Practices”** section (e.g., include a `reason`, avoid direct production changes, validate filters) to append to the end?
