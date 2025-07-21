#!/usr/bin/env python3
"""
Probabilistic search model for ABB product matching.
Trains on customer queries to match products from ABB catalog.
"""

import pandas as pd
import numpy as np
import pickle
import os
import re
from typing import List, Tuple, Dict, Any
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from rapidfuzz import fuzz
import joblib

class ProbabilisticProductMatcher:
    def __init__(self, model_path: str = None):
        from resource_utils import get_product_model_path
        self.model_path = model_path or get_product_model_path()
        self.tfidf_vectorizer = TfidfVectorizer(
            ngram_range=(1, 3),
            max_features=5000,
            stop_words='english',
            lowercase=True
        )
        self.rf_model = RandomForestRegressor(n_estimators=100, random_state=42)
        self.scaler = StandardScaler()
        self.product_catalog = None
        self.training_data = None
        self.is_trained = False
        
    def preprocess_text(self, text: str) -> str:
        """Clean and normalize text for better matching."""
        if pd.isna(text) or text is None:
            return ""
        
        # Convert to lowercase
        text = str(text).lower()
        
        # Remove special characters but keep alphanumeric and spaces
        text = re.sub(r'[^\w\s]', ' ', text)
        
        # Remove extra whitespace
        text = ' '.join(text.split())
        
        return text
    
    def load_data(self):
        """Load training data and product catalog."""
        print("Loading training data...")
        
        # Load training data
        training_files = []
        training_dir = "/Users/henghonglee/abb2/training"
        
        for file in os.listdir(training_dir):
            if file.endswith('.csv'):
                file_path = os.path.join(training_dir, file)
                df = pd.read_csv(file_path)
                training_files.append(df)
        
        if training_files:
            self.training_data = pd.concat(training_files, ignore_index=True)
        else:
            raise ValueError("No training CSV files found in training directory")
        
        print(f"Loaded {len(self.training_data)} training examples")
        
        # Load product catalog
        try:
            from resource_utils import get_abb_csv_path
            catalog_df = pd.read_csv(get_abb_csv_path())
            print(f"Product catalog loaded with shape: {catalog_df.shape}")
            # Check if it has the expected columns
            if 'Order Code' in catalog_df.columns and 'Description' in catalog_df.columns:
                self.product_catalog = catalog_df[['Order Code', 'Description']].dropna()
                print(f"Loaded product catalog with {len(self.product_catalog)} products")
            else:
                print("CSV file doesn't contain expected columns. Using training data as catalog.")
                self.product_catalog = self.training_data[['Order Code', 'Description']].drop_duplicates()
        except Exception as e:
            print(f"Error loading ABB.csv: {e}")
            print("Will use training data descriptions as catalog")
            self.product_catalog = self.training_data[['Order Code', 'Description']].drop_duplicates()
    
    def extract_features(self, query: str, candidate_desc: str, candidate_code: str) -> np.ndarray:
        """Extract features for similarity scoring."""
        query_clean = self.preprocess_text(query)
        desc_clean = self.preprocess_text(candidate_desc)
        code_clean = self.preprocess_text(candidate_code)
        
        # Text similarity features
        features = []
        
        # Fuzzy string matching scores
        features.append(fuzz.ratio(query_clean, desc_clean) / 100.0)
        features.append(fuzz.partial_ratio(query_clean, desc_clean) / 100.0)
        features.append(fuzz.token_sort_ratio(query_clean, desc_clean) / 100.0)
        features.append(fuzz.token_set_ratio(query_clean, desc_clean) / 100.0)
        
        # Code matching
        features.append(fuzz.ratio(query_clean, code_clean) / 100.0)
        features.append(fuzz.partial_ratio(query_clean, code_clean) / 100.0)
        
        # Length ratio
        if len(desc_clean) > 0:
            features.append(len(query_clean) / len(desc_clean))
        else:
            features.append(0.0)
            
        # Word overlap
        query_words = set(query_clean.split())
        desc_words = set(desc_clean.split())
        code_words = set(code_clean.split())
        
        if len(desc_words) > 0:
            features.append(len(query_words & desc_words) / len(desc_words))
        else:
            features.append(0.0)
            
        if len(query_words) > 0:
            features.append(len(query_words & desc_words) / len(query_words))
        else:
            features.append(0.0)
            
        if len(code_words) > 0:
            features.append(len(query_words & code_words) / len(code_words))
        else:
            features.append(0.0)
        
        return np.array(features)
    
    def prepare_training_data(self) -> Tuple[np.ndarray, np.ndarray]:
        """Prepare features and labels for training."""
        print("Preparing training features...")
        
        X_features = []
        y_labels = []
        
        # Use only training data for creating negative examples
        training_products = self.training_data[['Order Code', 'Description']].drop_duplicates()
        
        for idx, row in self.training_data.iterrows():
            query = row['Customer Query']
            correct_code = row['Order Code']
            correct_desc = row['Description']
            
            # Positive example (correct match)
            features = self.extract_features(query, correct_desc, correct_code)
            X_features.append(features)
            y_labels.append(1.0)
            
            # Generate negative examples from training data only
            negative_samples = training_products[training_products['Order Code'] != correct_code].sample(n=min(3, len(training_products)-1))
            
            for _, neg_row in negative_samples.iterrows():
                neg_desc = neg_row.get('Description', '')
                neg_code = neg_row.get('Order Code', '')
                
                features = self.extract_features(query, neg_desc, neg_code)
                X_features.append(features)
                y_labels.append(0.0)
        
        return np.array(X_features), np.array(y_labels)
    
    def train(self):
        """Train the probabilistic model."""
        self.load_data()
        
        print("Training probabilistic model...")
        X, y = self.prepare_training_data()
        
        # Scale features
        X_scaled = self.scaler.fit_transform(X)
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X_scaled, y, test_size=0.2, random_state=42
        )
        
        # Train model
        self.rf_model.fit(X_train, y_train)
        
        # Evaluate
        train_score = self.rf_model.score(X_train, y_train)
        test_score = self.rf_model.score(X_test, y_test)
        
        print(f"Training score: {train_score:.3f}")
        print(f"Test score: {test_score:.3f}")
        
        self.is_trained = True
        self.save_model()
    
    def predict_probability(self, query: str, candidate_desc: str, candidate_code: str) -> float:
        """Predict probability that candidate matches query."""
        if not self.is_trained:
            raise ValueError("Model not trained. Call train() first.")
            
        features = self.extract_features(query, candidate_desc, candidate_code)
        features_scaled = self.scaler.transform(features.reshape(1, -1))
        
        # Get probability from random forest
        prob = self.rf_model.predict(features_scaled)[0]
        return max(0.0, min(1.0, prob))  # Clip to [0, 1]
    
    def search(self, query: str, top_k: int = 10) -> List[Dict[str, Any]]:
        """Search for best matching products given a customer query."""
        if not self.is_trained:
            self.load_model()
        
        if self.product_catalog is None:
            self.load_data()
        
        results = []
        
        # Check for exact or near-exact matches in training data first
        training_boost = self.get_training_boost(query)
        
        for idx, row in self.product_catalog.iterrows():
            code = row.get('Order Code', '')
            desc = row.get('Description', '')
            
            prob = self.predict_probability(query, desc, code)
            
            # Apply heavy boost for training data matches
            if code in training_boost:
                prob = min(1.0, prob + training_boost[code])
            
            results.append({
                'order_code': code,
                'description': desc,
                'probability': prob,
                'query': query,
                'is_training_match': code in training_boost
            })
        
        # Sort by probability and return top results
        results.sort(key=lambda x: x['probability'], reverse=True)
        return results[:top_k]
    
    def get_training_boost(self, query: str) -> Dict[str, float]:
        """Calculate boost scores for products that appear in training data."""
        if self.training_data is None:
            return {}
        
        query_clean = self.preprocess_text(query)
        boost_scores = {}
        
        for _, row in self.training_data.iterrows():
            training_query = self.preprocess_text(row['Customer Query'])
            training_code = row['Order Code']
            
            # Calculate similarity between input query and training query
            similarity_scores = [
                fuzz.ratio(query_clean, training_query) / 100.0,
                fuzz.partial_ratio(query_clean, training_query) / 100.0,
                fuzz.token_sort_ratio(query_clean, training_query) / 100.0,
                fuzz.token_set_ratio(query_clean, training_query) / 100.0
            ]
            
            max_similarity = max(similarity_scores)
            
            # Apply heavy boost for high similarity (threshold: 0.7)
            if max_similarity >= 0.7:
                # Boost ranges from 0.3 to 0.8 based on similarity
                boost = 0.3 + (max_similarity - 0.7) * (0.5 / 0.3)
                boost_scores[training_code] = max(boost_scores.get(training_code, 0), boost)
        
        return boost_scores
    
    def save_model(self):
        """Save trained model to disk."""
        model_data = {
            'tfidf_vectorizer': self.tfidf_vectorizer,
            'rf_model': self.rf_model,
            'scaler': self.scaler,
            'is_trained': self.is_trained,
            'product_catalog': self.product_catalog,
            'training_data': self.training_data
        }
        
        joblib.dump(model_data, self.model_path)
        print(f"Model saved to {self.model_path}")
    
    def load_model(self):
        """Load trained model from disk."""
        if os.path.exists(self.model_path):
            model_data = joblib.load(self.model_path)
            
            self.tfidf_vectorizer = model_data['tfidf_vectorizer']
            self.rf_model = model_data['rf_model']
            self.scaler = model_data['scaler']
            self.is_trained = model_data['is_trained']
            self.product_catalog = model_data.get('product_catalog')
            self.training_data = model_data.get('training_data')
            
            print(f"Model loaded from {self.model_path}")
        else:
            print(f"No saved model found at {self.model_path}")
    
    def retrain_with_new_data(self):
        """Retrain model including any new files in training directory."""
        print("Retraining with updated data...")
        self.train()

def main():
    """Example usage of the probabilistic matcher."""
    matcher = ProbabilisticProductMatcher()
    
    # Train the model
    matcher.train()
    
    # Example search
    test_queries = [
        "ACB 4P 800A circuit breaker",
        "contactor 400A",
        "protection relay"
    ]
    
    print("\n" + "="*50)
    print("SEARCH RESULTS")
    print("="*50)
    
    for query in test_queries:
        print(f"\nQuery: '{query}'")
        print("-" * 40)
        
        results = matcher.search(query, top_k=5)
        
        for i, result in enumerate(results, 1):
            print(f"{i}. Code: {result['order_code']}")
            print(f"   Description: {result['description']}")
            print(f"   Probability: {result['probability']:.3f}")
            print()

if __name__ == "__main__":
    main()