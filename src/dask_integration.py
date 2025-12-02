"""Dask distributed computing integration for Prefect flows."""

from typing import Optional, Dict, Any
import logging

from dask.distributed import Client
from prefect import task, get_run_logger

logger = logging.getLogger(__name__)


class DaskClientManager:
    """Manages Dask client lifecycle."""
    
    _instance: Optional[Client] = None
    
    @classmethod
    def get_client(cls, scheduler_address: str = "tcp://localhost:8786") -> Client:
        """Get or create Dask client."""
        if cls._instance is None:
            logger.info(f"Connecting to Dask scheduler at {scheduler_address}")
            cls._instance = Client(scheduler_address=scheduler_address)
        return cls._instance
    
    @classmethod
    def close(cls):
        """Close Dask client."""
        if cls._instance is not None:
            cls._instance.close()
            cls._instance = None


@task(name="dask_info")
def get_dask_info() -> Dict[str, Any]:
    """Get Dask cluster information."""
    task_logger = get_run_logger()
    
    try:
        client = DaskClientManager.get_client()
        info = {
            "scheduler": client.scheduler_address,
            "workers": len(client.nthreads()),
            "threads": sum(client.nthreads().values()),
            "dashboard": "http://localhost:8787",
        }
        task_logger.info(f"Dask cluster: {info['workers']} workers, {info['threads']} threads")
        return info
    except Exception as e:
        task_logger.error(f"Dask not available: {e}")
        raise


@task(name="dask_parallel_compute")
def parallel_compute(items: list, compute_fn) -> list:
    """
    Execute function on items in parallel using Dask.
    
    Args:
        items: List of items to process
        compute_fn: Function to apply to each item
        
    Returns:
        List of results
    """
    task_logger = get_run_logger()
    client = DaskClientManager.get_client()
    
    task_logger.info(f"Parallel computing {len(items)} items")
    
    try:
        # Submit jobs to Dask
        futures = [client.submit(compute_fn, item) for item in items]
        
        # Collect results
        results = []
        for i, future in enumerate(futures):
            try:
                result = future.result(timeout=5)
                results.append(result)
            except Exception as e:
                task_logger.warning(f"Item {i} failed: {e}")
                results.append(None)
        
        task_logger.info(f"Completed {len(results)} computations")
        return results
        
    except Exception as e:
        task_logger.error(f"Parallel compute failed: {e}")
        raise