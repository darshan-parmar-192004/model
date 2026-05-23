#!/usr/bin/env python3
"""
Macro signals scraper for Project Foresight.
Monitors SEC EDGAR for filings related to compute/AI infrastructure.
"""

import requests
import time
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import re
from bs4 import BeautifulSoup

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Kafka producer (optional, for streaming)
try:
    from kafka import KafkaProducer
    import json
    producer = KafkaProducer(
        bootstrap_servers=['localhost:9092'],
        value_serializer=lambda v: json.dumps(v).encode('utf-8')
    )
    KAFKA_AVAILABLE = True
except Exception as e:
    logger.warning(f"Kafka not available: {e}. Events will be logged but not streamed.")
    KAFKA_AVAILABLE = False
    producer = None

class MacroSignalsScraper:
    def __init__(self):
        """
        Initialize the SEC EDGAR scraper.
        """
        # SEC EDGAR base URLs
        self.BASE_URL = "https://www.sec.gov/cgi-bin/browse-edgar"
        self.SEARCH_URL = "https://www.sec.gov/edgar/search/"
        
        # Required headers for SEC EDGAR (as per their usage policy)
        self.HEADERS = {
            'User-Agent': 'Foresight Research (foresight@research.dev)',
            'Accept-Encoding': 'gzip, deflate',
            'Host': 'www.sec.gov'
        }
        
        # Target companies (CIK numbers) - Amazon, Microsoft, Google/Alphabet
        self.TARGET_COMPANIES = {
            'AMZN': '0001018724',   # Amazon.com Inc
            'MSFT': '0000789019',   # Microsoft Corp
            'GOOGL': '0001652044',  # Alphabet Inc (Google)
            'META': '0001326801',   # Meta Platforms Inc (Facebook)
            'NVDA': '0001045810',   # NVIDIA Corp
        }
        
        # Keywords to search for in filings
        self.KEYWORDS = [
            "GPU", "data center", "compute", "infrastructure", 
            "capital expenditure", "AI", "machine learning", 
            "artificial intelligence", "training", "cluster", 
            "TPU", "accelerator", "H100", "A100", "B100", "Blackwell", "Hopper"
        ]
        
        # Filing types we're interested in
        self.FILING_TYPES = ["10-K", "10-Q", "8-K", "6-K", "20-F", "40-F"]
        
        # Rate limiting: SEC allows 10 requests per second
        self.REQUEST_DELAY = 0.1  # 100ms between requests

    def _make_request(self, url: str, params: Optional[Dict] = None) -> Optional[requests.Response]:
        """
        Make a request to SEC EDGAR with rate limiting and error handling.
        """
        time.sleep(self.REQUEST_DELAY)  # Rate limiting
        
        try:
            response = requests.get(url, headers=self.HEADERS, params=params, timeout=30)
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed for {url}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error requesting {url}: {e}")
            return None

    def _parse_filing_index(self, cik: str, filing_type: str, since: datetime) -> List[Dict]:
        """
        Parse SEC EDGAR index for a specific company and filing type.
        Returns list of filing metadata.
        """
        filings = []
        
        # Construct URL for company filings
        # Format: https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=0001018724&type=10-K&dateb=&owner=exclude&count=100
        params = {
            'action': 'getcompany',
            'CIK': cik,
            'type': filing_type,
            'dateb': '',  # Empty for all dates
            'owner': 'exclude',
            'count': '100'  # Get up to 100 filings
        }
        
        response = self._make_request(self.BASE_URL, params)
        if not response:
            return filings
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Find the table with filing information
        table = soup.find('table', class_='tableFile2')
        if not table:
            logger.warning(f"No filing table found for CIK {cik}, type {filing_type}")
            return filings
        
        # Parse each row in the table
        rows = table.find_all('tr')
        for row in rows[1:]:  # Skip header row
            cols = row.find_all('td')
            if len(cols) < 5:
                continue
            
            # Extract filing details
            filing_type_col = cols[0].get_text(strip=True)
            filing_date_col = cols[3].get_text(strip=True)
            filing_link_col = cols[1].find('a', href=True)
            
            if not filing_link_col:
                continue
            
            try:
                filing_date = datetime.strptime(filing_date_col, '%Y-%m-%d')
            except ValueError:
                # Try different date format if needed
                try:
                    filing_date = datetime.strptime(filing_date_col, '%m/%d/%Y')
                except ValueError:
                    logger.warning(f"Could not parse date: {filing_date_col}")
                    continue
            
            # Skip if older than since date
            if filing_date < since:
                continue
            
            # Construct URLs
            relative_link = filing_link_col['href']
            if not relative_link.startswith('http'):
                filing_url = f"https://www.sec.gov{relative_link}"
            else:
                filing_url = relative_link
            
            # Get the documents page for this filing
            documents_url = filing_url
            
            filing_info = {
                'cik': cik,
                'filing_type': filing_type_col,
                'filing_date': filing_date.isoformat(),
                'filing_url': filing_url,
                'documents_url': documents_url,
                'description': cols[4].get_text(strip=True) if len(cols) > 4 else ''
            }
            filings.append(filing_info)
        
        return filings

    def _analyze_filing_for_keywords(self, filing_url: str) -> Dict:
        """
        Analyze a specific filing for keywords and return matches.
        """
        # First, get the filing's index page to find the actual document
        response = self._make_request(filing_url)
        if not response:
            return {'matches': [], 'keyword_count': 0, 'confidence': 0.0}
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Find links to actual documents (HTML, TXT, XML)
        doc_links = []
        table = soup.find('table', class_='tableFile')
        if table:
            rows = table.find_all('tr')
            for row in rows[1:]:  # Skip header
                cols = row.find_all('td')
                if len(cols) >= 3:
                    link_col = cols[2]
                    if link_col:
                        link = link_col.find('a', href=True)
                        if link and link.get_text(strip=True) in ['HTML', 'TXT', 'XML']:
                            href = link['href']
                            if not href.startswith('http'):
                                href = f"https://www.sec.gov{href}"
                            doc_links.append((
                                href,
                                link.get_text(strip=True),
                                cols[0].get_text(strip=True)  # Description
                            ))
        
        # If no document links found, construct the proper SEC document URL
        # SEC filing URLs: https://www.sec.gov/Archives/edgar/data/{cik}/{accession_nodash}/{accession}.txt
        if not doc_links:
            # Extract CIK and accession from the filing URL
            # URL format: https://www.sec.gov/Archives/edgar/data/{cik}/{accession_nodash}/{accession}-index.html
            try:
                parts = filing_url.split('/')
                if len(parts) >= 7:
                    cik = parts[-3]
                    accession_nodash_dir = parts[-2]
                    # The accession in the file should have dashes (e.g., 0001018724-24-000005)
                    # The directory name doesn't have dashes (000101872424000005)
                    # Reconstruct: add dashes at positions 10 and 12
                    if len(accession_nodash_dir) == 18:
                        accession_with_dashes = f"{accession_nodash_dir[:10]}-{accession_nodash_dir[10:12]}-{accession_nodash_dir[12:]}"
                    else:
                        accession_with_dashes = accession_nodash_dir
                    
                    base = f"https://www.sec.gov/Archives/edgar/data/{cik}/{accession_nodash_dir}/{accession_with_dashes}"
                    doc_links = [
                        (f"{base}.txt", "TXT", "Text document"),
                        (f"{base}.htm", "HTML", "HTML document")
                    ]
            except Exception as e:
                logger.warning(f"Could not construct document URL from {filing_url}: {e}")
        
        # Analyze each document for keywords
        total_matches = []
        for doc_url, doc_type, description in doc_links[:2]:  # Limit to first 2 documents to avoid too many requests
            matches = self._scan_document_for_keywords(doc_url)
            total_matches.extend(matches)
            # Be nice to SEC servers - small delay between document requests
            time.sleep(self.REQUEST_DELAY)
        
        # Calculate confidence based on number and quality of matches
        keyword_count = len(total_matches)
        if keyword_count > 0:
            # Boost confidence for multiple matches or specific high-value keywords
            high_value_keywords = ['GPU', 'data center', 'capital expenditure', 'AI', 'training']
            high_value_matches = [m for m in total_matches if m['keyword'].lower() in [k.lower() for k in high_value_keywords]]
            confidence = min(0.95, 0.5 + (keyword_count * 0.1) + (len(high_value_matches) * 0.15))
        else:
            confidence = 0.0
        
        return {
            'matches': total_matches,
            'keyword_count': keyword_count,
            'confidence': confidence
        }

    def _scan_document_for_keywords(self, doc_url: str) -> List[Dict]:
        """
        Scan a document (HTML/TXT) for keyword matches.
        """
        matches = []
        
        response = self._make_request(doc_url)
        if not response:
            return matches
        
        # For text content, we'll search the raw text
        text = response.text
        
        # Limit the amount of text we process to avoid memory issues
        # SEC filings can be very large, so we'll search the first 500k characters
        search_text = text[:500000].lower() if len(text) > 500000 else text.lower()
        
        for keyword in self.KEYWORDS:
            # Case-insensitive search
            pattern = re.compile(re.escape(keyword.lower()), re.IGNORECASE)
            for match in pattern.finditer(search_text):
                # Extract context around the match
                start = max(0, match.start() - 200)
                end = min(len(text), match.end() + 200)
                context = text[start:end]
                
                matches.append({
                    'keyword': keyword,
                    'context': context.strip(),
                    'position': match.start()
                })
        
        return matches

    def poll(self, since: Optional[datetime] = None) -> List[Dict]:
        """
        Poll SEC EDGAR for new filings since the given timestamp.
        If since is None, defaults to last 30 days.
        Returns list of SignalEvent dictionaries.
        """
        if since is None:
            since = datetime.utcnow() - timedelta(days=30)
        
        events = []
        
        # For each target company and filing type
        for company_name, cik in self.TARGET_COMPANIES.items():
            for filing_type in self.FILING_TYPES:
                try:
                    logger.info(f"Checking {company_name} ({cik}) for {filing_type} filings since {since}")
                    
                    # Get list of filings
                    filings = self._parse_filing_index(cik, filing_type, since)
                    
                    for filing in filings:
                        # Analyze the filing for keywords
                        analysis = self._analyze_filing_for_keywords(filing['filing_url'])
                        
                        # Only create an event if we found relevant keywords
                        if analysis['keyword_count'] > 0:
                            # Create a summary of matches for the content
                            matches_summary = "; ".join([
                                f"{m['keyword']}: {m['context'][:100]}..." 
                                for m in analysis['matches'][:3]  # Top 3 matches
                            ])
                            
                            event = {
                                "id": f"sec_{cik}_{filing_type}_{filing['filing_date']}_{hash(filing['filing_url']) & 0xffffffff}",
                                "timestamp": filing['filing_date'],
                                "stream": "macro",
                                "signal_type": "filing",
                                "confidence": analysis['confidence'],
                                "content_raw": f"{company_name} {filing_type} filing ({filing['filing_date']}): {matches_summary}",
                                "entities": [company_name],
                                "source_url": filing['filing_url'],
                                "metadata": {
                                    "cik": cik,
                                    "company_name": company_name,
                                    "filing_type": filing_type,
                                    "filing_date": filing['filing_date'],
                                    "filing_url": filing['filing_url'],
                                    "documents_url": filing['documents_url'],
                                    "description": filing['description'],
                                    "keyword_matches": analysis['matches'],
                                    "keyword_count": analysis['keyword_count']
                                }
                            }
                            events.append(event)
                            
                            logger.info(f"Found {analysis['keyword_count']} keyword matches in {company_name} {filing_type} from {filing['filing_date']}")
                
                except Exception as e:
                    logger.error(f"Error processing {company_name} {filing_type}: {e}")
                    continue
        
        # Stream to Kafka if available
        if KAFKA_AVAILABLE and producer:
            for event in events:
                try:
                    producer.send('tech_intel_stream', value=event)
                except Exception as e:
                    logger.error(f"Failed to send to Kafka: {e}")
        
        logger.info(f"Found {len(events)} new macro signal events since {since}")
        return events

def run_continuous_polling(interval_seconds: int = 3600):  # 1 hour
    """
    Run continuous polling at the given interval.
    """
    scraper = MacroSignalsScraper()
    logger.info("Starting continuous polling for macro signals (SEC EDGAR)...")
    last_poll = datetime.utcnow() - timedelta(days=1)  # Start by looking at last day
    
    while True:
        try:
            events = scraper.poll(since=last_poll)
            if events:
                logger.info(f"Polled {len(events)} new macro signal events")
                # In a real system, we would save these to a database or message queue
                # For now, we just log
                for event in events[:5]:  # Log first 5
                    logger.info(f"  - {event['content_raw'][:100]}...")
            last_poll = datetime.utcnow()
            time.sleep(interval_seconds)
        except KeyboardInterrupt:
            logger.info("Stopping continuous polling.")
            break
        except Exception as e:
            logger.error(f"Error in continuous polling: {e}")
            time.sleep(60)  # Wait a minute before retrying

if __name__ == "__main__":
    # Run a single poll for testing
    events = poll()
    print(f"Found {len(events)} events")
    for event in events[:3]:
        print(f"- {event['content_raw']}")