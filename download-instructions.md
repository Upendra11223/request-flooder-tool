# 📥 Network Tester - Download & Installation Guide

## 🚀 Quick Download Options

### Option 1: Direct Download (Recommended)
1. **Download the ZIP file** from your browser
2. **Extract** the ZIP file to your desired location
3. **Open terminal/command prompt** in the extracted folder
4. **Run the installer**: `python3 install.py`

### Option 2: Git Clone (If you have Git)
```bash
git clone <repository-url>
cd network-tester
python3 install.py
```

## 📁 What's Included

```
network-tester/
├── request_flooder.py      # Main tool
├── install.py             # Automatic installer
├── run.py                 # Alternative launcher
├── requirements.txt       # Python dependencies
├── package.json          # NPM scripts
├── environment.yml       # Conda environment
├── setup.sh             # Linux/macOS setup script
├── example_proxies.txt  # Sample proxy list
└── README.md           # Documentation
```

## 🔧 Installation Steps

### Step 1: Download & Extract
- Download the ZIP file
- Extract to a folder (e.g., `C:\network-tester` or `~/network-tester`)

### Step 2: Install Dependencies
Open terminal/command prompt in the extracted folder and run:

**Windows:**
```cmd
python install.py
```

**Linux/macOS:**
```bash
python3 install.py
```

### Step 3: Run the Tool
```bash
python3 request_flooder.py
```

## 🎯 Quick Start Example

1. **Run the tool:**
   ```bash
   python3 request_flooder.py
   ```

2. **Select attack type:**
   - Choose `1` for HTTP/HTTPS websites
   - Choose `2` for TCP port attacks
   - Choose `3` for UDP attacks
   - Choose `4` for port scanning

3. **Enter target:**
   - For websites: `https://example.com` or just `example.com`
   - For TCP/UDP: `192.168.1.1:80` or just `192.168.1.1`

4. **Configure settings:**
   - Number of requests/connections
   - Concurrency level
   - Timeout settings

## 🚨 Important Notes

- **Educational Use Only** - Only test systems you own or have permission to test
- **Python 3.7+** required
- **Internet connection** needed for initial setup
- **Administrator privileges** may be needed for some features

## 🆘 Troubleshooting

**If installation fails:**
```bash
# Try manual installation
pip3 install aiohttp
python3 request_flooder.py
```

**If Python not found:**
- Install Python 3.7+ from python.org
- Make sure Python is in your system PATH

**For permission errors:**
- Run terminal as Administrator (Windows)
- Use `sudo` if needed (Linux/macOS)

## 📞 Support

If you encounter issues:
1. Check that Python 3.7+ is installed
2. Ensure internet connection for dependency installation
3. Try running `python3 install.py` again
4. Check the README.md for detailed documentation

---
**Developed by Upendra Khanal**