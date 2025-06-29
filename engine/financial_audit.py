"""
Financial Calculation Audit Trail System
Logs all financial calculations for compliance and debugging
"""
import json
import logging
import threading
from threading import Timer
from typing import Dict, Any, Optional, List
from datetime import datetime
from decimal import Decimal
from pathlib import Path
import uuid
from dataclasses import dataclass, asdict
from enum import Enum

logger = logging.getLogger(__name__)


class CalculationType(Enum):
    """Types of financial calculations"""
    PAYMENT_COMPONENT = "payment_component"
    MONTHLY_PAYMENT = "monthly_payment"
    NPV = "npv"
    AMORTIZATION = "amortization"
    INTEREST = "interest"
    PRINCIPAL = "principal"
    FEES = "fees"


@dataclass
class AuditEntry:
    """Represents a single audit log entry"""
    audit_id: str
    timestamp: datetime
    calculation_type: CalculationType
    customer_id: Optional[str]
    request_id: Optional[str]
    inputs: Dict[str, Any]
    outputs: Dict[str, Any]
    metadata: Dict[str, Any]
    errors: Optional[List[str]] = None
    warnings: Optional[List[str]] = None


class FinancialAuditLogger:
    """
    Comprehensive audit logging for financial calculations
    
    Features:
    - Thread-safe logging
    - Structured JSON format
    - Automatic serialization of Decimal values
    - Rotating file logs
    - Optional database logging
    - Query capabilities
    """
    
    def __init__(self, log_dir: str = "logs/financial_audit", 
                 max_file_size_mb: int = 100,
                 max_entries_per_file: int = 10000,
                 retention_days: int = 30):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        self._lock = threading.Lock()
        self._current_log_file = None
        self._entries_count = 0
        self._max_entries_per_file = max_entries_per_file
        self._max_file_size_bytes = max_file_size_mb * 1024 * 1024
        self._retention_days = retention_days
        
        # Initialize audit logger
        self.audit_logger = self._setup_audit_logger()
        
        # In-memory buffer for recent entries
        self._recent_entries = []
        self._max_recent_entries = 1000
        
        # Clean up old logs on initialization
        self._cleanup_old_logs()
        
    def _setup_audit_logger(self) -> logging.Logger:
        """Set up dedicated audit logger"""
        audit_logger = logging.getLogger("financial_audit")
        audit_logger.setLevel(logging.INFO)
        audit_logger.propagate = False
        
        # Remove existing handlers
        audit_logger.handlers.clear()
        
        # Create file handler
        log_file = self._get_current_log_file()
        handler = logging.FileHandler(log_file)
        handler.setLevel(logging.INFO)
        
        # JSON formatter
        formatter = logging.Formatter('%(message)s')
        handler.setFormatter(formatter)
        
        audit_logger.addHandler(handler)
        
        return audit_logger
    
    def _get_current_log_file(self) -> Path:
        """Get current log file path with size and line count checks"""
        now = datetime.now()
        date_str = now.strftime("%Y%m%d")
        
        # Create date-based folder structure: logs/financial_audit/2025/06/27/
        year_month_day = self.log_dir / now.strftime("%Y/%m/%d")
        year_month_day.mkdir(parents=True, exist_ok=True)
        
        file_index = 1
        
        while True:
            log_file = year_month_day / f"audit_{file_index:04d}.jsonl"
            
            if not log_file.exists():
                return log_file
                
            # Check both size and line count
            file_size = log_file.stat().st_size
            line_count = self._count_lines(log_file)
            
            if file_size < self._max_file_size_bytes and line_count < self._max_entries_per_file:
                return log_file
                
            file_index += 1
    
    def _count_lines(self, file_path: Path) -> int:
        """Count lines in a file"""
        try:
            with open(file_path) as f:
                return sum(1 for _ in f)
        except:
            return 0
    
    def _serialize_value(self, value: Any) -> Any:
        """Serialize values for JSON storage"""
        if isinstance(value, Decimal):
            return str(value)
        elif isinstance(value, datetime):
            return value.isoformat()
        elif isinstance(value, dict):
            return {k: self._serialize_value(v) for k, v in value.items()}
        elif isinstance(value, list):
            return [self._serialize_value(v) for v in value]
        elif hasattr(value, '__dict__'):
            return self._serialize_value(value.__dict__)
        return value
    
    def log_calculation(
        self,
        calculation_type: CalculationType,
        inputs: Dict[str, Any],
        outputs: Dict[str, Any],
        customer_id: Optional[str] = None,
        request_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        errors: Optional[List[str]] = None,
        warnings: Optional[List[str]] = None
    ) -> str:
        """
        Log a financial calculation
        
        Args:
            calculation_type: Type of calculation
            inputs: Input parameters
            outputs: Calculation results
            customer_id: Optional customer identifier
            request_id: Optional request identifier
            metadata: Additional context
            errors: Any errors encountered
            warnings: Any warnings generated
            
        Returns:
            Audit ID for this entry
        """
        audit_id = str(uuid.uuid4())
        
        entry = AuditEntry(
            audit_id=audit_id,
            timestamp=datetime.now(),
            calculation_type=calculation_type,
            customer_id=customer_id,
            request_id=request_id,
            inputs=self._serialize_value(inputs),
            outputs=self._serialize_value(outputs),
            metadata=self._serialize_value(metadata or {}),
            errors=errors,
            warnings=warnings
        )
        
        with self._lock:
            # Check if rotation is needed before logging
            self.rotate_log_if_needed()
            
            # Log to file
            self._log_entry(entry)
            
            # Add to recent entries buffer
            self._recent_entries.append(entry)
            if len(self._recent_entries) > self._max_recent_entries:
                self._recent_entries.pop(0)
            
            # Increment counter
            self._entries_count += 1
        
        return audit_id
    
    def _log_entry(self, entry: AuditEntry):
        """Log entry to file"""
        entry_dict = asdict(entry)
        entry_dict['calculation_type'] = entry.calculation_type.value
        entry_dict['timestamp'] = entry.timestamp.isoformat()
        
        json_line = json.dumps(entry_dict, ensure_ascii=False)
        self.audit_logger.info(json_line)
    
    
    def log_payment_calculation(
        self,
        loan_amount: Decimal,
        interest_rate: Decimal,
        term_months: int,
        fees: Dict[str, Decimal],
        monthly_payment: Decimal,
        customer_id: Optional[str] = None,
        **kwargs
    ) -> str:
        """Convenience method for logging payment calculations"""
        inputs = {
            "loan_amount": loan_amount,
            "interest_rate": interest_rate,
            "term_months": term_months,
            "fees": fees,
            **kwargs
        }
        
        outputs = {
            "monthly_payment": monthly_payment,
            "total_payment": monthly_payment * term_months,
            "total_interest": (monthly_payment * term_months) - loan_amount
        }
        
        return self.log_calculation(
            calculation_type=CalculationType.MONTHLY_PAYMENT,
            inputs=inputs,
            outputs=outputs,
            customer_id=customer_id
        )
    
    def log_npv_calculation(
        self,
        loan_amount: Decimal,
        interest_rate: Decimal,
        term_months: int,
        npv: Decimal,
        customer_id: Optional[str] = None,
        **kwargs
    ) -> str:
        """Convenience method for logging NPV calculations"""
        inputs = {
            "loan_amount": loan_amount,
            "interest_rate": interest_rate,
            "term_months": term_months,
            **kwargs
        }
        
        outputs = {
            "npv": npv,
            "irr": kwargs.get("irr"),
            "payback_months": kwargs.get("payback_months")
        }
        
        return self.log_calculation(
            calculation_type=CalculationType.NPV,
            inputs=inputs,
            outputs=outputs,
            customer_id=customer_id
        )
    
    def get_recent_entries(self, limit: int = 100) -> List[Dict]:
        """Get recent audit entries"""
        with self._lock:
            entries = self._recent_entries[-limit:]
            return [asdict(e) for e in entries]
    
    def search_entries(
        self,
        customer_id: Optional[str] = None,
        calculation_type: Optional[CalculationType] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        audit_id: Optional[str] = None
    ) -> List[Dict]:
        """
        Search audit entries
        
        Note: This is a simple implementation. For production,
        consider using a database with proper indexing.
        """
        results = []
        
        # Search through log files in date-based directory structure
        for log_file in sorted(self.log_dir.rglob("*.jsonl")):
            try:
                with open(log_file) as f:
                    for line in f:
                        entry = json.loads(line)
                        
                        # Apply filters
                        if audit_id and entry.get("audit_id") != audit_id:
                            continue
                        if customer_id and entry.get("customer_id") != customer_id:
                            continue
                        if calculation_type and entry.get("calculation_type") != calculation_type.value:
                            continue
                        
                        # Date filtering
                        entry_time = datetime.fromisoformat(entry["timestamp"])
                        if start_date and entry_time < start_date:
                            continue
                        if end_date and entry_time > end_date:
                            continue
                        
                        results.append(entry)
                        
                        # Limit results
                        if len(results) >= 1000:
                            return results
                            
            except Exception as e:
                logger.error(f"Error searching log file {log_file}: {e}")
        
        return results
    
    def _cleanup_old_logs(self):
        """Remove log files older than retention period"""
        if self._retention_days <= 0:
            return
            
        from datetime import timedelta
        cutoff_date = datetime.now() - timedelta(days=self._retention_days)
        removed_count = 0
        removed_dirs = 0
        total_size_removed = 0
        
        try:
            # Walk through year/month/day structure
            for year_dir in self.log_dir.iterdir():
                if not year_dir.is_dir() or not year_dir.name.isdigit():
                    continue
                    
                for month_dir in year_dir.iterdir():
                    if not month_dir.is_dir() or not month_dir.name.isdigit():
                        continue
                        
                    for day_dir in month_dir.iterdir():
                        if not day_dir.is_dir() or not day_dir.name.isdigit():
                            continue
                            
                        # Parse date from directory structure
                        try:
                            dir_date = datetime(int(year_dir.name), int(month_dir.name), int(day_dir.name))
                            
                            if dir_date < cutoff_date:
                                # Remove all files in this day directory
                                for log_file in day_dir.glob("*.jsonl"):
                                    file_size = log_file.stat().st_size
                                    log_file.unlink()
                                    removed_count += 1
                                    total_size_removed += file_size
                                
                                # Remove empty directory
                                day_dir.rmdir()
                                removed_dirs += 1
                                logger.info(f"🗑️ Removed old audit logs from: {day_dir}")
                        except (ValueError, OSError) as e:
                            logger.warning(f"Could not process directory: {day_dir}")
                    
                    # Clean up empty month directories
                    try:
                        if not any(month_dir.iterdir()):
                            month_dir.rmdir()
                    except OSError:
                        pass
                
                # Clean up empty year directories
                try:
                    if not any(year_dir.iterdir()):
                        year_dir.rmdir()
                except OSError:
                    pass
                    
            if removed_count > 0:
                logger.info(
                    f"✅ Cleaned up {removed_count} audit logs in {removed_dirs} directories, "
                    f"freed {total_size_removed / 1024 / 1024:.1f} MB"
                )
        except Exception as e:
            logger.error(f"Error during log cleanup: {e}")
    
    def rotate_log_if_needed(self):
        """Check if current log needs rotation and rotate if necessary"""
        with self._lock:
            current_file = self._get_current_log_file()
            
            # If file changed, update the logger
            if self._current_log_file != current_file:
                self._current_log_file = current_file
                self._entries_count = 0
                
                # Update the file handler
                for handler in self.audit_logger.handlers[:]:
                    self.audit_logger.removeHandler(handler)
                    handler.close()
                
                handler = logging.FileHandler(current_file)
                handler.setLevel(logging.INFO)
                handler.setFormatter(logging.Formatter('%(message)s'))
                self.audit_logger.addHandler(handler)
                
                logger.info(f"📝 Rotated to new audit log: {current_file.name}")
    
    def generate_audit_report(
        self,
        start_date: datetime,
        end_date: datetime,
        output_file: Optional[str] = None
    ) -> Dict:
        """Generate audit report for a date range"""
        entries = self.search_entries(start_date=start_date, end_date=end_date)
        
        # Aggregate statistics
        report = {
            "period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat()
            },
            "total_calculations": len(entries),
            "calculations_by_type": {},
            "errors_count": 0,
            "warnings_count": 0,
            "unique_customers": set(),
            "average_loan_amount": Decimal("0"),
            "average_interest_rate": Decimal("0"),
            "total_npv": Decimal("0")
        }
        
        loan_amounts = []
        interest_rates = []
        
        for entry in entries:
            # Count by type
            calc_type = entry.get("calculation_type", "unknown")
            report["calculations_by_type"][calc_type] = report["calculations_by_type"].get(calc_type, 0) + 1
            
            # Count errors/warnings
            if entry.get("errors"):
                report["errors_count"] += 1
            if entry.get("warnings"):
                report["warnings_count"] += 1
            
            # Track customers
            if entry.get("customer_id"):
                report["unique_customers"].add(entry["customer_id"])
            
            # Aggregate financial metrics
            inputs = entry.get("inputs", {})
            if "loan_amount" in inputs:
                loan_amounts.append(Decimal(inputs["loan_amount"]))
            if "interest_rate" in inputs:
                interest_rates.append(Decimal(inputs["interest_rate"]))
            
            outputs = entry.get("outputs", {})
            if "npv" in outputs and outputs["npv"]:
                report["total_npv"] += Decimal(outputs["npv"])
        
        # Calculate averages
        if loan_amounts:
            report["average_loan_amount"] = sum(loan_amounts) / len(loan_amounts)
        if interest_rates:
            report["average_interest_rate"] = sum(interest_rates) / len(interest_rates)
        
        report["unique_customers"] = len(report["unique_customers"])
        
        # Save report if requested
        if output_file:
            with open(output_file, 'w') as f:
                json.dump(self._serialize_value(report), f, indent=2)
        
        return report


# Singleton instance
_audit_logger: Optional[FinancialAuditLogger] = None
_audit_lock = threading.Lock()
_cleanup_thread: Optional[threading.Timer] = None


def _schedule_cleanup():
    """Schedule periodic cleanup of old logs"""
    global _cleanup_thread
    
    if _audit_logger:
        # Run cleanup
        _audit_logger._cleanup_old_logs()
        
        # Schedule next cleanup in 24 hours
        _cleanup_thread = threading.Timer(86400, _schedule_cleanup)  # 24 hours
        _cleanup_thread.daemon = True
        _cleanup_thread.start()


def get_audit_logger() -> FinancialAuditLogger:
    """Get or create the global audit logger"""
    global _audit_logger, _cleanup_thread
    
    if _audit_logger is None:
        with _audit_lock:
            if _audit_logger is None:
                from config.facade import get_bool
                enabled = get_bool("features.enable_audit_logging", True)
                
                if enabled:
                    _audit_logger = FinancialAuditLogger()
                    logger.info("Financial audit logger initialized")
                    
                    # Schedule periodic cleanup
                    if _cleanup_thread is None:
                        _schedule_cleanup()
    
    return _audit_logger