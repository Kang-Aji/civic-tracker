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
- Timeline view of all official activities
- Real-time updates of official actions

## Setup

1. Clone the repository:
```bash
git clone [repository-url]
cd civic-tracker
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up environment variables in `.env`:
```
GOOGLE_API_KEY=your_google_api_key_here
PROPUBLICA_API_KEY=your_propublica_api_key_here
```

4. Initialize the database:
```bash
flask db upgrade
```

5. Run the application:
```bash
python -m flask run
```

## Required API Keys

1. Google Civic Information API
   - Used to fetch elected official information
   - Enable it in Google Cloud Console
   - Set the API key in `.env`

2. ProPublica Congress API (optional, for congressional voting records)
   - Get API key from ProPublica
   - Set the API key in `.env`

## Adding Action Sources

To track an official's actions, you can add sources:

```bash
curl -X POST http://localhost:5000/official/sources \
  -H "Content-Type: application/json" \
  -d '{
    "official_name": "Official Name",
    "source_type": "rss",
    "source_url": "https://example.com/feed.xml"
  }'
```

Source types:
- `rss`: RSS feed of news or press releases
- `website`: Official's website press release page
- `api`: API endpoint (like ProPublica for Congress members)

## Development

The application uses:
- Flask for the web framework
- SQLAlchemy for database management
- Flask-Migrate for database migrations
- APScheduler for periodic updates
- BeautifulSoup4 for web scraping
- Feedparser for RSS processing

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Google Civic Information API
- Google Places API
- Flask framework
- Contributors and maintainers
