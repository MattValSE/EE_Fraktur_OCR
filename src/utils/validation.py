import os
from jiwer import wer, cer
import re
from collections import Counter
import json
import duckdb
import pandas as pd

conn = duckdb.connect("duckdb/main.duckdb")
write_conn = duckdb.connect("duckdb/main.duckdb")  # For UPDATEs and COPY

# Regex pattern to remove [number,number] blocks (like [12,293])
coord_pattern = re.compile(r'\[\d+,\d+\]')
conn.execute("""
   DROP TABLE val_text          
""")



conn.execute(
"""
CREATE TABLE IF NOT EXISTS val_text (
    Newspaper TEXT,
    idx INTEGER,
    Reference TEXT,
    Response TEXT,
    CER DOUBLE,
    WER DOUBLE,
    Per_Word_Error INTEGER,  
    Timestamp TIMESTAMP
);
"""

)
import re

coord_pattern = re.compile(r'<coord>.*?</coord>')

def clean(response):
    # Remove coordinate tags and strip whitespace
    cleaned_text = coord_pattern.sub('', response).strip()
    
    # Remove leading numbers like 1., 2., etc. at the beginning of lines
    cleaned_text = re.sub(r'^\d+\.\s*', '', cleaned_text, flags=re.MULTILINE)
    
    # Split based on "assistant\n" and select the correct part
    splitting = cleaned_text.split("assistant\n")
    if len(splitting) > 1:
        resp = splitting[1]
    else:
        resp = splitting[0]
    
    return resp


def dict_diff(dict1, dict2):
    diff = {}
    # Keys only in dict1
    for k in dict1:
        if k not in dict2:
            diff[k] = ('only_in_orig', dict1[k])
        elif dict1[k] != dict2[k]:
            diff[k] = ('different_values', dict1[k], dict2[k])
    # Keys only in dict2
    for k in dict2:
        if k not in dict1:
            diff[k] = ('only_in_new', dict2[k])
    return diff

def count_words(text):
    text = re.sub(r'[^\w\s]', '', text)
    return Counter(text.split())

for file in os.listdir("src/datasets/gold/inference"):
    file_dir = os.path.join("src/datasets/gold/inference", file)
    if not os.path.isfile(file_dir):
        continue
        
    with open(file_dir, "r", encoding="utf-8") as f:
        layout_json = json.load(f)
    
    for idx, element in enumerate(layout_json):
        # Clean the assistant/response string
        cleaned_response = clean(element["response"])
        cleaned_reference = clean(element["reference"])

        word_count_orig = count_words(cleaned_reference)
        word_count_new = count_words(cleaned_response)
        errorw = wer(cleaned_reference, cleaned_response)
        errorc = cer(cleaned_reference, cleaned_response)
        dict_comp = dict_diff(word_count_new,word_count_orig)
        per_word_error = round(len(dict_diff(word_count_orig, word_count_new)) / len(word_count_orig) * 100, 1)


        df = pd.DataFrame ([{
            "newspaper": file,
            "id" : idx,
            "reference": cleaned_reference,
            "response": cleaned_response,
            "errorw": errorw,
            "errorc": errorc,
            "per_word_error": per_word_error
        }])

        write_conn.register("df", df)
        
        write_conn.execute("""
        INSERT INTO val_text (Newspaper ,
                    idx,
                    reference ,
                    response ,
                    CER ,
                    WER ,
                    Per_Word_Error ,  
                    Timestamp  )
        SELECT newspaper, id, reference, response, errorc, errorw,per_word_error, CURRENT_TIMESTAMP
                           from df
        WHERE NOT EXISTS (
            SELECT 1 FROM val_text vt
            WHERE vt.Newspaper = df.newspaper
                  AND vt.idx = df.id

        )
        """)
    

write_conn.execute("""
        COPY val_text TO 'duckdb/val_text.parquet' (FORMAT PARQUET);
        """)


write_conn.close()
conn.close()