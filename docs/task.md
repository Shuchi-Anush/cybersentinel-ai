# Architecture Fixes

- [/] F1 — Unify selected_features.json path to data/processed/
  - [ ] Update selector.py OUTPUT_PATH
  - [ ] Verify preprocessor.py FEATURES_JSON
  - [ ] Move file from configs/ to data/processed/
- [ ] F2 — Fix pipeline_runner.py to new stage signatures
- [ ] F3 — Fix Dockerfile to COPY models/ and data/processed/
- [ ] F4 — Load InferencePipeline at FastAPI startup (lifespan)
- [ ] F5 — Remove empty stub files
- [ ] Show updated folder tree
