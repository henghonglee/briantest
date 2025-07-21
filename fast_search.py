#!/usr/bin/env python3
"""
Optimized search implementation using pre-computed embeddings and efficient filtering.
"""

import pandas as pd
import numpy as np
import pickle
import os
from typing import List, Dict, Any
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from rapidfuzz import fuzz
import joblib
import time

class FastProductMatcher:
    def __init__(self, model_path: str = None):
        from resource_utils import get_fast_model_path
        self.model_path = model_path or get_fast_model_path()
        self.tfidf_vectorizer = TfidfVectorizer(
            ngram_range=(1, 2),
            max_features=1000,
            stop_words='english',
            lowercase=True
        )
        self.training_data = None
        self.query_embeddings = None
        self.is_ready = False
        
    def preprocess_text(self, text: str) -> str:
        """Clean and normalize text."""
        if pd.isna(text) or text is None:
            return ""
        text = str(text).lower()
        # Keep only alphanumeric and spaces
        import re
        text = re.sub(r'[^\w\s]', ' ', text)
        return ' '.join(text.split())
    
    def load_data_and_prepare(self):
        """Load training data and prepare embeddings."""
        print("Loading training data...")
        from resource_utils import load_training_data
        try:
            self.training_data = load_training_data()
        except FileNotFoundError:
            print("⚠️  Training data not found, creating empty dataset...")
            # Create empty training data structure
            self.training_data = pd.DataFrame(columns=['Customer Query', 'Order Code', 'Description'])
        # Filter out rows with invalid queries
        self.training_data = self.training_data.dropna(subset=['Customer Query', 'Order Code', 'Description'])
        self.training_data = self.training_data[self.training_data['Customer Query'].str.strip() != '']
        print(f"Loaded {len(self.training_data)} training examples")
        
        print("Preparing training query embeddings...")
        # Create embeddings from training queries
        training_queries = []
        for _, row in self.training_data.iterrows():
            query = self.preprocess_text(row['Customer Query'])
            training_queries.append(query)
        
        if training_queries:
            # Fit TF-IDF and create embeddings from training queries
            self.query_embeddings = self.tfidf_vectorizer.fit_transform(training_queries)
            print(f"Created embeddings with shape: {self.query_embeddings.shape}")
        else:
            # No training data available, fit on dummy data
            print("⚠️  No training queries available, using minimal setup...")
            dummy_queries = ["default query"]
            self.query_embeddings = self.tfidf_vectorizer.fit_transform(dummy_queries)
            print("Created minimal embeddings setup")
        
        self.is_ready = True
        self.save_model()
    
    def search_fast(self, query: str, top_k: int = 10) -> List[Dict[str, Any]]:
        """Fast search with exact match priority and fuzzy fallback."""
        if not self.is_ready:
            self.load_model()
        
        start_time = time.time()
        
        # Preprocess query
        query_clean = self.preprocess_text(query)
        query_original = query.strip()
        
        # FIRST PASS: Check for exact matches in training queries
        exact_matches = []
        exact_match_indices = set()
        
        for idx, row in self.training_data.iterrows():
            training_query = row['Customer Query']
            training_query_clean = self.preprocess_text(training_query)
            
            # Check for exact match (case insensitive, normalized)
            if query_clean == training_query_clean:
                exact_matches.append({
                    'order_code': row['Order Code'],
                    'description': row['Description'],
                    'training_query': training_query,
                    'probability': 1.0,  # Perfect match
                    'tfidf_score': 1.0,
                    'fuzzy_score': 1.0,
                    'match_type': 'exact'
                })
                exact_match_indices.add(idx)
        
        # SECOND PASS: TF-IDF + fuzzy matching for remaining slots
        # Transform query to TF-IDF space
        query_embedding = self.tfidf_vectorizer.transform([query_clean])
        
        # Calculate cosine similarity with all training queries
        similarities = cosine_similarity(query_embedding, self.query_embeddings).flatten()
        
        # Get top matches, excluding exact matches
        top_indices = similarities.argsort()[-top_k*3:][::-1]  # Get more candidates
        
        fuzzy_results = []
        for idx in top_indices:
            # Check if index is within bounds
            if idx >= len(self.training_data):
                continue  # Skip out-of-bounds indices
                
            if idx in exact_match_indices:
                continue  # Skip exact matches already found
                
            if len(fuzzy_results) >= top_k:
                break
                
            row = self.training_data.iloc[idx]
            code = row['Order Code']
            desc = row['Description']
            training_query = row['Customer Query']
            
            # Additional fuzzy matching for refinement
            fuzzy_score = max(
                fuzz.partial_ratio(query_clean, self.preprocess_text(training_query)),
                fuzz.token_sort_ratio(query_clean, self.preprocess_text(training_query)),
                fuzz.partial_ratio(query_clean, self.preprocess_text(desc))
            ) / 100.0
            
            # Combine TF-IDF and fuzzy scores
            combined_score = 0.7 * similarities[idx] + 0.3 * fuzzy_score
            
            fuzzy_results.append({
                'order_code': code,
                'description': desc,
                'training_query': training_query,
                'probability': combined_score,
                'tfidf_score': similarities[idx],
                'fuzzy_score': fuzzy_score,
                'match_type': 'fuzzy'
            })
        
        # Sort fuzzy results by combined score
        fuzzy_results.sort(key=lambda x: x['probability'], reverse=True)
        
        # Combine results: exact matches first, then fuzzy matches
        all_results = exact_matches + fuzzy_results
        
        # Remove duplicates based on order_code, keeping the highest scoring one
        seen_codes = set()
        deduplicated_results = []
        for result in all_results:
            order_code = result['order_code']
            if order_code not in seen_codes:
                deduplicated_results.append(result)
                seen_codes.add(order_code)
        
        search_time = time.time() - start_time
        # print(f"Search completed in {search_time:.3f} seconds")
        
        return deduplicated_results[:top_k]
    
    def save_model(self):
        """Save the model and embeddings."""
        model_data = {
            'tfidf_vectorizer': self.tfidf_vectorizer,
            'training_data': self.training_data,
            'query_embeddings': self.query_embeddings,
            'is_ready': self.is_ready
        }
        joblib.dump(model_data, self.model_path)
        print(f"Model saved to {self.model_path}")
    
    def load_model(self):
        """Load the model and embeddings."""
        if os.path.exists(self.model_path):
            print(f"Loading model from {self.model_path}")
            model_data = joblib.load(self.model_path)
            
            self.tfidf_vectorizer = model_data['tfidf_vectorizer']
            self.training_data = model_data['training_data']
            self.query_embeddings = model_data['query_embeddings']
            self.is_ready = model_data['is_ready']
            
            print(f"Model loaded successfully. Ready: {self.is_ready}")
        else:
            print("No saved model found. Preparing from scratch...")
            self.load_data_and_prepare()
    
    def add_training_example(self, query: str, order_code: str, description: str) -> bool:
        """Add a new training example and update the model."""
        try:
            if not self.is_ready:
                self.load_model()
            
            # Create new row
            new_row = pd.DataFrame({
                'Customer Query': [query.strip()],
                'Order Code': [order_code.strip()],
                'Description': [description.strip()]
            })
            
            # Add to training data
            self.training_data = pd.concat([self.training_data, new_row], ignore_index=True)
            
            # Save to CSV file
            from resource_utils import get_training_csv_path
            self.training_data.to_csv(get_training_csv_path(), index=False)
            
            # Regenerate embeddings with new data
            print("Regenerating embeddings with new training data...")
            training_queries = []
            for _, row in self.training_data.iterrows():
                query_clean = self.preprocess_text(row['Customer Query'])
                training_queries.append(query_clean)
            
            # Refit TF-IDF and create new embeddings
            self.query_embeddings = self.tfidf_vectorizer.fit_transform(training_queries)
            
            # Save updated model
            self.save_model()
            
            print(f"Added training example: '{query}' -> '{order_code}'")
            return True
            
        except Exception as e:
            print(f"Error adding training example: {e}")
            return False

def main():
    """Test the fast search."""
    matcher = FastProductMatcher()
    
    test_queries = [
        "ACB 4P 800A 65KA",
        "contactor 400A", 
        "circuit breaker 100A",
        "relay protection",
        "switch disconnector"
    ]
    
    print("="*60)
    print("FAST SEARCH RESULTS")
    print("="*60)
    
    for query in test_queries:
        print(f"\nQuery: '{query}'")
        print("-" * 50)
        
        results = matcher.search_fast(query, top_k=5)
        
        for i, result in enumerate(results, 1):
            print(f"{i}. {result['order_code']}")
            print(f"   Description: {result['description'][:60]}...")
            print(f"   Training Query: {result['training_query'][:60]}...")
            print(f"   Score: {result['probability']:.3f} (TF-IDF: {result['tfidf_score']:.3f}, Fuzzy: {result['fuzzy_score']:.3f})")
            print()

if __name__ == "__main__":
    main()