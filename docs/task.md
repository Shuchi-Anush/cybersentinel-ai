# Task Tracking — Targeted Production Hardening

- [ ] Hardening `src/models/evaluator.py`
    - [ ] Add module execution instruction header
    - [ ] Refactor `_print_summary()` to use `logger.info()` exclusively
    - [ ] Remove all `print()` occurrences
    - [ ] Audit `evaluate_binary` for concise single-line logging
    - [ ] Audit `evaluate_multiclass` for concise single-line logging
    - [ ] Ensure `_print_summary()` is only called in `run_evaluation()`
- [ ] Global Dashboard Streamlit Fixes
    - [ ] `src/dashboard/pages/1_Overview.py`: Replace `use_container_width=True` -> `width="stretch"`
    - [ ] `src/dashboard/pages/2_Predict.py`: Replace `use_container_width=True` -> `width="stretch"`
    - [ ] `src/dashboard/pages/3_Evaluation.py`: Replace `use_container_width=True` -> `width="stretch"`
    - [ ] `src/dashboard/pages/4_Policy.py`: Replace `use_container_width=True` -> `width="stretch"`
- [ ] Final Verification
    - [ ] Verify no `print()` remains in `evaluator.py`
    - [ ] Verify `grep` returns 0 for `use_container_width`
    - [ ] Confirm no Streamlit terminal warnings
