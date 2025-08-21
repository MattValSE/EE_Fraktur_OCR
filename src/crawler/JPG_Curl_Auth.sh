# Input file containing the base pageoid and the number of pages
input_file="./input.txt"

if [[ ! -f "$input_file" || ! -s "$input_file" ]]; then
    echo "Error: Input file '$input_file' is missing or empty."
    exit 1
fi

# Read the base pageoid and the number of pages from the input file
while IFS=' ' read -r base_pageoid num_pages img_width img_height; do
    echo "Base pageoid: $base_pageoid"
    echo "Number of pages: $num_pages"
    echo "Width: $img_width"
    echo "Height: $img_height"
    # Loop through the range of pages
    for ((page=1; page<=num_pages; page++)); do
        pageoid="${base_pageoid}.${page}"
        echo "Processing page: $pageoid"

        # Create a folder for the tiles for this page
        mkdir -p "../datasets/bronze/scanned/${pageoid}/tiles"

        # Initialize counters
        max_amt=0
        error_count=0
        tile_size=256

        if  [ -z "$img_width" ] || [ -z "$img_height" ]; then
            echo "Error: Missing width, height, or tile_size variables."
            exit 1
        fi


        # Loop until we either reach 50 attempts or errors are too many (>=2)
        while [[ $max_amt -lt 50 || $error_count -lt 2 ]]; do
            ((max_amt++))
            echo "Attempt #$max_amt to download all tiles for page $pageoid."
            error_count=0  # Reset error count for this attempt
            echo "height: $img_height tile_size: $tile_size"
            
            # Loop over Y and X coordinates
            for (( y=0; y<img_height; y+=tile_size )); do
                echo "Processing Y coordinate: $y"
                
                for (( x=0; x<img_width; x+=tile_size )); do
                    echo "Processing X coordinate: $y"
                    
                    x2=$(( tile_size ))
                    y2=$(( tile_size ))
                    # Create a zero-padded filename so that montage sorts them correctly.
                    tile_file=$(printf "../datasets/bronze/scanned/${pageoid}/tiles/tile_%04d_%04d.jpeg" "$y" "$x")
                    echo "Downloading tile: $tile_file with crop ${x},${y},${x2},${y2}"

                    
                    echo "Missing curl script to not publish a crawler"
                    
                    # Generate a random sleep duration between 0.5 and 1 second
                    sleep_duration=$(awk -v min=0.5 -v max=1 "BEGIN {srand(); print min + (rand() * (max - min))}")
                    sleep "$sleep_duration"
                    #exit
                    # Check if the downloaded file starts with an error response
                    if grep -q "<?xml.*<VeridianXMLResponse>[ ]*<Error>" "$tile_file"; then
                        echo "Error detected in $tile_file. Removing file and counting error."
                        rm "$tile_file"
                        ((error_count++))
                        if [[ $error_count -ge 2 ]]; then
                            echo "Too many errors for page $pageoid. Skipping to the next page."
                            break 2
                        fi
                    fi
                done
            done
        done
    done
done < "$input_file"
