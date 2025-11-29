"""
Configuration loader for API keys and sensitive parameters.
Loads configuration from config.csv and environment variables.
"""

import os
import csv
from pathlib import Path
from typing import Optional


class ConfigLoader:
    """Load and manage configuration from CSV and environment variables."""
    
    def __init__(self, config_file: str = "config.csv"):
        """
        Initialize config loader.
        
        Args:
            config_file: Path to config.csv file
        """
        self.config_file = config_file
        self.config = {}
        self._load_config()
    
    def _load_config(self):
        """Load configuration from CSV file."""
        if not Path(self.config_file).exists():
            raise FileNotFoundError(
                f"Config file not found: {self.config_file}\n"
                f"Please create {self.config_file} from {self.config_file}.template"
            )
        
        try:
            with open(self.config_file, 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row and 'api_key' in row and 'value' in row:
                        key = row['api_key'].strip()
                        value = row['value'].strip()
                        if key:
                            self.config[key] = value
        except Exception as e:
            raise ValueError(f"Error reading config file: {e}")
    
    def get(self, key: str, default: Optional[str] = None, env_var: Optional[str] = None) -> Optional[str]:
        """
        Get configuration value.
        
        Priority:
        1. Environment variable (if specified)
        2. Config file value
        3. Default value
        
        Args:
            key: Configuration key
            default: Default value if not found
            env_var: Environment variable name to check first
            
        Returns:
            Configuration value or None
        """
        # Check environment variable first if specified
        if env_var:
            env_value = os.getenv(env_var)
            if env_value:
                return env_value
        
        # Check config file
        value = self.config.get(key, default)
        
        # Validate not placeholder
        if value == "your_api_key_here":
            raise ValueError(
                f"Config value for '{key}' is still placeholder 'your_api_key_here'. "
                f"Please update {self.config_file} with your actual API key."
            )
        
        return value
    
    def get_alpha_vantage_key(self) -> str:
        """
        Get Alpha Vantage API key.
        
        Returns:
            API key string
            
        Raises:
            ValueError: If key not found or is placeholder
        """
        key = self.get(
            "alpha_vantage_key",
            env_var="ALPHA_VANTAGE_KEY"
        )
        
        if not key:
            raise ValueError(
                "Alpha Vantage API key not found. "
                "Set ALPHA_VANTAGE_KEY env var or add to config.csv"
            )
        
        return key


# Create global config instance
config = ConfigLoader()
