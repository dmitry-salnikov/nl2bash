#!/usr/bin/env python
# -*- coding: UTF-8 -*-

"""
A natural language command tokenizer.
"""

import re

from . import constants, ner
from .spellcheck import spell_check as spc

# from nltk.stem.wordnet import WordNetLemmatizer
# lmtzr = WordNetLemmatizer()
from nltk.stem import SnowballStemmer
stemmer = SnowballStemmer("english")

# Regular expressions used to tokenize an English sentence.
_WORD_SPLIT = re.compile("^\s+|\s*,\s*|\s+$|^[\(|\[|\{|\<]|[\)|\]|\}|\>]$")
_WORD_SPLIT_RESPECT_QUOTES = re.compile('(?:[^\s,"]|"(?:\\.|[^"])*")+')


def clean_sentence(sentence):
    """
    Fix punctuation errors and extract main content of a sentence.
    """

    # remove content in parentheses
    _PAREN_REMOVE = re.compile('\([^)]*\)')
    sentence = re.sub(_PAREN_REMOVE, '', sentence)

    try:
        sentence = sentence.replace("“", '"')
        sentence = sentence.replace("”", '"')
        sentence = sentence.replace('‘', '\'')
        sentence = sentence.replace('’', '\'')
    except UnicodeDecodeError:
        sentence = sentence.replace("“".decode('utf-8'), '"')
        sentence = sentence.replace("”".decode('utf-8'), '"')
        sentence = sentence.replace('‘'.decode('utf-8'), '\'')
        sentence = sentence.replace('’'.decode('utf-8'), '\'')
    sentence = sentence.replace('`\'', '"') \
            .replace('``', '"') \
            .replace("''", '"') \
            .replace(' \'', ' "') \
            .replace('\' ', '" ') \
            .replace('`', '"') \
            .replace('(', ' ( ') \
            .replace(')', ' ) ')
            # .replace('[', '[ ') \
            # .replace('{', '{ ') \
            # .replace(']', ' ]') \
            # .replace('}', ' }') \
            # .replace('<', '< ') \
            # .replace('>', ' >')
    sentence = re.sub('^\'', '"', sentence)
    sentence = re.sub('\'$', '"', sentence)

    sentence = re.sub('(,\s+)|(,$)', ' ', sentence)
    sentence = re.sub('(;\s+)|(;$)', ' ', sentence)
    sentence = re.sub('(:\s+)|(:$)', ' ', sentence)
    sentence = re.sub('(\.\s+)|(\.$)', ' ', sentence)

    # convert abbreviation writings and negations
    sentence = re.sub('\'s', ' \'s', sentence)
    sentence = re.sub('\'re', ' \'re', sentence)
    sentence = re.sub('\'ve', ' \'ve', sentence)
    sentence = re.sub('\'d', ' \'d', sentence)
    sentence = re.sub('\'t', ' \'t', sentence)

    sentence = re.sub("^[T|t]o ", '', sentence)
    sentence = re.sub('\$\{HOME\}', '\$HOME', sentence)
    sentence = re.sub('"?normal\/regular"?', 'regular', sentence)
    sentence = re.sub('"?regular\/normal"?', 'regular', sentence)
    sentence = re.sub('"?files\/directories"?', 'files and directories', sentence)

    return sentence


def basic_tokenizer(sentence, lower_case=True, lemmatization=True,
                    remove_stop_words=True, correct_spell=True):
    """Very basic tokenizer: used for English tokenization."""
    sentence = clean_sentence(sentence)
    words = re.findall(_WORD_SPLIT_RESPECT_QUOTES, sentence)

    normalized_words = []
    for i in xrange(len(words)):
        word = words[i].strip()
        # remove unnecessary upper cases
        if lower_case:
            if i == 0 and word[0].isupper() and len(word) > 1 and word[1:].islower():
                word = word.lower()

        # spelling correction
        if correct_spell:
            if word.isalpha() and word.islower() and len(word) > 2:
                old_w = word
                word = spc.correction(word)
                if word != old_w:
                    print("spell correction: {} -> {}".format(old_w, word))

        # remove English stopwords
        if remove_stop_words:
            if word in constants.ENGLISH_STOPWORDS:
                continue

        # covert number words into numbers
        if word in constants.word2num:
            word = str(constants.word2num[word])

        # lemmatization
        if lemmatization:
            try:
                word = stemmer.stem(word.decode('utf-8'))
            except AttributeError:
                word = stemmer.stem(word)

        # remove empty words
        if not word.strip():
            continue

        normalized_words.append(word)

    return normalized_words, entities


def ner_tokenizer(sentence):
    words = basic_tokenizer(sentence)
    return ner.annotate(words)


# --- Utility functions --- #

def is_stopword(w):
    return w in constants.ENGLISH_STOPWORDS


def test_nl_tokenizer():
    while True:
        nl = raw_input("> ")
        tokens = basic_tokenizer(nl)
        print(tokens)


if __name__ == '__main__':
    test_nl_tokenizer()