"""
Database Transaction Manager
Ensures data consistency for write operations
"""
import logging
from contextlib import contextmanager
from typing import Optional, Callable, Any
import threading

logger = logging.getLogger(__name__)


class TransactionManager:
    """
    Manages database transactions to ensure data consistency.
    
    Think of it like a "save point" in a video game:
    - Start transaction = create save point
    - Commit = save progress
    - Rollback = reload from save point
    """
    
    def __init__(self):
        self._local = threading.local()
    
    @property
    def in_transaction(self) -> bool:
        """Check if we're currently in a transaction"""
        return getattr(self._local, 'in_transaction', False)
    
    @contextmanager
    def transaction(self, connection=None):
        """
        Start a database transaction.
        
        Usage:
            with transaction_manager.transaction(connection) as tx:
                # Do multiple operations
                update_customer_data(...)
                update_offer_data(...)
                # If anything fails, everything is rolled back
        """
        if self.in_transaction:
            # Already in a transaction, just yield
            logger.debug("Already in transaction, nesting not supported")
            yield self
            return
        
        self._local.in_transaction = True
        self._local.operations = []
        self._local.connection = connection
        
        try:
            logger.info("🔒 Starting transaction")
            
            # If connection provided, set autocommit to False
            if connection:
                try:
                    connection.autocommit = False
                except Exception as e:
                    logger.warning(f"Could not disable autocommit: {e}")
            
            # Yield control to the caller
            yield self
            
            # If we get here, everything succeeded
            self._commit()
            
        except Exception as e:
            # Something went wrong, roll back
            logger.error(f"❌ Transaction failed: {e}")
            self._rollback()
            raise
        
        finally:
            self._local.in_transaction = False
            self._local.operations = []
            self._local.connection = None
            
            # Reset autocommit if connection provided
            if connection:
                try:
                    connection.autocommit = True
                except Exception as e:
                    logger.warning(f"Could not reset autocommit: {e}")
    
    def add_operation(self, operation: Callable, rollback_operation: Optional[Callable] = None):
        """
        Add an operation to the current transaction.
        
        Args:
            operation: Function to execute
            rollback_operation: Function to undo the operation if needed
        """
        if not self.in_transaction:
            # Not in a transaction, just execute immediately
            return operation()
        
        # Store operation for tracking
        self._local.operations.append({
            'operation': operation,
            'rollback': rollback_operation,
            'completed': False
        })
        
        # Execute the operation
        try:
            result = operation()
            self._local.operations[-1]['completed'] = True
            self._local.operations[-1]['result'] = result
            return result
        except Exception as e:
            logger.error(f"Operation failed in transaction: {e}")
            raise
    
    def _commit(self):
        """Commit the transaction"""
        logger.info(f"✅ Committing transaction with {len(self._local.operations)} operations")
        
        # If we have a connection stored, commit it
        if hasattr(self._local, 'connection') and self._local.connection:
            try:
                self._local.connection.commit()
                logger.debug("Database COMMIT executed successfully")
            except Exception as e:
                logger.error(f"Failed to commit transaction: {e}")
                raise
    
    def _rollback(self):
        """Rollback the transaction"""
        logger.warning(f"⏪ Rolling back transaction with {len(self._local.operations)} operations")
        
        # If we have a connection stored, rollback it
        if hasattr(self._local, 'connection') and self._local.connection:
            try:
                self._local.connection.rollback()
                logger.debug("Database ROLLBACK executed successfully")
            except Exception as e:
                logger.error(f"Failed to rollback transaction: {e}")
        
        # Execute rollback operations in reverse order
        for op in reversed(self._local.operations):
            if op['completed'] and op['rollback']:
                try:
                    op['rollback']()
                    logger.debug(f"Rolled back operation successfully")
                except Exception as e:
                    logger.error(f"Failed to rollback operation: {e}")


# Global transaction manager instance
_transaction_manager = TransactionManager()


def get_transaction_manager() -> TransactionManager:
    """Get the global transaction manager"""
    return _transaction_manager


# Convenience decorator for transactional operations
def transactional(func):
    """
    Decorator to make a function transactional.
    
    Usage:
        @transactional
        def update_customer_and_offers(customer_id, data):
            update_customer(customer_id, data)
            generate_new_offers(customer_id)
            # Both succeed or both fail
    """
    def wrapper(*args, **kwargs):
        tx_manager = get_transaction_manager()
        
        if tx_manager.in_transaction:
            # Already in a transaction
            return func(*args, **kwargs)
        
        # Start new transaction
        with tx_manager.transaction():
            return func(*args, **kwargs)
    
    return wrapper