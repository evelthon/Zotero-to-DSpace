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

## Configuration
- Set the equivalent of Zotero language in ISO format in ```languages_zotero.csv```. This is used to generate dc.language.iso
- Set the header of the generate DSpace CSV file using values in ```dspace_csv_header.yml```.
The file comprises of 3 sections:
    1. ```initial_fieldnames``` are header values that always exists. Note that ```dc.type.uhtype``` is a custom field used at gnosis.ucy.ac.cy, to store item type. In your case you could copy values in ```dc.type``` and delete this column.
    2. ```fieldnames_with_language``` are fields that have a language value, for example ```dc.title[el]``` or ```dc.title[en]```.
    3. ```fieldnames_with_no_language``` are fields (headers) without language destinction, for example ```dc.source.uri[]```.
- Set metadata mapping in ```metadata_mapping.yml```. In it are 2 main groups of settings:
    1. ```metadata_with_language```. These are fields that should have their language detected. For example if a title in in english, it should be set in ```dc.title[en]``` column. If a title in in greek, it should be set in ```dc.title[el]``` column.
    2. ```metadata_without_language```. These are fields that should not have their language detected. For example ```dc.source.uri[]``` column.    
    - On the left you have the DC field.
    - On the right you have the column number of Zotero's CSV file. CAUTION: numbering starts at zero (0)!
- Set type translation in ```types.yml```. This configuration file allows to translate a Zotero type to a "friendlier" value in case you need to index it and present it to th end-user.