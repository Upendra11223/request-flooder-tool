#!/usr/bin/env python3
"""
Installation script for Network Tester
Ensures all dependencies are properly installed
"""

import subprocess
import sys
import os

def run_command(cmd, description):
    """Run a command and handle errors"""
    print(f"🔧 {description}...")
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ {description} completed successfully")
            if result.stdout.strip():
                print(f"   Output: {result.stdout.strip()}")
        else:
            print(f"⚠️ {description} completed with warnings")
            if result.stderr.strip():
                print(f"   Warning: {result.stderr.strip()}")
        return result.returncode == 0
    except Exception as e:
        print(f"❌ Error during {description}: {e}")
        return False

def check_python():
    """Check Python installation"""
    print("🐍 Checking Python installation...")
    try:
        version = sys.version_info
        print(f"✅ Python {version.major}.{version.minor}.{version.micro} found")
        return version.major >= 3 and version.minor >= 7
    except Exception as e:
        print(f"❌ Python check failed: {e}")
        return False

def install_dependencies():
    """Install Python dependencies"""
    print("\n📦 Installing Python dependencies...")
    
    # Try different pip commands
    pip_commands = [
        "python3 -m pip install --user aiohttp",
        "python -m pip install --user aiohttp", 
        "pip3 install --user aiohttp",
        "pip install --user aiohttp"
    ]
    
    for cmd in pip_commands:
        print(f"Trying: {cmd}")
        if run_command(cmd, "Installing aiohttp"):
            break
    else:
        print("⚠️ Could not install aiohttp via pip, but the tool may still work")
    
    # Try to install uvloop for better performance (optional)
    if sys.platform != 'win32':
        uvloop_commands = [
            "python3 -m pip install --user uvloop",
            "python -m pip install --user uvloop",
            "pip3 install --user uvloop", 
            "pip install --user uvloop"
        ]
        
        for cmd in uvloop_commands:
            if run_command(cmd, "Installing uvloop (optional performance boost)"):
                break
        else:
            print("⚠️ Could not install uvloop, but it's optional")

def test_imports():
    """Test if required modules can be imported"""
    print("\n🧪 Testing module imports...")
    
    modules_to_test = [
        ('asyncio', 'Core async functionality'),
        ('aiohttp', 'HTTP client library'),
        ('socket', 'Network socket operations'),
        ('time', 'Time operations'),
        ('random', 'Random number generation'),
        ('sys', 'System operations'),
        ('os', 'Operating system interface'),
        ('urllib.parse', 'URL parsing'),
        ('signal', 'Signal handling')
    ]
    
    failed_imports = []
    
    for module_name, description in modules_to_test:
        try:
            __import__(module_name)
            print(f"✅ {module_name} - {description}")
        except ImportError as e:
            print(f"❌ {module_name} - {description} - FAILED: {e}")
            failed_imports.append(module_name)
    
    # Test optional uvloop
    try:
        import uvloop
        print("✅ uvloop - Performance boost (optional)")
    except ImportError:
        print("⚠️ uvloop - Performance boost (optional) - Not available")
    
    return len(failed_imports) == 0, failed_imports

def main():
    """Main installation function"""
    print("⚡ Network Tester Installation Script")
    print("Developed by Upendra Khanal")
    print("=" * 50)
    
    # Check Python
    if not check_python():
        print("❌ Python 3.7+ is required")
        sys.exit(1)
    
    # Install dependencies
    install_dependencies()
    
    # Test imports
    success, failed = test_imports()
    
    print("\n" + "=" * 50)
    if success:
        print("🎉 Installation completed successfully!")
        print("\nTo run the Network Tester:")
        print("   python3 request_flooder.py")
        print("\nOr use npm scripts:")
        print("   npm start")
    else:
        print("⚠️ Installation completed with some issues")
        print(f"Failed to import: {', '.join(failed)}")
        print("\nThe tool may still work, but some features might be limited")
        print("Try running: python3 request_flooder.py")
    
    print("\n⚠️ REMINDER: This tool is for educational and authorized testing only!")

if __name__ == "__main__":
    main()