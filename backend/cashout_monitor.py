"""
Cashout Monitor Background Task
Periodically checks for expired cashout codes and returns gems to users.
"""

import asyncio
from datetime import datetime
from typing import Optional
from sqlalchemy import select

from backend.database import CashoutTransaction, CashoutStatus, async_session_maker
from backend.cashout_service import cancel_cashout_transaction
from backend.config import CASHOUT_MONITOR_INTERVAL


class CashoutMonitor:
    """Background task to monitor cashout transactions and handle expirations."""
    
    def __init__(self):
        self.running = False
        self.task: Optional[asyncio.Task] = None
    
    async def start(self):
        """Start the monitoring task."""
        if self.running:
            print("⚠️  Cashout monitor already running")
            return
        
        self.running = True
        self.task = asyncio.create_task(self._monitor_loop())
        print(f"✅ Cashout monitor started (checking every {CASHOUT_MONITOR_INTERVAL}s)")
    
    async def stop(self):
        """Stop the monitoring task."""
        if not self.running:
            return
        
        self.running = False
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
        
        print("✅ Cashout monitor stopped")
    
    async def _monitor_loop(self):
        """Main monitoring loop."""
        while self.running:
            try:
                await self._check_expired_codes()
            except Exception as e:
                print(f"❌ Error in cashout monitor: {e}")
            
            # Wait before next check
            await asyncio.sleep(CASHOUT_MONITOR_INTERVAL)
    
    async def _check_expired_codes(self):
        """Check for expired redemption codes and return gems to users."""
        async with async_session_maker() as db:
            # Get all pending transactions
            query = select(CashoutTransaction).where(
                CashoutTransaction.status == CashoutStatus.PENDING
            )
            result = await db.execute(query)
            pending_transactions = result.scalars().all()
            
            if not pending_transactions:
                return  # Nothing to process
            
            expired_count = 0
            
            for transaction in pending_transactions:
                try:
                    # Check if code has expired
                    if transaction.expires_at and datetime.utcnow() > transaction.expires_at:
                        print(f"⏰ Redemption code {transaction.redemption_code[:16]}... expired, returning gems to user")
                        await cancel_cashout_transaction(
                            transaction=transaction,
                            db=db,
                            reason="Redemption code expired after 7 days - gems returned to balance"
                        )
                        expired_count += 1
                
                except Exception as e:
                    print(f"❌ Error processing transaction {transaction.id}: {e}")
                    continue
            
            if expired_count > 0:
                print(f"🔄 Processed {expired_count} expired redemption code(s)")


# Global monitor instance
_cashout_monitor: Optional[CashoutMonitor] = None


def get_cashout_monitor() -> CashoutMonitor:
    """Get or create the global cashout monitor instance."""
    global _cashout_monitor
    if _cashout_monitor is None:
        _cashout_monitor = CashoutMonitor()
    return _cashout_monitor


async def start_cashout_monitor():
    """Start the cashout monitor (called on app startup)."""
    monitor = get_cashout_monitor()
    await monitor.start()


async def stop_cashout_monitor():
    """Stop the cashout monitor (called on app shutdown)."""
    monitor = get_cashout_monitor()
    await monitor.stop()
