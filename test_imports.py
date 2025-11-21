import sys
import os
from pathlib import Path

# Add src to path
src_path = str(Path(__file__).resolve().parent / "src")
sys.path.append(src_path)

print(f"Testing imports with path: {src_path}")

try:
    print("Importing database.supabase_client...")
    import database.supabase_client
    print("✅ database.supabase_client imported successfully")
except Exception as e:
    print(f"❌ Failed to import database.supabase_client: {e}")

try:
    print("Importing project.caption...")
    import project.caption
    print("✅ project.caption imported successfully")
except Exception as e:
    print(f"❌ Failed to import project.caption: {e}")

try:
    print("Importing project.scheduler...")
    import project.scheduler
    print("✅ project.scheduler imported successfully")
except Exception as e:
    print(f"❌ Failed to import project.scheduler: {e}")

try:
    print("Importing project.poster...")
    import project.poster
    print("✅ project.poster imported successfully")
except Exception as e:
    print(f"❌ Failed to import project.poster: {e}")

try:
    print("Importing project.bot_central...")
    # Mocking telegram dependencies might be needed if not installed, but let's try direct import first
    import project.bot_central
    print("✅ project.bot_central imported successfully")
except Exception as e:
    print(f"❌ Failed to import project.bot_central: {e}")
