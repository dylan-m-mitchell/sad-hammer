# Codebase Cleanup and Refactoring

## Issues Identified

### 1. Empty Directories (Remove)

- `backend/app/models/` - empty
- `backend/app/routes/` - empty
- `backend/app/services/` - empty
- `backend/app/utils/` - empty
- `frontend/src/assets/` - empty
- `frontend/src/services/` - empty
- `frontend/src/utils/` - empty
- `tools/` - empty

### 2. Unused Python Files (Remove)

- `prototype/coordinate_charge_demo.py` - Standalone prototype demo, not imported by app or tests
- `scripts/example_remove_unit.py` - Example/demo script, not used by application
- Entire `prototype/` directory can be removed

### 3. Build Artifacts (Should be gitignored)

- `frontend/dist/` - Build output, shouldn't be in repo
- `test-results/` - Test output
- `playwright-report/` - Test reports

### 4. Old/Unused Directories (Investigate)

- `web/` - Check if this is old frontend before React migration

## Python Files to KEEP (Used by Application)

**Core Application:**

- `backend/api_server.py` - Main Flask server
- `backend/deck_manager.py` - Battle tactics & action decks
- `backend/full_simulator.py` - Core simulator logic
- `backend/battlescribe_parser.py` - Roster parsing
- `backend/placement.py` - Unit placement logic
- `backend/reference_card_decks.py` - Card deck data
- `backend/server.py` - Docker entry point
- `backend/__init__.py` - Package init

**Used by Tests:**

- `backend/interactive_simulator.py` - Used by test_acceptance_accurate.py

**Compatibility Shims:**

- `api_server.py` (root) - For test compatibility
- `reference_card_decks.py` (root) - For test compatibility

## Proposed Actions

### Phase 1: Remove Empty Directories

```bash
rmdir backend/app/models
rmdir backend/app/routes
rmdir backend/app/services
rmdir backend/app/utils
rmdir frontend/src/assets
rmdir frontend/src/services
rmdir frontend/src/utils
rmdir tools
```

### Phase 2: Remove Unused Files

```bash
# Remove prototype directory
rm -rf prototype/

# Remove example script
rm scripts/example_remove_unit.py

# Keep for reference (per user request):
# - Current-Stormcasts.html
# - New-Orruk-Roster.html
```

### Phase 3: Investigate web/ Directory

- Check if `web/` is still used by api_server.py
- If unused, remove it
- If used, document why it exists

### Phase 4: Update .gitignore

Ensure these are ignored:

- `frontend/dist/`
- `test-results/`
- `playwright-report/`
- `__pycache__/`

## Validation Strategy

1. Run test suite to ensure nothing breaks
2. Verify Docker builds still work
3. Check all imports still resolve
4. Verify no functionality is lost
