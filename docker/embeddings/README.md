# Embeddings Service

This directory configures a local embedding server using Hugging Face Text Embeddings Inference (TEI) with the `sentence-transformers/all-MiniLM-L6-v2` model.

## Overview

The embeddings service provides an OpenAI-compatible API for generating text embeddings locally.

- **Model**: sentence-transformers/all-MiniLM-L6-v2
- **Embedding Dimension**: 384
- **API Endpoint**: http://embeddings:80/v1 (internal), http://localhost:8081/v1 (external)

## Prerequisites

To use embeddings for search and agent features, add these to your `.env` file (see `.env.example`):

```env
AGENT_ENABLED=True
SEARCH_ENABLED=True
OPENAI_API_KEY=your-api-key-here  # Optional: only needed for agent features or when using OpenAI embeddings
```

## Local Embeddings (Default)

This setup uses a local embedding service with no external API required. The default configuration in `embeddings.env` is:

- `OPENAI_BASE_URL=http://embeddings:80/v1`
- `EMBEDDING_DIMENSION=384`

### Start the orchestrator

Start the orchestrator with the local embeddings service:

```bash
docker compose --profile embeddings up orchestrator
```

## Alternative: Using OpenAI Embeddings

If you prefer to use OpenAI's embedding service instead of running a local model:

### Configuration

Override the embedding settings by editing `docker/overrides/embeddings/embeddings.env`:

```env
OPENAI_BASE_URL=https://api.openai.com/v1
EMBEDDING_DIMENSION=1536
```

### Start the orchestrator

Start only the orchestrator (skips the local embeddings service):

```bash
docker compose up orchestrator
```

## Post-Setup Steps

After starting the services and making sure you have data for the entity you want to index:

### 1. Apply the schema change

This will resize the vector dimension to match your embedding configuration (384 for local, 1536 for OpenAI) and delete existing records:

```bash
docker compose exec orchestrator /home/orchestrator/.venv/bin/python main.py embedding resize
```

⚠️ **Note**: This command will delete all existing embedding records.

### 2. Re-index your data

Example Index subscriptions:

```bash
docker compose exec orchestrator /home/orchestrator/.venv/bin/python main.py index subscriptions
```

## Advanced Configuration

The following configurations use conservative defaults for local/unknown models:

- `EMBEDDING_FALLBACK_MAX_TOKENS=512`: Maximum tokens per embedding request
- `EMBEDDING_MAX_BATCH_SIZE=32`: Maximum batch size for embedding requests

**Note**: These settings are only used as fallbacks for local or unknown models (like the example in this setup). For known providers and models, the system automatically retrieves the correct values via LiteLLM. The fallback values are already configured safely for local models, but can be adjusted if needed in `docker/overrides/embeddings/embeddings.env`.
