"""
YOLO JSON to CSV Converter

This script renames image files in a directory, runs YOLO object detection to generate JSON outputs,
and converts those outputs to CSV files. It is designed to be portable and easy to use in any environment.

Default image directory: static/Images
"""
import os
import json
import csv
import argparse
import subprocess
from typing import List

# Default directory for images
DEFAULT_IMAGES_DIR = os.path.join('static', 'Images')

IMAGE_EXTENSIONS = ('.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp')


def rename_files(images_dir: str) -> None:
    """
    Rename all image files in the directory to a standard format: Image 1.jpg, Image 2.jpg, ...
    """
    i = 1
    for filename in sorted(os.listdir(images_dir)):
        if filename.lower().endswith(IMAGE_EXTENSIONS):
            dst = f"Image {i}.jpg"
            src = os.path.join(images_dir, filename)
            dst = os.path.join(images_dir, dst)
            if src != dst:
                os.rename(src, dst)
            i += 1


def ensure_dir_exists(directory: str) -> None:
    """
    Ensure that a directory exists. If not, create it.
    """
    os.makedirs(directory, exist_ok=True)


def run_yolo_detector(yolo_dir: str, images_dir: str) -> None:
    """
    Run YOLO object detector to generate JSON outputs for images in images_dir.
    Changes to the YOLO directory, runs the command, and returns to the original directory.
    """
    command = [
        'python', 'flow',
        '--imgdir', images_dir + '/',
        '--model', 'cfg/yolo.cfg',
        '--load', 'bin/yolo.weights',
        '--json'
    ]
    original_dir = os.getcwd()
    try:
        os.chdir(yolo_dir)
        subprocess.run(command, check=True)
    finally:
        os.chdir(original_dir)


def convert_json_to_csv(json_dir: str, output_dir: str) -> None:
    """
    Convert all JSON files in json_dir to CSV files in output_dir.
    """
    ensure_dir_exists(output_dir)
    file_list = [f for f in os.listdir(json_dir) if f.endswith('.json')]
    for json_file in file_list:
        json_path = os.path.join(json_dir, json_file)
        csv_filename = os.path.splitext(json_file)[0] + '.csv'
        csv_path = os.path.join(output_dir, csv_filename)
        with open(json_path, 'r') as infile, open(csv_path, 'w', newline='') as outfile:
            csvwriter = csv.writer(outfile)
            header = ["label", "confidence", "top_left_x", "top_left_y", "bottom_right_x", "bottom_right_y", "BBox_area"]
            csvwriter.writerow(header)
            for line in infile:
                data = json.loads(line)
                for obj in data:
                    s = list(obj.values())
                    area = (s[3]["y"] - s[2]["y"]) * (s[3]["x"] - s[2]["x"])
                    row = [s[0], s[1], s[2]["x"], s[2]["y"], s[3]["x"], s[3]["y"], area]
                    csvwriter.writerow(row)

    
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description='Convert YOLO JSON outputs to CSV (yolo_json_to_csv.py)',
        usage="\n\npython yolo_json_to_csv.py"
              "\t --input_dir <images_dir>"
              "\t --output_dir <csv_output_dir>"
              "\t --yolo_dir <yolo_directory>"
    )
    parser.add_argument('--input_dir',
                        action='store',
                        dest='input_dir',
                        default=DEFAULT_IMAGES_DIR,
                        help=f'Directory where images are stored (default: {DEFAULT_IMAGES_DIR})')
    parser.add_argument('--output_dir',
                        action='store',
                        dest='output_dir',
                        required=True,
                        help='Directory where output CSV files will be stored')
    parser.add_argument('--yolo_dir',
                        action='store',
                        dest='yolo_dir',
                        required=True,
                        help='Directory where YOLO object detector resides')
    parser.add_argument('--yolo_out_dir',
                        action='store',
                        dest='yolo_out_dir',
                        default='out',
                        help='Subdirectory (inside input_dir) where YOLO outputs JSON (default: out)')
    args = parser.parse_args()

    # Step 1: Ensure images directory exists and rename files
    ensure_dir_exists(args.input_dir)
    rename_files(args.input_dir)

    # Step 2: Run YOLO detector
    run_yolo_detector(args.yolo_dir, args.input_dir)

    # Step 3: Convert YOLO JSON outputs to CSV
    yolo_json_dir = os.path.join(args.input_dir, args.yolo_out_dir)
    convert_json_to_csv(yolo_json_dir, args.output_dir)

