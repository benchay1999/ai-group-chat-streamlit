# Load Test User Cleanup Guide

## Problem

When running load tests with `load_test.py`, test users are created in the database with the pattern `loadtest_user_*`. These users remain in the database after the test completes.

---

## Quick Cleanup

### Step 1: Preview what will be deleted

```bash
python3 cleanup_loadtest_users.py --dry-run
```

**Example output:**
```
============================================================
  Load Test User Cleanup
============================================================

📊 Found 3 load test users to delete

🔍 DRY RUN - Would delete the following users:
  1. loadtest_user_2_1764086513
  2. loadtest_user_17_1764086513
  3. loadtest_user_34_1764086513

💡 Run without --dry-run to actually delete these users
============================================================
```

### Step 2: Delete test users

```bash
python3 cleanup_loadtest_users.py
```

**Confirmation prompt:**
```
⚠️  This will permanently delete these users and their data!

Continue? (yes/no):
```

Type `yes` and press Enter.

**Success:**
```
✅ Successfully deleted 3 load test users
```

---

## Why Test Users Remain

The load test creates real user accounts to test the registration endpoint. These users are not automatically deleted because:

1. **Realistic testing:** Tests real database writes and user creation
2. **Post-test analysis:** You may want to inspect test user data
3. **Safety:** Prevents accidental deletion of real users

---

## Automated Cleanup

If you want to automatically clean up after every load test:

```bash
# Run load test followed by automatic cleanup
python3 load_test.py --users 100 --duration 60 && python3 cleanup_loadtest_users.py <<< "yes"
```

Or create an alias in your `~/.bashrc`:

```bash
alias loadtest='python3 load_test.py "$@" && python3 cleanup_loadtest_users.py <<< "yes"'
```

Then use:
```bash
loadtest --users 100 --duration 60
```

---

## Manual Cleanup (SQL)

If you prefer SQL:

### Using Python
```bash
python3 -c "
from backend.database import async_session_maker, User
from sqlalchemy import delete
import asyncio

async def cleanup():
    async with async_session_maker() as db:
        await db.execute(delete(User).where(User.user_id.like('loadtest_user_%')))
        await db.commit()
        print('Cleanup complete')

asyncio.run(cleanup())
"
```

### Using SQLite CLI (if installed)
```bash
sqlite3 backend/group_chat.db "DELETE FROM users WHERE user_id LIKE 'loadtest_user_%';"
```

---

## Verifying Cleanup

Check if any test users remain:

```bash
python3 cleanup_loadtest_users.py --dry-run
```

Expected output if clean:
```
✅ No load test users found in database
```

---

## Best Practices

1. **Clean after each test:** Don't let test users accumulate
2. **Use dry-run first:** Always preview what will be deleted
3. **Check production:** Never run load tests on production database
4. **Regular cleanup:** Clean up before deploying to production

---

## Troubleshooting

### "No module named 'backend'"
**Solution:** Run from project root:
```bash
cd /home/wschay/ai-group-chat-streamlit
python3 cleanup_loadtest_users.py --dry-run
```

### "Database is locked"
**Solution:** Stop the backend server first:
```bash
# Stop backend (Ctrl+C in backend terminal)
python3 cleanup_loadtest_users.py
# Restart backend
```

### Script doesn't find users
**Solution:** Check database location:
```bash
# The script uses backend/group_chat.db by default
# Make sure you're in the project root directory
pwd  # Should show: /home/wschay/ai-group-chat-streamlit
```

---

## Related Files

- `load_test.py` - Load testing script that creates test users
- `cleanup_loadtest_users.py` - Cleanup script (this tool)
- `backend/group_chat.db` - SQLite database (development)

---

## Summary

**To clean up load test users:**

```bash
# 1. Preview
python3 cleanup_loadtest_users.py --dry-run

# 2. Delete
python3 cleanup_loadtest_users.py

# 3. Confirm by typing 'yes'
```

Done! 🎉

