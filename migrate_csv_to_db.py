#!/usr/bin/env python3
"""
Standalone script to migrate existing CSV training data to PostgreSQL database.
Run this script to migrate your existing training.csv to the database.
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app
from models import TrainingData, init_db, migrate_csv_to_db
from resource_utils import get_training_csv_path


def main():
    """Main migration function."""
    print("🔄 Starting CSV to Database Migration...")
    
    # Check database configuration
    DATABASE_URL = os.environ.get('DATABASE_URL')
    if not DATABASE_URL:
        print("⚠️  No DATABASE_URL found, using SQLite for local testing")
    else:
        print(f"📊 Database URL configured: {DATABASE_URL[:50]}...")
    
    try:
        with app.app_context():
            # Initialize database
            print("🔧 Initializing database...")
            init_db(app)
            
            # Check existing data
            existing_count = TrainingData.get_total_count()
            print(f"📊 Current database records: {existing_count}")
            
            if existing_count > 0:
                choice = input("Database already contains data. Continue? (y/N): ")
                if choice.lower() != 'y':
                    print("❌ Migration cancelled")
                    return
            
            # Find CSV file
            training_path = get_training_csv_path()
            print(f"📁 Training data path: {training_path}")
            
            if training_path == "REMOTE_TRAINING_DATA":
                print("🌐 No local CSV found, trying remote data...")
                from remote_data_loader import remote_loader
                df = remote_loader.load_training_data()
                
                if len(df) == 0:
                    print("❌ No training data found in remote source")
                    return
                
                print(f"📥 Downloaded {len(df)} records from remote")
                result = TrainingData.bulk_insert_from_dataframe(df, skip_duplicates=True)
                
            elif os.path.exists(training_path):
                print(f"📁 Found local CSV file: {training_path}")
                migrate_csv_to_db(training_path, app)
                result = {'added': TrainingData.get_total_count() - existing_count}
            else:
                print("❌ No training data file found")
                return
            
            final_count = TrainingData.get_total_count()
            print(f"✅ Migration complete!")
            print(f"📊 Final database records: {final_count}")
            print(f"➕ Records added: {final_count - existing_count}")
            
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())