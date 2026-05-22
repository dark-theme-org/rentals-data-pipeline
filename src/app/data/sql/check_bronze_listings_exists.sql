/*
 * check_bronze_listings_exists.sql
 *
 * Purpose:
 *   Check whether any of the blobs about to be loaded have already been
 *   inserted into the Bronze table. Returns one row per already-loaded blob.
 *   An empty result means none of the blobs have been loaded yet.
 *
 * Partition pruning:
 *   The Bronze table is partitioned by DATE(SRC_EXECUTED_AT_TS). Filtering on
 *   <executed_at> ensures BigQuery scans only the relevant partitions
 *   instead of the full table, keeping the check cheap regardless of table size.
 *
 * Placeholders (resolved at runtime by BronzeListingsTable.read_and_replace_params):
 *   <destination>  — fully-qualified table ref (e.g. "my-project.dev_bronze.listings")
 *   <executed_at>  — scraper run date in YYYY-MM-DD format (e.g. '2026-01-01')
 *   <blob_name>    — GCS blob path to check (e.g. 'dev/vivareal/macae/apartment/1/blob.json')
 */
SELECT DISTINCT SRC_BLOB
FROM `{{ destination }}`
WHERE DATE(SRC_EXECUTED_AT_TS) = DATE('{{ executed_at }}')
    AND SRC_BLOB = '{{ blob_name }}'
