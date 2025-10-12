#!/usr/bin/env python3
"""
AIVim - An AI-enhanced version of Vim implemented in Python
Web interface and API server
"""
import os
import logging
import secrets
import re
from datetime import datetime, timedelta
from collections import deque
from flask import Flask, render_template, jsonify, request, send_from_directory
from functools import wraps

# Create Flask app
app = Flask(__name__)

# Rate limiting configuration
class RateLimiter:
    """Simple in-memory rate limiter"""
    def __init__(self, max_calls=20, window_seconds=60):
        self.max_calls = max_calls
        self.window_seconds = window_seconds
        self.call_history = {}

    def is_allowed(self, client_id):
        """Check if client is within rate limit"""
        now = datetime.now()
        cutoff = now - timedelta(seconds=self.window_seconds)

        # Initialize or clean old entries
        if client_id not in self.call_history:
            self.call_history[client_id] = deque()

        client_calls = self.call_history[client_id]

        # Remove calls outside the window
        while client_calls and client_calls[0] < cutoff:
            client_calls.popleft()

        # Check if under limit
        if len(client_calls) >= self.max_calls:
            return False

        # Record this call
        client_calls.append(now)
        return True

# Initialize rate limiter (20 calls per minute)
rate_limiter = RateLimiter(max_calls=20, window_seconds=60)

def rate_limit(f):
    """Rate limiting decorator"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        client_id = request.remote_addr
        if not rate_limiter.is_allowed(client_id):
            return jsonify({"error": "Rate limit exceeded. Please try again later."}), 429
        return f(*args, **kwargs)
    return decorated_function

# Security: Require SESSION_SECRET in production, generate random key for dev
app.secret_key = os.environ.get("SESSION_SECRET")
if not app.secret_key:
    if os.environ.get("FLASK_ENV") == "production":
        raise ValueError("SESSION_SECRET environment variable must be set in production")
    # Only use random key in development
    app.secret_key = secrets.token_hex(32)
    logging.warning("Using temporary session secret for development only")

# Enable logging with configurable level
LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO').upper()
LOG_FILE = os.environ.get('LOG_FILE', 'aivim.log')

logging.basicConfig(
    filename=LOG_FILE,
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

# Add filter to redact sensitive data from logs
class SensitiveDataFilter(logging.Filter):
    def filter(self, record):
        # Redact API keys from log messages
        if hasattr(record, 'msg'):
            record.msg = re.sub(
                r'(api[_-]?key["\']?\s*[:=]\s*["\']?)([^"\'}\s]+)',
                r'\1***REDACTED***',
                str(record.msg),
                flags=re.IGNORECASE
            )
        return True

logging.getLogger().addFilter(SensitiveDataFilter())

# Web application routes
@app.route('/')
def index():
    """Render the main web interface"""
    return render_template('index.html')

@app.route('/api/ai-assist', methods=['POST'])
@rate_limit
def ai_assist():
    """Handle AI assistance requests from the web interface"""
    # Validate Content-Type
    if not request.is_json:
        return jsonify({"error": "Content-Type must be application/json"}), 415

    data = request.json or {}

    # Validate required fields
    if 'action' not in data:
        return jsonify({"error": "Missing required field: action"}), 400

    action = data.get('action')
    code = data.get('code', '')
    context = data.get('context', '')

    # Validate input length (prevent DoS with large payloads)
    MAX_CODE_LENGTH = 50000  # ~50KB
    if len(code) > MAX_CODE_LENGTH or len(context) > MAX_CODE_LENGTH:
        return jsonify({"error": "Input too large. Maximum size is 50KB per field."}), 413
    
    # Create an instance of the AI service
    from aivim.ai_service import AIService
    ai_service = AIService()
    
    if action == 'explain':
        result = ai_service.get_explanation(code, context)
    elif action == 'improve':
        result = ai_service.get_improvement(code, context)
    elif action == 'generate':
        spec = data.get('specification', '')
        result = ai_service.generate_code(spec, context)
    elif action == 'query':
        query = data.get('query', '')
        result = ai_service.custom_query(query, context)
    elif action == 'analyze':
        result = ai_service.analyze_code(code, context)
    else:
        return jsonify({"error": "Invalid action"}), 400
        
    return jsonify({"result": result})

@app.route('/api/check-api-key', methods=['GET'])
@rate_limit
def check_api_key():
    """Check if the OPENAI_API_KEY is set"""
    has_key = bool(os.environ.get("OPENAI_API_KEY"))
    return jsonify({"has_key": has_key})

@app.route('/api/model-info', methods=['GET'])
@rate_limit
def get_model_info():
    """Get information about the currently configured AI model"""
    # Create an instance of the AI service
    from aivim.ai_service import AIService
    ai_service = AIService()
    
    # Get model information
    model_info = ai_service.get_current_model_info()
    config_status = ai_service.get_config_status()
    is_configured = ai_service.is_model_configured()
    
    return jsonify({
        "model": model_info,
        "config_status": config_status,
        "is_configured": is_configured
    })

@app.route('/api/set-model', methods=['POST'])
@rate_limit
def set_model():
    """Set the AI model to use"""
    # Validate Content-Type
    if not request.is_json:
        return jsonify({"error": "Content-Type must be application/json"}), 415

    data = request.json or {}
    model_name = data.get('model')
    
    if not model_name:
        return jsonify({"success": False, "message": "Model name is required"}), 400
        
    # Validate model name
    valid_models = ['openai', 'claude', 'local']
    if model_name not in valid_models:
        return jsonify({"success": False, "message": f"Invalid model. Must be one of: {', '.join(valid_models)}"}), 400
    
    try:
        # Create an instance of the AI service
        from aivim.ai_service import AIService
        ai_service = AIService()
        
        # Set the model
        ai_service.set_model(model_name)
        
        # Save the model setting for future sessions
        # Note: AIService might not have save_config method in all versions
        try:
            if hasattr(ai_service, 'save_config') and callable(getattr(ai_service, 'save_config')):
                ai_service.save_config()
        except Exception as e:
            logging.warning(f"Could not save model configuration: {str(e)}")
            # Continue anyway as the model will be set for this session
        
        return jsonify({"success": True, "model": model_name})
    except Exception as e:
        logging.error(f"Error setting model: {str(e)}")
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/static/<path:path>')
def send_static(path):
    """Serve static files"""
    return send_from_directory('static', path)

if __name__ == "__main__":
    DEBUG = os.environ.get('FLASK_DEBUG', 'False').lower() in ('true', '1', 'yes')

    if DEBUG:
        logging.warning("Running in DEBUG mode. Never use this in production!")

    app.run(
        host=os.environ.get('FLASK_HOST', '127.0.0.1'),  # Don't default to 0.0.0.0
        port=int(os.environ.get('FLASK_PORT', '5000')),
        debug=DEBUG
    )