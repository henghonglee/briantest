#!/usr/bin/env python3
"""
ABB Product Search Interface
Combines probabilistic model with fast TF-IDF search for optimal results.
"""

import sys
import os
import time
from fast_search import FastProductMatcher
from probabilistic_search import ProbabilisticProductMatcher

class ABBProductSearch:
    def __init__(self):
        self.fast_matcher = FastProductMatcher()
        self.probabilistic_matcher = None
        self.use_probabilistic = False
        
    def initialize(self):
        """Initialize the search system."""
        print("Initializing ABB Product Search System...")
        
        # Always initialize fast search
        self.fast_matcher.load_model()
        
        # Check if probabilistic model exists
        if os.path.exists("product_matcher_model.pkl"):
            print("Probabilistic model found. Loading...")
            try:
                self.probabilistic_matcher = ProbabilisticProductMatcher()
                self.probabilistic_matcher.load_model()
                if self.probabilistic_matcher.product_catalog is None:
                    self.probabilistic_matcher.load_data()
                self.use_probabilistic = True
                print("Probabilistic model ready.")
            except Exception as e:
                print(f"Error loading probabilistic model: {e}")
                print("Will use fast search only.")
        else:
            print("No probabilistic model found. Use 'train' command to create one.")
        
        print(f"Search system ready with {len(self.fast_matcher.product_catalog)} products.")
    
    def search(self, query: str, method: str = "auto", top_k: int = 10):
        """Search for products using specified method."""
        if method == "auto":
            method = "probabilistic" if self.use_probabilistic else "fast"
        
        if method == "fast" or not self.use_probabilistic:
            return self.fast_matcher.search_fast(query, top_k)
        elif method == "probabilistic" and self.use_probabilistic:
            return self.probabilistic_matcher.search(query, top_k)
        else:
            raise ValueError(f"Unknown method: {method}")
    
    def train_probabilistic_model(self):
        """Train the probabilistic model."""
        print("Training probabilistic model...")
        self.probabilistic_matcher = ProbabilisticProductMatcher()
        self.probabilistic_matcher.train()
        self.use_probabilistic = True
        print("Probabilistic model training completed.")
    
    def interactive_search(self):
        """Interactive search interface."""
        print("\nABB Product Search Interface")
        print("Commands:")
        print("  search <query>     - Search for products")
        print("  fast <query>       - Use fast TF-IDF search")
        print("  prob <query>       - Use probabilistic search")
        print("  train              - Train probabilistic model")
        print("  quit/exit          - Exit")
        print("-" * 60)
        
        while True:
            try:
                command = input("\nabb-search> ").strip()
                
                if not command:
                    continue
                    
                parts = command.split(' ', 1)
                cmd = parts[0].lower()
                
                if cmd in ['quit', 'exit', 'q']:
                    break
                elif cmd == 'train':
                    self.train_probabilistic_model()
                elif cmd in ['search', 'fast', 'prob']:
                    if len(parts) < 2:
                        print("Please provide a search query.")
                        continue
                        
                    query = parts[1]
                    method = "fast" if cmd == "fast" else ("probabilistic" if cmd == "prob" else "auto")
                    
                    print(f"\nSearching for: '{query}' (method: {method})")
                    start_time = time.time()
                    
                    try:
                        results = self.search(query, method=method, top_k=10)
                        search_time = time.time() - start_time
                        
                        print(f"Found {len(results)} results in {search_time:.3f}s")
                        print("-" * 50)
                        
                        for i, result in enumerate(results, 1):
                            print(f"{i:2}. Code: {result['order_code']}")
                            print(f"    Desc: {result['description'][:60]}...")
                            
                            if 'probability' in result:
                                print(f"    Score: {result['probability']:.3f}")
                            elif 'tfidf_score' in result:
                                print(f"    Score: {result.get('probability', 0):.3f} " +
                                      f"(TF-IDF: {result['tfidf_score']:.3f})")
                            print()
                            
                    except Exception as e:
                        print(f"Search error: {e}")
                        
                else:
                    print(f"Unknown command: {cmd}")
                    print("Type 'search <query>' to search, or 'quit' to exit.")
                    
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"Error: {e}")
        
        print("\nGoodbye!")

def main():
    """Main entry point."""
    if len(sys.argv) > 1:
        # Command line usage
        search_system = ABBProductSearch()
        search_system.initialize()
        
        query = ' '.join(sys.argv[1:])
        print(f"\nSearching for: '{query}'")
        print("-" * 50)
        
        results = search_system.search(query)
        
        for i, result in enumerate(results, 1):
            print(f"{i}. {result['order_code']} - {result['description']}")
            if 'probability' in result:
                print(f"   Score: {result['probability']:.3f}")
            print()
    else:
        # Interactive mode
        search_system = ABBProductSearch()
        search_system.initialize()
        search_system.interactive_search()

if __name__ == "__main__":
    main()