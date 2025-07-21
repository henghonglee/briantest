#!/usr/bin/env python3
"""
Utility functions for handling resources in both development and installed environments.
"""

import os
import sys
from config_manager import config_manager


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
    """Get path to training CSV file."""
    # First try config manager (installed version)
    try:
        return config_manager.get_training_file_path("training.csv")
    except:
        # Fallback to bundled resource (PyInstaller)
        return get_resource_path(os.path.join("training", "training.csv"))


def get_abb_csv_path():
    """Get path to ABB CSV file."""
    # First try config manager (installed version)
    try:
        return config_manager.get_data_file_path("ABB.csv")
    except:
        # Fallback to bundled resource (PyInstaller)
        return get_resource_path("ABB.csv")


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