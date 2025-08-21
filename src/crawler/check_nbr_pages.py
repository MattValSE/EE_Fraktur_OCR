import PyPDF2
import os

file_content = {}

dir = 'src/datasets/bronze/downloaded_pdf'
for file in os.listdir(dir):
    if file.endswith('.pdf'):
        with open(f"{dir}/{file}", 'rb') as pdf_file:
            reader = PyPDF2.PdfReader(pdf_file)
            num_pages = len(reader.pages)
            file_content[file] = num_pages
            #print(f"Filename: {file} , Number of pages: {num_pages}")

trg_lines = []

with open("src/data/input_copy.txt", "r") as trg_file:
    line_content = trg_file.readlines()
    #print(line_content)
    for line in line_content:
        #print(line)
        line = line.strip().split()
        name = line[0]
        #print(line)
        width = line[2]
        height = line[3]
        ind = line[4]
        
        parsed_name = name
        #print(f"Parsed name: {parsed_name}")
        for pn, num_pages in file_content.items():
            #print(pn,f"{pn[:-4]}.1", parsed_name, name)
            #break
            if f"{pn[:-4]}.1" == parsed_name:

                #print(f"Filename: {pn} , Number of pages: {num_pages}")
                trg_name = f"{parsed_name[:-4]}.pdf"
                trg_lines.append(f"{parsed_name} {num_pages} {width} {height} {ind}\n")
        #    trg_file.write(f"{pn} {num_pages}\n")

#print(trg_lines)
with open("src/data/input.txt", "w") as trg_file:
    trg_file.writelines(trg_lines)