"""
Database and connection-related exceptions
"""


class DatabaseError(Exception):
    """Base exception for all database-related errors"""
    pass


class ConnectionPoolError(DatabaseError):
    """Base exception for connection pool errors"""
    pass


class PoolExhaustedError(ConnectionPoolError):
    """Raised when connection pool has no available connections"""
    def __init__(self, timeout: float, max_connections: int):
        self.timeout = timeout
        self.max_connections = max_connections
        super().__init__(
            f"Connection pool exhausted after {timeout}s timeout. "
            f"Max connections: {max_connections}. "
            f"Consider increasing pool size or connection timeout."
        )


class ConnectionCreationError(ConnectionPoolError):
    """Raised when a new connection cannot be created"""
    def __init__(self, reason: str, original_error: Exception = None):
        self.reason = reason
        self.original_error = original_error
        message = f"Failed to create database connection: {reason}"
        if original_error:
            message += f" (Original error: {original_error})"
        super().__init__(message)


class ConnectionValidationError(ConnectionPoolError):
    """Raised when a connection fails validation"""
    def __init__(self, connection_id: str = None):
        self.connection_id = connection_id
        super().__init__(
            f"Connection {'#' + connection_id if connection_id else ''} "
            f"failed validation check and was removed from pool"
        )


class DatabaseTimeoutError(DatabaseError):
    """Raised when a database operation times out"""
    def __init__(self, operation: str, timeout: float):
        self.operation = operation
        self.timeout = timeout
        super().__init__(
            f"Database operation '{operation}' timed out after {timeout}s"
        )


class TransactionError(DatabaseError):
    """Base exception for transaction-related errors"""
    pass


class NestedTransactionError(TransactionError):
    """Raised when nested transaction operations fail"""
    def __init__(self, savepoint_name: str, reason: str):
        self.savepoint_name = savepoint_name
        self.reason = reason
        super().__init__(
            f"Nested transaction at savepoint '{savepoint_name}' failed: {reason}"
        )


class RollbackError(TransactionError):
    """Raised when transaction rollback fails"""
    def __init__(self, operation_count: int, failed_count: int):
        self.operation_count = operation_count
        self.failed_count = failed_count
        super().__init__(
            f"Failed to rollback {failed_count} of {operation_count} operations. "
            f"Database may be in inconsistent state."
        )