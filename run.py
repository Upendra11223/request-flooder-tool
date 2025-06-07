#!/usr/bin/env python3
"""
Launcher script for Network Tester
Handles environment setup and runs the main tool
"""

import sys
import os
import subprocess

def check_dependencies():
    """Check if required dependencies are available"""
    required_modules = ['asyncio', 'aiohttp', 'socket', 'time', 'random', 'urllib.parse', 'signal']
    missing_modules = []
    
    for module in required_modules:
        try:
            __import__(module)
        except ImportError:
            missing_modules.append(module)
    
    return missing_modules

def main():
    """Main launcher function"""
    print("⚡ Network Tester Launcher")
    print("=" * 30)
    
    # Check dependencies
    missing = check_dependencies()
    if missing:
        print(f"❌ Missing required modules: {', '.join(missing)}")
        print("Run the installation script first: python3 install.py")
        sys.exit(1)
    
    print("✅ All dependencies available")
    print("🚀 Starting Network Tester...\n")
    
    # Run the main tool
    try:
        # Import and run the main function from request_flooder
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from request_flooder import main as run_tester
        run_tester()
    except KeyboardInterrupt:
        print("\n\n🛑 Network Tester stopped by user")
    except Exception as e:
        print(f"\n❌ Error running Network Tester: {e}")
        print("Try running directly: python3 request_flooder.py")

if __name__ == "__main__":
    main()