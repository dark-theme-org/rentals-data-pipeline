/*
 * check_table_exists.sql
 *
 * Purpose:
 *   Check whether a BigQuery table already exists in a given dataset.
 *   Returns a single row with cnt = 1 if the table exists, cnt = 0 otherwise.
 *
 * Placeholders (resolved at runtime by Table.read_and_replace_params):
 *   <project>     — GCP project ID (e.g. "my-project")
 *   <dataset>     — BigQuery dataset name (e.g. "dev_bronze")
 *   <table_name>  — BigQuery table name (e.g. "listings")
 */
SELECT COUNT(*) AS CNT
FROM `{{ project }}.{{ dataset }}.INFORMATION_SCHEMA.TABLES`
WHERE TABLE_NAME = '{{ table_name }}'
