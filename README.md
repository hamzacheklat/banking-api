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
