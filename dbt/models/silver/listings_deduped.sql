{{
    config(
        unique_key=['LISTING_ID', 'SCRAPE_DATE'],
        partition_by={
            'field': 'SCRAPE_DATE',
            'data_type': 'date'
        },
        cluster_by=['SITE', 'CITY', 'PROPERTY_TYPE', 'PAGE']
    )
}}

{% set scrape_date = var('scrape_date', none) %}
{% set default_text = "'unknown'" %}
{% set default_flag = true %}
{% set default_int = 0 %}
{% set default_array = "[]" %}

WITH SOURCE AS (
    SELECT *
    FROM {{ source('bronze', 'bronze_listings') }}
    WHERE
        DATE(SRC_EXECUTED_AT_TS) = {% if scrape_date %}DATE('{{ scrape_date }}')
    {% else %}CURRENT_DATE{% endif %}
)

SELECT
    ID AS BRONZE_ID,
    LISTING_ID,
    INITCAP(COALESCE(LISTING_NAME, {{ default_text }})) AS LISTING_NAME,
    LISTING_URL AS URL,
    INITCAP(COALESCE(LISTING_DESCRIPTION, {{ default_text }})) AS DESCRIPTION,
    COALESCE(LISTING_PETS_ALLOWED_FLAG, {{ default_flag }}) AS PETS_ALLOWED,
    LISTING_NUMBER_OF_ROOMS_AMT AS ROOMS,
    LISTING_NUMBER_OF_BEDROOMS_AMT AS BEDROOMS,
    LISTING_NUMBER_OF_BATHROOMS_AMT AS BATHROOMS,
    COALESCE(LISTING_ADDRESS_INFOS.STREET_ADDRESS, {{ default_text }}) AS STREET_ADDRESS,
    COALESCE(LISTING_ADDRESS_INFOS.LOCALITY, {{ default_text }}) AS LOCALITY,
    COALESCE(LISTING_ADDRESS_INFOS.REGION, {{ default_text }}) AS REGION,
    COALESCE(LISTING_ADDRESS_INFOS.COUNTRY, {{ default_text }}) AS COUNTRY,
    LISTING_FLOOR_SIZE_INFOS.VALUE AS FLOOR_SIZE,
    COALESCE(LISTING_FLOOR_SIZE_INFOS.UNIT_CODE, {{ default_text }}) AS FLOOR_SIZE_UNIT_CODE,
    COALESCE(LISTING_IMAGES_LIST, {{ default_array }}) AS IMAGES,
    COALESCE(LISTING_AMENITY_FEATURES_INFOS, {{ default_array }}) AS AMENITY_FEATURES,
    LISTING_OFFERS_INFOS.PRICE,
    COALESCE(LISTING_OFFERS_INFOS.PRICE_CURRENCY, {{ default_text }}) AS PRICE_CURRENCY,
    COALESCE(LISTING_OFFERS_INFOS.AVAILABILITY, {{ default_text }}) AS AVAILABILITY,
    COALESCE(LISTING_OFFERS_INFOS.PROPERTY_VALUE.NAME, {{ default_text }}) AS OFFERS_NAME,
    LISTING_OFFERS_INFOS.PROPERTY_VALUE.VALUE AS OFFERS_PRICE,
    COALESCE(
        REGEXP_EXTRACT(LISTING_OFFERS_INFOS.PROPERTY_VALUE.UNIT_TEXT, r'^([A-Za-z]+)'),
        {{ default_text }}
    ) AS OFFERS_PRICE_CURRENCY,
    COALESCE(
        REGEXP_EXTRACT(LISTING_OFFERS_INFOS.PROPERTY_VALUE.UNIT_TEXT, r'/([A-Za-z]+)$'),
        {{ default_text }}
    ) AS OFFERS_PRICE_PERIOD,
    COALESCE(SRC_SITE_NAME, {{ default_text }}) AS SITE,
    COALESCE(SRC_CITY_NAME, {{ default_text }}) AS CITY,
    COALESCE(SRC_PROPERTY_TYPE_CAT, {{ default_text }}) AS PROPERTY_TYPE,
    SRC_PAGE_NUM AS PAGE,
    DATE(SRC_EXECUTED_AT_TS) AS SCRAPE_DATE,
    CURRENT_TIMESTAMP() AS AUD_INS_TS,
    CURRENT_TIMESTAMP() AS AUD_UPD_TS
FROM SOURCE
WHERE LISTING_URL IS NOT NULL
QUALIFY
    ROW_NUMBER() OVER (
        PARTITION BY
            SCRAPE_DATE,
            COALESCE(LISTING_ADDRESS_INFOS.STREET_ADDRESS, {{ default_text }}),
            COALESCE(SRC_PROPERTY_TYPE_CAT, {{ default_text }}),
            CAST(COALESCE(LISTING_FLOOR_SIZE_INFOS.VALUE, {{ default_int }}) AS INT64),
            CAST(COALESCE(LISTING_OFFERS_INFOS.PRICE, {{ default_int }}) AS INT64),
            COALESCE(LISTING_NUMBER_OF_ROOMS_AMT, {{ default_int }}),
            COALESCE(LISTING_NUMBER_OF_BEDROOMS_AMT, {{ default_int }}),
            COALESCE(LISTING_NUMBER_OF_BATHROOMS_AMT, {{ default_int }})
        ORDER BY
            CASE SRC_SITE_NAME
                WHEN 'vivareal' THEN 1
                WHEN 'zapimoveis' THEN 2
                ELSE 3
            END ASC,
            SRC_EXECUTED_AT_TS DESC
    ) = 1
