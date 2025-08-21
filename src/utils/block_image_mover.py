import os
import shutil

def move_images():
    base_dir = "./src/datasets/silver/scanned"
    gold = "./src/datasets/gold/scanned"

    for subdir in os.listdir(base_dir):
        subpath = os.path.join(base_dir, subdir)
        image_dir = os.path.join(subpath, 'image')
        gold_json = os.path.join(gold, subdir, 'json', 'blocks.json')

        #if not os.path.isfile(gold_json):
        #    print(gold_json)
        #    continue  # Skip if blocks.json doesn't exist

        if not os.path.isdir(image_dir):
            print(image_dir)
            continue  # Skip if there's no image folder

        output_subdir = os.path.join(gold, subdir, 'image')
        os.makedirs(output_subdir, exist_ok=True)

        for fname in os.listdir(image_dir):
            if fname.lower().endswith(".jpg") and fname != f"{subdir}.jpg":
                src_path = os.path.join(image_dir, fname)
                dst_path = os.path.join(output_subdir, fname)
                shutil.copyfile(src_path, dst_path)
                print(f"Moved {src_path} -> {dst_path}")

if __name__ == "__main__":
    move_images()
