# Secure Chat App Backend

A production-ready, secure 1-to-1 communication backend built with FastAPI, PostgreSQL, and Redis.

## 🚀 Features

- **Authentication**: JWT-based auth (Access & Refresh tokens) with password hashing.
- **API Standards**: All responses follow a unified `{status, message, data, errors}` schema.
- **1-to-1 Chat**: Real-time messaging using WebSockets with Redis Pub/Sub for scalability.
- **Presence Tracking**: Real-time online/offline status indicators.
- **Security**: 
  - **End-to-End Encryption (E2EE)**: Server acts as a relay for encrypted blobs.
  - **Encryption at Rest**: Messages are encrypted using a server-side master key before being saved to the database.
- **WebRTC Signaling**: Support for voice and video call signaling (Offer/Answer/ICE Candidates).
- **Admin Dashboard**: Built-in web interface at `/admin` for database exploration.
- **API Documentation**: Automated Swagger UI at `/docs`.

## 🛠 Tech Stack

- **Framework**: [FastAPI](https://fastapi.tiangolo.com/) (Async)
- **Database**: [PostgreSQL](https://www.postgresql.org/) with [SQLAlchemy 2.0](https://www.sqlalchemy.org/)
- **Caching/PubSub**: [Redis](https://redis.io/)
- **Migrations**: [Alembic](https://alembic.sqlalchemy.org/)
- **Security**: [cryptography](https://cryptography.io/), [python-jose](https://python-jose.readthedocs.io/), [bcrypt](https://github.com/pyca/bcrypt)
- **Testing**: [pytest](https://docs.pytest.org/) with `pytest-asyncio`

## ⚙️ Setup

### Prerequisites
- Python 3.9+
- PostgreSQL
- Redis

### Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/krishnaprasad0/Chat-App-1-1.git
   cd Chat-App-1-1
   ```

2. **Create a virtual environment**:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Environment Variables**:
   Create a `.env` file in the root directory (refer to `.env.example`):
   ```env
   DATABASE_URL=postgresql+asyncpg://user:password@localhost/dbname
   REDIS_URL=redis://localhost:6379/0
   SECRET_KEY=your_jwt_secret
   ENCRYPTION_KEY=your_32_byte_base64_key
   ```

5. **Run Migrations**:
   ```bash
   alembic upgrade head
   ```

6. **Start the server**:
   ```bash
   uvicorn app.main:app --reload
   ```

## 📖 API Documentation

- **Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Admin Dashboard**: [http://localhost:8000/admin](http://localhost:8000/admin)

## 🧪 Testing

Run the test suite using pytest:
```bash
PYTHONPATH=. pytest
```

## 📄 License

This project is licensed under the MIT License.
