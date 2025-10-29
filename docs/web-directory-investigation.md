# Web Directory Investigation Results

## Summary
The `web/` directory is a legacy simple HTML test interface that predates the React frontend. It is NOT used in production Docker builds.

## Findings

### Web Directory (legacy)
- **Location:** `web/index.html`
- **Size:** 98 lines
- **Functionality:** Basic roster upload, simulation run, simple log display
- **Served by:** backend/api_server.py (lines 107, 112) via Flask
- **Status:** Legacy/test interface

### React Frontend (production)
- **Location:** `frontend/src/App.jsx`
- **Size:** 1,113 lines
- **Functionality:** 
  - Full stateless session management
  - Battleplan selection
  - Unit removal
  - Roll resolution (player mode)
  - Placement modal
  - Detailed event log
  - Multiple UI components
- **Served by:** Nginx (Docker production) or Vite dev server
- **Status:** Production-ready UI

## Usage in Build Pipeline
- ❌ NOT used in `docker-compose.yml`
- ❌ NOT used in `frontend/Dockerfile`
- ❌ NOT used in `scripts/start_frontend.sh`
- ✅ Served by `backend/api_server.py` when running Flask directly

## Recommendation
**Option A: Remove `web/` entirely** (Recommended)
- React frontend has complete feature parity
- Simpler codebase maintenance
- Remove Flask route handlers for web/ serving
- Update api_server.py to remove web/ routes

**Option B: Keep as fallback**
- Useful for testing API without React
- Minimal overhead
- Document as test interface

**Option C: Convert to static assets**
- Move battleplan maps or other assets there
- Rename directory to avoid confusion

## Decision: Keep `web/` Directory

After investigation, the decision is to **keep the `web/` directory** for the following reasons:

1. **Local Development Fallback**: When running `python backend/server.py` locally without Docker, Flask needs to serve something at the root route
2. **API Testing**: The simple HTML interface allows testing the API without React dependencies
3. **Minimal Maintenance Burden**: The 98-line file has minimal maintenance overhead
4. **Production Uses React**: In production Docker setup, nginx serves the React frontend, so web/ is not used

The `web/` directory will remain but be documented as a legacy test interface. The React frontend remains the primary user interface.
