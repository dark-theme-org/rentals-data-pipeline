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
{%- set address_sk_cols = ['LISTING_ID', 'STREET_ADDRESS'] -%}
{%- set images_sk_cols = ['LISTING_ID', 'IMAGES'] -%}
{%- set amenity_sk_cols = ['LISTING_ID', 'AMENITY_FEATURES'] -%}

WITH SOURCE AS (
    SELECT *
    FROM {{ ref('listings_deduped') }}
    WHERE
        SCRAPE_DATE = {% if file_date %}DATE('{{ file_date }}'){% else %}CURRENT_DATE{% endif %}  -- noqa: LT05
)

SELECT
    BRONZE_ID,
    LISTING_ID,
    {{ generate_surrogate_key(address_sk_cols) }} AS ADDRESS_SK,
    {{ generate_surrogate_key(images_sk_cols) }} AS IMAGES_SK,
    {{ generate_surrogate_key(amenity_sk_cols) }} AS AMENITIES_SK,
    SITE,
    CITY,
    PROPERTY_TYPE,
    PAGE,
    SCRAPE_DATE,
    PETS_ALLOWED,
    ROOMS,
    BEDROOMS,
    BATHROOMS,
    IF(FLOOR_SIZE_UNIT_CODE = 'M2', FLOOR_SIZE, NULL) AS FLOOR_SIZE_M2,
    IF(PRICE_CURRENCY = 'BRL', PRICE, NULL) AS PRICE_BRL,
    IF(OFFERS_NAME = 'Condominium Fee', OFFERS_PRICE, NULL) AS CONDO_FEE_BRL,
    CURRENT_TIMESTAMP() AS AUD_INS_TS,
    CURRENT_TIMESTAMP() AS AUD_UPD_TS
FROM SOURCE
