import os
import json
import xml.etree.ElementTree as ET
import html 

NS = {'ns': 'http://schema.primaresearch.org/PAGE/gts/pagecontent/2013-07-15'}

def extract_continuous_text_from_pagexml(pagexml_path):
    tree = ET.parse(pagexml_path)
    root = tree.getroot()

    lines = []
    for line in root.findall(".//ns:TextLine", NS):
        unicode_el = line.find(".//ns:Unicode", NS)
        if unicode_el is not None and unicode_el.text:
            text = html.unescape(unicode_el.text.strip()) 
            lines.append(text)

    # Join lines, but handle hyphenation more carefully
    joined_lines = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.endswith('-') and i + 1 < len(lines):
            # Remove hyphen and join with next line without space
            joined_lines.append(line[:-1] + lines[i + 1].lstrip())
            i += 2  # skip next line
        else:
            joined_lines.append(line)
            i += 1

    full_text = "\n".join(joined_lines)
    modernized_text = full_text.replace("w", "v").replace("W", "V")
    modernized_text = modernized_text.replace("- ", "")
    return modernized_text

def process_all_papers_continuous(bronze_root="src/datasets/bronze/scanned", silver_root="src/datasets/silver/scanned"):
    for paper_name in os.listdir(bronze_root):
        paper_path = os.path.join(bronze_root, paper_name)
        pagexml_path = os.path.join(paper_path, "transkribus", "page.xml")

        if not os.path.isfile(pagexml_path):
            continue

        print(f"Processing: {paper_name}")
        continuous_text = extract_continuous_text_from_pagexml(pagexml_path)

        output_dir = os.path.join(silver_root, paper_name, "text")
        os.makedirs(output_dir, exist_ok=True)
        output_file = os.path.join(output_dir, "continuous_text.txt")

        with open(output_file, "w", encoding="utf-8") as f:
            f.write(continuous_text)

        print(f"Wrote continuous text to {output_file}")

# Run
process_all_papers_continuous()