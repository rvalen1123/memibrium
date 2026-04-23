#!/usr/bin/env python3
"""Re-embed all memories from 768d (nomic) to 1536d (Azure embed-v-4-0)."""
import asyncio
import os
import time
import asyncpg
from openai import AzureOpenAI

# Azure config
AZURE_ENDPOINT = os.environ.get("AZURE_EMBEDDING_ENDPOINT", "https://azuregateway.azure-api.net/sector-7")
AZURE_KEY = os.environ.get("AZURE_EMBEDDING_API_KEY", os.environ.get("AZURE_OPENAI_API_KEY", ""))
AZURE_DEPLOYMENT = os.environ.get("AZURE_EMBEDDING_DEPLOYMENT", "embed-v-4-0")
AZURE_API_VERSION = os.environ.get("AZURE_API_VERSION", "2024-12-01-preview")

# DB config
DB_URL = os.environ.get("DATABASE_URL", "postgresql://memory:memory@localhost:5432/memory")

BATCH_SIZE = 50  # Azure supports up to ~2048 inputs, but keep batches manageable


async def main():
    client = AzureOpenAI(
        api_key=AZURE_KEY,
        azure_endpoint=AZURE_ENDPOINT,
        api_version=AZURE_API_VERSION,
    )
    
    # Test embed first
    print("Testing Azure embedding endpoint...")
    test = client.embeddings.create(input=["test"], model=AZURE_DEPLOYMENT)
    dim = len(test.data[0].embedding)
    print(f"  Model: {AZURE_DEPLOYMENT}, Dimensions: {dim}")
    assert dim == 1536, f"Expected 1536d, got {dim}d"
    
    conn = await asyncpg.connect(DB_URL)
    
    # Step 1: Drop HNSW index and alter column
    print("\nStep 1: Dropping HNSW index and altering column to 1536d...")
    await conn.execute("DROP INDEX IF EXISTS memories_embedding_idx;")
    await conn.execute("ALTER TABLE memories ALTER COLUMN embedding TYPE ruvector(1536);")
    # Clear all existing embeddings (they're 768d, incompatible)
    await conn.execute("UPDATE memories SET embedding = NULL;")
    print("  Done.")
    
    # Step 2: Fetch all memories
    rows = await conn.fetch("SELECT id, content FROM memories ORDER BY created_at;")
    total = len(rows)
    print(f"\nStep 2: Re-embedding {total} memories in batches of {BATCH_SIZE}...")
    
    embedded = 0
    errors = 0
    t0 = time.time()
    
    for i in range(0, total, BATCH_SIZE):
        batch = rows[i:i+BATCH_SIZE]
        texts = [r["content"][:8000] for r in batch]  # truncate to avoid token limits
        ids = [r["id"] for r in batch]
        
        try:
            resp = client.embeddings.create(input=texts, model=AZURE_DEPLOYMENT)
            for j, emb_data in enumerate(resp.data):
                vec = emb_data.embedding
                vec_str = "[" + ",".join(str(v) for v in vec) + "]"
                await conn.execute(
                    "UPDATE memories SET embedding = $1::ruvector WHERE id = $2;",
                    vec_str, ids[j]
                )
            embedded += len(batch)
            elapsed = time.time() - t0
            rate = embedded / elapsed if elapsed > 0 else 0
            print(f"  {embedded}/{total} ({embedded*100//total}%) — {rate:.1f} mem/s")
        except Exception as e:
            errors += len(batch)
            print(f"  ERROR at batch {i//BATCH_SIZE}: {e}")
            # Try one-by-one for this batch
            for j, (text, mid) in enumerate(zip(texts, ids)):
                try:
                    resp = client.embeddings.create(input=[text], model=AZURE_DEPLOYMENT)
                    vec = resp.data[0].embedding
                    vec_str = "[" + ",".join(str(v) for v in vec) + "]"
                    await conn.execute(
                        "UPDATE memories SET embedding = $1::ruvector WHERE id = $2;",
                        vec_str, mid
                    )
                    embedded += 1
                    errors -= 1
                except Exception as e2:
                    print(f"    SKIP {mid}: {e2}")
    
    elapsed = time.time() - t0
    print(f"\nEmbedding complete: {embedded}/{total} in {elapsed:.1f}s, {errors} errors")
    
    # Step 3: Rebuild HNSW index
    print("\nStep 3: Rebuilding HNSW index (1536d)...")
    await conn.execute("""
        CREATE INDEX memories_embedding_idx 
        ON memories USING hnsw (embedding ruvector_cosine_ops) 
        WITH (m = 16, ef_construction = 200);
    """)
    print("  Done.")
    
    # Verify
    count = await conn.fetchval("SELECT COUNT(id) FROM memories WHERE embedding IS NOT NULL;")
    print(f"\nVerification: {count}/{total} memories have embeddings")
    
    await conn.close()
    print("All done!")


if __name__ == "__main__":
    asyncio.run(main())
