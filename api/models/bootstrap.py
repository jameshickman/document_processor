"""
Database Bootstrapping Module

Handles seeding the database with default configuration from config/defaults.yaml.
Provides idempotent operations that only populate empty tables.
"""

import os
import logging
import uuid
from dataclasses import dataclass
from typing import List, Optional

from sqlalchemy.orm import Session
from sqlalchemy import text

from api.util.bootstrap_config import BootstrapConfigLoader, UserConfig, ModelConfig
from api.util.password_security import PasswordSecurity
from api.models import Account, LLMModel

logger = logging.getLogger(__name__)


@dataclass
class BootstrapResult:
    """Result of database bootstrapping operation"""
    success: bool
    users_created: int = 0
    models_created: int = 0
    errors: List[str] = None
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []
    
    def __str__(self):
        status = "successful" if self.success else "failed"
        parts = [f"Bootstrapping {status}"]
        parts.append(f"Users created: {self.users_created}")
        parts.append(f"Models created: {self.models_created}")
        if self.errors:
            parts.append(f"Errors: {', '.join(self.errors)}")
        return ", ".join(parts)


class DatabaseBootstrapper:
    """Handles seeding database with default configuration"""
    
    def __init__(self, db: Session, config_loader: BootstrapConfigLoader):
        self.db = db
        self.config = config_loader
        self._password_secret = None
    
    def bootstrap(self) -> BootstrapResult:
        """
        Main entry point - executes all bootstrapping steps.
        
        Returns:
            BootstrapResult with details of the operation
        """
        result = BootstrapResult(success=True)
        
        try:
            logger.info("Starting database bootstrapping...")
            
            # Check if bootstrapping should proceed
            if not self._should_bootstrap():
                logger.info("Database already contains data, skipping bootstrapping")
                result.users_created = 0
                result.models_created = 0
                return result
            
            # Get password secret
            password_secret = os.getenv('PASSWORD_SECRET')
            if not password_secret:
                error = "PASSWORD_SECRET environment variable not set"
                logger.error(error)
                result.success = False
                result.errors.append(error)
                return result
            
            self._password_secret = password_secret
            
            # Seed users
            users_created = self._seed_users()
            result.users_created = users_created
            
            # Seed LLM models for each user
            models_created = 0
            users = self.db.query(Account).all()
            for user in users:
                count = self._seed_models(user.id)
                models_created += count
            result.models_created = models_created
            
            # Commit all changes
            self.db.commit()
            logger.info(f"Bootstrapping completed: {result}")
            
        except Exception as e:
            logger.error(f"Bootstrapping failed: {e}", exc_info=True)
            result.success = False
            result.errors.append(str(e))
            try:
                self.db.rollback()
            except Exception as rollback_error:
                logger.error(f"Failed to rollback transaction: {rollback_error}")
        
        return result
    
    def _should_bootstrap(self) -> bool:
        """
        Check if bootstrapping should proceed.
        
        Returns:
            True if database is empty or FORCE_BOOTSTRAP is enabled
        """
        # Check for force bootstrap (development only)
        force_bootstrap = os.getenv('FORCE_BOOTSTRAP', 'false').lower() == 'true'
        if force_bootstrap:
            logger.warning("FORCE_BOOTSTRAP enabled - will create records even if data exists")
            return True
        
        # Check if database is empty
        account_count = self.db.query(Account).count()
        model_count = self.db.query(LLMModel).count()
        
        # Only bootstrap if both tables are empty
        is_empty = account_count == 0 and model_count == 0
        
        if is_empty:
            logger.info("Database is empty, proceeding with bootstrapping")
        else:
            logger.info(f"Database contains {account_count} accounts and {model_count} models, skipping bootstrapping")
        
        return is_empty
    
    def _seed_users(self) -> int:
        """
        Seed default users from configuration.
        
        Returns:
            Number of users created
        """
        users = self.config.get_users()
        created = 0
        
        for user_config in users:
            try:
                # Check if user already exists by email
                existing = self.db.query(Account).filter(
                    Account.email == user_config.email
                ).first()
                
                if existing:
                    logger.info(f"User already exists: {user_config.email}, skipping")
                    continue
                
                # Create new user with encrypted password
                account = self._create_user(user_config)
                self.db.add(account)
                self.db.flush()
                
                created += 1
                logger.info(f"Created default user: {user_config.email} with roles: {user_config.roles}")
                
            except Exception as e:
                error_msg = f"Failed to create user {user_config.email}: {e}"
                logger.error(error_msg)
                raise Exception(error_msg)
        
        return created
    
    def _create_user(self, user_config: UserConfig) -> Account:
        """
        Create Account with encrypted password.
        
        Args:
            user_config: User configuration
            
        Returns:
            Account instance
        """
        # Generate unique salt
        salt = str(uuid.uuid4())
        
        # Create password security instance
        security = PasswordSecurity(self._password_secret, salt)
        encrypted_password = security.encrypt_password(user_config.password)
        
        # Create Account
        account = Account(
            email=user_config.email,
            name=user_config.name,
            password_local=encrypted_password,
            password_encrypted=True,
            password_salt=salt,
            active=True,
            grandfathered=False
        )
        
        return account
    
    def _seed_models(self, account_id: int) -> int:
        """
        Seed LLM models for specified account from configuration.
        
        Args:
            account_id: ID of the account to create models for
            
        Returns:
            Number of models created
        """
        models = self.config.get_models()
        created = 0
        
        for model_config in models:
            try:
                # Check if model already exists for this account
                existing = self.db.query(LLMModel).filter(
                    LLMModel.account_id == account_id,
                    LLMModel.provider == model_config.provider,
                    LLMModel.model_identifier == model_config.model
                ).first()
                
                if existing:
                    logger.info(
                        f"Model already exists: {model_config.provider}/{model_config.model}, "
                        f"skipping"
                    )
                    continue
                
                # Create new LLM model
                model = self._create_model(account_id, model_config)
                self.db.add(model)
                self.db.flush()
                
                created += 1
                logger.info(
                    f"Created default model: {model_config.provider}/{model_config.model} "
                    f"({model_config.name})"
                )
                
            except Exception as e:
                error_msg = f"Failed to create model {model_config.provider}/{model_config.model}: {e}"
                logger.error(error_msg)
                raise Exception(error_msg)
        
        return created
    
    def _create_model(self, account_id: int, model_config: ModelConfig) -> LLMModel:
        """
        Create LLMModel from configuration.
        
        Args:
            account_id: ID of the account
            model_config: Model configuration
            
        Returns:
            LLMModel instance
        """
        model = LLMModel(
            name=model_config.name,
            provider=model_config.provider,
            model_identifier=model_config.model,
            base_url=None,
            temperature=model_config.temperature,
            max_tokens=model_config.max_tokens,
            timeout=model_config.timeout,
            model_kwargs_json=None,
            account_id=account_id
        )
        
        return model


def bootstrap_database(db: Session, config_path: Optional[str] = None) -> BootstrapResult:
    """
    Bootstrap database with default configuration.
    
    This is the main entry point for database bootstrapping. It loads configuration
    from the defaults.yaml file and seeds the database with users and LLM models.
    
    Args:
        db: Database session
        config_path: Optional path to configuration file (defaults to env var or config/defaults.yaml)
    
    Returns:
        BootstrapResult with details of the operation
    """
    # Load configuration
    config_loader = BootstrapConfigLoader(config_path)
    
    if not config_loader.load():
        result = BootstrapResult(
            success=False,
            users_created=0,
            models_created=0,
            errors=["Could not load defaults configuration file"]
        )
        logger.warning("Could not load config/defaults.yaml, skipping bootstrap")
        return result
    
    # Validate configuration
    errors = config_loader.validate()
    if errors:
        result = BootstrapResult(
            success=False,
            users_created=0,
            models_created=0,
            errors=errors
        )
        logger.error(f"Configuration validation failed: {errors}")
        return result
    
    # Execute bootstrap
    bootstrapper = DatabaseBootstrapper(db, config_loader)
    result = bootstrapper.bootstrap()
    
    return result
