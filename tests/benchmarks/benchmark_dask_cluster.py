#!/usr/bin/env python3
"""Simple test of Dask cluster connectivity and basic computation."""

from dask.distributed import Client
import time


def simple_task(x):
    """Simple computation for testing."""
    time.sleep(0.1)
    return x * 2


def main():
    """Test Dask cluster."""
    print("Connecting to Dask cluster...")
    
    try:
        client = Client("tcp://localhost:8786", timeout=10)
        print(f"✓ Connected to cluster: {client}")
        print(f"  Scheduler: {client.scheduler_info()['address']}")
        print(f"  Workers: {client.scheduler_info()['n_workers']}")
        print(f"  Threads: {client.scheduler_info()['total_threads']}")
        print()
        
        # Test 1: Submit function directly
        print("Test 1: Submit function directly")
        future = client.submit(simple_task, 21)
        result = future.result()
        print(f"  Result: simple_task(21) = {result}")
        print()
        
        # Test 2: Submit multiple tasks
        print("Test 2: Submit multiple tasks")
        futures = [client.submit(simple_task, i) for i in range(5)]
        results = [f.result() for f in futures]
        print(f"  Results: {results}")
        print()
        
        # Test 3: Map operation (works with version mismatch)
        print("Test 3: Map operation")
        futures = client.map(simple_task, range(10))
        results = client.gather(futures)
        print(f"  Map results: {results}")
        print()
        
        # Test 4: Scatter/gather (efficient batch processing)
        print("Test 4: Scatter/Gather")
        data = list(range(20))
        scattered = client.scatter(data)
        results = client.map(simple_task, scattered)
        gathered = client.gather(results)
        print(f"  Processed {len(gathered)} items")
        print(f"  Sample: {gathered[:5]}")
        
        client.close()
        print("\n✓ All tests passed!")
        
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
