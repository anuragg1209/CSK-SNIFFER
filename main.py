from subprocess import Popen, PIPE
import argparse


def invoke_scripts(args):

    p0 = Popen(['python', 'image_downloader.py', '--search-string', f'{args.image_search_term}', '--output', f'{args.image_output_dir}'], stdin=PIPE, stdout=PIPE, stderr=PIPE)
    out0, err0 = p0.communicate()
    print(f"working0 with err {err0} and\n output {out0}")

    p1 = Popen(['python', 'yolo_json_to_csv.py', '--input_dir', f'{args.image_output_dir}', '--output_dir', f'{args.yolo_output_dir}', '--yolo_dir', f'{args.yolo_dir}'], stdin=PIPE, stdout=PIPE, stderr=PIPE)
    out1, err1 = p1.communicate()
    print(f"working1 with err {err1} and\n output {out1}")

    p2 = Popen(['python', 'collocation_detector.py', '--input_dir', f'{args.yolo_output_dir}', '--output_dir', f'{args.collocations_output_dir}'], stdin=PIPE, stdout=PIPE, stderr=PIPE)
    out2, err2 = p2.communicate()
    print(f"working2 with err {err2} and\n output {out2}")

    p3 = Popen(['python', 'csk_error_checker.py', '--csk_dir', f'{args.csk_in_dir}', '--inverted_index_dir', f'{args.index_dir}'],stdin=PIPE, stdout=PIPE, stderr=PIPE)
    out3, err3 = p3.communicate()
    print(f"working3 with err {err3} and\n output {out3}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='End to end script',
                                     usage="\n\npython main.py"
                                           "\t --image_output_dir "
                                           "\t --yolo_output_dir "
                                           "\t --yolo_dir "
                                           "\t --image_search_term"
                                           "\t --collocations_output_dir"
                                           "\t --csk_in_dir"
                                           "\t --index_dir")


    parser.add_argument('--image_search_term',
                        action='store',
                        dest='image_search_term',
                        required=True,
                        help='Collect images using this search term e.g., kids on boat')

    parser.add_argument('--image_output_dir',
                        action='store',
                        dest='image_output_dir',
                        default=f'static/Images/',
                        required=False,
                        help='Path where downloaded Images will be stored')
    parser.add_argument('--yolo_output_dir',
                        action='store',
                        dest='yolo_output_dir',
                        default='output/csv_files/',
                        required=False,
                        help='CSV files output directory location (default: output/csv_files/)')
    parser.add_argument('--yolo_dir',
                        action='store',
                        dest='yolo_dir',
                        default='yolo/darkflow/',
                        required=False,
                        help='Directory where your YOLO model is present')
    parser.add_argument('--collocations_output_dir',
                        action='store',
                        dest='collocations_output_dir',
                        default='output/tsv_files/',
                        required=False,
                        help='Collocations_map output directory location (default: output/tsv_files/)')
    parser.add_argument('--csk_in_dir',
                        action='store',
                        dest='csk_in_dir',
                        default='KB-CSK-SNIFFER.csv',
                        required=False,
                        help='Directory where csk file is stored')
    parser.add_argument('--index_dir',
                        action='store',
                        dest='index_dir',
                        default='output/tsv_files/inverted_index.tsv',
                        required=False,
                        help='Directory where inverted_index is stored (default: output/tsv_files/inverted_index.tsv)')

    args = parser.parse_args()
    invoke_scripts(args=args)