#!/usr/bin/env python3
"""
AIVim - An AI-enhanced version of Vim implemented in Python
Web interface and API server
"""
import os
import logging
from flask import Flask, render_template, jsonify, request, send_from_directory

# Create Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key")

# Enable logging
logging.basicConfig(
    filename="aivim.log",
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

# Web application routes
@app.route('/')
def index():
    """Render the main web interface"""
    return render_template('index.html')

@app.route('/api/ai-assist', methods=['POST'])
def ai_assist():
    """Handle AI assistance requests from the web interface"""
    data = request.json
    action = data.get('action')
    code = data.get('code', '')
    context = data.get('context', '')
    
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
def check_api_key():
    """Check if the OPENAI_API_KEY is set"""
    has_key = bool(os.environ.get("OPENAI_API_KEY"))
    return jsonify({"has_key": has_key})

@app.route('/api/model-info', methods=['GET'])
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

@app.route('/static/<path:path>')
def send_static(path):
    """Serve static files"""
    return send_from_directory('static', path)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)