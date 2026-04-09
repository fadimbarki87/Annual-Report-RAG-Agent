# Qdrant Cloud Storage

This document explains how this project stores generated embeddings in Qdrant Cloud for the later RAG website.

## Decision

Use Qdrant Cloud free tier from the beginning.

This is better for the project goal because the final app will be deployed online with Render. If we start directly with Qdrant Cloud, the later Render website can connect to the same vector database without changing the storage architecture.

Local Qdrant with Docker is still useful for experimentation, but it is no longer the main path for this project.

## Why Qdrant Cloud Free

Qdrant Cloud is a managed vector database. Qdrant's pricing page says Managed Cloud starts at `$0` with a `1GB` free cluster and no credit card required.

Qdrant's free cluster documentation says free clusters are intended for prototyping and testing and include:

```text
RAM: 1 GB
vCPU: 0.5
Disk space: 4 GB
Nodes: 1
```

For this project, that is a reasonable fit because the current embedding set contains:

```text
7426 vectors
3072 dimensions per vector
```

This is small enough for a prototype/demo vector database.

One important free-tier note: Qdrant says unused free clusters can be suspended after 1 week and deleted after 4 weeks of inactivity if not reactivated. For a CV demo, that is acceptable, but we should remember it before sharing the public website.

## Why Not Local Qdrant On Render Free

Render free web services are not a good place to store a vector database locally.

The reason is persistence:

- Render services have an ephemeral filesystem by default.
- Persistent disks are for paid Render services.
- If Qdrant stores its database inside a free Render web service, the vectors can disappear after redeploys, restarts, or spin-downs.

So for a no-cost online demo, the better architecture is:

```text
Render free web app -> Qdrant Cloud free cluster
```

That keeps the database outside the website container, which is more professional and safer.

## Files

The Qdrant storage files are:

```text
ingestion_pipeline/vector_storage/qdrant/upsert_embeddings_to_qdrant.py
ingestion_pipeline/vector_storage/qdrant/qdrant_config.template.json
ingestion_pipeline/vector_storage/qdrant/qdrant_config.json
ingestion_pipeline/vector_storage/qdrant/QDRANT_STORAGE.md
```

The real config file is ignored by Git:

```text
ingestion_pipeline/vector_storage/qdrant/qdrant_config.json
```

The GitHub-safe template is:

```text
ingestion_pipeline/vector_storage/qdrant/qdrant_config.template.json
```

## Qdrant Cloud Setup

In Qdrant Cloud:

1. Create a free cluster.
2. Open the cluster details.
3. Copy the cluster URL.
4. Create a database API key for the cluster.
5. Store the URL and API key in `qdrant_config.json`.

Use a database API key for the cluster, not a Qdrant Cloud management key.

The config should look like this:

```json
{
  "qdrant_url": "https://YOUR-QDRANT-CLOUD-CLUSTER-URL",
  "api_key": "YOUR_QDRANT_DATABASE_API_KEY",
  "collection_name": "annual_report_chunks",
  "vector_size": 3072,
  "distance": "Cosine",
  "batch_size": 64,
  "recreate_collection": false,
  "on_disk_payload": true,
  "payload_indexes": {
    "document_id": "keyword",
    "source_file": "keyword",
    "chunk_type": "keyword",
    "content_source": "keyword",
    "chunk_index": "integer",
    "page_start": "integer",
    "page_end": "integer"
  }
}
```

Replace:

```text
YOUR-QDRANT-CLOUD-CLUSTER-URL
YOUR_QDRANT_DATABASE_API_KEY
```

with your real Qdrant Cloud values.

## Upsert Script

The upsert script reads embedding JSONL files from:

```text
ingestion_pipeline/embeeding/data/embeddings
```

It creates or reuses a Qdrant collection and upserts one point per embedded chunk.

Each point contains:

- a stable UUID point ID derived from the chunk ID
- the `3072`-dimension embedding vector
- the original chunk text and metadata as payload
- `table_metadata` for table chunks, including row range and table shape

The collection uses:

```text
vector size: 3072
distance: Cosine
```

This matches the `text-embedding-3-large` embeddings generated earlier.

The script also creates payload indexes for filterable fields:

```text
document_id
source_file
chunk_type
content_source
chunk_index
page_start
page_end
```

These indexes are needed for reliable filtered retrieval, for example BMW-only search or table-only search.

## Run Command

After editing `qdrant_config.json`, run from the project root:

```powershell
python .\ingestion_pipeline\vector_storage\qdrant\upsert_embeddings_to_qdrant.py
```

The script writes a storage summary here:

```text
ingestion_pipeline/vector_storage/qdrant/data/qdrant_upsert_summary.json
```

The key field is:

```text
collection_count_matches_upserted_points
```

If this is `true`, Qdrant contains the same number of points that the script upserted.

## Do We Need Evaluation Metrics Here?

Not the same kind as parsing/chunking/retrieval.

For Qdrant storage, we need storage integrity checks:

- number of points upserted
- collection point count after upsert
- whether point count matches expected embeddings
- whether collection vector size is correct

Those are handled by the upsert summary.

Final retrieval quality metrics come later, after we implement search:

- `Recall@k`
- `MRR`
- `nDCG@k`
- `Hit@k`
- answer faithfulness
- answer correctness

## Sources

- Qdrant pricing: https://qdrant.tech/pricing/
- Qdrant Cloud cluster creation: https://qdrant.tech/documentation/cloud/create-cluster/
- Qdrant Cloud quickstart: https://qdrant.tech/documentation/cloud/quickstart-cloud/
- Qdrant database authentication: https://qdrant.tech/documentation/cloud/authentication/
- Render persistent disks: https://render.com/docs/disks
