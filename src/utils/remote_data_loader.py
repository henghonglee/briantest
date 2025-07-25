import requests
import pandas as pd
import os
from io import StringIO
import time

class RemoteDataLoader:
    def __init__(self):
        # GitHub raw URLs for data files
        self.base_url = "https://raw.githubusercontent.com/henghonglee/briantest/main"
        self.training_url = f"{self.base_url}/data/training/training.csv"
        self.catalog_url = f"{self.base_url}/data/ABB.csv"
        
        # Cache settings
        self.cache_timeout = 300  # 5 minutes
        self._cache = {}
        self._cache_timestamps = {}
    
    def _download_with_retry(self, url, max_retries=3, timeout=30):
        """Download data with retry mechanism"""
        for attempt in range(max_retries):
            try:
                response = requests.get(url, timeout=timeout)
                response.raise_for_status()
                return response.text
            except requests.RequestException as e:
                if attempt == max_retries - 1:
                    raise Exception(f"Failed to download {url} after {max_retries} attempts: {str(e)}")
                time.sleep(2 ** attempt)  # Exponential backoff
    
    def _is_cache_valid(self, cache_key):
        """Check if cached data is still valid"""
        if cache_key not in self._cache_timestamps:
            return False
        return time.time() - self._cache_timestamps[cache_key] < self.cache_timeout
    
    def load_training_data(self):
        """Load training data from remote storage with caching"""
        cache_key = 'training_data'
        
        # Return cached data if valid
        if self._is_cache_valid(cache_key):
            return self._cache[cache_key]
        
        try:
            print("📥 Downloading training data from remote storage...")
            csv_content = self._download_with_retry(self.training_url)
            
            # Parse CSV content with encoding detection
            # Try different encodings to handle various CSV file formats
            encodings = ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']
            df = None
            for encoding in encodings:
                try:
                    # For remote content, try decoding the content with different encodings
                    if encoding != 'utf-8':
                        # Re-encode to bytes and decode with target encoding
                        csv_bytes = csv_content.encode('latin1')  # Safe encoding for bytes
                        decoded_content = csv_bytes.decode(encoding)
                    else:
                        decoded_content = csv_content
                    df = pd.read_csv(StringIO(decoded_content))
                    break
                except (UnicodeDecodeError, pd.errors.ParserError):
                    continue
            
            if df is None:
                # Final fallback with error replacement
                df = pd.read_csv(StringIO(csv_content), encoding='utf-8', errors='replace')
            
            # Cache the data
            self._cache[cache_key] = df
            self._cache_timestamps[cache_key] = time.time()
            
            print(f"✅ Successfully loaded {len(df)} training examples from remote storage")
            return df
            
        except Exception as e:
            print(f"❌ Failed to load training data from remote storage: {str(e)}")
            # Return empty DataFrame as fallback
            return pd.DataFrame(columns=['Customer Query', 'Order Code', 'Description'])
    
    def load_catalog_data(self):
        """Load product catalog from remote storage with caching"""
        cache_key = 'catalog_data'
        
        # Return cached data if valid
        if self._is_cache_valid(cache_key):
            return self._cache[cache_key]
        
        try:
            print("📥 Downloading catalog data from remote storage...")
            csv_content = self._download_with_retry(self.catalog_url)
            
            # Parse CSV content with encoding detection
            # Try different encodings to handle various CSV file formats
            encodings = ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']
            df = None
            for encoding in encodings:
                try:
                    # For remote content, try decoding the content with different encodings
                    if encoding != 'utf-8':
                        # Re-encode to bytes and decode with target encoding
                        csv_bytes = csv_content.encode('latin1')  # Safe encoding for bytes
                        decoded_content = csv_bytes.decode(encoding)
                    else:
                        decoded_content = csv_content
                    df = pd.read_csv(StringIO(decoded_content))
                    break
                except (UnicodeDecodeError, pd.errors.ParserError):
                    continue
            
            if df is None:
                # Final fallback with error replacement
                df = pd.read_csv(StringIO(csv_content), encoding='utf-8', errors='replace')
            
            # Cache the data
            self._cache[cache_key] = df
            self._cache_timestamps[cache_key] = time.time()
            
            print(f"✅ Successfully loaded {len(df)} catalog items from remote storage")
            return df
            
        except Exception as e:
            print(f"❌ Failed to load catalog data from remote storage: {str(e)}")
            # Return empty DataFrame as fallback
            return pd.DataFrame()
    
    def clear_cache(self):
        """Clear all cached data"""
        self._cache.clear()
        self._cache_timestamps.clear()
        print("🗑️ Cache cleared")

# Global instance
remote_loader = RemoteDataLoader()