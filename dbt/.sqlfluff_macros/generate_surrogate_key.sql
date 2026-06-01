{% macro generate_surrogate_key(field_list) %}
    TO_HEX(MD5(CONCAT_WS(
        '||',
{%- for field in field_list %}
        COALESCE(CAST({{ field }} AS STRING), ''){% if not loop.last %},{% endif %}
{%- endfor %}
    )))
{% endmacro %}
