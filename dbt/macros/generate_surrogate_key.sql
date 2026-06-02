{% macro generate_surrogate_key(field_list, array_fields=[]) %}
    TO_HEX(MD5(CONCAT(
{%- for field in field_list %}
{%- if field in array_fields %}
        COALESCE(TO_JSON_STRING({{ field }}), ''){% if not loop.last %}, '||', {% endif %}
{%- else %}
        COALESCE(CAST({{ field }} AS STRING), ''){% if not loop.last %}, '||', {% endif %}
{%- endif %}
{%- endfor %}
    )))
{% endmacro %}
