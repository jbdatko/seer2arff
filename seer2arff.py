import os
import re

breast =
"/Users/jdatko/cs610/SEER_1973_2009_TEXTDATA/incidence/yr1973_2009.seer9/BREAST.txt"


def format_blank(func):
    """Returns a function that will format blanks in the SEER data.  Useful as a
    decorator.

    Args:
        func: The function to wrap

    Returns:
        A function that will format missing entries in a SEER row
    """

    def remove_blank(*args,**kwargs):
        """Converts SEER missing data with the ARFF missing data sentinel.

        Returns:
            The ARFF missing data sentinel value.
        """
        value = func(*args,**kwargs)
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

        self.start = start - 1 #oncologists starting counting at 1
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
        return self._get_from_seer(seer_string)


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

class SurvivalTimeRecode(SeerAttribute):
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
            print "orignal: " + val
            years = int(val[0:2])
            months = int(val[2:4])

            time = years * 12 + months
            converted = str(time)
            print converted
            return converted

    def get_attribute(self, seer_string):
        return self._to_months(seer_string)

    def __repr__(self):
        return "SurvivalTimeRecode" + self._get_repr()

class VitalStatusRecode(SeerAttribute):

    def is_dead(self, seer_string):

        DEAD_CODE = '4'

        val = self._get_from_seer(seer_string)

        return self.is_match(val, DEAD_CODE)

    def __repr__(self):
        return "VitalStatusRecode" + self._get_repr()

class CauseSpecificDeathClassification(SeerAttribute):

    def is_dead_from_cancer(self, seer_string):
        DEAD_OF_CANCER = "1"

        val = self._get_from_seer(seer_string)

        return self.is_match(val, DEAD_OF_CANCER)

class AJCCStage3rdEdition(SeerAttribute):

    def is_stage_iv(self, seer_string):
        stage4 = '^4\d$'
        val = self._get_from_seer(seer_string)

        return re.search(stage4, val)

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

def load_seer_types():

    seer_types = dict()

    seer_types['marital-status-at-dx'] = SeerAttribute(19, 1, 'marital-status-at-dx')
    seer_types['sex'] = SeerAttribute(24, 1, 'sex')
    seer_types['age-at-dx'] = SeerAttribute(25, 3, 'age-at-dx')
    seer_types['birth-place'] = SeerAttribute(32, 3, 'birth-place')
    seer_types['sequence-number-central'] = SeerAttribute(35, 2, 'sequence-number-central')
    seer_types['year-of-dx'] = SeerAttribute(39, 4, 'year-of-dx')
    seer_types['primary-site'] = SeerAttribute(43, 4, 'primary-site')
    seer_types['laterality'] = SeerAttribute(47, 1, 'laterality')
    seer_types['histology'] = SeerAttribute(48, 4, 'histology')
    seer_types['histologic-type'] = SeerAttribute(53, 4, 'histologic-type')
    seer_types['grade'] = SeerAttribute(58, 1, 'grade')
    seer_types['dx-confirmation'] = SeerAttribute(59, 1, 'dx-confirmation')
    seer_types['eod-tumor-size'] = SeerAttribute(61, 3, 'eod-tumor-size')
    seer_types['eod-extension'] = SeerAttribute(64, 2, 'eod-extension')
    seer_types['eod-lymph-node-involv'] = SeerAttribute(68, 1, 'eod-lymph-node-involv')
    seer_types['regional-nodes-positive'] = SeerAttribute(69, 2, 'regional-nodes-positive')
    seer_types['regional-nodes-examined'] = SeerAttribute(71, 2, 'regional-nodes-examined')
    seer_types['tumor-marker-1'] = SeerAttribute(93, 1, 'tumor-marker-1')
    seer_types['tumor-marker-2'] = SeerAttribute(94, 1, 'tumor-marker-2')
    seer_types['cs-tumor-size'] = SeerAttribute(96, 3, 'cs-tumor-size')
    #http://web2.facs.org/cstage0204/breast/Breast_hau.html
    seer_types['cs-mets-at-dx'] = SeerAttribute(105, 2, 'cs-mets-at-dx')
    seer_types['cs-site-specific-factor-3'] = SeerAttribute(113, 3, 'cs-site-specific-factor-3')
    seer_types['cs-site-specific-factor-4'] = SeerAttribute(116, 3, 'cs-site-specific-factor-4')
    seer_types['cs-site-specific-factor-5'] = SeerAttribute(119, 3, 'cs-site-specific-factor-5')
    seer_types['cs-site-specific-factor-6'] = SeerAttribute(122, 3, 'cs-site-specific-factor-6')
    seer_types['derived-ajcc-t'] = SeerAttribute(128, 2, 'derived-ajcc-t')
    seer_types['derived-ajcc-n'] = SeerAttribute(130, 2, 'derived-ajcc-n')
    seer_types['derived-ajcc-m'] = SeerAttribute(132, 2, 'derived-ajcc-m')
    seer_types['rx-summ-surg-prim-site'] = SeerAttribute(159, 2, 'rx-summ-surg-prim-site')
    seer_types['rx-summ-scope-reg-ln-sur'] = SeerAttribute(161, 1, 'rx-summ-scope-reg-ln-sur')
    seer_types['rx-summ-surg-oth-reg-dis'] = SeerAttribute(162, 1, 'rx-summ-surg-oth-reg-dis')
    seer_types['rx-summ-reg-ln-examined'] = SeerAttribute(163, 2, 'rx-summ-reg-ln-examined')
    seer_types['rx-summ-reconstruct-1'] = SeerAttribute(165, 1, 'rx-summ-reconstruct-1')
    seer_types['reason-for-no-surgery'] = SeerAttribute(166, 1, 'reason-for-no-surgery')
    seer_types['rx-summ-radiation'] = SeerAttribute(167, 1, 'rx-summ-radiation')
    seer_types['rx-summ-surg-rad-seq'] = SeerAttribute(169, 1, 'rx-summ-surg-rad-seq')
    seer_types['rx-summ-surg-site-98-02'] = SeerAttribute(172, 2, 'rx-summ-surg-site-98-02')
    seer_types['seer-record-number'] = SeerAttribute(176, 2, 'seer-record-number')
    seer_types['race-recode'] = SeerAttribute(234, 1, 'race-recode')
    seer_types['origin-recode'] = SeerAttribute(235, 1, 'origin-recode')
    seer_types['seer-historic-stage-a'] = SeerAttribute(236, 1, 'seer-historic-stage-a')
    seer_types['number-of-primaries'] = SeerAttribute(243, 2, 'number-of-primaries')
    seer_types['first-malignant-primary-indicator'] = SeerAttribute(245, 1, 'first-malignant-primary-indicator')
    seer_types['survival-time-recode'] = SurvivalTimeRecode(251, 4, 'survival-time-recode')
    seer_types['vital-status-recode'] = VitalStatusRecode(265, 1, 'vital-status-recode')
    seer_types['seer-cause-specific-death-classification'] = SeerAttribute(272, 1, 'seer-cause-specific-death-classification')
    seer_types['er-status-recode-breast-cancer'] = SeerAttribute(278, 1, 'er-status-recode-breast-cancer')
    seer_types['pr-status-recode-breast-cancer'] = SeerAttribute(279, 1, 'pr-status-recode-breast-cancer')
    seer_types['cs-site-specific-factor-8'] = SeerAttribute(282, 3, 'cs-site-specific-factor-8')
    seer_types['cs-site-specific-factor-10'] = SeerAttribute(285, 3, 'cs-site-specific-factor-10')
    seer_types['cs-site-specific-factor-11'] = SeerAttribute(288, 3, 'cs-site-specific-factor-11')
    seer_types['cs-site-specific-factor-15'] = SeerAttribute(294, 3, 'cs-site-specific-factor-15')
    seer_types['cs-site-specific-factor-16'] = SeerAttribute(297, 3, 'cs-site-specific-factor-16')
    seer_types['lymph-vascular-invasion'] = SeerAttribute(300, 1, 'lymph-vascular-invasion')
    seer_types['ajcc-stage-3rd-edition'] = AJCCStage3rdEdition(237, 2, 'ajcc-stage-3rd-edition')
    return seer_types

d = load_seer_types()
