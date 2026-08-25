//! In-process channel-based IPC primitive.
//!
//! This is a single-process implementation used for testing and
//! when cross-process shared memory is not required. The interface
//! mirrors what a real shm-based IPC would provide.

const std = @import("std");

const Channel = std.ArrayListUnmanaged(u8);

/// A map of named channels, each holding a queue of byte payloads.
pub const ChannelMap = struct {
    channels: std.StringHashMapUnmanaged(std.ArrayListUnmanaged(std.ArrayListUnmanaged(u8))),

    pub fn init(_: std.mem.Allocator) ChannelMap {
        return ChannelMap{
            .channels = .{},
        };
    }

    /// Send a payload on a named channel.
    pub fn send(self: *ChannelMap, name: []const u8, data: []const u8) !void {
        const gpa = std.heap.page_allocator;
        const entry = try self.channels.getOrPut(gpa, name);
        if (!entry.found_existing) {
            entry.value_ptr.* = .{};
        }
        var queue = &entry.value_ptr.*;
        var msg = try std.ArrayListUnmanaged(u8).initCapacity(gpa, data.len);
        msg.appendSliceAssumeCapacity(data);
        try queue.append(gpa, msg);
    }

    /// Receive a payload from a named channel (non-blocking).
    ///
    /// Returns an owned copy of the payload (the internal queue entry is
    /// freed before returning, so the caller must free the returned slice
    /// with the page allocator). `null` when the channel is empty.
    pub fn recv(self: *ChannelMap, name: []const u8) ?[]u8 {
        const gpa = std.heap.page_allocator;
        const entry = self.channels.getEntry(name) orelse return null;
        var queue = &entry.value_ptr.*;
        if (queue.pop()) |m| {
            var msg = m;
            // Copy the payload out before freeing the queue entry.
            const owned = gpa.dupe(u8, msg.items) catch {
                msg.deinit(gpa);
                return null;
            };
            msg.deinit(gpa);
            return owned;
        }
        return null;
    }

    /// Deinitialize all channels and their messages.
    pub fn deinit(self: *ChannelMap) void {
        const gpa = std.heap.page_allocator;
        var iter = self.channels.iterator();
        while (iter.next()) |entry| {
            var queue = entry.value_ptr.*;
            for (queue.items) |*msg| {
                msg.deinit(gpa);
            }
            queue.deinit(gpa);
        }
        self.channels.deinit(gpa);
    }
};

test "ChannelMap send/recv" {
    var map = ChannelMap.init(std.testing.allocator);
    defer map.deinit();

    try map.send("test", "hello");
    const msg = map.recv("test") orelse @panic("should have message");
    defer std.heap.page_allocator.free(msg);
    try std.testing.expectEqualSlices(u8, "hello", msg);

    // Channel is now empty.
    try std.testing.expectEqual(@as(?[]u8, null), map.recv("test"));
}

test "ChannelMap no message" {
    var map = ChannelMap.init(std.testing.allocator);
    defer map.deinit();

    const msg = map.recv("nonexistent");
    try std.testing.expect(msg == null);
}
