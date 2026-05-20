/*
 * create_bronze_listings_table.sql
 *
 * Creates the Bronze layer table for scraped real-estate rental listings.
 *
 * Purpose:
 *   Idempotent DDL executed by the gcs_to_bigquery_bronze task before each
 *   load run. The table is append-only — rows are never updated or deleted at
 *   this layer. Deduplication and transformation happen in Silver (dbt).
 *
 * Destination:
 *   Resolved at runtime by BronzeListingsTable.destination
 *   (e.g. "my-project.dev_bronze.listings")
 *
 * Column groups:
 *   LISTING_*      — fields sourced directly from the scraped JSON (schema.org).
 *   SRC_*          — source lineage columns mirroring the GCS path structure:
 *                    SRC_BLOB / SRC_SITE / SRC_CITY / SRC_PROPERTY_TYPE /
 *                    SRC_PAGE / SRC_EXECUTED_AT
 *   AUD_*          — warehouse audit columns set by the load job:
 *                    AUD_VERSION / AUD_INS_DTTM / AUD_UPD_DTTM
 *
 * Partitioning:  DATE(SRC_EXECUTED_AT)  — one partition per scraper run date.
 * Clustering:    SRC_SITE, SRC_CITY, SRC_PROPERTY_TYPE, SRC_PAGE
 */
CREATE TABLE IF NOT EXISTS `{{ destination }}` (
    ID STRING NOT NULL DEFAULT GENERATE_UUID() OPTIONS (
        description = "Surrogate key generated at row insertion."
    ),
    LISTING_ID STRING NOT NULL OPTIONS (
        description = "Unique listing identifier from the source site (schema.org @id)."
    ),
    LISTING_NAME STRING OPTIONS (description = "Full listing title as scraped from the site."),
    LISTING_URL STRING OPTIONS (description = "Canonical URL of the listing on the source site."),
    LISTING_DESCRIPTION STRING OPTIONS (
        description = "Free-text property description provided by the advertiser."
    ),
    LISTING_PETS_ALLOWED BOOL OPTIONS (description = "Whether the listing explicitly allows pets."),
    LISTING_NUMBER_OF_ROOMS INT64 OPTIONS (
        description = "Total number of rooms reported by the listing."
    ),
    LISTING_NUMBER_OF_BEDROOMS INT64 OPTIONS (
        description = "Number of bedrooms reported by the listing."
    ),
    LISTING_NUMBER_OF_BATHROOMS_TOTAL INT64 OPTIONS (
        description = "Total number of bathrooms reported by the listing."
    ),
    LISTING_ADDRESS STRUCT<
        STREET_ADDRESS STRING,
        LOCALITY STRING,
        REGION STRING,
        COUNTRY STRING
    > OPTIONS (
        description = "Postal address as reported by the listing. STREET_ADDRESS may be absent."
    ),
    LISTING_FLOOR_SIZE STRUCT<
        VALUE FLOAT64,
        UNIT_CODE STRING
    > OPTIONS (
        description = "Floor area with its unit (UNIT_CODE is always 'M2' for current sources)."
    ),
    LISTING_IMAGES ARRAY<STRING> OPTIONS (
        description = "Ordered list of image URLs associated with the listing."
    ),
    LISTING_AMENITY_FEATURES ARRAY<STRUCT<
        NAME STRING,
        VALUE STRING
    >> OPTIONS (
        description = "List of amenity features declared by the listing (e.g. 'Pool', 'Gym')."
    ),
    LISTING_OFFERS STRUCT<
        PRICE FLOAT64,
        PRICE_CURRENCY STRING,
        AVAILABILITY STRING,
        POTENTIAL_ACTION STRUCT<
            TARGET STRING,
            PRICE_SPECIFICATION STRUCT<
                PRICE FLOAT64,
                PRICE_CURRENCY STRING
            >
        >,
        PROPERTY_VALUE STRUCT<
            NAME STRING,
            VALUE FLOAT64,
            UNIT_TEXT STRING
        >
    > OPTIONS (
        description
        = "Pricing information. PROPERTY_VALUE carries the condominium fee when present."
    ),
    SRC_BLOB STRING OPTIONS (
        description
        = "Full GCS blob path the row was loaded from "
        || "(e.g. 'dev/vivareal/macae/apartment/1/2026-01-01T00-00-00Z.json')."
    ),
    SRC_SITE STRING OPTIONS (
        description = "Source site identifier (e.g. 'vivareal', 'zapimoveis')."
    ),
    SRC_CITY STRING OPTIONS (description = "City slug used in the scraper run (e.g. 'macae')."),
    SRC_PROPERTY_TYPE STRING OPTIONS (
        description = "Search filter used to collect this listing (e.g. 'apartment', 'house')."
    ),
    SRC_PAGE INT64 OPTIONS (description = "Pagination page number the listing was collected from."),
    SRC_EXECUTED_AT TIMESTAMP OPTIONS (
        description = "UTC timestamp of the scraper run, parsed from the GCS blob filename."
    ),
    AUD_VERSION STRING OPTIONS (
        description
        = "Pipeline version that produced this row "
        || "(Cloud Run image tag or declared version for local runs)."
    ),
    AUD_INS_DTTM TIMESTAMP OPTIONS (
        description = "Timestamp when this row was inserted into BigQuery."
    ),
    AUD_UPD_DTTM TIMESTAMP OPTIONS (description = "Timestamp when this row was last updated.")
)
PARTITION BY DATE(SRC_EXECUTED_AT)
CLUSTER BY SRC_SITE, SRC_CITY, SRC_PROPERTY_TYPE, SRC_PAGE
OPTIONS (
    description = (
        "Bronze layer for scraped real-estate rental listings. "
        || "One row per listing per scrape run — append-only, no deduplication. "
        || "Partitioned by scraper execution date, clustered by site/city/property_type."
    )
);
