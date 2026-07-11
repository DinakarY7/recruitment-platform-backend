# CareerHive - Recruitment Platform (Backend)

CareerHive is a production-level, optimized job recruitment platform. This is the FastAPI backend service of the application.

## 🏗️ Tech Stack
- **FastAPI Async Stack**: The backend utilizes `asyncpg` and SQLAlchemy's asynchronous extensions for non-blocking I/O.
- **SQLModel Core**: Model schemas serve dual purposes as database tables and Pydantic validation schemas, reducing code duplication.
- **CockroachDB Serverless**: Highly available, distributed PostgreSQL-compatible database.

## 🚀 Local Development Setup

### Prerequisite Tools
- Python 3.12+
- CockroachDB (Local or Cloud Serverless)

### Step-by-Step Installation

1. Navigate to the backend directory:
   ```bash
   cd backend
   ```

2. Create and activate the Python virtual environment:
   ```bash
   # Windows PowerShell
   python -m venv venv
   .\venv\Scripts\Activate.ps1

   # macOS/Linux
   python3 -m venv venv
   source venv/bin/activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Configure your `.env` file (create one in the root of the backend folder):
   ```env
   DATABASE_URL=postgresql+asyncpg://<USER>:<PASSWORD>@<HOST>:<PORT>/defaultdb?sslmode=verify-full
   SECRET_KEY=your-jwt-secret-key
   ALGORITHM=HS256
   ACCESS_TOKEN_EXPIRE_MINUTES=60
   ```

5. Run database initialization script (if any):
   ```bash
   python create_db.py
   ```

6. Start the FastAPI server:
   ```bash
   uvicorn app.main:app --reload
   ```

The Swagger interactive documentation will be available at [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs).

## 🔧 Production Hosting Guide (Render)
1. Sign in to [Render](https://render.com).
2. Click **New +** -> **Web Service**.
3. Connect your backend GitHub repository.
4. Specify settings:
    - **Runtime**: `Python`
    - **Build Command**: `pip install -r requirements.txt`
    - **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
5. Add **Environment Variables** matching your `.env` parameters (e.g. `DATABASE_URL`, `SECRET_KEY`).
