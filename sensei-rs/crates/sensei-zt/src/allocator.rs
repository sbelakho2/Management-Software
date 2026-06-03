//! Custom memory allocators backed by Zig arena/pool allocators.
//!
//! When the Zig library is not available, pure-Rust `Vec`-backed
//! fallbacks are used.

use std::cell::UnsafeCell;
use std::ptr::NonNull;

/// A simple arena allocator.
///
/// Allocations are bump-allocated from a pre-allocated buffer.
/// The arena must be reset explicitly; individual frees are a no-op.
pub struct ArenaAllocator {
    buffer: UnsafeCell<Vec<u8>>,
    cursor: UnsafeCell<usize>,
}

impl ArenaAllocator {
    /// Create a new arena with the given capacity in bytes.
    pub fn new(capacity: usize) -> Self {
        Self {
            buffer: UnsafeCell::new(vec![0u8; capacity]),
            cursor: UnsafeCell::new(0),
        }
    }

    /// Allocate `size` bytes from the arena.
    ///
    /// Returns `None` if the arena is full.
    pub fn allocate(&self, size: usize) -> Option<NonNull<u8>> {
        let cursor = unsafe { &mut *self.cursor.get() };
        let buffer = unsafe { &mut *self.buffer.get() };

        let start = *cursor;
        let end = start.checked_add(size)?;

        if end > buffer.len() {
            return None;
        }

        *cursor = end;
        NonNull::new(buffer.as_mut_ptr().wrapping_add(start))
    }

    /// Reset the arena, making all memory available for reuse.
    pub fn reset(&self) {
        unsafe {
            *self.cursor.get() = 0;
        }
    }

    /// Return the number of used bytes.
    pub fn used(&self) -> usize {
        unsafe { *self.cursor.get() }
    }

    /// Return the total capacity in bytes.
    pub fn capacity(&self) -> usize {
        unsafe { (*self.buffer.get()).len() }
    }
}

unsafe impl Send for ArenaAllocator {}
unsafe impl Sync for ArenaAllocator {}

/// A pool allocator for fixed-size blocks.
///
/// Useful for frequently-allocated objects of uniform size.
pub struct PoolAllocator {
    block_size: usize,
    arena: ArenaAllocator,
    free_list: UnsafeCell<Vec<*mut u8>>,
}

impl PoolAllocator {
    /// Create a new pool with the given block size and total capacity.
    pub fn new(block_size: usize, capacity: usize) -> Self {
        let total = block_size * capacity;
        Self {
            block_size,
            arena: ArenaAllocator::new(total),
            free_list: UnsafeCell::new(Vec::with_capacity(capacity)),
        }
    }

    /// Allocate a block from the pool.
    pub fn alloc(&self) -> Option<NonNull<u8>> {
        // Try the free list first
        let free_list = unsafe { &mut *self.free_list.get() };
        if let Some(ptr) = free_list.pop() {
            return NonNull::new(ptr);
        }

        // Otherwise bump from the arena
        self.arena.allocate(self.block_size)
    }

    /// Return a block to the pool for reuse.
    pub fn dealloc(&self, ptr: *mut u8) {
        let free_list = unsafe { &mut *self.free_list.get() };
        free_list.push(ptr);
    }

    /// Reset the pool.
    pub fn reset(&self) {
        self.arena.reset();
        unsafe {
            (*self.free_list.get()).clear();
        }
    }
}

unsafe impl Send for PoolAllocator {}
unsafe impl Sync for PoolAllocator {}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_arena_alloc() {
        let arena = ArenaAllocator::new(1024);
        let ptr = arena.allocate(64).expect("should allocate");
        assert!(!ptr.as_ptr().is_null());
        assert_eq!(arena.used(), 64);
    }

    #[test]
    fn test_arena_overflow() {
        let arena = ArenaAllocator::new(16);
        assert!(arena.allocate(8).is_some());
        assert!(arena.allocate(8).is_some());
        assert!(arena.allocate(1).is_none());
    }

    #[test]
    fn test_arena_reset() {
        let arena = ArenaAllocator::new(1024);
        arena.allocate(512);
        assert_eq!(arena.used(), 512);
        arena.reset();
        assert_eq!(arena.used(), 0);
    }

    #[test]
    fn test_pool_alloc_dealloc() {
        let pool = PoolAllocator::new(32, 10);
        let ptr = pool.alloc().expect("should alloc");
        pool.dealloc(ptr.as_ptr());
        let ptr2 = pool.alloc().expect("should reuse");
        assert_eq!(ptr, ptr2);
    }
}
