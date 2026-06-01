{{
    config(
        unique_key=['AMENITIES_SK', 'AMENITY_NAME', 'AMENITY_VALUE'],
        partition_by={
            'field': 'AUD_UPD_TS',
            'data_type': 'timestamp',
            'granularity': 'day'
        },
        cluster_by=['AMENITIES_SK', 'IN_LAST_SCRAPE_FLAG']
    )
}}

{%- set amenity_sk_cols = ['AMENITY_FEATURES'] -%}
{%- set amenity_array_fields = ['AMENITY_FEATURES'] -%}
{% set default_text = "'unknown'" %}

{% if not is_incremental() %}

SELECT
    {{ generate_surrogate_key(amenity_sk_cols, amenity_array_fields) }} AS AMENITIES_SK,
    COALESCE(AF.NAME, {{ default_text }}) AS AMENITY_NAME,
    COALESCE(AF.VALUE, {{ default_text }}) AS AMENITY_VALUE,
    TRUE AS IN_LAST_SCRAPE_FLAG,
    CURRENT_TIMESTAMP() AS AUD_INS_TS,
    CURRENT_TIMESTAMP() AS AUD_UPD_TS
FROM {{ ref('listings_deduped') }},
    UNNEST(AMENITY_FEATURES) AS AF
QUALIFY ROW_NUMBER() OVER (
    PARTITION BY AMENITIES_SK, AMENITY_NAME, AMENITY_VALUE
    ORDER BY SCRAPE_DATE DESC
) = 1

{% else %}

WITH SOURCE AS (
    SELECT DISTINCT
        {{ generate_surrogate_key(amenity_sk_cols, amenity_array_fields) }} AS AMENITIES_SK,
        COALESCE(AF.NAME, {{ default_text }}) AS AMENITY_NAME,
        COALESCE(AF.VALUE, {{ default_text }}) AS AMENITY_VALUE
    FROM {{ ref('listings_deduped') }},
        UNNEST(AMENITY_FEATURES) AS AF
    QUALIFY SCRAPE_DATE = MAX(SCRAPE_DATE) OVER ()
),

ACTIVE AS (
    SELECT
        SRC.AMENITIES_SK,
        SRC.AMENITY_NAME,
        SRC.AMENITY_VALUE,
        TRUE AS IN_LAST_SCRAPE_FLAG,
        COALESCE(TGT.AUD_INS_TS, CURRENT_TIMESTAMP()) AS AUD_INS_TS,
        CURRENT_TIMESTAMP() AS AUD_UPD_TS
    FROM SOURCE AS SRC
    LEFT JOIN {{ this }} AS TGT
        ON SRC.AMENITIES_SK = TGT.AMENITIES_SK
            AND SRC.AMENITY_NAME = TGT.AMENITY_NAME
            AND SRC.AMENITY_VALUE = TGT.AMENITY_VALUE
),

DEACTIVATED AS (
    SELECT
        TGT.AMENITIES_SK,
        TGT.AMENITY_NAME,
        TGT.AMENITY_VALUE,
        FALSE AS IN_LAST_SCRAPE_FLAG,
        TGT.AUD_INS_TS,
        CURRENT_TIMESTAMP() AS AUD_UPD_TS
    FROM {{ this }} AS TGT
    WHERE TGT.IN_LAST_SCRAPE_FLAG = TRUE
        AND NOT EXISTS (
            SELECT 1
            FROM SOURCE AS SRC
            WHERE SRC.AMENITIES_SK = TGT.AMENITIES_SK
                AND SRC.AMENITY_NAME = TGT.AMENITY_NAME
                AND SRC.AMENITY_VALUE = TGT.AMENITY_VALUE
        )
)

SELECT * FROM ACTIVE
UNION ALL
SELECT * FROM DEACTIVATED

{% endif %}
