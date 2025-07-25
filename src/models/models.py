"""
Database models for ABB Product Search training data.
"""

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Column, Integer, String, DateTime, Text, Index
from sqlalchemy.sql import func
from datetime import datetime
import pandas as pd


def clean_corrupted_characters(text):
    """Replace corrupted Unicode characters with proper equivalents."""
    if isinstance(text, str):
        # Replace Unicode replacement character (�) with dash for ranges
        text = text.replace('�', '-')
        # Replace other common corrupted characters
        text = text.replace('\ufffd', '-')  # Another form of replacement character
    return text


def clean_dataframe_text(df):
    """Clean corrupted characters in all text columns of a DataFrame."""
    for col in df.columns:
        if df[col].dtype == 'object':  # Text columns
            df[col] = df[col].astype(str).apply(clean_corrupted_characters)
    return df


db = SQLAlchemy()

class TrainingData(db.Model):
    """Model for storing training data examples."""
    __tablename__ = 'training_data'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    customer_query = Column(String(500), nullable=False, index=True)
    order_code = Column(String(100), nullable=False, index=True)
    description = Column(Text, nullable=False)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    
    # Composite index for duplicate detection
    __table_args__ = (
        Index('idx_query_order_code', 'customer_query', 'order_code'),
    )
    
    def __repr__(self):
        return f'<TrainingData {self.id}: "{self.customer_query[:50]}" -> {self.order_code}>'
    
    def to_dict(self):
        """Convert model instance to dictionary."""
        return {
            'id': self.id,
            'customer_query': self.customer_query,
            'order_code': self.order_code,
            'description': self.description,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    @staticmethod
    def from_dict(data):
        """Create model instance from dictionary."""
        return TrainingData(
            customer_query=data.get('customer_query', ''),
            order_code=data.get('order_code', ''),
            description=data.get('description', '')
        )
    
    @classmethod
    def get_all_as_dataframe(cls):
        """Get all training data as pandas DataFrame."""
        records = cls.query.all()
        if not records:
            return pd.DataFrame(columns=['Customer Query', 'Order Code', 'Description'])
        
        data = []
        for record in records:
            data.append({
                'Customer Query': record.customer_query,
                'Order Code': record.order_code,
                'Description': record.description
            })
        
        return pd.DataFrame(data)
    
    @classmethod
    def bulk_insert_from_dataframe(cls, df, skip_duplicates=True):
        """Insert multiple records from pandas DataFrame."""
        added_count = 0
        duplicate_count = 0
        
        for _, row in df.iterrows():
            customer_query = str(row.get('Customer Query', '')).strip()
            order_code = str(row.get('Order Code', '')).strip()
            description = str(row.get('Description', '')).strip()
            
            # Skip empty rows
            if not customer_query or not order_code or not description:
                continue
            
            # Check for duplicates if requested
            if skip_duplicates:
                existing = cls.query.filter_by(
                    customer_query=customer_query,
                    order_code=order_code
                ).first()
                
                if existing:
                    duplicate_count += 1
                    continue
            
            # Create new record
            record = cls(
                customer_query=customer_query,
                order_code=order_code,
                description=description
            )
            
            try:
                db.session.add(record)
                added_count += 1
            except Exception as e:
                print(f"Error adding record: {e}")
                db.session.rollback()
                continue
        
        # Commit all changes
        try:
            db.session.commit()
            return {'added': added_count, 'duplicates': duplicate_count}
        except Exception as e:
            db.session.rollback()
            raise e
    
    @classmethod
    def delete_by_id(cls, record_id):
        """Delete a specific training record by ID."""
        record = cls.query.get(record_id)
        if record:
            db.session.delete(record)
            db.session.commit()
            return True
        return False
    
    @classmethod
    def get_total_count(cls):
        """Get total number of training records."""
        return cls.query.count()
    
    @classmethod
    def search_records(cls, query=None, limit=None, offset=None):
        """Search training records with optional filtering."""
        base_query = cls.query
        
        if query:
            search_term = f"%{query.lower()}%"
            base_query = base_query.filter(
                db.or_(
                    cls.customer_query.ilike(search_term),
                    cls.order_code.ilike(search_term),
                    cls.description.ilike(search_term)
                )
            )
        
        # Order by most recent first
        base_query = base_query.order_by(cls.created_at.desc())
        
        if offset:
            base_query = base_query.offset(offset)
        
        if limit:
            base_query = base_query.limit(limit)
        
        return base_query.all()
    
    @classmethod
    def clear_all(cls):
        """Delete all training data records."""
        try:
            cls.query.delete()
            db.session.commit()
            return True
        except Exception as e:
            db.session.rollback()
            raise e
    
    @classmethod
    def create(cls, customer_query, order_code, description):
        """Create a new training data record."""
        try:
            record = cls(
                customer_query=customer_query.strip(),
                order_code=order_code.strip(), 
                description=description.strip()
            )
            db.session.add(record)
            db.session.commit()
            return True
        except Exception as e:
            db.session.rollback()
            print(f"Error creating training record: {e}")
            return False


def init_db(app):
    """Initialize database with Flask app."""
    # Don't call db.init_app here since it's already done in app.py
    
    with app.app_context():
        # Create all tables
        db.create_all()
        print("✅ Database tables created successfully")
        
        # Print database info
        total_records = TrainingData.get_total_count()
        print(f"📊 Current training data records: {total_records}")


