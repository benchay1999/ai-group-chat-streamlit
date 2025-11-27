# Monitoring & Alerting Setup Guide

**Purpose:** Set up production monitoring and alerting for 100-120 concurrent users  
**Time Required:** 30-60 minutes  
**Difficulty:** Beginner-friendly

---

## Why Monitoring Matters

Without monitoring, you won't know:
- When users can't log in (authentication failures)
- When attackers are trying to brute-force passwords
- When the database is overloaded
- When MTurk payments fail
- When the server crashes

**Result:** Poor user experience and potential security incidents

---

## Option 1: Sentry (Recommended - Free Tier Available)

### Features
- ✅ Error tracking and crash reports
- ✅ Performance monitoring
- ✅ Real-time alerts via email/Slack
- ✅ User context (which user experienced error)
- ✅ Free tier: 5,000 errors/month

### Setup (10 minutes)

**Step 1: Sign Up**
1. Go to https://sentry.io
2. Create free account
3. Create new project (select "Python" → "FastAPI")
4. Copy your DSN (looks like: `https://abc123@o123.ingest.sentry.io/456`)

**Step 2: Install Sentry SDK**
```bash
cd /home/wschay/ai-group-chat-streamlit
pip install sentry-sdk[fastapi]

# Add to requirements.txt
echo "sentry-sdk[fastapi]>=1.40.0" >> backend/requirements.txt
```

**Step 3: Configure Backend**

Add to `backend/main.py` (at the top, after imports):

```python
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

# Initialize Sentry (only in production)
SENTRY_DSN = os.getenv('SENTRY_DSN')
if SENTRY_DSN:
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[
            FastApiIntegration(),
            SqlalchemyIntegration(),
        ],
        traces_sample_rate=0.1,  # 10% of transactions for performance monitoring
        profiles_sample_rate=0.1,  # 10% of transactions for profiling
        environment=os.getenv('ENVIRONMENT', 'development'),
        release=os.getenv('GIT_COMMIT', 'unknown'),
    )
    print(f"✅ Sentry initialized for {os.getenv('ENVIRONMENT', 'development')}")
```

**Step 4: Add to .env**
```bash
# In your .env file
SENTRY_DSN=https://your-actual-dsn@o123.ingest.sentry.io/456
```

**Step 5: Test**
```python
# Add a test endpoint to backend/main.py
@app.get("/test-sentry")
async def test_sentry():
    """Test endpoint to verify Sentry integration"""
    1 / 0  # Intentional error
```

Visit `http://localhost:8000/test-sentry` and check Sentry dashboard for error.

**Step 6: Configure Alerts**
1. Go to Sentry → Settings → Alerts
2. Create alert: "High Error Rate"
   - Condition: >10 errors in 1 hour
   - Action: Email or Slack notification
3. Create alert: "New Issue"
   - Condition: First occurrence of new error
   - Action: Email notification

---

## Option 2: Custom Logging + Email Alerts (Free)

### Features
- ✅ Completely free
- ✅ No external dependencies
- ✅ Simple email alerts
- ❌ No fancy dashboard
- ❌ Manual log review required

### Setup (15 minutes)

**Step 1: Create Alert System**

Create `backend/alert_system.py`:

```python
"""
Simple email alert system for critical events.
"""
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
from datetime import datetime
from collections import defaultdict
import time

# Email configuration
ALERT_EMAIL_FROM = os.getenv('ALERT_EMAIL_FROM', 'alerts@yourapp.com')
ALERT_EMAIL_TO = os.getenv('ALERT_EMAIL_TO', 'admin@yourapp.com')
ALERT_EMAIL_PASSWORD = os.getenv('ALERT_EMAIL_PASSWORD')
SMTP_HOST = os.getenv('SMTP_HOST', 'smtp.gmail.com')
SMTP_PORT = int(os.getenv('SMTP_PORT', '587'))

# Alert throttling (don't spam)
alert_last_sent = defaultdict(float)
ALERT_COOLDOWN = 3600  # 1 hour between same alert type


def send_alert(subject: str, message: str, alert_type: str = "general"):
    """
    Send email alert (throttled to prevent spam).
    """
    # Check cooldown
    now = time.time()
    if now - alert_last_sent[alert_type] < ALERT_COOLDOWN:
        print(f"⏳ Alert throttled: {alert_type} (last sent {int((now - alert_last_sent[alert_type])/60)} min ago)")
        return
    
    if not ALERT_EMAIL_PASSWORD:
        print(f"⚠️  Cannot send alert: ALERT_EMAIL_PASSWORD not configured")
        print(f"   {subject}: {message}")
        return
    
    try:
        # Create email
        msg = MIMEMultipart()
        msg['From'] = ALERT_EMAIL_FROM
        msg['To'] = ALERT_EMAIL_TO
        msg['Subject'] = f"[ALERT] {subject}"
        
        body = f"""
Production Alert - AI Group Chat Application

Time: {datetime.utcnow().isoformat()}
Type: {alert_type}
Environment: {os.getenv('ENVIRONMENT', 'unknown')}

{message}

---
This is an automated alert. Please investigate immediately.
        """
        
        msg.attach(MIMEText(body, 'plain'))
        
        # Send email
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(ALERT_EMAIL_FROM, ALERT_EMAIL_PASSWORD)
            server.send_message(msg)
        
        alert_last_sent[alert_type] = now
        print(f"📧 Alert sent: {subject}")
        
    except Exception as e:
        print(f"❌ Failed to send alert: {e}")


# Alert wrappers for specific events
def alert_high_login_failures(count: int, window_minutes: int):
    """Alert on high login failure rate."""
    send_alert(
        subject=f"High Login Failure Rate: {count} failures",
        message=f"{count} failed login attempts in the last {window_minutes} minutes. Possible brute-force attack.",
        alert_type="login_failures"
    )


def alert_high_rate_limit_violations(count: int):
    """Alert on high rate limit violation rate."""
    send_alert(
        subject=f"High Rate Limit Violations: {count} violations",
        message=f"{count} rate limit violations in the last hour. Possible DoS attack or bug.",
        alert_type="rate_limits"
    )


def alert_database_connection_error(error: str):
    """Alert on database connection failure."""
    send_alert(
        subject="Database Connection Failure",
        message=f"Cannot connect to database. Error: {error}\n\nApplication may be down!",
        alert_type="database"
    )


def alert_mturk_payment_failure(user_id: str, error: str):
    """Alert on MTurk payment failure."""
    send_alert(
        subject=f"MTurk Payment Failure for {user_id}",
        message=f"Failed to process payment for user {user_id}. Error: {error}",
        alert_type="mturk_payment"
    )
```

**Step 2: Integrate with Existing Security Monitor**

Update `backend/security_monitor.py`:

```python
# Add at the top
from .alert_system import alert_high_login_failures, alert_high_rate_limit_violations

# In SecurityMonitor class, add alert triggers:
def check_and_alert_failures(self):
    """Check for concerning patterns and alert."""
    # Count recent failures
    now = time.time()
    recent_failures = sum(
        1 for timestamp in self.failed_logins
        if now - timestamp < 3600  # Last hour
    )
    
    if recent_failures > 50:  # More than 50 failed logins per hour
        alert_high_login_failures(recent_failures, 60)
    
    # Count rate limit violations
    recent_violations = sum(
        1 for timestamp in self.rate_limit_violations
        if now - timestamp < 3600
    )
    
    if recent_violations > 100:  # More than 100 violations per hour
        alert_high_rate_limit_violations(recent_violations)
```

**Step 3: Configure Email Credentials**

For Gmail (free):
1. Enable 2-factor authentication: https://myaccount.google.com/security
2. Generate app password: https://myaccount.google.com/apppasswords
3. Add to `.env`:

```bash
ALERT_EMAIL_FROM=your-email@gmail.com
ALERT_EMAIL_TO=admin@yourcompany.com
ALERT_EMAIL_PASSWORD=your-app-password-here
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
```

**Step 4: Test**
```python
# In Python console
from backend.alert_system import send_alert
send_alert("Test Alert", "This is a test", "test")
```

---

## Option 3: Uptime Monitoring (Free - Supplement to Above)

### UptimeRobot (Recommended)

**Features:**
- ✅ Monitors if your app is up/down
- ✅ Email/SMS/Slack alerts on downtime
- ✅ Free tier: 50 monitors, 5-minute intervals
- ✅ Public status page

**Setup (5 minutes):**
1. Go to https://uptimerobot.com
2. Sign up for free account
3. Add new monitor:
   - Type: HTTP(s)
   - URL: `https://your-backend-url.com/health`
   - Interval: 5 minutes
   - Alert contacts: Your email
4. Test by stopping your backend (should get alert in 5 min)

**Health Check Endpoint:**

Ensure your backend has a health check (already implemented):
```python
@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}
```

---

## Monitoring Checklist

### Initial Setup
- [ ] Choose monitoring solution (Sentry recommended)
- [ ] Install and configure monitoring SDK
- [ ] Test error reporting (trigger test error)
- [ ] Configure email/Slack alerts
- [ ] Set up uptime monitoring (UptimeRobot)

### Alert Configuration
- [ ] High login failure rate (>10/hour)
- [ ] High rate limit violations (>50/hour)
- [ ] Database connection failures (immediate)
- [ ] MTurk payment failures (immediate)
- [ ] Application downtime (5 min)
- [ ] High error rate (>5% requests)

### Testing
- [ ] Test error tracking (trigger test error)
- [ ] Test email alerts (send test alert)
- [ ] Test uptime monitoring (stop server)
- [ ] Verify alerts arrive within expected time

---

## Monitoring Best Practices

### 1. Set Appropriate Thresholds
- **Too sensitive:** Alert fatigue, ignored alerts
- **Too lenient:** Miss critical issues
- **Start conservative:** Lower thresholds initially, adjust based on false positives

### 2. Alert Routing
- **Critical (page immediately):** Database down, payment failures
- **Warning (email/Slack):** High error rate, rate limit violations
- **Info (log only):** Individual failed logins, expected errors

### 3. Regular Review
- Check error dashboard weekly
- Review alert effectiveness monthly
- Update thresholds based on actual traffic

### 4. Incident Response
1. Acknowledge alert
2. Check monitoring dashboard
3. Review recent logs
4. Identify root cause
5. Implement fix or rollback
6. Document in post-mortem

---

## What to Monitor

### Application Health
- ✅ HTTP 5xx error rate
- ✅ Response time (p50, p95, p99)
- ✅ Request rate (requests/second)
- ✅ WebSocket connections (active count)

### Security
- ✅ Failed login attempts
- ✅ Rate limit violations
- ✅ Invalid JWT tokens
- ✅ SQL injection attempts (blocked by validation)

### Database
- ✅ Connection pool usage (should be <80%)
- ✅ Query performance (slow queries >1s)
- ✅ Database connection errors
- ✅ Lock wait timeouts (if using SQLite)

### Business Metrics
- ✅ User registrations
- ✅ Game sessions completed
- ✅ Cashout requests
- ✅ MTurk payments processed

---

## Cost Comparison

| Solution | Free Tier | Paid Tier | Recommended For |
|----------|-----------|-----------|-----------------|
| Sentry | 5K errors/month | $26/month | Best all-around |
| Custom Email | Unlimited | Free | Budget-conscious |
| UptimeRobot | 50 monitors | $7/month | Everyone (uptime) |
| LogDNA/Mezmo | 500MB/day | $15/month | Large-scale logs |

**Recommended Setup for 100-120 users:**
- Sentry (free tier) for errors and performance
- UptimeRobot (free tier) for uptime
- **Total cost: $0/month**

---

## Quick Start (5 Minutes)

```bash
# 1. Install Sentry
pip install sentry-sdk[fastapi]

# 2. Sign up at sentry.io and get DSN

# 3. Add to .env
echo "SENTRY_DSN=your-dsn-here" >> .env

# 4. Add to backend/main.py (after imports):
"""
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration

if os.getenv('SENTRY_DSN'):
    sentry_sdk.init(
        dsn=os.getenv('SENTRY_DSN'),
        integrations=[FastApiIntegration()],
        traces_sample_rate=0.1,
    )
"""

# 5. Restart backend
# 6. Trigger test error: visit /test-sentry
# 7. Check Sentry dashboard

# Done! You're monitoring production.
```

---

## Next Steps

After initial setup:
1. Monitor error dashboard daily for first week
2. Adjust alert thresholds based on actual patterns
3. Set up more specific alerts (e.g., cashout failures)
4. Create incident response runbook
5. Train team on monitoring tools

**Remember:** Monitoring is not "set and forget" - regularly review and improve!

