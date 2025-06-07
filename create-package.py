#!/usr/bin/env python3
"""
Package creator for Network Tester
Creates a downloadable ZIP package with all necessary files
"""

import os
import zipfile
import shutil
from datetime import datetime

def create_package():
    """Create downloadable package"""
    
    # Files to include in the package
    files_to_include = [
        'request_flooder.py',
        'install.py', 
        'run.py',
        'requirements.txt',
        'package.json',
        'environment.yml',
        'setup.sh',
        'README.md',
        'example_proxies.txt',
        'download-instructions.md',
        'DOWNLOAD.txt'
    ]
    
    # Create package directory
    package_name = f"network-tester-{datetime.now().strftime('%Y%m%d')}"
    package_dir = f"packages/{package_name}"
    
    # Create directories
    os.makedirs(package_dir, exist_ok=True)
    os.makedirs("packages", exist_ok=True)
    
    print(f"📦 Creating package: {package_name}")
    
    # Copy files to package directory
    for file_name in files_to_include:
        if os.path.exists(file_name):
            shutil.copy2(file_name, package_dir)
            print(f"✅ Added: {file_name}")
        else:
            print(f"⚠️ Missing: {file_name}")
    
    # Create ZIP file
    zip_path = f"packages/{package_name}.zip"
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(package_dir):
            for file in files:
                file_path = os.path.join(root, file)
                arc_name = os.path.relpath(file_path, package_dir)
                zipf.write(file_path, arc_name)
    
    # Get file size
    size_mb = os.path.getsize(zip_path) / (1024 * 1024)
    
    print(f"\n🎉 Package created successfully!")
    print(f"📁 Location: {zip_path}")
    print(f"📊 Size: {size_mb:.2f} MB")
    print(f"\n📥 To download:")
    print(f"   1. Download: {zip_path}")
    print(f"   2. Extract the ZIP file")
    print(f"   3. Run: python3 install.py")
    print(f"   4. Start: python3 request_flooder.py")
    
    # Clean up temporary directory
    shutil.rmtree(package_dir)
    
    return zip_path

if __name__ == "__main__":
    create_package()