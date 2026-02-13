"""
Bootstrap Configuration Loader

Loads and validates the defaults.yaml configuration file for database bootstrapping.
"""

import os
import logging
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)


@dataclass
class UserConfig:
    """Configuration for a default user account"""
    email: str
    password: str
    name: str
    roles: List[str]


@dataclass
class ModelConfig:
    """Configuration for a default LLM model"""
    provider: str
    model: str
    name: str
    temperature: float
    max_tokens: int
    timeout: int


class BootstrapConfigLoader:
    """Loads and validates config/defaults.yaml for database bootstrapping"""
    
    VALID_PROVIDERS = {'ollama', 'openai', 'deepinfra', 'anthropic'}
    VALID_ROLE_PREFIXES = {'admin', 'user', 'super_admin', 'auditor', 'settings_manager'}
    
    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path or os.getenv(
            'DEFAULTS_CONFIG_PATH', 
            'config/defaults.yaml'
        )
        self.config: Dict[str, Any] = {}
        self.users: List[UserConfig] = []
        self.models: List[ModelConfig] = []
    
    def load(self) -> bool:
        """
        Load YAML configuration from file.
        
        Returns:
            True if loaded successfully, False otherwise
        """
        config_file = Path(self.config_path)
        
        if not config_file.exists():
            logger.warning(f"Bootstrap configuration file not found: {self.config_path}")
            return False
        
        try:
            with open(config_file, 'r') as f:
                self.config = yaml.safe_load(f)
            logger.info(f"Loaded bootstrap configuration from {self.config_path}")
            return True
        except yaml.YAMLError as e:
            logger.error(f"Failed to parse YAML configuration: {e}")
            return False
        except Exception as e:
            logger.error(f"Failed to load configuration file: {e}")
            return False
    
    def validate(self) -> List[str]:
        """
        Validate the loaded configuration.
        
        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []
        
        if not self.config:
            errors.append("Configuration is empty or not loaded")
            return errors
        
        # Validate users section
        if 'users' not in self.config:
            errors.append("Missing 'users' section in configuration")
        elif not isinstance(self.config['users'], list):
            errors.append("'users' must be a list")
        else:
            user_errors = self._validate_users(self.config['users'])
            errors.extend(user_errors)
        
        # Validate providers section
        if 'providers' not in self.config:
            errors.append("Missing 'providers' section in configuration")
        elif not isinstance(self.config['providers'], dict):
            errors.append("'providers' must be a dictionary")
        else:
            provider_errors = self._validate_providers(self.config['providers'])
            errors.extend(provider_errors)
        
        if not errors:
            self._parse_config()
        
        return errors
    
    def _validate_users(self, users: List[Dict]) -> List[str]:
        """Validate user configurations"""
        errors = []
        
        for i, user in enumerate(users):
            if not isinstance(user, dict):
                errors.append(f"User {i} must be a dictionary")
                continue
            
            # Required fields
            if 'email' not in user or not user['email']:
                errors.append(f"User {i}: Missing 'email' field")
            elif not self._is_valid_email(user['email']):
                errors.append(f"User {i}: Invalid email format: {user.get('email')}")
            
            if 'password' not in user or not user['password']:
                errors.append(f"User {i}: Missing 'password' field")
            
            if 'name' not in user or not user['name']:
                errors.append(f"User {i}: Missing 'name' field")
            
            # Optional roles field
            if 'roles' in user:
                if not isinstance(user['roles'], list):
                    errors.append(f"User {i}: 'roles' must be a list")
                else:
                    for role in user['roles']:
                        if not isinstance(role, str):
                            errors.append(f"User {i}: Role '{role}' must be a string")
        
        return errors
    
    def _validate_providers(self, providers: Dict[str, List[Dict]]) -> List[str]:
        """Validate provider configurations"""
        errors = []
        
        for provider_name, models in providers.items():
            # Normalize provider name (fix typo in example: opan_ai -> openai)
            normalized_provider = self._normalize_provider_name(provider_name)
            
            if normalized_provider not in self.VALID_PROVIDERS:
                errors.append(f"Invalid provider: '{provider_name}' (must be one of: {', '.join(sorted(self.VALID_PROVIDERS))})")
                continue
            
            if not isinstance(models, list):
                errors.append(f"'{provider_name}' must be a list of models")
                continue
            
            for i, model in enumerate(models):
                if not isinstance(model, dict):
                    errors.append(f"{provider_name} model {i}: Must be a dictionary")
                    continue
                
                # Required fields
                if 'model' not in model or not model['model']:
                    errors.append(f"{provider_name} model {i}: Missing 'model' field")
                
                if 'name' not in model or not model['name']:
                    errors.append(f"{provider_name} model {i}: Missing 'name' field")
                
                # Optional numeric fields with defaults
                temperature = model.get('temperature', 0)
                if not isinstance(temperature, (int, float)) or temperature < 0 or temperature > 2:
                    errors.append(f"{provider_name} model {i}: 'temperature' must be between 0 and 2")
                
                max_tokens = model.get('max_tokens', 2048)
                if not isinstance(max_tokens, int) or max_tokens <= 0:
                    errors.append(f"{provider_name} model {i}: 'max_tokens' must be a positive integer")
                
                timeout = model.get('timeout', 360)
                if not isinstance(timeout, int) or timeout <= 0:
                    errors.append(f"{provider_name} model {i}: 'timeout' must be a positive integer")
        
        return errors
    
    def _parse_config(self) -> None:
        """Parse validated configuration into data objects"""
        # Parse users
        self.users = []
        for user_data in self.config.get('users', []):
            if isinstance(user_data, dict):
                self.users.append(UserConfig(
                    email=user_data['email'],
                    password=user_data['password'],
                    name=user_data['name'],
                    roles=user_data.get('roles', [])
                ))
        
        # Parse models
        self.models = []
        for provider_name, models in self.config.get('providers', {}).items():
            normalized_provider = self._normalize_provider_name(provider_name)
            if normalized_provider in self.VALID_PROVIDERS:
                for model_data in models:
                    if isinstance(model_data, dict):
                        self.models.append(ModelConfig(
                            provider=normalized_provider,
                            model=model_data['model'],
                            name=model_data['name'],
                            temperature=float(model_data.get('temperature', 0)),
                            max_tokens=int(model_data.get('max_tokens', 2048)),
                            timeout=int(model_data.get('timeout', 360))
                        ))
    
    def _normalize_provider_name(self, provider: str) -> str:
        """Normalize provider name (fix common typos)"""
        provider_lower = provider.lower()
        if provider_lower == 'opan_ai':
            return 'openai'
        return provider_lower
    
    def _is_valid_email(self, email: str) -> bool:
        """Basic email validation"""
        if not email or '@' not in email:
            return False
        parts = email.split('@')
        return len(parts) == 2 and len(parts[0]) > 0 and len(parts[1]) > 0
    
    def get_users(self) -> List[UserConfig]:
        """Get parsed user configurations"""
        return self.users
    
    def get_models(self) -> List[ModelConfig]:
        """Get parsed model configurations"""
        return self.models
