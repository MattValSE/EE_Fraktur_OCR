import os
import pandas as pd
import shutil
import duckdb

# Path to your list of newspapers + blocks (TSV or CSV)
db_path = "duckdb/main.duckdb" 
output_folder = "src/datasets/gold/collected_images"

# Create the output folder
os.makedirs(output_folder, exist_ok=True)

conn = duckdb.connect(db_path)


base_dir = "src/datasets/silver/scanned"

# Query your list
rows = conn.execute("""
    SELECT distinct newspaper, block
    FROM block_quality
    WHERE correct_ind IN ('C','Y')
      AND line_amt > 1
""").fetchall()

print(f"Found {len(rows)} blocks to copy")

for newspaper, block_xml in rows:

    block_jpg = os.path.splitext(block_xml)[0] + ".jpg"
    src_path = os.path.join(base_dir, newspaper, "image", block_jpg)

    if os.path.isfile(src_path):
        # Always prefix the newspaper name to avoid duplicates and missing info
        dst_filename = f"{newspaper}_{block_jpg}"
        dst_path = os.path.join(output_folder, dst_filename)

        shutil.copy2(src_path, dst_path)
        print(f"Copied {src_path} -> {dst_path}")
    else:
        print(f"WARNING: Missing image {src_path}")
