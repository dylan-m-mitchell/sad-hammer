# Architecture Decisions

## File Structure Explained

### Why both `api_server.py` (root) and `backend/api_server.py` exist?
- `backend/api_server.py` - Actual Flask application with all routes
- `api_server.py` (root) - Compatibility shim for tests that import from project root
- Root shim is needed for backward compatibility with test suite

### Why both `api_server.py` and `backend/server.py` exist?
- `backend/api_server.py` - Defines the Flask `app` object with all routes
- `backend/server.py` - Entry point wrapper that sets up paths for Docker
- Used by Docker (`CMD ["python", "backend/server.py"]`) and `scripts/start_backend.sh`
- Handles sys.path setup to ensure imports work correctly
- Both are required and serve different purposes

### Why `web/` directory exists alongside React frontend?
- `web/` - Simple HTML test interface for local Flask development
- `frontend/` - Production React application served by nginx in Docker
- `web/` used when running Flask directly without Docker
- React frontend used in production Docker setup
- Both needed for different deployment scenarios

## Recommendation
Keep all current files - they each serve a purpose in the deployment pipeline.
