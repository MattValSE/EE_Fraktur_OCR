import os
import json

## Exclude json files with no corresponding images

def read_images_as_strings():
    base_image = "src/datasets/silver/scanned_jpg"
    image_names = []
    for filename in os.listdir(base_image):
        if filename.lower().endswith(".jpg"):
            name = os.path.splitext(filename)[0]
            image_names.append(name)
    return set(image_names)

def batch_convert():
    image_names = read_images_as_strings()
    base_dir = "src/datasets/silver/scanned"
    gold = "src/datasets/gold/scanned"
    for subdir in os.listdir(base_dir):
        subpath = os.path.join(base_dir, subdir)
        full_path = os.path.join(subpath, 'json/fulltext.json')
        output_subdir = os.path.join(gold, subdir)
        output_final = os.path.join(output_subdir, 'json/fulltext.json')
        if os.path.isfile(full_path):
            if subdir in image_names:
                os.makedirs(os.path.dirname(output_final), exist_ok=True)
                with open(full_path, 'r', encoding="utf-8") as f:
                    result = json.load(f)
                with open(output_final, "w", encoding="utf-8") as f:
                    json.dump(result, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    batch_convert()