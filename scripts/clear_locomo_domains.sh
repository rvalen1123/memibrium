#!/usr/bin/env bash
set -euo pipefail

docker exec -i memibrium-ruvector-db psql -U memory -d memory <<'SQL'
BEGIN;
DELETE FROM temporal_expressions WHERE memory_id IN (SELECT id FROM memories WHERE domain LIKE 'locomo-%');
DELETE FROM memory_snapshots WHERE memory_id IN (SELECT id FROM memories WHERE domain LIKE 'locomo-%');
DELETE FROM user_feedback WHERE memory_id IN (SELECT id FROM memories WHERE domain LIKE 'locomo-%');
DELETE FROM contradictions WHERE memory_a_id IN (SELECT id FROM memories WHERE domain LIKE 'locomo-%') OR memory_b_id IN (SELECT id FROM memories WHERE domain LIKE 'locomo-%');
DELETE FROM memory_edges WHERE source_id IN (SELECT id FROM memories WHERE domain LIKE 'locomo-%') OR target_id IN (SELECT id FROM memories WHERE domain LIKE 'locomo-%');
DELETE FROM memories WHERE domain LIKE 'locomo-%';
COMMIT;
SQL

docker exec -i memibrium-ruvector-db psql -U memory -d memory -c "SELECT count(*) AS remaining_locomo FROM memories WHERE domain LIKE 'locomo-%';"
echo "cleared locomo-* domains"
