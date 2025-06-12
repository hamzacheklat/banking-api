```markdown
# Banking API with Sanic

### Prerequisites
- Python 3.8+

### Installation
```bash
# 1. Clone repository
git clone https://github.com/yourrepo/banking-api.git
cd banking-api

# 2. Setup environment
cp .env.example .env
nano .env # Configure your database credentials

# 3. Install dependencies
python -m pip install -r requirements.txt


# 5. Run application
python server.py
```

## 📚 API Documentation
Interactive Swagger UI available at:
- `http://localhost:8000/docs` when running locally

## 🏗️ Project Structure
```
banking-api/
├── app/
│   ├── api/              # API endpoints
│   ├── core/             # Core configurations
│   ├── models/           # Database models
│   ├── services/         # Business logic layer
│   └── schemas/          # Pydantic schemas
└── server.py             # Application entry point
```

## Running APIs in Debug Mode with PyCharm

To run an API in debug mode using PyCharm, follow these steps:

1. Go to **"Edit Configurations"** in the top-right corner of PyCharm and click **"+" → Python** to create a new configuration.

2. In the **"Script path"** field, point to the `sanic` executable located in your virtual environment, like this:

   ```
   bin/sanic
   ```

3. In the **"Parameters"** field, add the following:

   ```
   --server
   ```

4. In the **"Environment variables"** section, add:

   ```
   Var=1
   ```

5. Set the **"Working directory"** to:

   ```
   /app
   ```

6. Save the configuration.

You can now run the API either in **debug mode** or **normal mode**. Debug mode allows you to place breakpoints and step through your code using:

* **F7**: Step into
* **F8**: Step over
* **F9**: Continue

