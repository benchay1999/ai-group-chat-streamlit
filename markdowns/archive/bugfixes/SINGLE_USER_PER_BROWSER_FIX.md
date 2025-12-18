# Single User Per Browser - Fix Implementation

## Problem Statement

**Issue**: Users could log in as different users in different tabs of the same browser simultaneously.

**Example Scenario**:
1. User opens 2 tabs while logged out
2. Tab A: Logs in as "user1"
3. Tab B: Logs in as "user2"
4. Result: Both users are authenticated in the same browser at the same time ❌

This creates:
- **Security issues**: Shared browser state between different users
- **UX confusion**: Users may not realize they're logged in as different people
- **Data integrity issues**: LocalStorage and cookies contain mixed user data

---

## Solution Implemented

### ✅ Cross-Tab Login Synchronization

Implemented a **login event broadcasting system** similar to the existing logout synchronization. When any tab logs in, all other tabs are notified and react accordingly.

---

## Implementation Details

### File Modified: `frontend/src/contexts/AuthContext.jsx`

### 1. Enhanced Storage Event Listener (Lines 52-128)

**Before**: Only listened for logout events  
**After**: Listens for both logout AND login events

#### New Login Event Handler:

```javascript
// Handle login events from other tabs
// Enforce single user per browser - if different user logs in, log out current user
if (e.key === 'login_event' && e.newValue) {
  const loginData = JSON.parse(e.newValue);
  const currentUserId = user?.user_id;
  const newUserId = loginData.user_id;
  
  // Scenario 1: Different user logged in → Force logout current user
  if (currentUserId && newUserId && currentUserId !== newUserId) {
    setUser(null);
    setIsAuthenticated(false);
    toast.info(`Another user (${newUserId}) logged in. You have been logged out.`);
  }
  
  // Scenario 2: No user in this tab → Sync with new login
  else if (!currentUserId && newUserId) {
    // Auto-login the user in this tab too
    const userData = await authAPI.getCurrentUser();
    setUser(userData);
    setIsAuthenticated(true);
    toast.success(`Logged in as ${userData.user_id} (from another tab)`);
  }
}
```

**Key Logic**:
- **Force Logout**: If Tab A has user1 logged in and Tab B logs in as user2, Tab A is automatically logged out
- **Auto Sync**: If Tab A is logged out and Tab B logs in, Tab A automatically syncs and logs in with the same user

### 2. Updated `login()` Function (Lines 130-163)

**Added login event broadcast**:

```javascript
// Broadcast login event to other tabs
const loginEvent = JSON.stringify({
  user_id: data.user_id,
  timestamp: Date.now()
});
localStorage.setItem('login_event', loginEvent);
localStorage.removeItem('login_event'); // Trigger event by removing
```

**How It Works**:
1. Set `login_event` in localStorage with user_id and timestamp
2. Immediately remove it to trigger the storage event
3. Other tabs detect this change and react accordingly

### 3. Updated `mturkLogin()` Function (Lines 195-237)

**Same login event broadcast added** to ensure MTurk workers also follow the single-user-per-browser rule.

---

## Behavior Matrix

### Scenario 1: Same User in Multiple Tabs ✅
- **Tab A**: Logged in as "alice"
- **Tab B**: Logs in as "alice"
- **Result**: Both tabs stay logged in as "alice" (synced)

### Scenario 2: Different Users ✅
- **Tab A**: Logged in as "alice"
- **Tab B**: Attempts to log in as "bob"
- **Result**: 
  - Tab B logs in as "bob" ✓
  - Tab A is **automatically logged out** with notification ✓
  - Only "bob" is logged in across all tabs ✓

### Scenario 3: Login While Logged Out ✅
- **Tab A**: Logged out
- **Tab B**: Logs in as "carol"
- **Result**: Both tabs automatically log in as "carol" (synced)

### Scenario 4: Logout Synchronization ✅ (Already Existed)
- **Tab A**: Logged in as "dave"
- **Tab B**: Clicks logout
- **Result**: Both tabs logged out (synced)

---

## Technical Implementation

### Storage Event Mechanism

The browser's `storage` event fires when localStorage changes **in other tabs only** (not the current tab). This is perfect for cross-tab synchronization.

```javascript
window.addEventListener('storage', (e) => {
  // e.key: The key that changed
  // e.newValue: The new value
  // e.oldValue: The previous value
  // Only fires for changes from OTHER tabs
});
```

### Why Set + Remove Immediately?

```javascript
localStorage.setItem('login_event', loginEvent);
localStorage.removeItem('login_event');
```

**Reason**: We want to trigger an event every time someone logs in, even with the same user. By setting and immediately removing, we ensure:
1. The value changes (triggers event)
2. The localStorage doesn't accumulate stale login events
3. Each login creates a new event with a unique timestamp

---

## Testing Checklist

### ✅ Basic Scenarios
- [x] Open 2 tabs, log in as different users → First user is logged out
- [x] Open 2 tabs logged out, log in as same user → Both tabs log in
- [x] Log out from one tab → All tabs log out
- [x] Log in as user1, then log in as user2 → Only user2 remains

### ✅ Edge Cases
- [x] Log in on Tab A, close Tab A, Tab B remains logged in
- [x] Log in on Tab A, log in as different user on Tab B → Tab A shows notification
- [x] MTurk login follows same rules as regular login
- [x] Multiple rapid logins/logouts sync correctly

### ✅ User Experience
- [x] Clear toast notifications when logged out from another tab
- [x] Clear toast notifications when automatically logged in from another tab
- [x] No confusing state where users think they're logged in but aren't

---

## Security Benefits

1. **No Mixed Sessions**: Prevents different users' data from mixing in localStorage
2. **Clear Boundaries**: One browser = one user at a time
3. **Explicit Notifications**: Users are informed when authentication state changes
4. **Token Consistency**: All tabs share the same access token

---

## Backward Compatibility

✅ **Fully backward compatible**
- Existing logout synchronization unchanged
- New login synchronization is additive
- Works with both regular login and MTurk login
- No breaking changes to API or state management

---

## Performance Impact

**Minimal**: 
- Event listener is lightweight (only fires on actual storage changes)
- No polling or timers
- Uses native browser events (very efficient)
- Added dependency `[user]` to useEffect (necessary for checking current user)

---

## Future Enhancements (Optional)

1. **Session Conflict Warning**: Before forcing logout, show a confirmation dialog
2. **Tab Identification**: Track which tab initiated the login for better UX
3. **Session History**: Log all login/logout events for debugging
4. **Explicit User Switch**: Add a "Switch User" button instead of just logout

---

## Conclusion

✅ **Problem Solved**: Users can no longer log in as different users in different tabs of the same browser.

✅ **Behavior**: One browser = one user at a time, fully synchronized across all tabs.

✅ **Implementation**: Clean, efficient, and follows existing patterns in the codebase.

