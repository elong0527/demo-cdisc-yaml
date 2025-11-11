"""
Logging utilities for ADaM derivation audit trail
"""

import logging
from typing import Any
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class DerivationLog:
    """Record of a single derivation step"""
    column: str
    method: str
    source: str = None
    records_affected: int = 0
    error: str = None
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "column": self.column,
            "method": self.method,
            "source": self.source,
            "records_affected": self.records_affected,
            "error": self.error,
            "timestamp": self.timestamp.isoformat()
        }


class DerivationLogger:
    """Logger for tracking derivation steps and errors"""
    
    def __init__(self, dataset_name: str):
        self.dataset_name = dataset_name
        self.logs: list[DerivationLog] = []
        self.errors: list[DerivationLog] = []
        
        # Setup standard logger
        self.logger = logging.getLogger(f"adam_derivation.{dataset_name}")
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '[%(levelname)s] %(name)s: %(message)s'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)
    
    def log_derivation(self, column: str, method: str, source: str = None, 
                      records: int = 0):
        """Log successful derivation"""
        log_entry = DerivationLog(
            column=column,
            method=method,
            source=source,
            records_affected=records
        )
        self.logs.append(log_entry)
        self.logger.info(f"Derived {column} using {method} from {source or 'constant'}")
    
    def log_error(self, column: str, method: str, error: str, source: str = None):
        """Log derivation error"""
        log_entry = DerivationLog(
            column=column,
            method=method,
            source=source,
            error=error
        )
        self.errors.append(log_entry)
        self.logger.error(f"Failed to derive {column}: {error}")
    
    def get_summary(self) -> dict[str, Any]:
        """Get summary of derivation process"""
        return {
            "dataset": self.dataset_name,
            "columns_derived": len(self.logs),
            "errors": len(self.errors),
            "derivations": [log.to_dict() for log in self.logs],
            "error_details": [log.to_dict() for log in self.errors]
        }
    
    def has_errors(self) -> bool:
        """Check if any errors occurred"""
        return len(self.errors) > 0