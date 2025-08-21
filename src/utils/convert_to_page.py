import os
import xml.etree.ElementTree as ET
import subprocess
import html
from bs4 import BeautifulSoup
from PIL import Image
import fitz  # PyMuPDF

def safe_int(val, default=0):
    try:
        return int(val)
    except (ValueError, TypeError):
        return default

def get_pdf_dimensions(page_sizes_file, subdir):
    """
    Reads the page_sizes file and retrieves the real_pdf_width and real_pdf_height
    for the given subdir.

    Args:
        page_sizes_file (str): Path to the page_sizes file.
        subdir (str): The subdir to match.

    Returns:
        tuple: (real_pdf_width, real_pdf_height) if found, otherwise (None, None).
    """
    if not os.path.exists(page_sizes_file):
        print(f"Error: Page sizes file '{page_sizes_file}' not found.")
        return None, None

    with open(page_sizes_file, "r", encoding="utf-8") as file:
        for line in file:
            parts = line.strip().split()
            if len(parts) >= 3 and parts[0].startswith(subdir):
                real_pdf_width = int(parts[1])
                real_pdf_height = int(parts[2])
                return real_pdf_width, real_pdf_height

    print(f"No matching entry found in page_sizes for subdir '{subdir}'.")
    return None, None

def convert_veridian_to_pagexml(page_dir, subdir):
    text_dir = os.path.join(page_dir, 'text')
    image_dir = os.path.join(page_dir, 'image')
    transkribus_dir = os.path.join(page_dir, 'transkribus')
    os.makedirs(transkribus_dir, exist_ok=True)

    # File to store BlockCompletelyCorrect results
    block_correct_file = "src/datasets/bronze/metadata/block_correct_ind.txt"

    page_sizes_file = "src/datasets/bronze/scanned/metadata/page_sizes.txt"
    real_pdf_width, real_pdf_height = get_pdf_dimensions(page_sizes_file, subdir)
    if real_pdf_width is None or real_pdf_height is None:
        print(f"Skipping {subdir} due to missing dimensions.")
        return

    # Collect image
    image_path = os.path.join(image_dir, f"{subdir}.jpg")
    pdf_path = os.path.join(image_dir, f"{subdir}.pdf")
    if not os.path.exists(image_path):
        try:
            subprocess.run(
                ["convert", "-density", "300", pdf_path, "-quality", "90", "-resize", "2479x3508!", image_path],
                check=True
            )
            print(f"Converted {pdf_path} to {image_path}")
        except subprocess.CalledProcessError as e:
            print(f"Error during PDF to image conversion: {e}")
            return

    if not os.path.exists(image_path):
        print(f"No image found in {image_dir} after conversion.")
        return

    img = Image.open(image_path)
    target_width, target_height = img.size
    scale_x = target_width / real_pdf_width
    scale_y = target_height / real_pdf_height

    # --- PAGE-XML building ---
    root = ET.Element(
        "PcGts",
        xmlns="http://schema.primaresearch.org/PAGE/gts/pagecontent/2013-07-15",
        attrib={
            "xmlns:xsi": "http://www.w3.org/2001/XMLSchema-instance",
            "xsi:schemaLocation": "http://schema.primaresearch.org/PAGE/gts/pagecontent/2013-07-15 http://schema.primaresearch.org/PAGE/gts/pagecontent/2013-07-15/pagecontent.xsd"
        }
    )

    page_xml = ET.SubElement(root, "Page", imageFilename=os.path.basename(image_path),
                              imageWidth=str(target_width), imageHeight=str(target_height))
    reading_order = ET.SubElement(page_xml, "ReadingOrder")
    group = ET.SubElement(reading_order, "OrderedGroup", id="ro_1", caption="Regions reading order")
    region = ET.SubElement(page_xml, "TextRegion", id="tr_1", orientation="0.0", custom="readingOrder {index:0;}")
    ET.SubElement(region, "Coords", points="0,0 0,100 100,100 100,0")
    ET.SubElement(group, "RegionRefIndexed", index="0", regionRef="tr_1")

    textline_index = 0

    with open(block_correct_file, "a", encoding="utf-8") as block_file:
        for filename in sorted(os.listdir(text_dir)):
            if not filename.endswith(".xml"):
                continue
            filepath = os.path.join(text_dir, filename)
            tree = ET.parse(filepath)
            root_in = tree.getroot()

            block_text_form = root_in.find(".//BlockTextForm")
            num_lines = 0
            if block_text_form is None or not block_text_form.text:
                print(f"No BlockTextForm found in {filepath}")
                continue
            if block_text_form is not None and block_text_form.text:
                decoded_html = block_text_form.text
                soup = BeautifulSoup(decoded_html, "html.parser")
                input_fields = soup.find_all("input")
                num_lines = sum(1 for inp in input_fields if inp.get('name') == 'otv')

            # Check for <BlockCompletelyCorrect> and write to file if true
            block_correct = root_in.find(".//BlockCompletelyCorrect")
            if block_correct is not None and block_correct.text == "true":
                block_file.write(f"{subdir};{filename};Y;{num_lines}\n")
            elif block_correct is not None and block_correct.text != "true" and num_lines > 3: # Don't count page numbers etc
                block_file.write(f"{subdir};{filename};N;{num_lines}\n")
            elif block_correct is not None and block_correct.text != "true" and num_lines <= 3:
                block_file.write(f"{subdir};{filename};N/A;{num_lines}\n")
           
            decoded_html = block_text_form.text
            soup = BeautifulSoup(decoded_html, "html.parser")
            input_fields = soup.find_all("input")

            ntv_inputs = {inp.get('id'): inp for inp in input_fields if inp.get('id')}

            blockid_input = soup.find("input", {"name": "blockid"})
            blockid_value = blockid_input.get('value') if blockid_input else None

            for inp in input_fields:
                if inp.get('name') == 'otv':
                    line_text = inp.get('value', '')


                    lid_input = inp.find_previous("input", {"name": "lid"})
                    if not lid_input:
                        print(f"No lid found for otv: {line_text}")
                        continue

                    lid_value = lid_input.get('value')
                    if not lid_value:
                        print(f"No lid value for otv: {line_text}")
                        continue

                    ntv_input = ntv_inputs.get(lid_value)
                    if not ntv_input:
                        print(f"No ntv input found for lid: {lid_value}")
                        continue

                    # --- SAFE extraction ---
                    x = safe_int(ntv_input.get('data-line-x'))
                    y = safe_int(ntv_input.get('data-line-y'))
                    w = safe_int(ntv_input.get('data-line-w'), 100)
                    h = safe_int(ntv_input.get('data-line-h'), 100)

                    # Scale correctly
                    x = int(x * scale_x)
                    y = int(y * scale_y)
                    w = int(w * scale_x)
                    h = int(h * scale_y)

                    offset = int(1.7 * h)

                    # Build TextLine
                    line_id = f"tr_1_tl_{textline_index + 1}"
                    textline = ET.SubElement(region, "TextLine", id=line_id, custom=f"readingOrder {{index:{textline_index};}}")
                    ET.SubElement(textline, "Coords", points=f"{x},{y} {x+w},{y} {x+w},{y+offset} {x},{y+offset}")
                    baseline_y = y  + offset 
                    ET.SubElement(textline, "Baseline", points=f"{x},{baseline_y} {x+w},{baseline_y}")
                    textequiv = ET.SubElement(textline, "TextEquiv")
                    unicode_el = ET.SubElement(textequiv, "Unicode")
                    unicode_el.text = html.unescape(line_text)
                    if blockid_value: #Added blockid for categorization purposes
                        ET.SubElement(textline, "blockid").text = blockid_value
                    textline_index += 1
                    

    tree = ET.ElementTree(root)
    output_path = os.path.join(transkribus_dir, "page.xml")
    tree.write(output_path, encoding="utf-8", xml_declaration=True)
    print(f"Saved: {output_path}")

def batch_convert():
    base_dir = "src/datasets/bronze/scanned"
    for subdir in os.listdir(base_dir):
        full_path = os.path.join(base_dir, subdir)
        if os.path.isdir(full_path):
            convert_veridian_to_pagexml(full_path, subdir)

if __name__ == "__main__":
    batch_convert()
