"""
Bulk Request Queue Manager
Handles queueing and rate limiting for bulk offer generation
"""
import asyncio
import time
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime
from uuid import uuid4
import threading

logger = logging.getLogger(__name__)


@dataclass
class BulkRequest:
    """Represents a bulk offer generation request"""
    request_id: str
    customer_ids: List[str]
    max_offers_per_customer: Optional[int]
    timestamp: datetime
    status: str = "queued"  # queued, processing, completed, failed
    result: Optional[Dict] = None
    error: Optional[str] = None


class BulkRequestQueue:
    """
    Manages bulk offer generation requests with:
    - Request queueing
    - Concurrent request limiting
    - Memory usage protection
    - Status tracking
    """
    
    def __init__(self, 
                 max_concurrent_requests: int = 3,
                 max_customers_per_request: int = 50,
                 request_timeout: int = 300):  # 5 minutes
        """
        Initialize the bulk request queue
        
        Args:
            max_concurrent_requests: Maximum concurrent bulk requests
            max_customers_per_request: Maximum customers per request
            request_timeout: Timeout for each request in seconds
        """
        self.max_concurrent_requests = max_concurrent_requests
        self.max_customers_per_request = max_customers_per_request
        self.request_timeout = request_timeout
        
        # Request tracking
        self._requests: Dict[str, BulkRequest] = {}
        self._request_queue = asyncio.Queue()
        self._active_requests = 0
        self._lock = threading.Lock()
        
        # Start background processor
        self._processor_task = None
        self._shutdown = False
    
    async def start(self):
        """Start the background request processor"""
        if not self._processor_task:
            self._processor_task = asyncio.create_task(self._process_requests())
            logger.info("Bulk request processor started")
    
    async def stop(self):
        """Stop the background processor"""
        self._shutdown = True
        if self._processor_task:
            await self._processor_task
            logger.info("Bulk request processor stopped")
    
    async def submit_request(self, 
                           customer_ids: List[str], 
                           max_offers_per_customer: Optional[int] = None) -> str:
        """
        Submit a bulk offer generation request
        
        Args:
            customer_ids: List of customer IDs
            max_offers_per_customer: Optional offer limit
            
        Returns:
            Request ID for tracking
            
        Raises:
            ValueError: If request exceeds limits
        """
        # Validate request
        if len(customer_ids) > self.max_customers_per_request:
            raise ValueError(f"Request exceeds maximum of {self.max_customers_per_request} customers")
        
        if not customer_ids:
            raise ValueError("No customer IDs provided")
        
        # Create request
        request_id = str(uuid4())
        request = BulkRequest(
            request_id=request_id,
            customer_ids=customer_ids[:self.max_customers_per_request],
            max_offers_per_customer=max_offers_per_customer,
            timestamp=datetime.now()
        )
        
        # Store and queue request
        with self._lock:
            self._requests[request_id] = request
        
        await self._request_queue.put(request)
        logger.info(f"Queued bulk request {request_id} for {len(customer_ids)} customers")
        
        return request_id
    
    def get_request_status(self, request_id: str) -> Optional[Dict]:
        """
        Get status of a bulk request
        
        Args:
            request_id: Request ID to check
            
        Returns:
            Status dict or None if not found
        """
        with self._lock:
            request = self._requests.get(request_id)
            
        if not request:
            return None
        
        return {
            "request_id": request.request_id,
            "status": request.status,
            "customer_count": len(request.customer_ids),
            "timestamp": request.timestamp.isoformat(),
            "result": request.result,
            "error": request.error
        }
    
    async def _process_requests(self):
        """Background task to process queued requests"""
        while not self._shutdown:
            try:
                # Wait for request with timeout
                request = await asyncio.wait_for(
                    self._request_queue.get(), 
                    timeout=1.0
                )
                
                # Check concurrent limit
                while self._active_requests >= self.max_concurrent_requests:
                    await asyncio.sleep(0.1)
                
                # Process request
                asyncio.create_task(self._process_single_request(request))
                
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Error in request processor: {e}")
    
    async def _process_single_request(self, request: BulkRequest):
        """Process a single bulk request"""
        with self._lock:
            self._active_requests += 1
            request.status = "processing"
        
        try:
            # Import here to avoid circular dependencies
            from app.services.offer_service import offer_service
            
            # Process with timeout
            result = await asyncio.wait_for(
                self._generate_offers_safely(request),
                timeout=self.request_timeout
            )
            
            # Update request
            with self._lock:
                request.status = "completed"
                request.result = result
            
            logger.info(f"Completed bulk request {request.request_id}")
            
        except asyncio.TimeoutError:
            with self._lock:
                request.status = "failed"
                request.error = f"Request timed out after {self.request_timeout} seconds"
            logger.error(f"Bulk request {request.request_id} timed out")
            
        except Exception as e:
            with self._lock:
                request.status = "failed"
                request.error = str(e)
            logger.error(f"Bulk request {request.request_id} failed: {e}")
            
        finally:
            with self._lock:
                self._active_requests -= 1
    
    async def _generate_offers_safely(self, request: BulkRequest) -> Dict:
        """
        Generate offers with memory protection
        
        Instead of loading entire inventory into memory,
        we'll process in smaller batches
        """
        from app.services.offer_service import offer_service
        from data import database
        
        results = []
        errors = []
        
        # Process customers in smaller batches to limit memory usage
        batch_size = 10
        for i in range(0, len(request.customer_ids), batch_size):
            batch_ids = request.customer_ids[i:i + batch_size]
            
            for customer_id in batch_ids:
                try:
                    # Get customer
                    customer = database.get_customer_by_id(customer_id)
                    if not customer:
                        errors.append({
                            "customer_id": customer_id,
                            "error": "Customer not found"
                        })
                        continue
                    
                    # Get pre-filtered inventory for this specific customer
                    inventory = database.get_tradeup_inventory_for_customer(customer)
                    
                    if not inventory:
                        results.append({
                            "customer_id": customer_id,
                            "offers_count": 0,
                            "best_npv": 0
                        })
                        continue
                    
                    # Generate offers
                    from engine.basic_matcher import basic_matcher
                    offer_result = await asyncio.to_thread(
                        basic_matcher.find_all_viable,
                        customer,
                        inventory
                    )
                    
                    # Summarize results
                    total_offers = sum(
                        len(offers) for offers in offer_result["offers"].values()
                    )
                    
                    best_npv = max(
                        (offer.get("npv", 0) for tier_offers in offer_result["offers"].values() 
                         for offer in tier_offers),
                        default=0
                    )
                    
                    results.append({
                        "customer_id": customer_id,
                        "offers_count": total_offers,
                        "best_npv": best_npv
                    })
                    
                except Exception as e:
                    errors.append({
                        "customer_id": customer_id,
                        "error": str(e)
                    })
            
            # Small delay between batches to prevent overload
            await asyncio.sleep(0.1)
        
        return {
            "processed": len(request.customer_ids),
            "successful": len(results),
            "failed": len(errors),
            "results": results,
            "errors": errors,
            "processing_time": (datetime.now() - request.timestamp).total_seconds()
        }
    
    def cleanup_old_requests(self, max_age_hours: int = 24):
        """Remove old completed requests"""
        cutoff = datetime.now().timestamp() - (max_age_hours * 3600)
        
        with self._lock:
            to_remove = []
            for request_id, request in self._requests.items():
                if request.timestamp.timestamp() < cutoff and request.status in ["completed", "failed"]:
                    to_remove.append(request_id)
            
            for request_id in to_remove:
                del self._requests[request_id]
        
        if to_remove:
            logger.info(f"Cleaned up {len(to_remove)} old requests")


# Global queue instance
_queue_instance = None
_queue_lock = threading.Lock()


def get_bulk_queue() -> BulkRequestQueue:
    """Get or create the global bulk request queue"""
    global _queue_instance
    
    if _queue_instance is None:
        with _queue_lock:
            if _queue_instance is None:
                _queue_instance = BulkRequestQueue()
                logger.info("Initialized bulk request queue")
    
    return _queue_instance