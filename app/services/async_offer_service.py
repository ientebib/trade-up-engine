"""
Async Offer Service - Non-blocking offer generation
"""
import asyncio
import logging
import uuid
from typing import Dict, Optional, Any
from datetime import datetime, timedelta
import threading
import atexit

from engine.basic_matcher_sync import basic_matcher_sync as basic_matcher
from data import database

logger = logging.getLogger(__name__)


class AsyncOfferService:
    """
    Manages async offer generation with status tracking
    """
    
    def __init__(self):
        self._tasks: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()
        self._cleanup_interval = 300  # 5 minutes
        self._cleanup_thread = None
        self._stop_cleanup = threading.Event()
        self._running_tasks: Dict[str, asyncio.Task] = {}
        
        logger.info(f"🏗️ Initializing AsyncOfferService with asyncio")
        
        # Start cleanup thread
        self._start_cleanup_thread()
        
        # Register cleanup on exit
        atexit.register(self._shutdown)
        
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
        
        logger.info(f"📋 Created task {task_id} for customer {customer_id}")
        
        try:
            # Create asyncio task
            loop = asyncio.get_event_loop()
            
            # Create the coroutine
            coro = self._process_offer_generation_async(task_id, customer_id, custom_config)
            
            # Schedule it as a task
            async_task = loop.create_task(coro)
            
            # Store the task reference
            with self._lock:
                self._running_tasks[task_id] = async_task
            
            # Add completion callback
            def task_done_callback(task):
                try:
                    # Check if task had an exception
                    if task.exception():
                        logger.error(f"❌ Task {task_id} failed: {task.exception()}")
                        with self._lock:
                            if task_id in self._tasks:
                                self._tasks[task_id]["status"] = "failed"
                                self._tasks[task_id]["error"] = str(task.exception())
                                self._tasks[task_id]["completed_at"] = datetime.utcnow().isoformat()
                except Exception as e:
                    logger.error(f"Error in task callback: {e}")
                finally:
                    # Remove from running tasks
                    with self._lock:
                        self._running_tasks.pop(task_id, None)
            
            async_task.add_done_callback(task_done_callback)
            
            logger.info(f"✅ Submitted task {task_id} as asyncio task")
            
        except Exception as e:
            logger.error(f"❌ Failed to submit task {task_id}: {e}")
            with self._lock:
                self._tasks[task_id]["status"] = "failed"
                self._tasks[task_id]["error"] = f"Submission error: {str(e)}"
                self._tasks[task_id]["completed_at"] = datetime.utcnow().isoformat()
            raise
        
        return task_id
    
    async def _process_offer_generation_async(self, task_id: str, customer_id: str, custom_config: Optional[Dict]):
        """
        Process offer generation asynchronously
        """
        logger.info(f"🔄 Async task started for {task_id}")
        
        # Run the synchronous code in a thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        try:
            await loop.run_in_executor(
                None,  # Use default executor
                self._process_offer_generation_sync_internal,
                task_id,
                customer_id,
                custom_config
            )
        except Exception as e:
            logger.error(f"❌ Async task {task_id} failed: {e}")
            raise
    
    def _process_offer_generation_sync_internal(self, task_id: str, customer_id: str, custom_config: Optional[Dict]):
        """
        Internal synchronous processing logic
        """
        logger.info(f"🔄 Processing task {task_id} for customer {customer_id}")
        
        try:
            # Update status to processing
            with self._lock:
                if task_id not in self._tasks:
                    logger.error(f"❌ Task {task_id} not found in tasks dict!")
                    return
                self._tasks[task_id]["status"] = "processing"
                self._tasks[task_id]["started_at"] = datetime.utcnow().isoformat()
                logger.info(f"📝 Updated task {task_id} status to processing")
            
            logger.info(f"🚀 Starting offer generation for task {task_id}, customer {customer_id}")
            
            # Get customer data
            logger.info(f"📊 Fetching customer data for {customer_id}")
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
    
    def _start_cleanup_thread(self):
        """Start the background cleanup thread"""
        self._cleanup_thread = threading.Thread(target=self._cleanup_loop, daemon=True)
        self._cleanup_thread.start()
        logger.info("🔄 Started async task cleanup thread")
    
    def _cleanup_loop(self):
        """Background thread that periodically cleans up old tasks"""
        while not self._stop_cleanup.is_set():
            try:
                # Wait for interval or stop signal
                if self._stop_cleanup.wait(timeout=self._cleanup_interval):
                    break
                
                # Perform cleanup
                self.cleanup_old_tasks(max_age_hours=1)
            except Exception as e:
                logger.error(f"Error in cleanup thread: {e}")
    
    def _shutdown(self):
        """Shutdown the service gracefully"""
        logger.info("🛑 Shutting down AsyncOfferService...")
        
        # Stop cleanup thread
        self._stop_cleanup.set()
        if self._cleanup_thread:
            self._cleanup_thread.join(timeout=5)
        
        # Cancel any running async tasks
        with self._lock:
            for task_id, task in self._running_tasks.items():
                if not task.done():
                    task.cancel()
                    logger.info(f"Cancelled task {task_id}")
        
        logger.info("✅ AsyncOfferService shutdown complete")
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get health status of the async service"""
        with self._lock:
            active_tasks = sum(1 for t in self._tasks.values() if t["status"] in ["pending", "processing"])
            completed_tasks = sum(1 for t in self._tasks.values() if t["status"] == "completed")
            failed_tasks = sum(1 for t in self._tasks.values() if t["status"] == "failed")
            
        return {
            "status": "healthy",
            "total_tasks": len(self._tasks),
            "active_tasks": active_tasks,
            "completed_tasks": completed_tasks,
            "failed_tasks": failed_tasks,
            "cleanup_thread_active": self._cleanup_thread and self._cleanup_thread.is_alive()
        }
    
    def process_offer_generation_sync(self, customer_id: str, custom_config: Optional[Dict] = None) -> Dict:
        """
        Synchronous fallback for offer generation
        """
        logger.info(f"🔄 Processing offer generation synchronously for customer {customer_id}")
        
        try:
            # Get customer data
            customer = database.get_customer_by_id(customer_id)
            if not customer:
                raise ValueError(f"Customer {customer_id} not found")
            
            # Get pre-filtered inventory
            inventory_records = database.get_tradeup_inventory_for_customer(customer)
            
            if not inventory_records:
                return {
                    "offers": {"refresh": [], "upgrade": [], "max_upgrade": []},
                    "total_offers": 0,
                    "cars_tested": 0,
                    "customer": customer,
                    "stats": {"total_evaluated": 0, "total_viable": 0}
                }
            
            # Apply financial matching
            if custom_config:
                result = basic_matcher.find_all_viable(customer, inventory_records, custom_config)
            else:
                result = basic_matcher.find_all_viable(customer, inventory_records)
            
            # Map to frontend keys
            tier_mapping = {
                "Refresh": "refresh",
                "Upgrade": "upgrade", 
                "Max Upgrade": "max_upgrade"
            }
            
            validated_offers = {}
            for backend_tier, frontend_tier in tier_mapping.items():
                validated_offers[frontend_tier] = result.get("offers", {}).get(backend_tier, [])
            
            return {
                "offers": validated_offers,
                "total_offers": sum(len(offers) for offers in validated_offers.values()),
                "cars_tested": len(inventory_records),
                "customer": customer
            }
            
        except Exception as e:
            logger.error(f"❌ Synchronous offer generation failed: {e}")
            raise


# Singleton instance
async_offer_service = AsyncOfferService()