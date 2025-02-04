# Civic Tracker

A web application that helps citizens find and track their elected officials at all levels of government - federal, state, and local.

## Features

- View all US elected officials in one place
- Filter officials by location
- Automatic categorization of federal, state, and local officials
- Real-time search and filtering
- Detailed information about each official including:
  - Office held
  - Contact information
  - Official websites
  - Party affiliation
  - Photos (when available)

## Technical Stack

- Backend: Python/Flask
- Frontend: HTML, JavaScript, CSS
- APIs: Google Civic Information API
- Additional: Google Places API for address autocomplete

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

3. Create a `config.py` file with your API keys:
```python
GOOGLE_API_KEY = 'your-api-key'
DEBUG = False
CIVIC_INFO_API_URL = 'https://civicinfo.googleapis.com/civicinfo/v2/representatives'
```

4. Run the application:
```bash
python app.py
```

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
