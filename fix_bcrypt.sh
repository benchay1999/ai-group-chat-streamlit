#!/bin/bash
# Fix bcrypt compatibility issue

echo "Fixing bcrypt and passlib compatibility..."
echo "=========================================="

# Option 1: Upgrade both to latest compatible versions
pip install --upgrade 'passlib[bcrypt]>=1.7.4' 'bcrypt>=4.0.0'

echo ""
echo "✅ Libraries updated!"
echo ""
echo "Now try creating admin again with:"
echo "  python create_admin.py"
echo ""
echo "Or use this command with a SHORT password:"
echo "  python -c \""
echo "import asyncio, sys"
echo "sys.path.insert(0, 'backend')"
echo "from backend.database import async_session_maker"
echo "from backend.auth import create_admin_user"
echo ""
echo "async def main():"
echo "    async with async_session_maker() as db:"
echo "        admin = await create_admin_user(db, 'admin', 'Admin123!')"
echo "        print(f'✅ Admin created: {admin.user_id}')"
echo ""
echo "asyncio.run(main())"
echo "\""

