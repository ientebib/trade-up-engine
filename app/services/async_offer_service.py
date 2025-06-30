"""
Async Offer Service - Non-blocking offer generation
"""
import asyncio
import logging
import uuid
from typing import Dict, Optional, Any
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
import threading

from engine.basic_matcher import basic_matcher
from data import database

logger = logging.getLogger(__name__)


class AsyncOfferService:
    """
    Manages async offer generation with status tracking
    """
    
    def __init__(self):
        self._tasks: Dict[str, Dict[str, Any]] = {}
        self._executor = ThreadPoolExecutor(max_workers=2)  # Limited workers for background tasks
        self._lock = threading.Lock()
        
    def submit_offer_generation(self, customer_id: str, custom_config: Optional[Dict] = None) -> str:
        """
        Submit an offer generation request and return immediately with a task ID
        
        Args:
            customer_id: Customer identifier
            custom_config: Optional custom configuration
            
        Returns:
            task_id: Unique task identifier to check status
        """
        task_id = str(uuid.uuid4())
        
        # Create task record
        with self._lock:
            self._tasks[task_id] = {
                "id": task_id,
                "customer_id": customer_id,
                "status": "pending",
                "created_at": datetime.utcnow().isoformat(),
                "started_at": None,
                "completed_at": None,
                "progress": 0,
                "result": None,
                "error": None
            }
        
        # Submit to executor
        future = self._executor.submit(
            self._process_offer_generation,
            task_id,
            customer_id,
            custom_config
        )
        
        logger.info(f"📋 Submitted offer generation task {task_id} for customer {customer_id}")
        return task_id
    
    def _process_offer_generation(self, task_id: str, customer_id: str, custom_config: Optional[Dict]):
        """
        Process offer generation in background thread
        """
        try:
            # Update status to processing
            with self._lock:
                self._tasks[task_id]["status"] = "processing"
                self._tasks[task_id]["started_at"] = datetime.utcnow().isoformat()
            
            logger.info(f"🚀 Starting offer generation for task {task_id}")
            
            # Get customer data
            customer = database.get_customer_by_id(customer_id)
            if not customer:
                raise ValueError(f"Customer {customer_id} not found")
            
            # Update progress
            with self._lock:
                self._tasks[task_id]["progress"] = 10
            
            # Get pre-filtered inventory
            logger.info(f"🎯 Stage 1: Pre-filtering inventory for customer {customer_id}")
            inventory_records = database.get_tradeup_inventory_for_customer(customer)
            
            if not inventory_records:
                # No inventory found
                result = {
                    "offers": {"refresh": [], "upgrade": [], "max_upgrade": []},
                    "total_offers": 0,
                    "cars_tested": 0,
                    "customer": customer,
                    "stats": {"total_evaluated": 0, "total_viable": 0}
                }
            else:
                # Update progress
                with self._lock:
                    self._tasks[task_id]["progress"] = 30
                    self._tasks[task_id]["inventory_count"] = len(inventory_records)
                
                logger.info(f"✅ Stage 1 complete: {len(inventory_records)} potential trade-ups found")
                
                # Apply financial matching
                logger.info(f"🎯 Stage 2: Applying financial matching for {customer_id}")
                
                # Process in smaller chunks to update progress
                chunk_size = 100
                all_offers = {"Refresh": [], "Upgrade": [], "Max Upgrade": []}
                
                for i in range(0, len(inventory_records), chunk_size):
                    chunk = inventory_records[i:i + chunk_size]
                    
                    if custom_config:
                        chunk_result = basic_matcher.find_all_viable(customer, chunk, custom_config)
                    else:
                        chunk_result = basic_matcher.find_all_viable(customer, chunk)
                    
                    # Merge results
                    for tier, offers in chunk_result.get("offers", {}).items():
                        all_offers[tier].extend(offers)
                    
                    # Update progress
                    progress = 30 + int(((i + len(chunk)) / len(inventory_records)) * 60)
                    with self._lock:
                        self._tasks[task_id]["progress"] = min(progress, 90)
                
                # Map to frontend keys
                tier_mapping = {
                    "Refresh": "refresh",
                    "Upgrade": "upgrade", 
                    "Max Upgrade": "max_upgrade"
                }
                
                validated_offers = {}
                for backend_tier, frontend_tier in tier_mapping.items():
                    validated_offers[frontend_tier] = all_offers.get(backend_tier, [])
                
                # Prepare final result
                result = {
                    "offers": validated_offers,
                    "total_offers": sum(len(offers) for offers in validated_offers.values()),
                    "cars_tested": len(inventory_records),
                    "customer": customer
                }
            
            # Mark as complete
            with self._lock:
                self._tasks[task_id]["status"] = "completed"
                self._tasks[task_id]["completed_at"] = datetime.utcnow().isoformat()
                self._tasks[task_id]["progress"] = 100
                self._tasks[task_id]["result"] = result
            
            logger.info(f"✅ Task {task_id} completed successfully")
            
        except Exception as e:
            logger.error(f"❌ Task {task_id} failed: {e}")
            with self._lock:
                self._tasks[task_id]["status"] = "failed"
                self._tasks[task_id]["completed_at"] = datetime.utcnow().isoformat()
                self._tasks[task_id]["error"] = str(e)
    
    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the status of a task
        
        Args:
            task_id: Task identifier
            
        Returns:
            Task status dict or None if not found
        """
        with self._lock:
            task = self._tasks.get(task_id)
            if task:
                # Don't include full result in status check (too large)
                status = {
                    "id": task["id"],
                    "customer_id": task["customer_id"],
                    "status": task["status"],
                    "progress": task["progress"],
                    "created_at": task["created_at"],
                    "started_at": task["started_at"],
                    "completed_at": task["completed_at"],
                    "error": task["error"]
                }
                
                # Include summary if completed
                if task["status"] == "completed" and task["result"]:
                    status["summary"] = {
                        "total_offers": task["result"]["total_offers"],
                        "cars_tested": task["result"]["cars_tested"]
                    }
                
                return status
            return None
    
    def get_task_result(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the full result of a completed task
        
        Args:
            task_id: Task identifier
            
        Returns:
            Full task result or None if not found/not complete
        """
        with self._lock:
            task = self._tasks.get(task_id)
            if task and task["status"] == "completed":
                return task["result"]
            return None
    
    def cleanup_old_tasks(self, max_age_hours: int = 1):
        """
        Remove old completed tasks to free memory
        """
        from datetime import datetime, timedelta
        
        cutoff = datetime.utcnow() - timedelta(hours=max_age_hours)
        
        with self._lock:
            to_remove = []
            for task_id, task in self._tasks.items():
                if task["completed_at"]:
                    completed = datetime.fromisoformat(task["completed_at"])
                    if completed < cutoff:
                        to_remove.append(task_id)
            
            for task_id in to_remove:
                del self._tasks[task_id]
            
            if to_remove:
                logger.info(f"🧹 Cleaned up {len(to_remove)} old tasks")


# Singleton instance
async_offer_service = AsyncOfferService()