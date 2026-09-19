# Zuxuru Investigation Platform

Real business discovery platform with DataForSEO connector, multi-tenant architecture, and evidence-based investigations.

## Features

- **Real DataForSEO Connector**: Google Local Pack & Organic Search integration
- **Business Discovery**: Up to 5 candidate businesses per investigation
- **Website Extraction**: Title, description, headings, and contact info
- **Evidence Cards**: Source links, confidence labels, and explanations
- **"Why Here?"**: Clear reasoning for each discovery
- **Multi-Tenant Ready**: Workspace architecture prepared for Supabase
- **No Fabrication**: Shows "Search connector not connected" when credentials missing

## Quick Start

```bash
# Install dependencies
pip install fastapi uvicorn httpx sqlalchemy pydantic python-jose passlib

# Set DataForSEO credentials (optional but required for real searches)
export DATAFORSEO_LOGIN="your_login"
export DATAFORSEO_PASSWORD="your_password"

# Run the application
cd /workspace/zuxuru_platform
python app/main.py
```

## Access Points

- **Dashboard**: http://localhost:8001
- **Health Check**: http://localhost:8001/health
- **API Docs**: http://localhost:8001/docs

## Configuration

### DataForSEO Credentials

The application works without credentials but shows "Search connector not connected". To enable real investigations:

1. Sign up at https://dataforseo.com/
2. Get your API login and password
3. Set environment variables:
   ```bash
   export DATAFORSEO_LOGIN="your_api_login"
   export DATAFORSEO_PASSWORD="your_api_password"
   ```

## Architecture

### Database Models

- **Workspace**: Multi-tenant workspace (Supabase-ready)
- **Business**: Confirmed business entities with website data
- **InvestigationJob**: Job tracking with status (pending/running/completed/failed)
- **EvidenceCard**: Evidence with type, source, confidence, and explanation

### Connector Pattern

```python
class BaseConnector:
    async def connect() -> bool
    async def search(query, location) -> List[Dict]
    async def fetch_website(url) -> Dict

class DataForSEOConnector(BaseConnector):
    async def search_local(query, location)  # Google Local Pack
    async def search_organic(query, location)  # Google Organic
    async def fetch_website_content(url)  # Extract title, desc, headings, contact
```

## API Endpoints

### POST /investigate
Start a new investigation job
```json
{
  "query": "coffee shop",
  "location": "United States"
}
```

### GET /investigation/{job_id}
Get job status and results
```json
{
  "job_id": 1,
  "status": "completed",
  "candidate_count": 3,
  "candidates": [...],
  "evidence": [...]
}
```

### GET /health
Health and status check
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "dataforseo_connected": true,
  "database_connected": true
}
```

## Evidence Card Types

1. **search_result**: Found via Google Local/Organic
2. **website**: Extracted from official website
3. **contact**: Public contact information discovered
4. **social**: Social media profiles (future)
5. **review**: Customer reviews (future)

Each card includes:
- Title and content
- Source URL with clickable link
- Confidence label (high/medium/low)
- "Why here?" explanation

## Next Steps

1. **Supabase Integration**: Replace SQLite with Supabase for production
2. **User Authentication**: Add accounts and workspaces
3. **Additional Connectors**: 
   - Google Maps API
   - Social media platforms
   - Review aggregators
   - Company registries
4. **Customer Intelligence**: Assets, opportunities, competitive analysis

## File Structure

```
zuxuru_platform/
├── app/
│   └── main.py          # Main application
├── templates/
│   └── index.html       # Web dashboard
├── static/              # Static assets
└── zuxuru_platform.db   # SQLite database (auto-created)
```

## License

Proprietary - Zuxuru Investigation Platform
