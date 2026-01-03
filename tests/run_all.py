import sys
import pytest
from pathlib import Path

def main():
    # Ensure the 'src' directory is in the python path
    root_dir = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root_dir / "src"))
    
    # Run pytest on the tests directory
    args = [
        str(root_dir / "tests"),
        "-v",
        "--tb=short"
    ]
    
    return pytest.main(args)

if __name__ == "__main__":
    sys.exit(main())
