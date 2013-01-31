ATTRIBUTE = "@attribute"

class Record(object):
    def __init__(self, attribute, length, start, datatype, translator):
        self.attribute = attribute
        self.length = length
        self.start = start
        self.datatype = datatype
        self.translator = translator

    def get_attribute_declaration(self):
        attrib = []
        attrib.append(ATTRIBUTE)
        attrib.append(" ")
        attrib.append(self.attribute)
        attrib.append(" ")
        attrib.append(self.datatype())
        return "".join(attrib)

    def convert(self, row):
        s = self.start - 1
        e = s + self.length
        return self.translator(row[s:e])

def translate_numeric(num):
    return long

def translate_string(obj):
    return str(obj[1:-1])

def build_dict2attribute(target):
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

marital = { '1' : 'Single', '2' : 'Married', '3' : 'Seperated', '4':'Divorced',
'5':'Widowed', '6':'Unmarried', '9':'Unkown'}

married = Record("marital", 1, 19, build_dict2attribute(marital), get_dict_translator(marital))
