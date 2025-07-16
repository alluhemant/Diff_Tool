# 🧾 API Response Comparison Tool

## 🚀 Project Overview

A powerful API comparison tool that:

* Accepts two API URLs (GET or POST)
* Supports JSON and XML response formats
* Compares responses and highlights differences (Unified/Split diff view)
* Stores results in a SQLite database
* Provides a Streamlit dashboard for interactive viewing
* Includes Locust for load testing

## 🧱 Architecture Layers

## Architecture Layers

### 1. Application Layer
- **FastAPI** routes (`app/api/endpoints/compare.py`)
- **Streamlit** dashboard (`ui/dashboard.py`)
- **Error handling** and request validation

### 2. Core Engine
- **Comparison Engine** (`app/core/compare.py`)
- **Response Comparator**
- Async task processing with ThreadPoolExecutor

### 3. Data Layer
- **SQLite** database (`app/data/db.py`)
- **DBHandler** class for all database operations
- LRU caching for frequent queries

### 4. Service Layer
- **HTTP Client** (`app/services/http_client.py`)
- Async API requests with **httpx**
- Retry logic and timeout handling
```
## 🧱 Project Structure

📦 project_root
├── app
│   ├── api
│   │   └── endpoints        ➤ FastAPI route handlers
│   ├── core                 ➤ Response comparison logic
│   ├── data
│   │   └── db.py            ➤ SQLite + SQLAlchemy handler
│   └── config.py            ➤ .env config loader
├── ui
│   └── dashboard.py         ➤ Streamlit dashboard
├── locust.py                ➤ Load test (Locust)
├── main.py                  ➤ FastAPI entry point
```

## 🔧 Setup Instructions

### 1. Clone the repository

```bash
git clone <your-repo-url>
cd project-root
```

### 2. Create a `.env` file

```env
API_BASE_URL=http://localhost:8000
DB_PATH=sqlite:///./comparison.db
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Run FastAPI server

```bash
uvicorn main:app --reload
```

### 5. Launch the Streamlit dashboard

```bash
streamlit run ui/dashboard.py
```

### 6. Run Locust for load testing

```bash
locust -f locust.py --host http://localhost:8000
```

## 🧩 Feature Breakdown

* ✅ Compare two API responses (GET or POST)
* ✅ View Unified/Split diff with highlights
* ✅ Supports JSON and XML formats
* ✅ Shows metrics: length, diff count, normalized flag
* ✅ Save comparisons with content type and timestamps
* ✅ View history and latest results
* ✅ Launch Locust load tests from dashboard

## Technologies Used

* **FastAPI** — REST API backend
* **Streamlit** — Interactive web dashboard
* **SQLite + SQLAlchemy** — Data storage
* **httpx** — Async HTTP client
* **Locust** — Load testing
* **difflib** — Text comparison engine

## 🔍 Key Files

| File                | Description                                             |
| ------------------- | ------------------------------------------------------- |
| `main.py`           | FastAPI application entry point                         |
| `compare.py`        | API routes for comparison and history                   |
| `dashboard.py`      | Streamlit dashboard to interact with comparison results |
| `db.py`             | DB handler for storing & retrieving comparison logs     |
| `compare.py (core)` | Diff logic for JSON, XML, and plain text                |
| `locust.py`         | Load testing simulation script                          |

## ⚠️ Error Handling

* Handles JSON/XML parsing failures
* Shows 502 error if any endpoint returns empty
* Logs and catches all FastAPI exceptions with messages

## 📈 Future Enhancements

* Add auth/token support
* Export results as CSV/Excel
* Add more metrics (latency, status code check)
* CI/CD deployment with Cloud Run or Docker
