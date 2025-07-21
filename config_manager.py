#!/usr/bin/env python3
"""
Configuration manager for ABB Product Search.
Handles loading configuration and determining data paths.
"""

import os
import json
import sys
from pathlib import Path

class ConfigManager:
    def __init__(self):
        self.config = None
        self.config_path = None
        self.load_config()
        
    def find_config_file(self):
        """Find the configuration file in various locations."""
        possible_paths = [
            # Next to the executable/script
            os.path.join(os.path.dirname(os.path.abspath(__file__)), 'app_config.json'),
            # In application data directory
            os.path.join(self._get_app_data_dir(), 'config', 'app_config.json'),
            # In current directory
            'app_config.json'
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                return path
        return None
        
    def _get_app_data_dir(self):
        """Get the application data directory based on OS."""
        if sys.platform == "win32":
            return os.path.join(os.environ.get('APPDATA', ''), 'ABB Product Search')
        else:
            return os.path.expanduser('~/.abb_product_search')
            
    def load_config(self):
        """Load configuration from file or create default."""
        self.config_path = self.find_config_file()
        
        if self.config_path and os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r') as f:
                    self.config = json.load(f)
                print(f"✅ Loaded configuration from {self.config_path}")
            except Exception as e:
                print(f"⚠️  Error loading config: {e}")
                self.config = self._get_default_config()
        else:
            print("📁 Using default configuration")
            self.config = self._get_default_config()
            
    def _get_default_config(self):
        """Get default configuration."""
        app_data_dir = self._get_app_data_dir()
        
        return {
            "install_dir": os.path.dirname(os.path.abspath(__file__)),
            "data_dir": os.path.join(app_data_dir, 'data'),
            "models_dir": os.path.join(app_data_dir, 'models'),
            "training_dir": os.path.join(app_data_dir, 'training'), 
            "logs_dir": os.path.join(app_data_dir, 'logs'),
            "port": 5001,
            "host": "0.0.0.0",
            "debug": False
        }
        
    def get(self, key, default=None):
        """Get configuration value."""
        return self.config.get(key, default)
        
    def get_data_file_path(self, filename):
        """Get full path to a data file."""
        data_dir = self.get('data_dir')
        return os.path.join(data_dir, filename)
        
    def get_model_file_path(self, filename):
        """Get full path to a model file."""
        models_dir = self.get('models_dir') 
        return os.path.join(models_dir, filename)
        
    def get_training_file_path(self, filename):
        """Get full path to a training file."""
        training_dir = self.get('training_dir')
        return os.path.join(training_dir, filename)
        
    def get_log_file_path(self, filename):
        """Get full path to a log file."""
        logs_dir = self.get('logs_dir')
        return os.path.join(logs_dir, filename)
        
    def ensure_directories_exist(self):
        """Ensure all configured directories exist."""
        dirs_to_create = [
            self.get('data_dir'),
            self.get('models_dir'),
            self.get('training_dir'),
            self.get('logs_dir')
        ]
        
        for dir_path in dirs_to_create:
            if dir_path and not os.path.exists(dir_path):
                try:
                    os.makedirs(dir_path, exist_ok=True)
                    print(f"📁 Created directory: {dir_path}")
                except Exception as e:
                    print(f"❌ Failed to create directory {dir_path}: {e}")

# Global configuration instance
config_manager = ConfigManager()