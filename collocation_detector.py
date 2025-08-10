import pandas as pd
import argparse
import os
import operator
from collections import OrderedDict


class Rect:
    def __init__(self, coord_x1, coord_y1, coord_x2, coord_y2):
        self.x1 = coord_x1
        self.y1 = coord_y1
        self.x2 = coord_x2
        self.y2 = coord_y2

    def overlapsWith(self, rect2):
        return self.x1 <= rect2.x2 and self.x2 >= rect2.x1 and self.y1 <= rect2.y2 and self.y2 >= rect2.y1

    def is_above(self, rect2):
        return self.y2 <= rect2.y1 and rect2.x2 > self.x1 and rect2.x1 < self.x2

    def is_below(self, rect2):
        return self.y1 >= rect2.y2 and rect2.x2 > self.x1 and rect2.x1 < self.x2

    def is_inside(self, rect2):
        return self.x1 >= rect2.x1 and self.y1 >= rect2.y1 and self.x2 <= rect2.x2 and self.y2 <= rect2.y2

    def is_near(self, rect2):
        return self.x2 < rect2.x1 and self.y1 < rect2.y2 and self.y2 > rect2.y1


def compile_input_files(dir_or_file_path):
    input_is_directory = os.path.isdir(dir_or_file_path)
    input_files = []
    if input_is_directory:
        input_dir = os.fsencode(dir_or_file_path)
        for infile_bytename in os.listdir(input_dir):
            infile_fullpath = os.path.join(
                input_dir.decode("utf-8"), infile_bytename.decode("utf-8"))
            input_files.append(infile_fullpath)
    else:
        input_files.append(dir_or_file_path)
    return input_files


def serialize_in_pieces(out_dir_path, max_items_in_a_piece, items):
    print(f"Writing {len(items)} items to directory: {out_dir_path}")
    if not os.path.exists(out_dir_path):
        os.makedirs(out_dir_path)

    curr_file_num = 1
    curr_file = open(f"{out_dir_path}/{curr_file_num}.txt", 'w')

    for item_num, item in enumerate(items):
        if item_num % max_items_in_a_piece == 0 and item_num > 1:
            # close the old file.
            curr_file.close()
            # open a new file.
            curr_file_num += 1
            curr_file = open(f"{out_dir_path}/{curr_file_num}.txt", "w")

        curr_file.write(item)
        if "\n" not in item:
            curr_file.write("\n")

    if not curr_file.closed:
        curr_file.close()


def add_key_to_map_arr(key, value, map_):
    if key not in map_:
        map_[key] = []
    map_[key].append(value)


def sort_map_by_value(dic, reverse_order=True):
    an_ordered_dict = OrderedDict()
    for k, v in sorted(dic.items(), key=operator.itemgetter(1), reverse=reverse_order):
        an_ordered_dict[k] = v
    return an_ordered_dict


def topk(ordered_dic, k, as_str, separator="\n"):
    tops = []
    for item_num, (x, value) in enumerate(ordered_dic.items()):
        if item_num >= k:
            break
        tops.append(x)
    return separator.join(tops) if as_str else tops


def add_to_counter_map(_map, key, increment_by=1):
    if _map is None:
        print(f"WARNING! map is not initialized. (add_to_counter_map). Cannot increment counter for key: {key}")
        return
    if key is None:
        print(f"WARNING! key to insert in (add_to_counter_map) is None.")
        return
    if key not in _map:
        _map[key] = 0
    _map[key] += increment_by


def reader(filename):
    df = pd.read_csv(filename)
    return filename, df


def construct_triple(obj1, rel, obj2, sep=","):
    return f"{obj1}{sep}{rel}{sep}{obj2}"


def collocations_in(obj1, rect1, rect1_area, obj2, rect2, rect2_area):
    triples = []
    ################################################
    #  The following are non-commutative relations
    ################################################
    if rect1.is_inside(rect2):
        if rect1_area>5000:
            triples.append(construct_triple(obj1=obj1, rel='is_inside', obj2=obj2))
    if rect2.is_inside(rect1):
        if rect2_area>5000:
            triples.append(construct_triple(obj1=obj2, rel='is_inside', obj2=obj1))
    if rect1.is_above(rect2):
        if rect1_area>7500:
          triples.append(construct_triple(obj1=obj1, rel='is_above', obj2=obj2))
          triples.append(construct_triple(obj1=obj2, rel='is_below', obj2=obj1))
    if rect1.is_below(rect2):
        if rect2_area>7500:
          triples.append(construct_triple(obj1=obj1, rel='is_below', obj2=obj2))
          triples.append(construct_triple(obj1=obj2, rel='is_above', obj2=obj1))
        ################################################
    #  The following are commutative relations
    ################################################
    if rect1.overlapsWith(rect2) or rect2.overlapsWith(rect1):
        triples.append(obj1 + ',overlapsWith,' + obj2)
        triples.append(obj2 + ',overlapsWith,' + obj1)
    if rect1.is_near(rect2):
        triples.append(obj1 + ',is_near,' + obj2)
        triples.append(obj2 + ',is_near,' + obj1)

    return triples

def all_collocations_in_img(df, img_id, inverted_index, collocations_map):
    ''' Updates collocation map and inverted_index
    @param: df: csv data that looks like this:
        #label,confidence,top_left_x,top_left_y,bottom_right_x,bottom_right_y
          person,0.16,158,529,181,562
      person,0.51,838,488,881,594
      ball,0.15,906,502,927,566
      bike,0.52,899,486,933,599
    @param: img_id: e.g., "img_675.png"
    @param: inverted_index: # triple -> arr_of_img_ids
    @param: collocations_map: # triple -> count
    '''
    num_rows = len(df.index)
    # Only upper triangular matrix is considered.
    local_c_m = dict()

    for i in range(num_rows):
        for j in range(i + 1, num_rows):
            obj1 = (df.iloc[i]["label"])
            obj2 = (df.iloc[j]["label"])
            rect1 = Rect(coord_x1=int(df.iloc[i]["top_left_x"]), coord_y1=int(df.iloc[i]["top_left_y"]),
                         coord_x2=int(df.iloc[i]["bottom_right_x"]), coord_y2=int(df.iloc[i]["bottom_right_y"]))
            rect2 = Rect(coord_x1=int(df.iloc[j]["top_left_x"]), coord_y1=int(df.iloc[j]["top_left_y"]),
                         coord_x2=int(df.iloc[j]["bottom_right_x"]), coord_y2=int(df.iloc[j]["bottom_right_y"]))
            rect1_area=df.iloc[i]["BBox_area"]
            rect2_area=df.iloc[j]["BBox_area"]
            for triple in collocations_in(obj1, rect1, rect1_area, obj2, rect2, rect2_area):
                add_to_counter_map(_map=local_c_m, key=triple)

    update_inverted_index(local_c_m, inverted_index, img_id=img_id.split('/')[-1])
    update_collocation_map(local_c_m, collocations_map)

def update_collocation_map(local_c_m, collocations_map):
        for k, v in local_c_m.items():
            add_to_counter_map(_map=collocations_map, key=k, increment_by=v)

def update_inverted_index(collocations_map, inverted_index, img_id):
    ''' Operations are in place.
    @param: collocations_map: # triple -> count
    @param: inverted_index: # triple -> list of image_ids.
    '''
    for k, v in collocations_map.items():  # e.g., person overlaps_with ball -> 2
        add_key_to_map_arr(key=k, value=img_id.split('.')[0],
                           map_=inverted_index)  # e.g., person overlaps_with ball -> [img_id_5, img_id_72 ...]p
    #print(f"inverted_index: {inverted_index}")
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Code to generate spatial collocations',
                                     usage="\n\npython collocation_detector.py"
                                           "\t --input_dir "
                                           "\t --output_dir")

    parser.add_argument('--input_dir',
                        action='store',
                        dest='input_dir',
                        required=True,
                        help='Directory where csv file is stored')

    parser.add_argument('--output_dir',
                        action='store',
                        dest='output_dir',
                        required=True,
                        help='Directory where resulting collocations_map and inverted_index is stored')

    args = parser.parse_args()
    inverted_index = {}  # triple -> arr_of_img_ids
    collocations_map = {}  # triple -> count
    for infile_path in compile_input_files(dir_or_file_path=args.input_dir):
            img_id, df = reader(infile_path)
            all_collocations_in_img(df,img_id,inverted_index,collocations_map)

    # Save collocations map
    with open(f"{args.output_dir}/collocations.tsv", 'w') as outfile_collocations:
        for k, v in sort_map_by_value(collocations_map).items():
            outfile_collocations.write(f"{k}\t{v}\n")

    print(f"inverted_index :{inverted_index}")
    # Save inverted index
    with open(f"{args.output_dir}/inverted_index.tsv", 'w') as outfile_inverted_index:
        for k, v in inverted_index.items():
            formatted_image_ids = ",".join(v)
            outfile_inverted_index.write(f"{k}\t{formatted_image_ids}\n")

    print(f"Sample Top-20 collocations are:\n{topk(ordered_dic=collocations_map, k=20, as_str=True)}")
    print(f"\n\nOutput written to directory: {args.output_dir}")
