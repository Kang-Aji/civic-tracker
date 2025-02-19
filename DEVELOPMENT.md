# Development Setup Guide

This guide provides detailed instructions for setting up a development environment for the Civic Tracker project.

## Prerequisites

### Required Software
- Python 3.11 or higher
- Git
- Chrome or Firefox (for frontend testing)
- Visual Studio Code (recommended) or your preferred IDE
- PostgreSQL 14 or higher (for local development database)

### Recommended VS Code Extensions
- Python
- Pylance
- Python Test Explorer
- GitLens
- SQLTools
- Docker (if using containerized development)

## Initial Setup

1. **Clone the Repository**
```bash
git clone https://github.com/civic-tracker/civic-tracker.git
cd civic-tracker
```

2. **Create a Virtual Environment**
```bash
# Windows
python -m venv venv
.\venv\Scripts\activate

# Unix/macOS
python -m venv venv
source venv/bin/activate
```

3. **Install Dependencies**
```bash
# Core dependencies
pip install -r requirements.txt

# Development and testing dependencies
pip install -r requirements-test.txt

# Pre-commit hooks
pip install pre-commit
pre-commit install
```

4. **Set Up Environment Variables**
```bash
# Copy the example env file
cp .env.example .env

# Edit .env with your API keys and configuration
# For development, use:
DEBUG=True
FLASK_ENV=development
DATABASE_URL=postgresql://localhost/civic_tracker
GOOGLE_API_KEY=your_key_here
PROPUBLICA_API_KEY=your_key_here
CONGRESS_API_KEY=your_key_here
```

5. **Set Up the Database**
```bash
# Create the database
createdb civic_tracker

# Run migrations
flask db upgrade

# (Optional) Load sample data
python scripts/load_sample_data.py
```

## Development Workflow

### Running the Application

1. **Start the Development Server**
```bash
# With debug mode and auto-reload
flask run --debug

# Or with custom host/port
flask run --host=0.0.0.0 --port=5000
```

2. **Start the Action Tracker Service**
```bash
# In a separate terminal
python services/action_tracker.py
```

### Running Tests

1. **Unit Tests**
```bash
# Run all unit tests
pytest tests/unit/

# Run with coverage
pytest --cov=civic_tracker tests/unit/
```

2. **Frontend Integration Tests**
```bash
# Run frontend tests
pytest tests/frontend/

# Run specific test file
pytest tests/frontend/test_official_search.py
```

3. **API Tests**
```bash
pytest tests/api/
```

### Code Quality Tools

1. **Linting**
```bash
# Run flake8
flake8 civic_tracker tests

# Run pylint
pylint civic_tracker
```

2. **Type Checking**
```bash
mypy civic_tracker
```

3. **Code Formatting**
```bash
# Format code with black
black civic_tracker tests

# Sort imports
isort civic_tracker tests
```

### Database Management

1. **Creating Migrations**
```bash
# After model changes, create a new migration
flask db migrate -m "Description of changes"

# Review the migration file in migrations/versions/
# Then apply it
flask db upgrade
```

2. **Reset Database**
```bash
flask db downgrade base
flask db upgrade
```

## Project Structure

```
civic_tracker/
├── civic_tracker/           # Main application package
│   ├── __init__.py         # App initialization
│   ├── models/             # Database models
│   ├── services/           # Business logic
│   ├── api/                # API endpoints
│   ├── templates/          # Jinja2 templates
│   └── static/             # Static files
├── tests/
│   ├── unit/              # Unit tests
│   ├── frontend/          # Frontend integration tests
│   └── api/               # API tests
├── migrations/            # Database migrations
├── scripts/              # Utility scripts
├── requirements.txt      # Core dependencies
└── requirements-test.txt # Test dependencies
```

## Production Setup

Follow the steps below to deploy the application in a production environment:

1. **Environment Configuration:**
   - Set `DEBUG` to `False`.
   - Configure the following environment variables for production:
     - `GOOGLE_API_KEY`
     - `CONGRESS_API_KEY`
     - `PROPUBLICA_API_KEY`
     - `CIVIC_INFO_API_URL` (if different from the default)
     - `DATABASE_URL` (recommended: use PostgreSQL or MySQL instead of SQLite)
   - Example `.env.production` file:
     ```
     DEBUG=False
     GOOGLE_API_KEY=your_production_google_api_key
     CONGRESS_API_KEY=your_production_congress_api_key
     PROPUBLICA_API_KEY=your_production_propublica_api_key
     CIVIC_INFO_API_URL=https://www.googleapis.com/civicinfo/v2
     DATABASE_URL=postgresql://user:password@host:port/dbname
     ```

2. **Database Setup:**
   - Run database migrations using:
     ```
     flask db upgrade
     ```
   - Consider using a production-grade database such as PostgreSQL or MySQL.

3. **WSGI Server Setup:**
   - Use a production-grade WSGI server (e.g., Gunicorn) to run the application:
     ```
     gunicorn app:app
     ```
   - Optionally, configure a reverse proxy (e.g., NGINX) to handle static assets and improve performance.

4. **Static Assets:**
   - Serve static assets through a dedicated web server like NGINX for improved speed and caching.

5. **Security:**
   - Ensure proper security headers are configured and SSL is enabled.
   - Securely store and manage your environment secrets.

6. **Logging & Monitoring:**
   - Configure detailed logging (to files or external log management systems) for effective monitoring.
   - Implement monitoring solutions to track server health and performance.

7. **Process Management:**
   - Use a process manager (e.g., Supervisor or systemd) to manage the application processes.
   - Regularly back up your database and update your dependencies for security.

## Common Development Tasks

### Adding a New Feature

1. Create a new branch
```bash
git checkout -b feature/new-feature
```

2. Implement the feature
   - Add tests first (TDD approach)
   - Implement the feature
   - Update documentation

3. Run quality checks
```bash
# Run all checks
./scripts/quality_checks.sh
```

4. Commit changes
```bash
git add .
git commit -m "feat: Add new feature"
```

### Updating Dependencies

1. Review and update `requirements.txt`
```bash
# Generate requirements from pip-tools
pip-compile requirements.in

# Sync virtual environment
pip-sync requirements.txt requirements-test.txt
```

2. Test after updates
```bash
pytest
```

### Working with the Database

1. **Connect to Database**
```bash
psql civic_tracker
```

2. **Backup Database**
```bash
pg_dump civic_tracker > backup.sql
```

3. **Restore Database**
```bash
psql civic_tracker < backup.sql
```

## Debugging

### VS Code Configuration

1. Create `.vscode/launch.json`:
```json
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Flask",
            "type": "python",
            "request": "launch",
            "module": "flask",
            "env": {
                "FLASK_APP": "civic_tracker",
                "FLASK_ENV": "development"
            },
            "args": [
                "run",
                "--no-debugger"
            ],
            "jinja": true
        }
    ]
}
```

2. Set breakpoints in VS Code
3. Start debugging session (F5)

### Using pdb

Insert breakpoints in code:
```python
import pdb; pdb.set_trace()
```

### Debug Logging

```python
import logging
logging.debug("Debug message")
```

## Performance Profiling

1. **Profile API Endpoints**
```bash
python -m cProfile -o output.prof scripts/profile_api.py
```

2. **View Results**
```bash
python -m snakeviz output.prof
```

## Documentation

### Building Documentation
```bash
# Install documentation dependencies
pip install -r docs/requirements.txt

# Build documentation
cd docs
make html
```

### API Documentation
Update API documentation when endpoints change:
1. Update `API.md`
2. Update OpenAPI specification in `docs/openapi.yaml`
3. Regenerate API documentation

## Troubleshooting

### Common Issues

1. **Database Connection Issues**
   - Check PostgreSQL service is running
   - Verify database exists
   - Check connection string in `.env`

2. **Test Failures**
   - Ensure test database exists
   - Check test dependencies are installed
   - Verify Chrome WebDriver is installed

3. **API Key Issues**
   - Verify keys in `.env`
   - Check API quotas
   - Use mock responses in development

### Getting Help

1. Check the [FAQ](FAQ.md)
2. Search existing GitHub issues
3. Ask in the development channel
4. Create a new issue with:
   - Error message
   - Steps to reproduce
   - Environment details
