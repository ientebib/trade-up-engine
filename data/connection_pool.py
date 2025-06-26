"""
Redshift Connection Pool Manager
Handles connection pooling to prevent connection exhaustion
"""
import os
import logging
import threading
from queue import Queue, Empty
from contextlib import contextmanager
import redshift_connector
from typing import Optional
from .circuit_breaker import get_redshift_breaker, CircuitBreakerOpenError
from app.utils.metrics import metrics_collector
from app.constants import (
    MIN_CONNECTIONS,
    MAX_CONNECTIONS,
    CONNECTION_TIMEOUT,
    DATABASE_QUERY_TIMEOUT
)

logger = logging.getLogger(__name__)


class RedshiftConnectionPool:
    """Thread-safe connection pool for Redshift"""
    
    def __init__(self, 
                 min_connections: int = MIN_CONNECTIONS,
                 max_connections: int = MAX_CONNECTIONS,
                 connection_timeout: int = CONNECTION_TIMEOUT):
        """
        Initialize connection pool
        
        Args:
            min_connections: Minimum number of connections to maintain
            max_connections: Maximum number of connections allowed
            connection_timeout: Timeout for acquiring a connection from pool
        """
        self.min_connections = min_connections
        self.max_connections = max_connections
        self.connection_timeout = connection_timeout
        
        # Connection parameters
        self.host = os.getenv("REDSHIFT_HOST")
        self.port = int(os.getenv("REDSHIFT_PORT", 5439))
        self.database = os.getenv("REDSHIFT_DATABASE")
        self.user = os.getenv("REDSHIFT_USER")
        self.password = os.getenv("REDSHIFT_PASSWORD")
        
        # Pool management
        self._pool = Queue(maxsize=max_connections)
        self._all_connections = set()
        self._lock = threading.Lock()
        self._created_connections = 0
        
        # Initialize minimum connections
        self._initialize_pool()
    
    def _initialize_pool(self):
        """Create initial connections for the pool"""
        for _ in range(self.min_connections):
            try:
                conn = self._create_connection()
                self._pool.put(conn)
            except Exception as e:
                logger.error(f"Failed to create initial connection: {e}")
    
    def _create_connection(self):
        """Create a new Redshift connection with circuit breaker"""
        if not all([self.host, self.port, self.database, self.user, self.password]):
            raise ValueError("Incomplete Redshift configuration")
        
        # Check circuit breaker
        breaker = get_redshift_breaker()
        
        def connect():
            return redshift_connector.connect(
                host=self.host,
                database=self.database,
                user=self.user,
                password=self.password,
                port=self.port,
                timeout=10
            )
        
        try:
            conn = breaker.call(connect)
        except Exception as e:
            logger.error(f"Failed to create connection: {e}")
            raise
        
        with self._lock:
            self._all_connections.add(conn)
            self._created_connections += 1
            
        logger.debug(f"Created new connection (total: {self._created_connections})")
        return conn
    
    @contextmanager
    def get_connection(self, timeout: Optional[int] = None):
        """
        Get a connection from the pool
        
        Args:
            timeout: Override default timeout for this request
            
        Yields:
            Redshift connection object
        """
        timeout = timeout or self.connection_timeout
        connection = None
        
        try:
            # Try to get existing connection from pool
            try:
                connection = self._pool.get(timeout=timeout)
                
                # Test if connection is still alive
                with connection.cursor() as cursor:
                    cursor.execute("SELECT 1")
                
                # Track pool hit
                metrics_collector.track_connection_pool_hit()
            except Empty:
                # Pool is empty, try to create new connection if under limit
                with self._lock:
                    if self._created_connections < self.max_connections:
                        connection = self._create_connection()
                        metrics_collector.track_connection_pool_miss()
                    else:
                        raise Exception(f"Connection pool exhausted (max: {self.max_connections})")
            
            except Exception as e:
                # Connection is dead, remove it and create new one
                logger.warning(f"Dead connection detected: {e}")
                if connection:
                    self._remove_connection(connection)
                connection = self._create_connection()
            
            yield connection
            
        finally:
            # Return connection to pool
            if connection:
                try:
                    # Test if connection is still alive
                    with connection.cursor() as cursor:
                        cursor.execute("SELECT 1")
                    self._pool.put(connection)
                except:
                    # Connection is dead
                    self._remove_connection(connection)
    
    def _remove_connection(self, connection):
        """Remove a connection from tracking"""
        try:
            connection.close()
        except:
            pass
        
        with self._lock:
            self._all_connections.discard(connection)
    
    def close_all(self):
        """Close all connections in the pool"""
        with self._lock:
            for conn in self._all_connections:
                try:
                    conn.close()
                except:
                    pass
            
            self._all_connections.clear()
            self._created_connections = 0
            
            # Clear the queue
            while not self._pool.empty():
                try:
                    self._pool.get_nowait()
                except Empty:
                    break
        
        logger.info("Connection pool closed")
    
    def get_stats(self):
        """Get pool statistics"""
        return {
            "total_connections": self._created_connections,
            "available_connections": self._pool.qsize(),
            "in_use_connections": self._created_connections - self._pool.qsize(),
            "max_connections": self.max_connections
        }


# Global connection pool instance
_pool_instance = None
_pool_lock = threading.Lock()


def get_connection_pool() -> RedshiftConnectionPool:
    """Get or create the global connection pool instance"""
    global _pool_instance
    
    if _pool_instance is None:
        with _pool_lock:
            if _pool_instance is None:
                _pool_instance = RedshiftConnectionPool()
                logger.info("Initialized Redshift connection pool")
    
    return _pool_instance


def close_connection_pool():
    """Close the global connection pool"""
    global _pool_instance
    
    if _pool_instance:
        _pool_instance.close_all()
        _pool_instance = None