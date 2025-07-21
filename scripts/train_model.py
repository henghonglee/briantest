#!/usr/bin/env python3
"""
Training script for the probabilistic product matcher.
"""

from probabilistic_search import ProbabilisticProductMatcher
import time

def main():
    print("Starting model training...")
    start_time = time.time()
    
    matcher = ProbabilisticProductMatcher()
    matcher.train()
    
    end_time = time.time()
    print(f"\nTraining completed in {end_time - start_time:.2f} seconds")
    
    # Test with a few sample queries
    test_queries = [
        "ACB 4P 800A 65KA",
        "contactor 400A",
        "circuit breaker 100A",
        "relay protection",
        "switch disconnector"
    ]
    
    print("\n" + "="*60)
    print("TESTING MODEL WITH SAMPLE QUERIES")
    print("="*60)
    
    for query in test_queries:
        print(f"\nQuery: '{query}'")
        print("-" * 50)
        
        results = matcher.search(query, top_k=3)
        
        for i, result in enumerate(results, 1):
            print(f"{i}. {result['order_code']} - {result['description'][:60]}...")
            print(f"   Probability: {result['probability']:.3f}")

if __name__ == "__main__":
    main()