#!/usr/bin/env python3
"""
Utility functions for handling resources in both development and installed environments.
"""

import os
import sys
from .config_manager import config_manager
from .remote_data_loader import remote_loader


def get_resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller"""
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
        return os.path.join(base_path, relative_path)
    except Exception:
        # Not running from PyInstaller, use config manager
        return os.path.join(os.path.abspath("."), relative_path)


def get_training_csv_path():
    """Get path to training CSV file or load from remote."""
    # First try config manager (installed version)
    try:
        local_path = config_manager.get_training_file_path("training.csv")
        if os.path.exists(local_path):
            return local_path
    except:
        pass
    
    # Try bundled resource (PyInstaller)
    try:
        bundled_path = get_resource_path(os.path.join("training", "training.csv"))
        if os.path.exists(bundled_path):
            return bundled_path
    except:
        pass
    
    # Fallback to remote loading - return special marker
    return "REMOTE_TRAINING_DATA"


def get_abb_csv_path():
    """Get path to ABB CSV file or load from remote."""
    # First try config manager (installed version)
    try:
        local_path = config_manager.get_data_file_path("ABB.csv")
        if os.path.exists(local_path):
            return local_path
    except:
        pass
    
    # Try bundled resource (PyInstaller)
    try:
        bundled_path = get_resource_path("ABB.csv")
        if os.path.exists(bundled_path):
            return bundled_path
    except:
        pass
    
    # Fallback to remote loading - return special marker
    return "REMOTE_ABB_DATA"


def load_training_data():
    """Load training data from database, local file, or remote source."""
    # First try database
    try:
        from src.models.models import TrainingData
        df = TrainingData.get_all_as_dataframe()
        if len(df) > 0:
            print(f"📊 Loaded {len(df)} training examples from database")
            return df
    except Exception as e:
        print(f"⚠️  Database not available, trying fallback: {e}")
    
    # Fallback to CSV sources
    path = get_training_csv_path()
    if path == "REMOTE_TRAINING_DATA":
        return remote_loader.load_training_data()
    else:
        import pandas as pd
        # Try different encodings to handle various CSV file formats
        encodings = ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']
        for encoding in encodings:
            try:
                return pd.read_csv(path, encoding=encoding)
            except UnicodeDecodeError:
                continue
        # If all encodings fail, try with error handling
        return pd.read_csv(path, encoding='utf-8', errors='replace')


def load_catalog_data():
    """Load catalog data from local file or remote source."""
    path = get_abb_csv_path()
    if path == "REMOTE_ABB_DATA":
        return remote_loader.load_catalog_data()
    else:
        import pandas as pd
        # Try different encodings to handle various CSV file formats
        encodings = ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']
        for encoding in encodings:
            try:
                return pd.read_csv(path, encoding=encoding)
            except UnicodeDecodeError:
                continue
        # If all encodings fail, try with error handling
        return pd.read_csv(path, encoding='utf-8', errors='replace')


def get_fast_model_path():
    """Get path to fast matcher model."""
    # First try config manager (installed version)
    try:
        return config_manager.get_model_file_path("fast_matcher_model.pkl")
    except:
        # Fallback to bundled resource (PyInstaller)
        return get_resource_path("fast_matcher_model.pkl")


def get_product_model_path():
    """Get path to product matcher model."""
    # First try config manager (installed version)
    try:
        return config_manager.get_model_file_path("product_matcher_model.pkl")
    except:
        # Fallback to bundled resource (PyInstaller)
        return get_resource_path("product_matcher_model.pkl")