import json
from os import listdir
from os.path import isfile, join
from collections import namedtuple

ATTRIBUTE = "@attribute"
NUMERIC_TYPE = "numeric"
STRING_TYPE = "string"
NOMINAL_TYPE = "nominal"
FILES_DIR = "/Users/jdatko/cs610/seer2arff/json_fields/"
OUTPUT = "output.arff"

Seer_Functor = namedtuple('Seer_Functor', ['attribute', 'convert'])

def build_attribute_function(attribute, datatype):
    """Returns a function that will return the ARFF attribute string when
    called"""

    def get_arff_attribute():
        """Returns the ARFF formatted attribute string declaration"""

        attrib = []
        attrib.append(ATTRIBUTE)
        attrib.append(" ")
        attrib.append(attribute)
        attrib.append(" ")
        attrib.append(datatype())
        return "".join(attrib)

    return get_arff_attribute

def build_converter(start, length, translator):
    """Given the start postion, length and a translator function specific to
    this data format, return a function that will convert the SEER encoded row
    to the ARFF format as specified by the translator function"""

    def convert(row):
        """Convert the encoded data starting at start, which is length long,
        according to the supplied translator."""

        s = start - 1
        e = s + length
        return translator(row[s:e])

    return convert

def translate_string(obj):
    return str(obj[1:-1])

def build_dict2attribute(target):
    """Returns a function that will produce the ARFF attribute string for a
    nominal type for the target dictionary"""

    def dict2attribute():
        result = []
        result.append('{')
        for k in target.values():
            result.append(k)
            result.append(',')

        del result[len(result) - 1]
        result.append('}')
        return "".join(result)

    return dict2attribute

def get_dict_translator(mapping):

    def translate_dict(raw):
        return mapping[raw]

    return translate_dict


def get_datatype(arff_type, nominal=None):

    if NUMERIC_TYPE in arff_type:
        return lambda : NUMERIC_TYPE
    elif STRING_TYPE in arff_type:
        return lambda : STRING_TYPE
    elif NOMINAL_TYPE in arff_type:
        return build_dict2attribute(nominal)
    else:
        return None

def get_translator(arff_type, codes=None):
    if NOMINAL_TYPE in arff_type:
        return get_dict_translator(codes)
    else:
        return lambda x: x

def json2func(json_data):
    """Given the json data file, return a pair of functions to (1) produce the
    ARFF attribute string and (2) convert the SEER row into the ARFF row"""

    datatype = json_data['datatype']
    codes = None

    print datatype
    print codes

    create_attribute = build_attribute_function(json_data['name'],
                                                get_datatype(datatype, codes))

    converter = build_converter(json_data['start'], json_data['length'],
                                get_translator(datatype, codes))

    return create_attribute, converter



def _get_value(l, start, length):
    s = start - 1
    return l[s:s+length]

def get_c(file, start, length):
    for l in file:
        value = _get_value(l, start, length)

        if ' ' in value:
            pass
        else:
            print value

def is_stage_iv(l):
    stage = _get_value(l,236, 1)
    if ' ' in stage:
        return False

    s = int(stage)
    if s == 4:
        return True
    else:
        return False

def is_dead(l):
    dead = _get_value(l,265,1)
    if ' ' in dead:
        return False

    s = int(dead)
    if 4 == s:
        return True
    else:
        return False

def is_dead_from_cancer(l):
    dead = _get_value(l,272,1)
    if ' ' in dead:
        return False

    s = int(dead)
    if 1 == s:
        return True
    else:
        return False

def breast_filter(row):
    if is_stage_iv(row) and is_dead(row) and is_dead_from_cancer(row):
        return row
    else:
        return None

def count_stage_4(file):
    num = 0
    for l in file:
        if is_stage_iv(l) and is_dead(l) and is_dead_from_cancer(l):
            num = num + 1
        else:
            pass

    return num





# marital = { '1' : 'Single', '2' : 'Married', '3' : 'Seperated', '4':'Divorced',
# '5':'Widowed', '6':'Unmarried', '9':'Unkown'}

# married_attrib = build_attribute_function("marital",
#     build_dict2attribute(marital))
# married_converter = build_converter(19, 1, get_dict_translator(marital))


# json_data = open("marital_status_at_dx.json")
# m = json.load(json_data)

# a, b = json2func(m)

breast = "/Users/jdatko/cs610/SEER_1973_2009_TEXTDATA/incidence/yr1973_2009.seer9/BREAST.txt"

records = open(breast)

#Grab all files in the FILES_DIR directory
files = [ f for f in listdir(FILES_DIR) if isfile(join(FILES_DIR,f)) ]
files = [ FILES_DIR + f for f in files]

open_files = [open(o) for o in files ]

jsons = [json.load(j) for j in open_files]

def convert_survival(row):
    val = row[250:254]
    if "9999" in val or ' ' in val:
        return "?"
    else:
        print "orignal: " + val
        years = int(val[0:2])
        months = int(val[2:4])

        time = years * 12 + months
        converted = str(time)
        print converted
        return converted

def create_functor(json_data):
    attribute, convert = json2func(json_data)
    if "survival-time-recode" in json_data['name']:
        print "found survival time"
        return Seer_Functor(attribute, convert_survival)

    return Seer_Functor(attribute, convert)

functors = [create_functor(j) for j in jsons]

out = open(OUTPUT, 'w+')

out.write("@relation breast")
out.write("\n")

for f in functors:
    out.write(f.attribute())
    out.write("\n")

out.write("@data")
out.write("\n")

for line in records:
    if breast_filter(line):
        output = ""
        for f in functors:
            value = f.convert(line)
            if ' ' in value:
                value = '?'
            output = output + value + ","
        output = output[:len(output)-1]
        out.write(output)
        out.write("\n")

out.close()
