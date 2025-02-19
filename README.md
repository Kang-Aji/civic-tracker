# Civic Tracker

A web application that helps citizens track their elected officials and their actions.

## Features

- Find all your elected representatives by address
- Filter officials by federal, state, and local levels
- View contact information and official websites
- Track official actions including:
  - Voting records (for Congress members)
  - Press releases
  - News mentions
  - Bill sponsorships and co-sponsorships
- Timeline view of all official activities
- Real-time updates of official actions
- Advanced filtering:
  - Time-based filtering (7 days, 30 days, 90 days, 1 year)
  - Action type filtering (bills, press releases, news)
- Responsive design for mobile and desktop
- RESTful API with webhook support

## Documentation

- [API Documentation](API.md) - Comprehensive API reference
- [Development Guide](DEVELOPMENT.md) - Detailed setup and development instructions
- [Contributing Guidelines](CONTRIBUTING.md)
- [License](LICENSE)

## Quick Start

1. Clone the repository:
```bash
git clone [repository-url]
cd civic-tracker
```

2. Create and activate virtual environment:
```bash
python -m venv venv
.\venv\Scripts\activate  # Windows
source venv/bin/activate  # Unix/macOS
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables in `.env`:
```
GOOGLE_API_KEY=your_google_api_key_here
PROPUBLICA_API_KEY=your_propublica_api_key_here
CONGRESS_API_KEY=your_congress_api_key_here
```

5. Initialize the database:
```bash
flask db upgrade
```

6. Run the application:
```bash
flask run
```

For detailed development setup instructions, including test configuration and development tools, see our [Development Guide](DEVELOPMENT.md).

## Testing

The project includes comprehensive testing infrastructure:

### Frontend Integration Tests
Run the frontend tests with:
```bash
pytest tests/frontend/
```

Frontend tests cover:
- Address search functionality
- Official information display
- Action tracker interactions
- Time period filtering
- Action type filtering
- Dynamic content updates

### Test Configuration
- Tests use a simplified Flask application
- Mock API responses for consistent testing
- Selenium WebDriver for browser automation
- Configurable for both local and CI environments

## Required API Keys

1. Google Civic Information API
   - Used to fetch elected official information
   - Enable it in Google Cloud Console
   - Set the API key in `.env`

2. ProPublica Congress API (optional, for congressional voting records)
   - Get API key from ProPublica
   - Set the API key in `.env`

3. Congress.gov API (optional, for bill tracking)
   - Get API key from Congress.gov
   - Set the API key in `.env`

## Using the API

Civic Tracker provides a comprehensive RESTful API that allows you to:
- Search for officials by address
- Track official actions and voting records
- Set up webhooks for real-time updates
- Access official statistics and analytics

For detailed API documentation, see [API.md](API.md).

### Quick Start with the API

```python
import requests

# Search for officials
response = requests.get(
    'http://localhost:5000/api/v1/officials/search',
    params={'address': '1600 Pennsylvania Avenue NW, Washington, DC'}
)

# Get official's recent actions
official_id = response.json()['officials'][0]['id']
actions = requests.get(
    f'http://localhost:5000/api/v1/officials/{official_id}/actions'
)
```

## Development

The application uses:
- Flask for the web framework
- SQLAlchemy for database management
- Flask-Migrate for database migrations
- APScheduler for periodic updates
- BeautifulSoup4 for web scraping
- Feedparser for RSS processing
- Selenium for frontend testing
- Pytest for test infrastructure

For detailed development instructions, including:
- Setting up a development environment
- Running tests
- Database management
- Code quality tools
- Debugging tips
- Performance profiling

See our comprehensive [Development Guide](DEVELOPMENT.md).

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Add tests for new features
6. Open a Pull Request

For detailed contribution guidelines, see [CONTRIBUTING.md](CONTRIBUTING.md).

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Google Civic Information API
- Google Places API
- ProPublica Congress API
- Congress.gov API
- Flask framework
- Selenium WebDriver
- Contributors and maintainers
