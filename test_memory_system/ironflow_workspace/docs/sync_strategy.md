# Offline-First Sync Strategy for IronFlow

## Overview

IronFlow uses an offline-first architecture to ensure users can log workouts anywhere, anytime, even without internet connectivity. This document outlines the synchronization strategy for handling data conflicts and ensuring eventual consistency.

## Core Principles

1. **Local-First**: All operations happen locally first
2. **Eventual Consistency**: Data will eventually sync when connection available
3. **Conflict Resolution**: Clear rules for handling conflicting edits
4. **User Transparency**: Users are informed of sync status and conflicts
5. **Data Integrity**: No data loss, even in conflict scenarios

## Architecture Components

### 1. Local Storage
- **Primary Store**: SQLite or IndexedDB on mobile
- **Mirrors server schema**: Uses same JSONB structure for flexibility
- **Write-Ahead Log (WAL)**: Ensures durability of local changes

### 2. Sync Queue
- **Entity**: `sync_queue` table (see schema)
- **Fields**:
  - `entity_type`: workout, user_profile, progress, recovery
  - `entity_id`: UUID of the entity
  - `operation`: create, update, delete
  - `data`: Full entity snapshot (JSONB)
  - `timestamp`: When change was made locally
  - `version`: Optimistic locking version number
  - `status`: pending, synced, conflict, error
  - `retry_count`: Number of sync attempts

### 3. Sync Engine
- **Trigger**: Background job + manual sync button
- **Frequency**:
  - Every 5 minutes when app active
  - On app foreground (returning from background)
  - Immediately after workout completion (if online)
- **Batch Processing**: Syncs multiple changes in single request

## Sync Flow

### Happy Path (No Conflicts)

```
1. User makes change (e.g., logs workout)
   └─> Write to local DB
   └─> Add entry to sync_queue with status='pending'
   └─> UI shows "synced locally" indicator

2. Sync engine wakes up
   └─> Fetch pending items from sync_queue
   └─> Batch into sync request
   └─> Send to server via gRPC

3. Server processes sync
   └─> Validates data
   └─> Checks version numbers
   └─> Writes to Postgres
   └─> Returns success with server timestamps

4. Client receives confirmation
   └─> Update sync_queue items to status='synced'
   └─> Update local entities with server timestamps
   └─> UI shows "synced" indicator
```

### Conflict Detection

Conflicts occur when:
- Same entity modified on multiple devices
- Version mismatch detected
- Server has newer data than client's base version

**Detection Mechanism**: Optimistic Locking
```sql
-- Server checks version before update
UPDATE workouts
SET data = $1, version = version + 1
WHERE id = $2 AND version = $3
RETURNING *;

-- If no rows affected, version mismatch = conflict
```

## Conflict Resolution Strategies

### Strategy 1: Last-Write-Wins (LWW) - For User Profile
**Use Case**: User settings, preferences

**Logic**:
```typescript
if (serverTimestamp > clientTimestamp) {
  // Server version is newer, client updates local
  acceptServerVersion();
} else {
  // Client version is newer, push to server
  pushClientVersion();
}
```

**Rationale**: Profile changes are typically sequential (user changes settings on one device at a time). Simple timestamp comparison works well.

### Strategy 2: Merge with User Confirmation - For Workouts
**Use Case**: Workout logs (most critical data)

**Logic**:
```typescript
if (conflict detected) {
  // Store both versions
  storeConflictVersions(clientData, serverData);

  // Flag in sync_queue
  updateSyncQueue({
    status: 'conflict',
    conflict_data: { client: clientData, server: serverData }
  });

  // Notify user
  showConflictNotification();
}

// User resolves conflict
userSelectsVersion(selectedVersion) {
  // Push selected version as authoritative
  pushToServer(selectedVersion, forceOverwrite: true);
  updateSyncQueue({ status: 'synced' });
}
```

**Resolution UI**:
```
┌─────────────────────────────────────┐
│ Workout Conflict Detected           │
├─────────────────────────────────────┤
│ The same workout was edited on      │
│ multiple devices.                   │
│                                     │
│ Version A (Phone):                  │
│ - Bench Press: 3x225                │
│ - Completed at 2:15 PM              │
│                                     │
│ Version B (Tablet):                 │
│ - Bench Press: 3x225                │
│ - Squat: 3x315                      │
│ - Completed at 2:20 PM              │
│                                     │
│ [ Keep Phone ] [ Keep Tablet ]      │
│ [ Merge Both (advanced) ]           │
└─────────────────────────────────────┘
```

**Rationale**: Workouts are critical data. Automatic merging risks data loss. User knows context best.

### Strategy 3: CRDT-like Merge - For Volume Tracking
**Use Case**: Weekly volume counters

**Logic**:
```typescript
// Volume is additive - merge both sources
function mergeVolumeData(client, server) {
  const merged = {};

  Object.keys(client.muscleGroups).forEach(muscle => {
    // Take maximum sets seen (conservative estimate)
    merged[muscle] = Math.max(
      client.muscleGroups[muscle].sets || 0,
      server.muscleGroups[muscle].sets || 0
    );
  });

  return merged;
}
```

**Rationale**: Volume tracking is cumulative. Taking max ensures we don't undercount.

### Strategy 4: Server Authoritative - For Exercise Database
**Use Case**: Exercise definitions, app-provided data

**Logic**:
```typescript
// Always accept server version for reference data
if (entity_type === 'exercise_definition') {
  acceptServerVersion();
  notifyUserOfUpdates();
}
```

**Rationale**: Exercise database is managed by app, not user-generated content.

## Conflict Scenarios Matrix

| Entity Type      | Conflict Strategy           | User Action Required |
|------------------|-----------------------------|----------------------|
| Workout          | User confirmation           | Yes                  |
| User Profile     | Last-Write-Wins             | No                   |
| Volume Tracking  | Merge (max)                 | No                   |
| Recovery Data    | Last-Write-Wins per day     | No                   |
| Progression      | User confirmation           | Yes (affects training)|
| Exercise Library | Server authoritative        | No                   |

## Implementation Details

### Data Versioning

Each mutable entity includes:
```typescript
{
  id: string,
  data: any,          // The actual entity data
  version: number,    // Increments on each update
  createdAt: Date,
  updatedAt: Date,
  syncedAt?: Date,    // Last successful sync
  deviceId: string    // Which device made this change
}
```

### Sync Request Format (gRPC)

```protobuf
message SyncRequest {
  string user_id = 1;
  string device_id = 2;
  repeated SyncItem items = 3;
}

message SyncItem {
  string entity_type = 1;
  string entity_id = 2;
  string operation = 3;  // create, update, delete
  bytes data = 4;        // JSONB serialized
  int32 version = 5;
  int64 timestamp = 6;
}

message SyncResponse {
  repeated SyncResult results = 1;
}

message SyncResult {
  string entity_id = 1;
  SyncStatus status = 2;  // success, conflict, error
  bytes server_data = 3;   // Server version if conflict
  int32 server_version = 4;
  string error_message = 5;
}
```

### Handling Network Failures

**Retry Logic**:
```typescript
const RETRY_SCHEDULE = [
  30,      // 30 seconds
  60,      // 1 minute
  300,     // 5 minutes
  900,     // 15 minutes
  3600,    // 1 hour
  // After 5 failures, require manual sync
];

async function retrySyncItem(item) {
  if (item.retry_count >= RETRY_SCHEDULE.length) {
    // Flag for manual intervention
    flagForManualSync(item);
    notifyUser("Some changes couldn't sync. Check connection.");
    return;
  }

  const delay = RETRY_SCHEDULE[item.retry_count];
  setTimeout(() => attemptSync(item), delay * 1000);
}
```

**Error Categories**:
1. **Transient**: Network timeout, 503 server error → Retry automatically
2. **Conflict**: Version mismatch → User resolution flow
3. **Validation**: Invalid data → Log error, flag for review
4. **Auth**: Token expired → Re-authenticate, then retry

## Edge Cases

### 1. Same Workout Edited Offline on Two Devices
- **Detection**: Version mismatch when both try to sync
- **Resolution**: User confirmation (Strategy 2)
- **Prevention**: Show warning if another device recently synced this workout

### 2. Workout Created on Two Devices for Same Date/Time
- **Detection**: Duplicate workout at same timestamp
- **Resolution**: Keep both, let user merge or delete duplicate
- **Prevention**: Include device_id in workout metadata

### 3. Long Offline Period (Week+)
- **Issue**: Large sync queue, potential for many conflicts
- **Solution**:
  - Sync in batches (oldest first)
  - Show progress indicator
  - Prioritize workout data over stats/metadata

### 4. Deleted Entity Modified Elsewhere
- **Scenario**: Device A deletes workout, Device B edits it
- **Resolution**:
  - If B's edit timestamp > A's delete: Resurrect entity, apply edit
  - If A's delete timestamp > B's edit: Delete wins, notify user of lost edit

### 5. Clock Skew Between Devices
- **Issue**: Device timestamps unreliable for conflict resolution
- **Solution**:
  - Use version numbers as primary conflict detector
  - Server timestamps as secondary
  - Allow user to see both versions with device labels

## Monitoring & Debugging

### Metrics to Track
- Sync queue depth per device
- Conflict rate (conflicts / total syncs)
- Average sync latency
- Retry count distribution
- Failed syncs requiring manual intervention

### Debug Logs
```typescript
{
  event: 'sync_attempt',
  device_id: 'abc123',
  items_count: 5,
  timestamp: '2025-01-15T10:30:00Z'
}

{
  event: 'sync_conflict',
  entity_type: 'workout',
  entity_id: 'xyz789',
  client_version: 3,
  server_version: 4,
  resolution: 'user_prompt'
}

{
  event: 'sync_success',
  items_synced: 5,
  duration_ms: 234
}
```

## Future Enhancements

1. **Operational Transform**: More sophisticated merging for fine-grained edits
2. **Differential Sync**: Only sync changed fields, not full entities
3. **Peer-to-Peer Sync**: Direct device-to-device sync on same WiFi
4. **Predictive Pre-sync**: Sync before user goes offline (detect patterns)
5. **Conflict-Free Replicated Data Types (CRDTs)**: Automatic merging for counters

## Testing Strategy

### Unit Tests
- Conflict detection logic
- Version increment handling
- Merge functions for each entity type

### Integration Tests
- Multi-device simulation
- Network failure scenarios
- Clock skew simulation

### End-to-End Tests
- Log workout on Device A while offline
- Edit same workout on Device B
- Bring both devices online
- Verify conflict UI appears
- Test user resolution flow

## Security Considerations

1. **Authentication**: JWT tokens with refresh mechanism
2. **Authorization**: User can only sync their own data
3. **Data Validation**: Server validates all incoming data
4. **Encryption**: TLS for all network requests
5. **Local Encryption**: Encrypt local SQLite database

## Conclusion

This offline-first sync strategy balances user experience, data integrity, and implementation complexity. By using optimistic locking for conflict detection and smart resolution strategies per entity type, IronFlow ensures users never lose workout data while maintaining a seamless experience.

The key insight: **Different data types need different conflict strategies**. Critical user data (workouts) requires user input, while metadata can be merged automatically.
