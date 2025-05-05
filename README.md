# ⚡ High-Speed Request Flood Tool

### Developed by **Upendra Khanal**

A high-performance, asynchronous HTTP flood testing tool written in Python. This tool is designed for **stress testing websites and web applications** by sending a large volume of requests, measuring response stats, and optionally analyzing the content of responses (like extracting page titles).

> ⚠️ **Disclaimer**: This tool is intended **only for educational and authorized testing purposes**. Do **not** use it on systems you do not own or have explicit permission to test. Misuse may result in legal consequences.

---

## 🚀 Features

- 🔁 High-speed asynchronous request flooder using `aiohttp` and optionally `uvloop`
- 📊 Live statistics panel: request count, success rate, RPS, peak RPS
- 📋 Extracts and displays website title upon successful requests
- ⚙️ Fully configurable: concurrency, batch size, timeouts, user-agent, etc.
- 🌍 Proxy support (rotate proxies per request)
- 🔍 Pattern/content analyzer with optional keyword search in HTML response
- 🔐 Optimized for Linux performance (includes optional TCP tuning)

---

## 🛠️ Installation

### 1. Clone the repo

```bash
git clone https://github.com/Upendra11223/request-flooder-tool
cd request-flooder
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. (Optional) Speed boost on Linux/macOS

```bash
pip install uvloop
```

---

## 📦 Requirements

Your `requirements.txt` should include:

```txt
aiohttp
uvloop ; sys_platform != 'win32'
```

---

## 💻 Usage

Run the script:

```bash
python request_flooder.py
```

Then follow the interactive prompts:

- Enter target URL
- Number of requests to send
- Concurrency level (parallel connections)
- Custom timeout, user-agent, proxy list, etc.

---

## 🧪 Example

```bash
python request_flooder.py
# Sample session:
# Enter target URL: https://example.com
# Enter number of requests to send: 5000
# Enter concurrency level: 300
```

---

## 📁 Proxy Format

If you use proxies, provide a text file with one proxy per line:

```
http://ip:port
socks5://ip:port
```

---

## 📌 Additional Notes

- Uses non-blocking `asyncio` for high performance.
- You can press `Ctrl+C` anytime to stop the flood.
- The first request is used to test connectivity and print the website title.

---

## 👤 Author

**Upendra Khanal**  
Feel free to reach out or contribute ideas for improvement!
