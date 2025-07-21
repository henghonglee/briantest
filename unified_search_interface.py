#!/usr/bin/env python3
"""
Unified search interface allowing users to choose between fast search and probabilistic models.
"""

import sys
import time
from typing import Optional, List, Dict, Any

# Import both search models
try:
    from fast_search import FastProductMatcher
    fast_search_available = True
except ImportError as e:
    print(f"Warning: Fast search not available: {e}")
    fast_search_available = False

# Disable probabilistic search for now
probabilistic_search_available = False

class UnifiedSearchInterface:
    def __init__(self):
        self.fast_matcher = None
        self.probabilistic_matcher = None
        self.current_model = None
        
        # Initialize available models
        if fast_search_available:
            print("Loading Fast Search model...")
            try:
                self.fast_matcher = FastProductMatcher()
                self.fast_matcher.load_model()
                print("✅ Fast Search model loaded successfully")
            except Exception as e:
                print(f"❌ Failed to load Fast Search model: {e}")
                self.fast_matcher = None
        
        # Probabilistic search disabled for now
        # if probabilistic_search_available:
        #     print("Loading Probabilistic Search model...")
        #     try:
        #         self.probabilistic_matcher = ProbabilisticProductMatcher()
        #         self.probabilistic_matcher.load_model()
        #         print("✅ Probabilistic Search model loaded successfully")
        #     except Exception as e:
        #         print(f"❌ Failed to load Probabilistic Search model: {e}")
        #         self.probabilistic_matcher = None
    
    def get_available_models(self) -> List[str]:
        """Get list of available search models."""
        models = []
        if self.fast_matcher:
            models.append("fast")
        if self.probabilistic_matcher:
            models.append("probabilistic")
        return models
    
    def display_model_info(self):
        """Display information about available models."""
        print("\n" + "="*70)
        print("AVAILABLE SEARCH MODELS")
        print("="*70)
        
        if self.fast_matcher:
            print("🚀 FAST SEARCH")
            print("   • Ultra-fast query processing (~0.001s)")
            print("   • Compares with training queries directly")
            print("   • Best for: Quick searches, exact matches")
            print("   • Accuracy: 99.7% (training data, top 3)")
            print()
        
        # Probabilistic search option disabled for now
        # if self.probabilistic_matcher:
        #     print("🧠 PROBABILISTIC SEARCH") 
        #     print("   • Advanced ML-based matching")
        #     print("   • Learns from training data patterns")
        #     print("   • Best for: Complex queries, fuzzy matching")
        #     print("   • Accuracy: 95%+ (training data)")
        #     print()
        
        if not self.get_available_models():
            print("❌ No search models available!")
    
    def select_model(self) -> Optional[str]:
        """Allow user to select search model."""
        available_models = self.get_available_models()
        
        if not available_models:
            print("❌ No search models available!")
            return None
        
        if len(available_models) == 1:
            model = available_models[0]
            print(f"✅ Using {model} search (only available model)")
            return model
        
        print("\nSelect search model:")
        for i, model in enumerate(available_models, 1):
            model_name = "Fast Search" if model == "fast" else "Other Search"
            print(f"{i}. {model_name}")
        
        while True:
            try:
                choice = input(f"\nEnter choice (1-{len(available_models)}) or 'q' to quit: ").strip().lower()
                
                if choice == 'q':
                    return None
                
                choice_num = int(choice)
                if 1 <= choice_num <= len(available_models):
                    selected_model = available_models[choice_num - 1]
                    model_name = "Fast Search" if selected_model == "fast" else "Other Search"
                    print(f"✅ Selected: {model_name}")
                    return selected_model
                else:
                    print(f"Please enter a number between 1 and {len(available_models)}")
            
            except ValueError:
                print("Please enter a valid number or 'q' to quit")
            except KeyboardInterrupt:
                print("\n\n👋 Goodbye!")
                return None
    
    def search(self, query: str, model: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Perform search using specified model."""
        # Input validation
        if not query or not query.strip():
            raise ValueError("Query cannot be empty")
        
        if top_k <= 0:
            raise ValueError("top_k must be positive")
        
        if model not in self.get_available_models():
            available = ", ".join(self.get_available_models())
            raise ValueError(f"Model '{model}' not available. Available models: {available}")
        
        query = query.strip()
        
        try:
            if model == "fast" and self.fast_matcher:
                return self.fast_matcher.search_fast(query, top_k)
            else:
                raise ValueError(f"Model '{model}' not properly initialized")
        except Exception as e:
            raise RuntimeError(f"Search failed for model '{model}': {str(e)}")
    
    def display_results(self, results: List[Dict[str, Any]], model: str, search_time: float):
        """Display search results in a formatted way."""
        if not results:
            print("❌ No results found")
            return
        
        model_name = "Fast Search" if model == "fast" else "Other Search"
        print(f"\n🔍 {model_name} Results (⏱️ {search_time:.3f}s)")
        print("="*70)
        
        for i, result in enumerate(results, 1):
            print(f"{i}. {result['order_code']}")
            print(f"   📝 Description: {result['description']}")
            
            # Show model-specific information
            if model == "fast":
                if 'training_query' in result:
                    print(f"   🎯 Training Query: {result['training_query'][:50]}...")
                
                # Show match type if available
                match_type = result.get('match_type', 'fuzzy')
                if match_type == 'exact':
                    print(f"   ✨ EXACT MATCH - Score: {result['probability']:.3f}")
                else:
                    print(f"   📊 Score: {result['probability']:.3f} (TF-IDF: {result['tfidf_score']:.3f}, Fuzzy: {result['fuzzy_score']:.3f})")
            else:  # other search
                print(f"   📊 Probability: {result['probability']:.3f}")
            
            print()
    
    def interactive_search(self):
        """Run interactive search session."""
        print("\n" + "="*70)
        print("🔍 ABB PRODUCT SEARCH INTERFACE")
        print("="*70)
        
        # Display model information
        self.display_model_info()
        
        # Select model
        model = self.select_model()
        if not model:
            print("👋 Goodbye!")
            return
        
        self.current_model = model
        model_name = "Fast Search" if model == "fast" else "Other Search"
        
        print(f"\n🚀 Starting {model_name} session...")
        print("💡 Tips:")
        print("   • Try queries like: 'ACB 800A 4P', 'MCCB 100A', 'contactor 20A'")
        print("   • Type 'switch' to change models, 'help' for commands, 'quit' to exit")
        print()
        
        while True:
            try:
                # Get user query
                query = input("🔍 Enter search query: ").strip()
                
                if not query:
                    continue
                
                # Handle special commands
                if query.lower() in ['quit', 'exit', 'q']:
                    print("👋 Goodbye!")
                    break
                
                elif query.lower() in ['switch', 'change']:
                    new_model = self.select_model()
                    if new_model:
                        self.current_model = new_model
                        model_name = "Fast Search" if new_model == "fast" else "Other Search"
                        print(f"✅ Switched to {model_name}")
                    continue
                
                elif query.lower() == 'help':
                    print("\n📋 Available commands:")
                    print("   • 'switch' or 'change' - Change search model")
                    print("   • 'help' - Show this help")
                    print("   • 'quit', 'exit', or 'q' - Exit")
                    print("   • Any other text - Search for products")
                    continue
                
                elif query.lower() == 'info':
                    self.display_model_info()
                    continue
                
                # Perform search
                print(f"🔍 Searching for: '{query}'...")
                start_time = time.time()
                
                try:
                    results = self.search(query, self.current_model, top_k=5)
                    search_time = time.time() - start_time
                    
                    self.display_results(results, self.current_model, search_time)
                    
                except ValueError as e:
                    print(f"❌ Invalid input: {e}")
                except RuntimeError as e:
                    print(f"❌ Search error: {e}")
                except Exception as e:
                    print(f"❌ Unexpected error: {e}")
                    print("   Please try a different query or restart the application.")
                
            except KeyboardInterrupt:
                print("\n\n👋 Goodbye!")
                break
            except EOFError:
                print("\n\n👋 Goodbye!")
                break
    
    def batch_search(self, queries: List[str], model: str, top_k: int = 3):
        """Perform batch search for multiple queries."""
        # Input validation
        if not queries:
            print("❌ No queries provided for batch search")
            return
        
        if model not in self.get_available_models():
            available = ", ".join(self.get_available_models())
            print(f"❌ Model '{model}' not available. Available models: {available}")
            return
        
        if top_k <= 0:
            print("❌ top_k must be positive")
            return
        
        # Filter out empty queries
        valid_queries = [q.strip() for q in queries if q and q.strip()]
        if not valid_queries:
            print("❌ No valid queries provided (all queries are empty)")
            return
        
        if len(valid_queries) != len(queries):
            print(f"⚠️  Filtered out {len(queries) - len(valid_queries)} empty queries")
        
        model_name = "Fast Search" if model == "fast" else "Other Search"
        print(f"\n🔍 Batch Search using {model_name}")
        print("="*70)
        
        total_time = 0
        successful_searches = 0
        
        for i, query in enumerate(valid_queries, 1):
            print(f"\n{i}. Query: '{query}'")
            print("-" * 50)
            
            start_time = time.time()
            try:
                results = self.search(query, model, top_k)
                search_time = time.time() - start_time
                total_time += search_time
                successful_searches += 1
                
                if results:
                    for j, result in enumerate(results, 1):
                        score = result.get('probability', 0)
                        match_type = result.get('match_type', 'fuzzy')
                        match_indicator = "✨ EXACT" if match_type == 'exact' else "📊"
                        print(f"   {j}. {result['order_code']} ({match_indicator} Score: {score:.3f})")
                        print(f"      📝 {result['description']}")
                else:
                    print("   ❌ No results found")
                
                print(f"   ⏱️ Time: {search_time:.3f}s")
                
            except ValueError as e:
                print(f"   ❌ Invalid query: {e}")
            except RuntimeError as e:
                print(f"   ❌ Search error: {e}")
            except Exception as e:
                print(f"   ❌ Unexpected error: {e}")
        
        avg_time = total_time / successful_searches if successful_searches > 0 else 0
        print(f"\n📊 Batch Summary:")
        print(f"   Total queries: {len(queries)}")
        print(f"   Valid queries: {len(valid_queries)}")
        print(f"   Successful searches: {successful_searches}")
        print(f"   Failed searches: {len(valid_queries) - successful_searches}")
        print(f"   Total time: {total_time:.3f}s")
        print(f"   Average time: {avg_time:.3f}s per successful query")

def main():
    """Main function to run the unified search interface."""
    if len(sys.argv) > 1:
        # Batch mode with command line arguments
        search_interface = UnifiedSearchInterface()
        
        # Default to fast search for batch mode
        available_models = search_interface.get_available_models()
        if not available_models:
            print("❌ No search models available!")
            return
        
        model = "fast" if "fast" in available_models else available_models[0]
        queries = sys.argv[1:]
        
        search_interface.batch_search(queries, model)
    else:
        # Interactive mode
        search_interface = UnifiedSearchInterface()
        search_interface.interactive_search()

if __name__ == "__main__":
    main()