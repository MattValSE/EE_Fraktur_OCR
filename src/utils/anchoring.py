import sys
sys.path.append("src")
from utils.anchor_olmocr import get_anchor_text
import os
import xml.etree.ElementTree as ET
from collections import defaultdict
from PIL import Image,ImageOps
import json
import duckdb
import pandas as pd
write_conn = duckdb.connect("duckdb/main.duckdb") 


for paper_name in os.listdir("src/datasets/bronze/scanned"):
        paper_path = os.path.join("src/datasets/bronze/scanned", paper_name)
        pdf_path = os.path.join(paper_path, "image",f"{paper_name}.pdf" )

        if os.path.isfile(pdf_path):
            # pdfreport gave the most detailed response
            anchor_text = get_anchor_text(pdf_path, 1, pdf_engine="pdfreport")

            # Preset values from conversion of PDF to JPG
            jpg_width = 2479
            jpg_height = 3508

            row_nbr = 0

            lines = []

            for row in anchor_text.splitlines():
                if row_nbr < 2:
                
                    if row_nbr == 0:
                        page_size_list = row.split(" ")

                        x_split = page_size_list[-1].split("x")

                        pdf_width = float(x_split[0])
                        pdf_height  = float(x_split[1])

                        row_nbr += 1
                    else:
                        row_nbr += 1
                elif row.startswith('['):
                    ct_split = row.split(']')
                    coord = ct_split[0]  # Get text before the first ']'
                    text = ct_split[1]
                    text = text.strip()
                    coord = coord.strip('[')   # Remove the '[' from the start
                    coord = coord.split('x') # Output: 12.34, 56.78 etc.

                    #x_img = (x_pdf / pdf_width) * img_width
                    #_img = img_height - ((y_pdf / pdf_height) * img_height)
                    x_img = int(float(coord[0]) / pdf_width *   jpg_width)
                    y_img = int(jpg_height - (float(coord[1]) / pdf_height * jpg_height) )
                    line = f"{text} [{x_img},{y_img}] \n "
                    lines.append(line)
            block = ''.join(lines)
            #print(block)
            #break
            df = pd.DataFrame([{
            "Newspaper": paper_name,
            "Block": "All",
            "Source": 'anchoring.py',
            "Text": block,
            'Type': 'N/A'
            }])
            write_conn.register("df", df)
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

                


write_conn.execute("""
        COPY Full_Text TO 'duckdb/full_text.parquet' (FORMAT PARQUET);
        """)
write_conn.commit()
write_conn.close()
