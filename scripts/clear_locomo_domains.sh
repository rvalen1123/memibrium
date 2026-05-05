#!/usr/bin/env bash
set -euo pipefail

docker exec -i memibrium-ruvector-db psql -U memory -d memory <<'SQL'
BEGIN;
CREATE TEMP TABLE locomo_memory_ids AS
SELECT id FROM memories WHERE domain LIKE 'locomo-%';

CREATE TEMP TABLE affected_entities AS
SELECT DISTINCT e.entity_id
FROM entities e
JOIN locomo_memory_ids lm
  ON e.memory_ids ? lm.id;

DELETE FROM temporal_expressions WHERE memory_id IN (SELECT id FROM locomo_memory_ids);
DELETE FROM memory_snapshots WHERE memory_id IN (SELECT id FROM locomo_memory_ids);
DELETE FROM user_feedback WHERE memory_id IN (SELECT id FROM locomo_memory_ids);
DELETE FROM contradictions WHERE memory_a_id IN (SELECT id FROM locomo_memory_ids) OR memory_b_id IN (SELECT id FROM locomo_memory_ids);
DELETE FROM memory_edges WHERE source_id IN (SELECT id FROM locomo_memory_ids) OR target_id IN (SELECT id FROM locomo_memory_ids);
DELETE FROM memories WHERE id IN (SELECT id FROM locomo_memory_ids);

UPDATE entities e
SET memory_ids = COALESCE(
  (
    SELECT jsonb_agg(mid ORDER BY ord)
    FROM jsonb_array_elements_text(e.memory_ids) WITH ORDINALITY AS mids(mid, ord)
    WHERE mid NOT IN (SELECT id FROM locomo_memory_ids)
  ),
  '[]'::jsonb
),
updated_at = NOW()
WHERE e.entity_id IN (SELECT entity_id FROM affected_entities);

CREATE TEMP TABLE entities_to_delete AS
SELECT e.entity_id
FROM entities e
JOIN affected_entities ae ON ae.entity_id = e.entity_id
WHERE jsonb_array_length(e.memory_ids) = 0;

DELETE FROM entity_relationships
WHERE entity_a IN (SELECT entity_id FROM entities_to_delete)
   OR entity_b IN (SELECT entity_id FROM entities_to_delete)
   OR entity_a NOT IN (SELECT entity_id FROM entities)
   OR entity_b NOT IN (SELECT entity_id FROM entities);

DELETE FROM entities
WHERE entity_id IN (SELECT entity_id FROM entities_to_delete);

COMMIT;
SQL

docker exec -i memibrium-ruvector-db psql -U memory -d memory -c "SELECT count(*) AS remaining_locomo FROM memories WHERE domain LIKE 'locomo-%';"
echo "cleared locomo-* domains"
