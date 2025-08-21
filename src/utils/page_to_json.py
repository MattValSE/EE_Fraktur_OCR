import xml.etree.ElementTree as ET
import json
import os

def pagexml_to_json(directory, output_dir):
    ns = {'pg': 'http://schema.primaresearch.org/PAGE/gts/pagecontent/2013-07-15'}
    xml_path = os.path.join(directory, "transkribus/", "page.xml")
    json_folder = os.path.join(output_dir, "json")
    json_path = os.path.join(output_dir, "json/", "fulltext.json")
    os.makedirs(json_folder, exist_ok=True)

    if not os.path.exists(xml_path):
        print(f"Warning: File not found: {xml_path}. Skipping.")
        return None, None

    tree = ET.parse(xml_path)
    root = tree.getroot()

    page = root.find('pg:Page', ns)
    image_filename = page.attrib.get('imageFilename')
    width = int(page.attrib.get('imageWidth', 0))
    height = int(page.attrib.get('imageHeight', 0))

    result = {
        "image": image_filename,
        "width": width,
        "height": height,
        "lines": []
    }

    # Only take lines from the first (or only) region
    region = page.find('pg:TextRegion', ns)
    if region is not None:
        for line in region.findall('pg:TextLine', ns):
            line_id = line.attrib.get('id')
            line_coords = line.find('pg:Coords', ns).attrib.get('points')
            baseline = line.find('pg:Baseline', ns)
            baseline_points = baseline.attrib.get('points') if baseline is not None else None

            text_equiv = line.find('pg:TextEquiv', ns)
            text_unicode = text_equiv.find('pg:Unicode', ns).text if text_equiv is not None else ""

            blockid_el = line.find('pg:blockid', ns)
            blockid = blockid_el.text if blockid_el is not None else None


            line_obj = {
                #"id": line_id,
                "coords": line_coords,
                "baseline": baseline_points,
                "text": text_unicode
            }

            #if blockid:
            #    line_obj["blockid"] = blockid

            result["lines"].append(line_obj)

    return result, json_path


#data = pagexml_to_json("/mnt/3de36453-6164-4568-91b5-ae973509273e/Git/EE-Gothic-Script-OCR/src/datasets/bronze/scanned/sakalaew19361118.1.8/transkribus/page.xml")

def batch_convert():
    base_dir = "src/datasets/bronze/scanned"
    silver = "src/datasets/silver/scanned"
    for subdir in os.listdir(base_dir):
        full_path = os.path.join(base_dir, subdir)
        output_dir = os.path.join(silver, subdir)
        if os.path.isdir(full_path):
            result,json_path = pagexml_to_json(full_path,output_dir)
            if result is not None and json_path is not None:
                with open(json_path, "w", encoding="utf-8") as f:
                    json.dump(result, f, ensure_ascii=False, indent=2)

# Print or save
#print(json.dumps(data, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    batch_convert()

