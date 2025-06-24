"""
Unified configuration system with validation
Single source of truth for all business rules and settings
"""
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, field
import json
import os


@dataclass
class FeeConfiguration:
    """All fee-related configuration"""
    service_fee_pct: float = 0.04  # 4% of car price
    cxa_pct: float = 0.04          # 4% marketing fee
    cac_bonus_min: float = 0.0     # Min CAC subsidy
    cac_bonus_max: float = 50000.0 # Max CAC subsidy
    cac_bonus_default: float = 0.0 # Default CAC amount
    kavak_total_enabled: bool = True
    kavak_total_amount: float = 25000.0
    gps_monthly: float = 350.0      # Before IVA
    gps_installation: float = 750.0  # Before IVA
    insurance_annual: float = 10999.0
    
    def validate(self):
        """Validate fee configuration"""
        assert 0 <= self.service_fee_pct <= 0.10, "Service fee must be 0-10%"
        assert 0 <= self.cxa_pct <= 0.10, "CXA fee must be 0-10%"
        assert self.cac_bonus_min <= self.cac_bonus_max, "CAC min must be <= max"
        assert self.gps_monthly >= 0, "GPS monthly must be non-negative"
        assert self.gps_installation >= 0, "GPS installation must be non-negative"
        assert self.insurance_annual >= 0, "Insurance must be non-negative"


@dataclass
class TierConfiguration:
    """Payment tier configuration"""
    refresh_min: float = -0.05      # -5%
    refresh_max: float = 0.05       # +5%
    upgrade_min: float = 0.05       # +5%
    upgrade_max: float = 0.25       # +25%
    max_upgrade_min: float = 0.25   # +25%
    max_upgrade_max: float = 1.0    # +100%
    
    def validate(self):
        """Validate tier boundaries"""
        assert self.refresh_min <= self.refresh_max, "Refresh min must be <= max"
        assert self.refresh_max <= self.upgrade_min, "Refresh must end where upgrade begins"
        assert self.upgrade_min <= self.upgrade_max, "Upgrade min must be <= max"
        assert self.upgrade_max <= self.max_upgrade_min, "Upgrade must end where max upgrade begins"
        assert self.max_upgrade_min <= self.max_upgrade_max, "Max upgrade min must be <= max"
    
    def get_tier_name(self, payment_delta: float) -> str:
        """Get tier name for a payment delta"""
        if self.refresh_min <= payment_delta <= self.refresh_max:
            return "refresh"
        elif self.upgrade_min <= payment_delta <= self.upgrade_max:
            return "upgrade"
        elif self.max_upgrade_min <= payment_delta <= self.max_upgrade_max:
            return "max_upgrade"
        else:
            return "out_of_range"


@dataclass
class BusinessRules:
    """Core business rules"""
    min_npv: float = 5000.0          # Minimum NPV required
    max_payment_increase: float = 1.0 # Max 100% payment increase
    available_terms: List[int] = field(default_factory=lambda: [60, 72, 48, 36, 24, 12])
    min_down_payment_pct: float = 0.10  # 10% minimum
    
    def validate(self):
        """Validate business rules"""
        assert self.min_npv >= 0, "Min NPV must be non-negative"
        assert 0 < self.max_payment_increase <= 2.0, "Max payment increase must be 0-200%"
        assert all(term in [12, 24, 36, 48, 60, 72] for term in self.available_terms), "Invalid terms"
        assert 0 <= self.min_down_payment_pct <= 0.5, "Min down payment must be 0-50%"


@dataclass
class UnifiedConfig:
    """Complete configuration container"""
    fees: FeeConfiguration = field(default_factory=FeeConfiguration)
    tiers: TierConfiguration = field(default_factory=TierConfiguration)
    rules: BusinessRules = field(default_factory=BusinessRules)
    
    # Risk profile data (loaded from config.py)
    interest_rates: Dict[str, Dict[str, float]] = field(default_factory=dict)
    risk_indices: Dict[str, int] = field(default_factory=dict)
    down_payment_table: List[List[float]] = field(default_factory=list)
    
    def validate(self):
        """Validate entire configuration"""
        self.fees.validate()
        self.tiers.validate()
        self.rules.validate()
    
    def save_to_file(self, filepath: str = "engine_config.json"):
        """Save configuration to JSON file"""
        config_dict = {
            # Fees
            'service_fee_pct': self.fees.service_fee_pct,
            'cxa_pct': self.fees.cxa_pct,
            'cac_bonus_min': self.fees.cac_bonus_min,
            'cac_bonus_max': self.fees.cac_bonus_max,
            'cac_bonus_default': self.fees.cac_bonus_default,
            'kavak_total_enabled': self.fees.kavak_total_enabled,
            'kavak_total_amount': self.fees.kavak_total_amount,
            'gps_monthly': self.fees.gps_monthly,
            'gps_installation': self.fees.gps_installation,
            'insurance_annual': self.fees.insurance_annual,
            # Tiers
            'refresh_min': self.tiers.refresh_min,
            'refresh_max': self.tiers.refresh_max,
            'upgrade_min': self.tiers.upgrade_min,
            'upgrade_max': self.tiers.upgrade_max,
            'max_upgrade_min': self.tiers.max_upgrade_min,
            'max_upgrade_max': self.tiers.max_upgrade_max,
            # Rules
            'min_npv': self.rules.min_npv,
            'max_payment_increase': self.rules.max_payment_increase,
            'available_terms': self.rules.available_terms,
            'min_down_payment_pct': self.rules.min_down_payment_pct
        }
        
        with open(filepath, 'w') as f:
            json.dump(config_dict, f, indent=2)
    
    @classmethod
    def load_from_file(cls, filepath: str = "engine_config.json") -> 'UnifiedConfig':
        """Load configuration from JSON file"""
        config = cls()
        
        if os.path.exists(filepath):
            with open(filepath, 'r') as f:
                data = json.load(f)
            
            # Load fees
            config.fees.service_fee_pct = data.get('service_fee_pct', config.fees.service_fee_pct)
            config.fees.cxa_pct = data.get('cxa_pct', config.fees.cxa_pct)
            config.fees.cac_bonus_min = data.get('cac_bonus_min', config.fees.cac_bonus_min)
            config.fees.cac_bonus_max = data.get('cac_bonus_max', config.fees.cac_bonus_max)
            config.fees.cac_bonus_default = data.get('cac_bonus_default', config.fees.cac_bonus_default)
            config.fees.kavak_total_enabled = data.get('kavak_total_enabled', config.fees.kavak_total_enabled)
            config.fees.kavak_total_amount = data.get('kavak_total_amount', config.fees.kavak_total_amount)
            config.fees.gps_monthly = data.get('gps_monthly', config.fees.gps_monthly)
            config.fees.gps_installation = data.get('gps_installation', config.fees.gps_installation)
            config.fees.insurance_annual = data.get('insurance_annual', config.fees.insurance_annual)
            
            # Load tiers
            config.tiers.refresh_min = data.get('refresh_min', config.tiers.refresh_min)
            config.tiers.refresh_max = data.get('refresh_max', config.tiers.refresh_max)
            config.tiers.upgrade_min = data.get('upgrade_min', config.tiers.upgrade_min)
            config.tiers.upgrade_max = data.get('upgrade_max', config.tiers.upgrade_max)
            config.tiers.max_upgrade_min = data.get('max_upgrade_min', config.tiers.max_upgrade_min)
            config.tiers.max_upgrade_max = data.get('max_upgrade_max', config.tiers.max_upgrade_max)
            
            # Load rules
            config.rules.min_npv = data.get('min_npv', config.rules.min_npv)
            config.rules.max_payment_increase = data.get('max_payment_increase', config.rules.max_payment_increase)
            config.rules.available_terms = data.get('available_terms', config.rules.available_terms)
            config.rules.min_down_payment_pct = data.get('min_down_payment_pct', config.rules.min_down_payment_pct)
        
        # Load interest rates and risk data from existing config
        from config.config import INTEREST_RATE_TABLE, RISK_PROFILE_INDICES, DOWN_PAYMENT_TABLE
        config.interest_rates = INTEREST_RATE_TABLE
        config.risk_indices = RISK_PROFILE_INDICES
        config.down_payment_table = DOWN_PAYMENT_TABLE
        
        config.validate()
        return config
    
    def get_interest_rate(self, risk_profile: str, term: int) -> Optional[float]:
        """Get interest rate for risk profile and term"""
        if risk_profile in self.interest_rates:
            return self.interest_rates[risk_profile].get(str(term))
        return None
    
    def get_risk_index(self, risk_profile: str) -> int:
        """Get risk index for profile name"""
        return self.risk_indices.get(risk_profile, 25)  # Default to highest risk
    
    def get_min_down_payment_pct(self, risk_index: int, term: int) -> float:
        """Get minimum down payment percentage for risk and term"""
        term_map = {12: 0, 24: 1, 36: 2, 48: 3, 60: 4, 72: 5}
        term_idx = term_map.get(term, 5)  # Default to longest term
        
        if 0 <= risk_index < len(self.down_payment_table):
            return self.down_payment_table[risk_index][term_idx]
        return 0.20  # Default 20% for unknown risk


# Global singleton instance
_config_instance: Optional[UnifiedConfig] = None


def get_config() -> UnifiedConfig:
    """Get the global configuration instance"""
    global _config_instance
    if _config_instance is None:
        _config_instance = UnifiedConfig.load_from_file()
    return _config_instance


def reload_config():
    """Reload configuration from file"""
    global _config_instance
    _config_instance = UnifiedConfig.load_from_file()
    return _config_instance