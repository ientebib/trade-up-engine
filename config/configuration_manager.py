"""
Comprehensive Configuration Management System
Handles all business logic parameters with graceful fallbacks and validation
"""
import os
import json
import logging
from typing import Dict, Any, Optional, List, Union
from decimal import Decimal
from datetime import datetime
from pathlib import Path
import threading
from dataclasses import dataclass, asdict
from enum import Enum

logger = logging.getLogger(__name__)


class ConfigSource(Enum):
    """Configuration source priorities"""
    DATABASE = 1      # Highest priority
    FILE = 2          # JSON/YAML files
    ENVIRONMENT = 3   # Environment variables
    DEFAULT = 4       # Hardcoded defaults


@dataclass
class ConfigValue:
    """Represents a configuration value with metadata"""
    key: str
    value: Any
    source: ConfigSource
    loaded_at: datetime
    validation_rules: Optional[Dict] = None
    description: Optional[str] = None


class ConfigurationManager:
    """
    Centralized configuration management with:
    - Multiple source support (DB, files, env, defaults)
    - Runtime updates without restart
    - Validation and type safety
    - Audit trail
    - Graceful fallbacks
    """
    
    def __init__(self):
        self._config: Dict[str, ConfigValue] = {}
        self._lock = threading.RLock()
        self._watchers: List[callable] = []
        self._audit_log: List[Dict] = []
        self._initialized = False
        
        # Configuration paths
        self.config_dir = Path("config")
        self.override_file = self.config_dir / "engine_config.json"
        self.base_config_file = self.config_dir / "base_config.json"
        
    def initialize(self):
        """Initialize configuration from all sources"""
        if self._initialized:
            return
            
        with self._lock:
            # Load in priority order
            self._load_defaults()
            self._load_environment()
            self._load_files()
            self._load_database()
            
            self._initialized = True
            logger.info(f"Configuration initialized with {len(self._config)} settings")
    
    def _load_defaults(self):
        """Load hardcoded defaults as last fallback"""
        defaults = {
            # Financial Parameters
            "financial.iva_rate": Decimal("0.16"),
            "financial.max_loan_amount": Decimal("10000000"),
            "financial.min_loan_amount": Decimal("0"),
            "financial.max_interest_rate": Decimal("1.0"),
            "financial.min_interest_rate": Decimal("0.0"),
            "financial.max_term_months": 120,
            "financial.min_term_months": 1,
            
            # GPS Fees
            "fees.gps.monthly": Decimal("350.0"),
            "fees.gps.installation": Decimal("750.0"),
            "fees.gps.apply_iva": True,
            
            # Insurance
            "fees.insurance.amount": Decimal("10999.0"),
            "fees.insurance.term_months": 12,
            "fees.insurance.renewal_cycle": 12,
            
            # Service Fees
            "fees.service.percentage": Decimal("0.04"),
            "fees.cxa.percentage": Decimal("0.04"),
            "fees.kavak_total.amount": Decimal("25000.0"),
            "fees.kavak_total.cycle_months": 24,
            
            # CAC Bonus
            "fees.cac_bonus.min": Decimal("0"),
            "fees.cac_bonus.max": Decimal("5000.0"),
            "fees.cac_bonus.default": Decimal("0"),
            
            # Payment Tiers
            "tiers.refresh.min": Decimal("-0.05"),
            "tiers.refresh.max": Decimal("0.05"),
            "tiers.upgrade.min": Decimal("0.05"),
            "tiers.upgrade.max": Decimal("0.25"),
            "tiers.max_upgrade.min": Decimal("0.25"),
            "tiers.max_upgrade.max": Decimal("1.0"),
            
            # Term Search
            "terms.search_order": [60, 72, 48, 36, 24, 12],
            "terms.priority": "default",  # default, ascending, descending
            
            # Interest Rates by Profile
            "rates.AAA": Decimal("0.1949"),
            "rates.AA": Decimal("0.1949"),
            "rates.A": Decimal("0.1949"),
            "rates.A1": Decimal("0.1949"),
            "rates.A2": Decimal("0.2099"),
            "rates.B": Decimal("0.2249"),
            "rates.C1": Decimal("0.2299"),
            "rates.C2": Decimal("0.2349"),
            "rates.C3": Decimal("0.2549"),
            "rates.D1": Decimal("0.2949"),
            "rates.D2": Decimal("0.3249"),
            "rates.D3": Decimal("0.3249"),
            "rates.E1": Decimal("0.2399"),
            "rates.E2": Decimal("0.31"),
            "rates.E3": Decimal("0.3399"),
            "rates.E4": Decimal("0.3649"),
            "rates.E5": Decimal("0.4399"),
            "rates.F1": Decimal("0.3649"),
            "rates.F2": Decimal("0.3899"),
            "rates.F3": Decimal("0.4149"),
            "rates.F4": Decimal("0.4399"),
            "rates.B_SB": Decimal("0.2349"),
            "rates.C1_SB": Decimal("0.2449"),
            "rates.C2_SB": Decimal("0.27"),
            "rates.E5_SB": Decimal("0.4399"),
            "rates.Z": Decimal("0.4399"),
            
            # Down Payment Matrix (profile_index.term)
            "downpayment.0.12": Decimal("0.3"),
            "downpayment.0.24": Decimal("0.3"),
            "downpayment.0.36": Decimal("0.3"),
            "downpayment.0.48": Decimal("0.3"),
            "downpayment.0.60": Decimal("0.3"),
            "downpayment.0.72": Decimal("0.3"),
            "downpayment.1.12": Decimal("0.25"),
            "downpayment.1.24": Decimal("0.25"),
            # ... (truncated for brevity, but would include all values)
            
            # System Settings
            "system.max_concurrent_requests": 3,
            "system.request_timeout_seconds": 300,
            "system.cache_ttl_hours": 4.0,
            "system.max_customers_per_bulk": 50,
            
            # Feature Flags
            "features.enable_caching": True,
            "features.enable_audit_logging": True,
            "features.enable_decimal_precision": True,
            "features.enable_payment_validation": True,
        }
        
        for key, value in defaults.items():
            self._set_config(
                key=key,
                value=value,
                source=ConfigSource.DEFAULT,
                description=f"Default value for {key}"
            )
    
    def _load_environment(self):
        """Load configuration from environment variables"""
        # Map environment variables to config keys
        env_mapping = {
            "KAVAK_IVA_RATE": "financial.iva_rate",
            "KAVAK_GPS_MONTHLY": "fees.gps.monthly",
            "KAVAK_GPS_INSTALLATION": "fees.gps.installation",
            "KAVAK_INSURANCE_AMOUNT": "fees.insurance.amount",
            "KAVAK_SERVICE_FEE_PCT": "fees.service.percentage",
            "KAVAK_CXA_PCT": "fees.cxa.percentage",
            "KAVAK_TOTAL_AMOUNT": "fees.kavak_total.amount",
            "KAVAK_CAC_BONUS_MAX": "fees.cac_bonus.max",
            "KAVAK_CACHE_TTL_HOURS": "system.cache_ttl_hours",
            "KAVAK_ENABLE_CACHING": "features.enable_caching",
        }
        
        for env_var, config_key in env_mapping.items():
            value = os.getenv(env_var)
            if value is not None:
                try:
                    # Convert to appropriate type
                    parsed_value = self._parse_value(config_key, value)
                    self._set_config(
                        key=config_key,
                        value=parsed_value,
                        source=ConfigSource.ENVIRONMENT,
                        description=f"Loaded from environment variable {env_var}"
                    )
                except Exception as e:
                    logger.warning(f"Failed to parse env var {env_var}: {e}")
    
    def _load_files(self):
        """Load configuration from JSON files"""
        # Load base configuration
        if self.base_config_file.exists():
            try:
                with open(self.base_config_file) as f:
                    base_config = json.load(f)
                    self._process_config_dict(base_config, ConfigSource.FILE)
            except Exception as e:
                logger.error(f"Failed to load base config: {e}")
        
        # Load override configuration
        if self.override_file.exists():
            try:
                with open(self.override_file) as f:
                    override_config = json.load(f)
                    self._process_config_dict(override_config, ConfigSource.FILE)
            except Exception as e:
                logger.error(f"Failed to load override config: {e}")
    
    def _load_database(self):
        """Load configuration from database (if available)"""
        try:
            # This would connect to a configuration database
            # For now, we'll simulate with a file
            db_config_file = self.config_dir / "database_config.json"
            if db_config_file.exists():
                with open(db_config_file) as f:
                    db_config = json.load(f)
                    self._process_config_dict(db_config, ConfigSource.DATABASE)
        except Exception as e:
            logger.debug(f"Database config not available: {e}")
    
    def _process_config_dict(self, config_dict: Dict, source: ConfigSource):
        """Process a configuration dictionary"""
        def flatten_dict(d: Dict, parent_key: str = '') -> Dict:
            items = []
            for k, v in d.items():
                new_key = f"{parent_key}.{k}" if parent_key else k
                if isinstance(v, dict) and not isinstance(v, ConfigValue):
                    items.extend(flatten_dict(v, new_key).items())
                else:
                    items.append((new_key, v))
            return dict(items)
        
        flat_config = flatten_dict(config_dict)
        for key, value in flat_config.items():
            self._set_config(
                key=key,
                value=self._parse_value(key, value),
                source=source
            )
    
    def _parse_value(self, key: str, value: Any) -> Any:
        """Parse and validate configuration value"""
        # Determine expected type based on key pattern
        if any(k in key for k in ["rate", "percentage", "amount", "fee", "bonus", "min", "max"]):
            if isinstance(value, str):
                return Decimal(value)
            elif isinstance(value, (int, float)):
                return Decimal(str(value))
        elif any(k in key for k in ["months", "seconds", "count", "max_"]):
            return int(value)
        elif key.startswith("features.") or key.endswith(".enabled"):
            if isinstance(value, str):
                return value.lower() in ('true', '1', 'yes', 'on')
            return bool(value)
        elif key.endswith("search_order") and isinstance(value, str):
            return json.loads(value)
        
        return value
    
    def _set_config(self, key: str, value: Any, source: ConfigSource, 
                   description: Optional[str] = None):
        """Set a configuration value"""
        with self._lock:
            old_value = self._config.get(key)
            
            # Only update if new source has higher priority
            if old_value and old_value.source.value < source.value:
                return
            
            self._config[key] = ConfigValue(
                key=key,
                value=value,
                source=source,
                loaded_at=datetime.now(),
                description=description
            )
            
            # Log the change
            self._audit_log.append({
                "timestamp": datetime.now().isoformat(),
                "key": key,
                "old_value": old_value.value if old_value else None,
                "new_value": value,
                "source": source.name
            })
            
            # Notify watchers
            for watcher in self._watchers:
                try:
                    watcher(key, value, old_value.value if old_value else None)
                except Exception as e:
                    logger.error(f"Watcher error: {e}")
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value"""
        if not self._initialized:
            self.initialize()
            
        with self._lock:
            config_value = self._config.get(key)
            if config_value:
                return config_value.value
            return default
    
    def get_decimal(self, key: str, default: Decimal = Decimal("0")) -> Decimal:
        """Get a configuration value as Decimal"""
        value = self.get(key, default)
        if isinstance(value, Decimal):
            return value
        return Decimal(str(value))
    
    def get_int(self, key: str, default: int = 0) -> int:
        """Get a configuration value as integer"""
        return int(self.get(key, default))
    
    def get_bool(self, key: str, default: bool = False) -> bool:
        """Get a configuration value as boolean"""
        return bool(self.get(key, default))
    
    def get_list(self, key: str, default: Optional[List] = None) -> List:
        """Get a configuration value as list"""
        value = self.get(key, default or [])
        if isinstance(value, list):
            return value
        return list(value)
    
    def set(self, key: str, value: Any, persist: bool = True):
        """Set a configuration value at runtime"""
        parsed_value = self._parse_value(key, value)
        self._set_config(key, parsed_value, ConfigSource.FILE)
        
        if persist:
            self._persist_override(key, parsed_value)
    
    def _persist_override(self, key: str, value: Any):
        """Persist an override to the override file"""
        try:
            # Load existing overrides
            overrides = {}
            if self.override_file.exists():
                with open(self.override_file) as f:
                    overrides = json.load(f)
            
            # Update with new value
            parts = key.split('.')
            current = overrides
            for part in parts[:-1]:
                if part not in current:
                    current[part] = {}
                current = current[part]
            
            # Convert Decimal to string for JSON
            if isinstance(value, Decimal):
                value = str(value)
            
            current[parts[-1]] = value
            
            # Save back
            with open(self.override_file, 'w') as f:
                json.dump(overrides, f, indent=2)
                
        except Exception as e:
            logger.error(f"Failed to persist override: {e}")
    
    def reload(self):
        """Reload configuration from all sources"""
        with self._lock:
            old_config = self._config.copy()
            self._config.clear()
            self._initialized = False
            self.initialize()
            
            # Notify watchers of changes
            for key, new_value in self._config.items():
                old_value = old_config.get(key)
                if not old_value or old_value.value != new_value.value:
                    for watcher in self._watchers:
                        try:
                            watcher(key, new_value.value, old_value.value if old_value else None)
                        except Exception as e:
                            logger.error(f"Watcher error: {e}")
    
    def watch(self, callback: callable):
        """Register a configuration change watcher"""
        self._watchers.append(callback)
    
    def get_all(self) -> Dict[str, Any]:
        """Get all configuration values"""
        with self._lock:
            return {k: v.value for k, v in self._config.items()}
    
    def get_by_prefix(self, prefix: str) -> Dict[str, Any]:
        """Get all configuration values with a given prefix"""
        with self._lock:
            return {
                k: v.value 
                for k, v in self._config.items() 
                if k.startswith(prefix)
            }
    
    def get_audit_log(self, limit: int = 100) -> List[Dict]:
        """Get recent audit log entries"""
        with self._lock:
            return self._audit_log[-limit:]
    
    def export_config(self, source_filter: Optional[ConfigSource] = None) -> Dict:
        """Export configuration for backup or migration"""
        with self._lock:
            export_data = {
                "exported_at": datetime.now().isoformat(),
                "config_count": len(self._config),
                "configuration": {}
            }
            
            for key, config_value in self._config.items():
                if source_filter and config_value.source != source_filter:
                    continue
                    
                export_data["configuration"][key] = {
                    "value": str(config_value.value) if isinstance(config_value.value, Decimal) else config_value.value,
                    "source": config_value.source.name,
                    "loaded_at": config_value.loaded_at.isoformat(),
                    "description": config_value.description
                }
            
            return export_data
    
    def validate_config(self) -> List[str]:
        """Validate configuration consistency"""
        errors = []
        
        # Check required keys
        required_keys = [
            "financial.iva_rate",
            "fees.gps.monthly",
            "fees.gps.installation",
            "fees.insurance.amount"
        ]
        
        for key in required_keys:
            if key not in self._config:
                errors.append(f"Missing required configuration: {key}")
        
        # Validate ranges
        validations = [
            ("financial.iva_rate", 0, 1),
            ("fees.service.percentage", 0, 1),
            ("fees.cxa.percentage", 0, 1),
            ("tiers.refresh.min", -1, 0),
            ("tiers.refresh.max", 0, 1),
        ]
        
        for key, min_val, max_val in validations:
            value = self.get_decimal(key)
            if value and (value < min_val or value > max_val):
                errors.append(f"{key} value {value} outside valid range [{min_val}, {max_val}]")
        
        return errors


# Singleton instance
_config_manager: Optional[ConfigurationManager] = None
_config_lock = threading.Lock()


def get_config() -> ConfigurationManager:
    """Get or create the global configuration manager"""
    global _config_manager
    
    if _config_manager is None:
        with _config_lock:
            if _config_manager is None:
                _config_manager = ConfigurationManager()
                _config_manager.initialize()
    
    return _config_manager


# Convenience functions
def get_config_value(key: str, default: Any = None) -> Any:
    """Get a configuration value"""
    return get_config().get(key, default)


def get_gps_fees() -> Dict[str, Decimal]:
    """Get GPS fee configuration"""
    config = get_config()
    return {
        "monthly": config.get_decimal("fees.gps.monthly"),
        "installation": config.get_decimal("fees.gps.installation"),
        "apply_iva": config.get_bool("fees.gps.apply_iva", True)
    }


def get_payment_tiers() -> Dict[str, tuple]:
    """Get payment tier configuration"""
    config = get_config()
    return {
        "refresh": (
            float(config.get_decimal("tiers.refresh.min")),
            float(config.get_decimal("tiers.refresh.max"))
        ),
        "upgrade": (
            float(config.get_decimal("tiers.upgrade.min")),
            float(config.get_decimal("tiers.upgrade.max"))
        ),
        "max_upgrade": (
            float(config.get_decimal("tiers.max_upgrade.min")),
            float(config.get_decimal("tiers.max_upgrade.max"))
        ),
    }


def get_interest_rate(risk_profile: str) -> Decimal:
    """Get interest rate for a risk profile"""
    config = get_config()
    return config.get_decimal(f"rates.{risk_profile}", Decimal("0.4399"))  # Default to highest rate


def get_down_payment(profile_index: int, term: int) -> Decimal:
    """Get down payment percentage for profile and term"""
    config = get_config()
    return config.get_decimal(f"downpayment.{profile_index}.{term}", Decimal("0.3"))  # Default 30%