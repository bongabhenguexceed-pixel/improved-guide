import os
import httpx
import asyncio
from datetime import datetime, timedelta
from typing import Optional, List
from fastapi import FastAPI, Depends, HTTPException, status, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session, relationship
from passlib.context import CryptContext
from jose import JWTError, jwt
from pydantic import BaseModel

# Configuration
SECRET_KEY = "zuxuru-secret-key-change-in-production"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

DATABASE_URL = "sqlite:///./zuxuru.db"

# Database Setup
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Models
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    package = Column(String, default="free")  # free, starter, pro, enterprise
    credits = Column(Integer, default=5)
    investigations = relationship("Investigation", back_populates="user")

class Investigation(Base):
    __tablename__ = "investigations"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    name = Column(String)
    domains_checked = Column(Text)  # JSON string
    social_checked = Column(Text)   # JSON string
    score = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)
    user = relationship("User", back_populates="investigations")

Base.metadata.create_all(bind=engine)

# Security
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Pydantic Models
class Token(BaseModel):
    access_token: str
    token_type: str

class UserCreate(BaseModel):
    email: str
    password: str

class InvestigationResult(BaseModel):
    name: str
    domain_score: int
    social_score: int
    overall_score: int
    domains: dict
    social: dict
    recommendations: List[str]

# FastAPI App
app = FastAPI(title="Zuxuru Digital Name Investigator")
templates = Jinja2Templates(directory="templates")

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    user = db.query(User).filter(User.email == email).first()
    if user is None:
        raise credentials_exception
    return user

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# Domain & Social Check Functions
async def check_domain(name: str, tld: str) -> bool:
    domain = f"{name}.{tld}"
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"https://api.domain.com/availability?domain={domain}")
            # Simulating check (real implementation would use actual API)
            return True  # Assume available for demo
    except:
        return True

async def check_social(name: str, platform: str) -> bool:
    # Simulating social media handle check
    # In production, use official APIs
    taken_handles = ["zuxuru"]  # Example taken handles
    return name.lower() not in taken_handles

async def investigate_name(name: str) -> dict:
    tlds = ["com", "net", "org", "io", "co", "ai", "tech", "app"]
    platforms = ["twitter", "instagram", "facebook", "linkedin", "github", "tiktok", "youtube"]
    
    domains = {}
    social = {}
    
    # Check domains
    for tld in tlds:
        available = await check_domain(name, tld)
        domains[f"{name}.{tld}"] = available
    
    # Check social
    for platform in platforms:
        available = await check_social(name, platform)
        social[platform] = available
    
    domain_score = sum(1 for v in domains.values() if v) / len(domains) * 100
    social_score = sum(1 for v in social.values() if v) / len(social) * 100
    overall_score = (domain_score + social_score) / 2
    
    recommendations = []
    if domain_score == 100:
        recommendations.append("🎯 Secure all domains immediately - premium TLDs available!")
    if social_score < 50:
        recommendations.append("⚠️ Consider handle variations for social media")
    if overall_score > 70:
        recommendations.append("✅ Strong digital presence potential")
    
    return {
        "domains": domains,
        "social": social,
        "domain_score": int(domain_score),
        "social_score": int(social_score),
        "overall_score": int(overall_score),
        "recommendations": recommendations
    }

# Routes
@app.post("/register")
async def register(user: UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    hashed_pw = get_password_hash(user.password)
    new_user = User(email=user.email, hashed_password=hashed_pw)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return {"message": "User created successfully"}

@app.post("/token", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    access_token = create_access_token(data={"sub": user.email})
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/me")
async def read_users_me(current_user: User = Depends(get_current_user)):
    return {
        "email": current_user.email,
        "package": current_user.package,
        "credits": current_user.credits,
        "created_at": current_user.created_at
    }

@app.post("/investigate", response_model=InvestigationResult)
async def run_investigation(name: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.credits <= 0:
        raise HTTPException(status_code=403, detail="No credits remaining. Upgrade your package.")
    
    result = await investigate_name(name)
    
    # Save investigation
    investigation = Investigation(
        user_id=current_user.id,
        name=name,
        domains_checked=str(result["domains"]),
        social_checked=str(result["social"]),
        score=result["overall_score"]
    )
    db.add(investigation)
    current_user.credits -= 1
    db.commit()
    
    return InvestigationResult(
        name=name,
        **result
    )

@app.get("/packages")
async def get_packages():
    return {
        "free": {"credits": 5, "price": "$0/month", "features": ["Basic checks", "5 credits/month"]},
        "starter": {"credits": 25, "price": "$9/month", "features": ["Priority checks", "25 credits/month", "Email support"]},
        "pro": {"credits": 100, "price": "$29/month", "features": ["All checks", "100 credits/month", "Priority support", "API access"]},
        "enterprise": {"credits": 1000, "price": "$99/month", "features": ["Unlimited checks", "Dedicated support", "Custom integrations"]}
    }

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
