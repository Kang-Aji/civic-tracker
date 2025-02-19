from flask import Flask, render_template, jsonify, request, g
from flask_sqlalchemy import SQLAlchemy
import os
from dotenv import load_dotenv
import requests
import json
from models import db, OfficialAction, ActionSource
from services.action_tracker import ActionTracker
from flask_migrate import Migrate
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from flask_caching import Cache
import time
from threading import Thread
import logging

# Load environment variables
load_dotenv()

# Get configuration from environment variables
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
CONGRESS_API_KEY = os.getenv('CONGRESS_API_KEY')
PROPUBLICA_API_KEY = os.getenv('PROPUBLICA_API_KEY')
CIVIC_INFO_API_URL = os.getenv('CIVIC_INFO_API_URL', 'https://www.googleapis.com/civicinfo/v2/representatives')
DEBUG = True  # Force debug mode on

app = Flask(__name__)
app.debug = DEBUG

# Add more detailed logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Database configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///civic_tracker.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize extensions
db.init_app(app)
migrate = Migrate(app, db)

# Initialize Flask-Caching
cache = Cache(app, config={'CACHE_TYPE': 'simple'})

# Initialize action tracker with cache and Congress API key
action_tracker = ActionTracker(cache, CONGRESS_API_KEY)

@app.before_request
def before_request():
    """Set up database connection"""
    if not hasattr(g, 'start_time'):
        g.start_time = time.time()

@app.after_request
def after_request(response):
    """Log request timing and clean up"""
    if hasattr(g, 'start_time'):
        elapsed = time.time() - g.start_time
        app.logger.info(f'Request completed in {elapsed:.2f}s: {request.path}')
    return response

# Cache for storing all officials data
all_officials_cache = None
last_cache_update = None
CACHE_DURATION = 3600  # Cache duration in seconds (1 hour)

def normalize_name(name):
    """Normalize official names for comparison while preserving special characters"""
    import unicodedata
    
    # Normalize unicode characters (e.g., convert é to e with accent)
    normalized = unicodedata.normalize('NFKC', name)
    
    # Remove extra whitespace while preserving special characters
    normalized = ' '.join(normalized.split())
    
    return normalized

def create_official_key(official, offices):
    """Create a unique key for an official based on name and role"""
    name = normalize_name(official.get('name', ''))
    office_str = ','.join(sorted([o.lower() for o in offices]))
    return f"{name}_{office_str}"

def get_cached_officials():
    """Get officials from cache or fetch and cache them"""
    cache_key = f'all_officials_{request.args.get("address", "")}'
    officials = cache.get(cache_key)
    
    if officials is None:
        officials = fetch_all_officials()
        if officials:
            cache.set(cache_key, officials)
    
    return officials

def fetch_all_officials():
    """Get officials for multiple important addresses to create a comprehensive list"""
    global all_officials_cache, last_cache_update
    
    # Check if cache is valid
    if not all_officials_cache or not last_cache_update:
        if DEBUG:
            print("Starting fresh fetch of all officials...")
        
        # Comprehensive list of addresses to cover all levels of government
        addresses = [
            # Federal Level
            "1600 Pennsylvania Avenue NW, Washington, DC 20500",  # White House
            "First St SE, Washington, DC 20004",                  # Capitol Building
            
            # State Capitals (all 50 states)
            "600 Dexter Ave, Montgomery, AL 36130",              # Alabama
            "PO Box 110001, Juneau, AK 99811",                  # Alaska
            "1700 W Washington St, Phoenix, AZ 85007",           # Arizona
            "500 Woodlane St, Little Rock, AR 72201",           # Arkansas
            "1303 10th Street, Sacramento, CA 95814",           # California
            "200 E Colfax Ave, Denver, CO 80203",               # Colorado
            "210 Capitol Ave, Hartford, CT 06106",              # Connecticut
            "411 Legislative Ave, Dover, DE 19901",             # Delaware
            "400 S Monroe St, Tallahassee, FL 32399",          # Florida
            "206 Washington St, Atlanta, GA 30334",             # Georgia
            "415 S Beretania St, Honolulu, HI 96813",          # Hawaii
            "700 W Jefferson St, Boise, ID 83702",              # Idaho
            "401 S 2nd St, Springfield, IL 62701",             # Illinois
            "200 W Washington St, Indianapolis, IN 46204",      # Indiana
            "1007 E Grand Ave, Des Moines, IA 50319",          # Iowa
            "300 SW 10th Ave, Topeka, KS 66612",               # Kansas
            "700 Capitol Ave, Frankfort, KY 40601",            # Kentucky
            "900 N 3rd St, Baton Rouge, LA 70802",             # Louisiana
            "210 State St, Augusta, ME 04330",                 # Maine
            "100 State Cir, Annapolis, MD 21401",              # Maryland
            "24 Beacon St, Boston, MA 02133",                  # Massachusetts
            "100 N Capitol Ave, Lansing, MI 48933",            # Michigan
            "75 Rev Dr Martin Luther King Jr Blvd, St Paul, MN 55155",  # Minnesota
            "400 High St, Jackson, MS 39201",                  # Mississippi
            "201 W Capitol Ave, Jefferson City, MO 65101",     # Missouri
            "1301 E 6th Ave, Helena, MT 59601",                # Montana
            "1445 K St, Lincoln, NE 68509",                    # Nebraska
            "101 N Carson St, Carson City, NV 89701",          # Nevada
            "107 N Main St, Concord, NH 03301",                # New Hampshire
            "125 W State St, Trenton, NJ 08608",               # New Jersey
            "490 Old Santa Fe Trail, Santa Fe, NM 87501",      # New Mexico
            "State St & Washington Ave, Albany, NY 12224",     # New York
            "1 E Edenton St, Raleigh, NC 27601",              # North Carolina
            "600 E Boulevard Ave, Bismarck, ND 58505",         # North Dakota
            "1 Capitol Square, Columbus, OH 43215",            # Ohio
            "2300 N Lincoln Blvd, Oklahoma City, OK 73105",    # Oklahoma
            "900 Court St NE, Salem, OR 97301",                # Oregon
            "501 N 3rd St, Harrisburg, PA 17120",             # Pennsylvania
            "82 Smith St, Providence, RI 02903",               # Rhode Island
            "1100 Gervais St, Columbia, SC 29201",            # South Carolina
            "500 E Capitol Ave, Pierre, SD 57501",             # South Dakota
            "600 Dr. M.L.K. Jr. Blvd, Nashville, TN 37243",   # Tennessee
            "1100 Congress Ave, Austin, TX 78701",             # Texas
            "350 State St, Salt Lake City, UT 84111",          # Utah
            "115 State St, Montpelier, VT 05633",             # Vermont
            "1000 Bank St, Richmond, VA 23219",                # Virginia
            "416 Sid Snyder Ave SW, Olympia, WA 98504",       # Washington
            "1900 Kanawha Blvd E, Charleston, WV 25305",      # West Virginia
            "2 E Main St, Madison, WI 53703",                  # Wisconsin
            "200 W 24th St, Cheyenne, WY 82002",              # Wyoming

            # Major Cities (for local government coverage)
            "City Hall, New York, NY 10007",                   # New York City
            "121 N LaSalle St, Chicago, IL 60602",            # Chicago
            "200 N Spring St, Los Angeles, CA 90012",         # Los Angeles
            "1 Dr Carlton B Goodlett Pl, San Francisco, CA 94102",  # San Francisco
            "1500 Marilla St, Dallas, TX 75201",              # Dallas
            "901 Bagby St, Houston, TX 77002",                # Houston
            "1 Kennedy Dr, Philadelphia, PA 19102",            # Philadelphia
            "414 E 12th St, Kansas City, MO 64106",           # Kansas City
            "200 E Washington St, Phoenix, AZ 85004",          # Phoenix
            "451 S State St, Salt Lake City, UT 84111",       # Salt Lake City
            "600 4th Ave, Seattle, WA 98104",                 # Seattle
            "451 7th St SW, Washington, DC 20410",            # Washington DC
            "233 John F Kennedy Blvd, Newark, NJ 07102",      # Newark
            "455 N Main St, Wichita, KS 67202",               # Wichita
            "200 E Wells St, Milwaukee, WI 53202",            # Milwaukee
            "1 Frank H Ogawa Plaza, Oakland, CA 94612",       # Oakland
            "400 S Ft Harrison Ave, Clearwater, FL 33756",    # Clearwater
            "30 Church St, Buffalo, NY 14202",                # Buffalo
        ]
        
        all_officials = {}
        federal_count = 0
        state_count = 0
        local_count = 0
        errors = []
        
        for address in addresses:
            try:
                if DEBUG:
                    print(f"\nFetching officials for address: {address}")
                
                # Make multiple requests with different roles to ensure comprehensive coverage
                for roles in [
                    ['legislatorUpperBody', 'legislatorLowerBody'],  # State legislators
                    ['headOfGovernment', 'deputyHeadOfGovernment'],  # Governors and lt. governors
                    ['administrativeArea1', 'administrativeArea2'],   # State and county officials
                    ['locality', 'regional'],                        # City and regional officials
                    ['special'],                                     # Special district officials
                ]:
                    response = requests.get(CIVIC_INFO_API_URL, params={
                        'key': GOOGLE_API_KEY,
                        'address': address,
                        'roles': roles,
                        'levels': ['country', 'administrativeArea1', 'administrativeArea2', 'locality', 'regional', 'special']
                    })
                    
                    if response.status_code == 200:
                        data = response.json()
                        officials_count = len(data.get('officials', []))
                        offices_count = len(data.get('offices', []))
                        
                        if DEBUG:
                            print(f"Found {officials_count} officials and {offices_count} offices for roles {roles}")
                        
                        # Process each official
                        for idx, official in enumerate(data.get('officials', [])):
                            # Get all offices this official holds
                            offices = [
                                office['name'] 
                                for office in data.get('offices', []) 
                                if idx in office.get('officialIndices', [])
                            ]
                            
                            # Create a unique key for this official
                            key = create_official_key(official, offices)
                            
                            # Only add if we haven't seen this official before
                            if key not in all_officials:
                                official['offices'] = offices
                                
                                # Categorize the official
                                is_federal = any('United States' in office or 'President' in office or 'Congress' in office for office in offices)
                                is_state = any('State' in office or 'Governor' in office or 'Senator' in office or 'Assembly' in office for office in offices)
                                
                                if is_federal:
                                    federal_count += 1
                                elif is_state:
                                    state_count += 1
                                else:
                                    local_count += 1
                                    
                                if DEBUG:
                                    print(f"Adding new official: {official['name']}")
                                    print(f"  Offices: {offices}")
                                    print(f"  Level: {'Federal' if is_federal else 'State' if is_state else 'Local'}")
                                
                                all_officials[key] = official
                    
                    else:
                        error_msg = f"Error fetching data for {address} with roles {roles}: Status {response.status_code}"
                        if DEBUG:
                            print(error_msg)
                        errors.append(error_msg)
                        
            except Exception as e:
                error_msg = f"Error processing {address}: {str(e)}"
                if DEBUG:
                    print(error_msg)
                errors.append(error_msg)
        
        # Update cache
        all_officials_cache = list(all_officials.values())
        last_cache_update = time.time()
        
        if DEBUG:
            print("\nFetch Summary:")
            print(f"Total unique officials found: {len(all_officials)}")
            print(f"  Federal officials: {federal_count}")
            print(f"  State officials: {state_count}")
            print(f"  Local officials: {local_count}")
            if errors:
                print("\nErrors encountered:")
                for error in errors:
                    print(f"  - {error}")
        
        return all_officials_cache

@app.route('/')
def index():
    """Render the main page"""
    return render_template('index.html', debug_mode=app.debug, google_api_key=GOOGLE_API_KEY)

@app.route('/all_officials')
def all_officials():
    try:
        force_refresh = request.args.get('refresh', '').lower() == 'true'
        if DEBUG:
            print(f"\nHandling /all_officials request")
            print(f"Force refresh: {force_refresh}")
        
        officials = get_cached_officials()
        
        if DEBUG:
            print(f"Returning {len(officials)} officials")
            # Print first few officials as sample
            print("\nSample of officials being returned:")
            for official in officials[:3]:
                print(f"  - {official['name']}")
                print(f"    Offices: {official.get('offices', [])}")
        
        return jsonify({
            'officials': officials,
            'count': len(officials),
            'cache_age': int(time.time() - last_cache_update) if last_cache_update else 0
        })
    except Exception as e:
        error_msg = f"Error in /all_officials: {str(e)}"
        if DEBUG:
            print(error_msg)
        return jsonify({
            'error': error_msg,
            'cache_status': {
                'has_cache': all_officials_cache is not None,
                'cache_age': int(time.time() - last_cache_update) if last_cache_update else None
            }
        }), 500

@app.route('/search_representatives')
def search_representatives():
    address = request.args.get('address')
    if not address:
        logger.warning("Address parameter missing in search_representatives request")
        return jsonify({'error': 'Address is required'}), 400

    params = {
        'key': GOOGLE_API_KEY,
        'address': address
    }
    
    try:
        logger.info(f"Searching representatives for address: {address}")
        logger.debug(f"Making request to: {CIVIC_INFO_API_URL}")
        
        if not GOOGLE_API_KEY:
            logger.error("GOOGLE_API_KEY is not configured")
            return jsonify({
                'error': 'Google API key is not configured. Please set the GOOGLE_API_KEY environment variable.'
            }), 500

        response = requests.get(CIVIC_INFO_API_URL, params=params)
        
        logger.debug(f"Response status code: {response.status_code}")
        
        if response.status_code == 403:
            error_data = response.json()
            error_msg = error_data.get('error', {}).get('message', 'Access Forbidden')
            logger.error(f"API Access Error: {error_msg}")
            return jsonify({
                'error': f'API Access Error: {error_msg}\n' +
                        'Please ensure you have:\n' +
                        '1. Enabled the Google Civic Information API\n' +
                        '2. Enabled the Google Places API\n' +
                        '3. Enabled the Maps JavaScript API\n' +
                        '4. Properly configured your API key\n' +
                        '5. Enabled billing for your Google Cloud Project'
            }), 403
        elif response.status_code == 400:
            error_data = response.json()
            error_msg = error_data.get('error', {}).get('message', 'Invalid address')
            logger.warning(f"Invalid address error: {error_msg}")
            return jsonify({
                'error': 'Invalid address format or the address could not be found',
                'details': error_msg
            }), 400
        
        response.raise_for_status()
        data = response.json()
        
        officials_count = len(data.get('officials', []))
        offices_count = len(data.get('offices', []))
        logger.info(f"Found {officials_count} officials and {offices_count} offices for address")
            
        return jsonify(data)
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Request error in search_representatives: {str(e)}")
        error_message = str(e)
        if 'API not enabled' in error_message:
            error_message = 'The Google Civic Information API is not enabled. Please enable it in your Google Cloud Console.'
        return jsonify({
            'error': error_message,
            'type': 'request_error'
        }), 500
    except Exception as e:
        logger.error(f"Unexpected error in search_representatives: {str(e)}", exc_info=True)
        return jsonify({
            'error': 'An unexpected error occurred while fetching representatives',
            'type': 'server_error'
        }), 500

@app.route('/search')
def search():
    """Search for representatives by address"""
    address = request.args.get('address')
    if not address:
        return jsonify({'error': 'Address is required'}), 400
        
    try:
        response = requests.get(CIVIC_INFO_API_URL, params={
            'key': GOOGLE_API_KEY,
            'address': address,
            'levels': ['country', 'administrativeArea1', 'administrativeArea2', 'locality', 'regional', 'special']
        })
        
        if response.status_code != 200:
            return jsonify({'error': 'Error fetching representatives'}), response.status_code
            
        data = response.json()
        officials = data.get('officials', [])
        offices = data.get('offices', [])
        
        # Process officials and their offices
        processed_officials = []
        federal_count = 0
        state_count = 0
        local_count = 0
        
        for idx, official in enumerate(officials):
            # Get all offices this official holds
            official_offices = [
                office['name'] 
                for office in offices 
                if idx in office.get('officialIndices', [])
            ]
            
            official['offices'] = official_offices
            
            # Categorize the official
            is_federal = any('United States' in office or 'President' in office or 'Congress' in office for office in official_offices)
            is_state = any('State' in office or 'Governor' in office or 'Senator' in office or 'Assembly' in office for office in official_offices)
            
            if is_federal:
                federal_count += 1
            elif is_state:
                state_count += 1
            else:
                local_count += 1
                
            processed_officials.append(official)
        
        return jsonify({
            'officials': processed_officials,
            'counts': {
                'federal': federal_count,
                'state': state_count,
                'local': local_count,
                'total': len(processed_officials)
            }
        })
        
    except Exception as e:
        app.logger.error(f'Error in search: {str(e)}')
        return jsonify({'error': 'Error processing request'}), 500

@app.route('/api/officials/<path:n>/actions')
def get_official_actions(n):
    """Get actions for a specific official with filtering"""
    logger.debug(f"Received request for official actions: {n}")
    try:
        days = request.args.get('days', '30')
        action_type = request.args.get('type', 'all')
        
        logger.debug(f"Query parameters: days={days}, type={action_type}")
        
        # Convert days to integer
        try:
            days = int(days)
        except ValueError:
            days = 30
            
        # URL decode the name and normalize it
        from urllib.parse import unquote
        decoded_name = normalize_name(unquote(n))
        logger.debug(f"Decoded and normalized name: {decoded_name}")
        
        # Get actions from database using normalized name
        query = OfficialAction.query.filter(
            OfficialAction.official_name == decoded_name,
            OfficialAction.date >= (datetime.utcnow() - timedelta(days=days))
        )
        logger.debug(f"Database query: {query}")
        
        # Map frontend type to database type
        type_mapping = {
            'bill': ['bill_introduced', 'bill_action', 'vote'],
            'press-release': ['press_release'],
            'news': ['news_mention']
        }
        
        # Apply type filter if not 'all'
        if action_type != 'all' and action_type in type_mapping:
            query = query.filter(OfficialAction.action_type.in_(type_mapping[action_type]))
            
        actions = query.order_by(OfficialAction.date.desc()).all()
        
        if not actions:
            return jsonify({
                'success': True,
                'actions': []
            })
        
        return jsonify({
            'success': True,
            'actions': [{
                'id': action.id,
                'date': action.date.isoformat(),
                'action_type': action.action_type,
                'description': action.description,
                'source': action.source_url
            } for action in actions]
        })
        
    except Exception as e:
        app.logger.error(f"Error getting actions for {n}: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Error fetching actions: {str(e)}'
        }), 500

@app.route('/api/officials/<path:n>/actions/refresh', methods=['POST'])
def refresh_official_actions(n):
    """Refresh actions for a specific official"""
    try:
        # URL decode the name
        from urllib.parse import unquote
        decoded_name = unquote(n)
        
        # Get the official's sources
        sources = ActionSource.query.filter_by(official_name=decoded_name).all()
        
        if not sources:
            # Create default sources for the official
            sources = [
                ActionSource(
                    official_name=decoded_name,
                    source_type='congress_api',
                    source_url='https://api.congress.gov/v3/member'
                ),
                ActionSource(
                    official_name=decoded_name,
                    source_type='press_release',
                    source_url=f'https://www.congress.gov/member/{decoded_name.lower().replace(" ", "-")}/news'
                )
            ]
            for source in sources:
                db.session.add(source)
            db.session.commit()
        
        # Use action tracker to fetch new actions
        actions = action_tracker.fetch_official_actions(decoded_name, sources)
        
        # Add actions to database
        for action in actions:
            existing = OfficialAction.query.filter_by(
                official_name=decoded_name,
                date=action['date'],
                description=action['description']
            ).first()
            
            if not existing:
                new_action = OfficialAction(
                    official_name=decoded_name,
                    office=action.get('office', 'Unknown'),
                    action_type=action.get('action_type', 'unknown'),
                    description=action['description'],
                    date=action['date'],
                    source_url=action.get('source_url'),
                    source_type=action.get('source_type')
                )
                db.session.add(new_action)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Successfully refreshed actions for {decoded_name}',
            'count': len(actions)
        })
        
    except Exception as e:
        app.logger.error(f"Error refreshing actions for {n}: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Error refreshing actions: {str(e)}'
        }), 500

@app.route('/api/officials/<path:n>/sources', methods=['GET'])
def get_official_sources(n):
    """Get action sources for a specific official"""
    try:
        # URL decode the name
        from urllib.parse import unquote
        decoded_name = unquote(n)
        
        sources = ActionSource.query.filter_by(official_name=decoded_name).all()
        return jsonify([{
            'type': source.source_type,
            'url': source.source_url
        } for source in sources]), 200
        
    except Exception as e:
        app.logger.error(f"Error getting sources for {n}: {str(e)}")
        return jsonify({'error': 'Failed to get official sources'}), 500

@app.route('/api/officials/<path:n>/sources', methods=['POST'])
def add_official_source(n):
    """Add a new action source for an official"""
    try:
        # URL decode the name
        from urllib.parse import unquote
        decoded_name = unquote(n)
        
        data = request.get_json()
        
        # Validate required fields
        if not all(k in data for k in ['type', 'url']):
            return jsonify({'error': 'Missing required fields'}), 400
            
        # Create new source
        source = ActionSource(
            official_name=decoded_name,
            source_type=data['type'],
            source_url=data['url']
        )
        
        db.session.add(source)
        db.session.commit()
        
        return jsonify({'message': 'Source added successfully'}), 201
        
    except Exception as e:
        app.logger.error(f"Error adding source for {n}: {str(e)}")
        db.session.rollback()
        return jsonify({'error': 'Failed to add official source'}), 500

@app.route('/api/officials/<path:n>/sources', methods=['DELETE'])
def remove_official_source(n):
    """Remove an action source for an official"""
    try:
        # URL decode the name
        from urllib.parse import unquote
        decoded_name = unquote(n)
        
        data = request.get_json()
        
        # Validate required fields
        if 'url' not in data:
            return jsonify({'error': 'Missing source URL'}), 400
            
        # Find and delete source
        source = ActionSource.query.filter_by(
            official_name=decoded_name,
            source_url=data['url']
        ).first()
        
        if source:
            db.session.delete(source)
            db.session.commit()
            return jsonify({'message': 'Source removed successfully'}), 200
        else:
            return jsonify({'error': 'Source not found'}), 404
            
    except Exception as e:
        app.logger.error(f"Error removing source for {n}: {str(e)}")
        db.session.rollback()
        return jsonify({'error': 'Failed to remove official source'}), 500

def setup_action_updates():
    """Set up scheduled updates with optimized batch processing"""
    scheduler = BackgroundScheduler()
    
    def update_all_actions():
        with app.app_context():
            try:
                # Get all tracked officials from the database
                tracked_officials = db.session.query(ActionSource.official_name).distinct().all()
                
                # Update actions in batches
                batch_size = 5
                for i in range(0, len(tracked_officials), batch_size):
                    batch = tracked_officials[i:i + batch_size]
                    
                    for official in batch:
                        try:
                            # Get latest actions for the official
                            actions = action_tracker.get_official_actions(official.official_name)
                            
                            # Update database with new actions
                            for action in actions:
                                existing = OfficialAction.query.filter_by(
                                    official_name=official.official_name,
                                    date=action['date'],
                                    description=action['description']
                                ).first()
                                
                                if not existing:
                                    new_action = OfficialAction(
                                        official_name=official.official_name,
                                        action_date=action['date'],
                                        action_type=action['type'],
                                        description=action['description'],
                                        source_url=action['source']
                                    )
                                    db.session.add(new_action)
                            
                            db.session.commit()
                            app.logger.info(f"Updated actions for {official.official_name}")
                            
                        except Exception as e:
                            app.logger.error(f"Error updating actions for {official.official_name}: {str(e)}")
                            db.session.rollback()
                            continue
                            
                    # Add a small delay between batches to prevent rate limiting
                    time.sleep(2)
                    
            except Exception as e:
                app.logger.error(f"Error in update_all_actions: {str(e)}")
                
    # Schedule updates to run every hour
    scheduler.add_job(update_all_actions, 'interval', hours=1)
    scheduler.start()
    
    # Run initial update
    Thread(target=update_all_actions).start()

# Start the action update scheduler when the app starts
if not app.debug or os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
    setup_action_updates()

if __name__ == '__main__':
    # Create database tables
    with app.app_context():
        db.create_all()
    app.run()
