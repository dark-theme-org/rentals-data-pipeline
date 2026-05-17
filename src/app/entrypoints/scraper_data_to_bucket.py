"""Entrypoint: scrape listings from each configured site and upload them to GCS."""

import json
import logging
import random
import time
from collections import namedtuple
from typing import Dict

from google.cloud import storage

from app.data.scrapers import VivaRealScraper, ZapImoveisScraper
from app.utils import (
    CloudSettings,
    configure_logging,
    get_credentials,
    task,
)
from app.utils.gcs import ScraperBucket
from app.utils.validations import ScraperParameters

logger = logging.getLogger(__name__)
configure_logging()

ScraperMapping = namedtuple("ScraperMapping", ["scraper_class"])
SCRAPER_MAPPING: Dict[str, ScraperMapping] = {
    VivaRealScraper.get_site_name(): ScraperMapping(VivaRealScraper),
    ZapImoveisScraper.get_site_name(): ScraperMapping(ZapImoveisScraper),
}

params = ScraperParameters.from_env()


@task(label="scraper_data_to_bucket")
def scraper_data_to_bucket() -> None:
    """
    Iterate over every configured ``(site, property_type)`` pair, scrape the
    listings page, and upload the extracted payload as a single JSON blob to
    the matching :class:`ScraperBucket` location.
    """
    gcs_client = storage.Client(
        credentials=get_credentials(params.sa_name),
        project=CloudSettings.PROJECT_ID,
    )
    for site in params.sites:
        scraper_class = SCRAPER_MAPPING[site].scraper_class
        for property_type in params.property_types:
            logger.info(f"Scrapping for site '{site}' and property_type '{property_type}'...")
            scraper = scraper_class(params.city).set_url(property_type)
            page = params.start_page
            while True:
                if params.max_page is not None and page > params.max_page:
                    logger.info(
                        f"Reached max_page={params.max_page} for site '{site}' "
                        f"and property_type '{property_type}'."
                    )
                    break
                page_result = scraper.fetch_and_parse_html(page=page)
                if page_result is None:
                    logger.info(
                        f"Finished scrape for site '{site}' and property_type '{property_type}'."
                    )
                    break
                properties_dict = page_result.extract_properties()
                if not params.upload_to_gcs:
                    logger.info(
                        f"GCS upload skipped! Parameter was set as {params.upload_to_gcs})."
                    )
                    time.sleep(random.uniform(1.0, 3.0))  # Help avoiding HTTP Error 403!
                    page += 1
                    continue
                scraper_bucket = ScraperBucket(
                    env=params.environment,
                    site=scraper.get_site_name(),
                    city=params.city,
                    property_type=property_type,
                    page=page,
                )
                blob_name = scraper_bucket.blob_name(
                    filename=params.executed_at, extension=params.file_extension
                )
                logger.info(
                    f"Uploading '{params.file_extension}' files to '{scraper_bucket.prefix}'."
                )
                gcs_client.bucket(scraper_bucket.name).blob(blob_name).upload_from_string(
                    json.dumps(properties_dict, ensure_ascii=False, indent=2),
                    content_type="application/json",
                )
                logger.info(f"Upload completed! Full path: {blob_name}")
                time.sleep(random.uniform(1.0, 3.0))  # Help avoiding HTTP Error 403!
                page += 1


if __name__ == "__main__":
    scraper_data_to_bucket()
