#!/usr/bin/env python3
"""
Flask web application for ABB Product Search Interface.
"""

from flask import Flask, render_template, request, jsonify
from fast_search import FastProductMatcher
from probabilistic_search import ProbabilisticProductMatcher
from config_manager import config_manager
import time
import traceback
import logging
import os

app = Flask(__name__)

# Initialize search matchers
search_matcher = None
prob_matcher = None

def setup_logging():
    """Setup logging configuration."""
    try:
        log_dir = config_manager.get('logs_dir')
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)
        
        log_file = os.path.join(log_dir, 'app.log') if log_dir else 'app.log'
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )
    except Exception as e:
        print(f"⚠️  Could not setup logging: {e}")

def initialize_matcher():
    """Initialize the search matchers."""
    global search_matcher, prob_matcher
    try:
        # Ensure directories exist
        config_manager.ensure_directories_exist()
        
        print("Initializing FastProductMatcher...")
        search_matcher = FastProductMatcher()
        search_matcher.load_model()
        print("✅ Fast search matcher initialized successfully")
        
        print("Initializing ProbabilisticProductMatcher...")
        prob_matcher = ProbabilisticProductMatcher()
        prob_matcher.load_model()
        print("✅ Probabilistic matcher initialized successfully")
        
        return True
    except Exception as e:
        print(f"❌ Failed to initialize matchers: {e}")
        logging.error(f"Failed to initialize matchers: {e}")
        traceback.print_exc()
        return False

@app.route('/')
def index():
    """Main search page."""
    return render_template('index.html')

@app.route('/api/search', methods=['POST'])
def api_search():
    """API endpoint for search requests."""
    try:
        data = request.get_json()
        query = data.get('query', '').strip()
        top_k = min(data.get('top_k', 10), 20)  # Limit to max 20 results
        
        if not query:
            return jsonify({
                'success': False,
                'error': 'Query cannot be empty'
            }), 400
        
        if not search_matcher:
            return jsonify({
                'success': False,
                'error': 'Search service not available'
            }), 503
        
        # Perform search
        start_time = time.time()
        results = search_matcher.search_fast(query, top_k)
        search_time = time.time() - start_time
        
        # Format results for frontend
        formatted_results = []
        for result in results:
            formatted_results.append({
                'order_code': result['order_code'],
                'description': result['description'],
                'training_query': result.get('training_query', ''),
                'probability': round(result['probability'], 3),
                'tfidf_score': round(result.get('tfidf_score', 0), 3),
                'fuzzy_score': round(result.get('fuzzy_score', 0), 3),
                'match_type': result.get('match_type', 'fuzzy')
            })
        
        return jsonify({
            'success': True,
            'results': formatted_results,
            'search_time': round(search_time, 3),
            'query': query,
            'total_results': len(formatted_results)
        })
        
    except Exception as e:
        print(f"Search error: {e}")
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': f'Search failed: {str(e)}'
        }), 500

@app.route('/api/health')
def health_check():
    """Health check endpoint."""
    return jsonify({
        'status': 'healthy' if search_matcher else 'unhealthy',
        'matcher_ready': search_matcher is not None
    })

@app.route('/api/add_training', methods=['POST'])
def add_training():
    """API endpoint to add training data."""
    try:
        data = request.get_json()
        query = data.get('query', '').strip()
        order_code = data.get('order_code', '').strip()
        description = data.get('description', '').strip()
        
        if not query or not order_code or not description:
            return jsonify({
                'success': False,
                'error': 'Query, order code, and description are required'
            }), 400
        
        if not search_matcher:
            return jsonify({
                'success': False,
                'error': 'Search service not available'
            }), 503
        
        # Add the training example
        success = search_matcher.add_training_example(query, order_code, description)
        
        if success:
            return jsonify({
                'success': True,
                'message': f'Training example added successfully: "{query}" -> "{order_code}"'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to add training example'
            }), 500
            
    except Exception as e:
        print(f"Add training error: {e}")
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': f'Failed to add training data: {str(e)}'
        }), 500

@app.route('/api/probability_score', methods=['POST'])
def probability_score():
    """API endpoint to get probability scores for specific results."""
    try:
        data = request.get_json()
        query = data.get('query', '').strip()
        results = data.get('results', [])
        
        if not query or not results:
            return jsonify({
                'success': False,
                'error': 'Query and results are required'
            }), 400
        
        if not prob_matcher:
            return jsonify({
                'success': False,
                'error': 'Probability model not available'
            }), 503
        
        # Calculate probability scores for each result
        scored_results = []
        for result in results:
            order_code = result.get('order_code', '')
            description = result.get('description', '')
            
            try:
                prob_score = prob_matcher.predict_probability(query, description, order_code)
                scored_results.append({
                    'order_code': order_code,
                    'probability_score': round(prob_score, 3)
                })
            except Exception as e:
                print(f"Error scoring {order_code}: {e}")
                scored_results.append({
                    'order_code': order_code,
                    'probability_score': None,
                    'error': str(e)
                })
        
        return jsonify({
            'success': True,
            'scores': scored_results
        })
        
    except Exception as e:
        print(f"Probability scoring error: {e}")
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': f'Probability scoring failed: {str(e)}'
        }), 500

# Initialize matchers on startup for production
setup_logging()
print("🚀 ABB Product Search Starting...")
print(f"Configuration loaded from: {config_manager.config_path or 'defaults'}")
print(f"Data directory: {config_manager.get('data_dir')}")
print(f"Models directory: {config_manager.get('models_dir')}")

# Initialize the search matcher
if not initialize_matcher():
    print("⚠️  Failed to initialize matchers, but continuing...")
    print("📌 App will run in limited mode - add training data via API")

if __name__ == '__main__':
    host = config_manager.get('host', '0.0.0.0')
    port = int(os.environ.get('PORT', config_manager.get('port', 5001)))
    debug = config_manager.get('debug', False)
    
    print(f"🚀 Starting Flask web server on {host}:{port}...")
    print(f"🌐 Application will be available at: http://localhost:{port}")
    print("Press Ctrl+C to stop the server")
    
    try:
        app.run(debug=debug, host=host, port=port)
    except KeyboardInterrupt:
        print("\n👋 Server stopped by user")
    except Exception as e:
        print(f"❌ Server error: {e}")
        logging.error(f"Server error: {e}")