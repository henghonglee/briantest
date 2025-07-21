#!/usr/bin/env python3
"""
Flask web application for ABB Product Search Interface.
"""

from flask import Flask, render_template, request, jsonify
from werkzeug.utils import secure_filename
import pandas as pd
import io
from src.search import FastProductMatcher, ProbabilisticProductMatcher
from src.utils import config_manager
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
ENVIRONMENT = os.environ.get('ENVIRONMENT', 'development')

if DATABASE_URL:
    # Production: Use PostgreSQL from environment variable
    if DATABASE_URL.startswith('postgres://'):
        DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)
    app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
    print(f"🐘 Using PostgreSQL database in {ENVIRONMENT} environment")
else:
    # Development: Use SQLite
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///training_data.db'
    print(f"📄 Using SQLite database in {ENVIRONMENT} environment")

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_recycle': 300,
    'pool_pre_ping': True
}

# Initialize database and search matchers
from src.models import db, init_db, TrainingData, migrate_csv_to_db
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
        
        # Train the model if it's not already trained
        if not prob_matcher.is_trained:
            print("⚠️ Probabilistic model not trained, training now...")
            prob_matcher.train()
            print("✅ Probabilistic model training completed")
        
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

@app.route('/api/catalog_search', methods=['POST'])
def api_catalog_search():
    """API endpoint for fuzzy search against full product catalog."""
    try:
        data = request.get_json()
        query = data.get('query', '').strip()
        top_k = min(data.get('top_k', 10), 3000)  # Allow up to 3000 results for catalog search
        
        if not query:
            return jsonify({
                'success': False,
                'error': 'Query cannot be empty'
            }), 400
        
        # Load catalog data
        from src.utils import load_catalog_data
        catalog_df = load_catalog_data()
        
        if catalog_df.empty:
            return jsonify({
                'success': False,
                'error': 'Product catalog not available'
            }), 503
        
        # Perform fuzzy search against catalog
        start_time = time.time()
        results = perform_catalog_fuzzy_search(query, catalog_df, top_k)
        search_time = time.time() - start_time
        
        return jsonify({
            'success': True,
            'results': results,
            'search_time': round(search_time, 3),
            'query': query,
            'total_results': len(results),
            'catalog_size': len(catalog_df)
        })
        
    except Exception as e:
        print(f"Catalog search error: {e}")
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': f'Catalog search failed: {str(e)}'
        }), 500

def perform_catalog_fuzzy_search(query, catalog_df, top_k):
    """Perform fuzzy search against the full product catalog."""
    from rapidfuzz import fuzz
    import pandas as pd
    
    results = []
    query_lower = query.lower()
    
    # Search through descriptions and order codes
    for idx, row in catalog_df.iterrows():
        order_code = str(row.get('Order Code', ''))
        description = str(row.get('Description', ''))
        
        # Skip empty entries
        if not order_code or not description or order_code == 'nan' or description == 'nan':
            continue
        
        # Calculate fuzzy scores
        desc_score = fuzz.partial_ratio(query_lower, description.lower())
        code_score = fuzz.partial_ratio(query_lower, order_code.lower())
        
        # Use the higher score
        max_score = max(desc_score, code_score)
        
        # Only include results with reasonable similarity (>= 30% for broader search)
        if max_score >= 30:
            # Find the actual matched words
            matched_text = description if desc_score > code_score else order_code
            # Extract the matched words/phrases
            import re
            query_words = query_lower.split()
            text_lower = matched_text.lower()
            matched_words = []
            for word in query_words:
                if len(word) > 2:  # Skip very short words
                    pattern = r'\b' + re.escape(word) + r'\w*'
                    matches = re.findall(pattern, text_lower)
                    matched_words.extend(matches)
            
            results.append({
                'order_code': order_code,
                'description': description,
                'fuzzy_score': round(max_score / 100, 3),
                'match_type': 'catalog_fuzzy',
                'match_field': 'description' if desc_score > code_score else 'order_code',
                'matched_words': ' '.join(set(matched_words)) if matched_words else 'combined'
            })
    
    # Sort by fuzzy score (highest first) and return top_k
    results.sort(key=lambda x: x['fuzzy_score'], reverse=True)
    return results[:top_k]

@app.route('/api/database_info')
def database_info():
    """Get database connection information."""
    try:
        from sqlalchemy import create_engine
        from sqlalchemy.exc import OperationalError
        
        # Get database URL
        database_url = os.getenv('DATABASE_URL', 'sqlite:///instance/training_data.db')
        
        # Determine database type
        if database_url.startswith('postgresql://'):
            db_type = 'PostgreSQL'
        elif database_url.startswith('sqlite:///'):
            db_type = 'SQLite'
        elif database_url.startswith('mysql://'):
            db_type = 'MySQL'
        else:
            db_type = 'Other'
        
        # Test connection
        try:
            engine = create_engine(database_url)
            with engine.connect() as conn:
                conn.execute("SELECT 1")
            status = 'Connected'
        except Exception:
            status = 'Disconnected'
        
        # Clean connection string for display
        connection_display = database_url
        if 'password' in database_url.lower():
            # Hide password in connection string
            import re
            connection_display = re.sub(r':[^@]+@', ':***@', connection_display)
        elif database_url.startswith('sqlite:///'):
            connection_display = database_url.replace('sqlite:///', '')
        
        return jsonify({
            'success': True,
            'database_type': db_type,
            'connection_string': connection_display,
            'status': status,
            'full_connection': database_url
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/download_remote_training_data', methods=['POST'])
def download_remote_training_data():
    """Download training data from remote source and replace local data."""
    try:
        from src.utils.remote_data_loader import RemoteDataLoader
        from src.models.models import TrainingData
        
        loader = RemoteDataLoader()
        remote_data = loader.load_training_data()
        
        if remote_data is None or remote_data.empty:
            return jsonify({
                'success': False,
                'error': 'No training data available from remote source'
            }), 404
        
        # Clear existing training data
        TrainingData.clear_all()
        
        # Add remote data to database
        rows_added = 0
        for _, row in remote_data.iterrows():
            success = TrainingData.create(
                customer_query=row['Customer Query'],
                order_code=row['Order Code'],
                description=row['Description']
            )
            if success:
                rows_added += 1
        
        # Update search matcher and retrain models
        if search_matcher and rows_added > 0:
            df = TrainingData.get_all_as_dataframe()
            search_matcher.training_data = df
            search_matcher.load_data_and_prepare()
            retrain_fast_search_model()
        
        return jsonify({
            'success': True,
            'message': f'Downloaded {rows_added} training examples from remote source',
            'rows_downloaded': rows_added
        })
        
    except Exception as e:
        print(f"Download remote training data error: {e}")
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': f'Failed to download remote training data: {str(e)}'
        }), 500



@app.route('/download/<path:filename>')
def download_file(filename):
    """Download any file from the server."""
    try:
        import os
        from flask import send_file
        
        # Security: only allow downloads from specific directories
        allowed_dirs = ['models', 'data', 'src/models', 'instance']
        
        file_path = os.path.join(os.path.dirname(__file__), filename)
        
        # Ensure file exists and is in allowed directory
        if not os.path.exists(file_path):
            return jsonify({'error': 'File not found'}), 404
        
        # Check if file is in allowed directory
        file_dir = os.path.dirname(os.path.abspath(file_path))
        base_dir = os.path.dirname(os.path.abspath(__file__))
        
        if not file_dir.startswith(base_dir):
            return jsonify({'error': 'Access denied'}), 403
        
        return send_file(file_path, as_attachment=True)
        
    except Exception as e:
        print(f"Download file error: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

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
    global search_matcher
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
        
        # Add to database first
        try:
            # Check for duplicates
            existing = TrainingData.query.filter_by(
                customer_query=query,
                order_code=order_code
            ).first()
            
            if existing:
                return jsonify({
                    'success': False,
                    'error': f'Training example already exists: "{query}" -> "{order_code}"'
                }), 400
            
            # Create new training record
            new_record = TrainingData(
                customer_query=query,
                order_code=order_code,
                description=description
            )
            
            db.session.add(new_record)
            db.session.commit()
            print(f"✅ Added training example to database: '{query}' -> '{order_code}'")
            
        except Exception as db_error:
            print(f"Database insert failed: {db_error}")
            return jsonify({
                'success': False,
                'error': f'Failed to add training example to database: {str(db_error)}'
            }), 500
        
        # Update the search matcher with fresh data
        if search_matcher:
            try:
                print("🔄 Updating search matcher with new training data...")
                from src.search import FastProductMatcher
                search_matcher = FastProductMatcher()
                
                # Load fresh data from database
                df = TrainingData.get_all_as_dataframe()
                print(f"📊 Loaded {len(df)} training examples including new one")
                
                search_matcher.training_data = df
                search_matcher._rebuild_embeddings()
                search_matcher.save_model()
                print("✅ Search matcher updated successfully")
                
            except Exception as update_error:
                print(f"⚠️ Warning: Failed to update search matcher: {update_error}")
        
        return jsonify({
            'success': True,
            'message': f'Training example added successfully: "{query}" -> "{order_code}"',
            'model_updated': True
        })
            
    except Exception as e:
        print(f"Add training error: {e}")
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': f'Failed to add training data: {str(e)}'
        }), 500

def retrain_fast_search_model():
    """Retrain the fast search model after training data changes."""
    try:
        global search_matcher
        
        if search_matcher:
            print("🔄 Retraining fast search model...")
            # Get fresh data from database
            df = TrainingData.get_all_as_dataframe()
            search_matcher.training_data = df
            search_matcher._rebuild_embeddings()
            search_matcher.save_model()
            print("✅ Fast search model retrained successfully")
            return True
        else:
            print("❌ No search matcher available to retrain")
            return False
    except Exception as e:
        print(f"❌ Failed to retrain fast search model: {e}")
        traceback.print_exc()
        return False

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
            from src.utils import load_training_data
            
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
            from src.utils import load_training_data, get_training_csv_path
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
    global search_matcher
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
            # Check if record exists before deletion
            record = TrainingData.query.get(record_id)
            if record:
                print(f"📋 Found record {record_id}: '{record.customer_query}' -> {record.order_code}")
            
            success = TrainingData.delete_by_id(record_id)
            if success:
                print(f"✅ Deleted record {record_id} from database")
                
                # Update the fast search matcher and retrain models
                if search_matcher:
                    # Force a complete reload of the search matcher
                    print("🔄 Forcing complete reload of search matcher...")
                    
                    from src.search import FastProductMatcher
                    search_matcher = FastProductMatcher()
                    
                    # Load fresh data from database
                    df = TrainingData.get_all_as_dataframe()
                    print(f"📊 Fresh training data loaded: {len(df)} rows")
                    
                    # Check if the deleted record is still in the dataframe
                    if record:
                        still_exists = df[df['Customer Query'] == record.customer_query]
                        if not still_exists.empty:
                            print(f"⚠️  WARNING: Deleted record still found in training data!")
                        else:
                            print(f"✅ Confirmed: Deleted record no longer in training data")
                    
                    # Set the training data and rebuild embeddings
                    search_matcher.training_data = df
                    search_matcher._rebuild_embeddings()
                    search_matcher.save_model()
                    print("✅ Search matcher completely reloaded after row deletion")
                
                remaining_rows = TrainingData.get_total_count()
                
                return jsonify({
                    'success': True,
                    'message': f'Successfully deleted record {record_id}',
                    'remaining_rows': remaining_rows,
                    'storage': 'database',
                    'model_retrained': True
})
            else:
                return jsonify({
                    'success': False,
                    'error': 'Record not found'
                }), 404
                
        except Exception as db_error:
            print(f"Database delete failed: {db_error}")
            # Fallback to file-based deletion
            from src.utils import load_training_data, get_training_csv_path
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
            
            # Update the fast search matcher and retrain models
            if search_matcher:
                # Force a complete reload of the search matcher
                print("🔄 Forcing complete reload of search matcher (file fallback)...")
                
                from src.search import FastProductMatcher
                search_matcher = FastProductMatcher()
                search_matcher.training_data = df
                search_matcher._rebuild_embeddings()
                search_matcher.save_model()
                print("✅ Search matcher completely reloaded after row deletion (file fallback)")
            
            return jsonify({
                'success': True,
                'message': f'Successfully deleted row {row_index} (file fallback)',
                'remaining_rows': len(df),
                'storage': 'file_fallback',
                'model_retrained': True
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

@app.route('/api/process_excel', methods=['POST'])
def process_excel():
    """Process Excel file and add search results to Customer Query columns."""
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
        
        if not file.filename.lower().endswith(('.xlsx', '.xls')):
            return jsonify({
                'success': False,
                'error': 'Only Excel files (.xlsx, .xls) are allowed'
            }), 400
        
        if not search_matcher:
            return jsonify({
                'success': False,
                'error': 'Search service not available'
            }), 503
        
        # Read Excel file
        try:
            excel_file = pd.ExcelFile(io.BytesIO(file.read()))
            processed_sheets = {}
            total_queries_processed = 0
            
            for sheet_name in excel_file.sheet_names:
                df = pd.read_excel(excel_file, sheet_name=sheet_name)
                
                # Look for columns that could contain customer queries (more flexible matching)
                customer_query_cols = []
                possible_patterns = [
                    'customer query', 'customer_query', 'query', 'search',
                    'description', 'product description', 'item description',
                    'requirement', 'product requirement', 'product'
                ]
                
                for col in df.columns:
                    col_lower = str(col).lower().strip()
                    # Exact match for preferred patterns
                    if col_lower in ['customer query', 'customer_query']:
                        customer_query_cols.append(col)
                    # If no exact match found, look for other potential query columns
                    elif not customer_query_cols and any(pattern in col_lower for pattern in ['query', 'description', 'requirement']):
                        # Only suggest these as alternatives, don't auto-process
                        pass
                
                if not customer_query_cols:
                    continue  # Skip sheets without Customer Query column
                
                # Process each Customer Query column
                processed_df = df.copy()
                
                for query_col in customer_query_cols:
                    # Add new columns to the right of the Customer Query column
                    col_index = df.columns.get_loc(query_col)
                    
                    # Create new column names
                    order_code_col = f"{query_col}_Order_Code"
                    description_col = f"{query_col}_Description" 
                    match_info_col = f"{query_col}_Match_Info"
                    
                    # Initialize new columns
                    processed_df[order_code_col] = ''
                    processed_df[description_col] = ''
                    processed_df[match_info_col] = ''
                    
                    # Process each query in the column
                    for idx, query in enumerate(df[query_col]):
                        if pd.notna(query) and str(query).strip():
                            query_str = str(query).strip()
                            
                            # Perform search
                            try:
                                results = search_matcher.search_fast(query_str, top_k=1)
                                if results:
                                    best_result = results[0]
                                    processed_df.loc[idx, order_code_col] = best_result['order_code']
                                    processed_df.loc[idx, description_col] = best_result['description']
                                    
                                    # Determine match type and score
                                    match_type = best_result.get('match_type', 'fuzzy')
                                    score = best_result.get('probability', 0)
                                    
                                    if match_type == 'exact':
                                        match_info = f"Exact Match (Score: {score:.3f})"
                                    else:
                                        match_info = f"Fuzzy Match (Score: {score:.3f})"
                                    
                                    processed_df.loc[idx, match_info_col] = match_info
                                    total_queries_processed += 1
                                else:
                                    processed_df.loc[idx, match_info_col] = "No Match Found"
                                    
                            except Exception as search_error:
                                print(f"Search error for query '{query_str}': {search_error}")
                                processed_df.loc[idx, match_info_col] = f"Search Error: {str(search_error)}"
                
                # Reorder columns to put new columns right after Customer Query columns
                new_column_order = []
                for col in df.columns:
                    new_column_order.append(col)
                    if str(col).lower().strip() == 'customer query':
                        # Add the new columns right after this Customer Query column
                        order_code_col = f"{col}_Order_Code"
                        description_col = f"{col}_Description"
                        match_info_col = f"{col}_Match_Info"
                        if order_code_col in processed_df.columns:
                            new_column_order.extend([order_code_col, description_col, match_info_col])
                
                processed_df = processed_df[new_column_order]
                processed_sheets[sheet_name] = processed_df
            
            if not processed_sheets:
                # Provide helpful error message with suggestions
                all_columns = set()
                for sheet_name in excel_file.sheet_names:
                    df = pd.read_excel(excel_file, sheet_name=sheet_name)
                    all_columns.update([str(col) for col in df.columns if str(col) != 'nan'])
                
                # Find potential columns that might be what the user intended
                potential_cols = []
                for col in all_columns:
                    col_lower = str(col).lower().strip()
                    if any(pattern in col_lower for pattern in ['query', 'description', 'requirement', 'product', 'item']):
                        potential_cols.append(col)
                
                error_msg = 'No sheets found with "Customer Query" columns. '
                if potential_cols:
                    error_msg += f'Found potential columns: {", ".join(potential_cols[:5])}. '
                error_msg += 'Please ensure your Excel file has a column named "Customer Query" containing the product search terms.'
                
                return jsonify({
                    'success': False,
                    'error': error_msg
                }), 400
            
            # Create output Excel file
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                for sheet_name, df in processed_sheets.items():
                    df.to_excel(writer, sheet_name=sheet_name, index=False)
            
            output.seek(0)
            
            return jsonify({
                'success': True,
                'message': f'Successfully processed {len(processed_sheets)} sheet(s) with {total_queries_processed} queries',
                'sheets_processed': list(processed_sheets.keys()),
                'total_queries': total_queries_processed,
                'file_data': output.getvalue().hex()  # Convert to hex for JSON transport
            })
            
        except Exception as e:
            return jsonify({
                'success': False,
                'error': f'Failed to process Excel file: {str(e)}'
            }), 400
        
    except Exception as e:
        print(f"Excel processing error: {e}")
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': f'Failed to process Excel file: {str(e)}'
        }), 500

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
                from src.utils import get_training_csv_path
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