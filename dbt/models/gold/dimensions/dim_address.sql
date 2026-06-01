{{
    config(
        unique_key='ADDRESS_SK',
        partition_by={
            'field': 'AUD_UPD_TS',
            'data_type': 'timestamp',
            'granularity': 'day'
        },
        cluster_by=['LOCALITY', 'REGION', 'COUNTRY', 'IN_LAST_SCRAPE_FLAG']
    )
}}

{%- set address_sk_cols = ['STREET_ADDRESS', 'LOCALITY', 'REGION', 'COUNTRY'] -%}

{% if not is_incremental() %}

SELECT
    {{ generate_surrogate_key(address_sk_cols) }} AS ADDRESS_SK,
    STREET_ADDRESS,
    LOCALITY,
    REGION,
    COUNTRY,
    TRUE AS IN_LAST_SCRAPE_FLAG,
    CURRENT_TIMESTAMP() AS AUD_INS_TS,
    CURRENT_TIMESTAMP() AS AUD_UPD_TS
FROM {{ ref('listings_deduped') }}
QUALIFY ROW_NUMBER() OVER (
    PARTITION BY ADDRESS_SK
    ORDER BY SCRAPE_DATE DESC
) = 1

{% else %}

WITH SOURCE AS (
    SELECT DISTINCT
        {{ generate_surrogate_key(address_sk_cols) }} AS ADDRESS_SK,
        STREET_ADDRESS,
        LOCALITY,
        REGION,
        COUNTRY
    FROM {{ ref('listings_deduped') }}
    QUALIFY SCRAPE_DATE = MAX(SCRAPE_DATE) OVER ()
),

ACTIVE AS (
    SELECT
        SRC.ADDRESS_SK,
        SRC.STREET_ADDRESS,
        SRC.LOCALITY,
        SRC.REGION,
        SRC.COUNTRY,
        TRUE AS IN_LAST_SCRAPE_FLAG,
        COALESCE(TGT.AUD_INS_TS, CURRENT_TIMESTAMP()) AS AUD_INS_TS,
        CURRENT_TIMESTAMP() AS AUD_UPD_TS
    FROM SOURCE AS SRC
    LEFT JOIN {{ this }} AS TGT ON SRC.ADDRESS_SK = TGT.ADDRESS_SK
),

DEACTIVATED AS (
    SELECT
        TGT.ADDRESS_SK,
        TGT.STREET_ADDRESS,
        TGT.LOCALITY,
        TGT.REGION,
        TGT.COUNTRY,
        FALSE AS IN_LAST_SCRAPE_FLAG,
        TGT.AUD_INS_TS,
        CURRENT_TIMESTAMP() AS AUD_UPD_TS
    FROM {{ this }} AS TGT
    WHERE TGT.IN_LAST_SCRAPE_FLAG = TRUE
        AND NOT EXISTS (
            SELECT 1
            FROM SOURCE AS SRC
            WHERE SRC.ADDRESS_SK = TGT.ADDRESS_SK
        )
)

SELECT * FROM ACTIVE
UNION ALL
SELECT * FROM DEACTIVATED

{% endif %}
