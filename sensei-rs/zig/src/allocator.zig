//! Custom memory allocators: arena and pool.
//!
//! These are exported to Rust via FFI for zero-copy interop.

const std = @import("std");

// ──────────────────────────────────────────────
// Arena allocator
// ──────────────────────────────────────────────

pub const ArenaAllocator = struct {
    buffer: []u8,
    cursor: usize,

    pub fn init(capacity: usize) ArenaAllocator {
        const buf = std.heap.page_allocator.alloc(u8, capacity) catch @panic("OOM");
        return ArenaAllocator{ .buffer = buf, .cursor = 0 };
    }

    pub fn alloc(self: *ArenaAllocator, size: usize) ?[]u8 {
        const start = self.cursor;
        const end = start + size;
        if (end > self.buffer.len) return null;
        self.cursor = end;
        return self.buffer[start..end];
    }

    pub fn reset(self: *ArenaAllocator) void {
        self.cursor = 0;
    }

    pub fn deinit(self: *ArenaAllocator) void {
        std.heap.page_allocator.free(self.buffer);
    }
};

// ──────────────────────────────────────────────
// Pool allocator (fixed-size blocks)
// ──────────────────────────────────────────────

pub const PoolAllocator = struct {
    arena: ArenaAllocator,
    block_size: usize,
    free_list: std.ArrayListUnmanaged(usize),

    pub fn init(block_size: usize, capacity: usize) PoolAllocator {
        return PoolAllocator{
            .arena = ArenaAllocator.init(block_size * capacity),
            .block_size = block_size,
            .free_list = .{},
        };
    }

    pub fn alloc(self: *PoolAllocator) ?[]u8 {
        // Try free list first
        if (self.free_list.pop()) |offset| {
            return self.arena.buffer[offset .. offset + self.block_size];
        }
        // Otherwise bump from arena
        return self.arena.alloc(self.block_size);
    }

    pub fn dealloc(self: *PoolAllocator, ptr: []u8) void {
        const offset = @intFromPtr(ptr.ptr) - @intFromPtr(self.arena.buffer.ptr);
        self.free_list.append(std.heap.page_allocator, offset) catch @panic("OOM");
    }

    pub fn reset(self: *PoolAllocator) void {
        self.arena.reset();
        self.free_list.clearRetainingCapacity();
    }

    pub fn deinit(self: *PoolAllocator) void {
        self.arena.deinit();
        self.free_list.deinit(std.heap.page_allocator);
    }
};

test "ArenaAllocator basic" {
    var arena = ArenaAllocator.init(1024);
    defer arena.deinit();

    const block = arena.alloc(64) orelse @panic("should alloc");
    try std.testing.expectEqual(@as(usize, 64), block.len);
    try std.testing.expectEqual(@as(usize, 64), arena.cursor);
}

test "ArenaAllocator overflow" {
    var arena = ArenaAllocator.init(16);
    defer arena.deinit();

    try std.testing.expect(arena.alloc(8) != null);
    try std.testing.expect(arena.alloc(8) != null);
    try std.testing.expect(arena.alloc(1) == null);
}

test "PoolAllocator reuse" {
    var pool = PoolAllocator.init(32, 10);
    defer pool.deinit();

    const block1 = pool.alloc() orelse @panic("should alloc");
    pool.dealloc(block1);
    const block2 = pool.alloc() orelse @panic("should alloc");
    try std.testing.expectEqual(@intFromPtr(block1.ptr), @intFromPtr(block2.ptr));
}
