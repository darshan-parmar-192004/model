"""
Data ingestion modules for Foresight.
"""

from foresight.ingestion.research_scraper import poll_since as research_poll_since
from foresight.ingestion.product_footprint_scraper import ProductFootprintScraper
from foresight.ingestion.macro_signals_scraper import MacroSignalsScraper
# Note: openreview is optional and may not be available due to dependency conflicts