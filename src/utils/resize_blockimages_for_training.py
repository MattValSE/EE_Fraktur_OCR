from PIL import Image, ImageOps
import os

#Resize and pad the images for training

def resize_and_pad(img, height=64, max_width=512, padding_color="white"):
    # Resize while maintaining aspect ratio
    w, h = img.size
    new_w = int(w * height / h)
    img = img.resize((new_w, height), Image.LANCZOS)
    
    # Pad to max width
    if new_w > max_width:
        img = img.crop((0, 0, max_width, height))  # Optionally crop instead
    else:
        pad_width = max_width - new_w
        img = ImageOps.expand(img, (0, 0, pad_width, 0), fill=padding_color)
    
    return img


def process_all_papers_continuous():
    silver_root="src/datasets/silver/scanned"
    gold_root="src/datasets/gold/scanned"
    for paper_name in os.listdir(silver_root):
        paper_path = os.path.join(silver_root, paper_name)
        trg_paper_path = os.path.join(gold_root, paper_name)
        jpg_path = os.path.join(paper_path, "image")
        trg_jpg_path = os.path.join(trg_paper_path, "image")
        for image in jpg_path:
            if image.lower().endswith(".jpg") and image.startswith("TB"):
                img_path = os.path.join(jpg_path, image)
                img = Image.open(img_path)
                resized_img = resize_and_pad(img)
                save_path = os.path.join(trg_jpg_path, image)
                os.makedirs(os.path.dirname(save_path), exist_ok=True)
                resized_img.save(save_path)

        print(f"Processing: {paper_name}")

process_all_papers_continuous()