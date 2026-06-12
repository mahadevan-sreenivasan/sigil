# Structured similarity with weighted scoring over vector embeddings

We need to compare incoming browser fingerprints against stored historical fingerprints to find near-matches. We chose structured feature vectors with weighted similarity scoring (candidate filtering on indexed high-entropy columns, then arithmetic scoring on ~200 candidates) over dense vector embeddings with a vector database (Pinecone, Qdrant, pgvector).

Browser signals are structured and low-dimensional (~15-25 discrete features). A vector DB solves a problem we don't have — high-dimensional unstructured similarity search. Structured scoring is faster to build, runs on standard PostgreSQL indexes, and is fully explainable ("these two fingerprints matched on canvas and WebGL but differed on timezone"), which matters when integrators need to debug fraud decisions. At our target scale (100K active users/month, ~6M signal sets over 180 days), PostgreSQL handles the candidate filtering and scoring without specialized infrastructure.

## Considered Options

- **Vector DB (Pinecone, Qdrant, pgvector ANN)**: Better suited if signal count grew to hundreds or we needed learned embeddings. Rejected because it adds infrastructure complexity, reduces explainability, and is unnecessary at our signal count and data volume.
- **Exact hash matching**: Simpler but brittle — a single changed signal breaks the match entirely. Rejected because browser signals drift naturally (updates, configuration changes) and exact matching would produce excessive false negatives.
