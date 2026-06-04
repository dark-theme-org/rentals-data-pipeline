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

{% set file_date = env_var('FILE_DATE', none) %}
{%- set address_sk_cols = ['STREET_ADDRESS', 'LOCALITY', 'REGION', 'COUNTRY'] -%}
{%- set images_sk_cols = ['IMAGES'] -%}
{%- set images_array_fields = ['IMAGES'] -%}
{%- set amenity_sk_cols = ['AF.NAME', 'AF.VALUE'] -%}
{% set default_int = 0 %}

WITH SOURCE AS (
    SELECT
        *,
        {{ generate_surrogate_key(address_sk_cols) }} AS ADDRESS_SK,
        {{ generate_surrogate_key(images_sk_cols, images_array_fields) }} AS IMAGES_SK
    FROM {{ ref('listings_deduped') }}
    WHERE
        SCRAPE_DATE = {% if file_date %}DATE('{{ file_date }}'){% else %}CURRENT_DATE{% endif %}  -- noqa: LT05
),

AMENITIES AS (
    SELECT
        SRC.LISTING_ID,
        ARRAY_AGG(DISTINCT {{ generate_surrogate_key(amenity_sk_cols) }}) AS AMENITIES_SKS
    FROM SOURCE AS SRC,
        UNNEST(AMENITY_FEATURES) AS AF
    GROUP BY SRC.LISTING_ID
)

SELECT
    SRC.BRONZE_ID,
    SRC.LISTING_ID,
    SRC.ADDRESS_SK,
    SRC.IMAGES_SK,
    AMN.AMENITIES_SKS,
    SRC.SITE,
    SRC.CITY,
    SRC.PROPERTY_TYPE,
    SRC.PAGE,
    SRC.SCRAPE_DATE,
    SRC.PETS_ALLOWED,
    SRC.ROOMS,
    SRC.BEDROOMS,
    SRC.BATHROOMS,
    SRC.FLOOR_SIZE AS FLOOR_SIZE_M2,
    SRC.PRICE AS PRICE_BRL,
    IF(SRC.OFFERS_NAME = 'Condominium Fee', SRC.OFFERS_PRICE, {{ default_int }}) AS CONDO_FEE_BRL,
    CURRENT_TIMESTAMP() AS AUD_INS_TS,
    CURRENT_TIMESTAMP() AS AUD_UPD_TS
FROM SOURCE AS SRC
LEFT JOIN AMENITIES AS AMN ON SRC.LISTING_ID = AMN.LISTING_ID
WHERE SRC.PRICE_CURRENCY = 'BRL'
    AND SRC.FLOOR_SIZE_UNIT_CODE = 'M2'
