#!/usr/bin/env python3
"""
Extensive fuzzy validation tests for fast search.
"""

from fast_search import FastProductMatcher
import pandas as pd

def create_fuzzy_test_cases():
    """Create comprehensive fuzzy test cases based on common variations."""
    
    # Based on training data patterns, create fuzzy variations
    fuzzy_test_cases = [
        # ACB (Air Circuit Breaker) variations
        ("ACB 4P 800A 65KA", "air circuit breaker 4 pole 800A 65KA", "1SDA072894R1"),
        ("ACB 4P 800A 65KA", "ACB 4-pole 800 amp 65 KA", "1SDA072894R1"),
        ("ACB 4P 800A 65KA", "circuit breaker 800A 4P 65KA", "1SDA072894R1"),
        ("ACB 4P 800A 65KA", "800A ACB 4P 65KA", "1SDA072894R1"),
        ("ACB 4P 800A 65KA", "ACB 800 amp 4 pole 65ka", "1SDA072894R1"),
        
        ("ACB 4P 800A 36KA", "ACB 4 pole 800A 36KA", "1SDA072874R1"),
        ("ACB 4P 800A 36KA", "800A air circuit breaker 4P 36KA", "1SDA072874R1"),
        ("ACB 4P 800A 36KA", "circuit breaker 4P 800 amp 36ka", "1SDA072874R1"),
        
        # MCCB (Molded Case Circuit Breaker) variations
        ("MCCB 100A 3P 50KA", "molded case circuit breaker 100A 3P 50KA", "1SDA067406R1"),
        ("MCCB 100A 3P 50KA", "MCCB 100 amp 3 pole 50 KA", "1SDA067406R1"),
        ("MCCB 100A 3P 50KA", "100A MCCB 3P 50KA", "1SDA067406R1"),
        ("MCCB 100A 3P 50KA", "circuit breaker 100A 3P 50KA", "1SDA067406R1"),
        ("MCCB 100A 3P 50KA", "100 amp molded circuit breaker 3 pole", "1SDA067406R1"),
        
        ("MCCB 160A 3P 36KA", "MCCB 160 amp 3P 36KA", "1SDA067418R1"),
        ("MCCB 160A 3P 36KA", "160A molded case breaker 3 pole 36KA", "1SDA067418R1"),
        ("MCCB 160A 3P 36KA", "molded circuit breaker 160A 3P", "1SDA067418R1"),
        
        # MCB (Miniature Circuit Breaker) variations  
        ("MCB C10A 1P 10KA", "miniature circuit breaker C10A 1P 10KA", "2CDS251001R0104"),
        ("MCB C10A 1P 10KA", "MCB C 10A 1 pole 10KA", "2CDS251001R0104"),
        ("MCB C10A 1P 10KA", "mini circuit breaker 10A C curve 1P", "2CDS251001R0104"),
        ("MCB C10A 1P 10KA", "10A MCB C type 1P", "2CDS251001R0104"),
        ("MCB C10A 1P 10KA", "C10 miniature breaker 1 pole", "2CDS251001R0104"),
        
        ("MCB C20A 2P 10KA", "MCB C 20A 2P 10KA", "2CDS272001R0204"),
        ("MCB C20A 2P 10KA", "miniature circuit breaker 20A C curve 2P", "2CDS272001R0204"),
        ("MCB C20A 2P 10KA", "20A MCB C type 2 pole", "2CDS272001R0204"),
        
        # RCCB (Residual Current Circuit Breaker) variations
        ("RCCB 4P 40A 30mA", "residual current circuit breaker 4P 40A 30mA", "2CSF204005R3400"),
        ("RCCB 4P 40A 30mA", "RCCB 4 pole 40A 30 mA", "2CSF204005R3400"),
        ("RCCB 4P 40A 30mA", "40A RCCB 4P 30mA trip", "2CSF204005R3400"),
        ("RCCB 4P 40A 30mA", "residual current breaker 40A 4 pole 30mA", "2CSF204005R3400"),
        
        # Contactor variations
        ("contactor 20A", "mini contactor 20A", "GJL1211001R8100"),
        ("contactor 20A", "contactor 20 amp", "GJL1211001R8100"),
        ("contactor 20A", "20A contactor", "GJL1211001R8100"),
        ("contactor 20A", "mini type contactor 20A", "GJL1211001R8100"),
        
        # Isolator/Switch Disconnector variations
        ("isolator 4P 63A", "switch disconnector 4P 63A", "2CDD284101R0063"),
        ("isolator 4P 63A", "isolator 4 pole 63A", "2CDD284101R0063"),
        ("isolator 4P 63A", "63A isolator 4P", "2CDD284101R0063"),
        ("isolator 4P 63A", "disconnect switch 4P 63A", "2CDD284101R0063"),
        ("isolator 4P 63A", "load break switch 4P 63A", "2CDD284101R0063"),
        
        ("isolator 2P 100A", "isolator 2 pole 100A", "2CDE282001R0100"),
        ("isolator 2P 100A", "switch disconnector 2P 100A", "2CDE282001R0100"),
        ("isolator 2P 100A", "100A isolator 2P", "2CDE282001R0100"),
        
        # Accessories variations
        ("MCCB auxiliary switch", "MCCB aux switch", "1SDA066431R1"),
        ("MCCB auxiliary switch", "MCCB accessory auxiliary switch", "1SDA066431R1"),
        ("MCCB auxiliary switch", "auxiliary contact for MCCB", "1SDA066431R1"),
        ("MCCB auxiliary switch", "MCCB ACC AUX SW", "1SDA066431R1"),
        
        ("MCCB shunt trip", "MCCB shunt trip coil", "1SDA054873R1"),
        ("MCCB shunt trip", "shunt trip for MCCB", "1SDA054873R1"),
        ("MCCB shunt trip", "MCCB ACC SHUNT TRIP", "1SDA054873R1"),
        
        # Mixed format variations
        ("breaker 100A 3P", "circuit breaker 100A 3P", "1SDA067406R1"),
        ("switch 63A 4P", "switch disconnector 63A 4P", "2CDD284101R0063"),
        ("relay thermal overload", "thermal overload relay", "1SAZ211201R2009"),
        ("time delay relay", "time relay delay", "1SVR500020R0000"),
        
        # Abbreviated vs full terms
        ("CB 100A", "circuit breaker 100A", "1SDA067406R1"),
        ("SW DISC 63A", "switch disconnector 63A", "2CDD284101R0063"),
        ("AUX CONT", "auxiliary contact", "1SDA066431R1"),
        ("OL RELAY", "overload relay", "1SAZ211201R2009"),
        
        # Current/voltage format variations
        ("800 amp ACB", "ACB 800A", "1SDA072894R1"),
        ("100 amp MCCB", "MCCB 100A", "1SDA067406R1"),
        ("63 amp isolator", "isolator 63A", "2CDD284101R0063"),
        ("20 amp contactor", "contactor 20A", "GJL1211001R8100"),
        
        # Pole format variations
        ("4 pole ACB", "ACB 4P", "1SDA072894R1"),
        ("3 pole MCCB", "MCCB 3P", "1SDA067406R1"),
        ("2 pole MCB", "MCB 2P", "2CDS272001R0204"),
        ("1 pole MCB", "MCB 1P", "2CDS251001R0104"),
        
        # KA format variations
        ("65 KA ACB", "ACB 65KA", "1SDA072894R1"),
        ("50 KA MCCB", "MCCB 50KA", "1SDA067406R1"),
        ("36 ka circuit breaker", "circuit breaker 36KA", "1SDA067418R1"),
        
        # Product type synonyms
        ("air breaker 800A", "ACB 800A", "1SDA072894R1"),
        ("molded breaker 100A", "MCCB 100A", "1SDA067406R1"),
        ("mini breaker 10A", "MCB 10A", "2CDS251001R0104"),
        ("residual breaker 40A", "RCCB 40A", "2CSF204005R3400"),
        
        # Typos and misspellings (common ones)
        ("circit breaker 100A", "circuit breaker 100A", "1SDA067406R1"),
        ("contactor 20A", "contactor 20A", "GJL1211001R8100"),
        ("siwtch disconnector", "switch disconnector", "2CDD284101R0063"),
        ("auxillary switch", "auxiliary switch", "1SDA066431R1"),
        
        # Partial queries
        ("800A breaker", "ACB 800A", "1SDA072894R1"),
        ("100A 3P", "MCCB 100A 3P", "1SDA067406R1"),
        ("4P 63A", "isolator 4P 63A", "2CDD284101R0063"),
        ("20A mini", "contactor 20A", "GJL1211001R8100"),
        
        # Reordered terms
        ("4P 800A 65KA ACB", "ACB 4P 800A 65KA", "1SDA072894R1"),
        ("3P 100A 50KA MCCB", "MCCB 100A 3P 50KA", "1SDA067406R1"),
        ("1P 10A C MCB", "MCB C10A 1P", "2CDS251001R0104"),
        ("4P 40A 30mA RCCB", "RCCB 4P 40A 30mA", "2CSF204005R3400"),
    ]
    
    return fuzzy_test_cases

def run_extensive_fuzzy_tests():
    """Run comprehensive fuzzy tests."""
    matcher = FastProductMatcher()
    matcher.load_model()
    
    fuzzy_cases = create_fuzzy_test_cases()
    
    print(f"Running extensive fuzzy validation with {len(fuzzy_cases)} test cases...")
    print("="*80)
    
    # Group results by category
    results_by_category = {
        'ACB': {'passed': 0, 'total': 0, 'failed': []},
        'MCCB': {'passed': 0, 'total': 0, 'failed': []},
        'MCB': {'passed': 0, 'total': 0, 'failed': []},
        'RCCB': {'passed': 0, 'total': 0, 'failed': []},
        'Contactor': {'passed': 0, 'total': 0, 'failed': []},
        'Isolator': {'passed': 0, 'total': 0, 'failed': []},
        'Accessories': {'passed': 0, 'total': 0, 'failed': []},
        'Other': {'passed': 0, 'total': 0, 'failed': []}
    }
    
    overall_passed = 0
    overall_total = len(fuzzy_cases)
    
    for i, (original_query, fuzzy_query, expected_code) in enumerate(fuzzy_cases, 1):
        results = matcher.search_fast(fuzzy_query, top_k=5)
        
        # Check if expected result is in top 3
        found_match = False
        rank = -1
        
        # Get top 3 results only
        top_3_results = results[:3]
        
        for j, result in enumerate(top_3_results):
            if result['order_code'] == expected_code:
                found_match = True
                rank = j + 1
                break
        
        # Determine category
        category = 'Other'
        if 'acb' in fuzzy_query.lower() or 'air circuit' in fuzzy_query.lower():
            category = 'ACB'
        elif 'mccb' in fuzzy_query.lower() or 'molded' in fuzzy_query.lower():
            category = 'MCCB'
        elif 'mcb' in fuzzy_query.lower() or 'miniature' in fuzzy_query.lower() or 'mini' in fuzzy_query.lower():
            category = 'MCB'
        elif 'rccb' in fuzzy_query.lower() or 'residual' in fuzzy_query.lower():
            category = 'RCCB'
        elif 'contactor' in fuzzy_query.lower():
            category = 'Contactor'
        elif 'isolator' in fuzzy_query.lower() or 'switch' in fuzzy_query.lower() or 'disconnect' in fuzzy_query.lower():
            category = 'Isolator'
        elif 'aux' in fuzzy_query.lower() or 'shunt' in fuzzy_query.lower() or 'relay' in fuzzy_query.lower():
            category = 'Accessories'
        
        results_by_category[category]['total'] += 1
        
        if found_match:  # Accept if found in top 3
            overall_passed += 1
            results_by_category[category]['passed'] += 1
            status = f"✓ PASS (rank {rank})"
        else:
            status = "✗ FAIL (not in top 3)"
            results_by_category[category]['failed'].append({
                'original': original_query,
                'fuzzy': fuzzy_query,
                'expected': expected_code,
                'top_3': [r['order_code'] for r in top_3_results],
                'rank': rank
            })
        
        # Show progress every 25 tests
        if i % 25 == 0:
            current_accuracy = (overall_passed / i) * 100
            print(f"Progress: {i}/{overall_total} - Accuracy so far: {current_accuracy:.1f}%")
        
        # Show detailed output for failures with top 3 results
        if not found_match:
            print(f"FAIL #{i}: '{fuzzy_query[:50]}...'")
            print(f"  Expected: {expected_code}")
            print(f"  Top 3:    {[r['order_code'] for r in top_3_results]}")
            scores = [f"{r['probability']:.3f}" for r in top_3_results]
            print(f"  Scores:   {scores}")
    
    # Summary by category
    print(f"\n{'='*80}")
    print("FUZZY TEST RESULTS BY CATEGORY")
    print(f"{'='*80}")
    
    for category, data in results_by_category.items():
        if data['total'] > 0:
            accuracy = (data['passed'] / data['total']) * 100
            print(f"{category:<12}: {data['passed']}/{data['total']} ({accuracy:.1f}%)")
            
            # Show failed cases for each category
            if data['failed']:
                print(f"  Failed cases:")
                for fail in data['failed'][:3]:  # Show first 3 failures
                    print(f"    '{fail['fuzzy'][:35]}...' -> Expected: {fail['expected']}")
                    print(f"      Top 3: {fail['top_3']}")
                if len(data['failed']) > 3:
                    print(f"    ... and {len(data['failed'])-3} more")
    
    # Overall summary
    overall_accuracy = (overall_passed / overall_total) * 100
    print(f"\n{'='*80}")
    print("OVERALL FUZZY TEST SUMMARY")
    print(f"{'='*80}")
    print(f"Total Test Cases: {overall_total}")
    print(f"Passed (top 3): {overall_passed}")
    print(f"Failed: {overall_total - overall_passed}")
    print(f"Accuracy: {overall_accuracy:.1f}%")
    
    if overall_accuracy >= 70:
        print("✅ Fuzzy matching performance is good!")
    elif overall_accuracy >= 50:
        print("⚠️  Fuzzy matching performance is moderate")
    else:
        print("❌ Fuzzy matching needs improvement")
    
    return overall_accuracy

if __name__ == "__main__":
    run_extensive_fuzzy_tests()