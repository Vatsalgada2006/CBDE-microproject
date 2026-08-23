import os
import sys
import json
from io import BytesIO

# Add current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import the Flask app
from app import app

def handler(event, context):
    """
    Vercel serverless function handler for Flask app
    """
    try:
        # Import Flask utilities
        from flask import request as flask_request

        # Create a Flask request context from the Vercel event
        with app.request_context(
            environ={
                'REQUEST_METHOD': event.get('httpMethod', 'GET'),
                'PATH_INFO': event.get('path', '/'),
                'QUERY_STRING': event.get('query', '') or '',
                'SERVER_PROTOCOL': 'HTTP/1.1',
                'wsgi.version': (1, 0),
                'wsgi.input': BytesIO(
                    event.get('body', '').encode('utf-8')
                    if event.get('body') is not None
                    else b''
                ),
                'wsgi.errors': sys.stderr,
                'wsgi.multithread': False,
                'wsgi.run_once': False,
                'wsgi.url_scheme': 'https',
                'REMOTE_ADDR': '127.0.0.1',
                'CONTENT_LENGTH': str(
                    len(event.get('body', ''))
                    if event.get('body') is not None
                    else 0
                ),
                'CONTENT_TYPE': (
                    event.get('headers', {}).get('content-type')
                    or event.get('headers', {}).get('Content-Type')
                    or 'application/octet-stream'
                ),
            }
        ):
            # Process the request with Flask
            response = app.full_dispatch_request()

            # Convert Flask response to Vercel format
            return {
                'statusCode': response.status_code,
                'headers': dict(response.headers),
                'body': response.get_data(as_text=True)
            }

    except Exception as e:
        # Return error response
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({
                'error': 'Internal Server Error',
                'message': str(e)
            })
        }

# Export the handler
# Note: Vercel looks for a function named 'handler' by default