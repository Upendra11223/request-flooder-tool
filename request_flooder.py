import sys
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
import threading
import queue
import asyncio
import time
import os
import json
import random
from datetime import datetime
from functools import partial
from collections import Counter

# Import the main code from your original script
# This assumes your flood controller code is in a file called request_flood.py
# and has been placed in the same directory
try:
    from request_flood import FloodController, RequestStats, ContentAnalyzer
    IMPORTED_MODULES = True
except ImportError:
    IMPORTED_MODULES = False
    # We'll create a simplified version for the UI demo
    class RequestStats:
        def __init__(self):
            self.success = 0
            self.failed = 0
            self.total_time = 0
            self.start_time = 0
            self.end_time = 0
            self.lock = asyncio.Lock()
            self.peak_rps = 0
            self.status_codes = Counter()  # Add status code tracking
            self.responses = []  # Store response data for downloading
            
        async def increment_success(self, duration, status_code=200, response_data=None):
            self.success += 1
            self.total_time += duration
            self.status_codes[status_code] += 1  # Track status code
            
            # Store response data if provided
            if response_data:
                self.responses.append({
                    "timestamp": time.time(),
                    "status_code": status_code,
                    "duration": duration,
                    "success": True,
                    "response": response_data
                })
            
        async def increment_failed(self, status_code=0, error_data=None):
            self.failed += 1
            self.status_codes[status_code] += 1  # Track status code for failures too
            
            # Store error data if provided
            if error_data:
                self.responses.append({
                    "timestamp": time.time(),
                    "status_code": status_code,
                    "success": False,
                    "error": error_data
                })
            
        async def get_stats(self):
            total = self.success + self.failed
            avg_time = self.total_time / max(1, self.success)
            elapsed = time.time() - self.start_time if self.start_time else 0
            rps = total / max(0.1, elapsed)
            
            return {
                "success": self.success,
                "failed": self.failed, 
                "total": total,
                "avg_time": round(avg_time, 4),
                "elapsed": round(elapsed, 2),
                "requests_per_second": round(rps, 2),
                "peak_rps": round(self.peak_rps, 2),
                "status_codes": dict(self.status_codes),  # Return status code counts
                "has_responses": len(self.responses) > 0
            }
            
        async def get_responses(self):
            """Return the collected responses for download"""
            return self.responses
            
    class ContentAnalyzer:
        def __init__(self, patterns=None):
            self.patterns = patterns or []
            
        def add_text_search(self, text):
            self.patterns.append((text, f"Found: '{text}' in content"))
            
    class FloodController:
        def __init__(self, url, stats, analyzer, timeout=1):
            self.url = url
            self.stats = stats
            self.analyzer = analyzer
            self.timeout = timeout
            self.should_analyze_content = False
            self.should_save_responses = False
            self.max_response_size = 1024 * 10  # 10KB limit for responses by default
            
            # Proxy settings
            self.use_proxy = False
            self.proxy_url = None
            self.proxy_username = None
            self.proxy_password = None
            
            # Proxy list for rotation (new)
            self.proxy_list = []
            self.current_proxy_index = 0
            self.use_proxy_rotation = False
            
        def set_proxy(self, use_proxy, proxy_url=None, username=None, password=None):
            """Configure proxy settings"""
            self.use_proxy = use_proxy
            if use_proxy and proxy_url:
                self.proxy_url = proxy_url
                self.proxy_username = username
                self.proxy_password = password
            else:
                self.proxy_url = None
                self.proxy_username = None
                self.proxy_password = None
                
        def set_proxy_list(self, proxy_list, use_rotation=True):
            """Set a list of proxies for rotation"""
            self.proxy_list = proxy_list
            self.use_proxy_rotation = use_rotation and bool(proxy_list)
            self.current_proxy_index = 0
            
        def get_next_proxy(self):
            """Get the next proxy from the rotation list"""
            if not self.proxy_list:
                return None
                
            proxy = self.proxy_list[self.current_proxy_index]
            self.current_proxy_index = (self.current_proxy_index + 1) % len(self.proxy_list)
            return proxy
            
        async def flood(self, total_requests, concurrency, batch_size=100):
            """Simulated version for the UI demo"""
            self.stats.start_time = time.time()
            total_requests = int(total_requests)
            concurrency = int(concurrency)
            batch_size = int(batch_size)
            
            # Log proxy info in simulation
            if self.use_proxy and self.proxy_url:
                proxy_msg = f"Using proxy: {self.proxy_url}"
                if self.proxy_username:
                    proxy_msg += f" with authentication"
            elif self.use_proxy_rotation and self.proxy_list:
                proxy_msg = f"Using proxy rotation with {len(self.proxy_list)} proxies"
            else:
                proxy_msg = "No proxy configured"
                
            # Simulate requests with different status codes
            status_codes = [200, 200, 200, 200, 200, 200, 200, 200, 301, 404, 500]
            
            # Example response content for simulation
            response_bodies = {
                200: """{"status": "success", "message": "Request processed successfully", "data": {"id": 12345, "timestamp": "2025-05-05T12:34:56Z"}}""",
                301: """<html><head><title>Moved Permanently</title></head><body><h1>Moved Permanently</h1><p>The document has moved <a href="https://example.com/new-location">here</a>.</p></body></html>""",
                404: """<html><head><title>Not Found</title></head><body><h1>Not Found</h1><p>The requested URL was not found on this server.</p></body></html>""",
                500: """<html><head><title>Internal Server Error</title></head><body><h1>Internal Server Error</h1><p>The server encountered an internal error and was unable to complete your request.</p></body></html>"""
            }
            
            # Headers examples
            example_headers = {
                200: {
                    "Content-Type": "application/json",
                    "Server": "nginx/1.18.0",
                    "Date": "Mon, 05 May 2025 12:34:56 GMT",
                    "Content-Length": "120"
                },
                301: {
                    "Content-Type": "text/html",
                    "Location": "https://example.com/new-location",
                    "Server": "nginx/1.18.0",
                    "Date": "Mon, 05 May 2025 12:34:56 GMT",
                },
                404: {
                    "Content-Type": "text/html",
                    "Server": "nginx/1.18.0",
                    "Date": "Mon, 05 May 2025 12:34:56 GMT",
                },
                500: {
                    "Content-Type": "text/html",
                    "Server": "nginx/1.18.0",
                    "Date": "Mon, 05 May 2025 12:34:56 GMT",
                }
            }
            
            # Simulate requests with proxy rotation if enabled
            for i in range(total_requests):
                # Get the next proxy if using rotation
                current_proxy = None
                if self.use_proxy_rotation and self.proxy_list:
                    current_proxy = self.get_next_proxy()
                elif self.use_proxy and self.proxy_url:
                    current_proxy = {
                        "url": self.proxy_url,
                        "username": self.proxy_username,
                        "password": self.proxy_password
                    }
                
                # Simulate a random status code
                status_code = status_codes[i % len(status_codes)]
                
                # Create response data for storage if needed
                response_data = None
                if self.should_save_responses:
                    response_data = {
                        "url": self.url,
                        "status_code": status_code,
                        "headers": example_headers.get(status_code, {}),
                        "body": response_bodies.get(status_code, ""),
                        "request_id": i + 1,
                        "timestamp": datetime.now().isoformat(),
                        "proxy_used": True if current_proxy else False,
                        "proxy_details": current_proxy["url"] if current_proxy else None
                    }
                
                # Simulate success/failure based on status code
                if status_code >= 400:  # 4xx and 5xx are failures
                    await self.stats.increment_failed(status_code, error_data=response_data)
                else:
                    await self.stats.increment_success(0.05, status_code, response_data=response_data)  # 50ms response time
                
                # Sleep briefly to not block the event loop
                if i % 100 == 0:
                    await asyncio.sleep(0.1)
            
            self.stats.end_time = time.time()
            return await self.stats.get_stats()


# New class for managing proxy files and formats
class ProxyManager:
    def __init__(self):
        self.proxies = []
        self.current_index = 0
        
    def load_from_file(self, file_path):
        """Load proxies from a file"""
        try:
            with open(file_path, 'r') as f:
                content = f.read().strip()
                
            # Try to detect the format and parse accordingly
            self.proxies = self.parse_proxy_file(content, file_path)
            return len(self.proxies)
        except Exception as e:
            raise Exception(f"Failed to load proxy file: {str(e)}")
    
    def parse_proxy_file(self, content, file_path):
        """Parse different proxy file formats"""
        # Strip any BOM and remove empty lines
        content = content.replace('\ufeff', '')
        lines = [line.strip() for line in content.splitlines() if line.strip()]
        
        if not lines:
            return []
            
        proxies = []
        
        # Determine the format based on the first line
        first_line = lines[0]
        
        # Check if JSON format
        if file_path.lower().endswith('.json') or first_line.strip().startswith('{'):
            try:
                # Try parsing as JSON
                if first_line.strip().startswith('{'):
                    # Might be a JSON object per line
                    for line in lines:
                        proxy_obj = json.loads(line)
                        # Extract fields based on common JSON formats
                        proxy = self.extract_proxy_from_json(proxy_obj)
                        if proxy:
                            proxies.append(proxy)
                else:
                    # Might be a JSON array
                    proxy_list = json.loads(content)
                    if isinstance(proxy_list, list):
                        for proxy_obj in proxy_list:
                            proxy = self.extract_proxy_from_json(proxy_obj)
                            if proxy:
                                proxies.append(proxy)
            except json.JSONDecodeError:
                # Not a valid JSON, try other formats
                pass
                
        # If not JSON or couldn't parse as JSON, try other formats
        if not proxies:
            # Try other common formats
            for line in lines:
                proxy = self.parse_proxy_line(line)
                if proxy:
                    proxies.append(proxy)
                    
        return proxies
    
    def extract_proxy_from_json(self, proxy_obj):
        """Extract proxy details from a JSON object"""
        if not isinstance(proxy_obj, dict):
            return None
            
        proxy = {}
        
        # Common field names for proxy URL/host/port
        if 'url' in proxy_obj:
            proxy['url'] = proxy_obj['url']
        elif 'proxy' in proxy_obj:
            proxy['url'] = proxy_obj['proxy']
        elif all(k in proxy_obj for k in ['host', 'port']):
            # Construct URL from host and port
            protocol = proxy_obj.get('protocol', 'http')
            host = proxy_obj['host']
            port = proxy_obj['port']
            proxy['url'] = f"{protocol}://{host}:{port}"
        else:
            return None
            
        # Authentication details
        if 'username' in proxy_obj and 'password' in proxy_obj:
            proxy['username'] = proxy_obj['username']
            proxy['password'] = proxy_obj['password']
        
        return proxy
    
    def parse_proxy_line(self, line):
        """Parse a line of text in various proxy formats"""
        line = line.strip()
        if not line or line.startswith('#'):
            return None
            
        # Format: protocol://[username:password@]host:port
        if '://' in line:
            try:
                proxy = {'url': line}
                
                # Extract authentication if present
                if '@' in line:
                    auth_part = line.split('://')[1].split('@')[0]
                    if ':' in auth_part:
                        username, password = auth_part.split(':', 1)
                        proxy['username'] = username
                        proxy['password'] = password
                        
                return proxy
            except:
                pass
                
        # Format: host:port:username:password
        if line.count(':') >= 1:
            parts = line.split(':')
            if len(parts) >= 2:
                host, port = parts[0:2]
                # Default to http protocol
                proxy = {'url': f'http://{host}:{port}'}
                
                # Check if we have auth details
                if len(parts) >= 4:
                    proxy['username'] = parts[2]
                    proxy['password'] = parts[3]
                    
                return proxy
                
        return None
    
    def get_next_proxy(self):
        """Get the next proxy from the list (round-robin)"""
        if not self.proxies:
            return None
            
        proxy = self.proxies[self.current_index]
        self.current_index = (self.current_index + 1) % len(self.proxies)
        return proxy
    
    def get_random_proxy(self):
        """Get a random proxy from the list"""
        if not self.proxies:
            return None
            
        return random.choice(self.proxies)
    
    def clear(self):
        """Clear all proxies"""
        self.proxies = []
        self.current_index = 0
    
    def get_count(self):
        """Get the number of proxies"""
        return len(self.proxies)


class AsyncioThread(threading.Thread):
    """Thread that runs an asyncio event loop"""
    def __init__(self, queue):
        super().__init__()
        self.queue = queue
        self.daemon = True
        self.loop = None
        
    def run(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()
        
    def stop(self):
        if self.loop:
            self.loop.call_soon_threadsafe(self.loop.stop)
            
    def run_coro(self, coro):
        """Run a coroutine in this thread's event loop"""
        future = asyncio.run_coroutine_threadsafe(coro, self.loop)
        return future


class RequestFloodApp:
    def __init__(self, root):
        self.root = root
        self.root.title("High-Speed Web Request Testing Tool")
        self.root.geometry("900x650")  # Increased height for new options
        
        # Set the window icon (on Windows)
        if sys.platform == "win32":
            try:
                self.root.iconbitmap("icon.ico")
            except:
                pass
                
        # Create an asyncio thread for running the flood controller
        self.queue = queue.Queue()
        self.asyncio_thread = AsyncioThread(self.queue)
        self.asyncio_thread.start()
        
        # Create variables for form fields
        self.url_var = tk.StringVar(value="https://")
        self.num_requests_var = tk.StringVar(value="100")
        self.concurrency_var = tk.StringVar(value="10")
        self.batch_size_var = tk.StringVar(value="50")
        self.analyze_content_var = tk.BooleanVar(value=False)
        self.search_text_var = tk.StringVar()
        self.show_logs_var = tk.BooleanVar(value=True)
        self.save_responses_var = tk.BooleanVar(value=True)
        
        # Proxy settings
        self.use_proxy_var = tk.BooleanVar(value=False)
        self.proxy_url_var = tk.StringVar(value="")
        self.proxy_username_var = tk.StringVar(value="")
        self.proxy_password_var = tk.StringVar(value="")
        
        # Proxy file settings (new)
        self.use_proxy_file_var = tk.BooleanVar(value=False)
        self.proxy_file_path_var = tk.StringVar(value="")
        self.proxy_rotation_method_var = tk.StringVar(value="round-robin")
        
        # Create proxy manager
        self.proxy_manager = ProxyManager()
        
        # For stats tracking
        self.successes = 0
        self.failures = 0
        self.total = 0
        self.elapsed = 0
        self.rps = 0
        self.peak_rps = 0
        self.average_time = 0
        self.status_codes = {}
        self.has_responses = False
        
        # Running flag
        self.is_running = False
        self.controller = None
        self.stats = None
        self.analyzer = None
        
        # Create the UI
        self.create_widgets()
        
        # Update the UI every 100ms when running
        self.update_id = None
        
        # Bind window close event
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        
        # Initialize hidden frames
        self.toggle_search_field()
        self.toggle_proxy_fields()
        self.toggle_proxy_file_fields()
        
    def create_widgets(self):
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Style configuration
        style = ttk.Style()
        style.configure("TLabel", font=("Arial", 10))
        style.configure("TButton", font=("Arial", 10))
        style.configure("Header.TLabel", font=("Arial", 12, "bold"))
        style.configure("Stats.TLabel", font=("Arial", 10, "bold"))
        
        # Title and author info
        title_frame = ttk.Frame(main_frame)
        title_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(title_frame, text="High-Speed Web Request Testing Tool", 
                 font=("Arial", 16, "bold")).pack(anchor=tk.W)
        ttk.Label(title_frame, 
                 text="Developed by Upendra Khanal | Contact: @kinvilen on Telegram", 
                 font=("Arial", 10)).pack(anchor=tk.W)
        ttk.Separator(main_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=5)
        
        # Create two main sections in a grid
        content_frame = ttk.Frame(main_frame)
        content_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Form section (left)
        form_frame = ttk.LabelFrame(content_frame, text="Test Configuration", padding=10)
        form_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=False, padx=(0, 5))
        
        # URL field
        url_frame = ttk.Frame(form_frame)
        url_frame.pack(fill=tk.X, pady=5)
        ttk.Label(url_frame, text="Target URL:").pack(anchor=tk.W)
        ttk.Entry(url_frame, textvariable=self.url_var, width=40).pack(fill=tk.X, pady=2)
        
        # Number of requests and concurrency in a 2-column grid
        params_frame = ttk.Frame(form_frame)
        params_frame.pack(fill=tk.X, pady=5)
        
        # Requests
        req_frame = ttk.Frame(params_frame)
        req_frame.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        ttk.Label(req_frame, text="Number of Requests:").pack(anchor=tk.W)
        ttk.Entry(req_frame, textvariable=self.num_requests_var, width=10).pack(fill=tk.X, pady=2)
        
        # Concurrency
        conc_frame = ttk.Frame(params_frame)
        conc_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Label(conc_frame, text="Concurrency:").pack(anchor=tk.W)
        ttk.Entry(conc_frame, textvariable=self.concurrency_var, width=10).pack(fill=tk.X, pady=2)
        
        # Advanced options section
        advanced_frame = ttk.LabelFrame(form_frame, text="Advanced Options", padding=10)
        advanced_frame.pack(fill=tk.X, pady=5)
        
        # Batch size
        batch_frame = ttk.Frame(advanced_frame)
        batch_frame.pack(fill=tk.X, pady=5)
        ttk.Label(batch_frame, text="Batch Size:").pack(anchor=tk.W)
        ttk.Entry(batch_frame, textvariable=self.batch_size_var, width=10).pack(side=tk.LEFT, fill=tk.X, pady=2)
        
        # Checkboxes
        check_frame = ttk.Frame(advanced_frame)
        check_frame.pack(fill=tk.X, pady=5)
        
        ttk.Checkbutton(check_frame, text="Analyze Content (slower)", 
                       variable=self.analyze_content_var,
                       command=self.toggle_search_field).pack(anchor=tk.W)
        
        ttk.Checkbutton(check_frame, text="Show Detailed Logs", 
                       variable=self.show_logs_var).pack(anchor=tk.W)
        
        ttk.Checkbutton(check_frame, text="Save Full Response Data", 
                       variable=self.save_responses_var).pack(anchor=tk.W)
        
        # Search text (hidden by default)
        self.search_frame = ttk.Frame(advanced_frame)
        ttk.Label(self.search_frame, text="Search for Text:").pack(anchor=tk.W)
        ttk.Entry(self.search_frame, textvariable=self.search_text_var).pack(fill=tk.X, pady=2)
        
        # Proxy settings section
        proxy_frame = ttk.LabelFrame(form_frame, text="Proxy Settings", padding=10)
        proxy_frame.pack(fill=tk.X, pady=5)
        
        # Radio buttons for proxy type
        proxy_type_frame = ttk.Frame(proxy_frame)
        proxy_type_frame.pack(fill=tk.X, pady=5)
        
        # No proxy option
        ttk.Radiobutton(proxy_type_frame, text="No Proxy", 
                      variable=self.use_proxy_var, value=False,
                      command=self.handle_proxy_type_change).pack(anchor=tk.W)
        
        # Single proxy option
        ttk.Radiobutton(proxy_type_frame, text="Use Single Proxy", 
                      variable=self.use_proxy_var, value=True,
                      command=self.handle_proxy_type_change).pack(anchor=tk.W)
        
        # Proxy file option (new)
        self.proxy_file_radio = ttk.Radiobutton(proxy_type_frame, text="Use Proxy File (List)", 
                                             command=self.handle_proxy_type_change)
        self.proxy_file_radio.pack(anchor=tk.W)
        self.proxy_file_radio.configure(variable=self.use_proxy_file_var, value=True)
        
        # Single proxy settings (initially hidden)
        self.proxy_settings_frame = ttk.Frame(proxy_frame)
        
        # Proxy URL
        proxy_url_frame = ttk.Frame(self.proxy_settings_frame)
        proxy_url_frame.pack(fill=tk.X, pady=2)
        ttk.Label(proxy_url_frame, text="Proxy URL:").pack(anchor=tk.W)
        ttk.Entry(proxy_url_frame, textvariable=self.proxy_url_var).pack(fill=tk.X, pady=2)
        ttk.Label(proxy_url_frame, text="Format: http://host:port or socks5://host:port").pack(anchor=tk.W)
        
        # Proxy authentication
        proxy_auth_frame = ttk.Frame(self.proxy_settings_frame)
        proxy_auth_frame.pack(fill=tk.X, pady=5)
        
        # Username
        proxy_user_frame = ttk.Frame(proxy_auth_frame)
        proxy_user_frame.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        ttk.Label(proxy_user_frame, text="Username (optional):").pack(anchor=tk.W)
        ttk.Entry(proxy_user_frame, textvariable=self.proxy_username_var).pack(fill=tk.X, pady=2)
        
        # Password
        proxy_pass_frame = ttk.Frame(proxy_auth_frame)
        proxy_pass_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Label(proxy_pass_frame, text="Password (optional):").pack(anchor=tk.W)
        password_entry = ttk.Entry(proxy_pass_frame, textvariable=self.proxy_password_var, show="*")
        password_entry.pack(fill=tk.X, pady=2)
        
        # Proxy file settings frame (new)
        self.proxy_file_frame = ttk.Frame(proxy_frame)
        
        # Proxy file selection
        proxy_file_select_frame = ttk.Frame(self.proxy_file_frame)
        proxy_file_select_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(proxy_file_select_frame, text="Proxy File:").pack(anchor=tk.W)
        proxy_file_entry = ttk.Entry(proxy_file_select_frame, textvariable=self.proxy_file_path_var)
        proxy_file_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, pady=2, padx=(0, 5))
        
        browse_button = ttk.Button(proxy_file_select_frame, text="Browse", command=self.browse_proxy_file)
        browse_button.pack(side=tk.LEFT, pady=2)
        
        # Proxy file format info
        ttk.Label(self.proxy_file_frame, text="Supported formats: IP:PORT, user:pass@IP:PORT, http://IP:PORT, etc.").pack(anchor=tk.W)
        
        # Proxy rotation method
        rotation_frame = ttk.Frame(self.proxy_file_frame)
        rotation_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(rotation_frame, text="Rotation Method:").pack(anchor=tk.W)
        rotation_options = ttk.Frame(rotation_frame)
        rotation_options.pack(fill=tk.X)
        
        ttk.Radiobutton(rotation_options, text="Round-Robin", 
                      variable=self.proxy_rotation_method_var, value="round-robin").pack(anchor=tk.W)
        ttk.Radiobutton(rotation_options, text="Random", 
                      variable=self.proxy_rotation_method_var, value="random").pack(anchor=tk.W)
        
        # Proxy list info
        self.proxy_list_info_frame = ttk.Frame(self.proxy_file_frame)
        self.proxy_list_info_frame.pack(fill=tk.X, pady=5)
        
        self.proxy_count_label = ttk.Label(self.proxy_list_info_frame, text="No proxies loaded")
        self.proxy_count_label.pack(anchor=tk.W)
        
        # Load proxies button
        self.load_proxies_button = ttk.Button(self.proxy_file_frame, text="Load Proxies", 
                                           command=self.load_proxies)
        self.load_proxies_button.pack(side=tk.LEFT, pady=5)
        
        # Test proxies button (will be implemented in the future)
        self.test_proxies_button = ttk.Button(self.proxy_file_frame, text="Test Proxies", 
                                           command=self.test_proxies, state=tk.DISABLED)
        self.test_proxies_button.pack(side=tk.LEFT, pady=5, padx=5)
        
        # Start button
        button_frame = ttk.Frame(form_frame)
        button_frame.pack(fill=tk.X, pady=10)
        
        self.start_button = ttk.Button(button_frame, text="Start Test", 
                                     command=self.start_test, width=20)
        self.start_button.pack(side=tk.LEFT, padx=5)
        
        self.stop_button = ttk.Button(button_frame, text="Stop Test", 
                                    command=self.stop_test, width=20, state=tk.DISABLED)
        self.stop_button.pack(side=tk.LEFT, padx=5)
        
        # Warning label
        warning_frame = ttk.Frame(form_frame)
        warning_frame.pack(fill=tk.X, pady=10)
        ttk.Label(warning_frame, 
                 text="⚠️ WARNING: Only test websites you own or have permission to test!",
                 foreground="red").pack(anchor=tk.W)
        
        # Results section (right)
        results_frame = ttk.Frame(content_frame)
        results_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        # Stats panel
        stats_frame = ttk.LabelFrame(results_frame, text="Statistics", padding=10)
        stats_frame.pack(fill=tk.X, expand=False, pady=(0, 5))
        
        # Stats grid - 2 columns
        stats_grid = ttk.Frame(stats_frame)
        stats_grid.pack(fill=tk.X)
        
        # First row
        ttk.Label(stats_grid, text="Successful:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)
        self.success_label = ttk.Label(stats_grid, text="0", style="Stats.TLabel")
        self.success_label.grid(row=0, column=1, sticky=tk.W, padx=5, pady=2)
        
        ttk.Label(stats_grid, text="Failed:").grid(row=0, column=2, sticky=tk.W, padx=5, pady=2)
        self.failed_label = ttk.Label(stats_grid, text="0", style="Stats.TLabel")
        self.failed_label.grid(row=0, column=3, sticky=tk.W, padx=5, pady=2)
        
        # Second row
        ttk.Label(stats_grid, text="Total:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=2)
        self.total_label = ttk.Label(stats_grid, text="0", style="Stats.TLabel")
        self.total_label.grid(row=1, column=1, sticky=tk.W, padx=5, pady=2)
        
        ttk.Label(stats_grid, text="Elapsed:").grid(row=1, column=2, sticky=tk.W, padx=5, pady=2)
        self.elapsed_label = ttk.Label(stats_grid, text="0.00s", style="Stats.TLabel")
        self.elapsed_label.grid(row=1, column=3, sticky=tk.W, padx=5, pady=2)
        
        # Third row
        ttk.Label(stats_grid, text="Req/Sec:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=2)
        self.rps_label = ttk.Label(stats_grid, text="0.00", style="Stats.TLabel")
        self.rps_label.grid(row=2, column=1, sticky=tk.W, padx=5, pady=2)
        
        ttk.Label(stats_grid, text="Peak RPS:").grid(row=2, column=2, sticky=tk.W, padx=5, pady=2)
        self.peak_rps_label = ttk.Label(stats_grid, text="0.00", style="Stats.TLabel")
        self.peak_rps_label.grid(row=2, column=3, sticky=tk.W, padx=5, pady=2)
        
        # Fourth row
        ttk.Label(stats_grid, text="Avg Time:").grid(row=3, column=0, sticky=tk.W, padx=5, pady=2)
        self.avg_time_label = ttk.Label(stats_grid, text="0.0000s", style="Stats.TLabel")
        self.avg_time_label.grid(row=3, column=1, sticky=tk.W, padx=5, pady=2)
        
        ttk.Label(stats_grid, text="Success Rate:").grid(row=3, column=2, sticky=tk.W, padx=5, pady=2)
        self.success_rate_label = ttk.Label(stats_grid, text="0.0%", style="Stats.TLabel")
        self.success_rate_label.grid(row=3, column=3, sticky=tk.W, padx=5, pady=2)
        
        # Status Code Distribution section
        status_frame = ttk.LabelFrame(stats_frame, text="Status Code Distribution", padding=10)
        status_frame.pack(fill=tk.X, pady=5)
        
        # Create a frame for status codes with scrollbar
        status_scroll_frame = ttk.Frame(status_frame)
        status_scroll_frame.pack(fill=tk.X, expand=True)
        
        # Create a canvas for scrolling (needed for dynamic content)
        self.status_canvas = tk.Canvas(status_scroll_frame, height=100)
        scrollbar = ttk.Scrollbar(status_scroll_frame, orient="vertical", command=self.status_canvas.yview)
        self.status_canvas.configure(yscrollcommand=scrollbar.set)
        
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.status_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Create a frame inside the canvas for the status codes
        self.status_codes_frame = ttk.Frame(self.status_canvas)
        self.status_canvas.create_window((0, 0), window=self.status_codes_frame, anchor="nw")
        
        # Download Responses button (initially disabled)
        self.download_frame = ttk.Frame(status_frame)
        self.download_frame.pack(fill=tk.X, pady=5)
        self.download_button = ttk.Button(self.download_frame, text="Download Response Data", 
                                      command=self.download_responses, state=tk.DISABLED)
        self.download_button.pack(side=tk.RIGHT)
        
        # Progress bar
        progress_frame = ttk.Frame(stats_frame)
        progress_frame.pack(fill=tk.X, pady=5)
        ttk.Label(progress_frame, text="Progress:").pack(anchor=tk.W)
        self.progress_bar = ttk.Progressbar(progress_frame, orient=tk.HORIZONTAL, length=100, mode='determinate')
        self.progress_bar.pack(fill=tk.X, pady=2)
        
        # Terminal output
        log_frame = ttk.LabelFrame(results_frame, text="Terminal Output", padding=10)
        log_frame.pack(fill=tk.BOTH, expand=True)
        
        self.log_text = scrolledtext.ScrolledText(log_frame, wrap=tk.WORD, 
                                                background='black', foreground='#00FF00',
                                                font=('Courier New', 9))
        self.log_text.pack(fill=tk.BOTH, expand=True)
        self.log_text.configure(state='disabled')
        
        # Initialize UI states
        self.handle_proxy_type_change()
        self.toggle_search_field()
        
        # Configure the canvas scrolling
        self.status_codes_frame.bind("<Configure>", lambda e: self.status_canvas.configure(
            scrollregion=self.status_canvas.bbox("all")))
    
    def handle_proxy_type_change(self):
        """Handle proxy type selection changes"""
        # Hide all frames first
        self.proxy_settings_frame.pack_forget()
        self.proxy_file_frame.pack_forget()
        
        # Show the appropriate frame based on selection
        if self.use_proxy_var.get():
            # Single proxy selected
            self.proxy_settings_frame.pack(fill=tk.X, pady=5)
            # Reset the proxy file checkbox to avoid conflicts
            self.use_proxy_file_var.set(False)
        elif self.use_proxy_file_var.get():
            # Proxy file selected
            self.proxy_file_frame.pack(fill=tk.X, pady=5)
            # Reset the single proxy checkbox to avoid conflicts
            self.use_proxy_var.set(False)
    
    def toggle_search_field(self):
        """Show/hide the search text field based on analyze_content checkbox"""
        if self.analyze_content_var.get():
            self.search_frame.pack(fill=tk.X, pady=5)
        else:
            self.search_frame.pack_forget()
            
    def toggle_proxy_fields(self):
        """Show/hide the proxy settings fields based on use_proxy checkbox"""
        # This is now handled by handle_proxy_type_change
        self.handle_proxy_type_change()
    
    def toggle_proxy_file_fields(self):
        """Show/hide the proxy file fields based on use_proxy_file checkbox"""
        # This is now handled by handle_proxy_type_change
        self.handle_proxy_type_change()
    
    def browse_proxy_file(self):
        """Open a file dialog to select a proxy file"""
        file_path = filedialog.askopenfilename(
            title="Select Proxy File",
            filetypes=[
                ("Text Files", "*.txt"),
                ("JSON Files", "*.json"),
                ("CSV Files", "*.csv"),
                ("All Files", "*.*")
            ]
        )
        
        if file_path:
            self.proxy_file_path_var.set(file_path)
    
    def load_proxies(self):
        """Load proxies from the selected file"""
        file_path = self.proxy_file_path_var.get().strip()
        if not file_path:
            messagebox.showerror("Error", "Please select a proxy file first")
            return
            
        if not os.path.exists(file_path):
            messagebox.showerror("Error", f"File not found: {file_path}")
            return
            
        try:
            # Clear previous proxies
            self.proxy_manager.clear()
            
            # Load proxies from file
            count = self.proxy_manager.load_from_file(file_path)
            
            # Update the UI
            self.proxy_count_label.config(text=f"{count} proxies loaded successfully")
            
            # Enable test button if we have proxies
            if count > 0:
                self.test_proxies_button.config(state=tk.NORMAL)
            else:
                self.test_proxies_button.config(state=tk.DISABLED)
                
            # Log the result
            self.log(f"Loaded {count} proxies from {file_path}")
            
            # Show a sample of proxies in the log
            if count > 0:
                self.log("\nSample of loaded proxies:")
                for i, proxy in enumerate(self.proxy_manager.proxies[:5]):
                    proxy_url = proxy.get('url', 'N/A')
                    has_auth = 'Yes' if 'username' in proxy and 'password' in proxy else 'No'
                    self.log(f"  {i+1}. {proxy_url} (Auth: {has_auth})")
                    
                if count > 5:
                    self.log(f"  ... and {count - 5} more")
                    
            messagebox.showinfo("Success", f"Loaded {count} proxies from the file")
                
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load proxy file: {str(e)}")
            self.log(f"Error loading proxy file: {str(e)}")
    
    def test_proxies(self):
        """Test the loaded proxies"""
        # This will be implemented in a future version
        messagebox.showinfo("Coming Soon", "Proxy testing functionality will be available in a future update")
    
    def update_status_codes_display(self, status_codes):
        """Update the status codes distribution display"""
        # Clear the previous status codes
        for widget in self.status_codes_frame.winfo_children():
            widget.destroy()
            
        # If no status codes yet, show message
        if not status_codes:
            ttk.Label(self.status_codes_frame, text="No status codes recorded yet").pack(anchor=tk.W)
            return
            
        # Sort status codes by count (descending)
        sorted_codes = sorted(status_codes.items(), key=lambda x: x[1], reverse=True)
        
        # Create a grid for status codes
        for i, (code, count) in enumerate(sorted_codes):
            # Determine color based on status code
            if 100 <= code < 200:  # Informational
                color = "#6495ED"  # Cornflower Blue
            elif 200 <= code < 300:  # Success
                color = "#32CD32"  # Lime Green
            elif 300 <= code < 400:  # Redirection
                color = "#FF8C00"  # Dark Orange
            elif 400 <= code < 500:  # Client Error
                color = "#FF6347"  # Tomato
            elif 500 <= code < 600:  # Server Error
                color = "#DC143C"  # Crimson
            else:
                color = "#808080"  # Gray (for unknown codes)
                
            # Create a row for this status code
            row_frame = ttk.Frame(self.status_codes_frame)
            row_frame.pack(fill=tk.X, expand=True, pady=1)
            
            # Add a color indicator
            indicator = tk.Frame(row_frame, background=color, width=15, height=15)
            indicator.pack(side=tk.LEFT, padx=5)
            
            # Add the status code
            code_desc = self.get_status_code_description(code)
            code_label = ttk.Label(row_frame, text=f"HTTP {code} {code_desc}:")
            code_label.pack(side=tk.LEFT, padx=5)
            
            # Add the count
            count_label = ttk.Label(row_frame, text=str(count))
            count_label.pack(side=tk.LEFT, padx=5)
            
    def get_status_code_description(self, code):
        """Return a description for a given HTTP status code"""
        descriptions = {
            0: "Network Error/Timeout",
            200: "OK",
            201: "Created",
            204: "No Content",
            301: "Moved Permanently",
            302: "Found",
            304: "Not Modified",
            400: "Bad Request",
            401: "Unauthorized",
            403: "Forbidden",
            404: "Not Found",
            429: "Too Many Requests",
            500: "Internal Server Error",
            502: "Bad Gateway",
            503: "Service Unavailable",
            504: "Gateway Timeout"
        }
        return descriptions.get(code, "")
            
    def validate_input(self):
        """Validate the form inputs"""
        url = self.url_var.get().strip()
        if not url.startswith(('http://', 'https://')):
            messagebox.showerror("Invalid URL", "URL must start with http:// or https://")
            return False
            
        try:
            num_requests = int(self.num_requests_var.get())
            if num_requests <= 0:
                raise ValueError()
        except ValueError:
            messagebox.showerror("Invalid Input", "Number of requests must be a positive integer")
            return False
            
        try:
            concurrency = int(self.concurrency_var.get())
            if concurrency <= 0:
                raise ValueError()
        except ValueError:
            messagebox.showerror("Invalid Input", "Concurrency must be a positive integer")
            return False
            
        try:
            batch_size = int(self.batch_size_var.get())
            if batch_size <= 0:
                raise ValueError()
        except ValueError:
            messagebox.showerror("Invalid Input", "Batch size must be a positive integer")
            return False
            
        # Validate proxy settings if single proxy is enabled
        if self.use_proxy_var.get():
            proxy_url = self.proxy_url_var.get().strip()
            if not proxy_url:
                messagebox.showerror("Invalid Proxy", "Proxy URL is required when proxy is enabled")
                return False
                
            # Check if proxy URL has correct format
            if not proxy_url.startswith(('http://', 'https://', 'socks4://', 'socks5://')):
                messagebox.showerror("Invalid Proxy", 
                                   "Proxy URL must start with http://, https://, socks4://, or socks5://")
                return False
                
        # Validate proxy file settings if proxy file is enabled
        if self.use_proxy_file_var.get():
            if self.proxy_manager.get_count() == 0:
                messagebox.showerror("No Proxies", "Please load proxies from a file first")
                return False
        
        return True
        
    def log(self, message):
        """Add a message to the log terminal"""
        self.log_text.configure(state='normal')
        self.log_text.insert(tk.END, f"{message}\n")
        self.log_text.see(tk.END)
        self.log_text.configure(state='disabled')
        
    def clear_log(self):
        """Clear the log terminal"""
        self.log_text.configure(state='normal')
        self.log_text.delete(1.0, tk.END)
        self.log_text.configure(state='disabled')
        
    def update_stats(self, stats):
        """Update the statistics display"""
        self.successes = stats["success"]
        self.failures = stats["failed"]
        self.total = stats["total"]
        self.elapsed = stats["elapsed"]
        self.rps = stats["requests_per_second"]
        self.peak_rps = stats["peak_rps"]
        self.average_time = stats["avg_time"]
        self.status_codes = stats.get("status_codes", {})
        self.has_responses = stats.get("has_responses", False)
        
        # Update labels
        self.success_label.config(text=str(self.successes))
        self.failed_label.config(text=str(self.failures))
        self.total_label.config(text=str(self.total))
        self.elapsed_label.config(text=f"{self.elapsed:.2f}s")
        self.rps_label.config(text=f"{self.rps:.2f}")
        self.peak_rps_label.config(text=f"{self.peak_rps:.2f}")
        self.avg_time_label.config(text=f"{self.average_time:.4f}s")
        
        # Calculate success rate
        if self.total > 0:
            success_rate = (self.successes / self.total) * 100
        else:
            success_rate = 0
        self.success_rate_label.config(text=f"{success_rate:.1f}%")
        
        # Update progress bar
        try:
            target = int(self.num_requests_var.get())
            progress = min(100, int((self.total / max(1, target)) * 100))
            self.progress_bar["value"] = progress
        except ValueError:
            pass
            
        # Update status codes display
        self.update_status_codes_display(self.status_codes)
        
        # Enable/disable download button based on whether we have responses
        if self.has_responses and not self.is_running:
            self.download_button.config(state=tk.NORMAL)
        else:
            self.download_button.config(state=tk.DISABLED)
        
    def start_test(self):
        """Start the request flood test"""
        if not self.validate_input():
            return
            
        if self.is_running:
            return
            
        self.is_running = True
        self.start_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        
        # Clear previous results
        self.clear_log()
        self.update_stats({
            "success": 0,
            "failed": 0,
            "total": 0,
            "elapsed": 0,
            "requests_per_second": 0,
            "peak_rps": 0,
            "avg_time": 0,
            "status_codes": {}
        })
        
        # Get parameters
        url = self.url_var.get().strip()
        num_requests = int(self.num_requests_var.get())
        concurrency = int(self.concurrency_var.get())
        batch_size = int(self.batch_size_var.get())
        analyze_content = self.analyze_content_var.get()
        save_responses = self.save_responses_var.get()
        search_text = self.search_text_var.get() if analyze_content else ""
        
        # Log test parameters
        self.log(f"Starting test with the following parameters:")
        self.log(f"Target URL: {url}")
        self.log(f"Number of requests: {num_requests}")
        self.log(f"Concurrency: {concurrency}")
        self.log(f"Batch size: {batch_size}")
        self.log(f"Analyze content: {'Yes' if analyze_content else 'No'}")
        self.log(f"Save response data: {'Yes' if save_responses else 'No'}")
        
        # Create the controller
        self.stats = RequestStats()
        self.analyzer = ContentAnalyzer()
        if search_text:
            self.analyzer.add_text_search(search_text)
            
        self.controller = FloodController(
            url=url,
            stats=self.stats,
            analyzer=self.analyzer
        )
        self.controller.should_analyze_content = analyze_content
        self.controller.should_save_responses = save_responses
        
        # Configure proxy settings based on selection
        if self.use_proxy_var.get():
            # Single proxy
            proxy_url = self.proxy_url_var.get().strip()
            proxy_username = self.proxy_username_var.get().strip()
            proxy_password = self.proxy_password_var.get()
            
            self.controller.set_proxy(True, proxy_url, proxy_username, proxy_password)
            
            self.log(f"Using proxy: {proxy_url}")
            if proxy_username:
                self.log(f"Proxy authentication: Enabled")
            else:
                self.log(f"Proxy authentication: None")
                
        elif self.use_proxy_file_var.get():
            # Proxy file
            proxy_count = self.proxy_manager.get_count()
            rotation_method = self.proxy_rotation_method_var.get()
            
            # Set the proxy list in the controller
            self.controller.set_proxy_list(
                self.proxy_manager.proxies,
                use_rotation=True
            )
            
            self.log(f"Using proxy rotation with {proxy_count} proxies")
            self.log(f"Rotation method: {rotation_method}")
            
            # Sample of proxies to be used
            self.log("\nSample of proxies to be used:")
            for i, proxy in enumerate(self.proxy_manager.proxies[:3]):
                self.log(f"  {i+1}. {proxy.get('url', 'N/A')}")
                
            if proxy_count > 3:
                self.log(f"  ... and {proxy_count - 3} more")
        else:
            # No proxy
            self.controller.set_proxy(False)
            self.log("No proxy configured")
            
        if search_text:
            self.log(f"Search text: '{search_text}'")
            
        self.log("")
        self.log("Test is running... please wait.")
        
        # Run the test in the asyncio thread
        async def run_test():
            try:
                await self.controller.flood(num_requests, concurrency, batch_size)
                return True
            except Exception as e:
                return str(e)
                
        future = self.asyncio_thread.run_coro(run_test())
        future.add_done_callback(self.on_test_complete)
        
        # Start the update timer
        self.update_stats_ui()
        
    def update_stats_ui(self):
        """Update the stats UI periodically during the test"""
        if not self.is_running:
            return
            
        # Get the current stats
        async def get_current_stats():
            if self.stats:
                return await self.stats.get_stats()
            return None
            
        future = self.asyncio_thread.run_coro(get_current_stats())
        future.add_done_callback(lambda f: self.update_stats(f.result()) if f.result() else None)
        
        # Schedule the next update
        self.update_id = self.root.after(100, self.update_stats_ui)
        
    def on_test_complete(self, future):
        """Called when the test is complete"""
        result = future.result()
        
        if result is True:
            self.log("\nTest completed successfully!")
        else:
            self.log(f"\nTest failed with error: {result}")
            
        self.is_running = False
        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
        
        # Cancel the update timer
        if self.update_id:
            self.root.after_cancel(self.update_id)
            self.update_id = None
            
        # Final stats update
        async def get_final_stats():
            if self.stats:
                return await self.stats.get_stats()
            return None
            
        future = self.asyncio_thread.run_coro(get_final_stats())
        future.add_done_callback(lambda f: self.update_stats(f.result()) if f.result() else None)
        
        # Show summary
        self.log("\n" + "="*60)
        self.log(f"SUMMARY:")
        self.log(f"- Successful requests: {self.successes}")
        self.log(f"- Failed requests: {self.failures}")
        self.log(f"- Total requests: {self.total}")
        self.log(f"- Elapsed time: {self.elapsed:.2f} seconds")
        self.log(f"- Average response time: {self.average_time:.4f} seconds")
        self.log(f"- Requests per second: {self.rps:.2f}")
        self.log(f"- Peak RPS: {self.peak_rps:.2f}")
        
        if self.total > 0:
            success_rate = (self.successes / self.total) * 100
            self.log(f"- Success rate: {success_rate:.1f}%")
            
        # Show status code distribution
        self.log("\nSTATUS CODE DISTRIBUTION:")
        if self.status_codes:
            sorted_codes = sorted(self.status_codes.items(), key=lambda x: x[1], reverse=True)
            for code, count in sorted_codes:
                code_desc = self.get_status_code_description(code)
                self.log(f"- HTTP {code} {code_desc}: {count} requests")
        else:
            self.log("- No status codes recorded")
            
        self.log("="*60)
        
    def stop_test(self):
        """Stop the test if it's running"""
        if not self.is_running:
            return
            
        self.log("\nStopping test...")
        self.is_running = False
        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
        
        # Cancel the update timer
        if self.update_id:
            self.root.after_cancel(self.update_id)
            self.update_id = None
        
    def download_responses(self):
        """Download the response data as JSON file"""
        if not self.has_responses or not self.stats:
            messagebox.showerror("No Data", "No response data available to download.")
            return
            
        # Get a file name to save to
        file_path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            title="Save Response Data As"
        )
        
        if not file_path:
            return  # User cancelled the dialog
            
        # Get the responses from the stats object
        async def get_responses_data():
            if self.stats:
                return await self.stats.get_responses()
            return []
            
        future = self.asyncio_thread.run_coro(get_responses_data())
        
        def save_responses_to_file(future):
            try:
                responses = future.result()
                
                # Proxy info for metadata
                proxy_info = None
                if self.use_proxy_var.get():
                    proxy_info = {
                        "type": "single",
                        "url": self.proxy_url_var.get()
                    }
                elif self.use_proxy_file_var.get():
                    proxy_info = {
                        "type": "rotation",
                        "count": self.proxy_manager.get_count(),
                        "method": self.proxy_rotation_method_var.get()
                    }
                
                # Add metadata
                data = {
                    "metadata": {
                        "url": self.url_var.get(),
                        "timestamp": datetime.now().isoformat(),
                        "total_requests": self.total,
                        "successful_requests": self.successes,
                        "failed_requests": self.failures,
                        "average_response_time": self.average_time,
                        "requests_per_second": self.rps,
                        "proxy": proxy_info
                    },
                    "status_code_distribution": self.status_codes,
                    "responses": responses
                }
                
                # Save to file
                with open(file_path, 'w') as f:
                    json.dump(data, f, indent=2)
                    
                messagebox.showinfo("Download Complete", 
                                  f"Response data has been saved to:\n{file_path}")
                
            except Exception as e:
                messagebox.showerror("Download Failed", 
                                   f"Failed to save response data: {str(e)}")
                
        future.add_done_callback(save_responses_to_file)
        
    def on_close(self):
        """Called when the window is closed"""
        if self.is_running:
            if not messagebox.askyesno("Confirm Exit", 
                                       "A test is currently running. Are you sure you want to exit?"):
                return
                
        # Stop the asyncio thread
        self.asyncio_thread.stop()
        self.root.destroy()


def main():
    root = tk.Tk()
    app = RequestFloodApp(root)
    root.mainloop()
    

if __name__ == "__main__":
    main()

# Developed by Upendra Khanal