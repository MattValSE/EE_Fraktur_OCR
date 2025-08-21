import xml.etree.ElementTree as ET
from collections import defaultdict
from PIL import Image,ImageOps
import os
import json
#import shutil
import duckdb
import pandas as pd
import xml.etree.ElementTree as ET
from datetime import datetime

conn = duckdb.connect("duckdb/main.duckdb")  # For UPDATEs and COPY
write_conn = duckdb.connect("duckdb/main.duckdb")  # For UPDATEs and COPY

def parse_pagexml_blocks(xml_file):
    ns = {'pc': 'http://schema.primaresearch.org/PAGE/gts/pagecontent/2013-07-15'}
    tree = ET.parse(xml_file)
    root = tree.getroot()

    blocks = defaultdict(list)

    for textline in root.findall(".//pc:TextLine", ns):
        coords_el = textline.find("pc:Coords", ns)
        unicode_el = textline.find(".//pc:Unicode", ns)
        blockid_el = textline.find("pc:blockid", ns)

        if coords_el is None or blockid_el is None:
            continue  # skip malformed lines
        
        
        blockid = blockid_el.text.strip()
        points_str = coords_el.attrib["points"]
        points = [(int(x), int(y)) for x, y in (pt.split(",") for pt in points_str.strip().split())]

        x_coords = [x for x, y in points]
        y_coords = [y for x, y in points]

        x_min = min(x_coords)
        y_min = min(y_coords)
        x_max = max(x_coords)
        y_max = max(y_coords)

        width = x_max - x_min
        height = y_max - y_min
        text = unicode_el.text.strip() if unicode_el is not None and unicode_el.text else ""


        blocks[blockid].append({
            "x": x_min,
            "y": y_min,
            "width": width,
            "height": height,
            "text": text
        })

    return blocks


def save_block_pagexml(block_id, coords, scaled_lines, trg_paper_path, original_xml_path, crop_x, crop_y, scale, left_padding=3):
    """
    Saves a PAGE XML file for a given block with scaled coordinates and corrected bounding boxes.

    Args:
        block_id (str): The ID of the text block (TextRegion).
        coords (dict): A dictionary with the 'width' and 'height' of the final image.
        scaled_lines (list): A list of dictionaries, where each dictionary represents a
                             line and contains 'x', 'y', 'w', 'h', and 'text'.
                             This list should be sorted by the 'y' coordinate.
        trg_paper_path (str): The target directory path for the output paper.
        original_xml_path (str): The path to the original, uncropped PAGE XML file.
        crop_x (float): The x-offset of the cropped region in the original image.
        crop_y (float): The y-offset of the cropped region in the original image.
        scale (float): The scaling factor applied to the coordinates.
        left_padding (int, optional): Optional padding to add to the left of lines. Defaults to 3.
    """
    # Define the PAGE XML namespace
    ns = {'pc': 'http://schema.primaresearch.org/PAGE/gts/pagecontent/2013-07-15'}
    ET.register_namespace('', ns['pc'])

    # --- Correctly parse original XML to find baselines for the specific block ---
    all_scaled_baselines = []
    try:
        orig_tree = ET.parse(original_xml_path)
        orig_root = orig_tree.getroot()
        
        region_xpath = f".//pc:TextRegion[@id='{block_id}']"
        orig_region = orig_root.find(region_xpath, ns)

        if orig_region is not None:
            for tl in orig_region.findall("pc:TextLine", ns):
                baseline_elem = tl.find("pc:Baseline", ns)
                if baseline_elem is not None and baseline_elem.get("points"):
                    orig_points = baseline_elem.get("points").split()
                    scaled_points = []
                    for pt in orig_points:
                        x_str, y_str = pt.split(",")
                        x = (float(x_str) - crop_x) * scale - left_padding
                        y = (float(y_str) - crop_y) * scale
                        scaled_points.append(f"{int(x)},{int(y)}")
                    all_scaled_baselines.append(" ".join(scaled_points))
                else:
                    all_scaled_baselines.append(None)
    except ET.ParseError as e:
        print(f"Warning: Could not parse original XML file '{original_xml_path}'. Baselines will be estimated. Error: {e}")
    except FileNotFoundError:
        print(f"Warning: Original XML file not found at '{original_xml_path}'. Baselines will be estimated.")

    # Create the root for the new PAGE XML document
    root = ET.Element(f"{{{ns['pc']}}}PcGts")
    metadata = ET.SubElement(root, f"{{{ns['pc']}}}Metadata")
    now = datetime.now().isoformat()
    ET.SubElement(metadata, f"{{{ns['pc']}}}Creator").text = "save_block_pagexml (corrected)"
    ET.SubElement(metadata, f"{{{ns['pc']}}}Created").text = now
    ET.SubElement(metadata, f"{{{ns['pc']}}}LastChange").text = now

    page = ET.SubElement(root, f"{{{ns['pc']}}}Page", {
        "imageWidth": str(coords["width"]),
        "imageHeight": str(coords["height"])
    })

    # --- Filter out empty lines while keeping track of original index for baseline matching ---
    indexed_filtered_lines = []
    for i, line in enumerate(scaled_lines):
        if line.get("text", "").strip():
            indexed_filtered_lines.append({'original_index': i, 'line_data': line})

    if not indexed_filtered_lines:
        print(f"Warning: Block {block_id} contains no valid text lines after filtering. Skipping XML creation.")
        return

    text_region = ET.SubElement(page, f"{{{ns['pc']}}}TextRegion", {"id": block_id})

    for i, item in enumerate(indexed_filtered_lines):
        original_index = item['original_index']
        line = item['line_data']
        
        text_line = ET.SubElement(text_region, f"{{{ns['pc']}}}TextLine", {"id": f"{block_id}_line{i}"})

        x_new = int(line["x"]) - left_padding
        w_new = int(line["w"]) + left_padding
        h_new = int(line["h"])

        # --- FIX: Interpret y-coordinate as the TOP of the line box ---
        # This corrects the box position based on user feedback.
        y_top = int(line["y"])
        y_bottom = y_top + h_new # Calculate the bottom by adding the height

        # Construct the Coords string with the correct top and bottom y-values
        coords_str = f"{x_new},{y_top} {x_new+w_new},{y_top} {x_new+w_new},{y_bottom} {x_new},{y_bottom}"
        ET.SubElement(text_line, f"{{{ns['pc']}}}Coords", {"points": coords_str})

        # Set the Baseline using the corrected index.
        # The fallback baseline should be the bottom of the box.
        if original_index < len(all_scaled_baselines) and all_scaled_baselines[original_index] is not None:
            baseline_str = all_scaled_baselines[original_index]
        else:
            # Fallback baseline is the bottom edge of the coordinate box
            baseline_str = f"{x_new},{y_bottom} {x_new+w_new},{y_bottom}"
        ET.SubElement(text_line, f"{{{ns['pc']}}}Baseline", {"points": baseline_str})

        # Add the text content of the line
        text_equiv = ET.SubElement(text_line, f"{{{ns['pc']}}}TextEquiv")
        ET.SubElement(text_equiv, f"{{{ns['pc']}}}Unicode").text = line.get("text", "")

    # Ensure the target directory exists and save the new XML file
    block_xml_dir = os.path.join(trg_paper_path, "pagexml")
    os.makedirs(block_xml_dir, exist_ok=True)
    block_xml_path = os.path.join(block_xml_dir, f"{block_id}.xml")

    tree = ET.ElementTree(root)
    tree.write(block_xml_path, encoding="UTF-8", xml_declaration=True)

def compute_block_bboxes(blocks):
    block_bboxes = {}
    
    for blockid, lines in blocks.items():
        x_min = min(line['x'] for line in lines)
        y_min = min(line['y'] for line in lines)
        x_max = max(line['x'] + line['width'] for line in lines)
        y_max = max(line['y'] + line['height'] for line in lines)
        if x_min == x_max:
            x_max = x_max * 2
        if y_min == y_max:
            y_max = y_max * 2
        
        block_key = blockid[3:] 

        block_bboxes[block_key] = {
            "x": x_min,
            "y": y_min,
            "width": x_max - x_min,
            "height": y_max - y_min,
            "lines": [
                {
                    "x": line["x"],
                    "y": line["y"],
                    "w": line["width"],
                    "h": line["height"],
                    "text": line["text"]
                }
                for line in lines
            ]
        }

    return block_bboxes

"""
def resize_and_pad(img, target_widths=[512, 1024, 2048], max_height=2048, padding_color="white"):

    w, h = img.size
    
    # Choose appropriate width tier
    if w <= target_widths[0]:
        target_width = target_widths[0]
    elif w <= target_widths[1]:
        target_width = target_widths[1]
    else:
        target_width = target_widths[2]
    
    # Resize to target width
    new_h = int(h * target_width / w)
    img = img.resize((target_width, new_h), Image.LANCZOS)
    
    # Cap height if necessary
    if new_h > max_height:
        img = img.resize((target_width, max_height), Image.LANCZOS)
        new_h = max_height
    
    pad_height = 0  # No height padding in this version
    return img, pad_height

def insert_image(block_id, block_value, path, paper_path,trg_paper_path):
# Load the image
    img = Image.open(path)

    padding_x = 10 # Images seemed cut of from the left 
    # Define the block (example values)
    x = max(block_value["x"] - padding_x, 1)  
    y = max(block_value["y"] , 1) 
    width = block_value["width"] + padding_x  
    height = block_value["height"] 
    # Calculate bottom-right corner
    right = x + width
    bottom = y + height

    # Crop the image
    cropped = img.crop((x, y, right, bottom))

    # Get the new size
    _, original_h = cropped.size
    # Pad and conform to a certain size for training
    resized_img, pad_width = resize_and_pad(cropped)

    resized_img.save(os.path.join(trg_paper_path, "image", f"{block_id}.jpg"))
    
    scale = resized_img.height / original_h

    return scale, x, y
"""

def resize_img(img,x, y, right, bottom):
    max_dim = 1024
    cropped = img.crop((x, y, right, bottom))
    if right <= x or bottom <= y:
        raise ValueError(f"Invalid crop box: right <= x or bottom <= y")
    width, height = cropped.size
    if max(width, height) <= max_dim:
        return cropped
    if width > height:
        aspect_ratio = height / width
        new_width = max_dim
        new_height = max(1, int(new_width * aspect_ratio))
    else:
        aspect_ratio = width / height
        new_height = max_dim
        new_width = max(1, int(new_height * aspect_ratio))
    resized_img = cropped.resize((new_width, new_height), Image.Resampling.LANCZOS)

    return resized_img

def insert_image(block_id, block_value, path, paper_path,trg_paper_path):
# Load the image
    img = Image.open(path)

    padding_x = 10 # Images seemed cut of from the left 
    # Define the block (example values)
    x = max(block_value["x"] - padding_x, 0)  
    y = max(block_value["y"] , 0) 
    width = block_value["width"] + padding_x  
    height = block_value["height"] 
    # Calculate bottom-right corner
    right = min(x + width, img.width)
    bottom = min(y + height, img.height)
  
    
    # Crop the image
    resized_img = resize_img(img,x, y, right, bottom)
    resized_img = resized_img.convert('RGB')

    #resized_img.save(os.path.join(trg_paper_path, "image", f"{block_id}.jpg"))
    try:
        save_path = os.path.join(trg_paper_path, "image", f"{block_id}.jpg")
        resized_img.save(save_path)
        #print(f"Saved image {block_id}, size {resized_img.size}, at {save_path}")
    except Exception as e:
        print(f"Failed to save image {block_id}: {e}")
    scale = resized_img.height / height

    return scale, x, y

def update_json(trg_json, block_id, block_data,scaled_lines):
    # Load existing data or start fresh
    if os.path.isfile(trg_json):
        try: 
            with open(trg_json, "r", encoding="utf-8") as f:
                block_info = json.load(f)
        except (json.JSONDecodeError, ValueError):
            # File exists but is empty or invalid, start fresh
            block_info = {}
    else:
        block_info = {}

    # Insert or update block
    block_info[block_id] = {
        "x": block_data["x"],
        "y": block_data["y"],
        "w": block_data["width"],
        "h": block_data["height"],
        "lines" : scaled_lines
    }

    # Write back to file
    os.makedirs(os.path.dirname(trg_json), exist_ok=True)
    with open(trg_json, "w", encoding="utf-8") as f:
        json.dump(block_info, f, indent=2, ensure_ascii=False)

def pypdf_update(paper_name,block_id,nws_text, coords, crop_x, crop_y, scale):
    text_row_list = nws_text.split("\n")
    block_text = []
    
    x0 = coords['x']
    y0 = coords['y']
    x1 = x0 + coords['width']
    y1 = y0 + coords['height']
    ##print(text_row_list)
    #exit()
    parsed_lines = []
    for text_row in text_row_list:
        if "[" in text_row and "]" in text_row:
            try:
                # Extract coordinate string
                coord_str = text_row.split("[")[-1].split("]")[0]
                x_old, y_old = map(int, coord_str.split(","))
                #print(coord_str)
                #print(x_old,y_old)

                # Check if point is within the bounding box
                if x0 <= x_old <= x1 and y0 <= y_old <= y1:
                    x_new = int((x_old - crop_x) * scale)
                    y_new = int((y_old - crop_y) * scale)
                    #print(block_id)
                    #print(text_row)
                    #print(f"Box: {x0},{x1},{y0}, {y1}")
                    #print(x_old, y_old)

                    # Extract the prefix (before the coordinates)
                    prefix = text_row.split("[")[0].strip()
                    #print(prefix)
                    parsed_lines.append({
                        "text": prefix,
                        "x": x_new,
                        "y": y_new
                    })
                    
            except Exception as e:
                print(f"Failed to parse line: {text_row} ({e})")
                continue
    parsed_lines_sorted = sorted(parsed_lines, key=lambda l: (round(l["y"] / 10), l["x"]))
    block_text = [f"{line['text']} [{line['x']},{line['y']}]" for line in parsed_lines_sorted]
    block_text_str = "\n".join(block_text).strip()
    non_block_text = [f"{line['text']}" for line in parsed_lines_sorted]
    non_block_text_str =  "\n".join(non_block_text).strip()
    #print(block_text_str)
    #if paper_name == 'postimeesew19390716.1.1' and block_id == 'TB00040':
    #    print(text_row_list)
    #    exit()

    df_pypdf = pd.DataFrame(columns=["Newspaper", "Block", "Source", "Text", "Type"])
    df_pypdf_nc = pd.DataFrame(columns=["Newspaper", "Block", "Source", "Text", "Type"])

    if block_text_str:
        df_pypdf = pd.DataFrame([{
                    "Newspaper": paper_name,
                    "Block": block_id,
                    "Source": 'split_blocks_pypdf',
                    "Text": block_text_str,
                    'Type': 'N/A'
                    }])
        
    if non_block_text_str and block_text_str:
        df_pypdf_nc = pd.DataFrame([{
                    "Newspaper": paper_name,
                    "Block": block_id,
                    "Source": 'split_blocks_pypdf_no_coord',
                    "Text": non_block_text_str,
                    'Type': 'N/A'
                    }])

    df_combined_ppdf = pd.concat([df_pypdf, df_pypdf_nc], ignore_index=True)
        #print(df_combined)

    if not df_combined_ppdf.empty:
        write_conn.register("df", df_combined_ppdf)

        write_conn.execute("""
                INSERT INTO Full_Text (Text, Source, Type,Block, Newspaper, Timestamp)
                SELECT df.Text, df.Source, df.Type,df.Block, df.Newspaper, CURRENT_TIMESTAMP
                FROM df
                WHERE NOT EXISTS(SELECT 1 FROM Full_Text WHERE
                df.Newspaper = Full_Text.Newspaper
                AND Full_Text.Source = df.Source
                AND Full_Text.Type = df.Type
                AND Full_Text.Block = df.Block
                           )
                """)


    

def update_full_text(block_id,paper_name,scaled_lines):
    coords_list = []
    full_coords_list = []
    no_coord_lines  = []
    for line in scaled_lines:
        text = line.get("text", "").strip().replace("\n", " ")
        x, y, w, h = line["x"], line["y"], line["w"], line["h"]
        line_str = f"{text} [{x},{y}]" # Removed height and width to conform to OLMOCR anchoring outputs
        coords_list.append(line_str)
    for line in scaled_lines:
        text_nc = line.get("text", "").strip().replace("\n", " ")
        no_coord_lines.append(str(text_nc))
    for line in scaled_lines:
        text = line.get("text", "").strip().replace("\n", " ")
        x, y, w, h = line["x"], line["y"], line["w"], line["h"]
        line_str = f"{text} [{x},{y},{w},{h}]" # Removed height and width to conform to OLMOCR anchoring outputs
        full_coords_list.append(line_str)

    df_with_coords = pd.DataFrame([{
                "Newspaper": paper_name,
                "Block": block_id,
                "Source": 'split_blocks.py',
                "Text": "\n".join(coords_list),
                'Type': 'N/A'
                }])
    
    df_no_coords = pd.DataFrame([{
    "Newspaper": paper_name,
    "Block": block_id,
    "Source": 'split_blocks_no_coords',
    "Text": "\n".join(no_coord_lines),
    'Type': 'N/A'
    }])

    df_combined = pd.concat([df_with_coords, df_no_coords], ignore_index=True)
    #print(df_combined)
    write_conn.register("df", df_combined)

    write_conn.execute("""
            INSERT INTO Full_Text (Text, Source, Type,Block, Newspaper, Timestamp)
            SELECT df.Text, df.Source, df.Type,df.Block, df.Newspaper, CURRENT_TIMESTAMP
            FROM df
            WHERE NOT EXISTS(SELECT 1 FROM Full_Text WHERE
            df.Newspaper = Full_Text.Newspaper
            AND Full_Text.Source = df.Source
            AND Full_Text.Type = df.Type
            AND Full_Text.Block = df.Block
                       )
            """)


def process_all_papers_continuous(bronze_root="src/datasets/bronze/scanned", silver_root="src/datasets/silver/scanned"):
    # Optional
    #write_conn.execute("""
    #        DELETE FROM  Full_Text where Source IN( 'split_blocks.py','split_blocks_no_coords')
    #        """)
    
    for paper_name in os.listdir(bronze_root):
        paper_path = os.path.join(bronze_root, paper_name)
        pagexml_path = os.path.join(paper_path, "transkribus", "page.xml")
        jpg_path = os.path.join(paper_path, "image", f"{paper_name}.jpg")
        
        trg_paper_path = os.path.join(silver_root, paper_name)
        excess_img_path = os.path.join(trg_paper_path, "image")
        trg_json = os.path.join(trg_paper_path, "json", "blocks.json") 

        # Optional , but needed as of development as format changed of files
        #if os.path.isdir(excess_img_path):
        #    for filename in os.listdir(excess_img_path):
        #        file_path = os.path.join(excess_img_path, filename)
        #        if os.path.isfile(file_path):
        #            os.remove(file_path)  # Remove the file
        #            #print(f"Deleted file: {filename}")
        #if os.path.isfile(trg_json):
        #    os.remove(trg_json)
        #if not os.path.isfile(pagexml_path):
        #    continue
        #if not os.path.isfile(jpg_path):
        #    continue
        if os.path.isfile(pagexml_path):
            #print(f"Processing: {paper_name}")
            blocks = parse_pagexml_blocks(pagexml_path)
            block_bboxes = compute_block_bboxes(blocks)
            cursor = conn.execute(f"""
                     SELECT Text
                     FROM Full_Text anc
                     WHERE
                     Source = 'anchoring.py' 
                     AND Newspaper = TRIM('{paper_name}')      
                     AND Text is not null     
                     AND NOT EXISTS(SELECT 1 FROM Full_Text trg_ft WHERE
                     anc.Newspaper = trg_ft.Newspaper
                     AND trg_ft.Source = 'split_blocks_pypdf'
                     AND trg_ft.Type = anc.Type
                     AND trg_ft.Block = anc.Block
                     ) 
                     """)
            row = cursor.fetchone()
            #print(row)
            nws_text = row[0]
            #print(nws_text)
            #exit()

            #if paper_name ==  'sakalaew19361118.1.6':
                #print(nws_text)
            #    print(1)
            #else:
            #    continue


            for block_id, coords in block_bboxes.items():
                #if block_id == 'TB00004':
                scale, crop_x, crop_y = insert_image(block_id, coords, jpg_path, paper_path,trg_paper_path)
                scaled_lines = [
                    {
                    "x": int((line["x"] - crop_x) * scale),
                    "y": int((line["y"] - crop_y) * scale),
                    "w": int(line["w"] * scale),
                    "h": int(line["h"] * scale),
                    "text": line.get("text", "").strip()
                    }
                    for line in coords["lines"]
                    ]
                #print(scaled_lines)
                update_json(trg_json, block_id, coords,scaled_lines)
                save_block_pagexml(block_id, coords, scaled_lines, trg_paper_path, pagexml_path, crop_x, crop_y, scale)
                update_full_text( block_id,paper_name,scaled_lines)
                pypdf_update(paper_name,block_id, nws_text, coords, crop_x, crop_y, scale)


process_all_papers_continuous()
write_conn.execute("""
        COPY Full_Text TO 'duckdb/full_text.parquet' (FORMAT PARQUET);
        """)
write_conn.commit()
write_conn.close()
conn.close()