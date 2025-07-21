#!/usr/bin/env python3
"""
Simple search interface for the probabilistic product matcher.
"""

import sys
import os
from probabilistic_search import ProbabilisticProductMatcher

def main():
    matcher = ProbabilisticProductMatcher()
    
    # Check if model exists, otherwise train
    if not os.path.exists(matcher.model_path):
        print("No trained model found. Training new model...")
        matcher.train()
    else:
        print("Loading existing model...")
        matcher.load_model()
        if matcher.product_catalog is None:
            matcher.load_data()
    
    print(f"\nProduct Search Ready! ({len(matcher.product_catalog)} products in catalog)")
    print("Type 'quit' or 'exit' to stop")
    print("Type 'retrain' to retrain with updated data")
    print("-" * 50)
    
    while True:
        try:
            query = input("\nEnter your search query: ").strip()
            
            if query.lower() in ['quit', 'exit', 'q']:
                break
            elif query.lower() == 'retrain':
                print("Retraining model...")
                matcher.retrain_with_new_data()
                continue
            elif not query:
                continue
            
            print(f"\nSearching for: '{query}'")
            print("-" * 40)
            
            results = matcher.search(query, top_k=10)
            
            for i, result in enumerate(results, 1):
                print(f"{i:2}. Code: {result['order_code']}")
                print(f"    Description: {result['description']}")
                print(f"    Probability: {result['probability']:.3f}")
                print()
                
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"Error: {e}")
    
    print("\nGoodbye!")

if __name__ == "__main__":
    main()