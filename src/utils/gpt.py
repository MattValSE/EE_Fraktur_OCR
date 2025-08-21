from openai import AzureOpenAI
import argparse
import duckdb
import pandas as pd
import os
from google import genai
from dotenv import load_dotenv
import os
import json
import traceback
import time
import base64

conn = duckdb.connect("duckdb/main.duckdb")
write_conn = duckdb.connect("duckdb/main.duckdb")  # For UPDATEs and COPY


conn = duckdb.connect("duckdb/main.duckdb")
write_conn = duckdb.connect("duckdb/main.duckdb")  # For UPDATEs and COPY
parser = argparse.ArgumentParser(description="Run Gemini OCR processing")
parser.add_argument("--model", type=str, default="gpt-4o", help="Gemini model name (e.g., gemini-2.5-pro)")
parser.add_argument("--prompt", type=str, default="block_prompt", help="Prompt template name from DB")
parser.add_argument("--min", type=str, default="0", help="What is the minimum length of the text")
parser.add_argument("--l", type=int, default=-1, help="How many loops, for when you have some quota remaining")
args = parser.parse_args()




# Load environment variables
load_dotenv()

# Retrieve API key
GEMINI_API_KEY = os.getenv("GEM")
if not GEMINI_API_KEY:
    raise ValueError("Environment variable 'GEM' is not set or invalid.")

# Initialize the client
tbu_model = args.model
prompt_tmp = args.prompt
text_length = args.min
set_loops = args.l

# Initialize Azure GPT
client_gpt = None
if 'gpt-4o'== tbu_model:
    GPT_API_KEY = os.getenv("GPT")
    if not GPT_API_KEY:
        raise ValueError("Environment variable 'GPT' is not set or invalid.")

    endpoint = ""
    deployment = ""
    api_version = ""

    client_gpt = AzureOpenAI(
        api_version=api_version,
        azure_endpoint=endpoint,
        api_key=GPT_API_KEY,
    )

prompt_template = conn.execute(
    f"""
SELECT Prompt.Text
FROM Prompt
WHERE Text IS NOT NULL
AND Version = 1 -- Change if there are multiple version, should most likely be changed to take in max value
AND Prompt.Type = '{prompt_tmp}'
    """
)

cursor = conn.execute(
    f"""
/* Check for newspapers that do not have text from current model */
SELECT PV.Newspaper, PV.Block , PV.Text
FROM Full_Text PV
LEFT JOIN Full_Text NV
ON NV.Newspaper = PV.Newspaper
AND NV.Block = PV.Block
AND NV.Source = '{tbu_model}'
AND NV.Type = 'block_prompt'
LEFT JOIN Full_Text NVGem
ON NVGem.Newspaper = PV.Newspaper
AND NVGem.Block = PV.Block
AND NVGem.Source = 'gemini-2.5-pro'
AND NVGem.Type = 'block_prompt'

WHERE NV.Text IS NULL
AND NVGem.Text IS NULL
AND PV.Source = 'split_blocks.py'
AND PV.Type = 'N/A'
AND len(PV.Text) > 100 
AND NOT EXISTS(
SELECT 1 FROM BLOCK_QUALITY BQ
WHERE BQ.NEwspaper = PV.newspaper
AND left(BQ.block,7) = PV.block
AND Bq.Correct_Ind = 'Y' 
)
    """
)



row = cursor.fetchone()
results = []
max_rpd = 0
request_nbr = 0
# Based on free tier usage rates
if tbu_model == 'gemini-2.5-pro':
    max_rpd = 3000	
elif tbu_model == 'gemini-2.5-flash':
    max_rpd = 250
else:
    max_rpd = 1000

# Set in params if  you need to reduce the default
if set_loops != -1:
    max_rpd = int(set_loops)

while row and request_nbr <= max_rpd :
    
    try: 
        newspaper_id, block_id, existing_text = row
        request_nbr += 1 
    
        # Verify image path
        image_path = f"/mnt/3de36453-6164-4568-91b5-ae973509273e/Git/EE-Gothic-Script-OCR/src/datasets/silver/scanned/{newspaper_id}/image/{block_id}.jpg"
        if not os.path.exists(image_path):
            print(f"Image not found, skipping: {image_path}")
            row = cursor.fetchone()
            continue

        
        layout_text = existing_text
        # Upload file
        if layout_text and os.path.exists(image_path):

            # Load and encode image
            with open(image_path, "rb") as image_file:
                base64_image = base64.b64encode(image_file.read()).decode("utf-8")
                image_data_url = f"data:image/jpeg;base64,{base64_image}"

            response = client_gpt.chat.completions.create(
            model=deployment,
            # Prompt
            messages = [
                        {
            "role": "system",
            "content": "You are a helpful assistant."
        },
        {
            "role": "user",
            "content": [
                {
                    "type": "image_url",
                    "image_url": {
                        "url": image_data_url
                    }
                },
                { "type": "text",
                    "text": f"""Below is the image of a block from a PDF image, as well as some raw textual content that
                                was previously extracted for it that includes position information for each row(The origin [0 x0] of the coordinates is in the upper left corner of the
                                image).
                                Just return the plain text representation of this document as if you were reading it
                                naturally.
                                This is likely one article out of several in the document, so be sure to preserve any sentences
                                that come from the previous page, or continue onto the next page, exactly as they are.
                                If there is no text at all that you think you should read, you can output null.
                                Do not hallucinate.
                                RAW_TEXT_START
                                {layout_text}
                                RAW_TEXT_END
                            """
                                  }
            ]
        }
    ],

            # Generate content
            max_tokens=4096,
            temperature=1.0,
            top_p=1.0,
            )
            response_text = response.choices[0].message.content.strip() if response and response.choices else None

            # Collect result
            df = pd.DataFrame([{
                "Newspaper": newspaper_id,
                "Source": tbu_model,
                "Text": response_text,
                "Block": block_id
                }])
            write_conn.register("df", df)

            write_conn.execute(f"""
            INSERT INTO Full_Text (Text, Source, Type, Newspaper, Timestamp, Block)
            SELECT df.Text, df.Source, '{prompt_tmp}', df.Newspaper, CURRENT_TIMESTAMP, df.Block
            FROM df
            """)
            if request_nbr % 50 == 0:
                print(request_nbr)

    except Exception as e:
        print(f"[ERROR] While processing {row[0]}: {e}")
        traceback.print_exc()

    


    row = cursor.fetchone()  


# Convert results to DataFrame
write_conn.execute("""
        COPY Full_Text TO 'duckdb/full_text.parquet' (FORMAT PARQUET);
        """)
