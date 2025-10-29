#!/bin/bash
# Install Argon2 - a better password hashing library than bcrypt

echo "Installing Argon2 (replacing bcrypt)..."
echo "========================================"
echo ""
echo "Why Argon2?"
echo "  ✅ No password length limits (bcrypt has 72-byte limit)"
echo "  ✅ More secure (winner of Password Hashing Competition 2015)"
echo "  ✅ Memory-hard (resistant to GPU cracking)"
echo "  ✅ No compatibility issues"
echo ""

# Uninstall old bcrypt-related packages
pip uninstall -y bcrypt passlib 2>/dev/null

# Install Argon2 with passlib
pip install 'passlib[argon2]' argon2-cffi

echo ""
echo "✅ Argon2 installed successfully!"
echo ""
echo "Now you can use ANY password length you want!"
echo ""
echo "Create admin with:"
echo "  python create_admin.py"
echo ""
echo "Or quick one-liner:"
echo '  python -c "'
echo 'import asyncio, sys'
echo "sys.path.insert(0, 'backend')"
echo 'from backend.database import async_session_maker'
echo 'from backend.auth import create_admin_user'
echo ''
echo 'async def main():'
echo '    async with async_session_maker() as db:'
echo "        admin = await create_admin_user(db, 'admin', 'YourPasswordHere')"
echo '        print(f\"✅ Admin created: {admin.user_id}\")'
echo ''
echo 'asyncio.run(main())'
echo '"'

