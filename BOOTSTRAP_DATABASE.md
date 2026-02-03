# Database Bootstrapping Implementation Plan

## Overview

This document outlines the implementation of an automatic database bootstrapping system that initializes the application with default configuration from `config/defaults.yaml` when the database is empty.

### Goals

1. Automatically seed the database with default users and LLM model configurations on first startup
2. Ensure idempotent operation (can be safely run multiple times)
3. Maintain data integrity by only populating empty tables
4. Provide clear logging for troubleshooting
5. Support secure password handling using existing encryption infrastructure

## Current State

### Existing Configuration File

`config/defaults.yaml` contains:
- **users**: Default account(s) with email, password, name, and roles
- **providers**: LLM model configurations for multiple providers (ollama, openai, deepinfra)

### Current Database Initialization

Located in `api/models/database.py`:
- Creates database connection
- Enables pgvector extension
- Creates all tables via SQLAlchemy `Base.metadata.create_all()`
- **Missing**: No default data seeding

### Application Startup

Located in `api/main.py`:
- `lifespan()` function calls `init_database()` during FastAPI startup
- No bootstrapping logic implemented

## Proposed Architecture

```
config/
  ├── defaults.yaml          # Actual defaults (not committed to git)
  └── example.defaults.yaml  # Template for version control

api/models/
  ├── database.py            # Enhanced with bootstrap_database()
  └── bootstrap.py           # NEW: Bootstrapping logic

api/util/
  └── bootstrap_config.py    # NEW: YAML loading and validation
```

### Component Responsibilities

| Component | Responsibility |
|-----------|---------------|
| `bootstrap_config.py` | Load and validate `config/defaults.yaml`, convert to domain objects |
| `bootstrap.py` | Execute database seeding with idempotency checks |
| `database.py` | Call bootstrapping after table creation |
| `main.py` | No changes needed (calls init_database) |

## Implementation Details

### Phase 1: Configuration Loading (`api/util/bootstrap_config.py`)

Create a new utility module for loading and validating the defaults configuration:

```python
class BootstrapConfigLoader:
    """Loads and validates config/defaults.yaml"""
    
    def __init__(self, config_path: str = "config/defaults.yaml"):
        self.config_path = config_path
        self.config = None
    
    def load(self) -> dict:
        """Load YAML configuration from file"""
        
    def validate(self) -> List[str]:
        """Validate configuration structure, return list of errors"""
        
    def get_users(self) -> List[UserConfig]:
        """Extract and validate user configurations"""
        
    def get_models(self) -> List[ModelConfig]:
        """Extract and validate LLM model configurations"""

@dataclass
class UserConfig:
    email: str
    password: str
    name: str
    roles: List[str]

@dataclass  
class ModelConfig:
    provider: str
    model: str
    name: str
    temperature: float
    max_tokens: int
    timeout: int
```

**Validation Rules:**
- Required fields for users: email, password, name
- Email must be valid format
- Password must not be empty
- Model configs must have valid provider (ollama, openai, deepinfra)
- Temperature must be between 0 and 2
- Max tokens must be positive integer

### Phase 2: Database Bootstrapping (`api/models/bootstrap.py`)

Create the core bootstrapping logic with idempotent operations:

```python
class DatabaseBootstrapper:
    """Handles seeding database with default configuration"""
    
    def __init__(self, db: Session, config_loader: BootstrapConfigLoader):
        self.db = db
        self.config = config_loader
    
    def bootstrap(self) -> BootstrapResult:
        """Main entry point - executes all bootstrapping steps"""
        
    def _is_bootstrapped(self) -> bool:
        """Check if database has already been bootstrapped"""
        # Option 1: Check if accounts table has records
        # Option 2: Create a bootstrap_metadata table with timestamp
        
    def _seed_users(self) -> int:
        """Seed default users if accounts table is empty"""
        # Check existing users by email to avoid duplicates
        # Encrypt passwords using PasswordSecurity
        # Create Account records
        
    def _seed_models(self, account_id: int) -> int:
        """Seed LLM models for specified account if llm_models table is empty"""
        # Check existing models by (account_id, provider, model_identifier)
        # Create LLMModel records
        
    def _record_bootstrap_metadata(self) -> None:
        """Record that bootstrapping was completed"""
        # Create or update bootstrap_metadata table

@dataclass
class BootstrapResult:
    success: bool
    users_created: int
    models_created: int
    errors: List[str]
```

**Idempotency Strategy:**
- Users: Check by email before creating
- LLM Models: Check by (account_id, provider, model_identifier) before creating
- Use database transactions - rollback on any failure
- Only bootstrap if tables are empty OR explicitly requested

### Phase 3: Database Integration (`api/models/database.py`)

Enhance existing database initialization:

```python
def init_database(...):
    # Existing code
    ...
    Base.metadata.create_all(bind=engine)
    
    # NEW: Bootstrap default configuration
    from .bootstrap import bootstrap_database
    bootstrap_database(engine)

def bootstrap_database(engine) -> BootstrapResult:
    """Bootstrap database with default configuration"""
    from api.util.bootstrap_config import BootstrapConfigLoader
    from api.models.bootstrap import DatabaseBootstrapper
    
    with Session(engine) as db:
        # Load configuration
        config_loader = BootstrapConfigLoader()
        if not config_loader.load():
            logger.warning("Could not load config/defaults.yaml, skipping bootstrap")
            return BootstrapResult(success=False, ...)
        
        # Validate configuration
        errors = config_loader.validate()
        if errors:
            logger.error(f"Configuration validation failed: {errors}")
            return BootstrapResult(success=False, ...)
        
        # Execute bootstrap
        bootstrapper = DatabaseBootstrapper(db, config_loader)
        result = bootstrapper.bootstrap()
        
        logger.info(f"Database bootstrap completed: {result}")
        return result
```

### Phase 4: Password Encryption Integration

Use existing password security infrastructure:

```python
from api.util.password_security import PasswordSecurity

def _create_user(self, user_config: UserConfig) -> Account:
    """Create Account with encrypted password"""
    # Generate unique salt
    salt = str(uuid.uuid4())
    
    # Get PASSWORD_SECRET from environment
    password_secret = os.getenv("PASSWORD_SECRET")
    if not password_secret:
        raise ValueError("PASSWORD_SECRET must be set for bootstrapping")
    
    # Encrypt password
    security = PasswordSecurity(password_secret, salt)
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
```

### Phase 5: Environment Variables

Add to `.env.example`:

```bash
# -----------------------------------------------------------------------------
# Database Bootstrapping Configuration
# -----------------------------------------------------------------------------
# Path to defaults configuration file
DEFAULTS_CONFIG_PATH=config/defaults.yaml

# Force bootstrapping even if data exists (development only)
# WARNING: May create duplicate records if users/models already exist
# FORCE_BOOTSTRAP=false

# Password secret for encrypting default user passwords (required)
# MUST be set before first startup for bootstrapping to work
PASSWORD_SECRET=your-secure-random-password-secret-minimum-32-chars
```

## File Structure

### New Files

```
api/util/bootstrap_config.py     # Configuration loading and validation
api/models/bootstrap.py           # Database bootstrapping logic
BOOTSTRAP_DATABASE.md            # This document
```

### Modified Files

```
api/models/database.py           # Add bootstrap_database() call
config/.gitignore                # Ignore actual defaults.yaml (add to existing)
.env.example                     # Add bootstrapping environment variables
README.md                        # Document bootstrapping feature
```

### Config Directory

```
config/
  ├── defaults.yaml              # Actual defaults (NOT in git - contains credentials)
  ├── example.defaults.yaml      # Template (in git)
  └── .gitignore                 # Ensure defaults.yaml is ignored
```

## Implementation Steps

### Step 1: Configuration Loader (1-2 hours)

1. Create `api/util/bootstrap_config.py`
2. Implement `BootstrapConfigLoader` class
3. Implement `UserConfig` and `ModelConfig` dataclasses
4. Add YAML parsing with PyYAML
5. Implement validation logic
6. Write unit tests for configuration loading

### Step 2: Bootstrapping Logic (2-3 hours)

1. Create `api/models/bootstrap.py`
2. Implement `DatabaseBootstrapper` class
3. Implement user seeding with password encryption
4. Implement LLM model seeding
5. Add idempotency checks
6. Implement transaction handling with rollback
7. Add comprehensive logging

### Step 3: Database Integration (30 minutes)

1. Modify `api/models/database.py`
2. Add `bootstrap_database()` function
3. Call bootstrap after table creation
4. Add error handling for missing config

### Step 4: Configuration Setup (30 minutes)

1. Update `.env.example` with new variables
2. Ensure `config/defaults.yaml` is in `.gitignore`
3. Verify `example.defaults.yaml` has all required fields

### Step 5: Documentation (1 hour)

1. Update `README.md` with bootstrapping section
2. Document environment variables
3. Add troubleshooting section
4. Document configuration file format

### Step 6: Testing (2-3 hours)

1. Test fresh database startup
2. Test idempotency (run multiple times)
3. Test with missing configuration file
4. Test with invalid configuration
5. Test with missing PASSWORD_SECRET
6. Test password encryption/decryption
7. Verify LLM models appear in Model Manager

## Testing Strategy

### Unit Tests

- `test_bootstrap_config_loader.py`: Configuration loading and validation
- `test_password_security.py`: Password encryption for bootstrapping
- `test_database_bootstrapper.py`: Core bootstrapping logic

### Integration Tests

- Fresh database: Verify all defaults are created
- Partial database: Verify only missing entities are created
- Existing data: Verify no duplicates created
- Invalid config: Verify graceful failure with helpful error messages

### Manual Testing Checklist

- [ ] Start with empty database → defaults loaded
- [ ] Restart application → no duplicate data
- [ ] Delete all accounts → only users re-created
- [ ] Delete all models → only models re-created
- [ ] Missing defaults.yaml → application starts, warning logged
- [ ] Invalid YAML → application starts, error logged
- [ ] Missing PASSWORD_SECRET → application starts, error logged
- [ ] Login with default user → success
- [ ] Default models visible in Model Manager → success

## Security Considerations

1. **Password Encryption**: All default passwords must be encrypted using existing PasswordSecurity
2. **Secrets Management**: 
   - `config/defaults.yaml` must be in `.gitignore`
   - Never commit actual defaults with credentials
   - Use `example.defaults.yaml` for template
3. **Environment Variables**: `PASSWORD_SECRET` must be set for bootstrapping
4. **Logging**: Never log passwords or sensitive data
5. **Force Bootstrap**: Should only be available in development mode

## Error Handling

### Graceful Degradation

The application should **always start**, even if bootstrapping fails:

| Failure Scenario | Behavior |
|------------------|----------|
| Missing config file | Log warning, continue without bootstrapping |
| Invalid YAML | Log error with details, continue without bootstrapping |
| Missing PASSWORD_SECRET | Log error, continue without bootstrapping |
| Validation errors | Log all validation errors, continue without bootstrapping |
| Database constraint violation | Log error, rollback transaction, continue |
| Permission errors | Log error, continue without bootstrapping |

### Logging Strategy

```python
logger.info("Starting database bootstrapping...")
logger.info(f"Loaded configuration from {config_path}")
logger.info(f"Configuration validated successfully")
logger.info(f"Creating {len(users)} default users...")
logger.info(f"Created user: {email}")
logger.info(f"Creating {len(models)} LLM models for account {account_id}...")
logger.info(f"Bootstrapping completed: {users_created} users, {models_created} models created")

# Errors
logger.warning(f"Could not load config/defaults.yaml: {error}")
logger.error(f"Configuration validation failed: {errors}")
logger.error(f"Bootstrapping failed for user {email}: {error}")
```

## Migration Path

### Existing Deployments

For existing databases with data:

1. Bootstrapping detects existing users → skips user creation
2. Bootstrapping detects existing models → skips model creation
3. No impact on existing data
4. Safe to deploy without additional steps

### New Deployments

1. Set `PASSWORD_SECRET` environment variable
2. Ensure `config/defaults.yaml` exists with desired defaults
3. Start application
4. Defaults automatically loaded
5. Log in with default user credentials

## Rollback Plan

If issues arise:

1. Disable bootstrapping by renaming `config/defaults.yaml`
2. Clear bootstrap metadata (if implemented): `DELETE FROM bootstrap_metadata`
3. Manually delete seeded records if needed
4. Restart application

## Future Enhancements

### Potential Improvements

1. **Bootstrap Metadata Table**: Track when/what was bootstrapped
2. **Config Versioning**: Support configuration schema versions
3. **Partial Bootstrap**: Allow selective seeding (users only, models only)
4. **Update Mode**: Update existing defaults instead of skipping
5. **Multiple Environment Support**: `config/defaults.dev.yaml`, `config/defaults.prod.yaml`
6. **Validation Mode**: `--validate-config` flag to check config without running
7. **Dry Run Mode**: Show what would be created without creating it

## Questions for Review

1. **Bootstrap Detection**: Should we use a dedicated `bootstrap_metadata` table or simply check for existing records?
   - *Recommendation*: Use metadata table for cleaner tracking

2. **Force Bootstrap**: Should we support `FORCE_BOOTSTRAP=true` for development?
   - *Recommendation*: Yes, but only in development mode

3. **Configuration Path**: Should the path be configurable via environment variable?
   - *Recommendation*: Yes, use `DEFAULTS_CONFIG_PATH` env var

4. **Multiple Accounts**: Should defaults support multiple accounts?
   - *Recommendation*: Yes, current config already supports multiple users

5. **Role Assignment**: Should the system respect custom roles from config, or enforce standard roles?
   - *Recommendation*: Allow custom roles from config but validate against allowed roles

6. **Password Updates**: If a default user already exists with different password, should we update it?
   - *Recommendation*: No, skip existing users to avoid breaking changes

## Estimated Effort

| Task | Time |
|------|------|
| Phase 1: Configuration Loader | 1-2 hours |
| Phase 2: Bootstrapping Logic | 2-3 hours |
| Phase 3: Database Integration | 30 minutes |
| Phase 4: Configuration Setup | 30 minutes |
| Phase 5: Documentation | 1 hour |
| Phase 6: Testing | 2-3 hours |
| **Total** | **7-10 hours** |
