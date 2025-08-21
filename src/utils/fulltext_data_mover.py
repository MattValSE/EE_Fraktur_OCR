import os
import shutil

## Move images between layers

def move_images():
    base_dir = "./src/datasets/bronze/scanned"
    gold = "./src/datasets/gold/scanned"
    for subdir in os.listdir(base_dir):
        subpath = os.path.join(base_dir, subdir)
        image_path = os.path.join(subpath, f'image/{subdir}.jpg')
        output_subdir = os.path.join(gold, subdir, 'image')
        output_final = os.path.join(output_subdir, f'{subdir}.jpg')
        gold_json_subdir = os.path.join(gold, subdir, 'json')
        gold_json = os.path.join(gold_json_subdir, 'fulltext.json')
        #print(image_path)
        #print(os.path.isfile(image_path))
        if os.path.isfile(image_path):
            if os.path.isfile(gold_json):
                os.makedirs(output_subdir, exist_ok=True)
                shutil.copyfile(image_path, output_final)
                print(f"Moved {image_path} -> {output_final}")

if __name__ == "__main__":
    move_images()