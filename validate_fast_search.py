#!/usr/bin/env python3
"""
Validate that training queries return correct results using fast search.
"""

from fast_search import FastProductMatcher
import pandas as pd
import random

def test_exact_training_matches():
    """Test that exact training queries return the correct product using fast search."""
    matcher = FastProductMatcher()
    matcher.load_model()
    
    # Load training data
    print("Loading training data...")
    training_data = pd.read_csv("/Users/henghonglee/abb2/training/training.csv")
    
    print("Testing exact matches from training data...")
    print("="*60)
    
    # Test entire training set
    correct_matches = 0
    tests_completed = 0
    
    # Filter out rows with invalid queries first
    valid_training_data = training_data.dropna(subset=['Customer Query'])
    valid_training_data = valid_training_data[valid_training_data['Customer Query'].str.strip() != '']
    
    total_tests = len(valid_training_data)
    print(f"Testing all {total_tests} training examples...")
    
    # Use entire valid training data
    test_data = valid_training_data
    
    for i, row in test_data.iterrows():
        query = row['Customer Query']
        expected_code = row['Order Code']
        expected_desc = row['Description']
        
        results = matcher.search_fast(query, top_k=5)
        
        found_match = False
        rank = -1
        
        # Check top 3 results only
        top_3_results = results[:3]
        
        for j, result in enumerate(top_3_results):
            if result['order_code'] == expected_code:
                found_match = True
                rank = j + 1
                break
        
        status = f"✓ PASS (rank {rank})" if found_match else "✗ FAIL (not in top 3)"
        
        if found_match:
            correct_matches += 1
        
        tests_completed += 1
        
        # Print progress every 50 tests and show failures
        if tests_completed % 50 == 0:
            current_accuracy = (correct_matches / tests_completed) * 100
            print(f"Progress: {tests_completed}/{total_tests} - Accuracy so far: {current_accuracy:.1f}%")
        
        # Show failures for debugging with top 3 results
        if not found_match:
            print(f"FAIL #{tests_completed}: '{query[:40]}...'")
            print(f"  Expected: {expected_code}")
            print(f"  Top 3:    {[r['order_code'] for r in top_3_results]}")
            scores = [f"{r['probability']:.3f}" for r in top_3_results]
            print(f"  Scores:   {scores}")
    
    accuracy = (correct_matches / tests_completed) * 100
    print(f"\nAccuracy: {correct_matches}/{tests_completed} ({accuracy:.1f}%)")
    
    return accuracy

def test_fuzzy_training_matches():
    """Test fuzzy variations of training queries using fast search."""
    matcher = FastProductMatcher()
    matcher.load_model()
    
    print("\n" + "="*60)
    print("Testing fuzzy variations of training queries...")
    print("="*60)
    
    # Create fuzzy variations of some training queries
    test_cases = [
        ("ACB 4P 800A 65KA (3s)", "ACB 4P 800A 65KA", "1SDA072894R1"),
        ("ACB 4P 800A 36KA (3s)", "ACB 800A 36KA 4P", "1SDA072874R1"),
        ("ACB 4P 630A 36KA (3s)", "630A ACB 4P 36KA", "1SDA072874R1"),
        ("ACB 4P 5000A 36KA (3s)", "5000A ACB 4 pole 36KA", "1SDA073244R1"),
        ("ACB 4P 400A 36KA (3s)", "400A circuit breaker 4P", "1SDA072874R1")
    ]
    
    correct_matches = 0
    
    for original_query, fuzzy_query, expected_code in test_cases:
        results = matcher.search_fast(fuzzy_query, top_k=5)
        
        found_match = False
        rank = -1
        
        # Check top 3 results only
        top_3_results = results[:3]
        
        for j, result in enumerate(top_3_results):
            if result['order_code'] == expected_code:
                found_match = True
                rank = j + 1
                break
        
        status = f"✓ PASS (rank {rank})" if found_match else "✗ FAIL (not in top 3)"
        
        print(f"Original: '{original_query}'")
        print(f"Fuzzy: '{fuzzy_query}'")
        print(f"Expected: {expected_code}")
        if found_match:
            print(f"Found at rank {rank}: {results[rank-1]['order_code']} (score: {results[rank-1]['probability']:.3f})")
        else:
            print(f"Not found in top 3")
            print(f"Top 3: {[r['order_code'] for r in top_3_results]}")
            scores = [f"{r['probability']:.3f}" for r in top_3_results]
            print(f"Scores: {scores}")
        print(f"Status: {status}")
        
        if found_match:
            correct_matches += 1
        
        print("-" * 50)
    
    accuracy = (correct_matches / len(test_cases)) * 100
    print(f"\nFuzzy Accuracy: {correct_matches}/{len(test_cases)} ({accuracy:.1f}%)")

def test_performance_comparison():
    """Test performance comparison between fast search queries."""
    matcher = FastProductMatcher()
    matcher.load_model()
    
    print("\n" + "="*60)
    print("PERFORMANCE TEST - Fast Search")
    print("="*60)
    
    test_queries = [
        "ACB 4P 800A 65KA",
        "contactor 400A",
        "circuit breaker 100A",
        "relay protection",
        "switch disconnector"
    ]
    
    import time
    total_time = 0
    
    for query in test_queries:
        start_time = time.time()
        results = matcher.search_fast(query, top_k=3)
        end_time = time.time()
        
        query_time = end_time - start_time
        total_time += query_time
        
        print(f"Query: '{query}' - Time: {query_time:.4f}s")
        print(f"Top result: {results[0]['order_code']} (score: {results[0]['probability']:.3f})")
        print("-" * 40)
    
    avg_time = total_time / len(test_queries)
    print(f"\nAverage query time: {avg_time:.4f} seconds")
    print(f"Total time for {len(test_queries)} queries: {total_time:.4f} seconds")

if __name__ == "__main__":
    exact_accuracy = test_exact_training_matches()
    test_fuzzy_training_matches()
    test_performance_comparison()
    
    print(f"\n{'='*60}")
    print("FAST SEARCH VALIDATION SUMMARY")
    print(f"{'='*60}")
    print(f"Training match accuracy (top 3): {exact_accuracy:.1f}%")
    
    if exact_accuracy >= 85:
        print("✅ Fast search is performing excellently!")
    elif exact_accuracy >= 70:
        print("✅ Fast search is performing well!")
    else:
        print("❌ Fast search may need tuning.")