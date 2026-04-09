# GitHub And Render Prep

## Secrets

Do not commit the real local config files that contain secrets.

These are already ignored by [.gitignore](C:/Users/hp/Downloads/rag_annual_reports/.gitignore):

- `ingestion_pipeline/embeeding/azure_openai_config.json`
- `ingestion_pipeline/vector_storage/qdrant/qdrant_config.json`
- `agent_pipeline/answer_generation/answer_generation_config.json`
- `.env`
- `.env.*`

Safe files to keep in GitHub:

- `*.template.json`
- frontend source files
- backend source files
- evaluation files
- deployment docs

## Version Pinning

Backend runtime is pinned with:

- [requirements.txt](C:/Users/hp/Downloads/rag_annual_reports/requirements.txt)
- [.python-version](C:/Users/hp/Downloads/rag_annual_reports/.python-version)

Frontend runtime is pinned with:

- [.node-version](C:/Users/hp/Downloads/rag_annual_reports/.node-version)
- [package-lock.json](C:/Users/hp/Downloads/rag_annual_reports/ui/package-lock.json)

This keeps Render closer to the versions that already work locally.

## Render Notes

For the backend, install from:

```text
requirements.txt
```

For the frontend, Render will use the locked dependency tree from:

```text
ui/package-lock.json
```

Keep secrets in Render environment variables or private config files, not in GitHub.
