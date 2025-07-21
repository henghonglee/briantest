#!/usr/bin/env python3
"""
Flask web application for ABB Product Search Interface.
"""

from flask import Flask, render_template, request, jsonify
from werkzeug.utils import secure_filename
import pandas as pd
import io
from fast_search import FastProductMatcher
from probabilistic_search import ProbabilisticProductMatcher
from config_manager import config_manager
import time
import traceback
import logging
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Database configuration
DATABASE_URL = os.environ.get('DATABASE_URL')
if DATABASE_URL:
    # Handle Render.com PostgreSQL URL format
    if DATABASE_URL.startswith('postgres://'):
        DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)
    app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
else:
    # Local development fallback
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///training_data.db'

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_recycle': 300,
    'pool_pre_ping': True
}

# Initialize database and search matchers
from models import db, init_db, TrainingData, migrate_csv_to_db
db.init_app(app)

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

@app.route('/api/training_data')
def get_training_data():
    """Get current training data for browsing."""
    try:
        # Try database first
        try:
            records = TrainingData.search_records(limit=1000)  # Limit for performance
            training_data = []
            for record in records:
                training_data.append({
                    'id': record.id,
                    'index': record.id,  # For backward compatibility
                    'customer_query': record.customer_query,
                    'order_code': record.order_code,
                    'description': record.description
                })
            
            return jsonify({
                'success': True,
                'data': training_data,
                'total_rows': len(training_data),
                'source': 'database'
            })
            
        except Exception as db_error:
            print(f"Database query failed: {db_error}")
            # Fallback to file-based loading
            from resource_utils import load_training_data
            
            df = load_training_data()
            training_data = []
            for idx, row in df.iterrows():
                training_data.append({
                    'index': int(idx),
                    'customer_query': row.get('Customer Query', ''),
                    'order_code': row.get('Order Code', ''),
                    'description': row.get('Description', '')
                })
            
            return jsonify({
                'success': True,
                'data': training_data,
                'total_rows': len(training_data),
                'source': 'file_fallback'
            })
        
    except Exception as e:
        print(f"Error loading training data: {e}")
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': f'Failed to load training data: {str(e)}'
        }), 500

@app.route('/api/training_data/upload', methods=['POST'])
def upload_training_data():
    """Upload and append new training data from CSV file."""
    try:
        if 'file' not in request.files:
            return jsonify({
                'success': False,
                'error': 'No file provided'
            }), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({
                'success': False,
                'error': 'No file selected'
            }), 400
        
        if not file.filename.lower().endswith('.csv'):
            return jsonify({
                'success': False,
                'error': 'Only CSV files are allowed'
            }), 400
        
        # Read the uploaded CSV
        try:
            csv_content = file.read().decode('utf-8')
            new_df = pd.read_csv(io.StringIO(csv_content))
        except Exception as e:
            return jsonify({
                'success': False,
                'error': f'Failed to parse CSV file: {str(e)}'
            }), 400
        
        # Validate required columns
        required_columns = ['Customer Query', 'Order Code', 'Description']
        missing_columns = [col for col in required_columns if col not in new_df.columns]
        if missing_columns:
            return jsonify({
                'success': False,
                'error': f'Missing required columns: {", ".join(missing_columns)}'
            }), 400
        
        # Try database insertion first
        try:
            result = TrainingData.bulk_insert_from_dataframe(new_df[required_columns], skip_duplicates=True)
            print(f"✅ Database insert: {result['added']} added, {result['duplicates']} duplicates")
            
            # Update the fast search matcher if available
            if search_matcher:
                df = TrainingData.get_all_as_dataframe()
                search_matcher.training_data = df
                search_matcher.load_data_and_prepare()
                print("✅ Updated search matcher with new training data")
            
            total_rows = TrainingData.get_total_count()
            
            return jsonify({
                'success': True,
                'message': f'Successfully uploaded {result["added"]} rows',
                'new_rows': result['added'],
                'total_rows': total_rows,
                'duplicates_removed': result['duplicates'],
                'storage': 'database'
            })
            
        except Exception as db_error:
            print(f"Database insert failed: {db_error}")
            # Fallback to file-based storage
            from resource_utils import load_training_data, get_training_csv_path
            existing_df = load_training_data()
            
            # Append new data
            combined_df = pd.concat([existing_df, new_df[required_columns]], ignore_index=True)
            
            # Remove duplicates based on Customer Query and Order Code
            combined_df = combined_df.drop_duplicates(subset=['Customer Query', 'Order Code'], keep='first')
            
            # Save back to local file (if it exists locally)
            try:
                training_path = get_training_csv_path()
                if training_path != "REMOTE_TRAINING_DATA":
                    combined_df.to_csv(training_path, index=False)
                    print(f"✅ Updated local training file with {len(new_df)} new rows")
            except Exception as e:
                print(f"⚠️ Could not save to local file: {e}")
            
            # Update the fast search matcher if available
            if search_matcher:
                search_matcher.training_data = combined_df
                search_matcher.load_data_and_prepare()
                print("✅ Updated search matcher with new training data")
            
            return jsonify({
                'success': True,
                'message': f'Successfully uploaded {len(new_df)} rows (file fallback)',
                'new_rows': len(new_df),
                'total_rows': len(combined_df),
                'duplicates_removed': len(existing_df) + len(new_df) - len(combined_df),
                'storage': 'file_fallback'
            })
        
    except Exception as e:
        print(f"Upload training data error: {e}")
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': f'Failed to upload training data: {str(e)}'
        }), 500

@app.route('/api/training_data/delete', methods=['POST'])
def delete_training_row():
    """Delete a specific row from training data."""
    try:
        data = request.get_json()
        record_id = data.get('index') or data.get('id')
        
        if record_id is None:
            return jsonify({
                'success': False,
                'error': 'Row ID is required'
            }), 400
        
        # Try database deletion first
        try:
            success = TrainingData.delete_by_id(record_id)
            if success:
                print(f"✅ Deleted record {record_id} from database")
                
                # Update the fast search matcher if available
                if search_matcher:
                    df = TrainingData.get_all_as_dataframe()
                    search_matcher.training_data = df
                    search_matcher.load_data_and_prepare()
                    print("✅ Updated search matcher after row deletion")
                
                remaining_rows = TrainingData.get_total_count()
                
                return jsonify({
                    'success': True,
                    'message': f'Successfully deleted record {record_id}',
                    'remaining_rows': remaining_rows,
                    'storage': 'database'
                })
            else:
                return jsonify({
                    'success': False,
                    'error': 'Record not found'
                }), 404
                
        except Exception as db_error:
            print(f"Database delete failed: {db_error}")
            # Fallback to file-based deletion
            from resource_utils import load_training_data, get_training_csv_path
            df = load_training_data()
            
            row_index = int(record_id)
            if row_index < 0 or row_index >= len(df):
                return jsonify({
                    'success': False,
                    'error': 'Invalid row index'
                }), 400
            
            # Remove the specified row
            df = df.drop(df.index[row_index]).reset_index(drop=True)
            
            # Save back to local file (if it exists locally)
            try:
                training_path = get_training_csv_path()
                if training_path != "REMOTE_TRAINING_DATA":
                    df.to_csv(training_path, index=False)
                    print(f"✅ Deleted row {row_index} from local training file")
            except Exception as e:
                print(f"⚠️ Could not save to local file: {e}")
            
            # Update the fast search matcher if available
            if search_matcher:
                search_matcher.training_data = df
                search_matcher.load_data_and_prepare()
                print("✅ Updated search matcher after row deletion")
            
            return jsonify({
                'success': True,
                'message': f'Successfully deleted row {row_index} (file fallback)',
                'remaining_rows': len(df),
                'storage': 'file_fallback'
            })
        
    except Exception as e:
        print(f"Delete training row error: {e}")
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': f'Failed to delete training row: {str(e)}'
        }), 500

@app.route('/training')
def training_management():
    """Training data management page."""
    return render_template('training_management.html')

# Initialize database and matchers on startup for production
setup_logging()
print("🚀 ABB Product Search Starting...")
print(f"Configuration loaded from: {config_manager.config_path or 'defaults'}")
print(f"Data directory: {config_manager.get('data_dir')}")
print(f"Models directory: {config_manager.get('models_dir')}")

# Initialize database
try:
    with app.app_context():
        init_db(app)
        
        # Migrate existing CSV data if database is empty
        if TrainingData.get_total_count() == 0:
            print("🔄 Database is empty, attempting CSV migration...")
            try:
                from resource_utils import get_training_csv_path
                training_path = get_training_csv_path()
                if training_path != "REMOTE_TRAINING_DATA" and os.path.exists(training_path):
                    migrate_csv_to_db(training_path, app)
                else:
                    print("⚠️  No local CSV file found for migration")
            except Exception as migration_error:
                print(f"⚠️  CSV migration failed: {migration_error}")
        
except Exception as db_error:
    print(f"⚠️  Database initialization failed: {db_error}")
    print("📌 App will run with file/remote fallback mode")

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