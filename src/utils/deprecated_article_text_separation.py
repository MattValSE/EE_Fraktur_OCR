import os
import json
import xml.etree.ElementTree as ET
from collections import defaultdict
#import nltk
#nltk.download('punkt_tab')
#from estnltk import Text

# Stopwords, originally for MostTop preprocessing
#stopwords = set()
#with open("src/data/categories/stopwords_ee.txt", "r") as f:
#    stopwords = set(f.read().splitlines())


# PAGE XML namespace
NS = {'ns': 'http://schema.primaresearch.org/PAGE/gts/pagecontent/2013-07-15'}

def extract_articles_from_pagexml(pagexml_path, paper_name):
    tree = ET.parse(pagexml_path)
    root = tree.getroot()

    articles = defaultdict(list)

    # Go through all TextLine elements
    for line in root.findall(".//ns:TextLine", NS):
        blockid_el = line.find("ns:blockid", NS)
        unicode_el = line.find(".//ns:Unicode", NS)

        if blockid_el is not None and unicode_el is not None and unicode_el.text:
            block_id = blockid_el.text.strip()
            text = unicode_el.text.strip()
            articles[block_id].append(text)

    output = []
    for block_id, lines in articles.items():
        full_text = " ".join(lines)
        modified_text = full_text.replace("w", "v").replace("W", "V") # Modernise V usage
        modified_text = modified_text.replace("- ","") # Fix line breaks
        #text = Text(modified_text)  # Create an EstNLTK Text object for further processing
        #text.tag_layer(['morph_analysis'])  # Tagging layers for morphological analysis and POS tagging
        #print(text.morph_analysis.lemma)
        """
        lemmas = []
        for i in text.morph_analysis:
            if i.partofspeech[0] == 'Z':
                continue
            if i.lemma[0] is None:
                lemmas.append(i.text)
            if i.lemma[0] is not None:
                lemmas.append(i.lemma[0])
            
        #print(lemmas)
        filtered = [lemma for lemma in lemmas if lemma not in stopwords]
        """
        output.append({
            "article_id": f"{paper_name}_{block_id}",
            #"text": full_text, # Original text
            "modernized_text" : modified_text
            #"lemmas": filtered # EstNLTK lemmas, filtered by stopwords
        })

    return output


def process_all_papers(bronze_root="src/datasets/bronze/scanned", silver_root="src/datasets/silver/scanned"):
    all_articles = []
    for paper_name in os.listdir(bronze_root):
        paper_path = os.path.join(bronze_root, paper_name)
        pagexml_path = os.path.join(paper_path, "transkribus", "page.xml")

        if not os.path.isfile(pagexml_path):
            continue  # Skip if no page.xml

        print(f"Processing: {paper_name}")
        article_data = extract_articles_from_pagexml(pagexml_path, paper_name)

        # Output to silver layer
        output_dir = os.path.join(silver_root, paper_name, "text")
        os.makedirs(output_dir, exist_ok=True)
        output_file = os.path.join(output_dir, "article_text.json")

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(article_data, f, ensure_ascii=False, indent=2)

        print(f"→ Wrote {len(article_data)} articles to {output_file}")

        # Collect articles with more than 10 words for full_scope_data
        for article in article_data:
            word_count = len(article["modernized_text"].split())
            if word_count > 10:
                all_articles.append(article)

    # Write all qualifying articles to full_scope_data
    full_scope_dir = os.path.join(silver_root, "full_scope_data")
    os.makedirs(full_scope_dir, exist_ok=True)
    full_scope_file = os.path.join(full_scope_dir, "all_articles.json")
    with open(full_scope_file, "w", encoding="utf-8") as f:
        json.dump(all_articles, f, ensure_ascii=False, indent=2)
    print(f"→ Wrote {len(all_articles)} articles to {full_scope_file}")

# Run
process_all_papers()
