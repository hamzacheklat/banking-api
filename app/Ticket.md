Bien vu 👌 Tu veux une **description de ticket en anglais** (style Jira/GitLab) et un **message de commit clair**.

---

## 🔹 Ticket description (English)

**Title:** Implement product action availability table and CRUD API with Sanic

**Description:**
We need to create a new table `product_action_available` in the Oracle database to manage product actions and their availability.
Each product can have multiple actions (e.g., "buy", "sell", "download"), and each action can be either **open** or **close**.

The table must store:

* `product_name` (VARCHAR2(255), part of PK)
* `action_name` (VARCHAR2(100), part of PK)
* `status` (VARCHAR2(10), "open" or "close")
* `updated_by` (VARCHAR2(100))
* `updated_at` (TIMESTAMP, default `SYSDATE`)

We also need to expose a Sanic REST API to manage product actions:

**Endpoints:**

* `GET /products` → List all products and actions
* `GET /products/<product_name>` → List all actions for a product
* `GET /products/<product_name>?status=open|close` → Filter actions by status
* `GET /products/<product_name>/actions/<action_name>` → Get a specific action
* `POST /products/<product_name>/actions` → Add a new action to a product
* `PATCH /products/<product_name>/actions/<action_name>` → Update action status
* `PATCH /products/<product_name>/close` → Close all actions of a product
* `PATCH /products/<product_name>/open` → Open all actions of a product
* `DELETE /products/<product_name>/actions/<action_name>` → Delete a product action

**Acceptance criteria:**

* The table is created in Oracle DB.
* The API provides full CRUD functionality.
* A product can have multiple actions, each with its own status.
* It is possible to open/close a single action or all actions of a product.

---

## 🔹 Commit message (English)

```
feat(api): add product_action_available table and CRUD endpoints with Sanic

- Created Oracle table product_action_available with composite PK (product_name, action_name)
- Implemented service layer for managing product actions
- Added Sanic REST API endpoints:
  * GET /products
  * GET /products/<product_name>
  * GET /products/<product_name>?status=open|close
  * GET /products/<product_name>/actions/<action_name>
  * POST /products/<product_name>/actions
  * PATCH /products/<product_name>/actions/<action_name>
  * PATCH /products/<product_name>/close
  * PATCH /products/<product_name>/open
  * DELETE /products/<product_name>/actions/<action_name>
- Enabled filtering actions by status (open/close)
- Added support for updating status for a single action or all actions of a product
```

---

👉 Veux-tu que je t’écrive aussi un **exemple de test (unit test)** en Sanic pour valider ces endpoints automatiquement ?
