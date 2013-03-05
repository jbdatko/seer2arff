import os
import re
import logging

logging.basicConfig(
    format = "%(levelname) -4s %(asctime)s %(message)s",
    level = logging.INFO
    )

log = logging.getLogger('seer2arff')

breast = "/Users/jdatko/cs610/SEER_1973_2009_TEXTDATA/incidence/yr1973_2009.seer9/BREAST.txt"

# The default survival time recode value.  This can be changed with a command line option
DEFAULT_STR = 24


def nines_to_question_mark(value):
    """Most of the SEER attributes use all nines to indicate missing or unkown
    data.  The ARFF format is to represent this data as a question mark.

    Args:
        String representing the SEER value

    Returns:
        The orignal value or a question mark if the value was all nines
    """

    if re.search('^9+$', value):
        return '?'
    else:
        return value

def format_blank(func):
    """Returns a function that will format blanks in the SEER data.  Useful as
    a decorator.

    Args:
        func: The function to wrap

    Returns:
        A function that will format missing entries in a SEER row
    """

    def remove_blank(*args, **kwargs):
        """Converts SEER missing data with the ARFF missing data sentinel.

        Returns:
            The ARFF missing data sentinel value.
        """
        value = func(*args, **kwargs)
        if ' ' in value:
            value = '?'

        return value

    return remove_blank


class SeerAttribute(object):

    """Encapsulate a SEER column (attribute) into this class.  This class is a
    generic SeerAttribute and derived classes, perhaps with specific data
    transformations, are encouraged.

    Attributes:
        start: integer indicating the start of the SEER attribute.
        length: integer number of characters for this attribute
        name: string representing the unique name of this attribute
        datatype: The ARFF datatype (numeric, nominal, date, or string)
    """

    def __init__(self, start, length, name, datatype="numeric"):
        """Init the class with the definitions from the SEER data dictionary.

        Args:
            start: int start position of the attribute (as described by the
                SEER data dictionary)
            length: the length of the attribute
            name: the string representing the attribute name
            datatype: string representing the ARFF datatype
        """

        self.start = start - 1  # oncologists starting counting at 1
        self.length = length
        self.name = name
        self.datatype = datatype

    @property
    def end(self):
        """A convenient property to store the end of the attribute
        Returns:
            An integer end of the attribute.
        """

        return self.start + self.length

    def _get_repr(self):

        """Utility function to return the common attributes of the class in a
        consistent manner.  Useful when building the repr string.

        Returns:
            The parenthesis part of the repr string, which *should* be common
            to the class hierarchy.
        """
        return "(%d,%d,%s,%s)" % (self.start, self.length, self.name,
                                  self.datatype)

    def __repr__(self):
        return "SeerAttribute" + self._get_repr()

    def __string__(self):
        return self.name

    def _get_from_seer(self, seer_string):
        """Slices out this classes attribute from the SEER row.

        Args:
            seer_string: String representing one row in the SEER database.

        Returns:
            The SEER encoded value specific for this attribute.
        """
        return seer_string[self.start:self.end]

    def get_meta_string(self):

        """Get the ARFF string describing this attribute.  This string must
        precede data in ARFF files.

        Returns:
            The ARFF attribute description string.
        """
        return "@attribute %s %s" % (self.name, self.datatype)

    @format_blank
    def get_attribute(self, seer_string):
        """Retrieves the attribute value from the SEER row.  This method should
            be overridden by derived classes if custom data manipulation is
            required during seer2arff conversion.

        Args:
            seer_string: String representing the encoded SEER row.

        Returns:
            A string representing this attributes SEER value.
        """
        val = self._get_from_seer(seer_string)
        return nines_to_question_mark(val)

    def is_match(self, seer_string, match):
        """Utility method to test if the match parameter matches this
        attribute's value from the SEER row.

        Args:
            seer_string: String representing the SEER encoded row.
            match: String representing the string to match against.

        Returns:
            True if match equals the attributes value, False otherwise.
        """
        value = self._get_from_seer(seer_string)

        if value == match:
            return True
        else:
            return False


class SeerNominalAttribute(SeerAttribute):
    """Class definition for SEER nominal data types (those with categorical
    data).  Extends SeerAttribute to provide a custom attribute string.
    """

    def get_meta_string(self):
        return "@attribute %s %s" % (self.name, self.datatype)

    def __repr__(self):
        return "SeerNominalAttribute" + self._get_repr()


class ErPrStatusRecord(SeerNominalAttribute):

    def get_attribute(self, seer_string):

        value = super(SeerNominalAttribute,self).get_attribute(seer_string)

        if re.search('^4$', value):
            return '?'
        else:
            return value

    def __repr__(self):
        return "ErPrStatusRecord" + self._get_repr()


class SurvivalTimeRecode(SeerNominalAttribute):
    """Derived SeerAttribute that encapsulates the Survival Time Recode.

    STR is defined as (from the SEER data dictionary): The Survival Time Recode
    is calculated using the date of diagnosis and one of the following: date of
    death, date last known to be alive, or follow-up cutoff date used for this
    file (see title page for date for this file). Thus a person diagnosed in
    May 1976 and who died in May 1980 has a Survival Time Recode of 04 years
    and 00 months.
    """

    def _to_months(self, seer_string):
        """Converts the STR to pure months instead of the YYMM format.

        Args:
            seer_string: String representing the SEER row

        Returns:
            String, meeting the following regexp: [0-9]+
            So, this could possibly not be 4 characters, which is ok since the
            ARFF format is flexible on fixed data strings.
        """
        val = self._get_from_seer(seer_string)
        if "9999" in val or ' ' in val:
            return "?"
        else:

            years = int(val[0:2])
            months = int(val[2:4])

            time = years * 12 + months
            converted = str(time)

            return converted

    def _to_nominal(self, months):

        months = int(months)
        TIER1 = DEFAULT_STR

        if months <= TIER1:
            return '1'
        else:
            return '2'

    def get_attribute(self, seer_string):
        return self._to_nominal(self._to_months(seer_string))

    def __repr__(self):
        return "SurvivalTimeRecode" + self._get_repr()

class VitalStatusRecode(SeerAttribute):

    def is_dead(self, seer_string):

        DEAD_CODE = '4'

        return self.is_match(seer_string, DEAD_CODE)

    def __repr__(self):
        return "VitalStatusRecode" + self._get_repr()

class CauseSpecificDeathClassification(SeerAttribute):

    def is_dead_from_cancer(self, seer_string):
        DEAD_OF_CANCER = "1"

        return self.is_match(seer_string, DEAD_OF_CANCER)

    def __repr__(self):
        return "CauseSpecificDeathClassification" + self._get_repr()


class AJCCStage3rdEdition(SeerAttribute):

    def is_stage_iv(self, seer_string):
        stage4 = '^4\d$'
        val = self._get_from_seer(seer_string)

        return re.search(stage4, val)

    def __repr__(self):
        return "AJCCStage3rdEdition" + self._get_repr()

def convert_seer_to_arff(types_list, seer_string):
    output = ""
    for t in types_list:
        output = output + t.get_attribute(seer_string) + ","

    #Remove trailing comma
    output = output[:len(output)-1]
    return output

def count_matches(seer_file, query):
    count = 0
    with open(seer_file) as seer:
        for line in seer:
            if query(line):
                count = count + 1

    return count

def get_year_filter(year, seer_attribs):

    def is_year_greater_than(seer_string):

        val = seer_attribs['year-of-dx'].get_attribute(seer_string)

        if '?' in val:
            return False

        year_from_seer = int(val)

        if year > year_from_seer:
            return True
        else:
            return False


def get_truth_combinator(func_list):
    """Return an is_all_true function that closes over func_list

    Args:
        A list of functions that return True or False when passed in the SEER
        row.

    Returns:
        A function that contains the func_list as a closure.
    """
    def is_all_true(seer_string):
        """Evaluates all functions over the SEER string.

        Args:
            String representing the SEER row.

        Returns:
            True if all functions return True when passed the SEER string,
            otherwise False.
        """
        results = [f(seer_string) for f in func_list]
        return reduce(lambda x, y: x and y, results, True)

    return is_all_true


def builder(seer, cls, name, start, length, datatype="numeric"):
    seer[name] = cls(start, length, name, datatype)


def load_seer_types():



    attribs = dict()

    builder(attribs, SeerNominalAttribute, 'marital-status-at-dx', 19, 1,
            '{1,2,3,4,5}')
    #builder(attribs, SeerNominalAttribute, 'sex', 24, 1, '{1,2}')
    builder(attribs, SeerAttribute, 'age-at-dx', 25, 3)
    #builder(attribs, SeerAttribute, 'birth-place', 32, 3)
    #builder(attribs, SeerAttribute, 'sequence-number-central', 35, 2)
    builder(attribs, SeerAttribute, 'year-of-dx', 39, 4)
    #builder(attribs, SeerAttribute, 'primary-site', 43, 4, 'string')
    #builder(attribs, SeerAttribute, 'laterality', 47, 1)
    #builder(attribs, SeerAttribute, 'histology', 48, 4)
    #builder(attribs, SeerAttribute, 'histologic-type', 53, 4)
    builder(attribs, SeerNominalAttribute, 'grade', 58, 1, '{1,2,3,4}')
    #builder(attribs, SeerAttribute, 'dx-confirmation', 59, 1)
    builder(attribs, SeerAttribute, 'eod-tumor-size', 61, 3)
    #builder(attribs, SeerAttribute, 'eod-extension', 64, 2)
    builder(attribs, SeerNominalAttribute, 'eod-lymph-node-involv', 68, 1, '{0,1,2,3,4,5,6,7,8}')
    #builder(attribs, SeerAttribute, 'regional-nodes-positive', 69, 2)
    #builder(attribs, SeerAttribute, 'regional-nodes-examined', 71, 2)
    #builder(attribs, SeerNominalAttribute, 'tumor-marker-1', 93, 1, '{0,1,2,3,8,9}')
    #builder(attribs, SeerNominalAttribute, 'tumor-marker-2', 94, 1, '{0,1,2,3,8,9}')
    #builder(attribs, SeerAttribute, 'cs-tumor-size', 96, 3)
    #builder(attribs, SeerAttribute, 'cs-extension', 99, 3)
    #builder(attribs, SeerAttribute, 'cs-lymph-nodes', 102, 3)
    #builder(attribs, SeerAttribute, 'cs-mets-at-dx', 105, 2)
    #builder(attribs, SeerAttribute, 'cs-site-specific-factor-1', 107, 3)
    #builder(attribs, SeerAttribute, 'cs-site-specific-factor-2', 110, 3)
    #builder(attribs, SeerAttribute, 'cs-site-specific-factor-3', 113, 3)
    #builder(attribs, SeerAttribute, 'cs-site-specific-factor-4', 116, 3)
    #builder(attribs, SeerAttribute, 'cs-site-specific-factor-5', 119, 3)
    #builder(attribs, SeerAttribute, 'cs-site-specific-factor-6', 122, 3)
    #builder(attribs, SeerAttribute, 'derived-ajcc-t', 128, 2)
    #builder(attribs, SeerAttribute, 'derived-ajcc-n', 130, 2)
    #builder(attribs, SeerAttribute, 'derived-ajcc-m', 132, 2)
    #builder(attribs, SeerAttribute, 'rx-summ-surg-prim-site', 159, 2)
    #builder(attribs, SeerAttribute, 'rx-summ-scope-reg-ln-sur', 161, 1)
    #builder(attribs, SeerAttribute, 'rx-summ-surg-oth-reg-dis', 162, 1)
    #builder(attribs, SeerAttribute, 'rx-summ-reg-ln-examined', 163, 2)
    #builder(attribs, SeerAttribute, 'rx-summ-reconstruct-1', 165, 1)
    builder(attribs, SeerNominalAttribute, 'reason-for-no-surgery', 166, 1, '{0,1,2,6,7,8}')
    #builder(attribs, SeerAttribute, 'rx-summ-radiation', 167, 1)
    #builder(attribs, SeerAttribute, 'rx-summ-surg-rad-seq', 169, 1)
    #builder(attribs, SeerAttribute, 'rx-summ-surg-site-98-02', 172, 2)
    #builder(attribs, SeerAttribute, 'seer-record-number', 176, 2)
    builder(attribs, SeerNominalAttribute, 'race-recode', 234, 1, '{1,2,3,4,7}')
    #builder(attribs, SeerAttribute, 'origin-recode', 235, 1)
    #builder(attribs, SeerAttribute, 'seer-historic-stage-a', 236, 1)
    #builder(attribs, SeerAttribute, 'number-of-primaries', 243, 2)
    #builder(attribs, SeerAttribute, 'first-malignant-primary-indicator',
    #        245, 1)
    builder(attribs, SurvivalTimeRecode, 'survival-time-recode', 251, 4, '{1,2}')
    builder(attribs, VitalStatusRecode, 'vital-status-recode', 265, 1)
    builder(attribs, CauseSpecificDeathClassification,
            'seer-cause-specific-death-classification', 272, 1)
    builder(attribs, ErPrStatusRecord, 'er-status-recode-breast-cancer', 278,
            1, '{1,2,3}')
    builder(attribs, ErPrStatusRecord, 'pr-status-recode-breast-cancer', 279,
            1, '{1,2,3}')
    #builder(attribs, SeerAttribute, 'cs-site-specific-factor-8', 282, 3)
    #builder(attribs, SeerAttribute, 'cs-site-specific-factor-10', 285, 3)
    #builder(attribs, SeerAttribute, 'cs-site-specific-factor-11', 288, 3)
    #builder(attribs, SeerAttribute, 'cs-site-specific-factor-15', 294, 3)
    #builder(attribs, SeerAttribute, 'cs-site-specific-factor-16', 297, 3)
    #builder(attribs, SeerAttribute, 'lymph-vascular-invasion', 300, 1)
    builder(attribs, AJCCStage3rdEdition, 'ajcc-stage-3rd-edition', 237, 2)
    #builder(attribs, SeerAttribute, 'rx-summ-rad-2-cns', 168, 1)

    return attribs


d = load_seer_types()

def get_relation():
    return "@relation breast"

def format_instance(row, attributes):

    output = ""
    for attrib in attributes:
        output = output + attrib.get_attribute(row) + ","

    output = output[:len(output)-1]  # removing trailing comma

    return output


def to_arff(attribs, seer_file, output, filters=None):

    log.info("Started conversion.")

    keys = attribs.values()

    with open(output, "w") as outfile:
        with open(seer_file) as infile:

            outfile.write(get_relation() + "\n")

            for k in keys:
                outfile.write(k.get_meta_string() + "\n")

            outfile.write("\n@data\n")

            totalRecords = 0
            selectedRecords = 0

            for line in infile:
                totalRecords += 1

                if filters == None or filters(line):

                    outfile.write(format_instance(line, keys) + "\n")
                    selectedRecords += 1


    log.info("Processed %d total records" % (totalRecords))
    log.info("Selected %d records" % (selectedRecords))


filters = [d['ajcc-stage-3rd-edition'].is_stage_iv,
           d['seer-cause-specific-death-classification'].is_dead_from_cancer,
           d['vital-status-recode'].is_dead]

if __name__=="__main__":
    import optparse

    parser = optparse.OptionParser()

    # Get the option for survival time recode length
    parser.add_option("-t", "--time", action="store", type="int", dest="time", default=DEFAULT_STR)

    #parse the command line
    opts, args = parser.parse_args()

    output_file = args[0]

    DEFAULT_STR = opts.time

    log.info("Using survival time recode value of %d months" % (DEFAULT_STR))

    to_arff(d, breast, output_file, get_truth_combinator(filters))
