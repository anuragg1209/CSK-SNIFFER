import csv
import pandas as pd
import argparse
import sys


def check_csk(csk_file_path, inverted_index_path):
    """
    Checks for errors in the CSK file based on the inverted index.
    Writes errors to 'error_set.tsv' if a relation is missing between labels.
    Args:
        csk_file_path (str): Path to the CSK CSV file.
        inverted_index_path (str): Path to the inverted index TSV file.
    """
    csv.field_size_limit(10000000)
    with open(csk_file_path) as csv_file:
        csk_data = pd.read_csv(csv_file, index_col=0)
    labels = list(csk_data.columns)

    with open(inverted_index_path) as tsv_file:
        tsv_reader = csv.reader(tsv_file, delimiter="\t")
        for row in tsv_reader:
            # row example: ['person,is_near,bicycle', 'test1.csv,test4.csv']
            if len(row) < 2:
                continue  # skip malformed rows
            triple_str, img_ids = row[0], row[1]
            triple = triple_str.split(',')
            if len(triple) != 3:
                continue  # skip malformed triples
            label1, relation, label2 = triple

            # Skip if both labels are vehicles/person and relation is 'overlapsWith'
            if (
                label1 in ['person', 'truck', 'bus', 'car'] and
                label2 in ['person', 'truck', 'bus', 'car'] and
                relation == 'overlapsWith'
            ):
                continue

            if label1 in labels and label2 in labels:
                cell_value = csk_data.loc[label1][label2]
                relations = [rel.strip() for rel in str(cell_value).split(',')]
                if relation not in relations:
                    with open("error_set.tsv", "a+") as outfile:
                        outfile.write(f"{img_ids}\t{triple_str}\t{label1},{cell_value},{label2}\n")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='CSK error checker (csk_error_checker.py)',
        usage="\npython csk_error_checker.py\t --csk_dir \t --inverted_index_dir"
    )
    parser.add_argument(
        '--csk_dir',
        action='store',
        dest='csk_dir',
        required=True,
        help='Directory where CSK file is stored'
    )
    parser.add_argument(
        '--inverted_index_dir',
        action='store',
        dest='inverted_index_dir',
        required=True,
        help='Directory where inverted_index is stored'
    )
    args = parser.parse_args()
    check_csk(args.csk_dir, args.inverted_index_dir)
