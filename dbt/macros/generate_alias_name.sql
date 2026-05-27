/*
 * Overrides the default dbt alias-name logic for BigQuery.
 *
 * The +schema value set in dbt_project.yml (silver, gold) is repurposed here
 * as a table name prefix instead of a dataset suffix (see generate_schema_name).
 * All models land in the target dataset, with their layer as a prefix:
 *
 *   +schema: silver  →  silver_stg_bronze_listings
 *   +schema: gold    →  gold_fact_listing_snapshots
 *
 * Models without a +schema (e.g. seeds) fall back to the standard behaviour.
 */
{% macro generate_alias_name(custom_alias_name=none, node=none) -%}
{%- set schema_prefix = node.config.get('schema') if node and node.config else none -%}
{%- if schema_prefix is not none and schema_prefix | trim != '' -%}
{{ schema_prefix | trim }}_{{ node.name | trim }}
{%- elif custom_alias_name is not none -%}
{{ custom_alias_name | trim }}
{%- else -%}
{{ node.name | trim }}
{%- endif -%}
{%- endmacro %}
