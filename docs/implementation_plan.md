# Final Stabilization Patch — CyberSentinel-AI Dashboard

This plan outlines the final surgical fixes to resolve dashboard state synchronization issues, harden the API client, and ensure the UI strictly aligns with the production backend contract.

## User Review Required

> [!IMPORTANT]
> **API Client Refactor**: Moving all Streamlit caching (`@st.cache_data`) from class methods to module-level functions. The `health` check is explicitly **NON-CACHED** to ensure real-time status detection during model loading.

> [!IMPORTANT]
> **Forced Refresh**: Implementing a "Boot Refresh" mechanism in `app.py`. This ensures that when the backend transitions from "Loading" to "Online" in the background, the UI synchronizes immediately rather than waiting for the next 5s poll.

## Proposed Changes

### [Component] API Client Hardening

#### [MODIFY] [api_client.py](file:///d:/cybersentinel-ai/src/dashboard/api_client.py)
1. **Module-Level Helpers**:
    - Implement `_internal_request(method, base_url, path, timeout, json_data)` with:
        - 3 retries.
        - Exponential backoff: `0.5 * (attempt + 1)`.
        - Proper exception raising (`RequestException`).
2. **Metadata Functions (Cached)**:
    - `_features_cached`, `_models_cached`, `_policy_cached`, `_eval_cached`, `_config_cached` with TTL 300s.
    - **Fix (Task 1)**: Ensure `_get_policy` calls `_internal_request` correctly.
3. **Health Function (Real-time)**:
    - **Fix (Task 2)**: `_get_health` without caching.
4. **API Class**: Refactor to call these helpers. Remove `is_reachable` and old fallback logic.

### [Component] Dashboard Entry Point

#### [MODIFY] [app.py](file:///d:/cybersentinel-ai/src/dashboard/app.py)
1. **State Fetching**:
    - Use a single `health = api.health()` call in a `try/except` block.
    - **Fix (Task 4)**: Implement the following logic immediately after fetching `health`:
      ```python
      if api_online and not pipeline_ready and not pipeline_error:
          if "boot_refresh_done" not in st.session_state:
              st.session_state.boot_refresh_done = True
              st.rerun()
      ```
2. **Strict Status Mapping**:
    - Apply EXACT rules for Offline/Error/Online/Loading.
    - **Fix (Task 3)**: Use `pipeline_error is not None` for the error condition.
3. **Resilient Metrics**:
    - Update the metrics row to display mapped statuses.
    - Wrap `api.get_models()` in a `try/except` block for total UI stability.
4. **Auto Refresh**: Update fixed 5s refresh logic using `st.session_state` to prevent infinite loop instability.

## Open Questions

- None. The fixes are targeted and highly specific to reported bugs.

## Verification Plan

### Automated Tests
- None (Visual/Integrative verification is primary).

### Manual Verification
1. **Startup Check**: Observe **"🟡 Loading"** for 5-10s while background model loading occurs.
2. **Sync Check**: Verify the UI automatically refreshes to **"🟢 Online"** once the pipeline is ready (testing the boot refresh).
3. **Error Check**: Simulate a load failure and verify **"🔴 Error"** shows with a truncated snippet.
4. **Downtime**: Stop the API and verify all metrics instantly show **"🔴 Offline"**.
