from PyPDF2 import PdfReader, PdfWriter
import os

# Define paths
pdf_folder = "src/datasets/bronze/downloaded_pdf"
input_list = "src/datasets/bronze/downloaded_pdf/input_list.txt"

# Ensure input_list.txt exists
if not os.path.exists(input_list):
    open(input_list, "w").close()

# Read existing entries from input_list.txt
processed_files = {}
with open(input_list, "r") as file:
    for line in file:
        parts = line.strip().split(" ")
        if len(parts) == 2:
            processed_files[parts[0]] = parts[1]

# Scan the folder for PDFs
for filename in os.listdir(pdf_folder):
    if filename.endswith(".pdf"):
        # Check if the file has already been processed
        if processed_files.get(filename) == "Y":
            print(f"Skipping already processed file: {filename}")
            continue

        # Process the PDF
        input_pdf = os.path.join(pdf_folder, filename)
        reader = PdfReader(input_pdf)
        for i, page in enumerate(reader.pages):
            arv = 1 + i
            writer = PdfWriter()
            writer.add_page(page)
            output_dir = f"src/datasets/bronze/scanned/{filename[:-4]}.1.{arv}/image/{filename[:-4]}.1.{arv}.pdf"
            os.makedirs(os.path.dirname(output_dir), exist_ok=True)  # Ensure the directory exists
            with open(output_dir, "wb") as output_file:
                writer.write(output_file)
            print(f"Saved {output_dir}")

        # Mark the file as processed in input_list.txt
        processed_files[filename] = "Y"
        with open(input_list, "w") as file:
            for key, value in processed_files.items():
                file.write(f"{key} {value}\n")