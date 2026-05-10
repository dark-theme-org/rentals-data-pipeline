"""Entrypoint: scrape listings from each configured site and upload them to GCS."""

import json
import logging
from collections import namedtuple
from datetime import datetime, timezone
from typing import Dict

from google.cloud import storage

from app.data.scrapers import City, VivaRealScraper, ZapImoveisScraper
from app.utils import Environment, FileExtensions, task
from app.utils.gcs import ScraperBucket

logger = logging.getLogger(__name__)

ScraperMapping = namedtuple("ScraperMapping", ["scraper_class"])
SCRAPER_MAPPING: Dict[str, ScraperMapping] = {
    VivaRealScraper.get_site_name(): ScraperMapping(VivaRealScraper),
    ZapImoveisScraper.get_site_name(): ScraperMapping(ZapImoveisScraper),
}

# -> TODO: Create a RuntimeParameters class to manage parameters. Add validations also.

env = Environment.DEV  # -> TODO: Should be input
city = City.MACAE  # -> TODO: Should be input
sites = ["vivareal", "zapimoveis"]  # -> TODO: Should be input
property_types = ["apartment", "house"]  # -> TODO: Should be input
executed_at = datetime.now(timezone.utc).strftime(
    "%Y-%m-%dT%H-%M-%SZ"
)  # -> TODO: Should be auto-filled
file_extension = FileExtensions.JSON  # -> TODO: Should be auto-filled


@task(label="scraper_data_to_bucket")
def scraper_data_to_bucket() -> None:
    """
    Iterate over every configured ``(site, property_type)`` pair, scrape the
    listings page, and upload the extracted payload as a single JSON blob to
    the matching :class:`ScraperBucket` location.
    """
    gcs_client = storage.Client()
    for site in sites:
        scraper_class = SCRAPER_MAPPING[site].scraper_class
        for property_type in property_types:
            logger.info(f"Scrapping for site '{site}' and property_type '{property_type}'...")
            scraper = scraper_class(city).set_url(property_type).fetch_and_parse_html()
            properties_dict = scraper.extract_properties()
            scraper_bucket = ScraperBucket(
                env=env,
                site=scraper.get_site_name(),
                city=city,
                property_type=property_type,
            )
            blob_name = scraper_bucket.blob_name(filename=executed_at, extension=file_extension)
            logger.info(f"Uploading '{file_extension}' files to '{scraper_bucket.prefix}'.")
            gcs_client.bucket(scraper_bucket.name).blob(blob_name).upload_from_string(
                json.dumps(properties_dict, ensure_ascii=False, indent=2),
                content_type="application/json",
            )
            logger.info(f"Upload completed! Full path: {blob_name}")
            logger.info(f"Finished scrape for site '{site}' and property_type '{property_type}'.")


if __name__ == "__main__":
    scraper_data_to_bucket()
