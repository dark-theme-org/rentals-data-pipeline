{{
    config(
        unique_key='LISTING_ID',
        partition_by={
            'field': 'AUD_UPD_TS',
            'data_type': 'timestamp',
            'granularity': 'day'
        },
        cluster_by=['IN_LAST_SCRAPE_FLAG']
    )
}}

{% if not is_incremental() %}

SELECT
    LISTING_ID,
    LISTING_NAME,
    URL,
    DESCRIPTION,
    TRUE AS IN_LAST_SCRAPE_FLAG,
    CURRENT_TIMESTAMP() AS AUD_INS_TS,
    CURRENT_TIMESTAMP() AS AUD_UPD_TS
FROM {{ ref('listings_deduped') }}
QUALIFY ROW_NUMBER() OVER (
    PARTITION BY LISTING_ID
    ORDER BY SCRAPE_DATE DESC
) = 1

{% else %}

WITH SOURCE AS (
    SELECT DISTINCT
        LISTING_ID,
        LISTING_NAME,
        URL,
        DESCRIPTION
    FROM {{ ref('listings_deduped') }}
    QUALIFY SCRAPE_DATE = MAX(SCRAPE_DATE) OVER ()
),

ACTIVE AS (
    SELECT
        SRC.LISTING_ID,
        SRC.LISTING_NAME,
        SRC.URL,
        SRC.DESCRIPTION,
        TRUE AS IN_LAST_SCRAPE_FLAG,
        COALESCE(TGT.AUD_INS_TS, CURRENT_TIMESTAMP()) AS AUD_INS_TS,
        CURRENT_TIMESTAMP() AS AUD_UPD_TS
    FROM SOURCE AS SRC
    LEFT JOIN {{ this }} AS TGT ON SRC.LISTING_ID = TGT.LISTING_ID
),

DEACTIVATED AS (
    SELECT
        TGT.LISTING_ID,
        TGT.LISTING_NAME,
        TGT.URL,
        TGT.DESCRIPTION,
        FALSE AS IN_LAST_SCRAPE_FLAG,
        TGT.AUD_INS_TS,
        CURRENT_TIMESTAMP() AS AUD_UPD_TS
    FROM {{ this }} AS TGT
    WHERE TGT.IN_LAST_SCRAPE_FLAG = TRUE
        AND NOT EXISTS (
            SELECT 1
            FROM SOURCE AS SRC
            WHERE SRC.LISTING_ID = TGT.LISTING_ID
        )
)

SELECT * FROM ACTIVE
UNION ALL
SELECT * FROM DEACTIVATED

{% endif %}
