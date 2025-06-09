# This reads your file with detected encoding and saves as UTF-8

import chardet

filename = 'notion_writer.py'

# Detect encoding
with open(filename, 'rb') as f:
    rawdata = f.read()
    result = chardet.detect(rawdata)
    encoding = result['encoding']
    print(f"Detected encoding: {encoding}")

# Read with detected encoding and save as UTF-8
with open(filename, 'r', encoding=encoding) as f:
    content = f.read()

with open(filename, 'w', encoding='utf-8') as f:
    f.write(content)

print(f"File '{filename}' converted to UTF-8.")
