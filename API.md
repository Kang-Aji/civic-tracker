# Civic Tracker API Documentation

This document provides comprehensive documentation for the Civic Tracker API endpoints.

## Base URL

All API endpoints are relative to:
```
http://localhost:5000/api/v1
```

## Authentication

Currently, the API is open and does not require authentication. Rate limiting may apply.

## Endpoints

### Officials

#### Get Officials by Address
```http
GET /officials/search
```

Query Parameters:
- `address` (required): Full address or zip code
- `level` (optional): Filter by government level (federal, state, local)

Response:
```json
{
    "officials": [
        {
            "id": "string",
            "name": "string",
            "office": "string",
            "level": "string",
            "party": "string",
            "phone": "string",
            "url": "string",
            "photoUrl": "string",
            "address": {
                "line1": "string",
                "line2": "string",
                "city": "string",
                "state": "string",
                "zip": "string"
            },
            "channels": [
                {
                    "type": "string",
                    "id": "string"
                }
            ]
        }
    ]
}
```

#### Get Official Details
```http
GET /officials/{official_id}
```

Response includes all official information plus recent actions.

### Actions

#### Get Official Actions
```http
GET /officials/{official_id}/actions
```

Query Parameters:
- `timeframe` (optional): Filter by time period (7d, 30d, 90d, 1y)
- `type` (optional): Filter by action type (bills, press, news)
- `page` (optional): Page number for pagination
- `per_page` (optional): Items per page (default: 20)

Response:
```json
{
    "actions": [
        {
            "id": "string",
            "type": "string",
            "title": "string",
            "description": "string",
            "date": "string",
            "url": "string",
            "source": "string"
        }
    ],
    "pagination": {
        "current_page": 1,
        "total_pages": 10,
        "total_items": 195,
        "per_page": 20
    }
}
```

#### Get Action Details
```http
GET /actions/{action_id}
```

Response includes detailed information about a specific action.

### Sources

#### Add Action Source
```http
POST /officials/{official_id}/sources
```

Request Body:
```json
{
    "source_type": "string",
    "source_url": "string",
    "update_frequency": "string"
}
```

- `source_type`: One of: rss, website, api, bills
- `source_url`: URL of the source
- `update_frequency`: How often to check for updates (hourly, daily, weekly)

#### List Official Sources
```http
GET /officials/{official_id}/sources
```

Response:
```json
{
    "sources": [
        {
            "id": "string",
            "type": "string",
            "url": "string",
            "last_updated": "string",
            "update_frequency": "string",
            "status": "string"
        }
    ]
}
```

#### Update Source
```http
PUT /sources/{source_id}
```

Request Body:
```json
{
    "source_url": "string",
    "update_frequency": "string"
}
```

#### Delete Source
```http
DELETE /sources/{source_id}
```

### Statistics

#### Get Official Statistics
```http
GET /officials/{official_id}/stats
```

Response:
```json
{
    "total_actions": 123,
    "actions_by_type": {
        "bills": 45,
        "press": 38,
        "news": 40
    },
    "actions_by_timeframe": {
        "7d": 5,
        "30d": 25,
        "90d": 75
    }
}
```

## Error Responses

The API uses standard HTTP status codes and returns error details in JSON format:

```json
{
    "error": {
        "code": "string",
        "message": "string",
        "details": {}
    }
}
```

Common Error Codes:
- `400`: Bad Request - Invalid parameters
- `404`: Not Found - Resource doesn't exist
- `429`: Too Many Requests - Rate limit exceeded
- `500`: Internal Server Error - Server-side error

## Rate Limiting

- Rate limit: 100 requests per minute per IP
- Headers included in responses:
  - `X-RateLimit-Limit`: Total requests allowed per window
  - `X-RateLimit-Remaining`: Requests remaining in current window
  - `X-RateLimit-Reset`: Time when the rate limit resets

## Webhooks

### Register Webhook
```http
POST /webhooks
```

Request Body:
```json
{
    "url": "string",
    "events": ["action.created", "action.updated"],
    "official_id": "string"
}
```

### List Webhooks
```http
GET /webhooks
```

### Delete Webhook
```http
DELETE /webhooks/{webhook_id}
```

## Data Formats

### Date Format
All dates are in ISO 8601 format: `YYYY-MM-DDTHH:mm:ssZ`

### Action Types
- `bills`: Bill sponsorship or co-sponsorship
- `press`: Press releases
- `news`: News mentions
- `votes`: Voting records
- `statements`: Public statements
- `events`: Public events

### Government Levels
- `federal`: Federal government officials
- `state`: State government officials
- `local`: Local government officials

## SDK Support

Official SDKs are available for:
- Python: `pip install civic-tracker-python`
- JavaScript: `npm install civic-tracker-js`
- Ruby: `gem install civic-tracker-ruby`

## Best Practices

1. Use appropriate caching strategies
2. Implement exponential backoff for failed requests
3. Handle rate limiting appropriately
4. Use webhook events for real-time updates
5. Paginate results for large data sets

## Support

For API support:
- Email: api-support@civictracker.com
- Documentation: https://docs.civictracker.com
- Issue Tracker: https://github.com/civic-tracker/issues
