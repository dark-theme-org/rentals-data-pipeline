"""Entrypoint: load scraped listings from GCS into BigQuery bronze layer."""

import json
import logging

from google.cloud import bigquery, storage

from app.data.bigquery import AuditMetadata, BronzeListingsTable
from app.data.gcs import ScraperBucket
from app.utils import (
    BronzeParameters,
    configure_logging,
    get_credentials,
    task,
)

logger = logging.getLogger(__name__)
configure_logging()

params = BronzeParameters.from_env()


@task(label="gcs_to_bigquery_bronze")
def gcs_to_bigquery_bronze() -> None:
    """
    For each configured (site, property_type) pair, download all scraped JSON blobs
    from GCS and load the flattened listings into the BigQuery Bronze table.
    """
    credentials = get_credentials()
    bq_client = bigquery.Client(
        project=params.project_id,
        credentials=credentials,
        location=params.location,
    )
    table = BronzeListingsTable(env=params.environment, project=params.project_id)
    if not table.exists(bq_client):
        table.create(bq_client)
    gcs_client = storage.Client(credentials=credentials, project=params.project_id)
    for site in params.sites:
        for property_type in params.property_types:
            logger.info(f"Processing site='{site}', property_type='{property_type}'...")
            page = params.start_page
            while True:
                if params.max_page is not None and page > params.max_page:
                    logger.info(
                        f"Reached max_page={params.max_page} for site '{site}' "
                        f"and property_type '{property_type}'."
                    )
                    break
                scraper_bucket = ScraperBucket(
                    env=params.environment,
                    site=site,
                    city=params.city,
                    property_type=property_type,
                    page=page,
                )
                blob = scraper_bucket.latest_blob(
                    gcs_client,
                    filename=params.file_date,
                    extension=params.file_extension,
                )
                if blob is None:
                    logger.info(
                        f"No blob for page={page}, FILE_DATE='{params.file_date}' "
                        f"under '{scraper_bucket.prefix}'. Stopping."
                    )
                    break
                if table.blob_already_loaded(
                    bq_client,
                    blob_name=blob.name,
                    executed_at=params.file_date,
                ):
                    logger.info(
                        f"Skipping already-loaded blob '{blob.name}' for "
                        f"site='{site}', property_type='{property_type}'."
                    )
                    page += 1
                    continue
                listings = json.loads(blob.download_as_text(encoding="utf-8"))
                rows = [
                    table.row_schema(
                        listing,
                        src=BronzeListingsTable.SourceMetadata(
                            blob=blob.name,
                            site_name=scraper_bucket.site,
                            city_name=scraper_bucket.city,
                            property_type_cat=scraper_bucket.property_type,
                            page_num=scraper_bucket.page,
                        ),
                        aud=AuditMetadata(
                            version_id=params.version,
                            ins_ts=params.executed_at,
                            upd_ts=params.executed_at,
                        ),
                    )
                    for listing in listings.values()
                ]
                if not params.upload_to_bq:
                    logger.info(
                        f"BQ upload skipped (UPLOAD_TO_BQ=false). "
                        f"Would load {len(rows)} rows into '{table.destination}'."
                    )
                    continue
                logger.info(f"Loading {len(rows)} rows into '{table.destination}'...")
                bq_client.load_table_from_json(
                    rows, table.destination, job_config=table.load_job_config
                ).result()
                logger.info(f"Loaded rows for site='{site}', property_type='{property_type}'.")
                page += 1


if __name__ == "__main__":
    gcs_to_bigquery_bronze()
