import os
import requests
file = "src/crawler/input.txt"
trgt = "src/datasets/bronze/downloaded_pdf"
with open(file, "r") as f:
    lines = f.readlines()
    lines = [line.strip() for line in lines if line.strip()]  # Remove empty lines
    lines = [line for line in lines if not line.startswith("#")]  # Remove comments
    split_lines = [line.split() for line in lines]  # Split lines into words
    split_words = [word for word in split_lines]  # Flatten the list of lists
    for i in split_words:
         periodical = i[0]
         periodical_f = periodical[:len(periodical)-2]
         url = ""
         output_file = os.path.join(trgt, f"{periodical_f}.pdf")
         print(f"Downloading {url} to {output_file}...")
         response = requests.get(url, stream=True)
         if response.status_code == 200:
             with open(output_file, "wb") as pdf_file:
                 for chunk in response.iter_content(chunk_size=1024):
                     pdf_file.write(chunk)
             print(f"Downloaded: {output_file}")
         else:
            print(f"Failed to download {url}. HTTP Status Code: {response.status_code}")