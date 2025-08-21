Code for sourcing Estonian Newspapers from before 1944, extracting pdfs and texts and making the data available for model training and LLM usage.

## Utils

Data is to conform with a medallion architecture folder structure of datasets: bronze, silver, gold.
Duckdb database is presumed to be in the main folder.

anchor_olmocr - script based on the OLMOCR framework. Used to get the data embedded in the PDF-s. Outputs texts with [0,0] coordinates

anchoring - Creates coordinated text for each paper based on the utils of anchor_olmocr

block_image_mover - moves the silver layer block data to gold

convert_to_page - Creates a single page.xml file, a page xml representation for Tranksribus,  in silver layer from the gathered blocks

db_script_block - Prompts an LLM based on the OLMOCR framework scripts. Gives it an image and the text and asks for a  markdown response. No coordinates are returned.

gpt - Same as the previous block, but focused on AzureOpenAI

pdf_splitter - As the input data can consist of a single periodical edition then these are split into multiple pages. 

split_blocks - Creates a block representation of the current data and resizes the coordinates. Does this for JSON and XML for both Tranksribus and QWEN training. Data is stored in the final database as well.

validation - Prepares data for validation and stores in db.

## Tranksribus

Scripts for updating Tranksribus documents with data from parsed XML files.
Document_Ids are currently hardcoded due to how the platform works. 

## Crawler
Crawler scripts for sourcing the data. These are just for reference and have been limited by contents to not encourage bad faith crawling.
