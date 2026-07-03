"""Print the FastAPI OpenAPI schema as JSON (for frontend type codegen)."""
import json

from app.api.main import app

print(json.dumps(app.openapi()))
