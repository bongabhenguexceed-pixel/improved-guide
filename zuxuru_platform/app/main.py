"""
Zuxuru Investigation Platform
Real business discovery with DataForSEO connector
Multi-tenant architecture with Supabase-ready models
"""

import os
import json
import httpx
import asyncio
from datetime import datetime
from typing import Optional, List, Dict, Any
from fastapi import FastAPI, Depends, HTTPException, status, Request, BackgroundTasks
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime, ForeignKey, Text, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session, relationship

# Configuration
DATABASE_URL = "sqlite:///./zuxuru_platform.db"
DATAFORSEO_LOGIN = os.getenv("DATAFORSEO_LOGIN", "")
DATAFORSEO_PASSWORD = os.getenv("DATAFORSEO_PASSWORD", "")

# Database Setup
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# ==================== DATABASE MODELS ====================

class Workspace(Base):
    """Multi-tenant workspace (Supabase-ready)"""
    __tablename__ = "workspaces"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    businesses = relationship("Business", back_populates="workspace")
    investigations = relationship("InvestigationJob", back_populates="workspace")

class Business(Base):
    """Confirmed business entity"""
    __tablename__ = "businesses"
    id = Column(Integer, primary_key=True, index=True)
    workspace_id = Column(Integer, ForeignKey("workspaces.id"))
    name = Column(String, index=True)
    confirmed = Column(Boolean, default=False)
    website_url = Column(String)
    description = Column(Text)
    title = Column(String)
    headings = Column(Text)  # JSON array of headings
    contact_info = Column(Text)  # JSON object with email, phone, address
    confidence_score = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)
    workspace = relationship("Workspace", back_populates="businesses")
    evidence = relationship("EvidenceCard", back_populates="business")

class InvestigationJob(Base):
    """Investigation job with status tracking"""
    __tablename__ = "investigation_jobs"
    id = Column(Integer, primary_key=True, index=True)
    workspace_id = Column(Integer, ForeignKey("workspaces.id"))
    query = Column(String)
    status = Column(String, default="pending")  # pending, running, completed, failed
    candidate_count = Column(Integer, default=0)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    error_message = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    workspace = relationship("Workspace", back_populates="investigations")
    evidence_cards = relationship("EvidenceCard", back_populates="investigation")

class EvidenceCard(Base):
    """Evidence card with source and confidence"""
    __tablename__ = "evidence_cards"
    id = Column(Integer, primary_key=True, index=True)
    investigation_id = Column(Integer, ForeignKey("investigation_jobs.id"))
    business_id = Column(Integer, ForeignKey("businesses.id"))
    card_type = Column(String)  # search_result, website, contact, social, review
    title = Column(String)
    content = Column(Text)
    source_url = Column(String)
    source_link = Column(String)
    confidence_label = Column(String)  # high, medium, low
    why_here = Column(Text)  # Explanation of why Zuxuru looked here
    card_metadata = Column(Text)  # JSON metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    investigation = relationship("InvestigationJob", back_populates="evidence_cards")
    business = relationship("Business", back_populates="evidence")

Base.metadata.create_all(bind=engine)

# ==================== PYDANTIC MODELS ====================

class InvestigationRequest(BaseModel):
    query: str
    location: Optional[str] = "United States"

class BusinessCandidate(BaseModel):
    name: str
    website: Optional[str] = None
    source: str
    source_url: str
    confidence: float
    why_here: str

class EvidenceCardSchema(BaseModel):
    card_type: str
    title: str
    content: str
    source_url: str
    source_link: str
    confidence_label: str
    why_here: str

class InvestigationStatus(BaseModel):
    job_id: int
    status: str
    candidate_count: int
    candidates: Optional[List[BusinessCandidate]] = None
    evidence: Optional[List[EvidenceCardSchema]] = None

class HealthResponse(BaseModel):
    status: str
    version: str
    dataforseo_connected: bool
    database_connected: bool

# ==================== CONNECTOR ARCHITECTURE ====================

class BaseConnector:
    """Base connector interface"""
    def __init__(self):
        self.connected = False
    
    async def connect(self) -> bool:
        raise NotImplementedError
    
    async def search(self, query: str, location: str) -> List[Dict]:
        raise NotImplementedError
    
    async def fetch_website(self, url: str) -> Dict:
        raise NotImplementedError

class DataForSEOConnector(BaseConnector):
    """Real Google Local & Organic Search via DataForSEO API"""
    
    def __init__(self):
        super().__init__()
        self.base_url = "https://api.dataforseo.com/v3"
        self.auth = (DATAFORSEO_LOGIN, DATAFORSEO_PASSWORD) if DATAFORSEO_LOGIN and DATAFORSEO_PASSWORD else None
    
    async def connect(self) -> bool:
        """Test connection to DataForSEO"""
        if not self.auth or not self.auth[0]:
            self.connected = False
            return False
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                # Test endpoint - get tasks count
                response = await client.get(f"{self.base_url}/keywords_data/google_keywords/task_get", 
                                          auth=self.auth)
                self.connected = response.status_code == 200
                return self.connected
        except Exception as e:
            self.connected = False
            return False
    
    async def search_local(self, query: str, location: str = "United States") -> List[Dict]:
        """Search Google Local/Maps results"""
        if not self.connected:
            return []
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                payload = {
                    "location_name": location,
                    "language_code": "en",
                    "keyword": query,
                    "depth": 10
                }
                
                # Create task for Google Local search
                response = await client.post(
                    f"{self.base_url}/serp/google/local_pack/task_post",
                    json=[payload],
                    auth=self.auth
                )
                
                if response.status_code != 200:
                    return []
                
                task_data = response.json()
                if not task_data or 'tasks' not in task_data:
                    return []
                
                task_id = task_data['tasks'][0]['id']
                
                # Wait and get results
                await asyncio.sleep(5)
                
                result_response = await client.get(
                    f"{self.base_url}/serp/google/local_pack/task_get/{task_id}",
                    auth=self.auth
                )
                
                if result_response.status_code != 200:
                    return []
                
                result_data = result_response.json()
                if not result_data or 'tasks' not in result_data:
                    return []
                
                results = result_data['tasks'][0].get('result', [])
                if not results:
                    return []
                
                # Parse local pack results
                candidates = []
                for item in results[0].get('items', [])[:5]:
                    candidate = {
                        'name': item.get('title', ''),
                        'website': item.get('url', ''),
                        'address': item.get('address', ''),
                        'rating': item.get('rating', {}).get('value', 0),
                        'reviews_count': item.get('rating', {}).get('votes_count', 0),
                        'source': 'Google Local Pack',
                        'source_url': f"https://www.google.com/search?q={query}",
                        'confidence': 0.9 if item.get('url') else 0.7,
                        'why_here': f"Found in Google Local Pack for '{query}' in {location}"
                    }
                    candidates.append(candidate)
                
                return candidates
                
        except Exception as e:
            print(f"DataForSEO Local Search Error: {e}")
            return []
    
    async def search_organic(self, query: str, location: str = "United States") -> List[Dict]:
        """Search Google Organic results"""
        if not self.connected:
            return []
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                payload = {
                    "location_name": location,
                    "language_code": "en",
                    "keyword": query,
                    "depth": 10
                }
                
                response = await client.post(
                    f"{self.base_url}/serp/google/organic/task_post",
                    json=[payload],
                    auth=self.auth
                )
                
                if response.status_code != 200:
                    return []
                
                task_data = response.json()
                task_id = task_data['tasks'][0]['id']
                
                await asyncio.sleep(5)
                
                result_response = await client.get(
                    f"{self.base_url}/serp/google/organic/task_get/{task_id}",
                    auth=self.auth
                )
                
                if result_response.status_code != 200:
                    return []
                
                result_data = result_response.json()
                results = result_data['tasks'][0].get('result', [])
                
                if not results:
                    return []
                
                candidates = []
                for item in results[0].get('items', [])[:5]:
                    if item.get('type') != 'organic':
                        continue
                    
                    candidate = {
                        'name': item.get('title', ''),
                        'website': item.get('url', ''),
                        'description': item.get('description', ''),
                        'source': 'Google Organic',
                        'source_url': item.get('url', ''),
                        'confidence': 0.8,
                        'why_here': f"Found in Google Organic results for '{query}'"
                    }
                    candidates.append(candidate)
                
                return candidates
                
        except Exception as e:
            print(f"DataForSEO Organic Search Error: {e}")
            return []
    
    async def fetch_website_content(self, url: str) -> Dict:
        """Fetch and extract website content"""
        try:
            async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
                response = await client.get(url)
                response.raise_for_status()
                
                html = response.text
                
                # Simple extraction (in production, use BeautifulSoup/lxml)
                title = ""
                description = ""
                headings = []
                
                # Extract title
                if '<title>' in html:
                    start = html.find('<title>') + 7
                    end = html.find('</title>')
                    title = html[start:end].strip()
                
                # Extract meta description
                if 'name="description"' in html:
                    start = html.find('name="description"')
                    content_start = html.find('content="', start) + 9
                    content_end = html.find('"', content_start)
                    description = html[content_start:content_end]
                
                # Extract headings (simplified)
                import re
                h1_pattern = r'<h1[^>]*>(.*?)</h1>'
                h2_pattern = r'<h2[^>]*>(.*?)</h2>'
                
                headings = re.findall(h1_pattern, html, re.IGNORECASE)[:3]
                headings += re.findall(h2_pattern, html, re.IGNORECASE)[:5]
                
                # Extract contact info (simplified)
                contact = {'email': '', 'phone': '', 'address': ''}
                
                email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
                phone_pattern = r'\+?[\d\s\-\(\)]{10,}'
                
                email_matches = re.findall(email_pattern, html)
                if email_matches:
                    contact['email'] = email_matches[0]
                
                return {
                    'title': title,
                    'description': description,
                    'headings': headings,
                    'contact': contact,
                    'status_code': response.status_code
                }
                
        except Exception as e:
            return {
                'error': str(e),
                'title': '',
                'description': '',
                'headings': [],
                'contact': {}
            }

# ==================== FASTAPI APP ====================

app = FastAPI(title="Zuxuru Investigation Platform", version="1.0.0")

# Initialize connectors
dataforseo_connector = DataForSEOConnector()

# Templates and Static Files
templates = Jinja2Templates(directory="/workspace/zuxuru_platform/templates")
app.mount("/static", StaticFiles(directory="/workspace/zuxuru_platform/static"), name="static")

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ==================== ENDPOINTS ====================

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health and status endpoint"""
    db_connected = True
    try:
        db = SessionLocal()
        db.execute("SELECT 1")
        db.close()
    except:
        db_connected = False
    
    dataforseo_connected = await dataforseo_connector.connect()
    
    return HealthResponse(
        status="healthy" if db_connected else "unhealthy",
        version="1.0.0",
        dataforseo_connected=dataforseo_connected,
        database_connected=db_connected
    )

@app.post("/investigate", response_model=InvestigationStatus)
async def start_investigation(request: InvestigationRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """Start a new investigation job"""
    
    # Create workspace if not exists (demo: single workspace)
    workspace = db.query(Workspace).filter(Workspace.name == "Default").first()
    if not workspace:
        workspace = Workspace(name="Default")
        db.add(workspace)
        db.commit()
        db.refresh(workspace)
    
    # Create investigation job
    job = InvestigationJob(
        workspace_id=workspace.id,
        query=request.query,
        status="pending"
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    
    # Start background processing
    background_tasks.add_task(process_investigation, job.id, request.query, request.location)
    
    return InvestigationStatus(
        job_id=job.id,
        status="pending",
        candidate_count=0
    )

@app.get("/investigation/{job_id}", response_model=InvestigationStatus)
async def get_investigation_status(job_id: int, db: Session = Depends(get_db)):
    """Get investigation job status and results"""
    job = db.query(InvestigationJob).filter(InvestigationJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Investigation job not found")
    
    candidates = []
    if job.status == "completed":
        # Get businesses (candidates)
        businesses = db.query(Business).filter(
            Business.workspace_id == job.workspace_id
        ).limit(5).all()
        
        for biz in businesses:
            candidates.append(BusinessCandidate(
                name=biz.name,
                website=biz.website_url,
                source="DataForSEO",
                source_url=biz.website_url or "",
                confidence=biz.confidence_score,
                why_here=f"Confirmed business from search results"
            ))
    
    evidence_cards = []
    evidence = db.query(EvidenceCard).filter(
        EvidenceCard.investigation_id == job_id
    ).all()
    
    for ev in evidence:
        evidence_cards.append(EvidenceCardSchema(
            card_type=ev.card_type,
            title=ev.title,
            content=ev.content,
            source_url=ev.source_url,
            source_link=ev.source_link,
            confidence_label=ev.confidence_label,
            why_here=ev.why_here
        ))
    
    return InvestigationStatus(
        job_id=job.id,
        status=job.status,
        candidate_count=job.candidate_count,
        candidates=candidates if candidates else None,
        evidence=evidence_cards if evidence_cards else None
    )

async def process_investigation(job_id: int, query: str, location: str):
    """Background task to process investigation"""
    db = SessionLocal()
    
    try:
        job = db.query(InvestigationJob).filter(InvestigationJob.id == job_id).first()
        if not job:
            return
        
        job.status = "running"
        job.started_at = datetime.utcnow()
        db.commit()
        
        # Check if DataForSEO is connected
        if not await dataforseo_connector.connect():
            job.status = "failed"
            job.error_message = "Search connector not connected. Configure DataForSEO credentials."
            job.completed_at = datetime.utcnow()
            db.commit()
            return
        
        # Search for candidates
        local_results = await dataforseo_connector.search_local(query, location)
        organic_results = await dataforseo_connector.search_organic(query, location)
        
        all_candidates = local_results + organic_results
        all_candidates = all_candidates[:5]  # Max 5 candidates
        
        job.candidate_count = len(all_candidates)
        
        # Process each candidate
        workspace = db.query(Workspace).filter(Workspace.id == job.workspace_id).first()
        
        for idx, candidate in enumerate(all_candidates):
            # Create business record
            business = Business(
                workspace_id=workspace.id,
                name=candidate['name'],
                confirmed=True,
                website_url=candidate.get('website', ''),
                confidence_score=candidate.get('confidence', 0.7),
                description=candidate.get('description', '')
            )
            db.add(business)
            db.flush()
            
            # Create evidence card for search result
            search_evidence = EvidenceCard(
                investigation_id=job.id,
                business_id=business.id,
                card_type="search_result",
                title=f"Found: {candidate['name']}",
                content=f"Discovered via {candidate['source']}",
                source_url=candidate['source_url'],
                source_link=candidate['source_url'],
                confidence_label="high" if candidate['confidence'] > 0.8 else "medium",
                why_here=candidate['why_here'],
                card_metadata=json.dumps({'source': candidate['source']})
            )
            db.add(search_evidence)
            
            # Fetch website if available
            if candidate.get('website'):
                website_data = await dataforseo_connector.fetch_website_content(candidate['website'])
                
                if 'error' not in website_data:
                    business.title = website_data.get('title', '')
                    business.description = website_data.get('description', '')
                    business.headings = json.dumps(website_data.get('headings', []))
                    business.contact_info = json.dumps(website_data.get('contact', {}))
                    
                    # Website evidence card
                    website_evidence = EvidenceCard(
                        investigation_id=job.id,
                        business_id=business.id,
                        card_type="website",
                        title=website_data.get('title', candidate['name']),
                        content=website_data.get('description', '')[:500],
                        source_url=candidate['website'],
                        source_link=candidate['website'],
                        confidence_label="high",
                        why_here=f"Extracted from official website: {candidate['website']}",
                        card_metadata=json.dumps({'headings': website_data.get('headings', [])})
                    )
                    db.add(website_evidence)
                    
                    # Contact evidence card if found
                    contact = website_data.get('contact', {})
                    if contact.get('email') or contact.get('phone'):
                        contact_content = []
                        if contact.get('email'):
                            contact_content.append(f"Email: {contact['email']}")
                        if contact.get('phone'):
                            contact_content.append(f"Phone: {contact['phone']}")
                        
                        contact_evidence = EvidenceCard(
                            investigation_id=job.id,
                            business_id=business.id,
                            card_type="contact",
                            title="Public Contact Information",
                            content="\n".join(contact_content),
                            source_url=candidate['website'],
                            source_link=candidate['website'],
                            confidence_label="high",
                            why_here=f"Discovered public contact details from website",
                            card_metadata=json.dumps(contact)
                        )
                        db.add(contact_evidence)
        
        job.status = "completed"
        job.completed_at = datetime.utcnow()
        db.commit()
        
    except Exception as e:
        job = db.query(InvestigationJob).filter(InvestigationJob.id == job_id).first()
        if job:
            job.status = "failed"
            job.error_message = str(e)
            job.completed_at = datetime.utcnow()
            db.commit()
    finally:
        db.close()

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Main dashboard"""
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/api/config")
async def get_config():
    """Get application configuration"""
    return {
        "dataforseo_connected": DATAFORSEO_LOGIN != "",
        "version": "1.0.0",
        "features": [
            "Real DataForSEO connector",
            "Up to 5 candidate businesses",
            "Website content extraction",
            "Contact discovery",
            "Evidence cards with confidence labels",
            "Source links and explanations"
        ]
    }

if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting Zuxuru Investigation Platform...")
    print("📊 Health check: http://localhost:8001/health")
    print("🔍 Dashboard: http://localhost:8001")
    print("⚙️  Configure DataForSEO: Set DATAFORSEO_LOGIN and DATAFORSEO_PASSWORD env vars")
    uvicorn.run(app, host="0.0.0.0", port=8001)
