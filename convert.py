#!/usr/bin/env python
# -*- coding: utf-8 -*-

import csv as csv
from collections import OrderedDict
import langid
from langid.langid import LanguageIdentifier, model
import argparse
import sys
import re
from stdnum import isbn, issn
import yaml

from tqdm import tqdm
import time

output_file = 'output.csv'
input_file = 'input.csv'
handle = '7/1234'
# orcid_file = None

# configuration files
ZOTERO_LANGUAGES = './settings/languages_zotero.csv'
DSPACE_CSV_HEADER = './settings/dspace_csv_header.yml'
METADATA_MAPPING = './settings/metadata_mapping.yml'
ITEM_TYPES = './settings/types.yml'
ORCID_FILE = './settings/orcid.csv'


class SpreadSheet:

    def __init__(self, input_file, output_file, handle, add_orcids):
        self.input_file = input_file
        self.output_file = output_file
        self.handle = handle
        self.add_orcids = add_orcids

        # print(self.handle)
        # print( self.orcid_file)

        self.di = OrderedDict()
        self.csvRow = None
        self.detected_languages = []
        self.document_types = None

        self.initial_fieldnames = None
        self.fieldnames_with_language = None
        self.fieldnames_with_no_language = None

        self.orcid_list = None

        '''
        Scan csv for these language. ALso use this languages to generate DSpace csv land headers.

        '''
        self.searched_for_languages = ['el', 'en', 'fr', 'de', 'tr', 'es', 'sk', '']
        self.langid_languages = ['el', 'en', 'fr', 'de', 'tr', 'es', 'sk']
        self.oDi = OrderedDict()
        self.langid_identifier = LanguageIdentifier.from_modelstring(model, norm_probs=True)

        self.languages_iso = {}

        if self.add_orcids:
            self.load_orcid()

        """
        Load document types
        Translates Zotero types to preferred values of DSpace 
        (how we prefer each value)
        """
        with open(ITEM_TYPES, 'r') as typefile:
            cfg = yaml.load(typefile, Loader=yaml.FullLoader)
        self.document_types = cfg['types']
        # print(types)

        """
        Load csv header values.
        These are the headers in DSpace's CSV file (to be generated)
        """
        with open(DSPACE_CSV_HEADER, 'r') as dspace_csv_header_file:
            cfg_dspace = yaml.load(dspace_csv_header_file, Loader=yaml.FullLoader)
        self.initial_fieldnames = cfg_dspace['initial_fieldnames']
        self.fieldnames_with_language = cfg_dspace['fieldnames_with_language']
        self.fieldnames_with_no_language = cfg_dspace['fieldnames_with_no_language']

        """
        Load metadata mapping.
        Defines which value of Zotero goes to what DC variable.
        """
        with open(METADATA_MAPPING, 'r') as metadata_mapping_file:
            cfg_metadata_mapping = yaml.load(metadata_mapping_file, Loader=yaml.FullLoader)
        self.metadata_with_language = cfg_metadata_mapping['metadata_with_language']
        self.metadata_without_language = cfg_metadata_mapping['metadata_without_language']

        self.load_languages()

    def load_languages(self):
        try:
            readdata = csv.reader(open(ZOTERO_LANGUAGES))
        except FileNotFoundError:
            print('Zotero language file not found: ' + ZOTERO_LANGUAGES)
            sys.exit()
        self.languages_iso = {rows[0]: rows[1] for rows in readdata}

    def load_orcid(self):
        try:
            readdata = csv.reader(open(ORCID_FILE))
        except FileNotFoundError:
            print('ORCiD file not found: ' + ORCID_FILE)
            sys.exit()
        self.orcid_list = {rows[0].strip() + ', ' + rows[1].strip(): rows[2].strip() for rows in readdata}

        # print(self.orcid_list)

    def exportCSV(self):
        with open(self.output_file, 'w') as csvfile:

            fieldnames = self.generate_csv_header_for_dspace()

            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()

            # print(self.oDi)
            a_row = OrderedDict()
            for key, value in self.oDi.items():
                # print(key)
                # print(value)

                for field in fieldnames:
                    # print(field)
                    # print(self.oDi[key][field])
                    if field in self.oDi[key]:
                        a_row[field] = self.oDi[key][field]
                    else:
                        a_row[field] = ''
                # print('-------------------------------')
                # print(a_row)

                writer.writerow(a_row)
        return None

    def importCSV(self):

        di = OrderedDict()

        try:
            # print(self.input_file)
            readdata = csv.reader(open(self.input_file), delimiter=',', quotechar='"')
        except FileNotFoundError:
            print('File not found: ' + self.input_file)
            sys.exit()
        i = 0
        for row in readdata:

            # print(row)

            # Ignore the header row
            if row[1] != 'Item Type':
                di[i] = row
                i += 1

        # num or records discovered
        print("Found records: " + str(len(di)))

        '''
        Generate a dictionary with keys, the csv headers of the ending csv file
        '''

        for key, value in tqdm(di.items()):
            # time.sleep(3)
            # By-pass non-valid lines or header
            if len(value) < 10 or str(value).startswith("['Reference Typ"):
                # print('Empty key at: ' + str(key) + ' where value was: ' + str(value))
                continue

            self.oDi[key] = OrderedDict()
            self.csvRow = value
            # print(value)

            """
            Columns with special function generator
            """

            self.oDi[key]['id'] = '+'
            self.oDi[key]['collection'] = self.handle

            # dc.type
            self.csvRow[1] = self.csvRow[1].strip()
            self.csvRow[1] = self.enrich_document_type(self.csvRow[1])
            # print(self.csvRow[0])
            self.oDi[key]['dc.type.uhtype[en]'] = self.csvRow[1]

            # dc.language.iso
            self.csvRow[28] = self.csvRow[28].strip()
            self.rename_language(28)
            # print(self.csvRow[0])
            self.oDi[key]['dc.language.iso[en]'] = self.csvRow[28]

            # dc.date.issued (no language distinction)
            if 'dc.date.issued' in self.metadata_without_language:
                primary_var = int(self.metadata_without_language['dc.date.issued'].split(',')[0].strip())
                sec_var = int(self.metadata_without_language['dc.date.issued'].split(',')[1].strip())
                self.oDi[key]['dc.date.issued[]'] = self.create_date_issued(primary_var, sec_var)

            # dc.description.startingpage
            if 'dc.description.startingpage' in self.metadata_without_language:
                self.oDi[key]['dc.description.startingpage[]'] = self.create_startingpage(
                    int(self.metadata_without_language['dc.description.startingpage']))

            # dc.description.endingpage
            if 'dc.description.endingpage' in self.metadata_without_language:
                self.oDi[key]['dc.description.endingpage[]'] = self.create_endingpage(
                    int(self.metadata_without_language['dc.description.endingpage']))
            # self.oDi[key]['dc.description.endingpage[]'] = self.create_endingpage(15)

            # dc.description.totalnumpages[]
            if 'dc.description.totalnumpages' in self.metadata_without_language:
                num_col = int(self.metadata_without_language['dc.description.endingpage'])
                self.oDi[key]['dc.description.totalnumpages[]'] = self.csvRow[num_col].strip()

            # dc.identifier.lc[]
            # SPECIAL
            if 'dc.identifier.lc' in self.metadata_without_language:
                lc_col = int(self.metadata_without_language['dc.identifier.lc'])
                self.create_lc(key, [lc_col])

            # dc.source.uri
            if 'dc.source.uri' in self.metadata_without_language:
                # col_num = self.metadata_without_language['dc.source.uri']
                col_num = list(map(int, str(self.metadata_without_language['dc.source.uri']).split(',')))
                # print(col_num)
                self.oDi[key]['dc.source.uri[]'] = self.generate_repeative_fields(col_num)

            # dc.identifier.doi
            if 'dc.identifier.doi' in self.metadata_without_language:
                col_num = int(self.metadata_without_language['dc.identifier.doi'])
                self.oDi[key]['dc.identifier.doi[]'] = self.csvRow[col_num].strip()

            # dc.identifier.isbn[]
            if 'dc.identifier.isbn' in self.metadata_without_language:
                col_num = list(map(int, str(self.metadata_without_language['dc.identifier.isbn']).split(',')))
                self.oDi[key]['dc.identifier.isbn[]'] = self.create_isbn(key, col_num)

            # dc.identifier.issn[]
            if 'dc.identifier.issn' in self.metadata_without_language:
                col_num = list(map(int, str(self.metadata_without_language['dc.identifier.issn']).split(',')))
                self.oDi[key]['dc.identifier.issn[]'] = self.create_issn(key, col_num)

            # dc.contributor.orcid
            if self.add_orcids:
                tmp_orcis = str(self.metadata_with_language['dc.contributor.author']) + ',' + str(self.metadata_with_language['dc.contributor.editor'])
                # print(list(map(int, str(tmp_orcis).split(','))))
                # print(list(map(int, str(self.metadata_with_language['dc.contributor.editor']).split(','))))
                self.populate_orcids(key, list(map(int, str(tmp_orcis).split(','))))

            # dc.date.available (no language distinction)
            # self.oDi[key]['dc.date.available[]'] = self.csvRow[6].strip()

            """
            Columns with common function generator
            """

            for k in self.metadata_with_language:
                self.create_metadata_with_language(key,
                                                   list(map(int, str(self.metadata_with_language[k]).split(','))),
                                                   str(k))

            """
                dc.identifier.isbn	International Standard Book Number
                dc.identifier.ismn	International Standard Music Number
                dc.identifier.issn
            """

            """
            Regex validator for LC
            [A-Z]{1,4}[0-9]{1,4}([.][0-9]{1,3})?([.][A-Z]?)?[0-9]+([\w ]+[0-9]{4})? 
            """

    # print(str(key) + ': ' + value[23])

    def normalize_string(self, str):
        """
        Return a string with the first letter capital, rest lower case.

        :param str str: A given string:
        :return: A normalized string
        :rtype: str
        """
        return str[:1].upper() + str[1:].lower()

    def create_startingpage(self, var_list=None):
        splitted_pages = re.split(r'\s|-', self.csvRow[var_list].strip())
        # print(splitted_pages)
        if len(splitted_pages) > 1:
            # print(splitted_pages[0])
            return splitted_pages[0]
        else:
            return ''

    def create_endingpage(self, var_list=None):
        splitted_pages = re.split(r'\s|-', self.csvRow[var_list].strip())
        # print(splitted_pages)
        if len(splitted_pages) > 1:
            # print(splitted_pages[1])
            return splitted_pages[1]
        else:
            return ''

    def create_date_issued(self, primary_field, secondary_field):
        if self.csvRow[primary_field].strip():
            return self.csvRow[primary_field].strip()
        if self.csvRow[secondary_field].strip():
            return self.csvRow[secondary_field].strip()
        return ''

    def create_lc(self, key, var_list=None):
        lc_dict = OrderedDict()
        lc_dict["dc.identifier.lc[en]"] = None
        tmp_list = []
        for var in var_list:
            # tmp_list.append(self.csvRow[var].strip())
            tmp_list += self.csvRow[var].split(";")
        tmp_list = list(filter(None, tmp_list))  # remove empty list elements

        # strip all elements in the list
        tmp_list = map(str.strip, tmp_list)
        # remove duplicates
        tmp_list = list(set(tmp_list))
        pattern = re.compile("[A-Z]{1,4}[0-9]{1,4}([.][0-9]{1,3})?([.][A-Z]?)?[0-9]+([\w ]+[0-9]{4})?")
        for item in tmp_list:
            item = item.strip()
            if pattern.match(item):
                k = "dc.identifier.lc[en]"
                if not lc_dict[k]:
                    lc_dict[k] = item
                else:
                    lc_dict[k] += '||' + item

        for k, v in lc_dict.items():
            self.oDi[key][k] = v
        # return None

    def populate_orcids(self, key, var_list=None):
        orcid_dict = OrderedDict()
        orcid_dict["dc.contributor.orcid[]"] = None
        tmp_list = []
        for var in var_list:
            # tmp_list.append(self.csvRow[var].strip())
            tmp_list += self.csvRow[var].split(";")
        tmp_list = list(filter(None, tmp_list))  # remove empty list elements

        # strip all elements in the list
        tmp_list = map(str.strip, tmp_list)
        # remove duplicates
        tmp_list = list(set(tmp_list))
        for item in tmp_list:
            item = item.strip()
            # if pattern.match(item):
            if item in self.orcid_list:
                k = "dc.contributor.orcid[]"

                # print(self.orcid_list[item])
                if not orcid_dict[k]:
                    orcid_dict[k] = item + ' [' + self.orcid_list[item] + ']'

                else:
                    orcid_dict[k] += '||' + item + ' [' + self.orcid_list[item] + ']'

        for k, v in orcid_dict.items():
            self.oDi[key][k] = v

    def create_isbn(self, key, var_list=None):
        tmp_list = []
        for var in var_list:
            # print(self.csvRow[var].strip())
            tmp_elem = re.split('; |, ', self.csvRow[var].strip())
            for i in range(len(tmp_elem)):
                """
                Filter ISSN and ISBN only
                """
                tmp_var_isbn = self.remove_non_isbn_chars(tmp_elem[i].upper())
                if isbn.is_valid(tmp_var_isbn):
                    # print("Valid ISBN: " + tmp_var_isbn)
                    tmp_elem[i] = isbn.format(tmp_var_isbn)
                else:
                    tmp_elem[i] = None

            # Filter all elements, remove text chars, parenthesis etc

            # print(tmp_elem)
            tmp_list += tmp_elem
            # print(tmp_list)
        tmp_list = list(filter(None, tmp_list))  # remove empty list elements
        # print(tmp_list)
        # No semi-colon, so do a join here. Cannot use the function to split semi-colons
        return '||'.join(filter(None, tmp_list)).strip()

    def create_issn(self, key, var_list=None):
        tmp_list = []
        for var in var_list:
            # print(self.csvRow[var].strip())
            tmp_elem = re.split('; |, ', self.csvRow[var].strip())
            for i in range(len(tmp_elem)):
                """
                Filter ISSN and ISBN only
                """
                tmp_var_issn = self.remove_non_isbn_chars(tmp_elem[i].upper())
                if issn.is_valid(tmp_var_issn):
                    # print("Valid ISSN: " + tmp_var_issn)
                    tmp_elem[i] = issn.format(tmp_var_issn)
                else:
                    tmp_elem[i] = None

            # Filter all elements, remove text chars, parenthesis etc

            # print(tmp_elem)
            tmp_list += tmp_elem
            # print(tmp_list)
        tmp_list = list(filter(None, tmp_list))  # remove empty list elements
        # print(tmp_list)
        # No semi-colon, so do a join here. Cannot use the function to split semi-colons
        return '||'.join(filter(None, tmp_list)).strip()

    def remove_non_isbn_chars(self, str):
        str = re.sub(r'[^0-9X\-]', "", str)
        return str

    def remove_non_issn_chars(self, str):
        str = re.sub(r'[^0-9X\-]', "", str)
        return str


    '''
    metadata_val should have a value like dc.contributor.translator
    '''
    def create_metadata_with_language(self, key, var_list=None, metadata_val=None):
        """
           Convert Zotero value to corresponding DSpace metadata
            :param int key: An integer of currently processed item row. Corresponds to CSV file rows.
            :param list var_list: A list with column numbers to be used from Zotero csv file (multiple)
            :param str metadata_val: The DSpace metadata value to be created (e.g. dc.title)
          """
        if metadata_val is None:
            raise ValueError('Metadata field not set')

        # create a list of created_field keys by language
        # create a list of author keys by language like dc.contributor.author[el]
        meta_field = OrderedDict()
        for lang in self.searched_for_languages:
            k = metadata_val + "[" + lang + "]"
            meta_field[k] = ''
        # print(authors)

        # Convert all vars to list, and additionally separate any repeating fields with a semi-colon
        tmp_list = []
        for var in var_list:
            # print(var)
            # print(self.csvRow[var].split(";"))
            tmp_list += self.csvRow[var].split(";")
        tmp_list = list(filter(None, tmp_list))  # remove empty list elements

        # print(tmp_list)

        for item in tmp_list:
            item = item.strip()
            k = metadata_val + "[" + self.detect_language(item) + "]"
            if not meta_field[k]:
                meta_field[k] = item
            else:
                meta_field[k] += '||' + item

        for k, v in meta_field.items():
            self.oDi[key][k] = v


    def create_source_other(self, key, var_list=None):
        # create a list of title keys by language like dc.title[el]
        sources = OrderedDict()
        for lang in self.searched_for_languages:
            k = "dc.source.other[" + lang + "]"
            sources[k] = ''

        tmp_list = []
        for var in var_list:
            tmp_list.append(self.csvRow[var].strip())
        tmp_list = list(filter(None, tmp_list))  # remove empty list elements

        for item in tmp_list:
            k = "dc.source.other[" + self.detect_language(item) + "]"
            if not sources[k]:
                sources[k] = item
            else:
                sources[k] += '||' + item

        for k, v in sources.items():
            self.oDi[key][k] = v

    def detect_language(self, str):
        """
           Detect language of given string. 
           First, attempt to detect language with langid. Langid uses probabilities, so if probability score is low,
           use characters in string to detect language.
    
           :param str str: The given string
           :return: language in 2 letter ISO format.
           :rtype: str
        """

        # If passed an empty string, return empty result
        if len(str.strip()) < 1:
            return ''

        str_langid = str.strip()
        str = str.lower().strip()

        detected_langid_value = ''

        langid.set_languages(self.langid_languages)
        # langid.set_languages(['de', 'fr', 'it'])
        detected_lang = self.langid_identifier.classify(str_langid)
        # print(detected_lang)
        # if detected_lang[1] < 0.5:
        #     print(detected_lang)
        #     print(str_langid)
        '''
        If the statistical probability of a detected language is larger than
        0.9999, return that language, if it is included in langid_languages.
        If not, set it equal to 'en'.
        '''

        if detected_lang[1] > 0.9999 and detected_lang[0] in self.langid_languages:
            detected_langid_value = detected_lang[0]
            return detected_langid_value
        # else:
        #     detected_langid_value = 'en'

        # Greek characters
        chars_el = set('αβγδεζηθικλμνξοπρσςτυφχψω')
        # Latin characters
        chars_en = set('abcdefghijklmnopqrstuvwxyz')
        # French characters
        chars_fr = set('éàèùâêîôûçëïü')
        # German characters
        chars_de = set('äöüß')
        # Turkish characters
        chars_tr = set('şĞİğı')
        # Spanish characters
        chars_es = set('ñóíáã')
        # Slovak characters
        chars_sk = set('ýúčžň')
        # Czech characters
        chars_cz = set('řťšůď')

        '''
        If a greek character exists, return greek language immediately
        '''
        if any((c in chars_el) for c in str):
            return 'el'

        return_value = ''
        # if 'LATIN' in unicodedata.name(str.strip()[0]):
        if any((c in chars_en) for c in str):
            if any((c in chars_fr) for c in str):
                return_value = 'fr'
            if any((c in chars_de) for c in str):
                return_value = 'de'
            if any((c in chars_tr) for c in str):
                return_value = 'tr'
            if any((c in chars_es) for c in str):
                return_value = 'es'
            if any((c in chars_sk) for c in str):
                return_value = 'sk'
            if any((c in chars_cz) for c in str):
                return_value = 'cz'
            return_value = 'en'

        '''
        If no language is detected, return an empty string.
        This helps set DC values with no language.
        xstr = lambda s: s or ""
        '''
        return return_value

    def generate_repeative_fields(self, var_list=None):
        # fields seperated with ';' by export. They need to change to '||'
        temp_list = list()

        for var in var_list:
            self.csvRow[var] = self.replace_semicolon_with_vertical(self.csvRow[var])
            temp_list.append(self.csvRow[var].strip())

        return '||'.join(filter(None, temp_list)).strip()

    def replace_semicolon_with_vertical(self, var):
        return var.replace(';', '||')

    def enrich_document_type(self, str):
        if str in self.document_types:
            return self.document_types[str]

    def rename_language(self, lang_column):
        tmp_list = []
        tmp_list += [x.strip() for x in self.csvRow[lang_column].split(";")]
        for i, lang in enumerate(tmp_list):
            if lang in self.languages_iso.keys():
                tmp_list[i] = self.languages_iso[lang]
            if lang == 'No Linguistic Content' or lang == 'Undetermined':
                tmp_list[i] = ''
        # print(tmp_list)
        if len(tmp_list) > 1:
            self.csvRow[lang_column] = '||'.join(filter(None, tmp_list)).strip()
        elif len(tmp_list) == 1:
            self.csvRow[lang_column] = tmp_list[0].strip()
        else:
            self.csvRow[lang_column] = ""
        # print( self.csvRow[lang_column])

            # if self.csvRow[lang_column] in self.languages_iso.keys():
            #     self.csvRow[lang_column] = self.languages_iso[self.csvRow[lang_column]]

            # return '||'.join(filter(None, tmp_list)).strip()

    def generate_csv_header_for_dspace(self):
        complete_header_list = self.initial_fieldnames

        if self.add_orcids:
            complete_header_list.append("dc.contributor.orcid[]")

        for lang in self.searched_for_languages:
            for field in self.fieldnames_with_language:
                if field not in self.fieldnames_with_no_language:
                    complete_header_list.append(field + "[" + lang + "]")

        complete_header_list += self.fieldnames_with_no_language

        return complete_header_list


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description='This is a script to convert Zotero CSV export to DSpace CSV format.')
    # parser.add_argument('--foo', action='store_true', help='foo help')
    # subparsers = parser.add_subparsers(help='sub-command help')
    parser.add_argument('-i', '--input-file', default=input_file,
                        help='This is the filename of the input csv file from Zotero. If none is specified, input.csv is used.',
                        required=False)
    parser.add_argument('-o', '--output-file', default=output_file,
                        help='This is the filename of the generated csv file (to be imported to DSpace). If none is specified, output.csv is used.',
                        required=False)
    parser.add_argument('-hdl', '--handle', default=handle,
                        help='This is the collection handle (target collection) If none is specified, 7/1234 is used.',
                        required=False)
    parser.add_argument('-ao', '--add-orcids', action='store_true',
                        help='Add ORCiDs from file. It loads ORCiDs from ./settings/orcid.csv. This CSV file includes 3 columns (surname, name, ORCiD).',
                        required=False)
    # parser_a.set_defaults(which='migrate')

    args = parser.parse_args()
    # print(args)
    input_file = args.input_file
    output_file = args.output_file
    handle = args.handle
    add_orcids = args.add_orcids

    # obj = SpreadSheet(input_file, output_file, handle)
    # obj.importCSV()
    # obj.exportCSV()

    try:

        obj = SpreadSheet(input_file, output_file, handle, add_orcids)
        obj.importCSV()
        obj.exportCSV()

    except AttributeError:
        print ("\nUse -h for instructions.\n")
