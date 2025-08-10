#!/usr/bin/env python3
"""
Test script to verify the cleanup functionality
"""

import os
import shutil
from flask_app import cleanup_previous_search

def create_test_files():
    """Create some test files to simulate a previous search"""
    print("Creating test files...")
    
    # Create test images
    os.makedirs('static/Images', exist_ok=True)
    with open('static/Images/test1.jpg', 'w') as f:
        f.write('fake image data')
    with open('static/Images/test2.png', 'w') as f:
        f.write('fake image data')
    
    # Create test CSV files
    os.makedirs('csv_files', exist_ok=True)
    with open('csv_files/test1.csv', 'w') as f:
        f.write('test csv data')
    
    # Create test TSV files
    os.makedirs('tsv_files', exist_ok=True)
    with open('tsv_files/collocations.tsv', 'w') as f:
        f.write('test tsv data')
    with open('tsv_files/inverted_index.tsv', 'w') as f:
        f.write('test tsv data')
    
    # Create test error file
    with open('error_set.tsv', 'w') as f:
        f.write('test error data')
    
    print("Test files created successfully!")

def test_cleanup():
    """Test the cleanup function"""
    print("\nTesting cleanup function...")
    
    # Create test files first
    create_test_files()
    
    # Verify files exist
    print("\nBefore cleanup - checking if files exist:")
    print(f"Images exist: {os.path.exists('static/Images/test1.jpg')}")
    print(f"CSV exists: {os.path.exists('csv_files/test1.csv')}")
    print(f"TSV exists: {os.path.exists('tsv_files/collocations.tsv')}")
    print(f"Error file exists: {os.path.exists('error_set.tsv')}")
    
    # Run cleanup
    print("\nRunning cleanup...")
    cleanup_previous_search()
    
    # Verify files are deleted
    print("\nAfter cleanup - checking if files are deleted:")
    print(f"Images deleted: {not os.path.exists('static/Images/test1.jpg')}")
    print(f"CSV deleted: {not os.path.exists('csv_files/test1.csv')}")
    print(f"TSV deleted: {not os.path.exists('tsv_files/collocations.tsv')}")
    print(f"Error file deleted: {not os.path.exists('error_set.tsv')}")
    
    # Verify KB file is preserved
    print(f"KB file preserved: {os.path.exists('KB-CSK-SNIFFER.csv')}")
    
    print("\nCleanup test completed!")

if __name__ == "__main__":
    test_cleanup()
