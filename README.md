# Zotero-to-DSpace
A tool to migrate Zotero metadata to DSpace. It converts Zotero-CSV to DSpace-CSV format. 


Using:
- langid 1.1.6
- numpy 1.16.2
- python-stdnum 1.11
- PyYAML 5.1

## Getting Started

These instructions will install requirements and allow you to execute the code.

### Prerequisites
(Optional) Create a virtual environment to install

### Configuring your project

- Install requirements
```
pip install -r requirements.txt
```
- Place a Zotero CSV file in the same directory as convert.py
- Convert to DSpace CSV format using the command:
```
./convert -i <filename.csv> -o <filename2.csv>
```
###### Note 1: If not input file is declare with -i, input.csv is assumed.
###### Note 2: If not output file is declare with -o, output.csv is assumed.

