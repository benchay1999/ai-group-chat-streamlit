#!/usr/bin/env python3
"""
Simple script to create an admin user.
Handles password length validation automatically.

Usage:
    python create_admin.py

The script will prompt for user_id and password.
"""

import asyncio
import sys
import getpass

# Add backend to path so we can import modules
sys.path.insert(0, 'backend')

from database import async_session_maker
from auth import create_admin_user

async def main():
    print("=" * 60)
    print("Admin User Creation Tool")
    print("=" * 60)
    print()
    print("Note: No password length limits with Argon2! Use any length.")
    print()
    
    # Get user input
    user_id = input("Enter admin user ID: ").strip()
    if not user_id:
        print("❌ User ID cannot be empty")
        return
    
    password = getpass.getpass("Enter admin password: ").strip()
    if not password:
        print("❌ Password cannot be empty")
        return
    
    # Just show password strength
    password_length = len(password)
    if password_length < 12:
        print(f"\n⚠️  Warning: Password is only {password_length} characters")
        print("    Recommended: 12+ characters for better security.")
        confirm = input("    Continue anyway? (y/n): ").strip().lower()
        if confirm != 'y':
            print("❌ Cancelled")
            return
    
    # Confirm password
    password_confirm = getpass.getpass("Confirm admin password: ").strip()
    if password != password_confirm:
        print("❌ Passwords do not match")
        return
    
    # Create admin user
    print()
    print("Creating admin user...")
    
    try:
        async with async_session_maker() as db:
            admin = await create_admin_user(db, user_id, password)
            print()
            print("=" * 60)
            print("✅ Admin user created successfully!")
            print(f"   User ID: {admin.user_id}")
            print(f"   Role: {admin.role.value}")
            print("=" * 60)
            print()
            print("You can now login at: http://localhost:5173/login")
    
    except Exception as e:
        print()
        print("=" * 60)
        print(f"❌ Error creating admin user: {e}")
        print("=" * 60)
        print()
        print("Troubleshooting:")
        print("1. Make sure the backend server is NOT running")
        print("2. Check that DATABASE_URL is set in .env")
        print("3. Verify the database file exists or can be created")
        print("4. Check if user_id already exists (try a different one)")

if __name__ == "__main__":
    asyncio.run(main())

