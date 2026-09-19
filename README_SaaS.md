# Zuxuru Digital Name Investigator - Multi-Tenant SaaS Platform

## 🚀 Overview
A full-featured web application for investigating digital name availability across domains and social media platforms. Supports multiple tenants with subscription packages.

## ✨ Features
- **Multi-Tenant Architecture**: Separate user accounts with isolated data
- **Subscription Packages**: Free, Starter ($9/mo), Pro ($29/mo), Enterprise ($99/mo)
- **Credit System**: Each investigation consumes 1 credit
- **Domain Checking**: 8 TLDs (.com, .net, .org, .io, .co, .ai, .tech, .app)
- **Social Media Checking**: 7 platforms (Twitter, Instagram, Facebook, LinkedIn, GitHub, TikTok, YouTube)
- **JWT Authentication**: Secure user sessions
- **Web Dashboard**: Beautiful responsive UI
- **API Access**: RESTful endpoints for integration

## 📦 Installation

```bash
# Install dependencies
pip install fastapi uvicorn sqlalchemy python-jose passlib bcrypt httpx jinja2 python-multipart

# Run the server
python3 app.py
```

## 🌐 Access
- **Web Interface**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs

## 🔑 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/register` | Register new user |
| POST | `/token` | Login (OAuth2) |
| GET | `/me` | Get current user info |
| POST | `/investigate?name={name}` | Run name investigation |
| GET | `/packages` | View subscription packages |

## 📊 Package Tiers

| Package | Price | Credits/Month | Features |
|---------|-------|---------------|----------|
| Free | $0 | 5 | Basic checks |
| Starter | $9 | 25 | Priority checks, Email support |
| Pro | $29 | 100 | All checks, Priority support, API access |
| Enterprise | $99 | 1000 | Unlimited checks, Dedicated support |

## 🧪 Testing

```bash
# Register a user
curl -X POST http://localhost:8000/register \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"secure123"}'

# Login
curl -X POST http://localhost:8000/token \
  -d "username=user@example.com&password=secure123"

# Run investigation
curl -X POST "http://localhost:8000/investigate?name=YourBrand" \
  -H "Authorization: Bearer YOUR_TOKEN"

# Check credits
curl http://localhost:8000/me \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## 🗄️ Database
SQLite database (`zuxuru.db`) stores:
- User accounts with hashed passwords
- Subscription packages
- Credit balances
- Investigation history

## 🔐 Security
- Password hashing with bcrypt
- JWT token authentication
- Session management
- CORS protection ready

## 🏗️ Architecture
- **Backend**: FastAPI (Python)
- **Database**: SQLAlchemy ORM + SQLite
- **Frontend**: Vanilla JS + HTML/CSS
- **Auth**: OAuth2 with JWT
- **Templates**: Jinja2

## 📝 Notes
- Default admin secret key should be changed in production
- Social media checks use simulation (integrate real APIs for production)
- Domain checks use simulation (integrate domain API for production)
- For multi-tenant production: use PostgreSQL, add Stripe for payments
