import time
import threading
from server_lib.threadpool import ThreadPool


def test_worker_loop_basic():
    """Test basic worker loop functionality."""
    results = []
    
    def task(value):
        results.append(value)
        time.sleep(0.01)  # Simulate work
    
    pool = ThreadPool(num_workers=2, queue_max=10)
    
    # Submit tasks
    for i in range(5):
        assert pool.try_submit(task, i)
    
    # Wait for completion
    time.sleep(0.1)
    pool.shutdown()
    
    assert len(results) == 5
    assert set(results) == {0, 1, 2, 3, 4}


def test_worker_loop_exception_handling():
    """Test that worker handles exceptions and continues."""
    results = []
    
    def good_task(value):
        results.append(f"good_{value}")
    
    def bad_task(value):
        results.append(f"bad_{value}")
        raise ValueError("Test exception")
    
    pool = ThreadPool(num_workers=2, queue_max=10)
    
    # Mix good and bad tasks
    pool.try_submit(good_task, 1)
    pool.try_submit(bad_task, 2)
    pool.try_submit(good_task, 3)
    
    time.sleep(0.1)
    pool.shutdown()
    
    # All tasks should have been processed despite exception
    assert len(results) == 3
    assert "good_1" in results
    assert "bad_2" in results
    assert "good_3" in results


def test_worker_loop_shutdown_sentinel():
    """Test that workers stop on sentinel (None) values."""
    results = []
    
    def task(value):
        results.append(value)
        time.sleep(0.01)
    
    pool = ThreadPool(num_workers=2, queue_max=10)
    
    # Submit a few tasks
    for i in range(3):
        pool.try_submit(task, i)
    
    # Wait a bit for tasks to be processed
    time.sleep(0.05)
    
    # Shutdown should send sentinels
    pool.shutdown()
    
    # Should have processed all tasks (may be 2 or 3 depending on timing)
    assert len(results) >= 2  # At least 2 should be processed
    assert len(results) <= 3  # At most 3 should be processed
    assert all(r in {0, 1, 2} for r in results)  # All should be valid values
