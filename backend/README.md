# GeoSafe Backend

## Quick Start

```bash
# 1. Create virtual environment
python -m venv venv
source venv/Scripts/activate   # Windows
# source venv/bin/activate     # Linux/Mac

# 2. Install dependencies
pip install -r requirements.txt

# 3. Copy environment config
cp .env.example .env
# Edit .env with your API keys

# 4. (Optional) Train ML model
python -m ml.train_model

# 5. Start the API server
uvicorn app.main:app --reload --port 8000
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/validate` | Full 7-step pipeline → Safety Report |
| `POST` | `/api/v1/geocode` | Geocode survey number / coordinates |
| `GET` | `/api/v1/layers` | List available KGIS layers |
| `GET` | `/api/v1/reports/{token}` | Retrieve report by shareable token |
| `GET` | `/api/v1/reports/{token}/map` | GeoJSON map overlay data |
| `GET` | `/api/v1/health` | Health check |
| `GET` | `/docs` | Swagger UI |

## Example Request

```json
{
  "input_type": "coordinates",
  "coordinates_input": {
    "latitude": 12.8584,
    "longitude": 77.7842,
    "buffer_m": 500
  }
}
```
