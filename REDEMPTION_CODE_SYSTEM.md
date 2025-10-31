# 🔑 MTurk Redemption Code System

## Overview

The redemption code system allows players to cash out their gems using MTurk without creating individual HITs per transaction. Instead, a single **standing HIT** is used for all cashouts, and players submit unique redemption codes to claim their payments.

## How It Works

### For Players:
1. **Earn Gems**: Play the game and accumulate gems (1000 gems = $1.00 USD)
2. **Request Cashout**: Click "Cash Out" button and enter desired amount (minimum $2.00)
3. **Get Redemption Code**: System generates a unique 64-character code
4. **Submit to MTurk**: Log into MTurk, find the "ChatGame Payout" HIT, paste code, submit
5. **Instant Payment**: Backend validates code and approves assignment immediately

### For System:
1. **Standing HIT**: One permanent HIT on MTurk (never expires, auto-approved)
2. **Code Generation**: When player requests cashout, system generates unique hash
3. **Gem Deduction**: Gems immediately deducted from player's wallet (held in escrow)
4. **Code Validation**: When code is submitted, system validates and approves payment
5. **Auto-Refund**: If code expires unused (7 days), gems automatically returned to wallet

## Setup Instructions

### 1. Create the Standing MTurk HIT

You need to create **one permanent HIT** on MTurk that all players will use:

#### Using MTurk Web Interface:
1. Go to https://requester.mturk.com (production) or https://requester.sandbox.mturk.com (sandbox)
2. Create New Project → Survey Link
3. **Project Details:**
   - Project Name: `ChatGame Cashout System`
   - Title: `ChatGame - Redeem Your Earnings (Instant Payment)`
   - Description: `Redeem a code from the ChatGame to receive your earned payment. Instant approval.`
   - Keywords: `games, redemption, instant payment, bonus`
4. **Reward & Time:**
   - Reward per response: `$0.01` (minimum, actual payment varies by code)
   - Time per response: `60 minutes`
   - Auto-approve time: `1 hour`
5. **Worker Requirements:**
   - None (all workers should be able to see it)
   - Or restrict to specific regions if needed
6. **Survey Link:**
   - Use your frontend URL: `https://your-domain.com/cashout-confirm`
   - Frame height: `600` (or auto)
7. Publish HIT and copy the **HIT ID** (format: `3XXXXXXXXXXXXXXXXXXXXXX`)

#### Using MTurk API (Alternative):
```python
import boto3

mturk = boto3.client('mturk',
   region_name='us-east-1',
   endpoint_url='https://mturk-requester.us-east-1.amazonaws.com'  # Production
   # endpoint_url='https://mturk-requester-sandbox.us-east-1.amazonaws.com'  # Sandbox
)

question = """
<ExternalQuestion xmlns="http://mechanicalturk.amazonaws.com/AWSMechanicalTurkDataSchemas/2006-07-14/ExternalQuestion.xsd">
  <ExternalURL>https://your-domain.com/cashout-confirm</ExternalURL>
  <FrameHeight>600</FrameHeight>
</ExternalQuestion>
"""

response = mturk.create_hit(
    Title='ChatGame - Redeem Your Earnings (Instant Payment)',
    Description='Redeem a code from the ChatGame to receive your earned payment. Instant approval.',
    Keywords='games, redemption, instant payment',
    Reward='0.01',
    MaxAssignments=999999,  # Large number for standing HIT
    LifetimeInSeconds=31536000,  # 1 year
    AssignmentDurationInSeconds=3600,  # 1 hour
    AutoApprovalDelayInSeconds=3600,  # Auto-approve after 1 hour
    Question=question
)

hit_id = response['HIT']['HITId']
print(f"Standing HIT created: {hit_id}")
```

### 2. Configure Backend

Add the HIT ID to your `.env` file:

```bash
# REQUIRED: Your standing MTurk HIT ID
CASHOUT_HIT_ID=3XXXXXXXXXXXXXXXXXXXXXX

# Optional: Adjust these if needed
MINIMUM_CASHOUT_AMOUNT=2.00
CASHOUT_MONITOR_INTERVAL=3600  # Check expired codes every hour
```

### 3. Run Database Migration

Apply the gem economy schema changes:

```bash
cd backend
alembic upgrade head
```

### 4. (Optional) Migrate Existing Earnings

If you have existing users with earnings in sessions, run the migration script:

```bash
python backend/migrate_to_gems.py
```

This converts all `calculated_earnings` from sessions into gems.

### 5. Test the System

#### In Sandbox:
1. Set `MTURK_ENVIRONMENT=sandbox` in `.env`
2. Create a sandbox HIT as above
3. Test the full flow with a sandbox Worker ID

#### Verification Checklist:
- [ ] Backend starts without CASHOUT_HIT_ID warning
- [ ] Player can view gem balance at `/wallet`
- [ ] Player can set MTurk Worker ID at `/profile`
- [ ] Player can request cashout (gets redemption code)
- [ ] Gems are deducted immediately
- [ ] Code can be submitted to MTurk HIT
- [ ] Payment is approved instantly
- [ ] Transaction shows as "completed" in history
- [ ] Expired codes return gems to wallet

## API Endpoints

### Wallet Balance
```http
GET /api/wallet/balance
Authorization: Bearer {token}
```

Response:
```json
{
  "gem_balance": 5000,
  "usd_equivalent": 5.00,
  "total_gems_earned": 10000,
  "total_gems_cashed_out": 5000,
  "has_worker_id": true
}
```

### Request Cashout
```http
POST /api/wallet/cashout
Authorization: Bearer {token}
Content-Type: application/json

{
  "amount_usd": 2.50
}
```

Response:
```json
{
  "success": true,
  "transaction_id": "uuid",
  "amount_usd": 2.50,
  "amount_gems": 2500,
  "redemption_code": "abc123...",
  "expires_at": "2025-11-07T12:00:00Z",
  "hit_url": "https://worker.mturk.com/mturk/preview?groupId=...",
  "instructions": "..."
}
```

### Redeem Code (MTurk HIT)
```http
POST /api/wallet/redeem
Content-Type: application/json

{
  "redemption_code": "abc123...",
  "worker_id": "A12345...",
  "assignment_id": "...",
  "hit_id": "..."
}
```

Response:
```json
{
  "success": true,
  "amount_usd": 2.50,
  "worker_id": "A12345..."
}
```

### Cashout History
```http
GET /api/wallet/cashout-history?limit=10
Authorization: Bearer {token}
```

Response:
```json
{
  "cashouts": [
    {
      "transaction_id": "uuid",
      "status": "completed",
      "amount_usd": 2.50,
      "amount_gems": 2500,
      "redemption_code": "****abc123",  // Masked for security
      "created_at": "2025-10-31T12:00:00Z",
      "completed_at": "2025-10-31T12:05:00Z"
    }
  ]
}
```

## Security Features

1. **Unique Codes**: Each redemption code is a SHA-256 hash of random bytes + timestamp
2. **Single Use**: Codes can only be redeemed once
3. **Worker ID Validation**: System checks if Worker ID matches user's profile
4. **Expiration**: Codes expire after 7 days if not used
5. **Immediate Deduction**: Gems deducted when code is generated (prevents double-spending)
6. **Auto-Refund**: Expired codes trigger automatic gem refund

## Monitoring

### Cashout Monitor Background Task

The system runs a background task that:
- Checks for expired redemption codes every hour (configurable)
- Automatically refunds gems for expired codes
- Updates transaction status to "failed"

Configure check interval:
```bash
CASHOUT_MONITOR_INTERVAL=3600  # seconds
```

### Admin View

Admins can monitor cashouts at `/admin/analytics`:
- Total cashouts processed
- Average cashout amount
- Failed/expired transactions
- Revenue analytics

## Troubleshooting

### "CASHOUT_HIT_ID not configured" Error

**Problem**: Backend shows warning on startup
**Solution**: Create standing HIT and add HIT ID to `.env`

### "MTurk Worker ID not set" Error

**Problem**: Player tries to cash out without Worker ID
**Solution**: Player must set Worker ID at `/profile` before cashing out

### "Insufficient gem balance" Error

**Problem**: Player doesn't have enough gems
**Solution**: Player needs to play more games to earn gems

### "Invalid redemption code" Error

**Problem**: Code doesn't exist or already used
**Solution**: Check transaction history for valid pending codes

### "Worker ID mismatch" Error

**Problem**: Code was redeemed by different Worker ID
**Solution**: Ensure correct Worker ID in profile settings

### Gems Not Refunded After Expiration

**Problem**: Cashout monitor not running
**Solution**: Check backend logs, restart cashout monitor service

## Cost Estimation

MTurk fees (as of 2024):
- **20% fee** on all payments under $10
- **40% fee** on all payments $10 and above
- **Standing HIT**: Minimal cost ($0.01 × unused assignments)

Example:
- Player cashes out $2.50
- MTurk charges: $2.50 + 20% = $3.00 total
- Your cost: $0.50 (20% fee)

**Optimize costs:**
- Set minimum cashout to $5-10 to reduce percentage fees
- Encourage players to accumulate more before cashing out

## Future Enhancements

Ideas for improvement:
- [ ] Bulk payments (combine multiple small cashouts)
- [ ] Alternative payment methods (PayPal, Stripe)
- [ ] Cashout schedules (weekly/monthly auto-cashout)
- [ ] Referral bonuses (earn gems by inviting friends)
- [ ] Premium memberships (better gem rates)
- [ ] In-game marketplace (spend gems on items/upgrades)

## See Also

- [GEM_ECONOMY_IMPLEMENTATION.md](./GEM_ECONOMY_IMPLEMENTATION.md) - Detailed implementation guide
- [README.md](./README.md) - Project overview and setup
- [MTURK_API_SETUP.md](./MTURK_API_SETUP.md) - MTurk API configuration
