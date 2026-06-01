{{
    config(
        unique_key=['IMAGES_SK', 'IMAGE_URL'],
        partition_by={
            'field': 'AUD_UPD_TS',
            'data_type': 'timestamp',
            'granularity': 'day'
        },
        cluster_by=['IN_LAST_SCRAPE_FLAG']
    )
}}

{%- set images_sk_cols = ['LISTING_ID', 'IMAGES'] -%}
{% set default_text = "'unknown'" %}

{% if not is_incremental() %}

SELECT DISTINCT
    {{ generate_surrogate_key(images_sk_cols) }} AS IMAGES_SK,
    COALESCE(IMAGE_URL, {{ default_text }}) AS IMAGE_URL,
    TRUE AS IN_LAST_SCRAPE_FLAG,
    CURRENT_TIMESTAMP() AS AUD_INS_TS,
    CURRENT_TIMESTAMP() AS AUD_UPD_TS
FROM {{ ref('listings_deduped') }},
    UNNEST(IMAGES) AS IMAGE_URL

{% else %}

WITH SOURCE AS (
    SELECT DISTINCT
        {{ generate_surrogate_key(images_sk_cols) }} AS IMAGES_SK,
        COALESCE(IMAGE_URL, {{ default_text }}) AS IMAGE_URL
    FROM {{ ref('listings_deduped') }},
        UNNEST(IMAGES) AS IMAGE_URL
    QUALIFY SCRAPE_DATE = MAX(SCRAPE_DATE) OVER ()
),

ACTIVE AS (
    SELECT
        SRC.IMAGES_SK,
        SRC.IMAGE_URL,
        TRUE AS IN_LAST_SCRAPE_FLAG,
        COALESCE(TGT.AUD_INS_TS, CURRENT_TIMESTAMP()) AS AUD_INS_TS,
        CURRENT_TIMESTAMP() AS AUD_UPD_TS
    FROM SOURCE AS SRC
    LEFT JOIN {{ this }} AS TGT
        ON SRC.IMAGES_SK = TGT.IMAGES_SK
            AND SRC.IMAGE_URL = TGT.IMAGE_URL
),

DEACTIVATED AS (
    SELECT
        TGT.IMAGES_SK,
        TGT.IMAGE_URL,
        FALSE AS IN_LAST_SCRAPE_FLAG,
        TGT.AUD_INS_TS,
        CURRENT_TIMESTAMP() AS AUD_UPD_TS
    FROM {{ this }} AS TGT
    WHERE TGT.IN_LAST_SCRAPE_FLAG = TRUE
        AND NOT EXISTS (
            SELECT 1
            FROM SOURCE AS SRC
            WHERE SRC.IMAGES_SK = TGT.IMAGES_SK
                AND SRC.IMAGE_URL = TGT.IMAGE_URL
        )
)

SELECT * FROM ACTIVE
UNION ALL
SELECT * FROM DEACTIVATED

{% endif %}
