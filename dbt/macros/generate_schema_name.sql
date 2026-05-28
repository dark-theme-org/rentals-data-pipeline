/*
 * Overrides the default dbt schema-name logic for BigQuery.
 *
 * All models — regardless of their +schema setting — land in the target
 * dataset (e.g. "dev", "test", "prod"). The +schema value (silver, gold)
 * is repurposed as a table name prefix by generate_alias_name.sql, not as
 * a dataset suffix.
 *
 * Default dbt behaviour would produce "dev_silver" / "dev_gold" — this
 * macro suppresses that and always returns the bare target schema.
 */
{% macro generate_schema_name(custom_schema_name, node) -%}
{{ target.schema | trim }}
{%- endmacro %}
