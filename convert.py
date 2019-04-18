#!/usr/bin/env python
# -*- coding: utf-8 -*-

import csv as csv
from collections import OrderedDict
import langid
from langid.langid import LanguageIdentifier, model
import unicodedata
from decimal import Decimal
import argparse
import sys
import re

from stdnum import isbn, issn
import yaml

output_file = 'output.csv'
input_file = 'input.csv'
handle = '7/1234'
ZOTERO_LANGUAGES = './settings/languages_zotero.csv'


class SpreadSheet:

    def __init__(self, input_file, output_file, handle):
        self.input_file = input_file
        self.output_file = output_file
        self.handle = handle
        self.di = OrderedDict()
        self.csvRow = None
        self.detected_languages = []
        self.document_types = None



        '''
        Scan csv for these language. ALso use this languages to generate DSpace csv land headers.

        '''
        self.searched_for_languages = ['el', 'en', 'fr', 'de', 'tr', 'es', 'sk', '']
        self.langid_languages = ['el', 'en', 'fr', 'de', 'tr', 'es', 'sk']
        self.oDi = OrderedDict()
        self.langid_identifier = LanguageIdentifier.from_modelstring(model, norm_probs=True)

        self.languages_iso = {}

        with open('./settings/types.yml', 'r') as typefile:
            cfg = yaml.load(typefile, Loader=yaml.FullLoader)

        self.document_types = cfg['types']
        # print(types)


    def loadLanguages(self):

        try:
            readdata = csv.reader(open(ZOTERO_LANGUAGES))
        except FileNotFoundError:
            print('Zotero language file not found: ' + ZOTERO_LANGUAGES)
            sys.exit()
        self.languages_iso = {rows[0]: rows[1] for rows in readdata}
        # print(self.languages_iso)



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
        # lol = list(csv.reader(open('text.txt', 'rb'), delimiter='\t'))

        try:
            print(self.input_file)
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
        #
        # print(di[0])
        # print(di[122])

        # for key, value in di.items():
        #     print(str(key) + ': ' + value[2])

        '''
        Generate a dictionary with keys, the csv headers of the ending csv file
        '''
        # keys = self.generate_csv_header_for_dspace()
        # temp_row = OrderedDict()
        # for k in keys:
        #     temp_row[k] = ''
        # print('-------------------------------')
        # print(temp_row)

        # oDi = OrderedDict()
        # j = 0
        for key, value in di.items():
            # print(key)
            # By-pass non-valid lines (caused by refworks output)
            if len(value) < 10 or str(value).startswith("['Reference Typ"):
                # print('Empty key at: ' + str(key) + ' where value was: ' + str(value))
                continue

            self.oDi[key] = OrderedDict()
            self.csvRow = value
            # print(value)

            self.oDi[key]['id'] = '+'
            self.oDi[key]['collection'] = self.handle

            # dc.type
            self.csvRow[1] = self.csvRow[1].strip()
            self.enrich_document_type(1)
            # print(self.csvRow[0])
            self.oDi[key]['dc.type.uhtype[en]'] = self.csvRow[1]

            # dc.language.iso
            self.csvRow[28] = self.csvRow[28].strip()
            self.rename_language(28)
            # print(self.csvRow[0])
            self.oDi[key]['dc.language.iso[en]'] = self.csvRow[28]

            # dc.contributor.author
            # self.create_authors(key, [3])
            self.create_metadata_with_language(key, [3], "dc.contributor.author")

            # dc.contributor.translator
            # self.create_translator(key, [43])
            self.create_metadata_with_language(key, [43], "dc.contributor.translator")

            # dc.title
            # self.create_title(key, [4])
            self.create_metadata_with_language(key, [4], "dc.title")

            # dc.source
            # self.create_source(key, [5, 71])
            self.create_metadata_with_language(key, [5, 71], "dc.source")

            # dc.source.abbreviation
            # self.create_source_abbreviation(key, [20])
            self.create_metadata_with_language(key, [20], "dc.source.abbreviation")

            # dc.source.other
            # self.create_source(key, [39])

            # dc.date.issued (no language distinction)
            self.oDi[key]['dc.date.issued[]'] = self.create_date_issued(2, 11)

            # dc.date.available (no language distinction)
            # self.oDi[key]['dc.date.available[]'] = self.csvRow[6].strip()

            # dc.description.volume
            # self.create_volume(key, [18])
            self.create_metadata_with_language(key, [18], "dc.description.volume")

            # dc.description.issue
            # self.create_issue(key, [17])
            self.create_metadata_with_language(key, [17], "dc.description.issue")

            # dc.description.startingpage
            self.oDi[key]['dc.description.startingpage[]'] = self.create_startingpage(15)

            # dc.description.endingpage
            self.oDi[key]['dc.description.endingpage[]'] =  self.create_endingpage(15)

            # dc.description.totalnumpages[]
            self.oDi[key]['dc.description.totalnumpages[]'] = self.csvRow[16].strip()

            # dc.subject
            # self.create_subjects(key, [39])
            self.create_metadata_with_language(key, [39], "dc.subject")

            # dc.description.abstract
            # self.create_description_abstract(key, [10])
            self.create_metadata_with_language(key, [10], "dc.description.abstract")

            # dc.description.notes
            # self.create_description(key, [36])
            self.create_metadata_with_language(key, [36], "dc.description.notes")

            # dc.description.edition
            # self.create_edition(key, [71])
            self.create_metadata_with_language(key, [71], "dc.description.edition")

            # dc.publisher
            # self.create_publisher(key, [26])
            self.create_metadata_with_language(key, [26], "dc.publisher")

            # dc.coverage.spatial
            # self.create_spatial(key, [27])
            self.create_metadata_with_language(key, [27], "dc.coverage.spatial")

            # dc.identifier
            # self.oDi[key]['dc.identifier[]'] = self.csvRow[24].strip()
            # oDi[key][16] = self.generate_repeative_fields([24])

            # dc.identifier.lc // dc.identifier.lc[en]
            # self.oDi[key]['dc.identifier.other[]'] = self.generate_repeative_fields([27, 29])

            # dc.identifier.lc[]
            # SPECIAL
            self.create_lc(key, [34])

            # dc.language.iso
            self.oDi[key]['dc.language.iso[]'] = self.csvRow[28].strip()

            # dc.title.alternative
            # oDi[key][19] = self.generate_repeative_fields([23, 31])

            # dc.source.uri
            self.oDi[key]['dc.source.uri[]'] = self.generate_repeative_fields([9, 38])

            # dc.identifier.doi
            self.oDi[key]['dc.identifier.doi[]'] = self.csvRow[8].strip()

            # dc.contributor.editor
            # self.create_editor(key, [41, 42])
            self.create_metadata_with_language(key, [41, 42], "dc.contributor.editor")

            """
                dc.identifier.isbn	International Standard Book Number
                dc.identifier.ismn	International Standard Music Number
                dc.identifier.issn
            """
            '''
            num_type, num_data = self.create_isbn_or_issn(key, [24])
            if num_type == 'issn':
                self.oDi[key]['dc.identifier.issn[]'] = num_data
            else:
                self.oDi[key]['dc.identifier.isbn[]'] = num_data
            '''
            self.oDi[key]['dc.identifier.isbn[]'] = self.create_isbn(key, [6])
            self.oDi[key]['dc.identifier.issn[]'] = self.create_isbn(key, [7])

            """
            Regex validator for LC
            [A-Z]{1,4}[0-9]{1,4}([.][0-9]{1,3})?([.][A-Z]?)?[0-9]+([\w ]+[0-9]{4})? 
            """

            # print(self.oDi[key])

        # for key, value in oDi.items():
        #     print (str(key) + ': ' + value[23])
        # print(self.oDi)

    '''
            with open('export.csv', 'w') as csvfile:

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
    '''

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
        # print(tmp_list)
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

    # def create_isbn_or_issn(self, key, var_list=None):
    #     tmp_list = []
    #     type = None
    #     for var in var_list:
    #         # print(self.csvRow[var].strip())
    #         tmp_elem = re.split('; |, ', self.csvRow[var].strip())
    #         for i in range(len(tmp_elem)):
    #             """
    #             Filter ISSN and ISBN only
    #             """
    #             tmp_var_issn = self.remove_non_issn_chars(tmp_elem[i].upper())
    #             tmp_var_isbn = self.remove_non_isbn_chars(tmp_elem[i].upper())
    #             if issn.is_valid(tmp_var_issn):
    #                 # print("Valid ISSN: " + tmp_var_issn)
    #                 tmp_elem[i] = issn.format(tmp_var_issn)
    #                 type = 'issn'
    #
    #             elif isbn.is_valid(tmp_var_isbn):
    #                 # print("Valid ISBN: " + tmp_var_isbn)
    #                 tmp_elem[i] = isbn.format(tmp_var_isbn)
    #                 type = 'isbn'
    #
    #             else:
    #                 tmp_elem[i] = None
    #
    #         # Filter all elements, remove text chars, parenthesis etc
    #
    #         # print(tmp_elem)
    #         tmp_list += tmp_elem
    #         # print(tmp_list)
    #     tmp_list = list(filter(None, tmp_list))  # remove empty list elements
    #     # print(tmp_list)
    #     # No semi-colon, so do a join here. Cannot use the function to split semi-colons
    #     return type, '||'.join(filter(None, tmp_list)).strip()

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
        langid.set_languages(['de', 'fr', 'it'])
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
            # if detected_langid_value == 'el':
            #     detected_langid_value = 'el_GR'
            return detected_langid_value
        else:
            detected_langid_value = 'en'

        # Gent, België
        # German
        #
        # ä → ae
        # ö → oe
        # ü → ue
        # Ä → Ae
        # Ö → Oe
        # Ü → Ue
        # ß → ss( or SZ)

        # Turkish
        # ş, Ğ, İ, ğ, ı, ç

        # Spanish
        # ñ
        chars_el = set('αβγδεζηθικλμνξοπρσςτυφχψω')
        chars_en = set('abcdefghijklmnopqrstuvwxyz')
        chars_fr = set('éàèùâêîôûçëïü')
        chars_de = set('äöüß')
        chars_tr = set('şĞİğı')
        chars_es = set('ñóíáã')
        chars_sk = set('ýúčžň')
        chars_cz = set('řťšůď')

        # if str.startswith("Gagatsis"):
        #     if any((c in chars_el) for c in str):
        #         print('GREEK in Gagatsis')

        '''
        If a greek character exists, return greek language immediately
        '''
        # if 'GREEK' in unicodedata.name(str.strip()[0]):
        #     return 'el_GR'
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

            return return_value

        '''
        If no language is detected, return an empty string.
        This helps set DC values with no language.
        xstr = lambda s: s or ""
        '''
        return ''

    def generate_repeative_fields(self, var_list=None):
        # Generate a string list of source fields
        # my_list is a list of fields seperated with ';' by export. They need to change to '||'
        # this happens in author fields
        # my_list = {
        #     # authors
        #     1, 15, 20, 21, 22,
        #     # Subjects
        #     11
        # }
        temp_list = list()

        for var in var_list:
            # if var in my_list:
            self.csvRow[var] = self.replace_semicolon_with_vertical(self.csvRow[var])
            temp_list.append(self.csvRow[var].strip())

        return '||'.join(filter(None, temp_list)).strip()

    def replace_semicolon_with_vertical(self, var):
        return var.replace(';', '||')

    def enrich_document_type(self, str):
        if str in self.document_types:
            return self.document_types[str]

    def rename_language(self, lang_column):
        if self.csvRow[lang_column] in self.languages_iso.keys():
            self.csvRow[lang_column] = self.languages_iso[self.csvRow[lang_column]]

    def generate_csv_header_for_dspace(self):
        fieldnames = [
            # 'dc.type.uhtype',
            'dc.contributor.author',
            'dc.title',
            'dc.title.alternative',
            'dc.source',
            'dc.source.other',
            'dc.source.abbreviation',
            'dc.description.volume',
            'dc.description.issue',
            # 'dc.description.startingpage',
            # 'dc.description.endingpage',
            'dc.subject',
            'dc.description.abstract',
            'dc.description.notes',
            'dc.description.edition',
            'dc.contributor.editor',
            'dc.contributor.translator',
            'dc.publisher',
            'dc.coverage.spatial',
            # 'dc.identifier',
            # 'dc.identifier.lc',
            # 'dc.language.iso',
            # 'dc.title.alternative',
            # 'dc.source.uri',
            # 'dc.identifier.doi',
        ]
        fieldnames_with_no_language = [
            'dc.date.issued[]',
            'dc.date.available[]',
            'dc.description.startingpage[]',
            'dc.description.endingpage[]',
            'dc.description.totalnumpages[]',
            'dc.identifier[]',
            'dc.identifier.doi[]',
            'dc.identifier.isbn[]',
            'dc.identifier.issn[]',
            # 'dc.identifier.ismn[]',
            'dc.source.uri[]',
            'dc.identifier.other[]'
        ]
        complete_header_list = ['id', 'collection', 'dc.type', 'dc.type.uhtype[en]', 'dc.language.iso[en]',
                                'dc.identifier.lc[en]']
        for lang in self.searched_for_languages:
            for field in fieldnames:
                if field not in fieldnames_with_no_language:
                    #     complete_header_list.append(field)
                    # else:
                    complete_header_list.append(field + "[" + lang + "]")

        complete_header_list += fieldnames_with_no_language
        return complete_header_list


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description='This is a script to convert RefWorks CSV export to DSpace CSV format.')
    # parser.add_argument('--foo', action='store_true', help='foo help')
    # subparsers = parser.add_subparsers(help='sub-command help')
    parser.add_argument('-i', '--input-file', default=input_file,
                        help='This is the filename of the input csv file from RefWorks. If none is specified, input.csv is used.',
                        required=False)
    parser.add_argument('-o', '--output-file', default=output_file,
                        help='This is the filename of the generated csv file (to be imported to DSpace). If none is specified, output.csv is used.',
                        required=False)
    parser.add_argument('-hdl', '--handle',
                        help='This is the collection handle (target collection) If none is specified, 7/1234 is used.',
                        required=False)
    # parser_a.set_defaults(which='migrate')

    args = parser.parse_args()
    # print(args)
    input_file = args.input_file
    output_file = args.output_file
    handle = args.handle

    # obj = SpreadSheet(input_file, output_file, handle)
    # obj.loadLanguages()
    # obj.importCSV()
    # obj.exportCSV()

    try:
        input_file = args.input_file
        output_file = args.output_file
        handle = args.handle

        obj = SpreadSheet(input_file, output_file, handle)
        obj.loadLanguages()
        obj.importCSV()
        obj.exportCSV()

    except AttributeError:
        print ("\nUse -h for instructions.\n")
