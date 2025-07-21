#!/usr/bin/env python3
"""
Validate that training queries return correct results.
"""

from probabilistic_search import ProbabilisticProductMatcher
import pandas as pd
import random

def test_exact_training_matches():
    """Test that exact training queries return the correct product."""
    matcher = ProbabilisticProductMatcher()
    matcher.load_model()
    
    if matcher.training_data is None:
        matcher.load_data()
    
    print("Testing exact matches from training data...")
    print("="*60)
    
    # Test 20 random training examples
    correct_matches = 0
    total_tests = 20
    tests_completed = 0
    
    # Filter out rows with invalid queries first, then sample
    valid_training_data = matcher.training_data.dropna(subset=['Customer Query'])
    valid_training_data = valid_training_data[valid_training_data['Customer Query'].str.strip() != '']
    
    # Randomly sample 20 rows from valid training data
    random_sample = valid_training_data.sample(n=total_tests, random_state=42)
    
    for i, row in random_sample.iterrows():
        query = row['Customer Query']
        expected_code = row['Order Code']
        expected_desc = row['Description']
        
        results = matcher.search(query, top_k=5)
        
        found_match = False
        rank = -1
        
        for j, result in enumerate(results):
            if result['order_code'] == expected_code:
                found_match = True
                rank = j + 1
                break
        
        status = "✓ PASS" if found_match and rank == 1 else f"✗ FAIL (rank {rank})" if found_match else "✗ FAIL (not found)"
        
        print(f"Query: '{query[:50]}...'")
        print(f"Expected: {expected_code}")
        print(f"Got: {results[0]['order_code']} (prob: {results[0]['probability']:.3f})")
        print(f"Status: {status}")
        
        if found_match and rank == 1:
            correct_matches += 1
        
        tests_completed += 1
        print("-" * 50)
    
    accuracy = (correct_matches / tests_completed) * 100
    print(f"\nAccuracy: {correct_matches}/{tests_completed} ({accuracy:.1f}%)")
    
    return accuracy

def test_fuzzy_training_matches():
    """Test fuzzy variations of training queries."""
    matcher = ProbabilisticProductMatcher()
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
        results = matcher.search(fuzzy_query, top_k=5)
        
        found_match = False
        rank = -1
        
        for j, result in enumerate(results):
            if result['order_code'] == expected_code:
                found_match = True
                rank = j + 1
                break
        
        status = "✓ PASS" if found_match and rank <= 3 else f"✗ FAIL (rank {rank})" if found_match else "✗ FAIL (not found)"
        
        print(f"Original: '{original_query}'")
        print(f"Fuzzy: '{fuzzy_query}'")
        print(f"Expected: {expected_code}")
        print(f"Got: {results[0]['order_code']} (prob: {results[0]['probability']:.3f})")
        print(f"Status: {status}")
        
        if found_match and rank <= 3:
            correct_matches += 1
        
        print("-" * 50)
    
    accuracy = (correct_matches / len(test_cases)) * 100
    print(f"\nFuzzy Accuracy: {correct_matches}/{len(test_cases)} ({accuracy:.1f}%)")

if __name__ == "__main__":
    exact_accuracy = test_exact_training_matches()
    test_fuzzy_training_matches()
    
    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    print(f"Exact training match accuracy: {exact_accuracy:.1f}%")
    
    if exact_accuracy >= 90:
        print("✅ Training data is properly weighted!")
    else:
        print("❌ Need to increase training data weights further.")