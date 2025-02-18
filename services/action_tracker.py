import requests
import feedparser
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from dateutil import parser
from models import db, OfficialAction, ActionSource
import logging

logger = logging.getLogger(__name__)

class ActionTracker:
    def __init__(self, propublica_api_key=None):
        self.propublica_api_key = propublica_api_key
        
    def fetch_congress_member_actions(self, member_id):
        """Fetch actions for a congress member using ProPublica API"""
        if not self.propublica_api_key:
            logger.warning("ProPublica API key not configured")
            return []
            
        headers = {'X-API-Key': self.propublica_api_key}
        url = f'https://api.propublica.org/congress/v1/members/{member_id}/votes.json'
        
        try:
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                data = response.json()
                return self._process_congress_votes(data['results'][0]['votes'])
            else:
                logger.error(f"Error fetching congress member actions: {response.status_code}")
                return []
        except Exception as e:
            logger.error(f"Exception fetching congress member actions: {str(e)}")
            return []
    
    def fetch_official_news(self, official_name):
        """Fetch news articles mentioning the official"""
        sources = ActionSource.query.filter_by(
            official_name=official_name,
            source_type='rss'
        ).all()
        
        actions = []
        for source in sources:
            try:
                feed = feedparser.parse(source.source_url)
                actions.extend(self._process_news_feed(feed, official_name))
            except Exception as e:
                logger.error(f"Error processing RSS feed for {official_name}: {str(e)}")
        
        return actions
    
    def fetch_press_releases(self, official_name, press_release_url):
        """Fetch press releases from official's website"""
        try:
            response = requests.get(press_release_url)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                return self._process_press_releases(soup, official_name, press_release_url)
            else:
                logger.error(f"Error fetching press releases: {response.status_code}")
                return []
        except Exception as e:
            logger.error(f"Exception fetching press releases: {str(e)}")
            return []
    
    def _process_congress_votes(self, votes):
        """Process congressional voting records"""
        actions = []
        for vote in votes:
            action = OfficialAction(
                official_name=vote['member_id'],
                office='Congress',
                action_type='vote',
                description=f"Voted {vote['position']} on {vote['description']}",
                date=parser.parse(vote['date']),
                source_url=vote.get('url'),
                source_type='congress_api'
            )
            actions.append(action)
        return actions
    
    def _process_news_feed(self, feed, official_name):
        """Process RSS news feed entries"""
        actions = []
        for entry in feed.entries:
            # Only include entries from the last 30 days
            pub_date = parser.parse(entry.published)
            if datetime.now() - pub_date > timedelta(days=30):
                continue
                
            action = OfficialAction(
                official_name=official_name,
                office='Unknown',  # This would need to be populated from your officials database
                action_type='news',
                description=entry.title,
                date=pub_date,
                source_url=entry.link,
                source_type='news'
            )
            actions.append(action)
        return actions
    
    def _process_press_releases(self, soup, official_name, base_url):
        """Process press releases from official's website"""
        actions = []
        # This is a basic implementation - you'll need to customize based on the website structure
        for release in soup.find_all('article'):
            try:
                title = release.find('h2').text.strip()
                date_str = release.find('time').text.strip()
                link = release.find('a')['href']
                if not link.startswith('http'):
                    link = base_url + link
                
                action = OfficialAction(
                    official_name=official_name,
                    office='Unknown',  # This would need to be populated from your officials database
                    action_type='press_release',
                    description=title,
                    date=parser.parse(date_str),
                    source_url=link,
                    source_type='press_release'
                )
                actions.append(action)
            except Exception as e:
                logger.error(f"Error processing press release: {str(e)}")
                continue
        
        return actions
    
    def update_official_actions(self, official_name, office=None):
        """Update actions for a specific official"""
        try:
            # Fetch from all available sources
            actions = []
            
            # Check if this is a congress member
            if office and 'Congress' in office:
                member_id = self._get_congress_member_id(official_name)
                if member_id:
                    actions.extend(self.fetch_congress_member_actions(member_id))
            
            # Fetch news mentions
            actions.extend(self.fetch_official_news(official_name))
            
            # Fetch press releases if we have a URL
            sources = ActionSource.query.filter_by(
                official_name=official_name,
                source_type='website'
            ).all()
            
            for source in sources:
                actions.extend(self.fetch_press_releases(official_name, source.source_url))
            
            # Update last checked timestamp
            for source in ActionSource.query.filter_by(official_name=official_name).all():
                source.last_checked = datetime.utcnow()
            
            # Save all new actions
            for action in actions:
                db.session.add(action)
            
            db.session.commit()
            return len(actions)
            
        except Exception as e:
            logger.error(f"Error updating actions for {official_name}: {str(e)}")
            db.session.rollback()
            return 0
    
    def _get_congress_member_id(self, name):
        """Get ProPublica Congress API member ID from name"""
        # This would need to be implemented based on your data structure
        # You might want to store this mapping in your database
        return None
