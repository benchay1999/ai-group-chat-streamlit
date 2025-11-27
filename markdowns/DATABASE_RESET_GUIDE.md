# Database Reset Guide

## Purpose

This guide explains how to reset all transactional data (games, transactions, earnings) while preserving user accounts for a fresh start.

## What Gets Reset

### DELETED (Permanently Removed) ❌
- ✅ **All game sessions** (`sessions` table)
- ✅ **All session player mappings** (`session_players` table)
- ✅ **All AI agent usage records** (`ai_agent_usage` table)
- ✅ **All cashout transactions** (`cashout_transactions` table)

### RESET TO ZERO 🔄
User accounts are preserved, but statistics are reset:
- ✅ `gem_balance` → 0
- ✅ `total_gems_earned` → 0
- ✅ `total_gems_cashed_out` → 0
- ✅ `total_games` → 0
- ✅ `total_wins` → 0
- ✅ `total_points` → 0
- ✅ `current_streak` → 0
- ✅ `longest_streak` → 0
- ✅ `level` → 1
- ✅ `last_played_at` → NULL

### PRESERVED (Kept Intact) ✅
- ✅ User accounts (`user_id`, `password_hash`)
- ✅ User roles (`admin` or `user`)
- ✅ MTurk Worker IDs
- ✅ User creation dates

## How to Run the Reset

### Step 1: Navigate to Backend Directory

```bash
cd /home/wschay/ai-group-chat-streamlit/backend
```

### Step 2: Activate Conda Environment

```bash
bash & conda activate group-chat
```

### Step 3: Run the Reset Script

```bash
python reset_transactional_data.py
```

### Step 4: Confirm the Reset

The script will show you:
1. Current database statistics
2. What will be deleted/reset
3. What will be preserved

You **MUST** type `RESET` (all caps) to confirm.

```
⚠️  Are you ABSOLUTELY SURE? Type 'RESET' to continue: RESET
```

### Step 5: Verify the Results

The script will automatically verify that:
- All transactional tables are empty
- User accounts are preserved
- User stats are reset to 0

## Example Output

```
================================================================================
DATABASE RESET SCRIPT
================================================================================

⚠️  This script will clear all game data but keep user accounts.
Make sure you understand what this does before proceeding!

🔧 Database Reset Tool
================================================================================

📊 Collecting current database statistics...

Current database state:
  Users: 5
  Sessions: 127
  Session Players: 254
  AI Agent Usage: 381
  Cashout Transactions: 12

================================================================================
⚠️  DATABASE RESET - TRANSACTIONAL DATA
================================================================================

This will DELETE:
  ❌ All game sessions
  ❌ All session player mappings
  ❌ All AI agent usage records
  ❌ All cashout transactions

This will RESET:
  🔄 User gem balances → 0
  🔄 User total gems earned → 0
  🔄 User total gems cashed out → 0
  🔄 User game stats → 0

This will PRESERVE:
  ✅ User accounts (user_id, passwords)
  ✅ User roles (admin/user)
  ✅ MTurk Worker IDs
  ✅ User creation dates

================================================================================

⚠️  Are you ABSOLUTELY SURE? Type 'RESET' to continue: RESET

🔄 Starting reset process...

1️⃣  Deleting cashout transactions...
   ✅ Deleted 12 cashout transaction(s)

2️⃣  Deleting AI agent usage records...
   ✅ Deleted 381 AI agent usage record(s)

3️⃣  Deleting session player mappings...
   ✅ Deleted 254 session player mapping(s)

4️⃣  Deleting game sessions...
   ✅ Deleted 127 game session(s)

5️⃣  Resetting user statistics...
   🔄 Reset stats for user: alice
   🔄 Reset stats for user: bob
   🔄 Reset stats for user: charlie
   🔄 Reset stats for user: dave
   🔄 Reset stats for user: admin

   ✅ Reset 5 user account(s)

================================================================================
✅ RESET COMPLETE
================================================================================

📊 Verifying final database state...

Final database state:
  Users: 5 (preserved)
  Sessions: 0 (should be 0)
  Session Players: 0 (should be 0)
  AI Agent Usage: 0 (should be 0)
  Cashout Transactions: 0 (should be 0)

✅ Verification passed! All transactional data cleared.

🎉 Database reset successful!

User accounts preserved:
  ✅ alice (Role: user, MTurk: A1BCDEFG2HIJK)
  ✅ bob (Role: user, MTurk: A9ZYXWVU8TQRS)
  ✅ charlie (Role: user, MTurk: Not set)
  ✅ dave (Role: user, MTurk: Not set)
  ✅ admin (Role: admin, MTurk: Not set)

✅ All done! The database has been reset.
   User accounts are preserved and ready for a fresh start.
```

## Safety Features

1. **Confirmation Required**: Must type `RESET` to proceed
2. **Statistics First**: Shows what will be affected before proceeding
3. **Verification**: Automatically verifies the reset was successful
4. **Rollback on Error**: If anything fails, changes are rolled back
5. **Detailed Logging**: Every step is logged for transparency

## Common Use Cases

### 1. Fresh MTurk Testing Round
Reset all previous test data to start clean MTurk experiments.

### 2. After Development Testing
Clear test data before going to production.

### 3. New Study/Experiment
Start with clean slate for a new research study.

### 4. Fix Data Corruption
Clear corrupted data while keeping user accounts.

## What Users Will Experience

After the reset:
- ✅ Users can still log in with their existing passwords
- ✅ Admin accounts retain admin privileges
- ✅ MTurk Worker IDs remain linked
- ❌ Dashboard shows 0 gems, 0 games played
- ❌ No session history
- ❌ No cashout history
- ❌ Gem balance is 0

## Manual Reset (Alternative Method)

If you prefer manual SQL commands:

```sql
-- Delete transactional data
DELETE FROM cashout_transactions;
DELETE FROM ai_agent_usage;
DELETE FROM session_players;
DELETE FROM sessions;

-- Reset user stats
UPDATE users SET
    gem_balance = 0,
    total_gems_earned = 0,
    total_gems_cashed_out = 0,
    total_games = 0,
    total_wins = 0,
    total_points = 0,
    current_streak = 0,
    longest_streak = 0,
    level = 1,
    last_played_at = NULL;
```

## Backup (Optional)

If you want to create a backup before resetting:

```bash
# For SQLite
cp backend/group_chat.db backend/group_chat.db.backup

# For PostgreSQL
pg_dump database_name > backup.sql
```

## Restore from Backup

```bash
# For SQLite
cp backend/group_chat.db.backup backend/group_chat.db

# For PostgreSQL
psql database_name < backup.sql
```

## Troubleshooting

### Error: "Foreign key constraint failed"
**Solution**: The script deletes in the correct order (children first, then parents). If this error occurs, check if there are custom constraints.

### Error: "Permission denied"
**Solution**: Make sure the script is executable:
```bash
chmod +x backend/reset_transactional_data.py
```

### Error: "Database locked" (SQLite)
**Solution**: Stop the backend server first:
```bash
# Stop any running uvicorn processes
pkill -f uvicorn
```

### Script hangs or is slow
**Solution**: This is normal for large databases. Wait for it to complete.

## After Reset Checklist

- [ ] Verify users can still log in
- [ ] Check dashboard shows 0 gems
- [ ] Confirm no session history
- [ ] Test playing a new game
- [ ] Verify gems are credited correctly
- [ ] Restart backend server if needed

## Related Files

- **Reset Script**: `backend/reset_transactional_data.py`
- **Database Models**: `backend/database.py`
- **Migration Scripts**: `backend/alembic/versions/`

## Support

If you encounter issues:
1. Check the error message
2. Verify database is not locked
3. Ensure conda environment is activated
4. Check file permissions
5. Look at backend logs

---

**⚠️  WARNING**: This operation cannot be undone. Make a backup if you're unsure!

