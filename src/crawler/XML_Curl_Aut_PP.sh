#!/bin/bash
#set -x
# Input file containing the base pageoid and the number of pages
input_file="./src/crawler/input.txt"

if [[ ! -f "$input_file" || ! -s "$input_file" ]]; then
    echo "Error: Input file '$input_file' is missing or empty."
    exit 1
fi

# Read the base pageoid and the number of pages from the input file
while IFS=' ' read -r base_pageoid num_pages img_width img_height xml_complete_ind; do
    echo "Base pageoid: $base_pageoid"
    echo "Number of pages: $num_pages"
    echo "Width: $img_width" #Not used and incorrect
    echo "Height: $img_height" # Not used and incorrect
    echo "XML complete: $xml_complete_ind"


    # Loop through the range of pages
    if [[ $xml_complete_ind == "Y" ]]; then
        echo "Already scanned, skipping base pageoid: $base_pageoid"
        continue
    fi

    for ((i=1; i<=num_pages; i++)); do
        
        # Construct the full pageoid (e.g., maahaal19331023.1.1, maahaal19331023.1.2, ...)
        pageoid="${base_pageoid}.${i}"
        echo "Scanning: $pageoid"
        echo "Page number: $i"
        

        # Create directories for the page
        mkdir -p "./src/datasets/bronze/scanned/${pageoid}/text"

        max_amt=0
        error_count=0

        # Scan blocks for the page
        while [[ $max_amt -lt 80 && $error_count -lt 2 ]]; do
            ((max_amt++))
            if [[ $max_amt -lt 10 ]]; then
            max_padded="0$max_amt"
                else
            
            max_padded="$max_amt"
                fi

            echo "missing curl script to not spam the server"
            cmd=""          

            # Print it for debugging
            #echo "$cmd"         

            # Actually run it
            eval "$cmd"
            #exit
            # Cookie replacement: awk '{gsub(/"/, "", $2); gsub(/\+/, "%2b", $2); gsub(/=/, "%3d", $2); printf "%s=%s; ", $1, $2}' ./cookies.txt
            # Check if the file starts with the error pattern, allowing for spaces
            if [[ ! -s "./src/datasets/bronze/scanned/${pageoid}/text/TB000${max_padded}.xml" ]] || \
               grep -q "<VeridianXMLResponse>[ ]*<Error>" "./src/datasets/bronze/scanned/${pageoid}/text/TB000${max_padded}.xml"; then
                ((error_count++))
                echo "Error found in Block ${max_padded}, error count now: $error_count"
            fi
            if grep -q "Pead olema sisse logitud" "./src/datasets/bronze/scanned/${pageoid}/text/TB000${max_padded}.xml"; then
                echo "Pead olema sisse logitud"
                echo "${pageoid}"
                exit 1
            fi

            sleep 1
        done
    done
    # Mark the base_pageoid as complete in the input file
    sed -i "s/^${base_pageoid} .*/${base_pageoid} ${num_pages} ${img_width} ${img_height} Y/" "$input_file"
    echo "Marked ${base_pageoid} as complete in $input_file"

done < "$input_file"
