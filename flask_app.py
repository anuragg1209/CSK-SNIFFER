"""
CSK Sniffer Flask Application

A web interface for the CSK Sniffer tool that processes images and analyzes
commonsense knowledge relationships between detected objects.
"""

import os
import shutil
import logging
from pathlib import Path
from subprocess import Popen, PIPE
from typing import Dict, List, Optional, Any, Tuple

import pandas as pd
from flask import Flask, render_template, request, session, send_from_directory

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
class Config:
    """Application configuration with sensible defaults and environment variable support."""
    
    # Server configuration
    HOST = os.getenv('FLASK_HOST', '127.0.0.1')
    PORT = int(os.getenv('FLASK_PORT', 6007))
    DEBUG = os.getenv('FLASK_DEBUG', 'True').lower() == 'true'
    
    # File paths and directories
    STATIC_DIR = Path('static')
    IMAGES_DIR = STATIC_DIR / 'Images'
    CSV_DIR = Path('csv_files')
    TSV_DIR = Path('tsv_files')
    
    # File patterns
    IMAGE_EXTENSIONS = ('.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp')
    CSV_EXTENSION = '.csv'
    TSV_EXTENSION = '.tsv'
    
    # Important files
    KB_FILE = Path('KB-CSK-SNIFFER.csv')
    ERROR_FILE = Path('error_set.tsv')
    COLLOCATIONS_FILE = TSV_DIR / 'collocations.tsv'
    INVERTED_INDEX_FILE = TSV_DIR / 'inverted_index.tsv'
    
    # Main script
    MAIN_SCRIPT = Path('main.py')

# Initialize Flask app
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = str(Config.IMAGES_DIR)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'dev-secret-key-change-in-production')


def ensure_directories_exist() -> None:
    """Ensure all required directories exist."""
    directories = [Config.IMAGES_DIR, Config.CSV_DIR, Config.TSV_DIR]
    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)
        logger.info(f"Ensured directory exists: {directory}")


def cleanup_previous_search() -> None:
    """
    Clean up files from previous searches to ensure clean state for new search.
    
    Removes:
    - Image files from the images directory
    - CSV files from csv_files directory
    - TSV files from tsv_files directory
    - error_set.tsv file
    
    Preserves:
    - KB-CSK-SNIFFER.csv (original KB file)
    """
    try:
        # Clean up images directory
        if Config.IMAGES_DIR.exists():
            for file_path in Config.IMAGES_DIR.iterdir():
                if file_path.is_file() and file_path.suffix.lower() in Config.IMAGE_EXTENSIONS:
                    file_path.unlink()
                    logger.info(f"Deleted image: {file_path.name}")
                elif file_path.is_dir():
                    shutil.rmtree(file_path)
                    logger.info(f"Deleted directory: {file_path.name}")
        
        # Clean up CSV files
        if Config.CSV_DIR.exists():
            for file_path in Config.CSV_DIR.glob(f"*{Config.CSV_EXTENSION}"):
                file_path.unlink()
                logger.info(f"Deleted CSV: {file_path.name}")
        
        # Clean up TSV files
        if Config.TSV_DIR.exists():
            for file_path in Config.TSV_DIR.glob(f"*{Config.TSV_EXTENSION}"):
                file_path.unlink()
                logger.info(f"Deleted TSV: {file_path.name}")
        
        # Clean up error file
        if Config.ERROR_FILE.exists():
            Config.ERROR_FILE.unlink()
            logger.info("Cleaned up error_set.tsv")
        
        # Increment cache buster to force browser to reload images
        current_buster = session.get('cache_buster', 1)
        session['cache_buster'] = current_buster + 1
        logger.info(f"Cache buster incremented to: {session['cache_buster']}")
        
        logger.info("Cleanup completed successfully!")
        
    except Exception as e:
        logger.error(f"Error during cleanup: {e}")
        # Don't raise the exception to prevent the app from crashing


def run_main_script(query: str) -> Tuple[bytes, bytes]:
    """
    Run the main.py script with the given query.
    
    Args:
        query: The search term to process
        
    Returns:
        Tuple of (stdout, stderr) from the subprocess
    """
    if not Config.MAIN_SCRIPT.exists():
        raise FileNotFoundError(f"Main script not found: {Config.MAIN_SCRIPT}")
    
    cmd = ['python', str(Config.MAIN_SCRIPT), '--image_search_term', query]
    process = Popen(cmd, stdin=PIPE, stdout=PIPE, stderr=PIPE)
    stdout, stderr = process.communicate()
    
    logger.info(f"Main script execution completed with return code: {process.returncode}")
    if stderr:
        logger.warning(f"Main script stderr: {stderr.decode()}")
    if stdout:
        logger.info(f"Main script stdout: {stdout.decode()}")
    
    return stdout, stderr


def get_image_files() -> List[Dict[str, Any]]:
    """
    Get list of image files with metadata.
    
    Returns:
        List of dictionaries containing image file information
    """
    try:
        if not Config.IMAGES_DIR.exists():
            return []
        
        # Get all image files and sort them properly
        image_paths = []
        for file_path in Config.IMAGES_DIR.iterdir():
            if file_path.is_file() and file_path.suffix.lower() in Config.IMAGE_EXTENSIONS:
                image_paths.append(file_path)
        
        # Sort files by extracting the number from the filename
        def extract_number(filename):
            # Extract number from "Image X.jpg" format
            import re
            match = re.search(r'Image\s*(\d+)', filename)
            if match:
                return int(match.group(1))
            return 0
        
        # Sort by the extracted number
        image_paths.sort(key=lambda x: extract_number(x.name))
        
        # Create the image files list with proper indexing
        image_files = []
        for i, file_path in enumerate(image_paths, 1):
            image_files.append({
                'filename': file_path.name,
                'caption': f'Image {i}',
                'index': i
            })
        
        return image_files
        
    except Exception as e:
        logger.error(f"Error loading images: {e}")
        return []


def has_any_output_files() -> bool:
    """
    Check if any output files exist from a previous search.
    
    Returns:
        True if any output files exist, False otherwise
    """
    return (Config.COLLOCATIONS_FILE.exists() or 
            Config.INVERTED_INDEX_FILE.exists() or
            Config.ERROR_FILE.exists() or
            any(Config.IMAGES_DIR.glob("*")))


def get_status_info() -> Dict[str, Any]:
    """
    Get current application status information.
    
    Returns:
        Dictionary containing status information
    """
    status_info = {
        'current_query': session.get('current_query', 'No active search'),
        'search_id': session.get('search_id', 'No session'),
        'images_count': 0,
        'csv_files_count': 0,
        'tsv_files_count': 0,
        'has_error_file': False,
        'has_any_output': False
    }
    
    # Count files
    if Config.IMAGES_DIR.exists():
        image_files = list(Config.IMAGES_DIR.glob(f"*{Config.IMAGE_EXTENSIONS[0]}"))
        for ext in Config.IMAGE_EXTENSIONS[1:]:
            image_files.extend(Config.IMAGES_DIR.glob(f"*{ext}"))
        status_info['images_count'] = len(image_files)
    
    if Config.CSV_DIR.exists():
        csv_files = list(Config.CSV_DIR.glob(f"*{Config.CSV_EXTENSION}"))
        status_info['csv_files_count'] = len(csv_files)
    
    if Config.TSV_DIR.exists():
        tsv_files = list(Config.TSV_DIR.glob(f"*{Config.TSV_EXTENSION}"))
        status_info['tsv_files_count'] = len(tsv_files)
    
    status_info['has_error_file'] = Config.ERROR_FILE.exists()
    status_info['has_any_output'] = has_any_output_files()
    
    return status_info


# Route handlers
@app.route('/')
def search_page():
    """Render the main search page."""
    # Check if there are existing search results
    has_results = has_any_output_files()
    return render_template('search_page.html', has_results=has_results)


@app.route('/', methods=['GET', 'POST'])
def process_search():
    """Handle search form submission and process the query."""
    if request.method == 'POST':
        query = request.form.get('t', '').strip()
        
        if not query:
            return render_template('search_page.html', error="Please enter a search term.", has_results=has_any_output_files())
        
        try:
            # Store search info in session
            session['current_query'] = query
            session['search_id'] = f"search_{len(session)}"
            
            # Clean up previous search files
            cleanup_previous_search()
            
            # Run the main processing script
            stdout, stderr = run_main_script(query)
            
            logger.info(f"Search completed for query: {query}")
            return render_template('home_page.html', query=query)
            
        except Exception as e:
            logger.error(f"Error processing search '{query}': {e}")
            return render_template('search_page.html', 
                                 error=f"An error occurred while processing your search: {str(e)}",
                                 has_results=has_any_output_files())
    
    return render_template('search_page.html', has_results=has_any_output_files())


@app.route('/home_page')
def home_page():
    """Render the home page."""
    return render_template("home_page.html")


@app.route('/about')
def about_page():
    """Render the about page."""
    return render_template("about.html")


@app.route('/cleanup')
def manual_cleanup():
    """Manual cleanup route to clear all files from previous searches."""
    cleanup_previous_search()
    return render_template('search_page.html', 
                          message="All previous search files have been cleaned up. You can now perform a new search.",
                          has_results=False)


@app.route('/new_search')
def new_search():
    """New search route that cleans up previous files and redirects to search page."""
    cleanup_previous_search()
    return render_template('search_page.html', 
                          message="Previous search files have been cleared. You can now perform a new search.",
                          has_results=False)


@app.route('/clear_cache')
def clear_cache():
    """Route to manually clear browser cache by incrementing cache buster."""
    current_buster = session.get('cache_buster', 1)
    session['cache_buster'] = current_buster + 1
    logger.info(f"Cache manually cleared, buster incremented to: {session['cache_buster']}")
    return {'success': True, 'cache_buster': session['cache_buster']}


@app.route('/images/<filename>')
def serve_image(filename):
    """Serve images with cache control headers."""
    # Check if the image file exists
    image_path = Config.IMAGES_DIR / filename
    if not image_path.exists():
        return "Image not found", 404
    
    # Set cache control headers to prevent aggressive caching
    response = send_from_directory(Config.IMAGES_DIR, filename)
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    response.headers['Last-Modified'] = 'Thu, 01 Jan 1970 00:00:00 GMT'
    return response


@app.route('/status')
def status_page():
    """Show current search status and file information."""
    status_info = get_status_info()
    return render_template('status.html', status=status_info)


@app.route('/output_status')
def output_status():
    """Show detailed output file status."""
    status_info = get_status_info()
    
    # Check specific file statuses
    file_status = {
        'collocations': {
            'exists': Config.COLLOCATIONS_FILE.exists(),
            'name': 'Collocations Map (collocations.tsv)',
            'description': 'Contains spatial relationship data between detected objects'
        },
        'inverted_index': {
            'exists': Config.INVERTED_INDEX_FILE.exists(),
            'name': 'Inverted Index (inverted_index.tsv)',
            'description': 'Contains mapping between spatial relationships and image IDs'
        },
        'error_set': {
            'exists': Config.ERROR_FILE.exists(),
            'name': 'Error Set (error_set.tsv)',
            'description': 'Contains detected errors in object relationships'
        },
        'images': {
            'exists': status_info['images_count'] > 0,
            'name': f'Processed Images ({status_info["images_count"]} files)',
            'description': 'Downloaded and processed images from the search'
        }
    }
    
    return render_template('output_status.html', 
                         status=status_info, 
                         file_status=file_status)


@app.route('/get_images')
def get_images():
    """Display processed images."""
    image_files = get_image_files()
    if not image_files:
        return render_template("images.html", 
                             images=image_files,
                             error="No processed images available. Please run a search first to download and process images.")
    return render_template("images.html", images=image_files)


@app.route("/get_collocations_map")
def get_collocations_map():
    """Display collocations data."""
    try:
        if not Config.COLLOCATIONS_FILE.exists():
            return render_template("collocation.html", 
                                 name='Collocations Map', 
                                 data=pd.DataFrame(),
                                 error="The collocations.tsv output file is missing. This file contains spatial relationship data between detected objects. Please run a search first to generate this file.")
        
        data = pd.read_csv(Config.COLLOCATIONS_FILE, sep='\t')
        if data.empty:
            return render_template("collocation.html", 
                                 name='Collocations Map', 
                                 data=data,
                                 error="The collocations file exists but contains no data. This might indicate that no spatial relationships were detected in the processed images.")
        
        data.columns = ["Inferred spatial relation on predicted bounding boxes", "Frequency"]
        return render_template("collocation.html", name='Collocations Map', data=data)
        
    except Exception as e:
        logger.error(f"Error loading collocations: {e}")
        return render_template("collocation.html", 
                             name='Collocations Map', 
                             data=pd.DataFrame(),
                             error=f"Error loading collocations file: {str(e)}")


@app.route("/get_inverted_index")
def get_inverted_index():
    """Display inverted index data."""
    try:
        if not Config.INVERTED_INDEX_FILE.exists():
            return render_template("collocation.html", 
                                 name='Inverted Index', 
                                 data=pd.DataFrame(),
                                 error="The inverted_index.tsv output file is missing. This file contains the mapping between spatial relationships and image IDs. Please run a search first to generate this file.")
        
        data = pd.read_csv(Config.INVERTED_INDEX_FILE, sep='\t')
        if data.empty:
            return render_template("collocation.html", 
                                 name='Inverted Index', 
                                 data=data,
                                 error="The inverted index file exists but contains no data. This might indicate that no spatial relationships were detected in the processed images.")
        
        data.columns = ["Inferred spatial relation on predicted bounding boxes", "Image ID"]
        return render_template("collocation.html", name='Inverted Index', data=data)
        
    except Exception as e:
        logger.error(f"Error loading inverted index: {e}")
        return render_template("collocation.html", 
                             name='Inverted Index', 
                             data=pd.DataFrame(),
                             error=f"Error loading inverted index file: {str(e)}")


@app.route("/get_error_set")
def get_error_set():
    """Display error set data."""
    try:
        if not Config.ERROR_FILE.exists():
            # Check if any search has been performed by looking for other output files
            if has_any_output_files():
                # Create a DataFrame with a success message when no errors are detected
                success_data = pd.DataFrame({
                    "Status": ["SUCCESS"],
                    "Message": ["All objects were detected correctly as per the commonsense KB rules. No errors found."]
                })
                return render_template("collocation.html", 
                                     name='Error Set - No Errors Detected', 
                                     data=success_data)
            else:
                return render_template("collocation.html", 
                                     name='Error Set', 
                                     data=pd.DataFrame(),
                                     error="No error set data available. Please run a search first to generate output files and error analysis.")
        
        data = pd.read_csv(Config.ERROR_FILE, sep='\t')
        if data.empty:
            return render_template("collocation.html", 
                                 name='Error Set', 
                                 data=data,
                                 error="The error set file exists but contains no data. This might indicate that no errors were detected during processing.")
        
        data.columns = ["Image ID", "Inferred Spatial Relation on Predicted Bounding Boxes", 
                       "Expected Spatial Relation between these objects present in KB"]
        return render_template("collocation.html", name='Error Set', data=data)
        
    except Exception as e:
        logger.error(f"Error loading error set: {e}")
        return render_template("collocation.html", 
                             name='Error Set', 
                             data=pd.DataFrame(),
                             error=f"Error loading error set file: {str(e)}")


@app.route("/get_csk_graph")
def get_csk_graph():
    """Display commonsense knowledge graph data."""
    try:
        if not Config.KB_FILE.exists():
            return render_template("index.html", 
                                 name='Common Sense Knowledge Graph', 
                                 data=pd.DataFrame(),
                                 error="The KB-CSK-SNIFFER.csv file is missing. This file contains the commonsense knowledge base that the system uses for analysis.")
        
        data = pd.read_csv(Config.KB_FILE)
        if data.empty:
            return render_template("index.html", 
                                 name='Common Sense Knowledge Graph', 
                                 data=data,
                                 error="The KB file exists but contains no data. This might indicate that the knowledge base is empty or corrupted.")
        
        return render_template("index.html", name='Common Sense Knowledge Graph', data=data)
        
    except Exception as e:
        logger.error(f"Error loading CSK data: {e}")
        return render_template("index.html", 
                             name='Common Sense Knowledge Graph', 
                             data=pd.DataFrame(),
                             error=f"Error loading KB file: {str(e)}")


# Initialize application
if __name__ == "__main__":
    # Ensure all required directories exist
    ensure_directories_exist()
    
    # Start the Flask application
    logger.info(f"Starting CSK Sniffer Flask app on {Config.HOST}:{Config.PORT}")
    app.run(
        host=Config.HOST,
        port=Config.PORT,
        debug=Config.DEBUG
    )
