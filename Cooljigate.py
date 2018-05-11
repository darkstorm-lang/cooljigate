#-----------------------------------------------------------------------------
# Darkstorm Library
# Copyright (C) 2018 Martin Slater
# Created : Friday, 11 May 2018 10:11:57 AM
#-----------------------------------------------------------------------------
""" Looks up a verb in cooljigator and creates a file suitable for importing
into Ankidroid with all forms """

#-----------------------------------------------------------------------------
# Imports
#-----------------------------------------------------------------------------
import sys
import tempfile
import argparse
import os
from urllib.request import urlopen, quote
from bs4 import BeautifulSoup

#-----------------------------------------------------------------------------
# Constants
#-----------------------------------------------------------------------------

IMPERFECTIVE_TEXT = "Expresses incomplete action."
PERFECTIVE_TEXT = "Expresses complete action."
MEANING_STR = "This verb can also mean the following: "

ASPECT_UNKNOWN = 0
ASPECT_PERFECT = 1
ASPECT_IMPERFECT = 2

FORM_UNKNOWN = 0
FORM_I = 1
FORM_HE = 2
FORM_WE = 3
FORM_THEY = 5
FORM_MASC = 6
FORM_FEM = 7
FORM_PLURAL = 8
FORM_NEUTER = 9
FORM_YOU = 10

TENSER_UNKNOWN = 0
TENSE_PRESENT = 1
TENSE_PAST = 2
TENSE_FUTURE = 3
TENSE_IMPERATIVE = 4
TENSE_CONDITIONAL = 5

PAST_TENSE_FORMS = {
    FORM_MASC: 'past_singM',
    FORM_FEM: 'past_singF',
    FORM_NEUTER: 'past_singN',
    FORM_PLURAL: 'past_plur'
}

PRESENT_TENSE_FORMS = {
    FORM_I: 'present1',
    FORM_YOU: 'present2',
    FORM_HE: 'present3',
    FORM_WE: 'present4',
    FORM_PLURAL: 'present5',
    FORM_THEY: 'present6'
}

FUTURE_TENSE_FORMS = {
    FORM_I: 'future1',
    FORM_YOU: 'future2',
    FORM_HE: 'future3',
    FORM_WE: 'future4',
    FORM_PLURAL: 'future5',
    FORM_THEY: 'future6'
}

CONDITIONAL_TENSE_FORMS = {
    FORM_MASC: 'conditional_singM',
    FORM_FEM: 'conditional_singF',
    FORM_NEUTER: 'conditional_singN',
    FORM_PLURAL: 'conditional_plur'
}

IMPERATIVE_TENSE_FORMS = {
    FORM_YOU: 'imperative2',
    FORM_PLURAL: 'imperative5'
}

ASPECT_POSTFIX = {
    ASPECT_IMPERFECT: 'нсв',
    ASPECT_PERFECT: 'св'
}

TENSE_POSTFIX = {
    TENSE_PRESENT: 'pres',
    TENSE_CONDITIONAL: 'cond',
    TENSE_FUTURE: 'future',
    TENSE_PAST: 'past',
    TENSE_IMPERATIVE:'imp'
}

FORM_POSTFIX = {
    FORM_I: 'я',
    FORM_HE: 'он/она',
    FORM_YOU: 'ты',
    FORM_WE: 'мы',
    FORM_PLURAL: 'вы',
    FORM_THEY: 'они',
    FORM_FEM: 'она',
    FORM_MASC: 'он',
    FORM_NEUTER: 'оно'
}


#-----------------------------------------------------------------------------
# Functions
#-----------------------------------------------------------------------------

def make_fs_safe_name(filename):
    return "".join([c if c.isalpha() or c.isdigit() else '_' for c in filename]).strip()

def find_entry_by_id(soup, tense):
    elem = soup.find(id=tense)
    if elem is not None:
        en = elem.attrs['data-translated']
        if not en:
            en = elem.attrs['data=stressed']
        ru = elem.attrs['data-default']
        return Entry(en, ru)
    return None

def get_tense_entries(soup, forms):
    result = {}
    for key, val in forms.items():
        entry = find_entry_by_id(soup, val + '_no_accent')
        if not entry:
            entry = find_entry_by_id(soup, val)
        if entry:
            result[key] = entry
    return result

#-----------------------------------------------------------------------------
# Class
#-----------------------------------------------------------------------------

class Entry(object):
    def __init__(self, en, ru):
        self.ru = ru
        self.en = en

class Verb(object):
    def __init__(self):
        self.aspect = ASPECT_UNKNOWN
        self.meanings = []
        self.present = {}
        self.future = {}
        self.past = {}
        self.conditional = {}
        self.imperative = {}


    def _write_tense(self, stream, tense, entries):
        for key, val in entries.items():
            ru = ''
            if key in FORM_POSTFIX:
                ru += FORM_POSTFIX[key] + ' '
            ru += val.ru
            en = '%s (%s, %s)' % (val.en, ASPECT_POSTFIX[self.aspect], TENSE_POSTFIX[tense])

            line = '%s, %s\n' % (en, ru)
            stream.write(line)
            sys.stdout.write(line)

    def get_filename(self):
        return make_fs_safe_name('to ' + '/'.join(self.meanings)) + '.txt'

    def write(self, stream):
        self._write_tense(stream, TENSE_PRESENT, self.present),
        self._write_tense(stream, TENSE_FUTURE, self.future)
        self._write_tense(stream, TENSE_PAST, self.past)
        self._write_tense(stream, TENSE_CONDITIONAL, self.conditional)
        self._write_tense(stream, TENSE_IMPERATIVE, self.imperative)


class Cooljigate(object):
    """ Cooljigate """
    CoolUrl = "http://cooljugator.com/ru"

    def __init__(self, args):
        """ Constructor """
        self.verb = args.verb

    def _get_document(self):
        url = "%s/%s" % (Cooljigate.CoolUrl, quote(self.verb))

        # check if we have cached this file
        cache_name = os.path.join(tempfile.gettempdir(), make_fs_safe_name(url))
        if os.path.exists(cache_name):
            return open(cache_name, mode='r', encoding='utf-8').read()

        # update cache
        response = urlopen(url,).read().decode('utf-8')
        open(cache_name, mode='w', encoding='utf-8').write(response)
        return response

    def run(self):
        text = self._get_document()
        soup = BeautifulSoup(text, "lxml")
        result = Verb()

        # aspect
        imp = soup.find_all(attrs={"data-tooltip" : IMPERFECTIVE_TEXT})
        if len(imp):
            result.aspect = ASPECT_IMPERFECT
        else:
            perf  = soup.find_all(attrs={"data-tooltip" : PERFECTIVE_TEXT})
            if len(perf):
                result.aspect = ASPECT_PERFECT
            else:
                print('No aspect found')

        # meaning
        usage = soup.find(attrs={'id': 'usage-info'})
        if usage.contents[0].startswith(MEANING_STR):
            result.meanings = [ meaning.strip() for meaning in usage.contents[0][len(MEANING_STR):].split(',') ]
        else:
            print('No meanings found')

        # past tense
        result.past = get_tense_entries(soup, PAST_TENSE_FORMS)
        result.present = get_tense_entries(soup, PRESENT_TENSE_FORMS)
        result.future = get_tense_entries(soup, FUTURE_TENSE_FORMS)
        result.conditional = get_tense_entries(soup, CONDITIONAL_TENSE_FORMS)
        result.imperative = get_tense_entries(soup, IMPERATIVE_TENSE_FORMS)

        output = open(result.get_filename(), mode='w', encoding='utf-8')
        result.write(output)
        output.close()
        return 1




#-----------------------------------------------------------------------------
# Main
#-----------------------------------------------------------------------------

def main():
    """ Main script entry point """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('verb', metavar='V', type=str, help='Verb to conjugate')
    return Cooljigate(parser.parse_args()).run()

if __name__ == "__main__":
    main()
