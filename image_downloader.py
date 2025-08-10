import argparse
import hashlib
import imghdr
import os
import pickle
import posixpath
import re
import signal
import socket
import ssl
import threading
import time
import urllib.parse
import urllib.request
import urllib.error

# Configuration constants
DEFAULT_OUTPUT_DIR = './bing'
DEFAULT_TIMEOUT = 2
DEFAULT_LIMIT = 5
DEFAULT_THREADS = 20
DEFAULT_IMAGES_PER_REQUEST = 35
MAX_CONCURRENT_DOWNLOADS = 10
SLEEP_INTERVAL = 0.1
DELAY_BETWEEN_KEYWORDS = 10

# User agent for web requests
USER_AGENT = 'Mozilla/5.0 (X11; Fedora; Linux x86_64; rv:94.0) Gecko/20100101 Firefox/94.0'

# Global state variables
output_dir = DEFAULT_OUTPUT_DIR
socket.setdefaulttimeout(DEFAULT_TIMEOUT)

# Create SSL context to bypass certificate verification
ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE

# Global tracking variables
tried_urls = []
image_md5s = {}
in_progress = 0
image_counter = 0  # Global counter for sequential image naming
successful_downloads = 0  # Counter for successfully downloaded images
urlopenheader = {'User-Agent': USER_AGENT}


def download(pool_sema: threading.Semaphore, img_sema: threading.Semaphore, url: str, output_dir: str, limit: int):
    """
    Download an image from the given URL with sequential naming.
    Args:
        pool_sema: Semaphore to limit concurrent downloads
        img_sema: Semaphore to control image processing
        url: URL of the image to download
        output_dir: Directory to save the image
        limit: Maximum number of images to download
    """
    global in_progress, image_counter, successful_downloads

    if url in tried_urls:
        print('SKIP: Already checked url, skipping')
        return
    pool_sema.acquire()
    in_progress += 1
    acquired_img_sema = False

    # Get the original file extension from the URL and clean it
    path = urllib.parse.urlsplit(url).path
    original_filename = posixpath.basename(path).split('?')[0]  # Strip GET parameters from filename
    _, file_extension = os.path.splitext(original_filename)

    # Clean the file extension (remove any extra characters like !d, etc.)
    file_extension = file_extension.lower()  # Convert to lowercase
    # Remove any non-alphanumeric characters after the dot, keep only the main extension
    if '.' in file_extension:
        # Extract just the main extension (e.g., .jpg from .jpg!d)
        clean_extension = re.sub(r'[^a-zA-Z0-9]', '', file_extension[1:])  # Remove non-alphanumeric
        if clean_extension in ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp']:
            file_extension = f'.{clean_extension}'
        else:
            file_extension = '.jpg'  # Default to jpg if unknown extension
    else:
        file_extension = '.jpg'  # Default to jpg if no extension found

    # Generate filename with current counter (will be updated if successful)
    filename = f"Image{image_counter + 1}{file_extension}"

    try:
        request = urllib.request.Request(url, None, urlopenheader)
        image = urllib.request.urlopen(request, context=ssl_context).read()

        # Determine the actual image format from content
        image_format = imghdr.what(None, image)
        if not image_format:
            print('SKIP: Invalid image, not saving ' + filename)
            return

        # Update file extension based on actual image format
        if image_format in ['jpeg', 'jpg']:
            file_extension = '.jpg'
        elif image_format == 'png':
            file_extension = '.png'
        else:
            file_extension = '.jpg'  # Default fallback

        # Update filename with correct extension
        filename = f"Image{image_counter + 1}{file_extension}"

        md5_key = hashlib.md5(image).hexdigest()
        if md5_key in image_md5s:
            print('SKIP: Image is a duplicate of ' + image_md5s[md5_key] + ', not saving ' + filename)
            return

        # Check if we've reached the limit
        if limit is not None and successful_downloads >= limit:
            return

        # Check if the sequential filename already exists
        if os.path.exists(os.path.join(output_dir, filename)):
            # Check if the existing file is the same image (by MD5)
            try:
                with open(os.path.join(output_dir, filename), 'rb') as f:
                    existing_md5 = hashlib.md5(f.read()).hexdigest()
                if existing_md5 == md5_key:
                    print('SKIP: Already downloaded ' + filename + ', not saving')
                    return
            except (OSError, IOError):
                # File might be corrupted or unreadable, skip this image
                print('SKIP: Corrupted file ' + filename + ', skipping')
                return
            # If different image, skip this one (we want exact limit)
            print('SKIP: Filename conflict ' + filename + ', skipping')
            return

        image_md5s[md5_key] = filename

        img_sema.acquire()
        acquired_img_sema = True

        # Save the image to file
        with open(os.path.join(output_dir, filename), 'wb') as imagefile:
            imagefile.write(image)

        # Only increment counter after successful save
        image_counter += 1
        successful_downloads += 1
        print(" OK : " + filename)
        tried_urls.append(url)
    except Exception as e:
        print(f"FAIL: {filename} - {str(e)}")
    finally:
        pool_sema.release()
        if acquired_img_sema:
            img_sema.release()
        in_progress -= 1


def fetch_images_from_keyword(pool_sema: threading.Semaphore, img_sema: threading.Semaphore, keyword: str,
                              output_dir: str, filters: str, limit: int):
    """
    Fetch images from Bing search results for a given keyword.
    Args:
        pool_sema: Semaphore to limit concurrent downloads
        img_sema: Semaphore to control image processing
        keyword: Search keyword
        output_dir: Directory to save images
        filters: Search filters to apply
        limit: Maximum number of images to download
    """
    current_offset = 0
    last_link = ''

    while True:
        time.sleep(SLEEP_INTERVAL)

        if in_progress > MAX_CONCURRENT_DOWNLOADS:
            continue

        # Build Bing search URL
        request_url = (f'https://www.bing.com/images/async?q={urllib.parse.quote_plus(keyword)}'
                      f'&first={current_offset}&count={DEFAULT_IMAGES_PER_REQUEST}'
                      f'&qft={filters or ""}')

        try:
            request = urllib.request.Request(request_url, None, headers=urlopenheader)
            response = urllib.request.urlopen(request, context=ssl_context)
            html = response.read().decode('utf8')
            image_links = re.findall('murl&quot;:&quot;(.*?)&quot;', html)

            if not image_links:
                print(f'FAIL: No search results for "{keyword}"')
                return

            if image_links[-1] == last_link:
                return  # No new results

            for link in image_links:
                # Check if we've already reached the limit
                if limit is not None and successful_downloads >= limit:
                    print(f"Reached limit of {limit} images, stopping downloads")
                    return
                thread = threading.Thread(target=download, args=(pool_sema, img_sema, link, output_dir, limit))
                thread.start()
                current_offset += 1

            last_link = image_links[-1]

        except (urllib.error.URLError, urllib.error.HTTPError) as e:
            print(f'FAIL: Network error for "{keyword}": {str(e)}')
            return
        except Exception as e:
            print(f'FAIL: Unexpected error for "{keyword}": {str(e)}')
            return


def backup_history(*args):
    """
    Backup download history to a pickle file.
    Called on program exit or interrupt.
    """
    history_file_path = os.path.join(output_dir, 'download_history.pickle')
    try:
        with open(history_file_path, 'wb') as download_history:
            pickle.dump(tried_urls, download_history)
            # Create a copy to avoid modification during dumping
            copied_image_md5s = dict(image_md5s)
            pickle.dump(copied_image_md5s, download_history)
        print('Download history backed up successfully')
    except Exception as e:
        print(f'FAIL: Could not backup history: {str(e)}')

    if args:
        exit(0)

def load_download_history():
    """Load previous download history from pickle file."""
    history_file_path = os.path.join(output_dir, 'download_history.pickle')
    try:
        with open(history_file_path, 'rb') as download_history:
            global tried_urls, image_md5s
            tried_urls = pickle.load(download_history)
            image_md5s = pickle.load(download_history)
        print('Loaded previous download history')
    except (OSError, IOError):
        print('No previous download history found, starting fresh')
        tried_urls = []


def process_search_file(search_file_path, pool_sema, img_sema, output_dir_origin, filters, limit):
    """Process multiple keywords from a file."""
    try:
        with open(search_file_path, 'r') as input_file:
            keywords = input_file.readlines()
    except (OSError, IOError) as e:
        print(f"FAIL: Couldn't open file {search_file_path}: {str(e)}")
        exit(1)

    for keyword in keywords:
        keyword = keyword.strip()
        if not keyword:  # Skip empty lines
            continue

        # Reset counters for each new keyword
        global image_counter, successful_downloads
        image_counter = 0
        successful_downloads = 0

        output_sub_dir = os.path.join(output_dir_origin, keyword.replace(' ', '_'))
        if not os.path.exists(output_sub_dir):
            os.makedirs(output_sub_dir)

        print(f"Processing keyword: {keyword}")
        fetch_images_from_keyword(pool_sema, img_sema, keyword, output_sub_dir, filters, limit)
        print(f"Downloaded {successful_downloads} images for keyword: {keyword}")
        backup_history()
        time.sleep(DELAY_BETWEEN_KEYWORDS)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Bing image bulk downloader (image_downloader.py)')
    parser.add_argument('-s', '--search-string', help='Keyword to search', required=False)
    parser.add_argument('-f', '--search-file', help='Path to a file containing search strings line by line',
                        required=False)
    parser.add_argument('-o', '--output', help='Output directory', required=False, 
                        default='static/Images/')
    parser.add_argument('--adult-filter-off', help='Disable adult filter', action='store_true', required=False)
    parser.add_argument('--filters',
                        help='Any query based filters you want to append when searching for images, e.g. +filterui:license-L1',
                        required=False)
    parser.add_argument('--limit', help='Make sure not to search for more than specified amount of images.',
                        required=False, type=int, default=DEFAULT_LIMIT)
    parser.add_argument('--threads', help='Number of threads', type=int, default=DEFAULT_THREADS)
    
    args = parser.parse_args()
    
    # Validate arguments
    if (not args.search_string) and (not args.search_file):
        parser.error('Provide either search string or path to file containing search strings')
    
    # Set output directory
    if args.output:
        output_dir = args.output
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    output_dir_origin = output_dir
    
    # Set up signal handler for graceful exit
    signal.signal(signal.SIGINT, backup_history)
    
    # Load previous download history
    load_download_history()
    
    # Configure adult filter if requested
    if args.adult_filter_off:
        urlopenheader['Cookie'] = 'SRCHHPGUSR=ADLT=OFF'
    
    # Create semaphores for thread control
    pool_sema = threading.BoundedSemaphore(args.threads)
    img_sema = threading.Semaphore()
    
    # Process search request
    if args.search_string:
        print(f"Searching for: {args.search_string}")
        fetch_images_from_keyword(pool_sema, img_sema, args.search_string, output_dir, args.filters, args.limit)
        print(f"Downloaded {successful_downloads} images for keyword: {args.search_string}")
    elif args.search_file:
        process_search_file(args.search_file, pool_sema, img_sema, output_dir_origin, args.filters, args.limit)
