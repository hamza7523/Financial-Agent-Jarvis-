import os
import sys
import shutil
from pathlib import Path

print("=== Cache Configuration Test ===\n")

# Create cache directory on E drive
cache_dir = Path("E:\\Jarvis\\.cache")
cache_dir.mkdir(parents=True, exist_ok=True)

# Set environment variables
os.environ["CHROMA_CACHE_DIR"] = str(cache_dir / "chroma")
os.environ["HF_HOME"] = str(cache_dir / "huggingface")
os.environ["TRANSFORMERS_CACHE"] = str(cache_dir / "transformers")
os.environ["SENTENCE_TRANSFORMERS_HOME"] = str(cache_dir / "sentence_transformers")

print(f"✓ Cache directory created: {cache_dir}")
print(f"  - Chroma cache: {cache_dir / 'chroma'}")
print(f"  - HF Home: {cache_dir / 'huggingface'}")
print(f"  - Transformers cache: {cache_dir / 'transformers'}")

# Clear corrupted C drive cache if it exists
c_drive_cache = Path("C:\\Users\\Pc Planet\\.cache\\chroma")
if c_drive_cache.exists():
    try:
        print(f"\n✓ Clearing corrupted C drive cache...")
        shutil.rmtree(c_drive_cache)
        print(f"  Successfully removed: {c_drive_cache}")
    except Exception as e:
        print(f"✗ Could not clear C drive cache: {e}")
else:
    print(f"\n✓ No corrupted cache found at C drive")

# Verify environment variables
print("\n=== Environment Variables ===")
for var in ["CHROMA_CACHE_DIR", "HF_HOME", "TRANSFORMERS_CACHE", "SENTENCE_TRANSFORMERS_HOME"]:
    value = os.environ.get(var)
    print(f"  {var}: {value}")

print("\n✓ Cache configuration complete!")
