#!/usr/bin/env python3
"""
Test script to verify SSL fix for image downloading
"""
import ssl
import urllib.request
import urllib.parse

# Create SSL context to bypass certificate verification
ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE

# Test URL (a simple image)
test_url = "https://httpbin.org/image/png"

try:
    # Test the SSL context with a simple request
    request = urllib.request.Request(test_url)
    response = urllib.request.urlopen(request, context=ssl_context)
    print("SSL fix test: SUCCESS - SSL context works correctly")
    print(f"Response status: {response.status}")
    print(f"Response length: {len(response.read())} bytes")
except Exception as e:
    print(f"SSL fix test: FAILED - {e}")
