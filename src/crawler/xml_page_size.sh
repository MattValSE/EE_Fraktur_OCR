#!/bin/bash
input_file="src/crawler/input.txt"
output_dir="src/datasets/bronze/metadata"
output_file="${output_dir}/page_sizes.txt"
> "$output_file"

if [[ ! -f "$input_file" || ! -s "$input_file" ]]; then
    echo "Error: Input file '$input_file' is missing or empty."
    exit 1
fi

while IFS=' ' read -r base_pageoid num_pages img_width img_height xml_complete_ind; do
    echo "Base pageoid: $base_pageoid"
    echo "Number of pages: $num_pages"

    pageoid="$base_pageoid"
    page_sizes=$(curl -s -L "" \
        | grep "var pageImageSizes = { ")

    if [[ $page_sizes =~ \{([^}]*)\} ]]; then
        sizes="${BASH_REMATCH[1]}"
        while IFS= read -r line; do
            line=$(echo "$line" | sed 's/^,\s*//')
            if [[ $line =~ \'([0-9]+\.[0-9]+)\'\:\{[[:space:]]*w:([0-9]+),[[:space:]]*h:([0-9]+) ]]; then
                page_id="${BASH_REMATCH[1]}"
                width="${BASH_REMATCH[2]}"
                height="${BASH_REMATCH[3]}"
                cut_baseid="${base_pageoid%.*}"
                current_pageoid="${cut_baseid}.${page_id}"
                echo "${current_pageoid} ${width} ${height}" >> "$output_file"
                echo "Added page: ${current_pageoid}"
            fi
        done <<< "$(echo "$sizes" | tr '}' '\n')"
    fi
done < "$input_file"
