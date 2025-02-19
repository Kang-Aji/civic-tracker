import requests
import feedparser
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from dateutil import parser
from models import db, OfficialAction, ActionSource
import logging
from flask_caching import Cache
from typing import List, Dict, Optional, Any
import re
from concurrent.futures import ThreadPoolExecutor
import time

logger = logging.getLogger(__name__)

class ActionTracker:
    """Service for tracking actions of elected officials"""
    
    def __init__(self, app, cache: Cache, congress_api_key: str = None):
        self.app = app
        self.cache = cache
        self.congress_api_key = congress_api_key
        self.session = requests.Session()

    def _get_congress_member_id(self, name: str) -> Optional[str]:
        """Get Congress.gov member ID for a given name"""
        if not self.congress_api_key:
            logger.error("No Congress.gov API key provided")
            return None
            
        try:
            # Search for member by name
            offset = 0
            limit = 20
            
            # Break down name into parts and create variations
            name_parts = name.split()
            name_variations = [
                name.lower(),  # Full name
                ' '.join(reversed(name_parts)).lower(),  # Last name, First name
                name_parts[-1].lower(),  # Just last name
                f"{name_parts[-1]}, {name_parts[0]}".lower() if len(name_parts) > 1 else name_parts[0].lower(),  # Last, First
            ]
            
            # Known member IDs to help speed up search
            member_ids = {
                'Chuck Schumer': 'S000148',
                'Alexandria Ocasio-Cortez': 'O000172',
                'Mitch McConnell': 'M000355',
                'Nancy Pelosi': 'P000197',
                'Jim Jordan': 'J000289',
                'Elizabeth Warren': 'W000817',
                'Ted Cruz': 'C001098'
            }
            
            # Check if we have a known ID
            if name in member_ids:
                return member_ids[name]
                
            # Search Congress.gov API
            url = f"https://api.congress.gov/v3/member"
            params = {
                'api_key': self.congress_api_key,
                'format': 'json',
                'offset': offset,
                'limit': limit
            }
            
            response = self.session.get(url, params=params)
            if response.status_code != 200:
                logger.error(f"Error searching Congress.gov API: {response.status_code}")
                return None
                
            data = response.json()
            members = data.get('members', [])
            
            # Search through members for a name match
            for member in members:
                member_name = member.get('name', '').lower()
                if any(variation in member_name for variation in name_variations):
                    return member.get('bioguideId')
                    
            return None
            
        except Exception as e:
            logger.error(f"Error getting Congress member ID for {name}: {str(e)}")
            return None

    def fetch_official_actions(self, name: str, sources: List[ActionSource]) -> List[Dict[str, Any]]:
        """Fetch actions for a specific official from various sources"""
        actions = []
        
        try:
            # Group sources by type
            source_types = {}
            for source in sources:
                if source.source_type not in source_types:
                    source_types[source.source_type] = []
                source_types[source.source_type].append(source)
            
            # Use ThreadPoolExecutor for parallel fetching
            with ThreadPoolExecutor(max_workers=3) as executor:
                futures = []
                
                # Congress.gov API
                if 'congress_api' in source_types:
                    member_id = self._get_congress_member_id(name)
                    if member_id:
                        futures.append(executor.submit(self._fetch_congress_actions, member_id))
                
                # Press releases
                if 'press_release' in source_types:
                    for source in source_types['press_release']:
                        futures.append(executor.submit(self._fetch_press_releases, source.source_url))
                
                # News mentions
                if 'news' in source_types:
                    for source in source_types['news']:
                        futures.append(executor.submit(self._fetch_news_mentions, name, source.source_url))
                
                # Collect results
                for future in futures:
                    try:
                        result = future.result(timeout=30)
                        if result:
                            actions.extend(result)
                    except Exception as e:
                        logger.error(f"Error fetching actions: {str(e)}")
            
            # Sort actions by date
            actions.sort(key=lambda x: x['date'], reverse=True)
            
            return actions
            
        except Exception as e:
            logger.error(f"Error fetching actions for {name}: {str(e)}")
            return []

    def _fetch_congress_actions(self, member_id: str) -> List[Dict[str, Any]]:
        """Fetch actions from Congress.gov API"""
        actions = []
        
        try:
            # Fetch recent bills sponsored
            url = f"https://api.congress.gov/v3/member/{member_id}/sponsored-legislation"
            params = {
                'api_key': self.congress_api_key,
                'format': 'json',
                'limit': 50
            }
            
            response = self.session.get(url, params=params)
            if response.status_code != 200:
                logger.error(f"Error fetching Congress.gov API: {response.status_code}")
                return actions
                
            data = response.json()
            bills = data.get('sponsoredLegislation', [])
            
            for bill in bills:
                try:
                    # Get bill details
                    bill_url = f"https://api.congress.gov/v3/bill/{bill['congress']}/{bill['type']}/{bill['number']}"
                    bill_response = self.session.get(bill_url, params=params)
                    if bill_response.status_code == 200:
                        bill_data = bill_response.json()
                        bill_info = bill_data.get('bill', {})
                        
                        # Add bill introduction
                        actions.append({
                            'action_type': 'bill_introduced',
                            'date': parser.parse(bill_info.get('introducedDate', '')),
                            'description': f"Introduced {bill_info.get('type')} {bill_info.get('number')}: {bill_info.get('title')}",
                            'source_url': f"https://www.congress.gov/bill/{bill['congress']}/{bill['type']}/{bill['number']}"
                        })
                        
                        # Add bill actions
                        for action in bill_info.get('actions', []):
                            actions.append({
                                'action_type': 'bill_action',
                                'date': parser.parse(action.get('actionDate', '')),
                                'description': action.get('text', ''),
                                'source_url': f"https://www.congress.gov/bill/{bill['congress']}/{bill['type']}/{bill['number']}"
                            })
                            
                except Exception as e:
                    logger.error(f"Error processing bill {bill.get('number')}: {str(e)}")
                    continue
            
            return actions
            
        except Exception as e:
            logger.error(f"Error fetching Congress actions: {str(e)}")
            return []

    def _fetch_press_releases(self, url: str) -> List[Dict[str, Any]]:
        """Fetch press releases from official's website"""
        actions = []
        
        try:
            # Try to find RSS feed first
            feed = feedparser.parse(url)
            if feed.entries:
                for entry in feed.entries:
                    actions.append({
                        'action_type': 'press_release',
                        'date': parser.parse(entry.get('published', '')),
                        'description': entry.get('title', ''),
                        'source_url': entry.get('link', '')
                    })
            else:
                # If no RSS, try scraping the page
                response = self.session.get(url)
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    # Look for common press release patterns
                    for article in soup.find_all(['article', 'div'], class_=re.compile(r'press|release|news')):
                        try:
                            title = article.find(['h1', 'h2', 'h3', 'h4']).text.strip()
                            date_elem = article.find(['time', 'span', 'div'], class_=re.compile(r'date|time'))
                            if date_elem:
                                date = parser.parse(date_elem.text.strip())
                            else:
                                date = datetime.now()
                                
                            link = article.find('a')
                            source_url = link['href'] if link else url
                            
                            actions.append({
                                'action_type': 'press_release',
                                'date': date,
                                'description': title,
                                'source_url': source_url
                            })
                        except Exception as e:
                            logger.error(f"Error processing press release: {str(e)}")
                            continue
            
            return actions
            
        except Exception as e:
            logger.error(f"Error fetching press releases: {str(e)}")
            return []

    def _fetch_news_mentions(self, name: str, source_url: str) -> List[Dict[str, Any]]:
        """Fetch news mentions of the official"""
        actions = []
        
        try:
            # Use Google News RSS feed
            url = f"https://news.google.com/rss/search?q={name}&hl=en-US&gl=US&ceid=US:en"
            feed = feedparser.parse(url)
            
            for entry in feed.entries[:20]:  # Limit to 20 most recent
                actions.append({
                    'action_type': 'news_mention',
                    'date': parser.parse(entry.get('published', '')),
                    'description': entry.get('title', ''),
                    'source_url': entry.get('link', '')
                })
            
            return actions
            
        except Exception as e:
            logger.error(f"Error fetching news mentions: {str(e)}")
            return []

    def update_official_actions(self, official_name: str, office: Optional[str] = None) -> None:
        """Update actions for a specific official"""
        try:
            with self.app.app_context():
                # Get member ID if congressional official
                member_id = None
                if office and any(term in office.lower() for term in ['senator', 'representative', 'congress']):
                    member_id = self._get_congress_member_id(official_name)
                
                # Fetch actions from different sources concurrently
                with ThreadPoolExecutor(max_workers=3) as executor:
                    futures = []
                    
                    # Congressional votes
                    if member_id:
                        futures.append(
                            executor.submit(self._fetch_congress_actions, member_id)
                        )
                    
                    # News articles
                    futures.append(
                        executor.submit(self._fetch_news_mentions, official_name, "https://news.google.com/rss/search?q=" + official_name + "&hl=en-US&gl=US&ceid=US:en")
                    )
                    
                    # Press releases from known sources
                    sources = ActionSource.query.filter_by(
                        official_name=official_name,
                        source_type='press_releases'
                    ).all()
                    
                    for source in sources:
                        futures.append(
                            executor.submit(self._fetch_press_releases, source.source_url)
                        )
                    
                    # Collect all actions
                    all_actions = []
                    for future in futures:
                        try:
                            actions = future.result()
                            if actions:
                                all_actions.extend(actions)
                        except Exception as e:
                            logger.error(f"Error collecting actions: {str(e)}")
                    
                    # Sort by date
                    all_actions.sort(key=lambda x: x['date'], reverse=True)
                    
                    # Update database
                    for action in all_actions:
                        existing = OfficialAction.query.filter_by(
                            official_name=official_name,
                            action_type=action['action_type'],
                            date=action['date'],
                            source_url=action['source_url']
                        ).first()
                        
                        if not existing:
                            new_action = OfficialAction(
                                official_name=official_name,
                                office=office or 'Unknown',
                                action_type=action['action_type'],
                                description=action['description'],
                                date=action['date'],
                                source_url=action['source_url'],
                                source_type=action.get('source_type', action['action_type']),
                                metadata=action.get('metadata', {})
                            )
                            db.session.add(new_action)
                    
                    db.session.commit()
                    
        except Exception as e:
            logger.error(f"Error updating official actions: {str(e)}")
            db.session.rollback()

    def get_press_releases(self, name: str) -> List[Dict[str, Any]]:
        """Get press releases for a given official."""
        releases = []
        
        # Map of official names to their press release URLs with fallbacks
        url_map = {
            'Elizabeth Warren': [
                'https://www.warren.senate.gov/newsroom/press-releases',
                'https://www.warren.senate.gov/newsroom',
                'https://www.warren.senate.gov/news'
            ],
            'Ted Cruz': [
                'https://www.cruz.senate.gov/newsroom/press-releases',
                'https://www.cruz.senate.gov/news',
                'https://www.cruz.senate.gov/media'
            ],
            'Ron DeSantis': [
                'https://www.myflorida.com/news',
                'https://www.flgov.com/press-releases',
                'https://www.flgov.com/news'
            ],
            'Gavin Newsom': [
                'https://www.gov.ca.gov/news',
                'https://www.gov.ca.gov/newsroom',
                'https://www.ca.gov/news'
            ],
            'Greg Abbott': [
                'https://gov.texas.gov/news',
                'https://gov.texas.gov/news/category/press-release'
            ],
            'Josh Shapiro': [
                'https://www.governor.pa.gov/newsroom',
                'https://www.governor.pa.gov/news'
            ],
            'Gretchen Whitmer': [
                'https://www.michigan.gov/whitmer/news',
                'https://www.michigan.gov/whitmer/news/press-releases',
                'https://www.michigan.gov/whitmer/news/press-releases/all'
            ]
        }

        # Custom headers for sites that require them
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Cache-Control': 'max-age=0'
        }

        # Parsing functions for each official's website
        parse_funcs = {
            'Elizabeth Warren': self._parse_warren_releases,
            'Ted Cruz': self._parse_cruz_releases,
            'Ron DeSantis': self._parse_florida_releases,
            'Gavin Newsom': self._parse_california_releases,
            'Greg Abbott': self._parse_texas_releases,
            'Josh Shapiro': self._parse_pennsylvania_releases,
            'Gretchen Whitmer': self._parse_michigan_releases
        }

        try:
            if name in url_map:
                # Try each URL in order until one works
                for url in url_map[name]:
                    try:
                        response = self._get_with_retry(url, headers=headers, verify=True)
                        
                        if response.status_code == 200:
                            parse_func = parse_funcs.get(name)
                            if parse_func:
                                releases = parse_func(response.text)
                                if releases:
                                    break
                        elif response.status_code in [403, 503]:
                            # Add delay for rate-limited sites
                            time.sleep(2)
                            continue
                    except requests.exceptions.SSLError:
                        # Try without SSL verification for problematic sites
                        try:
                            response = self._get_with_retry(url, headers=headers, verify=False)
                            if response.status_code == 200:
                                parse_func = parse_funcs.get(name)
                                if parse_func:
                                    releases = parse_func(response.text)
                                    if releases:
                                        break
                        except requests.exceptions.RequestException as e:
                            logging.error(f"Error fetching press releases with SSL verification disabled: {str(e)}")
                    except requests.exceptions.RequestException as e:
                        logging.error(f"Error fetching press releases: {str(e)}")
                        continue

                if not releases:
                    logging.error(f"Failed to fetch press releases from all URLs for {name}")
                
        except Exception as e:
            logging.error(f"Unexpected error fetching press releases: {str(e)}")
        
        return releases

    def _get_with_retry(self, url: str, headers: Dict = None, verify: bool = True, max_retries: int = 3) -> Optional[requests.Response]:
        """Make a GET request with retry logic for rate limiting and SSL issues"""
        headers = headers or {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        for attempt in range(max_retries):
            try:
                # Try with SSL verification first
                if verify:
                    response = self.session.get(url, headers=headers, verify=True, timeout=10)
                else:
                    response = self.session.get(url, headers=headers, verify=False, timeout=10)
                
                # Handle rate limiting
                if response.status_code == 429:
                    wait_time = int(response.headers.get('Retry-After', 60))
                    logger.warning(f"Rate limited. Waiting {wait_time} seconds...")
                    time.sleep(wait_time)
                    continue
                    
                # Handle other status codes
                if response.status_code == 403:
                    # Try with different headers
                    headers['User-Agent'] = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Firefox/89.0'
                    continue
                    
                response.raise_for_status()
                return response
                
            except requests.exceptions.SSLError:
                logger.warning(f"SSL error for {url}, retrying without verification...")
                verify = False
                continue
                
            except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
                logger.warning(f"Connection error for {url}: {str(e)}, retrying...")
                time.sleep(5)
                continue
                
            except requests.exceptions.RequestException as e:
                if attempt == max_retries - 1:
                    logger.error(f"Error fetching {url}: {str(e)}")
                    return None
                time.sleep(5)
                continue
                
        return None

    def _fetch_press_releases(self, url: str) -> List[Dict]:
        """Fetch press releases from a given URL"""
        try:
            response = self._get_with_retry(url)
            if not response:
                return []
                
            soup = BeautifulSoup(response.text, 'html.parser')
            press_releases = []
            
            # Common patterns for press release containers
            containers = soup.find_all(['article', 'div', 'li'], class_=lambda x: x and any(
                term in x.lower() for term in ['press', 'release', 'news', 'item']
            ))
            
            if not containers:
                # Try finding by link text
                links = soup.find_all('a', text=lambda x: x and any(
                    term in x.lower() for term in ['press', 'release', 'statement']
                ))
                containers = [link.parent for link in links]
            
            for container in containers[:10]:  # Limit to 10 most recent
                try:
                    # Find title
                    title = container.find(['h1', 'h2', 'h3', 'h4', 'a'], text=True)
                    if not title:
                        continue
                        
                    # Find date
                    date_elem = container.find(['time', 'span', 'div'], class_=lambda x: x and any(
                        term in x.lower() for term in ['date', 'time', 'posted']
                    ))
                    
                    if not date_elem:
                        # Try finding date in text
                        text = container.get_text()
                        date_match = re.search(r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\w+ \d{1,2},? \d{4}', text)
                        if date_match:
                            date_str = date_match.group()
                        else:
                            continue
                    else:
                        date_str = date_elem.get_text()
                    
                    try:
                        date = parser.parse(date_str)
                    except (ValueError, TypeError):
                        continue
                    
                    # Find link
                    link = container.find('a')
                    if not link:
                        continue
                        
                    url = link['href']
                    if not url.startswith('http'):
                        base_url = '/'.join(response.url.split('/')[:3])
                        url = base_url + ('' if url.startswith('/') else '/') + url
                    
                    press_releases.append({
                        'action_type': 'press_release',
                        'date': date,
                        'description': title.get_text().strip(),
                        'source': url
                    })
                    
                except Exception as e:
                    logger.warning(f"Error parsing press release: {str(e)}")
                    continue
            
            return press_releases
            
        except Exception as e:
            logger.error(f"Error fetching press releases: {str(e)}")
            return []

    def _fetch_rss_feed(self, url: str) -> List[Dict]:
        """Fetch items from an RSS feed"""
        try:
            response = self._get_with_retry(url)
            if not response:
                return []
                
            feed = feedparser.parse(response.text)
            
            items = []
            for entry in feed.entries[:10]:  # Limit to 10 most recent
                try:
                    # Extract date
                    if hasattr(entry, 'published_parsed'):
                        action_date = datetime(*entry.published_parsed[:6])
                    elif hasattr(entry, 'updated_parsed'):
                        action_date = datetime(*entry.updated_parsed[:6])
                    else:
                        continue
                    
                    # Get description
                    description = entry.description
                    if hasattr(description, 'get_text'):
                        description = description.get_text()
                    description = re.sub(r'\s+', ' ', str(description)).strip()
                    
                    # Ensure the official is actually mentioned
                    if not self._verify_official_mention(official_name, entry.title + ' ' + description):
                        continue
                    
                    items.append({
                        'action_type': 'rss',
                        'date': action_date,
                        'description': f"{entry.title} - {description[:200]}...",
                        'source_url': entry.link,
                        'metadata': {
                            'title': entry.title,
                            'author': getattr(entry, 'author', 'Unknown'),
                            'source': feed.feed.title
                        }
                    })
                except Exception as e:
                    logger.error(f"Error processing RSS entry: {str(e)}")
                    continue
                
            return items
            
        except Exception as e:
            logger.error(f"Error fetching RSS feed: {str(e)}")
            return []
    
    def _parse_warren_releases(self, html: str) -> List[Dict[str, Any]]:
        """Parse press releases from Elizabeth Warren's website."""
        releases = []
        try:
            soup = BeautifulSoup(html, 'html.parser')
            for item in soup.select('.news-item'):
                release = {
                    'action_type': 'press_release',
                    'date': item.select_one('.date').text.strip(),
                    'title': item.select_one('h3').text.strip(),
                    'description': item.select_one('.description').text.strip(),
                    'source': item.select_one('a')['href']
                }
                releases.append(release)
        except Exception as e:
            logging.error(f"Error parsing Warren releases: {str(e)}")
        return releases

    def _parse_cruz_releases(self, html: str) -> List[Dict[str, Any]]:
        """Parse press releases from Ted Cruz's website."""
        releases = []
        try:
            soup = BeautifulSoup(html, 'html.parser')
            for item in soup.select('.press-release'):
                release = {
                    'action_type': 'press_release',
                    'date': item.select_one('.date').text.strip(),
                    'title': item.select_one('h2').text.strip(),
                    'description': item.select_one('.summary').text.strip(),
                    'source': item.select_one('a')['href']
                }
                releases.append(release)
        except Exception as e:
            logging.error(f"Error parsing Cruz releases: {str(e)}")
        return releases

    def _parse_florida_releases(self, html: str) -> List[Dict[str, Any]]:
        """Parse press releases from Ron DeSantis's website."""
        releases = []
        try:
            soup = BeautifulSoup(html, 'html.parser')
            for item in soup.select('.news-item'):
                release = {
                    'action_type': 'press_release',
                    'date': item.select_one('.date').text.strip(),
                    'title': item.select_one('h3').text.strip(),
                    'description': item.select_one('.excerpt').text.strip(),
                    'source': item.select_one('a')['href']
                }
                releases.append(release)
        except Exception as e:
            logging.error(f"Error parsing Florida releases: {str(e)}")
        return releases

    def _parse_california_releases(self, html: str) -> List[Dict[str, Any]]:
        """Parse press releases from Gavin Newsom's website."""
        releases = []
        try:
            soup = BeautifulSoup(html, 'html.parser')
            for item in soup.select('article'):
                release = {
                    'action_type': 'press_release',
                    'date': item.select_one('.date').text.strip(),
                    'title': item.select_one('h2').text.strip(),
                    'description': item.select_one('.excerpt').text.strip(),
                    'source': item.select_one('a')['href']
                }
                releases.append(release)
        except Exception as e:
            logging.error(f"Error parsing California releases: {str(e)}")
        return releases

    def _parse_texas_releases(self, html: str) -> List[Dict[str, Any]]:
        """Parse press releases from Greg Abbott's website."""
        releases = []
        try:
            soup = BeautifulSoup(html, 'html.parser')
            for item in soup.select('.news-item'):
                release = {
                    'action_type': 'press_release',
                    'date': item.select_one('.date').text.strip(),
                    'title': item.select_one('h3').text.strip(),
                    'description': item.select_one('.summary').text.strip(),
                    'source': item.select_one('a')['href']
                }
                releases.append(release)
        except Exception as e:
            logging.error(f"Error parsing Texas releases: {str(e)}")
        return releases

    def _parse_pennsylvania_releases(self, html: str) -> List[Dict[str, Any]]:
        """Parse press releases from Josh Shapiro's website."""
        releases = []
        try:
            soup = BeautifulSoup(html, 'html.parser')
            for item in soup.select('.press-release'):
                release = {
                    'action_type': 'press_release',
                    'date': item.select_one('.date').text.strip(),
                    'title': item.select_one('h2').text.strip(),
                    'description': item.select_one('.summary').text.strip(),
                    'source': item.select_one('a')['href']
                }
                releases.append(release)
        except Exception as e:
            logging.error(f"Error parsing Pennsylvania releases: {str(e)}")
        return releases

    def _parse_michigan_releases(self, html: str) -> List[Dict[str, Any]]:
        """Parse press releases from Gretchen Whitmer's website."""
        releases = []
        try:
            soup = BeautifulSoup(html, 'html.parser')
            for item in soup.select('.news-item'):
                release = {
                    'action_type': 'press_release',
                    'date': item.select_one('.date').text.strip(),
                    'title': item.select_one('h2').text.strip(),
                    'description': item.select_one('.summary').text.strip(),
                    'source': item.select_one('a')['href']
                }
                releases.append(release)
        except Exception as e:
            logging.error(f"Error parsing Michigan releases: {str(e)}")
        return releases

    def _fetch_single_news_source(self, source: ActionSource) -> List[Dict]:
        """Fetch news from a single RSS source"""
        try:
            feed = feedparser.parse(source.source_url)
            return self._process_news_feed(feed, source.official_name)
        except Exception as e:
            logger.error(f"Error processing RSS feed for {source.official_name}: {str(e)}")
            return []
    
    def _process_news_feed(self, feed, official_name: str) -> List[Dict]:
        """Process RSS news feed entries"""
        actions = []
        for entry in feed.entries:
            try:
                # Extract date
                if hasattr(entry, 'published_parsed'):
                    action_date = datetime(*entry.published_parsed[:6])
                elif hasattr(entry, 'updated_parsed'):
                    action_date = datetime(*entry.updated_parsed[:6])
                else:
                    continue
                
                # Get description
                description = entry.description
                if hasattr(description, 'get_text'):
                    description = description.get_text()
                description = re.sub(r'\s+', ' ', str(description)).strip()
                
                # Ensure the official is actually mentioned
                if not self._verify_official_mention(official_name, entry.title + ' ' + description):
                    continue
                
                actions.append({
                    'action_type': 'news',
                    'date': action_date,
                    'description': f"{entry.title} - {description[:200]}...",
                    'source_url': entry.link,
                    'metadata': {
                        'title': entry.title,
                        'author': getattr(entry, 'author', 'Unknown'),
                        'source': feed.feed.title
                    }
                })
            except Exception as e:
                logger.error(f"Error processing news entry: {str(e)}")
                continue
                
        return actions
    
    def _verify_official_mention(self, official_name: str, text: str) -> bool:
        """Verify that the official is actually mentioned in the text"""
        # Split name into parts
        name_parts = official_name.lower().split()
        text = text.lower()
        
        # Check for full name
        if official_name.lower() in text:
            return True
            
        # Check for last name with title
        last_name = name_parts[-1]
        titles = ['senator', 'representative', 'gov', 'governor', 'rep', 'sen']
        for title in titles:
            if f"{title} {last_name}" in text:
                return True
                
        return False
    
    def _process_press_releases(self, soup: BeautifulSoup, official_name: str, base_url: str) -> List[Dict]:
        """Process press releases from official's website"""
        actions = []
        
        # Common patterns for press release containers
        release_selectors = [
            '.press-release', '.news-item', '.media-release',
            'article', '.post', '.release'
        ]
        
        for selector in release_selectors:
            releases = soup.select(selector)
            if releases:
                for release in releases:
                    try:
                        # Extract date
                        date_elem = release.select_one('.date, .timestamp, time, .datetime')
                        if not date_elem:
                            continue
                            
                        action_date = parser.parse(date_elem.get_text())
                        
                        # Extract title
                        title_elem = release.select_one('h2, h3, .title')
                        title = title_elem.get_text().strip() if title_elem else 'Press Release'
                        
                        # Extract description
                        desc_elem = release.select_one('.description, .content, .summary, p')
                        description = desc_elem.get_text().strip() if desc_elem else ''
                        
                        # Extract link
                        link_elem = release.select_one('a')
                        link = link_elem.get('href') if link_elem else None
                        if link and not link.startswith('http'):
                            link = f"{base_url.rstrip('/')}/{link.lstrip('/')}"
                        
                        actions.append({
                            'action_type': 'press_releases',
                            'date': action_date,
                            'description': f"{title} - {description[:200]}...",
                            'source_url': link,
                            'metadata': {
                                'title': title,
                                'full_description': description
                            }
                        })
                    except Exception as e:
                        logger.error(f"Error processing press release: {str(e)}")
                        continue
                        
                # If we found and processed releases with one selector, stop trying others
                break
                
        return actions

    def get_official_actions(self, name: str, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """
        Get actions for a specific official within a date range
        
        Args:
            name (str): Name of the official
            start_date (datetime, optional): Start date for filtering actions
            end_date (datetime, optional): End date for filtering actions
            
        Returns:
            List[Dict[str, Any]]: List of actions with their details
        """
        try:
            # Query the database for actions
            query = OfficialAction.query.filter(OfficialAction.official_name == name)
            
            # Apply date filters if provided
            if start_date:
                query = query.filter(OfficialAction.date >= start_date)
            if end_date:
                query = query.filter(OfficialAction.date <= end_date)
                
            # Order by date descending
            query = query.order_by(OfficialAction.date.desc())
            
            # Convert to list of dictionaries
            actions = []
            for action in query.all():
                actions.append({
                    'id': action.id,
                    'date': action.date.isoformat() if action.date else None,
                    'description': action.description,
                    'action_type': action.action_type,
                    'source_url': action.source_url,
                    'source_type': action.source_type
                })
                
            return actions
            
        except Exception as e:
            logger.error(f"Error getting actions for {name}: {str(e)}")
            return []
