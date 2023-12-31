#!/usr/bin/env python
# SPDX-License-Identifier: GPL-3.0-or-later

# pid2bib (Paper Id to BibTeX), a command line tool to fetch a scientific
# paper (article) bibliographic entry and store it in a file, in the
# in the current path.
# Copyright (C) 2023 - Andrés Becerra <andres.becerra@gmail.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License, version 2, as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

# Usage: pid2bib pmid
#        pid2bib doi
#
# Examples:
# pid2bib 31726262
# pid2bib 10.1021/acs.jced.5b00684
#
# pmid: PubMed identifier, see:
# https://en.wikipedia.org/wiki/PubMed#PubMed_identifier
#
# DOI: Digital Object Identifier, see:
# https://www.doi.org/the-identifier/what-is-a-doi/
#
# Author: Andrés Becerra <andres.becerra@gmail.com>


__title__ = 'pid2bib'
__version__ = '0.1'
__author__ = 'Andrés Becerra'
__email__ = 'andres.becerra@gmail.com'
__website__ = 'https://github.com/abecerra/pid2bib'

from io import StringIO
import re
import sys
from urllib import request
from urllib.error import URLError
from urllib.request import Request
from xml.etree.ElementTree import fromstring


class Author:
    """Represents an Author."""

    def __init__(self):
        self.lastName: str = ''
        self.foreName: str = ''
        self.initials: str = ''
        self.institution: str = ''


class Reference:
    """Represents a bibliographic entry."""

    def __init__(self, pmid):
        self.pmid: str = pmid
        self.title: str = ''
        self.authors: list[Author] = []
        self.journal: str = ''
        self.volume: str = ''
        self.issue: str = ''
        self.startPage: str = ''
        self.endPage: str = ''
        self.doi: str = ''
        self.pbyear: str = ''
        self.pbmonth: str = ''
        self.issn: str = ''
        self.journalAb: str = ''
        self.copyright: str = ''
        self.article_url: str = ''
        self.abstract: str = ''


def fetchXML(pmid: str) -> str:
    """Fetch the pubmed XML bibliography for an article.

    Keyword arguments:
    pmid -- the pubmed identifier for the article
    returns the xml bibliography for the pmid
    raises an exception if the eutils service fails
    """
    eutils = 'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi'
    options = '?db=pubmed&retmode=xml&id='
    url = f'{eutils}{options}{pmid}'
    try:
        with request.urlopen(url) as resp:
            if resp.code == 200:
                return resp.read().decode("utf-8")
    except URLError as error:
        print('Error downloading XML entry from pubmed\n', error.reason)


def parseXML(pmid, xml: str) -> Reference:
    """Extracts information from string with pubmed XML.

    Keyword arguments:
    xml -- pubmed bibliographic entry in XML format
    returns Reference information retrieved from the XML string
    raises exception if xml content has an unexpected format
    """
    ref = Reference(pmid)
    pubmedArticleSet = fromstring(xml)
    pubmedArticles = pubmedArticleSet.findall('PubmedArticle')
    if ((pubmedArticles is None) or (len(pubmedArticles) == 0)):
        raise Exception('Empty result for the given pubmed id')
    pubmedArticle = pubmedArticles[0]

    for articleId in (pubmedArticle.find('PubmedData').find('ArticleIdList')):
        if articleId.attrib['IdType'] == 'doi':
            ref.doi = articleId.text
    if ref.doi == '':
        ref.article_url = f'https://pubmed.ncbi.nlm.nih.gov/{pmid}/'
    else:
        ref.article_url = f'https://doi.org/{ref.doi}'

    article = pubmedArticle.find('MedlineCitation').find('Article')
    currElem = article.find('ArticleTitle')
    ref.title = currElem.text if (currElem is not None) else ''

    absElem = article.find('Abstract')
    if (absElem is not None):
        currElem = absElem.find('AbstractText')
        abstractText = currElem.text if (currElem is not None) else ''
        if abstractText is not None:
            ref.abstract = abstractText
        currElem = absElem.find('CopyrightInformation')
        ref.copyright = currElem.text if (currElem is not None) else ''

    journalElement = article.find('Journal')
    if journalElement is not None:
        currElem = journalElement.find('Title')
        ref.journal = currElem.text if (currElem is not None) else ''
        currElem = journalElement.find('ISSN')
        ref.issn = currElem.text if (currElem is not None) else ''
        currElem = journalElement.find('ISOAbbreviation')
        ref.journalAb = currElem.text if (currElem is not None) else ''
        jissueElem = journalElement.find('JournalIssue')
        currElem = jissueElem.find('Volume')
        ref.volume = currElem.text if (currElem is not None) else ''
        currElem = jissueElem.find('Issue')
        ref.issue = currElem.text if (currElem is not None) else ''
        dateElem = jissueElem.find('PubDate')
        if dateElem is not None:
            currElem = dateElem.find('Year')
            ref.pbyear = currElem.text if (currElem is not None) else ''
            currElem = dateElem.find('Month')
            ref.pbmonth = currElem.text if (currElem is not None) else ''

    pagElem = article.find('Pagination')
    if pagElem is not None:
        currElem = pagElem.find('StartPage')
        ref.startPage = currElem.text if (currElem is not None) else ''
        currElem = pagElem.find('EndPage')
        ref.endPage = currElem.text if (currElem is not None) else ''

    for authorElem in article.find('AuthorList'):
        author = Author()
        currElem = authorElem.find('LastName')
        author.lastName = currElem.text if (currElem is not None) else ''
        currElem = authorElem.find('ForeName')
        author.foreName = currElem.text if (currElem is not None) else ''
        currElem = authorElem.find('Initials')
        author.initials = currElem.text if (currElem is not None) else ''
        affiElem = authorElem.find('AffiliationInfo')
        if affiElem is not None:
            currElem = affiElem.find('Affiliation')
            author.institution = '' if (currElem is None) else currElem.text
        else:
            author.institution = ''
        ref.authors.append(author)

    return ref


def appendFormattedField(stringBuffer: StringIO, name: str,
                         value: str) -> None:
    """Appends a bibtex fragment for one field.

    Keyword arguments:
    stringBuffer -- an existing StringIO to append the text
    name         -- the name of the bibtex field
    value        -- the value for the bibtex field
    Side Effect: appends text to stringBuffer
    """
    stringBuffer.write(f'   {name} = "')
    stringBuffer.write(value)
    stringBuffer.write('",\n')


def formatAuthor(author: Author) -> str:
    """Appends a bibtex fragment for one author.

    Keyword arguments:
    author -- the author
    returns a string representing the author
    """
    return author.lastName + ', ' + author.initials + '.'


def sanitizeFileName(text: str) -> str:
    """Removes dot at the end of the text and other characters

    Keyword arguments:
    text -- the text string e.g 'something.'
    returns removes characters from the string and final dot (if exists)
    """
    result = text.translate({
            ord('{'): None,
            ord('}'): None,
            ord('['): None,
            ord(']'): None,
            ord('"'): None,
            ord('/'): ' ',
            ord('?'): None})
    if result[-1] == '.':
        return result[:-1]
    else:
        return result


def monthToNumber(month: str) -> str:
    """Converts a month to its number, e.g Jan -> 1, Dec -> 12.

    Keyword arguments:
    month -- the month abbreviation in three letters
    returns a string with the number for the month
    """
    month_dict = dict(Jan=1, Feb=2, Mar=3, Apr=4, May=5, Jun=6, Jul=7,
                      Aug=8, Sep=9, Oct=10, Nov=11, Dec=12)
    return str(month_dict.get(month, ''))


def sanitizeBibtexField(text: str) -> str:
    '''Transforms problematic unicode characters to their LaTeX code

    Keyword arguments:
    text -- a text string
    returns a modified string with problematic characters replaced
    Adapted from https://gitlab.com/crossref/rest_api/-/blob/main/src/cayenne/latex.clj
    '''
    uni2tex = {
        "\u0023": "{\\#}",  # NUMBER SIGN
        "\u0024": "{\\textdollar}",  # DOLLAR SIGN
        "\u0025": "{\\%}",  # PERCENT SIGN
        "\u0026": "{\\&}",  # AMPERSAND
        "\u0027": "{\\textquotesingle}",  # APOSTROPHE
        "\u002A": "{\\ast}",  # ASTERISK
        "\u002B": "$\\mathplus$",  # PLUS SIGN
        "\u002D": "-",  # HYPHEN-MINUS
        "\u003B": "$\\mathsemicolon$",  # SEMICOLON
        "\u003C": "$\\less$",  # LESS-THAN SIGN
        "\u003E": "$\\greater$",  # GREATER-THAN SIGN
        "\u005C": "{\\textbackslash}",  # REVERSE SOLIDUS
        "\u005E": "{\\^{}}",  # CIRCUMFLEX ACCENT
        "\u005F": "{\\_}",  # LOW LINE
        "\u0060": "{\\textasciigrave}",  # GRAVE ACCENT
        "\u007B": "$\\lbrace$",  # LEFT CURLY BRACKET
        "\u007C": "$\\vert$",  # VERTICAL LINE
        "\u007D": "$\\rbrace$",  # RIGHT CURLY BRACKET
        "\u007E": "{\\textasciitilde}",  # TILDE
        "\u00A0": "~",  # NO-BREAK SPACE
        "\u00A1": "{\\textexclamdown}",  # INVERTED EXCLAMATION MARK
        "\u00A2": "{\\textcent}",  # CENT SIGN
        "\u00A3": "{\\textsterling}",  # POUND SIGN
        "\u00A4": "{\\textcurrency}",  # CURRENCY SIGN
        "\u00A5": "{\\textyen}",  # YEN SIGN
        "\u00A6": "{\\textbrokenbar}",  # BROKEN BAR
        "\u00A7": "{\\textsection}",  # SECTION SIGN
        "\u00A8": "{\\textasciidieresis}",  # DIAERESIS
        "\u00A9": "{\\textcopyright}",  # COPYRIGHT SIGN
        "\u00AA": "{\\textordfeminine}",  # FEMININE ORDINAL INDICATOR
        "\u00AB": "{\\guillemotleft}",  # LEFT-POINTING DOUBLE ANGLE QUOTATION MARK
        "\u00AC": "$\\neg$",  # NOT SIGN
        "\u00AD": "{\\-}",  # SOFT HYPHEN
        "\u00AE": "{\\textregistered}",  # REGISTERED SIGN
        "\u00AF": "{\\textasciimacron}",  # MACRON
        "\u00B0": "{\\textdegree}",  # DEGREE SIGN
        "\u00B1": "$\\pm$",  # PLUS-MINUS SIGN
        "\u00B2": "{^2}",  # SUPERSCRIPT TWO
        "\u00B3": "{^3}",  # SUPERSCRIPT THREE
        "\u00B4": "{\\textasciiacute}",  # ACUTE ACCENT
        "\u00B5": "$\\mathrm{\\mu}$",  # MICRO SIGN
        "\u00B6": "{\\textparagraph}",  # PILCROW SIGN
        "\u00B7": "$\\cdotp$",  # MIDDLE DOT
        "\u00B8": "{\\c{}}",  # CEDILLA
        "\u00B9": "{^1}",  # SUPERSCRIPT ONE
        "\u00BA": "{\\textordmasculine}",  # MASCULINE ORDINAL INDICATOR
        "\u00BB": "{\\guillemotright}",  # RIGHT-POINTING DOUBLE ANGLE QUOTATION MARK
        "\u00BC": "{\\textonequarter}",  # VULGAR FRACTION ONE QUARTER
        "\u00BD": "{\\textonehalf}",  # VULGAR FRACTION ONE HALF
        "\u00BE": "{\\textthreequarters}",  # VULGAR FRACTION THREE QUARTERS
        "\u00BF": "{\\textquestiondown}",  # INVERTED QUESTION MARK
        "\u00C0": "{\\`{A}}",  # LATIN CAPITAL LETTER A WITH GRAVE
        "\u00C1": "{\\'{A}}",  # LATIN CAPITAL LETTER A WITH ACUTE
        "\u00C2": "{\\^{A}}",  # LATIN CAPITAL LETTER A WITH CIRCUMFLEX
        "\u00C3": "{\\~{A}}",  # LATIN CAPITAL LETTER A WITH TILDE
        "\u00C5": "{\\AA}",  # LATIN CAPITAL LETTER A WITH RING ABOVE
        "\u00C6": "{\\AE}",  # LATIN CAPITAL LETTER AE
        "\u00C7": "{\\c{C}}",  # LATIN CAPITAL LETTER C WITH CEDILLA
        "\u00C8": "{\\`{E}}",  # LATIN CAPITAL LETTER E WITH GRAVE
        "\u00C9": "{\\'{E}}",  # LATIN CAPITAL LETTER E WITH ACUTE
        "\u00CA": "{\\^{E}}",  # LATIN CAPITAL LETTER E WITH CIRCUMFLEX
        "\u00CC": "{\\`{I}}",  # LATIN CAPITAL LETTER I WITH GRAVE
        "\u00CD": "{\\'{I}}",  # LATIN CAPITAL LETTER I WITH ACUTE
        "\u00CE": "{\\^{I}}",  # LATIN CAPITAL LETTER I WITH CIRCUMFLEX
        "\u00D0": "{\\DH}",  # LATIN CAPITAL LETTER ETH
        "\u00D1": "{\\~{N}}",  # LATIN CAPITAL LETTER N WITH TILDE
        "\u00D2": "{\\`{O}}",  # LATIN CAPITAL LETTER O WITH GRAVE
        "\u00D3": "{\\'{O}}",  # LATIN CAPITAL LETTER O WITH ACUTE
        "\u00D4": "{\\^{O}}",  # LATIN CAPITAL LETTER O WITH CIRCUMFLEX
        "\u00D5": "{\\~{O}}",  # LATIN CAPITAL LETTER O WITH TILDE
        "\u00D7": "{\\texttimes}",  # MULTIPLICATION SIGN
        "\u00D8": "{\\O}",  # LATIN CAPITAL LETTER O WITH STROKE
        "\u00D9": "{\\`{U}}",  # LATIN CAPITAL LETTER U WITH GRAVE
        "\u00DA": "{\\'{U}}",  # LATIN CAPITAL LETTER U WITH ACUTE
        "\u00DB": "{\\^{U}}",  # LATIN CAPITAL LETTER U WITH CIRCUMFLEX
        "\u00DD": "{\\'{Y}}",  # LATIN CAPITAL LETTER Y WITH ACUTE
        "\u00DE": "{\\TH}",  # LATIN CAPITAL LETTER THORN
        "\u00DF": "{\\ss}",  # LATIN SMALL LETTER SHARP S
        "\u00E0": "{\\`{a}}",  # LATIN SMALL LETTER A WITH GRAVE
        "\u00E1": "{\\'{a}}",  # LATIN SMALL LETTER A WITH ACUTE
        "\u00E2": "{\\^{a}}",  # LATIN SMALL LETTER A WITH CIRCUMFLEX
        "\u00E3": "{\\~{a}}",  # LATIN SMALL LETTER A WITH TILDE
        "\u00E5": "{\\aa}",  # LATIN SMALL LETTER A WITH RING ABOVE
        "\u00E6": "{\\ae}",  # LATIN SMALL LETTER AE
        "\u00E7": "{\\c{c}}",  # LATIN SMALL LETTER C WITH CEDILLA
        "\u00E8": "{\\`{e}}",  # LATIN SMALL LETTER E WITH GRAVE
        "\u00E9": "{\\'{e}}",  # LATIN SMALL LETTER E WITH ACUTE
        "\u00EA": "{\\^{e}}",  # LATIN SMALL LETTER E WITH CIRCUMFLEX
        "\u00EC": "{\\`{\\i}}",  # LATIN SMALL LETTER I WITH GRAVE
        "\u00ED": "{\\'{\\i}}",  # LATIN SMALL LETTER I WITH ACUTE
        "\u00EE": "{\\^{\\i}}",  # LATIN SMALL LETTER I WITH CIRCUMFLEX
        "\u00F0": "{\\dh}",  # LATIN SMALL LETTER ETH
        "\u00F1": "{\\~{n}}",  # LATIN SMALL LETTER N WITH TILDE
        "\u00F2": "{\\`{o}}",  # LATIN SMALL LETTER O WITH GRAVE
        "\u00F3": "{\\'{o}}",  # LATIN SMALL LETTER O WITH ACUTE
        "\u00F4": "{\\^{o}}",  # LATIN SMALL LETTER O WITH CIRCUMFLEX
        "\u00F5": "{\\~{o}}",  # LATIN SMALL LETTER O WITH TILDE
        "\u00F7": "$\\div$",  # DIVISION SIGN
        "\u00F8": "{\\o}",  # LATIN SMALL LETTER O WITH STROKE
        "\u00F9": "{\\`{u}}",  # LATIN SMALL LETTER U WITH GRAVE
        "\u00FA": "{\\'{u}}",  # LATIN SMALL LETTER U WITH ACUTE
        "\u00FB": "{\\^{u}}",  # LATIN SMALL LETTER U WITH CIRCUMFLEX
        "\u00FD": "{\\'{y}}",  # LATIN SMALL LETTER Y WITH ACUTE
        "\u00FE": "{\\th}",  # LATIN SMALL LETTER THORN
        "\u0100": "{\\={A}}",  # LATIN CAPITAL LETTER A WITH MACRON
        "\u0101": "{\\={a}}",  # LATIN SMALL LETTER A WITH MACRON
        "\u0102": "{\\u{A}}",  # LATIN CAPITAL LETTER A WITH BREVE
        "\u0103": "{\\u{a}}",  # LATIN SMALL LETTER A WITH BREVE
        "\u0104": "{\\k{A}}",  # LATIN CAPITAL LETTER A WITH OGONEK
        "\u0105": "{\\k{a}}",  # LATIN SMALL LETTER A WITH OGONEK
        "\u0106": "{\\'{C}}",  # LATIN CAPITAL LETTER C WITH ACUTE
        "\u0107": "{\\'{c}}",  # LATIN SMALL LETTER C WITH ACUTE
        "\u0108": "{\\^{C}}",  # LATIN CAPITAL LETTER C WITH CIRCUMFLEX
        "\u0109": "{\\^{c}}",  # LATIN SMALL LETTER C WITH CIRCUMFLEX
        "\u010A": "{\\.{C}}",  # LATIN CAPITAL LETTER C WITH DOT ABOVE
        "\u010B": "{\\.{c}}",  # LATIN SMALL LETTER C WITH DOT ABOVE
        "\u010C": "{\\v{C}}",  # LATIN CAPITAL LETTER C WITH CARON
        "\u010D": "{\\v{c}}",  # LATIN SMALL LETTER C WITH CARON
        "\u010E": "{\\v{D}}",  # LATIN CAPITAL LETTER D WITH CARON
        "\u010F": "{\\v{d}}",  # LATIN SMALL LETTER D WITH CARON
        "\u0110": "{\\DJ}",  # LATIN CAPITAL LETTER D WITH STROKE
        "\u0111": "{\\dj}",  # LATIN SMALL LETTER D WITH STROKE
        "\u0112": "{\\={E}}",  # LATIN CAPITAL LETTER E WITH MACRON
        "\u0113": "{\\={e}}",  # LATIN SMALL LETTER E WITH MACRON
        "\u0114": "{\\u{E}}",  # LATIN CAPITAL LETTER E WITH BREVE
        "\u0115": "{\\u{e}}",  # LATIN SMALL LETTER E WITH BREVE
        "\u0116": "{\\.{E}}",  # LATIN CAPITAL LETTER E WITH DOT ABOVE
        "\u0117": "{\\.{e}}",  # LATIN SMALL LETTER E WITH DOT ABOVE
        "\u0118": "{\\k{E}}",  # LATIN CAPITAL LETTER E WITH OGONEK
        "\u0119": "{\\k{e}}",  # LATIN SMALL LETTER E WITH OGONEK
        "\u011A": "{\\v{E}}",  # LATIN CAPITAL LETTER E WITH CARON
        "\u011B": "{\\v{e}}",  # LATIN SMALL LETTER E WITH CARON
        "\u011C": "{\\^{G}}",  # LATIN CAPITAL LETTER G WITH CIRCUMFLEX
        "\u011D": "{\\^{g}}",  # LATIN SMALL LETTER G WITH CIRCUMFLEX
        "\u011E": "{\\u{G}}",  # LATIN CAPITAL LETTER G WITH BREVE
        "\u011F": "{\\u{g}}",  # LATIN SMALL LETTER G WITH BREVE
        "\u0120": "{\\.{G}}",  # LATIN CAPITAL LETTER G WITH DOT ABOVE
        "\u0121": "{\\.{g}}",  # LATIN SMALL LETTER G WITH DOT ABOVE
        "\u0122": "{\\c{G}}",  # LATIN CAPITAL LETTER G WITH CEDILLA
        "\u0123": "{\\c{g}}",  # LATIN SMALL LETTER G WITH CEDILLA
        "\u0124": "{\\^{H}}",  # LATIN CAPITAL LETTER H WITH CIRCUMFLEX
        "\u0125": "{\\^{h}}",  # LATIN SMALL LETTER H WITH CIRCUMFLEX
        "\u0126": "{\\fontencoding{LELA}\\selectfont\\char40}",  # LATIN CAPITAL LETTER H WITH STROKE
        "\u0127": "{\\Elzxh}",  # LATIN SMALL LETTER H WITH STROKE
        "\u0128": "{\\~{I}}",  # LATIN CAPITAL LETTER I WITH TILDE
        "\u0129": "{\\~{\\i}}",  # LATIN SMALL LETTER I WITH TILDE
        "\u012A": "{\\={I}}",  # LATIN CAPITAL LETTER I WITH MACRON
        "\u012B": "{\\={\\i}}",  # LATIN SMALL LETTER I WITH MACRON
        "\u012C": "{\\u{I}}",  # LATIN CAPITAL LETTER I WITH BREVE
        "\u012D": "{\\u{\\i}}",  # LATIN SMALL LETTER I WITH BREVE
        "\u012E": "{\\k{I}}",  # LATIN CAPITAL LETTER I WITH OGONEK
        "\u012F": "{\\k{i}}",  # LATIN SMALL LETTER I WITH OGONEK
        "\u0130": "{\\.{I}}",  # LATIN CAPITAL LETTER I WITH DOT ABOVE
        "\u0131": "{\\i}",  # LATIN SMALL LETTER DOTLESS I
        "\u0132": "IJ",  # LATIN CAPITAL LIGATURE IJ
        "\u0133": "ij",  # LATIN SMALL LIGATURE IJ
        "\u0134": "{\\^{J}}",  # LATIN CAPITAL LETTER J WITH CIRCUMFLEX
        "\u0135": "{\\^{\\j}}",  # LATIN SMALL LETTER J WITH CIRCUMFLEX
        "\u0136": "{\\c{K}}",  # LATIN CAPITAL LETTER K WITH CEDILLA
        "\u0137": "{\\c{k}}",  # LATIN SMALL LETTER K WITH CEDILLA
        "\u0138": "{\\fontencoding{LELA}\\selectfont\\char91}",  # LATIN SMALL LETTER KRA
        "\u0139": "{\\'{L}}",  # LATIN CAPITAL LETTER L WITH ACUTE
        "\u013A": "{\\'{l}}",  # LATIN SMALL LETTER L WITH ACUTE
        "\u013B": "{\\c{L}}",  # LATIN CAPITAL LETTER L WITH CEDILLA
        "\u013C": "{\\c{l}}",  # LATIN SMALL LETTER L WITH CEDILLA
        "\u013D": "{\\v{L}}",  # LATIN CAPITAL LETTER L WITH CARON
        "\u013E": "{\\v{l}}",  # LATIN SMALL LETTER L WITH CARON
        "\u013F": "{\\fontencoding{LELA}\\selectfont\\char201}",  # LATIN CAPITAL LETTER L WITH MIDDLE DOT
        "\u0140": "{\\fontencoding{LELA}\\selectfont\\char202}",  # LATIN SMALL LETTER L WITH MIDDLE DOT
        "\u0141": "{\\L}",  # LATIN CAPITAL LETTER L WITH STROKE
        "\u0142": "{\\l}",  # LATIN SMALL LETTER L WITH STROKE
        "\u0143": "{\\'{N}}",  # LATIN CAPITAL LETTER N WITH ACUTE
        "\u0144": "{\\'{n}}",  # LATIN SMALL LETTER N WITH ACUTE
        "\u0145": "{\\c{N}}",  # LATIN CAPITAL LETTER N WITH CEDILLA
        "\u0146": "{\\c{n}}",  # LATIN SMALL LETTER N WITH CEDILLA
        "\u0147": "{\\v{N}}",  # LATIN CAPITAL LETTER N WITH CARON
        "\u0148": "{\\v{n}}",  # LATIN SMALL LETTER N WITH CARON
        "\u0149": "'n",  # LATIN SMALL LETTER N PRECEDED BY APOSTROPHE
        "\u014A": "{\\NG}",  # LATIN CAPITAL LETTER ENG
        "\u014B": "{\\ng}",  # LATIN SMALL LETTER ENG
        "\u014C": "{\\={O}}",  # LATIN CAPITAL LETTER O WITH MACRON
        "\u014D": "{\\={o}}",  # LATIN SMALL LETTER O WITH MACRON
        "\u014E": "{\\u{O}}",  # LATIN CAPITAL LETTER O WITH BREVE
        "\u014F": "{\\u{o}}",  # LATIN SMALL LETTER O WITH BREVE
        "\u0150": "{\\H{O}}",  # LATIN CAPITAL LETTER O WITH DOUBLE ACUTE
        "\u0151": "{\\H{o}}",  # LATIN SMALL LETTER O WITH DOUBLE ACUTE
        "\u0152": "{\\OE}",  # LATIN CAPITAL LIGATURE OE
        "\u0153": "{\\oe}",  # LATIN SMALL LIGATURE OE
        "\u0154": "{\\'{R}}",  # LATIN CAPITAL LETTER R WITH ACUTE
        "\u0155": "{\\'{r}}",  # LATIN SMALL LETTER R WITH ACUTE
        "\u0156": "{\\c{R}}",  # LATIN CAPITAL LETTER R WITH CEDILLA
        "\u0157": "{\\c{r}}",  # LATIN SMALL LETTER R WITH CEDILLA
        "\u0158": "{\\v{R}}",  # LATIN CAPITAL LETTER R WITH CARON
        "\u0159": "{\\v{r}}",  # LATIN SMALL LETTER R WITH CARON
        "\u015A": "{\\'{S}}",  # LATIN CAPITAL LETTER S WITH ACUTE
        "\u015B": "{\\'{s}}",  # LATIN SMALL LETTER S WITH ACUTE
        "\u015C": "{\\^{S}}",  # LATIN CAPITAL LETTER S WITH CIRCUMFLEX
        "\u015D": "{\\^{s}}",  # LATIN SMALL LETTER S WITH CIRCUMFLEX
        "\u015E": "{\\c{S}}",  # LATIN CAPITAL LETTER S WITH CEDILLA
        "\u015F": "{\\c{s}}",  # LATIN SMALL LETTER S WITH CEDILLA
        "\u0160": "{\\v{S}}",  # LATIN CAPITAL LETTER S WITH CARON
        "\u0161": "{\\v{s}}",  # LATIN SMALL LETTER S WITH CARON
        "\u0162": "{\\c{T}}",  # LATIN CAPITAL LETTER T WITH CEDILLA
        "\u0163": "{\\c{t}}",  # LATIN SMALL LETTER T WITH CEDILLA
        "\u0164": "{\\v{T}}",  # LATIN CAPITAL LETTER T WITH CARON
        "\u0165": "{\\v{t}}",  # LATIN SMALL LETTER T WITH CARON
        "\u0166": "{\\fontencoding{LELA}\\selectfont\\char47}",  # LATIN CAPITAL LETTER T WITH STROKE
        "\u0167": "{\\fontencoding{LELA}\\selectfont\\char63}",  # LATIN SMALL LETTER T WITH STROKE
        "\u0168": "{\\~{U}}",  # LATIN CAPITAL LETTER U WITH TILDE
        "\u0169": "{\\~{u}}",  # LATIN SMALL LETTER U WITH TILDE
        "\u016A": "{\\={U}}",  # LATIN CAPITAL LETTER U WITH MACRON
        "\u016B": "{\\={u}}",  # LATIN SMALL LETTER U WITH MACRON
        "\u016C": "{\\u{U}}",  # LATIN CAPITAL LETTER U WITH BREVE
        "\u016D": "{\\u{u}}",  # LATIN SMALL LETTER U WITH BREVE
        "\u016E": "{\\r{U}}",  # LATIN CAPITAL LETTER U WITH RING ABOVE
        "\u016F": "{\\r{u}}",  # LATIN SMALL LETTER U WITH RING ABOVE
        "\u0170": "{\\H{U}}",  # LATIN CAPITAL LETTER U WITH DOUBLE ACUTE
        "\u0171": "{\\H{u}}",  # LATIN SMALL LETTER U WITH DOUBLE ACUTE
        "\u0172": "{\\k{U}}",  # LATIN CAPITAL LETTER U WITH OGONEK
        "\u0173": "{\\k{u}}",  # LATIN SMALL LETTER U WITH OGONEK
        "\u0174": "{\\^{W}}",  # LATIN CAPITAL LETTER W WITH CIRCUMFLEX
        "\u0175": "{\\^{w}}",  # LATIN SMALL LETTER W WITH CIRCUMFLEX
        "\u0176": "{\\^{Y}}",  # LATIN CAPITAL LETTER Y WITH CIRCUMFLEX
        "\u0177": "{\\^{y}}",  # LATIN SMALL LETTER Y WITH CIRCUMFLEX
        "\u0179": "{\\'{Z}}",  # LATIN CAPITAL LETTER Z WITH ACUTE
        "\u017A": "{\\'{z}}",  # LATIN SMALL LETTER Z WITH ACUTE
        "\u017B": "{\\.{Z}}",  # LATIN CAPITAL LETTER Z WITH DOT ABOVE
        "\u017C": "{\\.{z}}",  # LATIN SMALL LETTER Z WITH DOT ABOVE
        "\u017D": "{\\v{Z}}",  # LATIN CAPITAL LETTER Z WITH CARON
        "\u017E": "{\\v{z}}",  # LATIN SMALL LETTER Z WITH CARON
        "\u0192": "f",  # LATIN SMALL LETTER F WITH HOOK
        "\u0195": "{\\texthvlig}",  # LATIN SMALL LETTER HV
        "\u019E": "{\\textnrleg}",  # LATIN SMALL LETTER N WITH LONG RIGHT LEG
        "\u01AA": "{\\eth}",  # LATIN LETTER REVERSED ESH LOOP
        "\u01BA": "{\\fontencoding{LELA}\\selectfont\\char195}",  # LATIN SMALL LETTER EZH WITH TAIL
        "\u01C2": "{\\textdoublepipe}",  # LATIN LETTER ALVEOLAR CLICK
        "\u01F5": "{\\'{g}}",  # LATIN SMALL LETTER G WITH ACUTE
        "\u0250": "{\\Elztrna}",  # LATIN SMALL LETTER TURNED A
        "\u0252": "{\\Elztrnsa}",  # LATIN SMALL LETTER TURNED ALPHA
        "\u0254": "{\\Elzopeno}",  # LATIN SMALL LETTER OPEN O
        "\u0256": "{\\Elzrtld}",  # LATIN SMALL LETTER D WITH TAIL
        "\u0258": "{\\fontencoding{LEIP}\\selectfont\\char61}",  # LATIN SMALL LETTER REVERSED E
        "\u0259": "{\\Elzschwa}",  # LATIN SMALL LETTER SCHWA
        "\u025B": "{\\varepsilon}",  # LATIN SMALL LETTER OPEN E
        "\u0261": "g",  # LATIN SMALL LETTER SCRIPT G
        "\u0263": "{\\Elzpgamma}",  # LATIN SMALL LETTER GAMMA
        "\u0264": "{\\Elzpbgam}",  # LATIN SMALL LETTER RAMS HORN
        "\u0265": "{\\Elztrnh}",  # LATIN SMALL LETTER TURNED H
        "\u026C": "{\\Elzbtdl}",  # LATIN SMALL LETTER L WITH BELT
        "\u026D": "{\\Elzrtll}",  # LATIN SMALL LETTER L WITH RETROFLEX HOOK
        "\u026F": "{\\Elztrnm}",  # LATIN SMALL LETTER TURNED M
        "\u0270": "{\\Elztrnmlr}",  # LATIN SMALL LETTER TURNED M WITH LONG LEG
        "\u0271": "{\\Elzltlmr}",  # LATIN SMALL LETTER M WITH HOOK
        "\u0272": "{\\Elzltln}",  # LATIN SMALL LETTER N WITH LEFT HOOK
        "\u0273": "{\\Elzrtln}",  # LATIN SMALL LETTER N WITH RETROFLEX HOOK
        "\u0277": "{\\Elzclomeg}",  # LATIN SMALL LETTER CLOSED OMEGA
        "\u0278": "{\\textphi}",  # LATIN SMALL LETTER PHI
        "\u0279": "{\\Elztrnr}",  # LATIN SMALL LETTER TURNED R
        "\u027A": "{\\Elztrnrl}",  # LATIN SMALL LETTER TURNED R WITH LONG LEG
        "\u027B": "{\\Elzrttrnr}",  # LATIN SMALL LETTER TURNED R WITH HOOK
        "\u027C": "{\\Elzrl}",  # LATIN SMALL LETTER R WITH LONG LEG
        "\u027D": "{\\Elzrtlr}",  # LATIN SMALL LETTER R WITH TAIL
        "\u027E": "{\\Elzfhr}",  # LATIN SMALL LETTER R WITH FISHHOOK
        "\u027F": "{\\fontencoding{LEIP}\\selectfont\\char202}",  # LATIN SMALL LETTER REVERSED R WITH FISHHOOK
        "\u0282": "{\\Elzrtls}",  # LATIN SMALL LETTER S WITH HOOK
        "\u0283": "{\\Elzesh}",  # LATIN SMALL LETTER ESH
        "\u0287": "{\\Elztrnt}",  # LATIN SMALL LETTER TURNED T
        "\u0288": "{\\Elzrtlt}",  # LATIN SMALL LETTER T WITH RETROFLEX HOOK
        "\u028A": "{\\Elzpupsil}",  # LATIN SMALL LETTER UPSILON
        "\u028B": "{\\Elzpscrv}",  # LATIN SMALL LETTER V WITH HOOK
        "\u028C": "{\\Elzinvv}",  # LATIN SMALL LETTER TURNED V
        "\u028D": "{\\Elzinvw}",  # LATIN SMALL LETTER TURNED W
        "\u028E": "{\\Elztrny}",  # LATIN SMALL LETTER TURNED Y
        "\u0290": "{\\Elzrtlz}",  # LATIN SMALL LETTER Z WITH RETROFLEX HOOK
        "\u0292": "{\\Elzyogh}",  # LATIN SMALL LETTER EZH
        "\u0294": "{\\Elzglst}",  # LATIN LETTER GLOTTAL STOP
        "\u0295": "{\\Elzreglst}",  # LATIN LETTER PHARYNGEAL VOICED FRICATIVE
        "\u0296": "{\\Elzinglst}",  # LATIN LETTER INVERTED GLOTTAL STOP
        "\u029E": "{\\textturnk}",  # LATIN SMALL LETTER TURNED K
        "\u02A4": "{\\Elzdyogh}",  # LATIN SMALL LETTER DEZH DIGRAPH
        "\u02A7": "{\\Elztesh}",  # LATIN SMALL LETTER TESH DIGRAPH
        "\u02BC": "'",  # MODIFIER LETTER APOSTROPHE
        "\u02C7": "{\\textasciicaron}",  # CARON
        "\u02C8": "{\\Elzverts}",  # MODIFIER LETTER VERTICAL LINE
        "\u02CC": "{\\Elzverti}",  # MODIFIER LETTER LOW VERTICAL LINE
        "\u02D0": "{\\Elzlmrk}",  # MODIFIER LETTER TRIANGULAR COLON
        "\u02D1": "{\\Elzhlmrk}",  # MODIFIER LETTER HALF TRIANGULAR COLON
        "\u02D2": "{\\Elzsbrhr}",  # MODIFIER LETTER CENTRED RIGHT HALF RING
        "\u02D3": "{\\Elzsblhr}",  # MODIFIER LETTER CENTRED LEFT HALF RING
        "\u02D4": "{\\Elzrais}",  # MODIFIER LETTER UP TACK
        "\u02D5": "{\\Elzlow}",  # MODIFIER LETTER DOWN TACK
        "\u02D8": "{\\textasciibreve}",  # BREVE
        "\u02D9": "{\\textperiodcentered}",  # DOT ABOVE
        "\u02DA": "{\\r{}}",  # RING ABOVE
        "\u02DB": "{\\k{}}",  # OGONEK
        "\u02DC": "{\\texttildelow}",  # SMALL TILDE
        "\u02DD": "{\\H{}}",  # DOUBLE ACUTE ACCENT
        "\u02E5": "{\\tone{55}}",  # MODIFIER LETTER EXTRA-HIGH TONE BAR
        "\u02E6": "{\\tone{44}}",  # MODIFIER LETTER HIGH TONE BAR
        "\u02E7": "{\\tone{33}}",  # MODIFIER LETTER MID TONE BAR
        "\u02E8": "{\\tone{22}}",  # MODIFIER LETTER LOW TONE BAR
        "\u02E9": "{\\tone{11}}",  # MODIFIER LETTER EXTRA-LOW TONE BAR
        "\u0300": "{\\`}",  # COMBINING GRAVE ACCENT
        "\u0301": "{\\'}",  # COMBINING ACUTE ACCENT
        "\u0302": "{\\^}",  # COMBINING CIRCUMFLEX ACCENT
        "\u0303": "{\\~}",  # COMBINING TILDE
        "\u0304": "{\\=}",  # COMBINING MACRON
        "\u0306": "{\\u}",  # COMBINING BREVE
        "\u0307": "{\\.}",  # COMBINING DOT ABOVE
        "\u030A": "{\\r}",  # COMBINING RING ABOVE
        "\u030B": "{\\H}",  # COMBINING DOUBLE ACUTE ACCENT
        "\u030C": "{\\v}",  # COMBINING CARON
        "\u030F": "{\\cyrchar\\C}",  # COMBINING DOUBLE GRAVE ACCENT
        "\u0311": "{\\fontencoding{LECO}\\selectfont\\char177}",  # COMBINING INVERTED BREVE
        "\u0318": "{\\fontencoding{LECO}\\selectfont\\char184}",  # COMBINING LEFT TACK BELOW
        "\u0319": "{\\fontencoding{LECO}\\selectfont\\char185}",  # COMBINING RIGHT TACK BELOW
        "\u0321": "{\\Elzpalh}",  # COMBINING PALATALIZED HOOK BELOW
        "\u0322": "{\\Elzrh}",  # COMBINING RETROFLEX HOOK BELOW
        "\u0327": "{\\c}",  # COMBINING CEDILLA
        "\u0328": "{\\k}",  # COMBINING OGONEK
        "\u032A": "{\\Elzsbbrg}",  # COMBINING BRIDGE BELOW
        "\u032B": "{\\fontencoding{LECO}\\selectfont\\char203}",  # COMBINING INVERTED DOUBLE ARCH BELOW
        "\u032F": "{\\fontencoding{LECO}\\selectfont\\char207}",  # COMBINING INVERTED BREVE BELOW
        "\u0335": "{\\Elzxl}",  # COMBINING SHORT STROKE OVERLAY
        "\u0336": "{\\Elzbar}",  # COMBINING LONG STROKE OVERLAY
        "\u0337": "{\\fontencoding{LECO}\\selectfont\\char215}",  # COMBINING SHORT SOLIDUS OVERLAY
        "\u0338": "{\\fontencoding{LECO}\\selectfont\\char216}",  # COMBINING LONG SOLIDUS OVERLAY
        "\u033A": "{\\fontencoding{LECO}\\selectfont\\char218}",  # COMBINING INVERTED BRIDGE BELOW
        "\u033B": "{\\fontencoding{LECO}\\selectfont\\char219}",  # COMBINING SQUARE BELOW
        "\u033C": "{\\fontencoding{LECO}\\selectfont\\char220}",  # COMBINING SEAGULL BELOW
        "\u033D": "{\\fontencoding{LECO}\\selectfont\\char221}",  # COMBINING X ABOVE
        "\u0361": "{\\fontencoding{LECO}\\selectfont\\char225}",  # COMBINING DOUBLE INVERTED BREVE
        "\u0386": "{\\'{A}}",  # GREEK CAPITAL LETTER ALPHA WITH TONOS
        "\u0388": "{\\'{E}}",  # GREEK CAPITAL LETTER EPSILON WITH TONOS
        "\u0389": "{\\'{H}}",  # GREEK CAPITAL LETTER ETA WITH TONOS
        "\u038A": "{\\'{}{I}}",  # GREEK CAPITAL LETTER IOTA WITH TONOS
        "\u038C": "{\\'{}O}",  # GREEK CAPITAL LETTER OMICRON WITH TONOS
        "\u038E": "$\\mathrm{'Y}$",  # GREEK CAPITAL LETTER UPSILON WITH TONOS
        "\u038F": '$\\mathrm{"\\Omega}$',  # GREEK CAPITAL LETTER OMEGA WITH TONOS
        "\u0390": "{\\acute{\\ddot{\\iota}}}",  # GREEK SMALL LETTER IOTA WITH DIALYTIKA AND TONOS
        "\u0391": "$\\upAlpha$",  # GREEK CAPITAL LETTER ALPHA
        "\u0392": "$\\upBeta$",  # GREEK CAPITAL LETTER BETA
        "\u0393": "$\\upGamma$",  # GREEK CAPITAL LETTER GAMMA
        "\u0394": "$\\upDelta$",  # GREEK CAPITAL LETTER DELTA
        "\u0395": "$\\upEpsilon$",  # GREEK CAPITAL LETTER EPSILON
        "\u0396": "$\\upZeta$",  # GREEK CAPITAL LETTER ZETA
        "\u0397": "$\\upEta$",  # GREEK CAPITAL LETTER ETA
        "\u0398": "$\\upTheta$",  # GREEK CAPITAL LETTER THETA
        "\u0399": "$\\upIota$",  # GREEK CAPITAL LETTER IOTA
        "\u039A": "$\\upKappa$",  # GREEK CAPITAL LETTER KAPPA
        "\u039B": "$\\upLambda$",  # GREEK CAPITAL LETTER LAMDA
        "\u039C": "$\\upMu$",  # GREEK CAPITAL LETTER MU
        "\u039D": "$\\upNu$",  # GREEK CAPITAL LETTER NU
        "\u039E": "$\\upXi$",  # GREEK CAPITAL LETTER XI
        "\u039F": "$\\upOmicron$",  # GREEK CAPITAL LETTER OMICRON
        "\u03A0": "$\\upPi$",  # GREEK CAPITAL LETTER PI
        "\u03A1": "$\\upRho$",  # GREEK CAPITAL LETTER RHO
        "\u03A3": "$\\upSigma$",  # GREEK CAPITAL LETTER SIGMA
        "\u03A4": "$\\upTau$",  # GREEK CAPITAL LETTER TAU
        "\u03A5": "$\\upUpsilon$",  # GREEK CAPITAL LETTER UPSILON
        "\u03A6": "$\\upPhi$",  # GREEK CAPITAL LETTER PHI
        "\u03A7": "$\\upChi$",  # GREEK CAPITAL LETTER CHI
        "\u03A8": "$\\upPsi$",  # GREEK CAPITAL LETTER PSI
        "\u03A9": "$\\upOmega$",  # GREEK CAPITAL LETTER OMEGA
        "\u03AA": "$\\mathrm{\\ddot{I}}$",  # GREEK CAPITAL LETTER IOTA WITH DIALYTIKA
        "\u03AB": "$\\mathrm{\\ddot{Y}}$",  # GREEK CAPITAL LETTER UPSILON WITH DIALYTIKA
        "\u03AC": "{\\'{$\\alpha$}}",  # GREEK SMALL LETTER ALPHA WITH TONOS
        "\u03AD": "{\\acute{\\epsilon}}",  # GREEK SMALL LETTER EPSILON WITH TONOS
        "\u03AE": "{\\acute{\\eta}}",  # GREEK SMALL LETTER ETA WITH TONOS
        "\u03AF": "{\\acute{\\iota}}",  # GREEK SMALL LETTER IOTA WITH TONOS
        "\u03B0": "{\\acute{\\ddot{\\upsilon}}}",  # GREEK SMALL LETTER UPSILON WITH DIALYTIKA AND TONOS
        "\u03B1": "$\\upalpha$",  # GREEK SMALL LETTER ALPHA
        "\u03B2": "$\\upbeta$",  # GREEK SMALL LETTER BETA
        "\u03B3": "$\\upgamma$",  # GREEK SMALL LETTER GAMMA
        "\u03B4": "$\\updelta$",  # GREEK SMALL LETTER DELTA
        "\u03B5": "$\\upepsilon$",  # GREEK SMALL LETTER EPSILON
        "\u03B6": "$\\upzeta$",  # GREEK SMALL LETTER ZETA
        "\u03B7": "$\\upeta$",  # GREEK SMALL LETTER ETA
        "\u03B8": "{\\texttheta}",  # GREEK SMALL LETTER THETA
        "\u03B9": "$\\upiota$",  # GREEK SMALL LETTER IOTA
        "\u03BA": "$\\upkappa$",  # GREEK SMALL LETTER KAPPA
        "\u03BB": "$\\uplambda$",  # GREEK SMALL LETTER LAMDA
        "\u03BC": "$\\upmu$",  # GREEK SMALL LETTER MU
        "\u03BD": "$\\upnu$",  # GREEK SMALL LETTER NU
        "\u03BE": "$\\upxi$",  # GREEK SMALL LETTER XI
        "\u03BF": "$\\upomicron$",  # GREEK SMALL LETTER OMICRON
        "\u03C0": "$\\uppi$",  # GREEK SMALL LETTER PI
        "\u03C1": "$\\uprho$",  # GREEK SMALL LETTER RHO
        "\u03C2": "$\\upvarsigma$",  # GREEK SMALL LETTER FINAL SIGMA
        "\u03C3": "$\\upsigma$",  # GREEK SMALL LETTER SIGMA
        "\u03C4": "$\\uptau$",  # GREEK SMALL LETTER TAU
        "\u03C5": "$\\upupsilon$",  # GREEK SMALL LETTER UPSILON
        "\u03C6": "$\\upvarphi$",  # GREEK SMALL LETTER PHI
        "\u03C7": "$\\upchi$",  # GREEK SMALL LETTER CHI
        "\u03C8": "$\\uppsi$",  # GREEK SMALL LETTER PSI
        "\u03C9": "$\\upomega$",  # GREEK SMALL LETTER OMEGA
        "\u03CA": "{\\ddot{\\iota}}",  # GREEK SMALL LETTER IOTA WITH DIALYTIKA
        "\u03CB": "{\\ddot{\\upsilon}}",  # GREEK SMALL LETTER UPSILON WITH DIALYTIKA
        "\u03CC": "{\\'{o}}",  # GREEK SMALL LETTER OMICRON WITH TONOS
        "\u03CD": "{\\acute{\\upsilon}}",  # GREEK SMALL LETTER UPSILON WITH TONOS
        "\u03CE": "{\\acute{\\omega}}",  # GREEK SMALL LETTER OMEGA WITH TONOS
        "\u03D0": "{\\Pisymbol{ppi022}{87}}",  # GREEK BETA SYMBOL
        "\u03D1": "{\\textvartheta}",  # GREEK THETA SYMBOL
        "\u03D2": "{\\Upsilon}",  # GREEK UPSILON WITH HOOK SYMBOL
        "\u03D5": "$\\upphi$",  # GREEK PHI SYMBOL
        "\u03D6": "$\\upvarpi$",  # GREEK PI SYMBOL
        "\u03DA": "$\\upStigma$",  # GREEK LETTER STIGMA
        "\u03DC": "$\\upDigamma$",  # GREEK LETTER DIGAMMA
        "\u03DD": "$\\updigamma$",  # GREEK SMALL LETTER DIGAMMA
        "\u03DE": "$\\upKoppa$",  # GREEK LETTER KOPPA
        "\u03E0": "$\\upSampi$",  # GREEK LETTER SAMPI
        "\u03F0": "$\\upvarkappa$",  # GREEK KAPPA SYMBOL
        "\u03F1": "$\\upvarrho$",  # GREEK RHO SYMBOL
        "\u03F4": "{\\textTheta}",  # GREEK CAPITAL THETA SYMBOL
        "\u03F6": "$\\upbackepsilon$",  # GREEK REVERSED LUNATE EPSILON SYMBOL
        "\u0401": "{\\cyrchar\\CYRYO}",  # CYRILLIC CAPITAL LETTER IO
        "\u0402": "{\\cyrchar\\CYRDJE}",  # CYRILLIC CAPITAL LETTER DJE
        "\u0403": '{\\cyrchar{\\"\\CYRG}}',  # CYRILLIC CAPITAL LETTER GJE
        "\u0404": "{\\cyrchar\\CYRIE}",  # CYRILLIC CAPITAL LETTER UKRAINIAN IE
        "\u0405": "{\\cyrchar\\CYRDZE}",  # CYRILLIC CAPITAL LETTER DZE
        "\u0406": "{\\cyrchar\\CYRII}",  # CYRILLIC CAPITAL LETTER BYELORUSSIAN-UKRAINIAN I
        "\u0407": "{\\cyrchar\\CYRYI}",  # CYRILLIC CAPITAL LETTER YI
        "\u0408": "{\\cyrchar\\CYRJE}",  # CYRILLIC CAPITAL LETTER JE
        "\u0409": "{\\cyrchar\\CYRLJE}",  # CYRILLIC CAPITAL LETTER LJE
        "\u040A": "{\\cyrchar\\CYRNJE}",  # CYRILLIC CAPITAL LETTER NJE
        "\u040B": "{\\cyrchar\\CYRTSHE}",  # CYRILLIC CAPITAL LETTER TSHE
        "\u040C": '{\\cyrchar{\\"\\CYRK}}',  # CYRILLIC CAPITAL LETTER KJE
        "\u040E": "{\\cyrchar\\CYRUSHRT}",  # CYRILLIC CAPITAL LETTER SHORT U
        "\u040F": "{\\cyrchar\\CYRDZHE}",  # CYRILLIC CAPITAL LETTER DZHE
        "\u0410": "{\\cyrchar\\CYRA}",  # CYRILLIC CAPITAL LETTER A
        "\u0411": "{\\cyrchar\\CYRB}",  # CYRILLIC CAPITAL LETTER BE
        "\u0412": "{\\cyrchar\\CYRV}",  # CYRILLIC CAPITAL LETTER VE
        "\u0413": "{\\cyrchar\\CYRG}",  # CYRILLIC CAPITAL LETTER GHE
        "\u0414": "{\\cyrchar\\CYRD}",  # CYRILLIC CAPITAL LETTER DE
        "\u0415": "{\\cyrchar\\CYRE}",  # CYRILLIC CAPITAL LETTER IE
        "\u0416": "{\\cyrchar\\CYRZH}",  # CYRILLIC CAPITAL LETTER ZHE
        "\u0417": "{\\cyrchar\\CYRZ}",  # CYRILLIC CAPITAL LETTER ZE
        "\u0418": "{\\cyrchar\\CYRI}",  # CYRILLIC CAPITAL LETTER I
        "\u0419": "{\\cyrchar\\CYRISHRT}",  # CYRILLIC CAPITAL LETTER SHORT I
        "\u041A": "{\\cyrchar\\CYRK}",  # CYRILLIC CAPITAL LETTER KA
        "\u041B": "{\\cyrchar\\CYRL}",  # CYRILLIC CAPITAL LETTER EL
        "\u041C": "{\\cyrchar\\CYRM}",  # CYRILLIC CAPITAL LETTER EM
        "\u041D": "{\\cyrchar\\CYRN}",  # CYRILLIC CAPITAL LETTER EN
        "\u041E": "{\\cyrchar\\CYRO}",  # CYRILLIC CAPITAL LETTER O
        "\u041F": "{\\cyrchar\\CYRP}",  # CYRILLIC CAPITAL LETTER PE
        "\u0420": "{\\cyrchar\\CYRR}",  # CYRILLIC CAPITAL LETTER ER
        "\u0421": "{\\cyrchar\\CYRS}",  # CYRILLIC CAPITAL LETTER ES
        "\u0422": "{\\cyrchar\\CYRT}",  # CYRILLIC CAPITAL LETTER TE
        "\u0423": "{\\cyrchar\\CYRU}",  # CYRILLIC CAPITAL LETTER U
        "\u0424": "{\\cyrchar\\CYRF}",  # CYRILLIC CAPITAL LETTER EF
        "\u0425": "{\\cyrchar\\CYRH}",  # CYRILLIC CAPITAL LETTER HA
        "\u0426": "{\\cyrchar\\CYRC}",  # CYRILLIC CAPITAL LETTER TSE
        "\u0427": "{\\cyrchar\\CYRCH}",  # CYRILLIC CAPITAL LETTER CHE
        "\u0428": "{\\cyrchar\\CYRSH}",  # CYRILLIC CAPITAL LETTER SHA
        "\u0429": "{\\cyrchar\\CYRSHCH}",  # CYRILLIC CAPITAL LETTER SHCHA
        "\u042A": "{\\cyrchar\\CYRHRDSN}",  # CYRILLIC CAPITAL LETTER HARD SIGN
        "\u042B": "{\\cyrchar\\CYRERY}",  # CYRILLIC CAPITAL LETTER YERU
        "\u042C": "{\\cyrchar\\CYRSFTSN}",  # CYRILLIC CAPITAL LETTER SOFT SIGN
        "\u042D": "{\\cyrchar\\CYREREV}",  # CYRILLIC CAPITAL LETTER E
        "\u042E": "{\\cyrchar\\CYRYU}",  # CYRILLIC CAPITAL LETTER YU
        "\u042F": "{\\cyrchar\\CYRYA}",  # CYRILLIC CAPITAL LETTER YA
        "\u0430": "{\\cyrchar\\cyra}",  # CYRILLIC SMALL LETTER A
        "\u0431": "{\\cyrchar\\cyrb}",  # CYRILLIC SMALL LETTER BE
        "\u0432": "{\\cyrchar\\cyrv}",  # CYRILLIC SMALL LETTER VE
        "\u0433": "{\\cyrchar\\cyrg}",  # CYRILLIC SMALL LETTER GHE
        "\u0434": "{\\cyrchar\\cyrd}",  # CYRILLIC SMALL LETTER DE
        "\u0435": "{\\cyrchar\\cyre}",  # CYRILLIC SMALL LETTER IE
        "\u0436": "{\\cyrchar\\cyrzh}",  # CYRILLIC SMALL LETTER ZHE
        "\u0437": "{\\cyrchar\\cyrz}",  # CYRILLIC SMALL LETTER ZE
        "\u0438": "{\\cyrchar\\cyri}",  # CYRILLIC SMALL LETTER I
        "\u0439": "{\\cyrchar\\cyrishrt}",  # CYRILLIC SMALL LETTER SHORT I
        "\u043A": "{\\cyrchar\\cyrk}",  # CYRILLIC SMALL LETTER KA
        "\u043B": "{\\cyrchar\\cyrl}",  # CYRILLIC SMALL LETTER EL
        "\u043C": "{\\cyrchar\\cyrm}",  # CYRILLIC SMALL LETTER EM
        "\u043D": "{\\cyrchar\\cyrn}",  # CYRILLIC SMALL LETTER EN
        "\u043E": "{\\cyrchar\\cyro}",  # CYRILLIC SMALL LETTER O
        "\u043F": "{\\cyrchar\\cyrp}",  # CYRILLIC SMALL LETTER PE
        "\u0440": "{\\cyrchar\\cyrr}",  # CYRILLIC SMALL LETTER ER
        "\u0441": "{\\cyrchar\\cyrs}",  # CYRILLIC SMALL LETTER ES
        "\u0442": "{\\cyrchar\\cyrt}",  # CYRILLIC SMALL LETTER TE
        "\u0443": "{\\cyrchar\\cyru}",  # CYRILLIC SMALL LETTER U
        "\u0444": "{\\cyrchar\\cyrf}",  # CYRILLIC SMALL LETTER EF
        "\u0445": "{\\cyrchar\\cyrh}",  # CYRILLIC SMALL LETTER HA
        "\u0446": "{\\cyrchar\\cyrc}",  # CYRILLIC SMALL LETTER TSE
        "\u0447": "{\\cyrchar\\cyrch}",  # CYRILLIC SMALL LETTER CHE
        "\u0448": "{\\cyrchar\\cyrsh}",  # CYRILLIC SMALL LETTER SHA
        "\u0449": "{\\cyrchar\\cyrshch}",  # CYRILLIC SMALL LETTER SHCHA
        "\u044A": "{\\cyrchar\\cyrhrdsn}",  # CYRILLIC SMALL LETTER HARD SIGN
        "\u044B": "{\\cyrchar\\cyrery}",  # CYRILLIC SMALL LETTER YERU
        "\u044C": "{\\cyrchar\\cyrsftsn}",  # CYRILLIC SMALL LETTER SOFT SIGN
        "\u044D": "{\\cyrchar\\cyrerev}",  # CYRILLIC SMALL LETTER E
        "\u044E": "{\\cyrchar\\cyryu}",  # CYRILLIC SMALL LETTER YU
        "\u044F": "{\\cyrchar\\cyrya}",  # CYRILLIC SMALL LETTER YA
        "\u0451": "{\\cyrchar\\cyryo}",  # CYRILLIC SMALL LETTER IO
        "\u0452": "{\\cyrchar\\cyrdje}",  # CYRILLIC SMALL LETTER DJE
        "\u0453": '{\\cyrchar{\\"\\cyrg}}',  # CYRILLIC SMALL LETTER GJE
        "\u0454": "{\\cyrchar\\cyrie}",  # CYRILLIC SMALL LETTER UKRAINIAN IE
        "\u0455": "{\\cyrchar\\cyrdze}",  # CYRILLIC SMALL LETTER DZE
        "\u0456": "{\\cyrchar\\cyrii}",  # CYRILLIC SMALL LETTER BYELORUSSIAN-UKRAINIAN I
        "\u0457": "{\\cyrchar\\cyryi}",  # CYRILLIC SMALL LETTER YI
        "\u0458": "{\\cyrchar\\cyrje}",  # CYRILLIC SMALL LETTER JE
        "\u0459": "{\\cyrchar\\cyrlje}",  # CYRILLIC SMALL LETTER LJE
        "\u045A": "{\\cyrchar\\cyrnje}",  # CYRILLIC SMALL LETTER NJE
        "\u045B": "{\\cyrchar\\cyrtshe}",  # CYRILLIC SMALL LETTER TSHE
        "\u045C": '{\\cyrchar{\\"\\cyrk}}',  # CYRILLIC SMALL LETTER KJE
        "\u045E": "{\\cyrchar\\cyrushrt}",  # CYRILLIC SMALL LETTER SHORT U
        "\u045F": "{\\cyrchar\\cyrdzhe}",  # CYRILLIC SMALL LETTER DZHE
        "\u0460": "{\\cyrchar\\CYROMEGA}",  # CYRILLIC CAPITAL LETTER OMEGA
        "\u0461": "{\\cyrchar\\cyromega}",  # CYRILLIC SMALL LETTER OMEGA
        "\u0462": "{\\cyrchar\\CYRYAT}",  # CYRILLIC CAPITAL LETTER YAT
        "\u0464": "{\\cyrchar\\CYRIOTE}",  # CYRILLIC CAPITAL LETTER IOTIFIED E
        "\u0465": "{\\cyrchar\\cyriote}",  # CYRILLIC SMALL LETTER IOTIFIED E
        "\u0466": "{\\cyrchar\\CYRLYUS}",  # CYRILLIC CAPITAL LETTER LITTLE YUS
        "\u0467": "{\\cyrchar\\cyrlyus}",  # CYRILLIC SMALL LETTER LITTLE YUS
        "\u0468": "{\\cyrchar\\CYRIOTLYUS}",  # CYRILLIC CAPITAL LETTER IOTIFIED LITTLE YUS
        "\u0469": "{\\cyrchar\\cyriotlyus}",  # CYRILLIC SMALL LETTER IOTIFIED LITTLE YUS
        "\u046A": "{\\cyrchar\\CYRBYUS}",  # CYRILLIC CAPITAL LETTER BIG YUS
        "\u046C": "{\\cyrchar\\CYRIOTBYUS}",  # CYRILLIC CAPITAL LETTER IOTIFIED BIG YUS
        "\u046D": "{\\cyrchar\\cyriotbyus}",  # CYRILLIC SMALL LETTER IOTIFIED BIG YUS
        "\u046E": "{\\cyrchar\\CYRKSI}",  # CYRILLIC CAPITAL LETTER KSI
        "\u046F": "{\\cyrchar\\cyrksi}",  # CYRILLIC SMALL LETTER KSI
        "\u0470": "{\\cyrchar\\CYRPSI}",  # CYRILLIC CAPITAL LETTER PSI
        "\u0471": "{\\cyrchar\\cyrpsi}",  # CYRILLIC SMALL LETTER PSI
        "\u0472": "{\\cyrchar\\CYRFITA}",  # CYRILLIC CAPITAL LETTER FITA
        "\u0474": "{\\cyrchar\\CYRIZH}",  # CYRILLIC CAPITAL LETTER IZHITSA
        "\u0478": "{\\cyrchar\\CYRUK}",  # CYRILLIC CAPITAL LETTER UK
        "\u0479": "{\\cyrchar\\cyruk}",  # CYRILLIC SMALL LETTER UK
        "\u047A": "{\\cyrchar\\CYROMEGARND}",  # CYRILLIC CAPITAL LETTER ROUND OMEGA
        "\u047B": "{\\cyrchar\\cyromegarnd}",  # CYRILLIC SMALL LETTER ROUND OMEGA
        "\u047C": "{\\cyrchar\\CYROMEGATITLO}",  # CYRILLIC CAPITAL LETTER OMEGA WITH TITLO
        "\u047D": "{\\cyrchar\\cyromegatitlo}",  # CYRILLIC SMALL LETTER OMEGA WITH TITLO
        "\u047E": "{\\cyrchar\\CYROT}",  # CYRILLIC CAPITAL LETTER OT
        "\u047F": "{\\cyrchar\\cyrot}",  # CYRILLIC SMALL LETTER OT
        "\u0480": "{\\cyrchar\\CYRKOPPA}",  # CYRILLIC CAPITAL LETTER KOPPA
        "\u0481": "{\\cyrchar\\cyrkoppa}",  # CYRILLIC SMALL LETTER KOPPA
        "\u0482": "{\\cyrchar\\cyrthousands}",  # CYRILLIC THOUSANDS SIGN
        "\u0488": "{\\cyrchar\\cyrhundredthousands}",  # COMBINING CYRILLIC HUNDRED THOUSANDS SIGN
        "\u0489": "{\\cyrchar\\cyrmillions}",  # COMBINING CYRILLIC MILLIONS SIGN
        "\u048C": "{\\cyrchar\\CYRSEMISFTSN}",  # CYRILLIC CAPITAL LETTER SEMISOFT SIGN
        "\u048D": "{\\cyrchar\\cyrsemisftsn}",  # CYRILLIC SMALL LETTER SEMISOFT SIGN
        "\u048E": "{\\cyrchar\\CYRRTICK}",  # CYRILLIC CAPITAL LETTER ER WITH TICK
        "\u048F": "{\\cyrchar\\cyrrtick}",  # CYRILLIC SMALL LETTER ER WITH TICK
        "\u0490": "{\\cyrchar\\CYRGUP}",  # CYRILLIC CAPITAL LETTER GHE WITH UPTURN
        "\u0491": "{\\cyrchar\\cyrgup}",  # CYRILLIC SMALL LETTER GHE WITH UPTURN
        "\u0492": "{\\cyrchar\\CYRGHCRS}",  # CYRILLIC CAPITAL LETTER GHE WITH STROKE
        "\u0493": "{\\cyrchar\\cyrghcrs}",  # CYRILLIC SMALL LETTER GHE WITH STROKE
        "\u0494": "{\\cyrchar\\CYRGHK}",  # CYRILLIC CAPITAL LETTER GHE WITH MIDDLE HOOK
        "\u0495": "{\\cyrchar\\cyrghk}",  # CYRILLIC SMALL LETTER GHE WITH MIDDLE HOOK
        "\u0496": "{\\cyrchar\\CYRZHDSC}",  # CYRILLIC CAPITAL LETTER ZHE WITH DESCENDER
        "\u0497": "{\\cyrchar\\cyrzhdsc}",  # CYRILLIC SMALL LETTER ZHE WITH DESCENDER
        "\u0498": "{\\cyrchar\\CYRZDSC}",  # CYRILLIC CAPITAL LETTER ZE WITH DESCENDER
        "\u0499": "{\\cyrchar\\cyrzdsc}",  # CYRILLIC SMALL LETTER ZE WITH DESCENDER
        "\u049A": "{\\cyrchar\\CYRKDSC}",  # CYRILLIC CAPITAL LETTER KA WITH DESCENDER
        "\u049B": "{\\cyrchar\\cyrkdsc}",  # CYRILLIC SMALL LETTER KA WITH DESCENDER
        "\u049C": "{\\cyrchar\\CYRKVCRS}",  # CYRILLIC CAPITAL LETTER KA WITH VERTICAL STROKE
        "\u049D": "{\\cyrchar\\cyrkvcrs}",  # CYRILLIC SMALL LETTER KA WITH VERTICAL STROKE
        "\u049E": "{\\cyrchar\\CYRKHCRS}",  # CYRILLIC CAPITAL LETTER KA WITH STROKE
        "\u049F": "{\\cyrchar\\cyrkhcrs}",  # CYRILLIC SMALL LETTER KA WITH STROKE
        "\u04A0": "{\\cyrchar\\CYRKBEAK}",  # CYRILLIC CAPITAL LETTER BASHKIR KA
        "\u04A1": "{\\cyrchar\\cyrkbeak}",  # CYRILLIC SMALL LETTER BASHKIR KA
        "\u04A2": "{\\cyrchar\\CYRNDSC}",  # CYRILLIC CAPITAL LETTER EN WITH DESCENDER
        "\u04A3": "{\\cyrchar\\cyrndsc}",  # CYRILLIC SMALL LETTER EN WITH DESCENDER
        "\u04A4": "{\\cyrchar\\CYRNG}",  # CYRILLIC CAPITAL LIGATURE EN GHE
        "\u04A5": "{\\cyrchar\\cyrng}",  # CYRILLIC SMALL LIGATURE EN GHE
        "\u04A6": "{\\cyrchar\\CYRPHK}",  # CYRILLIC CAPITAL LETTER PE WITH MIDDLE HOOK
        "\u04A7": "{\\cyrchar\\cyrphk}",  # CYRILLIC SMALL LETTER PE WITH MIDDLE HOOK
        "\u04A8": "{\\cyrchar\\CYRABHHA}",  # CYRILLIC CAPITAL LETTER ABKHASIAN HA
        "\u04A9": "{\\cyrchar\\cyrabhha}",  # CYRILLIC SMALL LETTER ABKHASIAN HA
        "\u04AA": "{\\cyrchar\\CYRSDSC}",  # CYRILLIC CAPITAL LETTER ES WITH DESCENDER
        "\u04AB": "{\\cyrchar\\cyrsdsc}",  # CYRILLIC SMALL LETTER ES WITH DESCENDER
        "\u04AC": "{\\cyrchar\\CYRTDSC}",  # CYRILLIC CAPITAL LETTER TE WITH DESCENDER
        "\u04AD": "{\\cyrchar\\cyrtdsc}",  # CYRILLIC SMALL LETTER TE WITH DESCENDER
        "\u04AE": "{\\cyrchar\\CYRY}",  # CYRILLIC CAPITAL LETTER STRAIGHT U
        "\u04AF": "{\\cyrchar\\cyry}",  # CYRILLIC SMALL LETTER STRAIGHT U
        "\u04B0": "{\\cyrchar\\CYRYHCRS}",  # CYRILLIC CAPITAL LETTER STRAIGHT U WITH STROKE
        "\u04B1": "{\\cyrchar\\cyryhcrs}",  # CYRILLIC SMALL LETTER STRAIGHT U WITH STROKE
        "\u04B2": "{\\cyrchar\\CYRHDSC}",  # CYRILLIC CAPITAL LETTER HA WITH DESCENDER
        "\u04B3": "{\\cyrchar\\cyrhdsc}",  # CYRILLIC SMALL LETTER HA WITH DESCENDER
        "\u04B4": "{\\cyrchar\\CYRTETSE}",  # CYRILLIC CAPITAL LIGATURE TE TSE
        "\u04B5": "{\\cyrchar\\cyrtetse}",  # CYRILLIC SMALL LIGATURE TE TSE
        "\u04B6": "{\\cyrchar\\CYRCHRDSC}",  # CYRILLIC CAPITAL LETTER CHE WITH DESCENDER
        "\u04B7": "{\\cyrchar\\cyrchrdsc}",  # CYRILLIC SMALL LETTER CHE WITH DESCENDER
        "\u04B8": "{\\cyrchar\\CYRCHVCRS}",  # CYRILLIC CAPITAL LETTER CHE WITH VERTICAL STROKE
        "\u04B9": "{\\cyrchar\\cyrchvcrs}",  # CYRILLIC SMALL LETTER CHE WITH VERTICAL STROKE
        "\u04BA": "{\\cyrchar\\CYRSHHA}",  # CYRILLIC CAPITAL LETTER SHHA
        "\u04BB": "{\\cyrchar\\cyrshha}",  # CYRILLIC SMALL LETTER SHHA
        "\u04BC": "{\\cyrchar\\CYRABHCH}",  # CYRILLIC CAPITAL LETTER ABKHASIAN CHE
        "\u04BD": "{\\cyrchar\\cyrabhch}",  # CYRILLIC SMALL LETTER ABKHASIAN CHE
        "\u04BE": "{\\cyrchar\\CYRABHCHDSC}",  # CYRILLIC CAPITAL LETTER ABKHASIAN CHE WITH DESCENDER
        "\u04BF": "{\\cyrchar\\cyrabhchdsc}",  # CYRILLIC SMALL LETTER ABKHASIAN CHE WITH DESCENDER
        "\u04C0": "{\\cyrchar\\CYRpalochka}",  # CYRILLIC LETTER PALOCHKA
        "\u04C3": "{\\cyrchar\\CYRKHK}",  # CYRILLIC CAPITAL LETTER KA WITH HOOK
        "\u04C4": "{\\cyrchar\\cyrkhk}",  # CYRILLIC SMALL LETTER KA WITH HOOK
        "\u04C7": "{\\cyrchar\\CYRNHK}",  # CYRILLIC CAPITAL LETTER EN WITH HOOK
        "\u04C8": "{\\cyrchar\\cyrnhk}",  # CYRILLIC SMALL LETTER EN WITH HOOK
        "\u04CB": "{\\cyrchar\\CYRCHLDSC}",  # CYRILLIC CAPITAL LETTER KHAKASSIAN CHE
        "\u04CC": "{\\cyrchar\\cyrchldsc}",  # CYRILLIC SMALL LETTER KHAKASSIAN CHE
        "\u04D4": "{\\cyrchar\\CYRAE}",  # CYRILLIC CAPITAL LIGATURE A IE
        "\u04D5": "{\\cyrchar\\cyrae}",  # CYRILLIC SMALL LIGATURE A IE
        "\u04D8": "{\\cyrchar\\CYRSCHWA}",  # CYRILLIC CAPITAL LETTER SCHWA
        "\u04D9": "{\\cyrchar\\cyrschwa}",  # CYRILLIC SMALL LETTER SCHWA
        "\u04E0": "{\\cyrchar\\CYRABHDZE}",  # CYRILLIC CAPITAL LETTER ABKHASIAN DZE
        "\u04E1": "{\\cyrchar\\cyrabhdze}",  # CYRILLIC SMALL LETTER ABKHASIAN DZE
        "\u04E8": "{\\cyrchar\\CYROTLD}",  # CYRILLIC CAPITAL LETTER BARRED O
        "\u04E9": "{\\cyrchar\\cyrotld}",  # CYRILLIC SMALL LETTER BARRED O
        "\u2002": "{\\hspace{0.6em}}",  # EN SPACE
        "\u2003": "{\\hspace{1em}}",  # EM SPACE
        "\u2004": "{\\hspace{0.33em}}",  # THREE-PER-EM SPACE
        "\u2005": "{\\hspace{0.25em}}",  # FOUR-PER-EM SPACE
        "\u2006": "{\\hspace{0.166em}}",  # SIX-PER-EM SPACE
        "\u2007": "{\\hphantom{0}}",  # FIGURE SPACE
        "\u2008": "{\\hphantom{,}}",  # PUNCTUATION SPACE
        "\u2009": "{\\hspace{0.167em}}",  # THIN SPACE
        "\u200A": "{\\mkern1mu}",  # HAIR SPACE
        "\u2010": "-",  # HYPHEN
        "\u2013": "{\\textendash}",  # EN DASH
        "\u2014": "{\\textemdash}",  # EM DASH
        "\u2015": "{\\rule{1em}{1pt}}",  # HORIZONTAL BAR
        "\u2016": "$\\Vert$",  # DOUBLE VERTICAL LINE
        "\u2018": "`",  # LEFT SINGLE QUOTATION MARK
        "\u2019": "'",  # RIGHT SINGLE QUOTATION MARK
        "\u201A": ",",  # SINGLE LOW-9 QUOTATION MARK
        "\u201B": "{\\Elzreapos}",  # SINGLE HIGH-REVERSED-9 QUOTATION MARK
        "\u201C": "{\\textquotedblleft}",  # LEFT DOUBLE QUOTATION MARK
        "\u201D": "{\\textquotedblright}",  # RIGHT DOUBLE QUOTATION MARK
        "\u201E": ",,",  # DOUBLE LOW-9 QUOTATION MARK
        "\u2020": "{\\textdagger}",  # DAGGER
        "\u2021": "{\\textdaggerdbl}",  # DOUBLE DAGGER
        "\u2022": "{\\textbullet}",  # BULLET
        "\u2024": ".",  # ONE DOT LEADER
        "\u2025": "..",  # TWO DOT LEADER
        "\u2026": "{\\ldots}",  # HORIZONTAL ELLIPSIS
        "\u2030": "{\\textperthousand}",  # PER MILLE SIGN
        "\u2031": "{\\textpertenthousand}",  # PER TEN THOUSAND SIGN
        "\u2032": "$\\prime$",  # PRIME
        "\u2033": "$\\dprime$",  # DOUBLE PRIME
        "\u2034": "$\\trprime$",  # TRIPLE PRIME
        "\u2035": "$\\backprime$",  # REVERSED PRIME
        "\u2039": "{\\guilsinglleft}",  # SINGLE LEFT-POINTING ANGLE QUOTATION MARK
        "\u203A": "{\\guilsinglright}",  # SINGLE RIGHT-POINTING ANGLE QUOTATION MARK
        "\u2057": "$\\qprime$",  # QUADRUPLE PRIME
        "\u205F": "{\\mkern4mu}",  # MEDIUM MATHEMATICAL SPACE
        "\u2060": "{\\nolinebreak}",  # WORD JOINER
        "\u20A7": "{\\ensuremath{\\Elzpes}}",  # PESETA SIGN
        "\u20AC": "{\\mbox{\\texteuro}}",  # EURO SIGN
        "\u20DB": "$\\dddot$",  # COMBINING THREE DOTS ABOVE
        "\u20DC": "$\\ddddot$",  # COMBINING FOUR DOTS ABOVE
        "\u2102": "$\\BbbC$",  # DOUBLE-STRUCK CAPITAL C
        "\u210A": "$\\mathscr{g}$",  # SCRIPT SMALL G
        "\u210B": "$\\mscrH$",  # SCRIPT CAPITAL H
        "\u210C": "$\\mfrakH$",  # BLACK-LETTER CAPITAL H
        "\u210D": "$\\BbbH$",  # DOUBLE-STRUCK CAPITAL H
        "\u210F": "$\\hslash$",  # PLANCK CONSTANT OVER TWO PI
        "\u2110": "$\\mscrI$",  # SCRIPT CAPITAL I
        "\u2111": "$\\Im$",  # BLACK-LETTER CAPITAL I
        "\u2112": "$\\mscrL$",  # SCRIPT CAPITAL L
        "\u2113": "$\\ell$",  # SCRIPT SMALL L
        "\u2115": "$\\BbbN$",  # DOUBLE-STRUCK CAPITAL N
        "\u2116": "{\\cyrchar\\textnumero}",  # NUMERO SIGN
        "\u2118": "$\\wp$",  # SCRIPT CAPITAL P
        "\u2119": "$\\BbbP$",  # DOUBLE-STRUCK CAPITAL P
        "\u211A": "$\\BbbQ$",  # DOUBLE-STRUCK CAPITAL Q
        "\u211B": "$\\mscrR$",  # SCRIPT CAPITAL R
        "\u211C": "$\\Re$",  # BLACK-LETTER CAPITAL R
        "\u211D": "$\\BbbR$",  # DOUBLE-STRUCK CAPITAL R
        "\u211E": "{\\Elzxrat}",  # PRESCRIPTION TAKE
        "\u2122": "{\\texttrademark}",  # TRADE MARK SIGN
        "\u2124": "$\\BbbZ$",  # DOUBLE-STRUCK CAPITAL Z
        "\u2126": "{\\Omega}",  # OHM SIGN
        "\u2127": "$\\mho$",  # INVERTED OHM SIGN
        "\u2128": "$\\mfrakZ$",  # BLACK-LETTER CAPITAL Z
        "\u2129": "$\\turnediota$",  # TURNED GREEK SMALL LETTER IOTA
        "\u212B": "{\\AA}",  # ANGSTROM SIGN
        "\u212C": "$\\mscrB$",  # SCRIPT CAPITAL B
        "\u212D": "$\\mfrakC$",  # BLACK-LETTER CAPITAL C
        "\u212F": "$\\mscre$",  # SCRIPT SMALL E
        "\u2130": "$\\mscrE$",  # SCRIPT CAPITAL E
        "\u2131": "$\\mscrF$",  # SCRIPT CAPITAL F
        "\u2133": "$\\mscrM$",  # SCRIPT CAPITAL M
        "\u2134": "$\\mscro$",  # SCRIPT SMALL O
        "\u2135": "$\\aleph$",  # ALEF SYMBOL
        "\u2136": "$\\beth$",  # BET SYMBOL
        "\u2137": "$\\gimel$",  # GIMEL SYMBOL
        "\u2138": "$\\daleth$",  # DALET SYMBOL
        "\u2153": "{\\textfrac{1}{3}}",  # VULGAR FRACTION ONE THIRD
        "\u2154": "{\\textfrac{2}{3}}",  # VULGAR FRACTION TWO THIRDS
        "\u2155": "{\\textfrac{1}{5}}",  # VULGAR FRACTION ONE FIFTH
        "\u2156": "{\\textfrac{2}{5}}",  # VULGAR FRACTION TWO FIFTHS
        "\u2157": "{\\textfrac{3}{5}}",  # VULGAR FRACTION THREE FIFTHS
        "\u2158": "{\\textfrac{4}{5}}",  # VULGAR FRACTION FOUR FIFTHS
        "\u2159": "{\\textfrac{1}{6}}",  # VULGAR FRACTION ONE SIXTH
        "\u215A": "{\\textfrac{5}{6}}",  # VULGAR FRACTION FIVE SIXTHS
        "\u215B": "{\\textfrac{1}{8}}",  # VULGAR FRACTION ONE EIGHTH
        "\u215C": "{\\textfrac{3}{8}}",  # VULGAR FRACTION THREE EIGHTHS
        "\u215D": "{\\textfrac{5}{8}}",  # VULGAR FRACTION FIVE EIGHTHS
        "\u215E": "{\\textfrac{7}{8}}",  # VULGAR FRACTION SEVEN EIGHTHS
        "\u2190": "$\\leftarrow$",  # LEFTWARDS ARROW
        "\u2191": "$\\uparrow$",  # UPWARDS ARROW
        "\u2192": "$\\rightarrow$",  # RIGHTWARDS ARROW
        "\u2193": "$\\downarrow$",  # DOWNWARDS ARROW
        "\u2194": "$\\leftrightarrow$",  # LEFT RIGHT ARROW
        "\u2195": "$\\updownarrow$",  # UP DOWN ARROW
        "\u2196": "$\\nwarrow$",  # NORTH WEST ARROW
        "\u2197": "$\\nearrow$",  # NORTH EAST ARROW
        "\u2198": "$\\searrow$",  # SOUTH EAST ARROW
        "\u2199": "$\\swarrow$",  # SOUTH WEST ARROW
        "\u219A": "$\\nleftarrow$",  # LEFTWARDS ARROW WITH STROKE
        "\u219B": "$\\nrightarrow$",  # RIGHTWARDS ARROW WITH STROKE
        "\u219C": "$\\leftwavearrow$",  # LEFTWARDS WAVE ARROW
        "\u219D": "$\\rightwavearrow$",  # RIGHTWARDS WAVE ARROW
        "\u219E": "$\\twoheadleftarrow$",  # LEFTWARDS TWO HEADED ARROW
        "\u21A0": "$\\twoheadrightarrow$",  # RIGHTWARDS TWO HEADED ARROW
        "\u21A2": "$\\leftarrowtail$",  # LEFTWARDS ARROW WITH TAIL
        "\u21A3": "$\\rightarrowtail$",  # RIGHTWARDS ARROW WITH TAIL
        "\u21A6": "$\\mapsto$",  # RIGHTWARDS ARROW FROM BAR
        "\u21A9": "$\\hookleftarrow$",  # LEFTWARDS ARROW WITH HOOK
        "\u21AA": "$\\hookrightarrow$",  # RIGHTWARDS ARROW WITH HOOK
        "\u21AB": "$\\looparrowleft$",  # LEFTWARDS ARROW WITH LOOP
        "\u21AC": "$\\looparrowright$",  # RIGHTWARDS ARROW WITH LOOP
        "\u21AD": "$\\leftrightsquigarrow$",  # LEFT RIGHT WAVE ARROW
        "\u21AE": "$\\nleftrightarrow$",  # LEFT RIGHT ARROW WITH STROKE
        "\u21B0": "$\\Lsh$",  # UPWARDS ARROW WITH TIP LEFTWARDS
        "\u21B1": "$\\Rsh$",  # UPWARDS ARROW WITH TIP RIGHTWARDS
        "\u21B3": "$\\Rdsh$",  # DOWNWARDS ARROW WITH TIP RIGHTWARDS
        "\u21B6": "$\\curvearrowleft$",  # ANTICLOCKWISE TOP SEMICIRCLE ARROW
        "\u21B7": "$\\curvearrowright$",  # CLOCKWISE TOP SEMICIRCLE ARROW
        "\u21BA": "$\\acwopencirclearrow$",  # ANTICLOCKWISE OPEN CIRCLE ARROW
        "\u21BB": "$\\cwopencirclearrow$",  # CLOCKWISE OPEN CIRCLE ARROW
        "\u21BC": "$\\leftharpoonup$",  # LEFTWARDS HARPOON WITH BARB UPWARDS
        "\u21BD": "$\\leftharpoondown$",  # LEFTWARDS HARPOON WITH BARB DOWNWARDS
        "\u21BE": "$\\upharpoonright$",  # UPWARDS HARPOON WITH BARB RIGHTWARDS
        "\u21BF": "$\\upharpoonleft$",  # UPWARDS HARPOON WITH BARB LEFTWARDS
        "\u21C0": "$\\rightharpoonup$",  # RIGHTWARDS HARPOON WITH BARB UPWARDS
        "\u21C1": "$\\rightharpoondown$",  # RIGHTWARDS HARPOON WITH BARB DOWNWARDS
        "\u21C2": "$\\downharpoonright$",  # DOWNWARDS HARPOON WITH BARB RIGHTWARDS
        "\u21C3": "$\\downharpoonleft$",  # DOWNWARDS HARPOON WITH BARB LEFTWARDS
        "\u21C4": "$\\rightleftarrows$",  # RIGHTWARDS ARROW OVER LEFTWARDS ARROW
        "\u21C5": "$\\updownarrows$",  # UPWARDS ARROW LEFTWARDS OF DOWNWARDS ARROW
        "\u21C6": "$\\leftrightarrows$",  # LEFTWARDS ARROW OVER RIGHTWARDS ARROW
        "\u21C7": "$\\leftleftarrows$",  # LEFTWARDS PAIRED ARROWS
        "\u21C8": "$\\upuparrows$",  # UPWARDS PAIRED ARROWS
        "\u21C9": "$\\rightrightarrows$",  # RIGHTWARDS PAIRED ARROWS
        "\u21CA": "$\\downdownarrows$",  # DOWNWARDS PAIRED ARROWS
        "\u21CB": "$\\leftrightharpoons$",  # LEFTWARDS HARPOON OVER RIGHTWARDS HARPOON
        "\u21CC": "$\\rightleftharpoons$",  # RIGHTWARDS HARPOON OVER LEFTWARDS HARPOON
        "\u21CD": "$\\nLeftarrow$",  # LEFTWARDS DOUBLE ARROW WITH STROKE
        "\u21CE": "$\\nLeftrightarrow$",  # LEFT RIGHT DOUBLE ARROW WITH STROKE
        "\u21CF": "$\\nRightarrow$",  # RIGHTWARDS DOUBLE ARROW WITH STROKE
        "\u21D0": "$\\Leftarrow$",  # LEFTWARDS DOUBLE ARROW
        "\u21D1": "$\\Uparrow$",  # UPWARDS DOUBLE ARROW
        "\u21D2": "$\\Rightarrow$",  # RIGHTWARDS DOUBLE ARROW
        "\u21D3": "$\\Downarrow$",  # DOWNWARDS DOUBLE ARROW
        "\u21D4": "$\\Leftrightarrow$",  # LEFT RIGHT DOUBLE ARROW
        "\u21D5": "$\\Updownarrow$",  # UP DOWN DOUBLE ARROW
        "\u21DA": "$\\Lleftarrow$",  # LEFTWARDS TRIPLE ARROW
        "\u21DB": "$\\Rrightarrow$",  # RIGHTWARDS TRIPLE ARROW
        "\u21DD": "$\\rightsquigarrow$",  # RIGHTWARDS SQUIGGLE ARROW
        "\u21F5": "$\\downuparrows$",  # DOWNWARDS ARROW LEFTWARDS OF UPWARDS ARROW
        "\u2200": "$\\forall$",  # FOR ALL
        "\u2201": "$\\complement$",  # COMPLEMENT
        "\u2202": "$\\partial$",  # PARTIAL DIFFERENTIAL
        "\u2203": "$\\exists$",  # THERE EXISTS
        "\u2204": "$\\nexists$",  # THERE DOES NOT EXIST
        "\u2205": "$\\varnothing$",  # EMPTY SET
        "\u2207": "$\\nabla$",  # NABLA
        "\u2208": "$\\in$",  # ELEMENT OF
        "\u2209": "$\\notin$",  # NOT AN ELEMENT OF
        "\u220B": "$\\ni$",  # CONTAINS AS MEMBER
        "\u220C": "$\\nni$",  # DOES NOT CONTAIN AS MEMBER
        "\u220F": "$\\prod$",  # N-ARY PRODUCT
        "\u2210": "$\\coprod$",  # N-ARY COPRODUCT
        "\u2211": "$\\sum$",  # N-ARY SUMMATION
        "\u2212": "-",  # MINUS SIGN
        "\u2213": "$\\mp$",  # MINUS-OR-PLUS SIGN
        "\u2214": "$\\dotplus$",  # DOT PLUS
        "\u2216": "$\\smallsetminus$",  # SET MINUS
        "\u2217": "$\\ast$",  # ASTERISK OPERATOR
        "\u2218": "$\\vysmwhtcircle$",  # RING OPERATOR
        "\u2219": "$\\vysmblkcircle$",  # BULLET OPERATOR
        "\u221A": "$\\sqrt$",  # SQUARE ROOT
        "\u221D": "$\\propto$",  # PROPORTIONAL TO
        "\u221E": "$\\infty$",  # INFINITY
        "\u221F": "$\\rightangle$",  # RIGHT ANGLE
        "\u2220": "$\\angle$",  # ANGLE
        "\u2221": "$\\measuredangle$",  # MEASURED ANGLE
        "\u2222": "$\\sphericalangle$",  # SPHERICAL ANGLE
        "\u2223": "$\\mid$",  # DIVIDES
        "\u2224": "$\\nmid$",  # DOES NOT DIVIDE
        "\u2225": "$\\parallel$",  # PARALLEL TO
        "\u2226": "$\\nparallel$",  # NOT PARALLEL TO
        "\u2227": "$\\wedge$",  # LOGICAL AND
        "\u2228": "$\\vee$",  # LOGICAL OR
        "\u2229": "$\\cap$",  # INTERSECTION
        "\u222A": "$\\cup$",  # UNION
        "\u222B": "$\\int$",  # INTEGRAL
        "\u222C": "$\\iint$",  # DOUBLE INTEGRAL
        "\u222D": "$\\iiint$",  # TRIPLE INTEGRAL
        "\u222E": "$\\oint$",  # CONTOUR INTEGRAL
        "\u222F": "$\\oiint$",  # SURFACE INTEGRAL
        "\u2230": "$\\oiiint$",  # VOLUME INTEGRAL
        "\u2231": "$\\intclockwise$",  # CLOCKWISE INTEGRAL
        "\u2232": "$\\varointclockwise$",  # CLOCKWISE CONTOUR INTEGRAL
        "\u2233": "$\\ointctrclockwise$",  # ANTICLOCKWISE CONTOUR INTEGRAL
        "\u2234": "$\\therefore$",  # THEREFORE
        "\u2235": "$\\because$",  # BECAUSE
        "\u2237": "$\\Colon$",  # PROPORTION
        "\u2238": "$\\dotminus$",  # DOT MINUS
        "\u223A": "$\\dotsminusdots$",  # GEOMETRIC PROPORTION
        "\u223B": "$\\kernelcontraction$",  # HOMOTHETIC
        "\u223C": "$\\sim$",  # TILDE OPERATOR
        "\u223D": "$\\backsim$",  # REVERSED TILDE
        "\u223E": "$\\invlazys$",  # INVERTED LAZY S
        "\u2240": "$\\wr$",  # WREATH PRODUCT
        "\u2241": "$\\nsim$",  # NOT TILDE
        "\u2242": "$\\eqsim$",  # MINUS TILDE
        "\u2243": "$\\simeq$",  # ASYMPTOTICALLY EQUAL TO
        "\u2244": "$\\nsime$",  # NOT ASYMPTOTICALLY EQUAL TO
        "\u2245": "$\\cong$",  # APPROXIMATELY EQUAL TO
        "\u2246": "$\\simneqq$",  # APPROXIMATELY BUT NOT ACTUALLY EQUAL TO
        "\u2247": "$\\ncong$",  # NEITHER APPROXIMATELY NOR ACTUALLY EQUAL TO
        "\u2248": "$\\approx$",  # ALMOST EQUAL TO
        "\u2249": "$\\napprox$",  # NOT ALMOST EQUAL TO
        "\u224A": "$\\approxeq$",  # ALMOST EQUAL OR EQUAL TO
        "\u224B": "$\\approxident$",  # TRIPLE TILDE
        "\u224C": "$\\backcong$",  # ALL EQUAL TO
        "\u224D": "$\\asymp$",  # EQUIVALENT TO
        "\u224E": "$\\Bumpeq$",  # GEOMETRICALLY EQUIVALENT TO
        "\u224F": "$\\bumpeq$",  # DIFFERENCE BETWEEN
        "\u2250": "$\\doteq$",  # APPROACHES THE LIMIT
        "\u2251": "$\\Doteq$",  # GEOMETRICALLY EQUAL TO
        "\u2252": "$\\fallingdotseq$",  # APPROXIMATELY EQUAL TO OR THE IMAGE OF
        "\u2253": "$\\risingdotseq$",  # IMAGE OF OR APPROXIMATELY EQUAL TO
        "\u2254": ":=",  # COLON EQUALS
        "\u2255": "$\\eqcolon$",  # EQUALS COLON
        "\u2256": "$\\eqcirc$",  # RING IN EQUAL TO
        "\u2257": "$\\circeq$",  # RING EQUAL TO
        "\u2259": "$\\wedgeq$",  # ESTIMATES
        "\u225A": "$\\veeeq$",  # EQUIANGULAR TO
        "\u225B": "$\\stareq$",  # STAR EQUALS
        "\u225C": "$\\triangleq$",  # DELTA EQUAL TO
        "\u225F": "$\\questeq$",  # QUESTIONED EQUAL TO
        "\u2260": "$\\ne$",  # NOT EQUAL TO
        "\u2261": "$\\equiv$",  # IDENTICAL TO
        "\u2262": "$\\nequiv$",  # NOT IDENTICAL TO
        "\u2264": "$\\leq$",  # LESS-THAN OR EQUAL TO
        "\u2265": "$\\geq$",  # GREATER-THAN OR EQUAL TO
        "\u2266": "$\\leqq$",  # LESS-THAN OVER EQUAL TO
        "\u2267": "$\\geqq$",  # GREATER-THAN OVER EQUAL TO
        "\u2268": "$\\lneqq$",  # LESS-THAN BUT NOT EQUAL TO
        "\u2269": "$\\gneqq$",  # GREATER-THAN BUT NOT EQUAL TO
        "\u226A": "$\\ll$",  # MUCH LESS-THAN
        "\u226B": "$\\gg$",  # MUCH GREATER-THAN
        "\u226C": "$\\between$",  # BETWEEN
        "\u226D": "$\\nasymp$",  # NOT EQUIVALENT TO
        "\u226E": "$\\nless$",  # NOT LESS-THAN
        "\u226F": "$\\ngtr$",  # NOT GREATER-THAN
        "\u2270": "$\\nleq$",  # NEITHER LESS-THAN NOR EQUAL TO
        "\u2271": "$\\ngeq$",  # NEITHER GREATER-THAN NOR EQUAL TO
        "\u2272": "$\\lesssim$",  # LESS-THAN OR EQUIVALENT TO
        "\u2273": "$\\gtrsim$",  # GREATER-THAN OR EQUIVALENT TO
        "\u2274": "$\\nlesssim$",  # NEITHER LESS-THAN NOR EQUIVALENT TO
        "\u2275": "$\\ngtrsim$",  # NEITHER GREATER-THAN NOR EQUIVALENT TO
        "\u2276": "$\\lessgtr$",  # LESS-THAN OR GREATER-THAN
        "\u2277": "$\\gtrless$",  # GREATER-THAN OR LESS-THAN
        "\u2278": "$\\nlessgtr$",  # NEITHER LESS-THAN NOR GREATER-THAN
        "\u2279": "$\\ngtrless$",  # NEITHER GREATER-THAN NOR LESS-THAN
        "\u227A": "$\\prec$",  # PRECEDES
        "\u227B": "$\\succ$",  # SUCCEEDS
        "\u227C": "$\\preccurlyeq$",  # PRECEDES OR EQUAL TO
        "\u227D": "$\\succcurlyeq$",  # SUCCEEDS OR EQUAL TO
        "\u227E": "$\\precsim$",  # PRECEDES OR EQUIVALENT TO
        "\u227F": "$\\succsim$",  # SUCCEEDS OR EQUIVALENT TO
        "\u2280": "$\\nprec$",  # DOES NOT PRECEDE
        "\u2281": "$\\nsucc$",  # DOES NOT SUCCEED
        "\u2282": "$\\subset$",  # SUBSET OF
        "\u2283": "$\\supset$",  # SUPERSET OF
        "\u2284": "$\\nsubset$",  # NOT A SUBSET OF
        "\u2285": "$\\nsupset$",  # NOT A SUPERSET OF
        "\u2286": "$\\subseteq$",  # SUBSET OF OR EQUAL TO
        "\u2287": "$\\supseteq$",  # SUPERSET OF OR EQUAL TO
        "\u2288": "$\\nsubseteq$",  # NEITHER A SUBSET OF NOR EQUAL TO
        "\u2289": "$\\nsupseteq$",  # NEITHER A SUPERSET OF NOR EQUAL TO
        "\u228A": "$\\subsetneq$",  # SUBSET OF WITH NOT EQUAL TO
        "\u228B": "$\\supsetneq$",  # SUPERSET OF WITH NOT EQUAL TO
        "\u228E": "$\\uplus$",  # MULTISET UNION
        "\u228F": "$\\sqsubset$",  # SQUARE IMAGE OF
        "\u2290": "$\\sqsupset$",  # SQUARE ORIGINAL OF
        "\u2291": "$\\sqsubseteq$",  # SQUARE IMAGE OF OR EQUAL TO
        "\u2292": "$\\sqsupseteq$",  # SQUARE ORIGINAL OF OR EQUAL TO
        "\u2293": "$\\sqcap$",  # SQUARE CAP
        "\u2294": "$\\sqcup$",  # SQUARE CUP
        "\u2295": "$\\oplus$",  # CIRCLED PLUS
        "\u2296": "$\\ominus$",  # CIRCLED MINUS
        "\u2297": "$\\otimes$",  # CIRCLED TIMES
        "\u2298": "$\\oslash$",  # CIRCLED DIVISION SLASH
        "\u2299": "$\\odot$",  # CIRCLED DOT OPERATOR
        "\u229A": "$\\circledcirc$",  # CIRCLED RING OPERATOR
        "\u229B": "$\\circledast$",  # CIRCLED ASTERISK OPERATOR
        "\u229D": "$\\circleddash$",  # CIRCLED DASH
        "\u229E": "$\\boxplus$",  # SQUARED PLUS
        "\u229F": "$\\boxminus$",  # SQUARED MINUS
        "\u22A0": "$\\boxtimes$",  # SQUARED TIMES
        "\u22A1": "$\\boxdot$",  # SQUARED DOT OPERATOR
        "\u22A2": "$\\vdash$",  # RIGHT TACK
        "\u22A3": "$\\dashv$",  # LEFT TACK
        "\u22A4": "$\\top$",  # DOWN TACK
        "\u22A5": "$\\bot$",  # UP TACK
        "\u22A7": "$\\models$",  # MODELS
        "\u22A8": "$\\vDash$",  # TRUE
        "\u22A9": "$\\Vdash$",  # FORCES
        "\u22AA": "$\\Vvdash$",  # TRIPLE VERTICAL BAR RIGHT TURNSTILE
        "\u22AB": "$\\VDash$",  # DOUBLE VERTICAL BAR DOUBLE RIGHT TURNSTILE
        "\u22AC": "$\\nvdash$",  # DOES NOT PROVE
        "\u22AD": "$\\nvDash$",  # NOT TRUE
        "\u22AE": "$\\nVdash$",  # DOES NOT FORCE
        "\u22AF": "$\\nVDash$",  # NEGATED DOUBLE VERTICAL BAR DOUBLE RIGHT TURNSTILE
        "\u22B2": "$\\vartriangleleft$",  # NORMAL SUBGROUP OF
        "\u22B3": "$\\vartriangleright$",  # CONTAINS AS NORMAL SUBGROUP
        "\u22B4": "$\\trianglelefteq$",  # NORMAL SUBGROUP OF OR EQUAL TO
        "\u22B5": "$\\trianglerighteq$",  # CONTAINS AS NORMAL SUBGROUP OR EQUAL TO
        "\u22B6": "$\\origof$",  # ORIGINAL OF
        "\u22B7": "$\\imageof$",  # IMAGE OF
        "\u22B8": "$\\multimap$",  # MULTIMAP
        "\u22B9": "$\\hermitmatrix$",  # HERMITIAN CONJUGATE MATRIX
        "\u22BA": "$\\intercal$",  # INTERCALATE
        "\u22BB": "$\\veebar$",  # XOR
        "\u22BE": "$\\measuredrightangle$",  # RIGHT ANGLE WITH ARC
        "\u22C0": "$\\bigwedge$",  # N-ARY LOGICAL AND
        "\u22C1": "$\\bigvee$",  # N-ARY LOGICAL OR
        "\u22C2": "$\\bigcap$",  # N-ARY INTERSECTION
        "\u22C3": "$\\bigcup$",  # N-ARY UNION
        "\u22C4": "$\\smwhtdiamond$",  # DIAMOND OPERATOR
        "\u22C5": "$\\cdot$",  # DOT OPERATOR
        "\u22C6": "$\\star$",  # STAR OPERATOR
        "\u22C7": "$\\divideontimes$",  # DIVISION TIMES
        "\u22C8": "$\\bowtie$",  # BOWTIE
        "\u22C9": "$\\ltimes$",  # LEFT NORMAL FACTOR SEMIDIRECT PRODUCT
        "\u22CA": "$\\rtimes$",  # RIGHT NORMAL FACTOR SEMIDIRECT PRODUCT
        "\u22CB": "$\\leftthreetimes$",  # LEFT SEMIDIRECT PRODUCT
        "\u22CC": "$\\rightthreetimes$",  # RIGHT SEMIDIRECT PRODUCT
        "\u22CD": "$\\backsimeq$",  # REVERSED TILDE EQUALS
        "\u22CE": "$\\curlyvee$",  # CURLY LOGICAL OR
        "\u22CF": "$\\curlywedge$",  # CURLY LOGICAL AND
        "\u22D0": "$\\Subset$",  # DOUBLE SUBSET
        "\u22D1": "$\\Supset$",  # DOUBLE SUPERSET
        "\u22D2": "$\\Cap$",  # DOUBLE INTERSECTION
        "\u22D3": "$\\Cup$",  # DOUBLE UNION
        "\u22D4": "$\\pitchfork$",  # PITCHFORK
        "\u22D6": "$\\lessdot$",  # LESS-THAN WITH DOT
        "\u22D7": "$\\gtrdot$",  # GREATER-THAN WITH DOT
        "\u22D8": "$\\lll$",  # VERY MUCH LESS-THAN
        "\u22D9": "$\\ggg$",  # VERY MUCH GREATER-THAN
        "\u22DA": "$\\lesseqgtr$",  # LESS-THAN EQUAL TO OR GREATER-THAN
        "\u22DB": "$\\gtreqless$",  # GREATER-THAN EQUAL TO OR LESS-THAN
        "\u22DE": "$\\curlyeqprec$",  # EQUAL TO OR PRECEDES
        "\u22DF": "$\\curlyeqsucc$",  # EQUAL TO OR SUCCEEDS
        "\u22E2": "$\\nsqsubseteq$",  # NOT SQUARE IMAGE OF OR EQUAL TO
        "\u22E3": "$\\nsqsupseteq$",  # NOT SQUARE ORIGINAL OF OR EQUAL TO
        "\u22E5": "$\\sqsupsetneq$",  # SQUARE ORIGINAL OF OR NOT EQUAL TO
        "\u22E6": "$\\lnsim$",  # LESS-THAN BUT NOT EQUIVALENT TO
        "\u22E7": "$\\gnsim$",  # GREATER-THAN BUT NOT EQUIVALENT TO
        "\u22E8": "$\\precnsim$",  # PRECEDES BUT NOT EQUIVALENT TO
        "\u22E9": "$\\succnsim$",  # SUCCEEDS BUT NOT EQUIVALENT TO
        "\u22EA": "$\\nvartriangleleft$",  # NOT NORMAL SUBGROUP OF
        "\u22EB": "$\\nvartriangleright$",  # DOES NOT CONTAIN AS NORMAL SUBGROUP
        "\u22EC": "$\\ntrianglelefteq$",  # NOT NORMAL SUBGROUP OF OR EQUAL TO
        "\u22ED": "$\\ntrianglerighteq$",  # DOES NOT CONTAIN AS NORMAL SUBGROUP OR EQUAL
        "\u22EE": "$\\vdots$",  # VERTICAL ELLIPSIS
        "\u22EF": "$\\unicodecdots$",  # MIDLINE HORIZONTAL ELLIPSIS
        "\u22F0": "$\\adots$",  # UP RIGHT DIAGONAL ELLIPSIS
        "\u22F1": "$\\ddots$",  # DOWN RIGHT DIAGONAL ELLIPSIS
        "\u2305": "{\\barwedge}",  # PROJECTIVE
        "\u2306": "$\\vardoublebarwedge$",  # PERSPECTIVE
        "\u2308": "$\\lceil$",  # LEFT CEILING
        "\u2309": "$\\rceil$",  # RIGHT CEILING
        "\u230A": "$\\lfloor$",  # LEFT FLOOR
        "\u230B": "$\\rfloor$",  # RIGHT FLOOR
        "\u2315": "{\\recorder}",  # TELEPHONE RECORDER
        "\u231C": "$\\ulcorner$",  # TOP LEFT CORNER
        "\u231D": "$\\urcorner$",  # TOP RIGHT CORNER
        "\u231E": "$\\llcorner$",  # BOTTOM LEFT CORNER
        "\u231F": "$\\lrcorner$",  # BOTTOM RIGHT CORNER
        "\u2322": "$\\frown$",  # FROWN
        "\u2323": "$\\smile$",  # SMILE
        "\u233D": "$\\obar$",  # APL FUNCTIONAL SYMBOL CIRCLE STILE
        "\u23A3": "$\\lbracklend$",  # LEFT SQUARE BRACKET LOWER CORNER
        "\u23B0": "$\\lmoustache$",  # UPPER LEFT OR LOWER RIGHT CURLY BRACKET SECTION
        "\u23B1": "$\\rmoustache$",  # UPPER RIGHT OR LOWER LEFT CURLY BRACKET SECTION
        "\u2423": "{\\textvisiblespace}",  # OPEN BOX
        "\u2460": "{\\ding{172}}",  # CIRCLED DIGIT ONE
        "\u2461": "{\\ding{173}}",  # CIRCLED DIGIT TWO
        "\u2462": "{\\ding{174}}",  # CIRCLED DIGIT THREE
        "\u2463": "{\\ding{175}}",  # CIRCLED DIGIT FOUR
        "\u2464": "{\\ding{176}}",  # CIRCLED DIGIT FIVE
        "\u2465": "{\\ding{177}}",  # CIRCLED DIGIT SIX
        "\u2466": "{\\ding{178}}",  # CIRCLED DIGIT SEVEN
        "\u2467": "{\\ding{179}}",  # CIRCLED DIGIT EIGHT
        "\u2468": "{\\ding{180}}",  # CIRCLED DIGIT NINE
        "\u2469": "{\\ding{181}}",  # CIRCLED NUMBER TEN
        "\u24C8": "{\\circledS}",  # CIRCLED LATIN CAPITAL LETTER S
        "\u2506": "$\\bdtriplevdash$",  # BOX DRAWINGS LIGHT TRIPLE DASH VERTICAL
        "\u2519": "{\\Elzsqfnw}",  # BOX DRAWINGS UP LIGHT AND LEFT HEAVY
        "\u2571": "{\\diagup}",  # BOX DRAWINGS LIGHT DIAGONAL UPPER RIGHT TO LOWER LEFT
        "\u25A0": "{\\ding{110}}",  # BLACK SQUARE
        "\u25A1": "$\\mdlgwhtsquare$",  # WHITE SQUARE
        "\u25AA": "$\\smblksquare$",  # BLACK SMALL SQUARE
        "\u25AD": "$\\hrectangle$",  # WHITE RECTANGLE
        "\u25AF": "$\\vrectangle$",  # WHITE VERTICAL RECTANGLE
        "\u25B1": "$\\parallelogram$",  # WHITE PARALLELOGRAM
        "\u25B2": "{\\ding{115}}",  # BLACK UP-POINTING TRIANGLE
        "\u25B3": "$\\bigtriangleup$",  # WHITE UP-POINTING TRIANGLE
        "\u25B4": "$\\blacktriangle$",  # BLACK UP-POINTING SMALL TRIANGLE
        "\u25B5": "$\\vartriangle$",  # WHITE UP-POINTING SMALL TRIANGLE
        "\u25B8": "$\\smallblacktriangleright$",  # BLACK RIGHT-POINTING SMALL TRIANGLE
        "\u25B9": "$\\smalltriangleright$",  # WHITE RIGHT-POINTING SMALL TRIANGLE
        "\u25BC": "{\\ding{116}}",  # BLACK DOWN-POINTING TRIANGLE
        "\u25BD": "$\\bigtriangledown$",  # WHITE DOWN-POINTING TRIANGLE
        "\u25BE": "$\\blacktriangledown$",  # BLACK DOWN-POINTING SMALL TRIANGLE
        "\u25BF": "$\\triangledown$",  # WHITE DOWN-POINTING SMALL TRIANGLE
        "\u25C2": "$\\smallblacktriangleleft$",  # BLACK LEFT-POINTING SMALL TRIANGLE
        "\u25C3": "$\\smalltriangleleft$",  # WHITE LEFT-POINTING SMALL TRIANGLE
        "\u25C6": "{\\ding{117}}",  # BLACK DIAMOND
        "\u25CA": "$\\mdlgwhtlozenge$",  # LOZENGE
        "\u25CB": "$\\mdlgwhtcircle$",  # WHITE CIRCLE
        "\u25CF": "{\\ding{108}}",  # BLACK CIRCLE
        "\u25D0": "$\\circlelefthalfblack$",  # CIRCLE WITH LEFT HALF BLACK
        "\u25D1": "$\\circlerighthalfblack$",  # CIRCLE WITH RIGHT HALF BLACK
        "\u25D2": "$\\circlebottomhalfblack$",  # CIRCLE WITH LOWER HALF BLACK
        "\u25D7": "{\\ding{119}}",  # RIGHT HALF BLACK CIRCLE
        "\u25D8": "$\\inversebullet$",  # INVERSE BULLET
        "\u25E7": "$\\squareleftblack$",  # SQUARE WITH LEFT HALF BLACK
        "\u25E8": "$\\squarerightblack$",  # SQUARE WITH RIGHT HALF BLACK
        "\u25EA": "$\\squarelrblack$",  # SQUARE WITH LOWER RIGHT DIAGONAL HALF BLACK
        "\u25EF": "$\\lgwhtcircle$",  # LARGE CIRCLE
        "\u2605": "{\\ding{72}}",  # BLACK STAR
        "\u2606": "{\\ding{73}}",  # WHITE STAR
        "\u260E": "{\\ding{37}}",  # BLACK TELEPHONE
        "\u261B": "{\\ding{42}}",  # BLACK RIGHT POINTING INDEX
        "\u261E": "{\\ding{43}}",  # WHITE RIGHT POINTING INDEX
        "\u263E": "{\\rightmoon}",  # LAST QUARTER MOON
        "\u263F": "{\\mercury}",  # MERCURY
        "\u2640": "{\\venus}",  # FEMALE SIGN
        "\u2642": "{\\male}",  # MALE SIGN
        "\u2643": "{\\jupiter}",  # JUPITER
        "\u2644": "{\\saturn}",  # SATURN
        "\u2645": "{\\uranus}",  # URANUS
        "\u2646": "{\\neptune}",  # NEPTUNE
        "\u2647": "{\\pluto}",  # PLUTO
        "\u2648": "{\\aries}",  # ARIES
        "\u2649": "{\\taurus}",  # TAURUS
        "\u264A": "{\\gemini}",  # GEMINI
        "\u264B": "{\\cancer}",  # CANCER
        "\u264C": "{\\leo}",  # LEO
        "\u264D": "{\\virgo}",  # VIRGO
        "\u264E": "{\\libra}",  # LIBRA
        "\u264F": "{\\scorpio}",  # SCORPIUS
        "\u2650": "{\\sagittarius}",  # SAGITTARIUS
        "\u2651": "{\\capricornus}",  # CAPRICORN
        "\u2652": "{\\aquarius}",  # AQUARIUS
        "\u2653": "{\\pisces}",  # PISCES
        "\u2660": "{\\ding{171}}",  # BLACK SPADE SUIT
        "\u2662": "$\\diamondsuit$",  # WHITE DIAMOND SUIT
        "\u2663": "{\\ding{168}}",  # BLACK CLUB SUIT
        "\u2665": "{\\ding{170}}",  # BLACK HEART SUIT
        "\u2666": "{\\ding{169}}",  # BLACK DIAMOND SUIT
        "\u2669": "{\\quarternote}",  # QUARTER NOTE
        "\u266A": "{\\eighthnote}",  # EIGHTH NOTE
        "\u266D": "$\\flat$",  # MUSIC FLAT SIGN
        "\u266E": "$\\natural$",  # MUSIC NATURAL SIGN
        "\u266F": "$\\sharp$",  # MUSIC SHARP SIGN
        "\u2701": "{\\ding{33}}",  # UPPER BLADE SCISSORS
        "\u2702": "{\\ding{34}}",  # BLACK SCISSORS
        "\u2703": "{\\ding{35}}",  # LOWER BLADE SCISSORS
        "\u2704": "{\\ding{36}}",  # WHITE SCISSORS
        "\u2706": "{\\ding{38}}",  # TELEPHONE LOCATION SIGN
        "\u2707": "{\\ding{39}}",  # TAPE DRIVE
        "\u2708": "{\\ding{40}}",  # AIRPLANE
        "\u2709": "{\\ding{41}}",  # ENVELOPE
        "\u270C": "{\\ding{44}}",  # VICTORY HAND
        "\u270D": "{\\ding{45}}",  # WRITING HAND
        "\u270E": "{\\ding{46}}",  # LOWER RIGHT PENCIL
        "\u270F": "{\\ding{47}}",  # PENCIL
        "\u2710": "{\\ding{48}}",  # UPPER RIGHT PENCIL
        "\u2711": "{\\ding{49}}",  # WHITE NIB
        "\u2712": "{\\ding{50}}",  # BLACK NIB
        "\u2713": "{\\ding{51}}",  # CHECK MARK
        "\u2714": "{\\ding{52}}",  # HEAVY CHECK MARK
        "\u2715": "{\\ding{53}}",  # MULTIPLICATION X
        "\u2716": "{\\ding{54}}",  # HEAVY MULTIPLICATION X
        "\u2717": "{\\ding{55}}",  # BALLOT X
        "\u2718": "{\\ding{56}}",  # HEAVY BALLOT X
        "\u2719": "{\\ding{57}}",  # OUTLINED GREEK CROSS
        "\u271A": "{\\ding{58}}",  # HEAVY GREEK CROSS
        "\u271B": "{\\ding{59}}",  # OPEN CENTRE CROSS
        "\u271C": "{\\ding{60}}",  # HEAVY OPEN CENTRE CROSS
        "\u271D": "{\\ding{61}}",  # LATIN CROSS
        "\u271E": "{\\ding{62}}",  # SHADOWED WHITE LATIN CROSS
        "\u271F": "{\\ding{63}}",  # OUTLINED LATIN CROSS
        "\u2720": "{\\ding{64}}",  # MALTESE CROSS
        "\u2721": "{\\ding{65}}",  # STAR OF DAVID
        "\u2722": "{\\ding{66}}",  # FOUR TEARDROP-SPOKED ASTERISK
        "\u2723": "{\\ding{67}}",  # FOUR BALLOON-SPOKED ASTERISK
        "\u2724": "{\\ding{68}}",  # HEAVY FOUR BALLOON-SPOKED ASTERISK
        "\u2725": "{\\ding{69}}",  # FOUR CLUB-SPOKED ASTERISK
        "\u2726": "{\\ding{70}}",  # BLACK FOUR POINTED STAR
        "\u2727": "{\\ding{71}}",  # WHITE FOUR POINTED STAR
        "\u2729": "{\\ding{73}}",  # STRESS OUTLINED WHITE STAR
        "\u272A": "{\\ding{74}}",  # CIRCLED WHITE STAR
        "\u272B": "{\\ding{75}}",  # OPEN CENTRE BLACK STAR
        "\u272C": "{\\ding{76}}",  # BLACK CENTRE WHITE STAR
        "\u272D": "{\\ding{77}}",  # OUTLINED BLACK STAR
        "\u272E": "{\\ding{78}}",  # HEAVY OUTLINED BLACK STAR
        "\u272F": "{\\ding{79}}",  # PINWHEEL STAR
        "\u2730": "{\\ding{80}}",  # SHADOWED WHITE STAR
        "\u2731": "{\\ding{81}}",  # HEAVY ASTERISK
        "\u2732": "{\\ding{82}}",  # OPEN CENTRE ASTERISK
        "\u2733": "{\\ding{83}}",  # EIGHT SPOKED ASTERISK
        "\u2734": "{\\ding{84}}",  # EIGHT POINTED BLACK STAR
        "\u2735": "{\\ding{85}}",  # EIGHT POINTED PINWHEEL STAR
        "\u2736": "{\\ding{86}}",  # SIX POINTED BLACK STAR
        "\u2737": "{\\ding{87}}",  # EIGHT POINTED RECTILINEAR BLACK STAR
        "\u2738": "{\\ding{88}}",  # HEAVY EIGHT POINTED RECTILINEAR BLACK STAR
        "\u2739": "{\\ding{89}}",  # TWELVE POINTED BLACK STAR
        "\u273A": "{\\ding{90}}",  # SIXTEEN POINTED ASTERISK
        "\u273B": "{\\ding{91}}",  # TEARDROP-SPOKED ASTERISK
        "\u273C": "{\\ding{92}}",  # OPEN CENTRE TEARDROP-SPOKED ASTERISK
        "\u273D": "{\\ding{93}}",  # HEAVY TEARDROP-SPOKED ASTERISK
        "\u273E": "{\\ding{94}}",  # SIX PETALLED BLACK AND WHITE FLORETTE
        "\u273F": "{\\ding{95}}",  # BLACK FLORETTE
        "\u2740": "{\\ding{96}}",  # WHITE FLORETTE
        "\u2741": "{\\ding{97}}",  # EIGHT PETALLED OUTLINED BLACK FLORETTE
        "\u2742": "{\\ding{98}}",  # CIRCLED OPEN CENTRE EIGHT POINTED STAR
        "\u2743": "{\\ding{99}}",  # HEAVY TEARDROP-SPOKED PINWHEEL ASTERISK
        "\u2744": "{\\ding{100}}",  # SNOWFLAKE
        "\u2745": "{\\ding{101}}",  # TIGHT TRIFOLIATE SNOWFLAKE
        "\u2746": "{\\ding{102}}",  # HEAVY CHEVRON SNOWFLAKE
        "\u2747": "{\\ding{103}}",  # SPARKLE
        "\u2748": "{\\ding{104}}",  # HEAVY SPARKLE
        "\u2749": "{\\ding{105}}",  # BALLOON-SPOKED ASTERISK
        "\u274A": "{\\ding{106}}",  # EIGHT TEARDROP-SPOKED PROPELLER ASTERISK
        "\u274B": "{\\ding{107}}",  # HEAVY EIGHT TEARDROP-SPOKED PROPELLER ASTERISK
        "\u274D": "{\\ding{109}}",  # SHADOWED WHITE CIRCLE
        "\u274F": "{\\ding{111}}",  # LOWER RIGHT DROP-SHADOWED WHITE SQUARE
        "\u2750": "{\\ding{112}}",  # UPPER RIGHT DROP-SHADOWED WHITE SQUARE
        "\u2751": "{\\ding{113}}",  # LOWER RIGHT SHADOWED WHITE SQUARE
        "\u2752": "{\\ding{114}}",  # UPPER RIGHT SHADOWED WHITE SQUARE
        "\u2756": "{\\ding{118}}",  # BLACK DIAMOND MINUS WHITE X
        "\u2758": "{\\ding{120}}",  # LIGHT VERTICAL BAR
        "\u2759": "{\\ding{121}}",  # MEDIUM VERTICAL BAR
        "\u275A": "{\\ding{122}}",  # HEAVY VERTICAL BAR
        "\u275B": "{\\ding{123}}",  # HEAVY SINGLE TURNED COMMA QUOTATION MARK ORNAMENT
        "\u275C": "{\\ding{124}}",  # HEAVY SINGLE COMMA QUOTATION MARK ORNAMENT
        "\u275D": "{\\ding{125}}",  # HEAVY DOUBLE TURNED COMMA QUOTATION MARK ORNAMENT
        "\u275E": "{\\ding{126}}",  # HEAVY DOUBLE COMMA QUOTATION MARK ORNAMENT
        "\u2761": "{\\ding{161}}",  # CURVED STEM PARAGRAPH SIGN ORNAMENT
        "\u2762": "{\\ding{162}}",  # HEAVY EXCLAMATION MARK ORNAMENT
        "\u2763": "{\\ding{163}}",  # HEAVY HEART EXCLAMATION MARK ORNAMENT
        "\u2764": "{\\ding{164}}",  # HEAVY BLACK HEART
        "\u2765": "{\\ding{165}}",  # ROTATED HEAVY BLACK HEART BULLET
        "\u2766": "{\\ding{166}}",  # FLORAL HEART
        "\u2767": "{\\ding{167}}",  # ROTATED FLORAL HEART BULLET
        "\u2776": "{\\ding{182}}",  # DINGBAT NEGATIVE CIRCLED DIGIT ONE
        "\u2777": "{\\ding{183}}",  # DINGBAT NEGATIVE CIRCLED DIGIT TWO
        "\u2778": "{\\ding{184}}",  # DINGBAT NEGATIVE CIRCLED DIGIT THREE
        "\u2779": "{\\ding{185}}",  # DINGBAT NEGATIVE CIRCLED DIGIT FOUR
        "\u277A": "{\\ding{186}}",  # DINGBAT NEGATIVE CIRCLED DIGIT FIVE
        "\u277B": "{\\ding{187}}",  # DINGBAT NEGATIVE CIRCLED DIGIT SIX
        "\u277C": "{\\ding{188}}",  # DINGBAT NEGATIVE CIRCLED DIGIT SEVEN
        "\u277D": "{\\ding{189}}",  # DINGBAT NEGATIVE CIRCLED DIGIT EIGHT
        "\u277E": "{\\ding{190}}",  # DINGBAT NEGATIVE CIRCLED DIGIT NINE
        "\u277F": "{\\ding{191}}",  # DINGBAT NEGATIVE CIRCLED NUMBER TEN
        "\u2780": "{\\ding{192}}",  # DINGBAT CIRCLED SANS-SERIF DIGIT ONE
        "\u2781": "{\\ding{193}}",  # DINGBAT CIRCLED SANS-SERIF DIGIT TWO
        "\u2782": "{\\ding{194}}",  # DINGBAT CIRCLED SANS-SERIF DIGIT THREE
        "\u2783": "{\\ding{195}}",  # DINGBAT CIRCLED SANS-SERIF DIGIT FOUR
        "\u2784": "{\\ding{196}}",  # DINGBAT CIRCLED SANS-SERIF DIGIT FIVE
        "\u2785": "{\\ding{197}}",  # DINGBAT CIRCLED SANS-SERIF DIGIT SIX
        "\u2786": "{\\ding{198}}",  # DINGBAT CIRCLED SANS-SERIF DIGIT SEVEN
        "\u2787": "{\\ding{199}}",  # DINGBAT CIRCLED SANS-SERIF DIGIT EIGHT
        "\u2788": "{\\ding{200}}",  # DINGBAT CIRCLED SANS-SERIF DIGIT NINE
        "\u2789": "{\\ding{201}}",  # DINGBAT CIRCLED SANS-SERIF NUMBER TEN
        "\u278A": "{\\ding{202}}",  # DINGBAT NEGATIVE CIRCLED SANS-SERIF DIGIT ONE
        "\u278B": "{\\ding{203}}",  # DINGBAT NEGATIVE CIRCLED SANS-SERIF DIGIT TWO
        "\u278C": "{\\ding{204}}",  # DINGBAT NEGATIVE CIRCLED SANS-SERIF DIGIT THREE
        "\u278D": "{\\ding{205}}",  # DINGBAT NEGATIVE CIRCLED SANS-SERIF DIGIT FOUR
        "\u278E": "{\\ding{206}}",  # DINGBAT NEGATIVE CIRCLED SANS-SERIF DIGIT FIVE
        "\u278F": "{\\ding{207}}",  # DINGBAT NEGATIVE CIRCLED SANS-SERIF DIGIT SIX
        "\u2790": "{\\ding{208}}",  # DINGBAT NEGATIVE CIRCLED SANS-SERIF DIGIT SEVEN
        "\u2791": "{\\ding{209}}",  # DINGBAT NEGATIVE CIRCLED SANS-SERIF DIGIT EIGHT
        "\u2792": "{\\ding{210}}",  # DINGBAT NEGATIVE CIRCLED SANS-SERIF DIGIT NINE
        "\u2793": "{\\ding{211}}",  # DINGBAT NEGATIVE CIRCLED SANS-SERIF NUMBER TEN
        "\u2794": "{\\ding{212}}",  # HEAVY WIDE-HEADED RIGHTWARDS ARROW
        "\u2798": "{\\ding{216}}",  # HEAVY SOUTH EAST ARROW
        "\u2799": "{\\ding{217}}",  # HEAVY RIGHTWARDS ARROW
        "\u279A": "{\\ding{218}}",  # HEAVY NORTH EAST ARROW
        "\u279B": "{\\ding{219}}",  # DRAFTING POINT RIGHTWARDS ARROW
        "\u279C": "{\\ding{220}}",  # HEAVY ROUND-TIPPED RIGHTWARDS ARROW
        "\u279D": "{\\ding{221}}",  # TRIANGLE-HEADED RIGHTWARDS ARROW
        "\u279E": "{\\ding{222}}",  # HEAVY TRIANGLE-HEADED RIGHTWARDS ARROW
        "\u279F": "{\\ding{223}}",  # DASHED TRIANGLE-HEADED RIGHTWARDS ARROW
        "\u27A0": "{\\ding{224}}",  # HEAVY DASHED TRIANGLE-HEADED RIGHTWARDS ARROW
        "\u27A1": "{\\ding{225}}",  # BLACK RIGHTWARDS ARROW
        "\u27A2": "{\\ding{226}}",  # THREE-D TOP-LIGHTED RIGHTWARDS ARROWHEAD
        "\u27A3": "{\\ding{227}}",  # THREE-D BOTTOM-LIGHTED RIGHTWARDS ARROWHEAD
        "\u27A4": "{\\ding{228}}",  # BLACK RIGHTWARDS ARROWHEAD
        "\u27A5": "{\\ding{229}}",  # HEAVY BLACK CURVED DOWNWARDS AND RIGHTWARDS ARROW
        "\u27A6": "{\\ding{230}}",  # HEAVY BLACK CURVED UPWARDS AND RIGHTWARDS ARROW
        "\u27A7": "{\\ding{231}}",  # SQUAT BLACK RIGHTWARDS ARROW
        "\u27A8": "{\\ding{232}}",  # HEAVY CONCAVE-POINTED BLACK RIGHTWARDS ARROW
        "\u27A9": "{\\ding{233}}",  # RIGHT-SHADED WHITE RIGHTWARDS ARROW
        "\u27AA": "{\\ding{234}}",  # LEFT-SHADED WHITE RIGHTWARDS ARROW
        "\u27AB": "{\\ding{235}}",  # BACK-TILTED SHADOWED WHITE RIGHTWARDS ARROW
        "\u27AC": "{\\ding{236}}",  # FRONT-TILTED SHADOWED WHITE RIGHTWARDS ARROW
        "\u27AD": "{\\ding{237}}",  # HEAVY LOWER RIGHT-SHADOWED WHITE RIGHTWARDS ARROW
        "\u27AE": "{\\ding{238}}",  # HEAVY UPPER RIGHT-SHADOWED WHITE RIGHTWARDS ARROW
        "\u27AF": "{\\ding{239}}",  # NOTCHED LOWER RIGHT-SHADOWED WHITE RIGHTWARDS ARROW
        "\u27B1": "{\\ding{241}}",  # NOTCHED UPPER RIGHT-SHADOWED WHITE RIGHTWARDS ARROW
        "\u27B2": "{\\ding{242}}",  # CIRCLED HEAVY WHITE RIGHTWARDS ARROW
        "\u27B3": "{\\ding{243}}",  # WHITE-FEATHERED RIGHTWARDS ARROW
        "\u27B4": "{\\ding{244}}",  # BLACK-FEATHERED SOUTH EAST ARROW
        "\u27B5": "{\\ding{245}}",  # BLACK-FEATHERED RIGHTWARDS ARROW
        "\u27B6": "{\\ding{246}}",  # BLACK-FEATHERED NORTH EAST ARROW
        "\u27B7": "{\\ding{247}}",  # HEAVY BLACK-FEATHERED SOUTH EAST ARROW
        "\u27B8": "{\\ding{248}}",  # HEAVY BLACK-FEATHERED RIGHTWARDS ARROW
        "\u27B9": "{\\ding{249}}",  # HEAVY BLACK-FEATHERED NORTH EAST ARROW
        "\u27BA": "{\\ding{250}}",  # TEARDROP-BARBED RIGHTWARDS ARROW
        "\u27BB": "{\\ding{251}}",  # HEAVY TEARDROP-SHANKED RIGHTWARDS ARROW
        "\u27BC": "{\\ding{252}}",  # WEDGE-TAILED RIGHTWARDS ARROW
        "\u27BD": "{\\ding{253}}",  # HEAVY WEDGE-TAILED RIGHTWARDS ARROW
        "\u27BE": "{\\ding{254}}",  # OPEN-OUTLINED RIGHTWARDS ARROW
        "\u27E8": "{\\langle}",  # MATHEMATICAL LEFT ANGLE BRACKET
        "\u27E9": "{\\rangle}",  # MATHEMATICAL RIGHT ANGLE BRACKET
        "\u27F5": "$\\longleftarrow$",  # LONG LEFTWARDS ARROW
        "\u27F6": "$\\longrightarrow$",  # LONG RIGHTWARDS ARROW
        "\u27F7": "$\\longleftrightarrow$",  # LONG LEFT RIGHT ARROW
        "\u27F8": "$\\Longleftarrow$",  # LONG LEFTWARDS DOUBLE ARROW
        "\u27F9": "$\\Longrightarrow$",  # LONG RIGHTWARDS DOUBLE ARROW
        "\u27FA": "$\\Longleftrightarrow$",  # LONG LEFT RIGHT DOUBLE ARROW
        "\u27FC": "$\\longmapsto$",  # LONG RIGHTWARDS ARROW FROM BAR
        "\u27FF": "$\\longrightsquigarrow$",  # LONG RIGHTWARDS SQUIGGLE ARROW
        "\u2905": "$\\twoheadmapsto$",  # RIGHTWARDS TWO-HEADED ARROW FROM BAR
        "\u2912": "$\\baruparrow$",  # UPWARDS ARROW TO BAR
        "\u2913": "$\\downarrowbar$",  # DOWNWARDS ARROW TO BAR
        "\u2923": "$\\hknwarrow$",  # NORTH WEST ARROW WITH HOOK
        "\u2924": "$\\hknearrow$",  # NORTH EAST ARROW WITH HOOK
        "\u2925": "$\\hksearow$",  # SOUTH EAST ARROW WITH HOOK
        "\u2926": "$\\hkswarow$",  # SOUTH WEST ARROW WITH HOOK
        "\u2927": "$\\tona$",  # NORTH WEST ARROW AND NORTH EAST ARROW
        "\u2928": "$\\toea$",  # NORTH EAST ARROW AND SOUTH EAST ARROW
        "\u2929": "$\\tosa$",  # SOUTH EAST ARROW AND SOUTH WEST ARROW
        "\u292A": "$\\towa$",  # SOUTH WEST ARROW AND NORTH WEST ARROW
        "\u2933": "$\\rightcurvedarrow$",  # WAVE ARROW POINTING DIRECTLY RIGHT
        "\u2936": "$\\leftdowncurvedarrow$",  # ARROW POINTING DOWNWARDS THEN CURVING LEFTWARDS
        "\u2937": "$\\rightdowncurvedarrow$",  # ARROW POINTING DOWNWARDS THEN CURVING RIGHTWARDS
        "\u2940": "$\\acwcirclearrow$",  # ANTICLOCKWISE CLOSED CIRCLE ARROW
        "\u2941": "$\\cwcirclearrow$",  # CLOCKWISE CLOSED CIRCLE ARROW
        "\u2942": "$\\rightarrowshortleftarrow$",  # RIGHTWARDS ARROW ABOVE SHORT LEFTWARDS ARROW
        "\u2944": "$\\shortrightarrowleftarrow$",  # SHORT RIGHTWARDS ARROW ABOVE LEFTWARDS ARROW
        "\u2947": "$\\rightarrowx$",  # RIGHTWARDS ARROW THROUGH X
        "\u294E": "$\\leftrightharpoonupup$",  # LEFT BARB UP RIGHT BARB UP HARPOON
        "\u294F": "$\\updownharpoonrightright$",  # UP BARB RIGHT DOWN BARB RIGHT HARPOON
        "\u2950": "$\\leftrightharpoondowndown$",  # LEFT BARB DOWN RIGHT BARB DOWN HARPOON
        "\u2951": "$\\updownharpoonleftleft$",  # UP BARB LEFT DOWN BARB LEFT HARPOON
        "\u2952": "$\\barleftharpoonup$",  # LEFTWARDS HARPOON WITH BARB UP TO BAR
        "\u2953": "$\\rightharpoonupbar$",  # RIGHTWARDS HARPOON WITH BARB UP TO BAR
        "\u2954": "$\\barupharpoonright$",  # UPWARDS HARPOON WITH BARB RIGHT TO BAR
        "\u2955": "$\\downharpoonrightbar$",  # DOWNWARDS HARPOON WITH BARB RIGHT TO BAR
        "\u2956": "$\\barleftharpoondown$",  # LEFTWARDS HARPOON WITH BARB DOWN TO BAR
        "\u2957": "$\\rightharpoondownbar$",  # RIGHTWARDS HARPOON WITH BARB DOWN TO BAR
        "\u2958": "$\\barupharpoonleft$",  # UPWARDS HARPOON WITH BARB LEFT TO BAR
        "\u2959": "$\\downharpoonleftbar$",  # DOWNWARDS HARPOON WITH BARB LEFT TO BAR
        "\u295A": "$\\leftharpoonupbar$",  # LEFTWARDS HARPOON WITH BARB UP FROM BAR
        "\u295B": "$\\barrightharpoonup$",  # RIGHTWARDS HARPOON WITH BARB UP FROM BAR
        "\u295C": "$\\upharpoonrightbar$",  # UPWARDS HARPOON WITH BARB RIGHT FROM BAR
        "\u295D": "$\\bardownharpoonright$",  # DOWNWARDS HARPOON WITH BARB RIGHT FROM BAR
        "\u295E": "$\\leftharpoondownbar$",  # LEFTWARDS HARPOON WITH BARB DOWN FROM BAR
        "\u295F": "$\\barrightharpoondown$",  # RIGHTWARDS HARPOON WITH BARB DOWN FROM BAR
        "\u2960": "$\\upharpoonleftbar$",  # UPWARDS HARPOON WITH BARB LEFT FROM BAR
        "\u2961": "$\\bardownharpoonleft$",  # DOWNWARDS HARPOON WITH BARB LEFT FROM BAR
        "\u296E": "$\\updownharpoonsleftright$",  # UPWARDS HARPOON WITH BARB LEFT BESIDE DOWNWARDS HARPOON WITH BARB RIGHT
        "\u296F": "$\\downupharpoonsleftright$",  # DOWNWARDS HARPOON WITH BARB LEFT BESIDE UPWARDS HARPOON WITH BARB RIGHT
        "\u2970": "$\\rightimply$",  # RIGHT DOUBLE ARROW WITH ROUNDED HEAD
        "\u297C": "$\\leftfishtail$",  # LEFT FISH TAIL
        "\u297D": "$\\rightfishtail$",  # RIGHT FISH TAIL
        "\u2980": "$\\Vvert$",  # TRIPLE VERTICAL BAR DELIMITER
        "\u2985": "$\\lParen$",  # LEFT WHITE PARENTHESIS
        "\u2986": "$\\rParen$",  # RIGHT WHITE PARENTHESIS
        "\u2993": "$\\lparenless$",  # LEFT ARC LESS-THAN BRACKET
        "\u2994": "$\\rparengtr$",  # RIGHT ARC GREATER-THAN BRACKET
        "\u2999": "$\\fourvdots$",  # DOTTED FENCE
        "\u299C": "$\\rightanglesqr$",  # RIGHT ANGLE VARIANT WITH SQUARE
        "\u29A0": "$\\gtlpar$",  # SPHERICAL ANGLE OPENING LEFT
        "\u29B5": "$\\circlehbar$",  # CIRCLE WITH HORIZONTAL BAR
        "\u29B6": "$\\circledvert$",  # CIRCLED VERTICAL BAR
        "\u29CA": "$\\triangleodot$",  # TRIANGLE WITH DOT ABOVE
        "\u29CB": "$\\triangleubar$",  # TRIANGLE WITH UNDERBAR
        "\u29CF": "$\\ltrivb$",  # LEFT TRIANGLE BESIDE VERTICAL BAR
        "\u29D0": "$\\vbrtri$",  # VERTICAL BAR BESIDE RIGHT TRIANGLE
        "\u29DC": "$\\iinfin$",  # INCOMPLETE INFINITY
        "\u29EB": "$\\mdlgblklozenge$",  # BLACK LOZENGE
        "\u29F4": "$\\ruledelayed$",  # RULE-DELAYED
        "\u2A04": "$\\biguplus$",  # N-ARY UNION OPERATOR WITH PLUS
        "\u2A05": "$\\bigsqcap$",  # N-ARY SQUARE INTERSECTION OPERATOR
        "\u2A06": "$\\bigsqcup$",  # N-ARY SQUARE UNION OPERATOR
        "\u2A07": "$\\conjquant$",  # TWO LOGICAL AND OPERATOR
        "\u2A08": "$\\disjquant$",  # TWO LOGICAL OR OPERATOR
        "\u2A0D": "$\\intbar$",  # FINITE PART INTEGRAL
        "\u2A0F": "$\\fint$",  # INTEGRAL AVERAGE WITH SLASH
        "\u2A10": "$\\cirfnint$",  # CIRCULATION FUNCTION
        "\u2A16": "$\\sqint$",  # QUATERNION INTEGRAL OPERATOR
        "\u2A25": "$\\plusdot$",  # PLUS SIGN WITH DOT BELOW
        "\u2A2A": "$\\minusdot$",  # MINUS SIGN WITH DOT BELOW
        "\u2A2D": "$\\opluslhrim$",  # PLUS SIGN IN LEFT HALF CIRCLE
        "\u2A2E": "$\\oplusrhrim$",  # PLUS SIGN IN RIGHT HALF CIRCLE
        "\u2A2F": "$\\vectimes$",  # VECTOR OR CROSS PRODUCT
        "\u2A34": "$\\otimeslhrim$",  # MULTIPLICATION SIGN IN LEFT HALF CIRCLE
        "\u2A35": "$\\otimesrhrim$",  # MULTIPLICATION SIGN IN RIGHT HALF CIRCLE
        "\u2A3C": "$\\intprod$",  # INTERIOR PRODUCT
        "\u2A3F": "$\\amalg$",  # AMALGAMATION OR COPRODUCT
        "\u2A53": "$\\Wedge$",  # DOUBLE LOGICAL AND
        "\u2A54": "$\\Vee$",  # DOUBLE LOGICAL OR
        "\u2A55": "$\\wedgeonwedge$",  # TWO INTERSECTING LOGICAL AND
        "\u2A56": "$\\veeonvee$",  # TWO INTERSECTING LOGICAL OR
        "\u2A5E": "$\\doublebarwedge$",  # LOGICAL AND WITH DOUBLE OVERBAR
        "\u2A5F": "$\\wedgebar$",  # LOGICAL AND WITH UNDERBAR
        "\u2A63": "$\\veedoublebar$",  # LOGICAL OR WITH DOUBLE UNDERBAR
        "\u2A6E": "$\\asteq$",  # EQUALS WITH ASTERISK
        "\u2A75": "$\\eqeq$",  # TWO CONSECUTIVE EQUALS SIGNS
        "\u2A7D": "$\\leqslant$",  # LESS-THAN OR SLANTED EQUAL TO
        "\u2A7E": "$\\geqslant$",  # GREATER-THAN OR SLANTED EQUAL TO
        "\u2A85": "$\\lessapprox$",  # LESS-THAN OR APPROXIMATE
        "\u2A86": "$\\gtrapprox$",  # GREATER-THAN OR APPROXIMATE
        "\u2A87": "$\\lneq$",  # LESS-THAN AND SINGLE-LINE NOT EQUAL TO
        "\u2A88": "$\\gneq$",  # GREATER-THAN AND SINGLE-LINE NOT EQUAL TO
        "\u2A89": "$\\lnapprox$",  # LESS-THAN AND NOT APPROXIMATE
        "\u2A8A": "$\\gnapprox$",  # GREATER-THAN AND NOT APPROXIMATE
        "\u2A8B": "$\\lesseqqgtr$",  # LESS-THAN ABOVE DOUBLE-LINE EQUAL ABOVE GREATER-THAN
        "\u2A8C": "$\\gtreqqless$",  # GREATER-THAN ABOVE DOUBLE-LINE EQUAL ABOVE LESS-THAN
        "\u2A95": "$\\eqslantless$",  # SLANTED EQUAL TO OR LESS-THAN
        "\u2A96": "$\\eqslantgtr$",  # SLANTED EQUAL TO OR GREATER-THAN
        "\u2A9D": "$\\simless$",  # SIMILAR OR LESS-THAN
        "\u2A9E": "$\\simgtr$",  # SIMILAR OR GREATER-THAN
        "\u2AA1": "$\\Lt$",  # DOUBLE NESTED LESS-THAN
        "\u2AA2": "$\\Gt$",  # DOUBLE NESTED GREATER-THAN
        "\u2AAF": "$\\preceq$",  # PRECEDES ABOVE SINGLE-LINE EQUALS SIGN
        "\u2AB0": "$\\succeq$",  # SUCCEEDS ABOVE SINGLE-LINE EQUALS SIGN
        "\u2AB5": "$\\precneqq$",  # PRECEDES ABOVE NOT EQUAL TO
        "\u2AB6": "$\\succneqq$",  # SUCCEEDS ABOVE NOT EQUAL TO
        "\u2AB7": "$\\precapprox$",  # PRECEDES ABOVE ALMOST EQUAL TO
        "\u2AB8": "$\\succapprox$",  # SUCCEEDS ABOVE ALMOST EQUAL TO
        "\u2AB9": "$\\precnapprox$",  # PRECEDES ABOVE NOT ALMOST EQUAL TO
        "\u2ABA": "$\\succnapprox$",  # SUCCEEDS ABOVE NOT ALMOST EQUAL TO
        "\u2AC5": "$\\subseteqq$",  # SUBSET OF ABOVE EQUALS SIGN
        "\u2AC6": "$\\supseteqq$",  # SUPERSET OF ABOVE EQUALS SIGN
        "\u2ACB": "$\\subsetneqq$",  # SUBSET OF ABOVE NOT EQUAL TO
        "\u2ACC": "$\\supsetneqq$",  # SUPERSET OF ABOVE NOT EQUAL TO
        "\u2AEB": "$\\Vbar$",  # DOUBLE UP TACK
        "\u2AF6": "$\\threedotcolon$",  # TRIPLE COLON OPERATOR
        "\u2AFD": "$\\sslash$",  # DOUBLE SOLIDUS OPERATOR
        "\u300A": "{\\ElsevierGlyph{300A}}",  # LEFT DOUBLE ANGLE BRACKET
        "\u300B": "{\\ElsevierGlyph{300B}}",  # RIGHT DOUBLE ANGLE BRACKET
        "\u3018": "$\\Lbrbrak$",  # LEFT WHITE TORTOISE SHELL BRACKET
        "\u3019": "$\\Rbrbrak$",  # RIGHT WHITE TORTOISE SHELL BRACKET
        "\u301A": "{\\openbracketleft}",  # LEFT WHITE SQUARE BRACKET
        "\u301B": "{\\openbracketright}",  # RIGHT WHITE SQUARE BRACKET
        "\uFB00": "ff",  # LATIN SMALL LIGATURE FF
        "\uFB01": "fi",  # LATIN SMALL LIGATURE FI
        "\uFB02": "fl",  # LATIN SMALL LIGATURE FL
        "\uFB03": "ffi",  # LATIN SMALL LIGATURE FFI
        "\uFB04": "ffl",  # LATIN SMALL LIGATURE FFL
        "\uD400": "$\\mbfA$",  # MATHEMATICAL BOLD CAPITAL A
        "\uD401": "$\\mbfB$",  # MATHEMATICAL BOLD CAPITAL B
        "\uD402": "$\\mbfC$",  # MATHEMATICAL BOLD CAPITAL C
        "\uD403": "$\\mbfD$",  # MATHEMATICAL BOLD CAPITAL D
        "\uD404": "$\\mbfE$",  # MATHEMATICAL BOLD CAPITAL E
        "\uD405": "$\\mbfF$",  # MATHEMATICAL BOLD CAPITAL F
        "\uD406": "$\\mbfG$",  # MATHEMATICAL BOLD CAPITAL G
        "\uD407": "$\\mbfH$",  # MATHEMATICAL BOLD CAPITAL H
        "\uD408": "$\\mbfI$",  # MATHEMATICAL BOLD CAPITAL I
        "\uD409": "$\\mbfJ$",  # MATHEMATICAL BOLD CAPITAL J
        "\uD40A": "$\\mbfK$",  # MATHEMATICAL BOLD CAPITAL K
        "\uD40B": "$\\mbfL$",  # MATHEMATICAL BOLD CAPITAL L
        "\uD40C": "$\\mbfM$",  # MATHEMATICAL BOLD CAPITAL M
        "\uD40D": "$\\mbfN$",  # MATHEMATICAL BOLD CAPITAL N
        "\uD40E": "$\\mbfO$",  # MATHEMATICAL BOLD CAPITAL O
        "\uD40F": "$\\mbfP$",  # MATHEMATICAL BOLD CAPITAL P
        "\uD410": "$\\mbfQ$",  # MATHEMATICAL BOLD CAPITAL Q
        "\uD411": "$\\mbfR$",  # MATHEMATICAL BOLD CAPITAL R
        "\uD412": "$\\mbfS$",  # MATHEMATICAL BOLD CAPITAL S
        "\uD413": "$\\mbfT$",  # MATHEMATICAL BOLD CAPITAL T
        "\uD414": "$\\mbfU$",  # MATHEMATICAL BOLD CAPITAL U
        "\uD415": "$\\mbfV$",  # MATHEMATICAL BOLD CAPITAL V
        "\uD416": "$\\mbfW$",  # MATHEMATICAL BOLD CAPITAL W
        "\uD417": "$\\mbfX$",  # MATHEMATICAL BOLD CAPITAL X
        "\uD418": "$\\mbfY$",  # MATHEMATICAL BOLD CAPITAL Y
        "\uD419": "$\\mbfZ$",  # MATHEMATICAL BOLD CAPITAL Z
        "\uD41A": "$\\mbfa$",  # MATHEMATICAL BOLD SMALL A
        "\uD41B": "$\\mbfb$",  # MATHEMATICAL BOLD SMALL B
        "\uD41C": "$\\mbfc$",  # MATHEMATICAL BOLD SMALL C
        "\uD41D": "$\\mbfd$",  # MATHEMATICAL BOLD SMALL D
        "\uD41E": "$\\mbfe$",  # MATHEMATICAL BOLD SMALL E
        "\uD41F": "$\\mbff$",  # MATHEMATICAL BOLD SMALL F
        "\uD420": "$\\mbfg$",  # MATHEMATICAL BOLD SMALL G
        "\uD421": "$\\mbfh$",  # MATHEMATICAL BOLD SMALL H
        "\uD422": "$\\mbfi$",  # MATHEMATICAL BOLD SMALL I
        "\uD423": "$\\mbfj$",  # MATHEMATICAL BOLD SMALL J
        "\uD424": "$\\mbfk$",  # MATHEMATICAL BOLD SMALL K
        "\uD425": "$\\mbfl$",  # MATHEMATICAL BOLD SMALL L
        "\uD426": "$\\mbfm$",  # MATHEMATICAL BOLD SMALL M
        "\uD427": "$\\mbfn$",  # MATHEMATICAL BOLD SMALL N
        "\uD428": "$\\mbfo$",  # MATHEMATICAL BOLD SMALL O
        "\uD429": "$\\mbfp$",  # MATHEMATICAL BOLD SMALL P
        "\uD42A": "$\\mbfq$",  # MATHEMATICAL BOLD SMALL Q
        "\uD42B": "$\\mbfr$",  # MATHEMATICAL BOLD SMALL R
        "\uD42C": "$\\mbfs$",  # MATHEMATICAL BOLD SMALL S
        "\uD42D": "$\\mbft$",  # MATHEMATICAL BOLD SMALL T
        "\uD42E": "$\\mbfu$",  # MATHEMATICAL BOLD SMALL U
        "\uD42F": "$\\mbfv$",  # MATHEMATICAL BOLD SMALL V
        "\uD430": "$\\mbfw$",  # MATHEMATICAL BOLD SMALL W
        "\uD431": "$\\mbfx$",  # MATHEMATICAL BOLD SMALL X
        "\uD432": "$\\mbfy$",  # MATHEMATICAL BOLD SMALL Y
        "\uD433": "$\\mbfz$",  # MATHEMATICAL BOLD SMALL Z
        "\uD434": "$\\mitA$",  # MATHEMATICAL ITALIC CAPITAL A
        "\uD435": "$\\mitB$",  # MATHEMATICAL ITALIC CAPITAL B
        "\uD436": "$\\mitC$",  # MATHEMATICAL ITALIC CAPITAL C
        "\uD437": "$\\mitD$",  # MATHEMATICAL ITALIC CAPITAL D
        "\uD438": "$\\mitE$",  # MATHEMATICAL ITALIC CAPITAL E
        "\uD439": "$\\mitF$",  # MATHEMATICAL ITALIC CAPITAL F
        "\uD43A": "$\\mitG$",  # MATHEMATICAL ITALIC CAPITAL G
        "\uD43B": "$\\mitH$",  # MATHEMATICAL ITALIC CAPITAL H
        "\uD43C": "$\\mitI$",  # MATHEMATICAL ITALIC CAPITAL I
        "\uD43D": "$\\mitJ$",  # MATHEMATICAL ITALIC CAPITAL J
        "\uD43E": "$\\mitK$",  # MATHEMATICAL ITALIC CAPITAL K
        "\uD43F": "$\\mitL$",  # MATHEMATICAL ITALIC CAPITAL L
        "\uD440": "$\\mitM$",  # MATHEMATICAL ITALIC CAPITAL M
        "\uD441": "$\\mitN$",  # MATHEMATICAL ITALIC CAPITAL N
        "\uD442": "$\\mitO$",  # MATHEMATICAL ITALIC CAPITAL O
        "\uD443": "$\\mitP$",  # MATHEMATICAL ITALIC CAPITAL P
        "\uD444": "$\\mitQ$",  # MATHEMATICAL ITALIC CAPITAL Q
        "\uD445": "$\\mitR$",  # MATHEMATICAL ITALIC CAPITAL R
        "\uD446": "$\\mitS$",  # MATHEMATICAL ITALIC CAPITAL S
        "\uD447": "$\\mitT$",  # MATHEMATICAL ITALIC CAPITAL T
        "\uD448": "$\\mitU$",  # MATHEMATICAL ITALIC CAPITAL U
        "\uD449": "$\\mitV$",  # MATHEMATICAL ITALIC CAPITAL V
        "\uD44A": "$\\mitW$",  # MATHEMATICAL ITALIC CAPITAL W
        "\uD44B": "$\\mitX$",  # MATHEMATICAL ITALIC CAPITAL X
        "\uD44C": "$\\mitY$",  # MATHEMATICAL ITALIC CAPITAL Y
        "\uD44D": "$\\mitZ$",  # MATHEMATICAL ITALIC CAPITAL Z
        "\uD44E": "$\\mita$",  # MATHEMATICAL ITALIC SMALL A
        "\uD44F": "$\\mitb$",  # MATHEMATICAL ITALIC SMALL B
        "\uD450": "$\\mitc$",  # MATHEMATICAL ITALIC SMALL C
        "\uD451": "$\\mitd$",  # MATHEMATICAL ITALIC SMALL D
        "\uD452": "$\\mite$",  # MATHEMATICAL ITALIC SMALL E
        "\uD453": "$\\mitf$",  # MATHEMATICAL ITALIC SMALL F
        "\uD454": "$\\mitg$",  # MATHEMATICAL ITALIC SMALL G
        "\uD456": "$\\miti$",  # MATHEMATICAL ITALIC SMALL I
        "\uD457": "$\\mitj$",  # MATHEMATICAL ITALIC SMALL J
        "\uD458": "$\\mitk$",  # MATHEMATICAL ITALIC SMALL K
        "\uD459": "$\\mitl$",  # MATHEMATICAL ITALIC SMALL L
        "\uD45A": "$\\mitm$",  # MATHEMATICAL ITALIC SMALL M
        "\uD45B": "$\\mitn$",  # MATHEMATICAL ITALIC SMALL N
        "\uD45C": "$\\mito$",  # MATHEMATICAL ITALIC SMALL O
        "\uD45D": "$\\mitp$",  # MATHEMATICAL ITALIC SMALL P
        "\uD45E": "$\\mitq$",  # MATHEMATICAL ITALIC SMALL Q
        "\uD45F": "$\\mitr$",  # MATHEMATICAL ITALIC SMALL R
        "\uD460": "$\\mits$",  # MATHEMATICAL ITALIC SMALL S
        "\uD461": "$\\mitt$",  # MATHEMATICAL ITALIC SMALL T
        "\uD462": "$\\mitu$",  # MATHEMATICAL ITALIC SMALL U
        "\uD463": "$\\mitv$",  # MATHEMATICAL ITALIC SMALL V
        "\uD464": "$\\mitw$",  # MATHEMATICAL ITALIC SMALL W
        "\uD465": "$\\mitx$",  # MATHEMATICAL ITALIC SMALL X
        "\uD466": "$\\mity$",  # MATHEMATICAL ITALIC SMALL Y
        "\uD467": "$\\mitz$",  # MATHEMATICAL ITALIC SMALL Z
        "\uD468": "$\\mbfitA$",  # MATHEMATICAL BOLD ITALIC CAPITAL A
        "\uD469": "$\\mbfitB$",  # MATHEMATICAL BOLD ITALIC CAPITAL B
        "\uD46A": "$\\mbfitC$",  # MATHEMATICAL BOLD ITALIC CAPITAL C
        "\uD46B": "$\\mbfitD$",  # MATHEMATICAL BOLD ITALIC CAPITAL D
        "\uD46C": "$\\mbfitE$",  # MATHEMATICAL BOLD ITALIC CAPITAL E
        "\uD46D": "$\\mbfitF$",  # MATHEMATICAL BOLD ITALIC CAPITAL F
        "\uD46E": "$\\mbfitG$",  # MATHEMATICAL BOLD ITALIC CAPITAL G
        "\uD46F": "$\\mbfitH$",  # MATHEMATICAL BOLD ITALIC CAPITAL H
        "\uD470": "$\\mbfitI$",  # MATHEMATICAL BOLD ITALIC CAPITAL I
        "\uD471": "$\\mbfitJ$",  # MATHEMATICAL BOLD ITALIC CAPITAL J
        "\uD472": "$\\mbfitK$",  # MATHEMATICAL BOLD ITALIC CAPITAL K
        "\uD473": "$\\mbfitL$",  # MATHEMATICAL BOLD ITALIC CAPITAL L
        "\uD474": "$\\mbfitM$",  # MATHEMATICAL BOLD ITALIC CAPITAL M
        "\uD475": "$\\mbfitN$",  # MATHEMATICAL BOLD ITALIC CAPITAL N
        "\uD476": "$\\mbfitO$",  # MATHEMATICAL BOLD ITALIC CAPITAL O
        "\uD477": "$\\mbfitP$",  # MATHEMATICAL BOLD ITALIC CAPITAL P
        "\uD478": "$\\mbfitQ$",  # MATHEMATICAL BOLD ITALIC CAPITAL Q
        "\uD479": "$\\mbfitR$",  # MATHEMATICAL BOLD ITALIC CAPITAL R
        "\uD47A": "$\\mbfitS$",  # MATHEMATICAL BOLD ITALIC CAPITAL S
        "\uD47B": "$\\mbfitT$",  # MATHEMATICAL BOLD ITALIC CAPITAL T
        "\uD47C": "$\\mbfitU$",  # MATHEMATICAL BOLD ITALIC CAPITAL U
        "\uD47D": "$\\mbfitV$",  # MATHEMATICAL BOLD ITALIC CAPITAL V
        "\uD47E": "$\\mbfitW$",  # MATHEMATICAL BOLD ITALIC CAPITAL W
        "\uD47F": "$\\mbfitX$",  # MATHEMATICAL BOLD ITALIC CAPITAL X
        "\uD480": "$\\mbfitY$",  # MATHEMATICAL BOLD ITALIC CAPITAL Y
        "\uD481": "$\\mbfitZ$",  # MATHEMATICAL BOLD ITALIC CAPITAL Z
        "\uD482": "$\\mbfita$",  # MATHEMATICAL BOLD ITALIC SMALL A
        "\uD483": "$\\mbfitb$",  # MATHEMATICAL BOLD ITALIC SMALL B
        "\uD484": "$\\mbfitc$",  # MATHEMATICAL BOLD ITALIC SMALL C
        "\uD485": "$\\mbfitd$",  # MATHEMATICAL BOLD ITALIC SMALL D
        "\uD486": "$\\mbfite$",  # MATHEMATICAL BOLD ITALIC SMALL E
        "\uD487": "$\\mbfitf$",  # MATHEMATICAL BOLD ITALIC SMALL F
        "\uD488": "$\\mbfitg$",  # MATHEMATICAL BOLD ITALIC SMALL G
        "\uD489": "$\\mbfith$",  # MATHEMATICAL BOLD ITALIC SMALL H
        "\uD48A": "$\\mbfiti$",  # MATHEMATICAL BOLD ITALIC SMALL I
        "\uD48B": "$\\mbfitj$",  # MATHEMATICAL BOLD ITALIC SMALL J
        "\uD48C": "$\\mbfitk$",  # MATHEMATICAL BOLD ITALIC SMALL K
        "\uD48D": "$\\mbfitl$",  # MATHEMATICAL BOLD ITALIC SMALL L
        "\uD48E": "$\\mbfitm$",  # MATHEMATICAL BOLD ITALIC SMALL M
        "\uD48F": "$\\mbfitn$",  # MATHEMATICAL BOLD ITALIC SMALL N
        "\uD490": "$\\mbfito$",  # MATHEMATICAL BOLD ITALIC SMALL O
        "\uD491": "$\\mbfitp$",  # MATHEMATICAL BOLD ITALIC SMALL P
        "\uD492": "$\\mbfitq$",  # MATHEMATICAL BOLD ITALIC SMALL Q
        "\uD493": "$\\mbfitr$",  # MATHEMATICAL BOLD ITALIC SMALL R
        "\uD494": "$\\mbfits$",  # MATHEMATICAL BOLD ITALIC SMALL S
        "\uD495": "$\\mbfitt$",  # MATHEMATICAL BOLD ITALIC SMALL T
        "\uD496": "$\\mbfitu$",  # MATHEMATICAL BOLD ITALIC SMALL U
        "\uD497": "$\\mbfitv$",  # MATHEMATICAL BOLD ITALIC SMALL V
        "\uD498": "$\\mbfitw$",  # MATHEMATICAL BOLD ITALIC SMALL W
        "\uD499": "$\\mbfitx$",  # MATHEMATICAL BOLD ITALIC SMALL X
        "\uD49A": "$\\mbfity$",  # MATHEMATICAL BOLD ITALIC SMALL Y
        "\uD49B": "$\\mbfitz$",  # MATHEMATICAL BOLD ITALIC SMALL Z
        "\uD49C": "$\\mscrA$",  # MATHEMATICAL SCRIPT CAPITAL A
        "\uD49E": "$\\mscrC$",  # MATHEMATICAL SCRIPT CAPITAL C
        "\uD49F": "$\\mscrD$",  # MATHEMATICAL SCRIPT CAPITAL D
        "\uD4A2": "$\\mscrG$",  # MATHEMATICAL SCRIPT CAPITAL G
        "\uD4A5": "$\\mscrJ$",  # MATHEMATICAL SCRIPT CAPITAL J
        "\uD4A6": "$\\mscrK$",  # MATHEMATICAL SCRIPT CAPITAL K
        "\uD4A9": "$\\mscrN$",  # MATHEMATICAL SCRIPT CAPITAL N
        "\uD4AA": "$\\mscrO$",  # MATHEMATICAL SCRIPT CAPITAL O
        "\uD4AB": "$\\mscrP$",  # MATHEMATICAL SCRIPT CAPITAL P
        "\uD4AC": "$\\mscrQ$",  # MATHEMATICAL SCRIPT CAPITAL Q
        "\uD4AE": "$\\mscrS$",  # MATHEMATICAL SCRIPT CAPITAL S
        "\uD4AF": "$\\mscrT$",  # MATHEMATICAL SCRIPT CAPITAL T
        "\uD4B0": "$\\mscrU$",  # MATHEMATICAL SCRIPT CAPITAL U
        "\uD4B1": "$\\mscrV$",  # MATHEMATICAL SCRIPT CAPITAL V
        "\uD4B2": "$\\mscrW$",  # MATHEMATICAL SCRIPT CAPITAL W
        "\uD4B3": "$\\mscrX$",  # MATHEMATICAL SCRIPT CAPITAL X
        "\uD4B4": "$\\mscrY$",  # MATHEMATICAL SCRIPT CAPITAL Y
        "\uD4B5": "$\\mscrZ$",  # MATHEMATICAL SCRIPT CAPITAL Z
        "\uD4B6": "$\\mscra$",  # MATHEMATICAL SCRIPT SMALL A
        "\uD4B7": "$\\mscrb$",  # MATHEMATICAL SCRIPT SMALL B
        "\uD4B8": "$\\mscrc$",  # MATHEMATICAL SCRIPT SMALL C
        "\uD4B9": "$\\mscrd$",  # MATHEMATICAL SCRIPT SMALL D
        "\uD4BB": "$\\mscrf$",  # MATHEMATICAL SCRIPT SMALL F
        "\uD4BD": "$\\mscrh$",  # MATHEMATICAL SCRIPT SMALL H
        "\uD4BE": "$\\mscri$",  # MATHEMATICAL SCRIPT SMALL I
        "\uD4BF": "$\\mscrj$",  # MATHEMATICAL SCRIPT SMALL J
        "\uD4C0": "$\\mscrk$",  # MATHEMATICAL SCRIPT SMALL K
        "\uD4C1": "$\\mscrl$",  # MATHEMATICAL SCRIPT SMALL L
        "\uD4C2": "$\\mscrm$",  # MATHEMATICAL SCRIPT SMALL M
        "\uD4C3": "$\\mscrn$",  # MATHEMATICAL SCRIPT SMALL N
        "\uD4C5": "$\\mscrp$",  # MATHEMATICAL SCRIPT SMALL P
        "\uD4C6": "$\\mscrq$",  # MATHEMATICAL SCRIPT SMALL Q
        "\uD4C7": "$\\mscrr$",  # MATHEMATICAL SCRIPT SMALL R
        "\uD4C8": "$\\mscrs$",  # MATHEMATICAL SCRIPT SMALL S
        "\uD4C9": "$\\mscrt$",  # MATHEMATICAL SCRIPT SMALL T
        "\uD4CA": "$\\mscru$",  # MATHEMATICAL SCRIPT SMALL U
        "\uD4CB": "$\\mscrv$",  # MATHEMATICAL SCRIPT SMALL V
        "\uD4CC": "$\\mscrw$",  # MATHEMATICAL SCRIPT SMALL W
        "\uD4CD": "$\\mscrx$",  # MATHEMATICAL SCRIPT SMALL X
        "\uD4CE": "$\\mscry$",  # MATHEMATICAL SCRIPT SMALL Y
        "\uD4CF": "$\\mscrz$",  # MATHEMATICAL SCRIPT SMALL Z
        "\uD4D0": "$\\mbfscrA$",  # MATHEMATICAL BOLD SCRIPT CAPITAL A
        "\uD4D1": "$\\mbfscrB$",  # MATHEMATICAL BOLD SCRIPT CAPITAL B
        "\uD4D2": "$\\mbfscrC$",  # MATHEMATICAL BOLD SCRIPT CAPITAL C
        "\uD4D3": "$\\mbfscrD$",  # MATHEMATICAL BOLD SCRIPT CAPITAL D
        "\uD4D4": "$\\mbfscrE$",  # MATHEMATICAL BOLD SCRIPT CAPITAL E
        "\uD4D5": "$\\mbfscrF$",  # MATHEMATICAL BOLD SCRIPT CAPITAL F
        "\uD4D6": "$\\mbfscrG$",  # MATHEMATICAL BOLD SCRIPT CAPITAL G
        "\uD4D7": "$\\mbfscrH$",  # MATHEMATICAL BOLD SCRIPT CAPITAL H
        "\uD4D8": "$\\mbfscrI$",  # MATHEMATICAL BOLD SCRIPT CAPITAL I
        "\uD4D9": "$\\mbfscrJ$",  # MATHEMATICAL BOLD SCRIPT CAPITAL J
        "\uD4DA": "$\\mbfscrK$",  # MATHEMATICAL BOLD SCRIPT CAPITAL K
        "\uD4DB": "$\\mbfscrL$",  # MATHEMATICAL BOLD SCRIPT CAPITAL L
        "\uD4DC": "$\\mbfscrM$",  # MATHEMATICAL BOLD SCRIPT CAPITAL M
        "\uD4DD": "$\\mbfscrN$",  # MATHEMATICAL BOLD SCRIPT CAPITAL N
        "\uD4DE": "$\\mbfscrO$",  # MATHEMATICAL BOLD SCRIPT CAPITAL O
        "\uD4DF": "$\\mbfscrP$",  # MATHEMATICAL BOLD SCRIPT CAPITAL P
        "\uD4E0": "$\\mbfscrQ$",  # MATHEMATICAL BOLD SCRIPT CAPITAL Q
        "\uD4E1": "$\\mbfscrR$",  # MATHEMATICAL BOLD SCRIPT CAPITAL R
        "\uD4E2": "$\\mbfscrS$",  # MATHEMATICAL BOLD SCRIPT CAPITAL S
        "\uD4E3": "$\\mbfscrT$",  # MATHEMATICAL BOLD SCRIPT CAPITAL T
        "\uD4E4": "$\\mbfscrU$",  # MATHEMATICAL BOLD SCRIPT CAPITAL U
        "\uD4E5": "$\\mbfscrV$",  # MATHEMATICAL BOLD SCRIPT CAPITAL V
        "\uD4E6": "$\\mbfscrW$",  # MATHEMATICAL BOLD SCRIPT CAPITAL W
        "\uD4E7": "$\\mbfscrX$",  # MATHEMATICAL BOLD SCRIPT CAPITAL X
        "\uD4E8": "$\\mbfscrY$",  # MATHEMATICAL BOLD SCRIPT CAPITAL Y
        "\uD4E9": "$\\mbfscrZ$",  # MATHEMATICAL BOLD SCRIPT CAPITAL Z
        "\uD4EA": "$\\mbfscra$",  # MATHEMATICAL BOLD SCRIPT SMALL A
        "\uD4EB": "$\\mbfscrb$",  # MATHEMATICAL BOLD SCRIPT SMALL B
        "\uD4EC": "$\\mbfscrc$",  # MATHEMATICAL BOLD SCRIPT SMALL C
        "\uD4ED": "$\\mbfscrd$",  # MATHEMATICAL BOLD SCRIPT SMALL D
        "\uD4EE": "$\\mbfscre$",  # MATHEMATICAL BOLD SCRIPT SMALL E
        "\uD4EF": "$\\mbfscrf$",  # MATHEMATICAL BOLD SCRIPT SMALL F
        "\uD4F0": "$\\mbfscrg$",  # MATHEMATICAL BOLD SCRIPT SMALL G
        "\uD4F1": "$\\mbfscrh$",  # MATHEMATICAL BOLD SCRIPT SMALL H
        "\uD4F2": "$\\mbfscri$",  # MATHEMATICAL BOLD SCRIPT SMALL I
        "\uD4F3": "$\\mbfscrj$",  # MATHEMATICAL BOLD SCRIPT SMALL J
        "\uD4F4": "$\\mbfscrk$",  # MATHEMATICAL BOLD SCRIPT SMALL K
        "\uD4F5": "$\\mbfscrl$",  # MATHEMATICAL BOLD SCRIPT SMALL L
        "\uD4F6": "$\\mbfscrm$",  # MATHEMATICAL BOLD SCRIPT SMALL M
        "\uD4F7": "$\\mbfscrn$",  # MATHEMATICAL BOLD SCRIPT SMALL N
        "\uD4F8": "$\\mbfscro$",  # MATHEMATICAL BOLD SCRIPT SMALL O
        "\uD4F9": "$\\mbfscrp$",  # MATHEMATICAL BOLD SCRIPT SMALL P
        "\uD4FA": "$\\mbfscrq$",  # MATHEMATICAL BOLD SCRIPT SMALL Q
        "\uD4FB": "$\\mbfscrr$",  # MATHEMATICAL BOLD SCRIPT SMALL R
        "\uD4FC": "$\\mbfscrs$",  # MATHEMATICAL BOLD SCRIPT SMALL S
        "\uD4FD": "$\\mbfscrt$",  # MATHEMATICAL BOLD SCRIPT SMALL T
        "\uD4FE": "$\\mbfscru$",  # MATHEMATICAL BOLD SCRIPT SMALL U
        "\uD4FF": "$\\mbfscrv$",  # MATHEMATICAL BOLD SCRIPT SMALL V
        "\uD500": "$\\mbfscrw$",  # MATHEMATICAL BOLD SCRIPT SMALL W
        "\uD501": "$\\mbfscrx$",  # MATHEMATICAL BOLD SCRIPT SMALL X
        "\uD502": "$\\mbfscry$",  # MATHEMATICAL BOLD SCRIPT SMALL Y
        "\uD503": "$\\mbfscrz$",  # MATHEMATICAL BOLD SCRIPT SMALL Z
        "\uD504": "$\\mfrakA$",  # MATHEMATICAL FRAKTUR CAPITAL A
        "\uD505": "$\\mfrakB$",  # MATHEMATICAL FRAKTUR CAPITAL B
        "\uD507": "$\\mfrakD$",  # MATHEMATICAL FRAKTUR CAPITAL D
        "\uD508": "$\\mfrakE$",  # MATHEMATICAL FRAKTUR CAPITAL E
        "\uD509": "$\\mfrakF$",  # MATHEMATICAL FRAKTUR CAPITAL F
        "\uD50A": "$\\mfrakG$",  # MATHEMATICAL FRAKTUR CAPITAL G
        "\uD50D": "$\\mfrakJ$",  # MATHEMATICAL FRAKTUR CAPITAL J
        "\uD50E": "$\\mfrakK$",  # MATHEMATICAL FRAKTUR CAPITAL K
        "\uD50F": "$\\mfrakL$",  # MATHEMATICAL FRAKTUR CAPITAL L
        "\uD510": "$\\mfrakM$",  # MATHEMATICAL FRAKTUR CAPITAL M
        "\uD511": "$\\mfrakN$",  # MATHEMATICAL FRAKTUR CAPITAL N
        "\uD512": "$\\mfrakO$",  # MATHEMATICAL FRAKTUR CAPITAL O
        "\uD513": "$\\mfrakP$",  # MATHEMATICAL FRAKTUR CAPITAL P
        "\uD514": "$\\mfrakQ$",  # MATHEMATICAL FRAKTUR CAPITAL Q
        "\uD516": "$\\mfrakS$",  # MATHEMATICAL FRAKTUR CAPITAL S
        "\uD517": "$\\mfrakT$",  # MATHEMATICAL FRAKTUR CAPITAL T
        "\uD518": "$\\mfrakU$",  # MATHEMATICAL FRAKTUR CAPITAL U
        "\uD519": "$\\mfrakV$",  # MATHEMATICAL FRAKTUR CAPITAL V
        "\uD51A": "$\\mfrakW$",  # MATHEMATICAL FRAKTUR CAPITAL W
        "\uD51B": "$\\mfrakX$",  # MATHEMATICAL FRAKTUR CAPITAL X
        "\uD51C": "$\\mfrakY$",  # MATHEMATICAL FRAKTUR CAPITAL Y
        "\uD51E": "$\\mfraka$",  # MATHEMATICAL FRAKTUR SMALL A
        "\uD51F": "$\\mfrakb$",  # MATHEMATICAL FRAKTUR SMALL B
        "\uD520": "$\\mfrakc$",  # MATHEMATICAL FRAKTUR SMALL C
        "\uD521": "$\\mfrakd$",  # MATHEMATICAL FRAKTUR SMALL D
        "\uD522": "$\\mfrake$",  # MATHEMATICAL FRAKTUR SMALL E
        "\uD523": "$\\mfrakf$",  # MATHEMATICAL FRAKTUR SMALL F
        "\uD524": "$\\mfrakg$",  # MATHEMATICAL FRAKTUR SMALL G
        "\uD525": "$\\mfrakh$",  # MATHEMATICAL FRAKTUR SMALL H
        "\uD526": "$\\mfraki$",  # MATHEMATICAL FRAKTUR SMALL I
        "\uD527": "$\\mfrakj$",  # MATHEMATICAL FRAKTUR SMALL J
        "\uD528": "$\\mfrakk$",  # MATHEMATICAL FRAKTUR SMALL K
        "\uD529": "$\\mfrakl$",  # MATHEMATICAL FRAKTUR SMALL L
        "\uD52A": "$\\mfrakm$",  # MATHEMATICAL FRAKTUR SMALL M
        "\uD52B": "$\\mfrakn$",  # MATHEMATICAL FRAKTUR SMALL N
        "\uD52C": "$\\mfrako$",  # MATHEMATICAL FRAKTUR SMALL O
        "\uD52D": "$\\mfrakp$",  # MATHEMATICAL FRAKTUR SMALL P
        "\uD52E": "$\\mfrakq$",  # MATHEMATICAL FRAKTUR SMALL Q
        "\uD52F": "$\\mfrakr$",  # MATHEMATICAL FRAKTUR SMALL R
        "\uD530": "$\\mfraks$",  # MATHEMATICAL FRAKTUR SMALL S
        "\uD531": "$\\mfrakt$",  # MATHEMATICAL FRAKTUR SMALL T
        "\uD532": "$\\mfraku$",  # MATHEMATICAL FRAKTUR SMALL U
        "\uD533": "$\\mfrakv$",  # MATHEMATICAL FRAKTUR SMALL V
        "\uD534": "$\\mfrakw$",  # MATHEMATICAL FRAKTUR SMALL W
        "\uD535": "$\\mfrakx$",  # MATHEMATICAL FRAKTUR SMALL X
        "\uD536": "$\\mfraky$",  # MATHEMATICAL FRAKTUR SMALL Y
        "\uD537": "$\\mfrakz$",  # MATHEMATICAL FRAKTUR SMALL Z
        "\uD538": "$\\BbbA$",  # MATHEMATICAL DOUBLE-STRUCK CAPITAL A
        "\uD539": "$\\BbbB$",  # MATHEMATICAL DOUBLE-STRUCK CAPITAL B
        "\uD53B": "$\\BbbD$",  # MATHEMATICAL DOUBLE-STRUCK CAPITAL D
        "\uD53C": "$\\BbbE$",  # MATHEMATICAL DOUBLE-STRUCK CAPITAL E
        "\uD53D": "$\\BbbF$",  # MATHEMATICAL DOUBLE-STRUCK CAPITAL F
        "\uD53E": "$\\BbbG$",  # MATHEMATICAL DOUBLE-STRUCK CAPITAL G
        "\uD540": "$\\BbbI$",  # MATHEMATICAL DOUBLE-STRUCK CAPITAL I
        "\uD541": "$\\BbbJ$",  # MATHEMATICAL DOUBLE-STRUCK CAPITAL J
        "\uD542": "$\\BbbK$",  # MATHEMATICAL DOUBLE-STRUCK CAPITAL K
        "\uD543": "$\\BbbL$",  # MATHEMATICAL DOUBLE-STRUCK CAPITAL L
        "\uD544": "$\\BbbM$",  # MATHEMATICAL DOUBLE-STRUCK CAPITAL M
        "\uD546": "$\\BbbO$",  # MATHEMATICAL DOUBLE-STRUCK CAPITAL O
        "\uD54A": "$\\BbbS$",  # MATHEMATICAL DOUBLE-STRUCK CAPITAL S
        "\uD54B": "$\\BbbT$",  # MATHEMATICAL DOUBLE-STRUCK CAPITAL T
        "\uD54C": "$\\BbbU$",  # MATHEMATICAL DOUBLE-STRUCK CAPITAL U
        "\uD54D": "$\\BbbV$",  # MATHEMATICAL DOUBLE-STRUCK CAPITAL V
        "\uD54E": "$\\BbbW$",  # MATHEMATICAL DOUBLE-STRUCK CAPITAL W
        "\uD54F": "$\\BbbX$",  # MATHEMATICAL DOUBLE-STRUCK CAPITAL X
        "\uD550": "$\\BbbY$",  # MATHEMATICAL DOUBLE-STRUCK CAPITAL Y
        "\uD552": "$\\Bbba$",  # MATHEMATICAL DOUBLE-STRUCK SMALL A
        "\uD553": "$\\Bbbb$",  # MATHEMATICAL DOUBLE-STRUCK SMALL B
        "\uD554": "$\\Bbbc$",  # MATHEMATICAL DOUBLE-STRUCK SMALL C
        "\uD555": "$\\Bbbd$",  # MATHEMATICAL DOUBLE-STRUCK SMALL D
        "\uD556": "$\\Bbbe$",  # MATHEMATICAL DOUBLE-STRUCK SMALL E
        "\uD557": "$\\Bbbf$",  # MATHEMATICAL DOUBLE-STRUCK SMALL F
        "\uD558": "$\\Bbbg$",  # MATHEMATICAL DOUBLE-STRUCK SMALL G
        "\uD559": "$\\Bbbh$",  # MATHEMATICAL DOUBLE-STRUCK SMALL H
        "\uD55A": "$\\Bbbi$",  # MATHEMATICAL DOUBLE-STRUCK SMALL I
        "\uD55B": "$\\Bbbj$",  # MATHEMATICAL DOUBLE-STRUCK SMALL J
        "\uD55C": "$\\Bbbk$",  # MATHEMATICAL DOUBLE-STRUCK SMALL K
        "\uD55D": "$\\Bbbl$",  # MATHEMATICAL DOUBLE-STRUCK SMALL L
        "\uD55E": "$\\Bbbm$",  # MATHEMATICAL DOUBLE-STRUCK SMALL M
        "\uD55F": "$\\Bbbn$",  # MATHEMATICAL DOUBLE-STRUCK SMALL N
        "\uD560": "$\\Bbbo$",  # MATHEMATICAL DOUBLE-STRUCK SMALL O
        "\uD561": "$\\Bbbp$",  # MATHEMATICAL DOUBLE-STRUCK SMALL P
        "\uD562": "$\\Bbbq$",  # MATHEMATICAL DOUBLE-STRUCK SMALL Q
        "\uD563": "$\\Bbbr$",  # MATHEMATICAL DOUBLE-STRUCK SMALL R
        "\uD564": "$\\Bbbs$",  # MATHEMATICAL DOUBLE-STRUCK SMALL S
        "\uD565": "$\\Bbbt$",  # MATHEMATICAL DOUBLE-STRUCK SMALL T
        "\uD566": "$\\Bbbu$",  # MATHEMATICAL DOUBLE-STRUCK SMALL U
        "\uD567": "$\\Bbbv$",  # MATHEMATICAL DOUBLE-STRUCK SMALL V
        "\uD568": "$\\Bbbw$",  # MATHEMATICAL DOUBLE-STRUCK SMALL W
        "\uD569": "$\\Bbbx$",  # MATHEMATICAL DOUBLE-STRUCK SMALL X
        "\uD56A": "$\\Bbby$",  # MATHEMATICAL DOUBLE-STRUCK SMALL Y
        "\uD56B": "$\\Bbbz$",  # MATHEMATICAL DOUBLE-STRUCK SMALL Z
        "\uD56C": "$\\mbffrakA$",  # MATHEMATICAL BOLD FRAKTUR CAPITAL A
        "\uD56D": "$\\mbffrakB$",  # MATHEMATICAL BOLD FRAKTUR CAPITAL B
        "\uD56E": "$\\mbffrakC$",  # MATHEMATICAL BOLD FRAKTUR CAPITAL C
        "\uD56F": "$\\mbffrakD$",  # MATHEMATICAL BOLD FRAKTUR CAPITAL D
        "\uD570": "$\\mbffrakE$",  # MATHEMATICAL BOLD FRAKTUR CAPITAL E
        "\uD571": "$\\mbffrakF$",  # MATHEMATICAL BOLD FRAKTUR CAPITAL F
        "\uD572": "$\\mbffrakG$",  # MATHEMATICAL BOLD FRAKTUR CAPITAL G
        "\uD573": "$\\mbffrakH$",  # MATHEMATICAL BOLD FRAKTUR CAPITAL H
        "\uD574": "$\\mbffrakI$",  # MATHEMATICAL BOLD FRAKTUR CAPITAL I
        "\uD575": "$\\mbffrakJ$",  # MATHEMATICAL BOLD FRAKTUR CAPITAL J
        "\uD576": "$\\mbffrakK$",  # MATHEMATICAL BOLD FRAKTUR CAPITAL K
        "\uD577": "$\\mbffrakL$",  # MATHEMATICAL BOLD FRAKTUR CAPITAL L
        "\uD578": "$\\mbffrakM$",  # MATHEMATICAL BOLD FRAKTUR CAPITAL M
        "\uD579": "$\\mbffrakN$",  # MATHEMATICAL BOLD FRAKTUR CAPITAL N
        "\uD57A": "$\\mbffrakO$",  # MATHEMATICAL BOLD FRAKTUR CAPITAL O
        "\uD57B": "$\\mbffrakP$",  # MATHEMATICAL BOLD FRAKTUR CAPITAL P
        "\uD57C": "$\\mbffrakQ$",  # MATHEMATICAL BOLD FRAKTUR CAPITAL Q
        "\uD57D": "$\\mbffrakR$",  # MATHEMATICAL BOLD FRAKTUR CAPITAL R
        "\uD57E": "$\\mbffrakS$",  # MATHEMATICAL BOLD FRAKTUR CAPITAL S
        "\uD57F": "$\\mbffrakT$",  # MATHEMATICAL BOLD FRAKTUR CAPITAL T
        "\uD580": "$\\mbffrakU$",  # MATHEMATICAL BOLD FRAKTUR CAPITAL U
        "\uD581": "$\\mbffrakV$",  # MATHEMATICAL BOLD FRAKTUR CAPITAL V
        "\uD582": "$\\mbffrakW$",  # MATHEMATICAL BOLD FRAKTUR CAPITAL W
        "\uD583": "$\\mbffrakX$",  # MATHEMATICAL BOLD FRAKTUR CAPITAL X
        "\uD584": "$\\mbffrakY$",  # MATHEMATICAL BOLD FRAKTUR CAPITAL Y
        "\uD585": "$\\mbffrakZ$",  # MATHEMATICAL BOLD FRAKTUR CAPITAL Z
        "\uD586": "$\\mbffraka$",  # MATHEMATICAL BOLD FRAKTUR SMALL A
        "\uD587": "$\\mbffrakb$",  # MATHEMATICAL BOLD FRAKTUR SMALL B
        "\uD588": "$\\mbffrakc$",  # MATHEMATICAL BOLD FRAKTUR SMALL C
        "\uD589": "$\\mbffrakd$",  # MATHEMATICAL BOLD FRAKTUR SMALL D
        "\uD58A": "$\\mbffrake$",  # MATHEMATICAL BOLD FRAKTUR SMALL E
        "\uD58B": "$\\mbffrakf$",  # MATHEMATICAL BOLD FRAKTUR SMALL F
        "\uD58C": "$\\mbffrakg$",  # MATHEMATICAL BOLD FRAKTUR SMALL G
        "\uD58D": "$\\mbffrakh$",  # MATHEMATICAL BOLD FRAKTUR SMALL H
        "\uD58E": "$\\mbffraki$",  # MATHEMATICAL BOLD FRAKTUR SMALL I
        "\uD58F": "$\\mbffrakj$",  # MATHEMATICAL BOLD FRAKTUR SMALL J
        "\uD590": "$\\mbffrakk$",  # MATHEMATICAL BOLD FRAKTUR SMALL K
        "\uD591": "$\\mbffrakl$",  # MATHEMATICAL BOLD FRAKTUR SMALL L
        "\uD592": "$\\mbffrakm$",  # MATHEMATICAL BOLD FRAKTUR SMALL M
        "\uD593": "$\\mbffrakn$",  # MATHEMATICAL BOLD FRAKTUR SMALL N
        "\uD594": "$\\mbffrako$",  # MATHEMATICAL BOLD FRAKTUR SMALL O
        "\uD595": "$\\mbffrakp$",  # MATHEMATICAL BOLD FRAKTUR SMALL P
        "\uD596": "$\\mbffrakq$",  # MATHEMATICAL BOLD FRAKTUR SMALL Q
        "\uD597": "$\\mbffrakr$",  # MATHEMATICAL BOLD FRAKTUR SMALL R
        "\uD598": "$\\mbffraks$",  # MATHEMATICAL BOLD FRAKTUR SMALL S
        "\uD599": "$\\mbffrakt$",  # MATHEMATICAL BOLD FRAKTUR SMALL T
        "\uD59A": "$\\mbffraku$",  # MATHEMATICAL BOLD FRAKTUR SMALL U
        "\uD59B": "$\\mbffrakv$",  # MATHEMATICAL BOLD FRAKTUR SMALL V
        "\uD59C": "$\\mbffrakw$",  # MATHEMATICAL BOLD FRAKTUR SMALL W
        "\uD59D": "$\\mbffrakx$",  # MATHEMATICAL BOLD FRAKTUR SMALL X
        "\uD59E": "$\\mbffraky$",  # MATHEMATICAL BOLD FRAKTUR SMALL Y
        "\uD59F": "$\\mbffrakz$",  # MATHEMATICAL BOLD FRAKTUR SMALL Z
        "\uD5A0": "$\\msansA$",  # MATHEMATICAL SANS-SERIF CAPITAL A
        "\uD5A1": "$\\msansB$",  # MATHEMATICAL SANS-SERIF CAPITAL B
        "\uD5A2": "$\\msansC$",  # MATHEMATICAL SANS-SERIF CAPITAL C
        "\uD5A3": "$\\msansD$",  # MATHEMATICAL SANS-SERIF CAPITAL D
        "\uD5A4": "$\\msansE$",  # MATHEMATICAL SANS-SERIF CAPITAL E
        "\uD5A5": "$\\msansF$",  # MATHEMATICAL SANS-SERIF CAPITAL F
        "\uD5A6": "$\\msansG$",  # MATHEMATICAL SANS-SERIF CAPITAL G
        "\uD5A7": "$\\msansH$",  # MATHEMATICAL SANS-SERIF CAPITAL H
        "\uD5A8": "$\\msansI$",  # MATHEMATICAL SANS-SERIF CAPITAL I
        "\uD5A9": "$\\msansJ$",  # MATHEMATICAL SANS-SERIF CAPITAL J
        "\uD5AA": "$\\msansK$",  # MATHEMATICAL SANS-SERIF CAPITAL K
        "\uD5AB": "$\\msansL$",  # MATHEMATICAL SANS-SERIF CAPITAL L
        "\uD5AC": "$\\msansM$",  # MATHEMATICAL SANS-SERIF CAPITAL M
        "\uD5AD": "$\\msansN$",  # MATHEMATICAL SANS-SERIF CAPITAL N
        "\uD5AE": "$\\msansO$",  # MATHEMATICAL SANS-SERIF CAPITAL O
        "\uD5AF": "$\\msansP$",  # MATHEMATICAL SANS-SERIF CAPITAL P
        "\uD5B0": "$\\msansQ$",  # MATHEMATICAL SANS-SERIF CAPITAL Q
        "\uD5B1": "$\\msansR$",  # MATHEMATICAL SANS-SERIF CAPITAL R
        "\uD5B2": "$\\msansS$",  # MATHEMATICAL SANS-SERIF CAPITAL S
        "\uD5B3": "$\\msansT$",  # MATHEMATICAL SANS-SERIF CAPITAL T
        "\uD5B4": "$\\msansU$",  # MATHEMATICAL SANS-SERIF CAPITAL U
        "\uD5B5": "$\\msansV$",  # MATHEMATICAL SANS-SERIF CAPITAL V
        "\uD5B6": "$\\msansW$",  # MATHEMATICAL SANS-SERIF CAPITAL W
        "\uD5B7": "$\\msansX$",  # MATHEMATICAL SANS-SERIF CAPITAL X
        "\uD5B8": "$\\msansY$",  # MATHEMATICAL SANS-SERIF CAPITAL Y
        "\uD5B9": "$\\msansZ$",  # MATHEMATICAL SANS-SERIF CAPITAL Z
        "\uD5BA": "$\\msansa$",  # MATHEMATICAL SANS-SERIF SMALL A
        "\uD5BB": "$\\msansb$",  # MATHEMATICAL SANS-SERIF SMALL B
        "\uD5BC": "$\\msansc$",  # MATHEMATICAL SANS-SERIF SMALL C
        "\uD5BD": "$\\msansd$",  # MATHEMATICAL SANS-SERIF SMALL D
        "\uD5BE": "$\\msanse$",  # MATHEMATICAL SANS-SERIF SMALL E
        "\uD5BF": "$\\msansf$",  # MATHEMATICAL SANS-SERIF SMALL F
        "\uD5C0": "$\\msansg$",  # MATHEMATICAL SANS-SERIF SMALL G
        "\uD5C1": "$\\msansh$",  # MATHEMATICAL SANS-SERIF SMALL H
        "\uD5C2": "$\\msansi$",  # MATHEMATICAL SANS-SERIF SMALL I
        "\uD5C3": "$\\msansj$",  # MATHEMATICAL SANS-SERIF SMALL J
        "\uD5C4": "$\\msansk$",  # MATHEMATICAL SANS-SERIF SMALL K
        "\uD5C5": "$\\msansl$",  # MATHEMATICAL SANS-SERIF SMALL L
        "\uD5C6": "$\\msansm$",  # MATHEMATICAL SANS-SERIF SMALL M
        "\uD5C7": "$\\msansn$",  # MATHEMATICAL SANS-SERIF SMALL N
        "\uD5C8": "$\\msanso$",  # MATHEMATICAL SANS-SERIF SMALL O
        "\uD5C9": "$\\msansp$",  # MATHEMATICAL SANS-SERIF SMALL P
        "\uD5CA": "$\\msansq$",  # MATHEMATICAL SANS-SERIF SMALL Q
        "\uD5CB": "$\\msansr$",  # MATHEMATICAL SANS-SERIF SMALL R
        "\uD5CC": "$\\msanss$",  # MATHEMATICAL SANS-SERIF SMALL S
        "\uD5CD": "$\\msanst$",  # MATHEMATICAL SANS-SERIF SMALL T
        "\uD5CE": "$\\msansu$",  # MATHEMATICAL SANS-SERIF SMALL U
        "\uD5CF": "$\\msansv$",  # MATHEMATICAL SANS-SERIF SMALL V
        "\uD5D0": "$\\msansw$",  # MATHEMATICAL SANS-SERIF SMALL W
        "\uD5D1": "$\\msansx$",  # MATHEMATICAL SANS-SERIF SMALL X
        "\uD5D2": "$\\msansy$",  # MATHEMATICAL SANS-SERIF SMALL Y
        "\uD5D3": "$\\msansz$",  # MATHEMATICAL SANS-SERIF SMALL Z
        "\uD5D4": "$\\mbfsansA$",  # MATHEMATICAL SANS-SERIF BOLD CAPITAL A
        "\uD5D5": "$\\mbfsansB$",  # MATHEMATICAL SANS-SERIF BOLD CAPITAL B
        "\uD5D6": "$\\mbfsansC$",  # MATHEMATICAL SANS-SERIF BOLD CAPITAL C
        "\uD5D7": "$\\mbfsansD$",  # MATHEMATICAL SANS-SERIF BOLD CAPITAL D
        "\uD5D8": "$\\mbfsansE$",  # MATHEMATICAL SANS-SERIF BOLD CAPITAL E
        "\uD5D9": "$\\mbfsansF$",  # MATHEMATICAL SANS-SERIF BOLD CAPITAL F
        "\uD5DA": "$\\mbfsansG$",  # MATHEMATICAL SANS-SERIF BOLD CAPITAL G
        "\uD5DB": "$\\mbfsansH$",  # MATHEMATICAL SANS-SERIF BOLD CAPITAL H
        "\uD5DC": "$\\mbfsansI$",  # MATHEMATICAL SANS-SERIF BOLD CAPITAL I
        "\uD5DD": "$\\mbfsansJ$",  # MATHEMATICAL SANS-SERIF BOLD CAPITAL J
        "\uD5DE": "$\\mbfsansK$",  # MATHEMATICAL SANS-SERIF BOLD CAPITAL K
        "\uD5DF": "$\\mbfsansL$",  # MATHEMATICAL SANS-SERIF BOLD CAPITAL L
        "\uD5E0": "$\\mbfsansM$",  # MATHEMATICAL SANS-SERIF BOLD CAPITAL M
        "\uD5E1": "$\\mbfsansN$",  # MATHEMATICAL SANS-SERIF BOLD CAPITAL N
        "\uD5E2": "$\\mbfsansO$",  # MATHEMATICAL SANS-SERIF BOLD CAPITAL O
        "\uD5E3": "$\\mbfsansP$",  # MATHEMATICAL SANS-SERIF BOLD CAPITAL P
        "\uD5E4": "$\\mbfsansQ$",  # MATHEMATICAL SANS-SERIF BOLD CAPITAL Q
        "\uD5E5": "$\\mbfsansR$",  # MATHEMATICAL SANS-SERIF BOLD CAPITAL R
        "\uD5E6": "$\\mbfsansS$",  # MATHEMATICAL SANS-SERIF BOLD CAPITAL S
        "\uD5E7": "$\\mbfsansT$",  # MATHEMATICAL SANS-SERIF BOLD CAPITAL T
        "\uD5E8": "$\\mbfsansU$",  # MATHEMATICAL SANS-SERIF BOLD CAPITAL U
        "\uD5E9": "$\\mbfsansV$",  # MATHEMATICAL SANS-SERIF BOLD CAPITAL V
        "\uD5EA": "$\\mbfsansW$",  # MATHEMATICAL SANS-SERIF BOLD CAPITAL W
        "\uD5EB": "$\\mbfsansX$",  # MATHEMATICAL SANS-SERIF BOLD CAPITAL X
        "\uD5EC": "$\\mbfsansY$",  # MATHEMATICAL SANS-SERIF BOLD CAPITAL Y
        "\uD5ED": "$\\mbfsansZ$",  # MATHEMATICAL SANS-SERIF BOLD CAPITAL Z
        "\uD5EE": "$\\mbfsansa$",  # MATHEMATICAL SANS-SERIF BOLD SMALL A
        "\uD5EF": "$\\mbfsansb$",  # MATHEMATICAL SANS-SERIF BOLD SMALL B
        "\uD5F0": "$\\mbfsansc$",  # MATHEMATICAL SANS-SERIF BOLD SMALL C
        "\uD5F1": "$\\mbfsansd$",  # MATHEMATICAL SANS-SERIF BOLD SMALL D
        "\uD5F2": "$\\mbfsanse$",  # MATHEMATICAL SANS-SERIF BOLD SMALL E
        "\uD5F3": "$\\mbfsansf$",  # MATHEMATICAL SANS-SERIF BOLD SMALL F
        "\uD5F4": "$\\mbfsansg$",  # MATHEMATICAL SANS-SERIF BOLD SMALL G
        "\uD5F5": "$\\mbfsansh$",  # MATHEMATICAL SANS-SERIF BOLD SMALL H
        "\uD5F6": "$\\mbfsansi$",  # MATHEMATICAL SANS-SERIF BOLD SMALL I
        "\uD5F7": "$\\mbfsansj$",  # MATHEMATICAL SANS-SERIF BOLD SMALL J
        "\uD5F8": "$\\mbfsansk$",  # MATHEMATICAL SANS-SERIF BOLD SMALL K
        "\uD5F9": "$\\mbfsansl$",  # MATHEMATICAL SANS-SERIF BOLD SMALL L
        "\uD5FA": "$\\mbfsansm$",  # MATHEMATICAL SANS-SERIF BOLD SMALL M
        "\uD5FB": "$\\mbfsansn$",  # MATHEMATICAL SANS-SERIF BOLD SMALL N
        "\uD5FC": "$\\mbfsanso$",  # MATHEMATICAL SANS-SERIF BOLD SMALL O
        "\uD5FD": "$\\mbfsansp$",  # MATHEMATICAL SANS-SERIF BOLD SMALL P
        "\uD5FE": "$\\mbfsansq$",  # MATHEMATICAL SANS-SERIF BOLD SMALL Q
        "\uD5FF": "$\\mbfsansr$",  # MATHEMATICAL SANS-SERIF BOLD SMALL R
        "\uD600": "$\\mbfsanss$",  # MATHEMATICAL SANS-SERIF BOLD SMALL S
        "\uD601": "$\\mbfsanst$",  # MATHEMATICAL SANS-SERIF BOLD SMALL T
        "\uD602": "$\\mbfsansu$",  # MATHEMATICAL SANS-SERIF BOLD SMALL U
        "\uD603": "$\\mbfsansv$",  # MATHEMATICAL SANS-SERIF BOLD SMALL V
        "\uD604": "$\\mbfsansw$",  # MATHEMATICAL SANS-SERIF BOLD SMALL W
        "\uD605": "$\\mbfsansx$",  # MATHEMATICAL SANS-SERIF BOLD SMALL X
        "\uD606": "$\\mbfsansy$",  # MATHEMATICAL SANS-SERIF BOLD SMALL Y
        "\uD607": "$\\mbfsansz$",  # MATHEMATICAL SANS-SERIF BOLD SMALL Z
        "\uD608": "$\\mitsansA$",  # MATHEMATICAL SANS-SERIF ITALIC CAPITAL A
        "\uD609": "$\\mitsansB$",  # MATHEMATICAL SANS-SERIF ITALIC CAPITAL B
        "\uD60A": "$\\mitsansC$",  # MATHEMATICAL SANS-SERIF ITALIC CAPITAL C
        "\uD60B": "$\\mitsansD$",  # MATHEMATICAL SANS-SERIF ITALIC CAPITAL D
        "\uD60C": "$\\mitsansE$",  # MATHEMATICAL SANS-SERIF ITALIC CAPITAL E
        "\uD60D": "$\\mitsansF$",  # MATHEMATICAL SANS-SERIF ITALIC CAPITAL F
        "\uD60E": "$\\mitsansG$",  # MATHEMATICAL SANS-SERIF ITALIC CAPITAL G
        "\uD60F": "$\\mitsansH$",  # MATHEMATICAL SANS-SERIF ITALIC CAPITAL H
        "\uD610": "$\\mitsansI$",  # MATHEMATICAL SANS-SERIF ITALIC CAPITAL I
        "\uD611": "$\\mitsansJ$",  # MATHEMATICAL SANS-SERIF ITALIC CAPITAL J
        "\uD612": "$\\mitsansK$",  # MATHEMATICAL SANS-SERIF ITALIC CAPITAL K
        "\uD613": "$\\mitsansL$",  # MATHEMATICAL SANS-SERIF ITALIC CAPITAL L
        "\uD614": "$\\mitsansM$",  # MATHEMATICAL SANS-SERIF ITALIC CAPITAL M
        "\uD615": "$\\mitsansN$",  # MATHEMATICAL SANS-SERIF ITALIC CAPITAL N
        "\uD616": "$\\mitsansO$",  # MATHEMATICAL SANS-SERIF ITALIC CAPITAL O
        "\uD617": "$\\mitsansP$",  # MATHEMATICAL SANS-SERIF ITALIC CAPITAL P
        "\uD618": "$\\mitsansQ$",  # MATHEMATICAL SANS-SERIF ITALIC CAPITAL Q
        "\uD619": "$\\mitsansR$",  # MATHEMATICAL SANS-SERIF ITALIC CAPITAL R
        "\uD61A": "$\\mitsansS$",  # MATHEMATICAL SANS-SERIF ITALIC CAPITAL S
        "\uD61B": "$\\mitsansT$",  # MATHEMATICAL SANS-SERIF ITALIC CAPITAL T
        "\uD61C": "$\\mitsansU$",  # MATHEMATICAL SANS-SERIF ITALIC CAPITAL U
        "\uD61D": "$\\mitsansV$",  # MATHEMATICAL SANS-SERIF ITALIC CAPITAL V
        "\uD61E": "$\\mitsansW$",  # MATHEMATICAL SANS-SERIF ITALIC CAPITAL W
        "\uD61F": "$\\mitsansX$",  # MATHEMATICAL SANS-SERIF ITALIC CAPITAL X
        "\uD620": "$\\mitsansY$",  # MATHEMATICAL SANS-SERIF ITALIC CAPITAL Y
        "\uD621": "$\\mitsansZ$",  # MATHEMATICAL SANS-SERIF ITALIC CAPITAL Z
        "\uD622": "$\\mitsansa$",  # MATHEMATICAL SANS-SERIF ITALIC SMALL A
        "\uD623": "$\\mitsansb$",  # MATHEMATICAL SANS-SERIF ITALIC SMALL B
        "\uD624": "$\\mitsansc$",  # MATHEMATICAL SANS-SERIF ITALIC SMALL C
        "\uD625": "$\\mitsansd$",  # MATHEMATICAL SANS-SERIF ITALIC SMALL D
        "\uD626": "$\\mitsanse$",  # MATHEMATICAL SANS-SERIF ITALIC SMALL E
        "\uD627": "$\\mitsansf$",  # MATHEMATICAL SANS-SERIF ITALIC SMALL F
        "\uD628": "$\\mitsansg$",  # MATHEMATICAL SANS-SERIF ITALIC SMALL G
        "\uD629": "$\\mitsansh$",  # MATHEMATICAL SANS-SERIF ITALIC SMALL H
        "\uD62A": "$\\mitsansi$",  # MATHEMATICAL SANS-SERIF ITALIC SMALL I
        "\uD62B": "$\\mitsansj$",  # MATHEMATICAL SANS-SERIF ITALIC SMALL J
        "\uD62C": "$\\mitsansk$",  # MATHEMATICAL SANS-SERIF ITALIC SMALL K
        "\uD62D": "$\\mitsansl$",  # MATHEMATICAL SANS-SERIF ITALIC SMALL L
        "\uD62E": "$\\mitsansm$",  # MATHEMATICAL SANS-SERIF ITALIC SMALL M
        "\uD62F": "$\\mitsansn$",  # MATHEMATICAL SANS-SERIF ITALIC SMALL N
        "\uD630": "$\\mitsanso$",  # MATHEMATICAL SANS-SERIF ITALIC SMALL O
        "\uD631": "$\\mitsansp$",  # MATHEMATICAL SANS-SERIF ITALIC SMALL P
        "\uD632": "$\\mitsansq$",  # MATHEMATICAL SANS-SERIF ITALIC SMALL Q
        "\uD633": "$\\mitsansr$",  # MATHEMATICAL SANS-SERIF ITALIC SMALL R
        "\uD634": "$\\mitsanss$",  # MATHEMATICAL SANS-SERIF ITALIC SMALL S
        "\uD635": "$\\mitsanst$",  # MATHEMATICAL SANS-SERIF ITALIC SMALL T
        "\uD636": "$\\mitsansu$",  # MATHEMATICAL SANS-SERIF ITALIC SMALL U
        "\uD637": "$\\mitsansv$",  # MATHEMATICAL SANS-SERIF ITALIC SMALL V
        "\uD638": "$\\mitsansw$",  # MATHEMATICAL SANS-SERIF ITALIC SMALL W
        "\uD639": "$\\mitsansx$",  # MATHEMATICAL SANS-SERIF ITALIC SMALL X
        "\uD63A": "$\\mitsansy$",  # MATHEMATICAL SANS-SERIF ITALIC SMALL Y
        "\uD63B": "$\\mitsansz$",  # MATHEMATICAL SANS-SERIF ITALIC SMALL Z
        "\uD63C": "$\\mbfitsansA$",  # MATHEMATICAL SANS-SERIF BOLD ITALIC CAPITAL A
        "\uD63D": "$\\mbfitsansB$",  # MATHEMATICAL SANS-SERIF BOLD ITALIC CAPITAL B
        "\uD63E": "$\\mbfitsansC$",  # MATHEMATICAL SANS-SERIF BOLD ITALIC CAPITAL C
        "\uD63F": "$\\mbfitsansD$",  # MATHEMATICAL SANS-SERIF BOLD ITALIC CAPITAL D
        "\uD640": "$\\mbfitsansE$",  # MATHEMATICAL SANS-SERIF BOLD ITALIC CAPITAL E
        "\uD641": "$\\mbfitsansF$",  # MATHEMATICAL SANS-SERIF BOLD ITALIC CAPITAL F
        "\uD642": "$\\mbfitsansG$",  # MATHEMATICAL SANS-SERIF BOLD ITALIC CAPITAL G
        "\uD643": "$\\mbfitsansH$",  # MATHEMATICAL SANS-SERIF BOLD ITALIC CAPITAL H
        "\uD644": "$\\mbfitsansI$",  # MATHEMATICAL SANS-SERIF BOLD ITALIC CAPITAL I
        "\uD645": "$\\mbfitsansJ$",  # MATHEMATICAL SANS-SERIF BOLD ITALIC CAPITAL J
        "\uD646": "$\\mbfitsansK$",  # MATHEMATICAL SANS-SERIF BOLD ITALIC CAPITAL K
        "\uD647": "$\\mbfitsansL$",  # MATHEMATICAL SANS-SERIF BOLD ITALIC CAPITAL L
        "\uD648": "$\\mbfitsansM$",  # MATHEMATICAL SANS-SERIF BOLD ITALIC CAPITAL M
        "\uD649": "$\\mbfitsansN$",  # MATHEMATICAL SANS-SERIF BOLD ITALIC CAPITAL N
        "\uD64A": "$\\mbfitsansO$",  # MATHEMATICAL SANS-SERIF BOLD ITALIC CAPITAL O
        "\uD64B": "$\\mbfitsansP$",  # MATHEMATICAL SANS-SERIF BOLD ITALIC CAPITAL P
        "\uD64C": "$\\mbfitsansQ$",  # MATHEMATICAL SANS-SERIF BOLD ITALIC CAPITAL Q
        "\uD64D": "$\\mbfitsansR$",  # MATHEMATICAL SANS-SERIF BOLD ITALIC CAPITAL R
        "\uD64E": "$\\mbfitsansS$",  # MATHEMATICAL SANS-SERIF BOLD ITALIC CAPITAL S
        "\uD64F": "$\\mbfitsansT$",  # MATHEMATICAL SANS-SERIF BOLD ITALIC CAPITAL T
        "\uD650": "$\\mbfitsansU$",  # MATHEMATICAL SANS-SERIF BOLD ITALIC CAPITAL U
        "\uD651": "$\\mbfitsansV$",  # MATHEMATICAL SANS-SERIF BOLD ITALIC CAPITAL V
        "\uD652": "$\\mbfitsansW$",  # MATHEMATICAL SANS-SERIF BOLD ITALIC CAPITAL W
        "\uD653": "$\\mbfitsansX$",  # MATHEMATICAL SANS-SERIF BOLD ITALIC CAPITAL X
        "\uD654": "$\\mbfitsansY$",  # MATHEMATICAL SANS-SERIF BOLD ITALIC CAPITAL Y
        "\uD655": "$\\mbfitsansZ$",  # MATHEMATICAL SANS-SERIF BOLD ITALIC CAPITAL Z
        "\uD656": "$\\mbfitsansa$",  # MATHEMATICAL SANS-SERIF BOLD ITALIC SMALL A
        "\uD657": "$\\mbfitsansb$",  # MATHEMATICAL SANS-SERIF BOLD ITALIC SMALL B
        "\uD658": "$\\mbfitsansc$",  # MATHEMATICAL SANS-SERIF BOLD ITALIC SMALL C
        "\uD659": "$\\mbfitsansd$",  # MATHEMATICAL SANS-SERIF BOLD ITALIC SMALL D
        "\uD65A": "$\\mbfitsanse$",  # MATHEMATICAL SANS-SERIF BOLD ITALIC SMALL E
        "\uD65B": "$\\mbfitsansf$",  # MATHEMATICAL SANS-SERIF BOLD ITALIC SMALL F
        "\uD65C": "$\\mbfitsansg$",  # MATHEMATICAL SANS-SERIF BOLD ITALIC SMALL G
        "\uD65D": "$\\mbfitsansh$",  # MATHEMATICAL SANS-SERIF BOLD ITALIC SMALL H
        "\uD65E": "$\\mbfitsansi$",  # MATHEMATICAL SANS-SERIF BOLD ITALIC SMALL I
        "\uD65F": "$\\mbfitsansj$",  # MATHEMATICAL SANS-SERIF BOLD ITALIC SMALL J
        "\uD660": "$\\mbfitsansk$",  # MATHEMATICAL SANS-SERIF BOLD ITALIC SMALL K
        "\uD661": "$\\mbfitsansl$",  # MATHEMATICAL SANS-SERIF BOLD ITALIC SMALL L
        "\uD662": "$\\mbfitsansm$",  # MATHEMATICAL SANS-SERIF BOLD ITALIC SMALL M
        "\uD663": "$\\mbfitsansn$",  # MATHEMATICAL SANS-SERIF BOLD ITALIC SMALL N
        "\uD664": "$\\mbfitsanso$",  # MATHEMATICAL SANS-SERIF BOLD ITALIC SMALL O
        "\uD665": "$\\mbfitsansp$",  # MATHEMATICAL SANS-SERIF BOLD ITALIC SMALL P
        "\uD666": "$\\mbfitsansq$",  # MATHEMATICAL SANS-SERIF BOLD ITALIC SMALL Q
        "\uD667": "$\\mbfitsansr$",  # MATHEMATICAL SANS-SERIF BOLD ITALIC SMALL R
        "\uD668": "$\\mbfitsanss$",  # MATHEMATICAL SANS-SERIF BOLD ITALIC SMALL S
        "\uD669": "$\\mbfitsanst$",  # MATHEMATICAL SANS-SERIF BOLD ITALIC SMALL T
        "\uD66A": "$\\mbfitsansu$",  # MATHEMATICAL SANS-SERIF BOLD ITALIC SMALL U
        "\uD66B": "$\\mbfitsansv$",  # MATHEMATICAL SANS-SERIF BOLD ITALIC SMALL V
        "\uD66C": "$\\mbfitsansw$",  # MATHEMATICAL SANS-SERIF BOLD ITALIC SMALL W
        "\uD66D": "$\\mbfitsansx$",  # MATHEMATICAL SANS-SERIF BOLD ITALIC SMALL X
        "\uD66E": "$\\mbfitsansy$",  # MATHEMATICAL SANS-SERIF BOLD ITALIC SMALL Y
        "\uD66F": "$\\mbfitsansz$",  # MATHEMATICAL SANS-SERIF BOLD ITALIC SMALL Z
        "\uD670": "$\\mttA$",  # MATHEMATICAL MONOSPACE CAPITAL A
        "\uD671": "$\\mttB$",  # MATHEMATICAL MONOSPACE CAPITAL B
        "\uD672": "$\\mttC$",  # MATHEMATICAL MONOSPACE CAPITAL C
        "\uD673": "$\\mttD$",  # MATHEMATICAL MONOSPACE CAPITAL D
        "\uD674": "$\\mttE$",  # MATHEMATICAL MONOSPACE CAPITAL E
        "\uD675": "$\\mttF$",  # MATHEMATICAL MONOSPACE CAPITAL F
        "\uD676": "$\\mttG$",  # MATHEMATICAL MONOSPACE CAPITAL G
        "\uD677": "$\\mttH$",  # MATHEMATICAL MONOSPACE CAPITAL H
        "\uD678": "$\\mttI$",  # MATHEMATICAL MONOSPACE CAPITAL I
        "\uD679": "$\\mttJ$",  # MATHEMATICAL MONOSPACE CAPITAL J
        "\uD67A": "$\\mttK$",  # MATHEMATICAL MONOSPACE CAPITAL K
        "\uD67B": "$\\mttL$",  # MATHEMATICAL MONOSPACE CAPITAL L
        "\uD67C": "$\\mttM$",  # MATHEMATICAL MONOSPACE CAPITAL M
        "\uD67D": "$\\mttN$",  # MATHEMATICAL MONOSPACE CAPITAL N
        "\uD67E": "$\\mttO$",  # MATHEMATICAL MONOSPACE CAPITAL O
        "\uD67F": "$\\mttP$",  # MATHEMATICAL MONOSPACE CAPITAL P
        "\uD680": "$\\mttQ$",  # MATHEMATICAL MONOSPACE CAPITAL Q
        "\uD681": "$\\mttR$",  # MATHEMATICAL MONOSPACE CAPITAL R
        "\uD682": "$\\mttS$",  # MATHEMATICAL MONOSPACE CAPITAL S
        "\uD683": "$\\mttT$",  # MATHEMATICAL MONOSPACE CAPITAL T
        "\uD684": "$\\mttU$",  # MATHEMATICAL MONOSPACE CAPITAL U
        "\uD685": "$\\mttV$",  # MATHEMATICAL MONOSPACE CAPITAL V
        "\uD686": "$\\mttW$",  # MATHEMATICAL MONOSPACE CAPITAL W
        "\uD687": "$\\mttX$",  # MATHEMATICAL MONOSPACE CAPITAL X
        "\uD688": "$\\mttY$",  # MATHEMATICAL MONOSPACE CAPITAL Y
        "\uD689": "$\\mttZ$",  # MATHEMATICAL MONOSPACE CAPITAL Z
        "\uD68A": "$\\mtta$",  # MATHEMATICAL MONOSPACE SMALL A
        "\uD68B": "$\\mttb$",  # MATHEMATICAL MONOSPACE SMALL B
        "\uD68C": "$\\mttc$",  # MATHEMATICAL MONOSPACE SMALL C
        "\uD68D": "$\\mttd$",  # MATHEMATICAL MONOSPACE SMALL D
        "\uD68E": "$\\mtte$",  # MATHEMATICAL MONOSPACE SMALL E
        "\uD68F": "$\\mttf$",  # MATHEMATICAL MONOSPACE SMALL F
        "\uD690": "$\\mttg$",  # MATHEMATICAL MONOSPACE SMALL G
        "\uD691": "$\\mtth$",  # MATHEMATICAL MONOSPACE SMALL H
        "\uD692": "$\\mtti$",  # MATHEMATICAL MONOSPACE SMALL I
        "\uD693": "$\\mttj$",  # MATHEMATICAL MONOSPACE SMALL J
        "\uD694": "$\\mttk$",  # MATHEMATICAL MONOSPACE SMALL K
        "\uD695": "$\\mttl$",  # MATHEMATICAL MONOSPACE SMALL L
        "\uD696": "$\\mttm$",  # MATHEMATICAL MONOSPACE SMALL M
        "\uD697": "$\\mttn$",  # MATHEMATICAL MONOSPACE SMALL N
        "\uD698": "$\\mtto$",  # MATHEMATICAL MONOSPACE SMALL O
        "\uD699": "$\\mttp$",  # MATHEMATICAL MONOSPACE SMALL P
        "\uD69A": "$\\mttq$",  # MATHEMATICAL MONOSPACE SMALL Q
        "\uD69B": "$\\mttr$",  # MATHEMATICAL MONOSPACE SMALL R
        "\uD69C": "$\\mtts$",  # MATHEMATICAL MONOSPACE SMALL S
        "\uD69D": "$\\mttt$",  # MATHEMATICAL MONOSPACE SMALL T
        "\uD69E": "$\\mttu$",  # MATHEMATICAL MONOSPACE SMALL U
        "\uD69F": "$\\mttv$",  # MATHEMATICAL MONOSPACE SMALL V
        "\uD6A0": "$\\mttw$",  # MATHEMATICAL MONOSPACE SMALL W
        "\uD6A1": "$\\mttx$",  # MATHEMATICAL MONOSPACE SMALL X
        "\uD6A2": "$\\mtty$",  # MATHEMATICAL MONOSPACE SMALL Y
        "\uD6A3": "$\\mttz$",  # MATHEMATICAL MONOSPACE SMALL Z
        "\uD6A8": "$\\mbfAlpha$",  # MATHEMATICAL BOLD CAPITAL ALPHA
        "\uD6A9": "$\\mbfBeta$",  # MATHEMATICAL BOLD CAPITAL BETA
        "\uD6AA": "$\\mbfGamma$",  # MATHEMATICAL BOLD CAPITAL GAMMA
        "\uD6AB": "$\\mbfDelta$",  # MATHEMATICAL BOLD CAPITAL DELTA
        "\uD6AC": "$\\mbfEpsilon$",  # MATHEMATICAL BOLD CAPITAL EPSILON
        "\uD6AD": "$\\mbfZeta$",  # MATHEMATICAL BOLD CAPITAL ZETA
        "\uD6AE": "$\\mbfEta$",  # MATHEMATICAL BOLD CAPITAL ETA
        "\uD6AF": "$\\mbfTheta$",  # MATHEMATICAL BOLD CAPITAL THETA
        "\uD6B0": "$\\mbfIota$",  # MATHEMATICAL BOLD CAPITAL IOTA
        "\uD6B1": "$\\mbfKappa$",  # MATHEMATICAL BOLD CAPITAL KAPPA
        "\uD6B2": "$\\mbfLambda$",  # MATHEMATICAL BOLD CAPITAL LAMDA
        "\uD6B3": "$\\mbfMu$",  # MATHEMATICAL BOLD CAPITAL MU
        "\uD6B4": "$\\mbfNu$",  # MATHEMATICAL BOLD CAPITAL NU
        "\uD6B5": "$\\mbfXi$",  # MATHEMATICAL BOLD CAPITAL XI
        "\uD6B6": "$\\mbfOmicron$",  # MATHEMATICAL BOLD CAPITAL OMICRON
        "\uD6B7": "$\\mbfPi$",  # MATHEMATICAL BOLD CAPITAL PI
        "\uD6B8": "$\\mbfRho$",  # MATHEMATICAL BOLD CAPITAL RHO
        "\uD6B9": "$\\mathbf{\\vartheta}$",  # MATHEMATICAL BOLD CAPITAL THETA SYMBOL
        "\uD6BA": "$\\mbfSigma$",  # MATHEMATICAL BOLD CAPITAL SIGMA
        "\uD6BB": "$\\mbfTau$",  # MATHEMATICAL BOLD CAPITAL TAU
        "\uD6BC": "$\\mbfUpsilon$",  # MATHEMATICAL BOLD CAPITAL UPSILON
        "\uD6BD": "$\\mbfPhi$",  # MATHEMATICAL BOLD CAPITAL PHI
        "\uD6BE": "$\\mbfChi$",  # MATHEMATICAL BOLD CAPITAL CHI
        "\uD6BF": "$\\mbfPsi$",  # MATHEMATICAL BOLD CAPITAL PSI
        "\uD6C0": "$\\mbfOmega$",  # MATHEMATICAL BOLD CAPITAL OMEGA
        "\uD6C1": "$\\mbfnabla$",  # MATHEMATICAL BOLD NABLA
        "\uD6C2": "$\\mbfalpha$",  # MATHEMATICAL BOLD SMALL ALPHA
        "\uD6C3": "$\\mbfbeta$",  # MATHEMATICAL BOLD SMALL BETA
        "\uD6C4": "$\\mbfgamma$",  # MATHEMATICAL BOLD SMALL GAMMA
        "\uD6C5": "$\\mbfdelta$",  # MATHEMATICAL BOLD SMALL DELTA
        "\uD6C6": "$\\mbfepsilon$",  # MATHEMATICAL BOLD SMALL EPSILON
        "\uD6C7": "$\\mbfzeta$",  # MATHEMATICAL BOLD SMALL ZETA
        "\uD6C8": "$\\mbfeta$",  # MATHEMATICAL BOLD SMALL ETA
        "\uD6C9": "$\\mbftheta$",  # MATHEMATICAL BOLD SMALL THETA
        "\uD6CA": "$\\mbfiota$",  # MATHEMATICAL BOLD SMALL IOTA
        "\uD6CB": "$\\mbfkappa$",  # MATHEMATICAL BOLD SMALL KAPPA
        "\uD6CC": "$\\mbflambda$",  # MATHEMATICAL BOLD SMALL LAMDA
        "\uD6CD": "$\\mbfmu$",  # MATHEMATICAL BOLD SMALL MU
        "\uD6CE": "$\\mbfnu$",  # MATHEMATICAL BOLD SMALL NU
        "\uD6CF": "$\\mbfxi$",  # MATHEMATICAL BOLD SMALL XI
        "\uD6D0": "$\\mbfomicron$",  # MATHEMATICAL BOLD SMALL OMICRON
        "\uD6D1": "$\\mbfpi$",  # MATHEMATICAL BOLD SMALL PI
        "\uD6D2": "$\\mbfrho$",  # MATHEMATICAL BOLD SMALL RHO
        "\uD6D3": "$\\mbfvarsigma$",  # MATHEMATICAL BOLD SMALL FINAL SIGMA
        "\uD6D4": "$\\mbfsigma$",  # MATHEMATICAL BOLD SMALL SIGMA
        "\uD6D5": "$\\mbftau$",  # MATHEMATICAL BOLD SMALL TAU
        "\uD6D6": "$\\mbfupsilon$",  # MATHEMATICAL BOLD SMALL UPSILON
        "\uD6D7": "$\\mbfvarphi$",  # MATHEMATICAL BOLD SMALL PHI
        "\uD6D8": "$\\mbfchi$",  # MATHEMATICAL BOLD SMALL CHI
        "\uD6D9": "$\\mbfpsi$",  # MATHEMATICAL BOLD SMALL PSI
        "\uD6DA": "$\\mbfomega$",  # MATHEMATICAL BOLD SMALL OMEGA
        "\uD6DB": "$\\mbfpartial$",  # MATHEMATICAL BOLD PARTIAL DIFFERENTIAL
        "\uD6DC": "$\\mbfvarepsilon$",  # MATHEMATICAL BOLD EPSILON SYMBOL
        "\uD6DD": "$\\mathbf{\\vartheta}$",  # MATHEMATICAL BOLD THETA SYMBOL
        "\uD6DE": "$\\mathbf{\\varkappa}$",  # MATHEMATICAL BOLD KAPPA SYMBOL
        "\uD6DF": "$\\mathbf{\\phi}$",  # MATHEMATICAL BOLD PHI SYMBOL
        "\uD6E0": "$\\mathbf{\\varrho}$",  # MATHEMATICAL BOLD RHO SYMBOL
        "\uD6E1": "$\\mathbf{\\varpi}$",  # MATHEMATICAL BOLD PI SYMBOL
        "\uD6E2": "$\\mitAlpha$",  # MATHEMATICAL ITALIC CAPITAL ALPHA
        "\uD6E3": "$\\mitBeta$",  # MATHEMATICAL ITALIC CAPITAL BETA
        "\uD6E4": "$\\mitGamma$",  # MATHEMATICAL ITALIC CAPITAL GAMMA
        "\uD6E5": "$\\mitDelta$",  # MATHEMATICAL ITALIC CAPITAL DELTA
        "\uD6E6": "$\\mitEpsilon$",  # MATHEMATICAL ITALIC CAPITAL EPSILON
        "\uD6E7": "$\\mitZeta$",  # MATHEMATICAL ITALIC CAPITAL ZETA
        "\uD6E8": "$\\mitEta$",  # MATHEMATICAL ITALIC CAPITAL ETA
        "\uD6E9": "$\\mitTheta$",  # MATHEMATICAL ITALIC CAPITAL THETA
        "\uD6EA": "$\\mitIota$",  # MATHEMATICAL ITALIC CAPITAL IOTA
        "\uD6EB": "$\\mitKappa$",  # MATHEMATICAL ITALIC CAPITAL KAPPA
        "\uD6EC": "$\\mitLambda$",  # MATHEMATICAL ITALIC CAPITAL LAMDA
        "\uD6ED": "$\\mitMu$",  # MATHEMATICAL ITALIC CAPITAL MU
        "\uD6EE": "$\\mitNu$",  # MATHEMATICAL ITALIC CAPITAL NU
        "\uD6EF": "$\\mitXi$",  # MATHEMATICAL ITALIC CAPITAL XI
        "\uD6F0": "$\\mitOmicron$",  # MATHEMATICAL ITALIC CAPITAL OMICRON
        "\uD6F1": "$\\mitPi$",  # MATHEMATICAL ITALIC CAPITAL PI
        "\uD6F2": "$\\mitRho$",  # MATHEMATICAL ITALIC CAPITAL RHO
        "\uD6F3": "$\\mathmit{\\vartheta}$",  # MATHEMATICAL ITALIC CAPITAL THETA SYMBOL
        "\uD6F4": "$\\mitSigma$",  # MATHEMATICAL ITALIC CAPITAL SIGMA
        "\uD6F5": "$\\mitTau$",  # MATHEMATICAL ITALIC CAPITAL TAU
        "\uD6F6": "$\\mitUpsilon$",  # MATHEMATICAL ITALIC CAPITAL UPSILON
        "\uD6F7": "$\\mitPhi$",  # MATHEMATICAL ITALIC CAPITAL PHI
        "\uD6F8": "$\\mitChi$",  # MATHEMATICAL ITALIC CAPITAL CHI
        "\uD6F9": "$\\mitPsi$",  # MATHEMATICAL ITALIC CAPITAL PSI
        "\uD6FA": "$\\mitOmega$",  # MATHEMATICAL ITALIC CAPITAL OMEGA
        "\uD6FB": "$\\mitnabla$",  # MATHEMATICAL ITALIC NABLA
        "\uD6FC": "$\\mitalpha$",  # MATHEMATICAL ITALIC SMALL ALPHA
        "\uD6FD": "$\\mitbeta$",  # MATHEMATICAL ITALIC SMALL BETA
        "\uD6FE": "$\\mitgamma$",  # MATHEMATICAL ITALIC SMALL GAMMA
        "\uD6FF": "$\\mitdelta$",  # MATHEMATICAL ITALIC SMALL DELTA
        "\uD700": "$\\mitepsilon$",  # MATHEMATICAL ITALIC SMALL EPSILON
        "\uD701": "$\\mitzeta$",  # MATHEMATICAL ITALIC SMALL ZETA
        "\uD702": "$\\miteta$",  # MATHEMATICAL ITALIC SMALL ETA
        "\uD703": "$\\mittheta$",  # MATHEMATICAL ITALIC SMALL THETA
        "\uD704": "$\\mitiota$",  # MATHEMATICAL ITALIC SMALL IOTA
        "\uD705": "$\\mitkappa$",  # MATHEMATICAL ITALIC SMALL KAPPA
        "\uD706": "$\\mitlambda$",  # MATHEMATICAL ITALIC SMALL LAMDA
        "\uD707": "$\\mitmu$",  # MATHEMATICAL ITALIC SMALL MU
        "\uD708": "$\\mitnu$",  # MATHEMATICAL ITALIC SMALL NU
        "\uD709": "$\\mitxi$",  # MATHEMATICAL ITALIC SMALL XI
        "\uD70A": "$\\mitomicron$",  # MATHEMATICAL ITALIC SMALL OMICRON
        "\uD70B": "$\\mitpi$",  # MATHEMATICAL ITALIC SMALL PI
        "\uD70C": "$\\mitrho$",  # MATHEMATICAL ITALIC SMALL RHO
        "\uD70D": "$\\mitvarsigma$",  # MATHEMATICAL ITALIC SMALL FINAL SIGMA
        "\uD70E": "$\\mitsigma$",  # MATHEMATICAL ITALIC SMALL SIGMA
        "\uD70F": "$\\mittau$",  # MATHEMATICAL ITALIC SMALL TAU
        "\uD710": "$\\mitupsilon$",  # MATHEMATICAL ITALIC SMALL UPSILON
        "\uD711": "$\\mitphi$",  # MATHEMATICAL ITALIC SMALL PHI
        "\uD712": "$\\mitchi$",  # MATHEMATICAL ITALIC SMALL CHI
        "\uD713": "$\\mitpsi$",  # MATHEMATICAL ITALIC SMALL PSI
        "\uD714": "$\\mitomega$",  # MATHEMATICAL ITALIC SMALL OMEGA
        "\uD715": "$\\mitpartial$",  # MATHEMATICAL ITALIC PARTIAL DIFFERENTIAL
        "\uD716": "$\\mitvarepsilon$",  # MATHEMATICAL ITALIC EPSILON SYMBOL
        "\uD717": "$\\mathmit{\\vartheta}$",  # MATHEMATICAL ITALIC THETA SYMBOL
        "\uD718": "$\\mathmit{\\varkappa}$",  # MATHEMATICAL ITALIC KAPPA SYMBOL
        "\uD719": "$\\mathmit{\\phi}$",  # MATHEMATICAL ITALIC PHI SYMBOL
        "\uD71A": "$\\mathmit{\\varrho}$",  # MATHEMATICAL ITALIC RHO SYMBOL
        "\uD71B": "$\\mathmit{\\varpi}$",  # MATHEMATICAL ITALIC PI SYMBOL
        "\uD71C": "$\\mbfitAlpha$",  # MATHEMATICAL BOLD ITALIC CAPITAL ALPHA
        "\uD71D": "$\\mbfitBeta$",  # MATHEMATICAL BOLD ITALIC CAPITAL BETA
        "\uD71E": "$\\mbfitGamma$",  # MATHEMATICAL BOLD ITALIC CAPITAL GAMMA
        "\uD71F": "$\\mbfitDelta$",  # MATHEMATICAL BOLD ITALIC CAPITAL DELTA
        "\uD720": "$\\mbfitEpsilon$",  # MATHEMATICAL BOLD ITALIC CAPITAL EPSILON
        "\uD721": "$\\mbfitZeta$",  # MATHEMATICAL BOLD ITALIC CAPITAL ZETA
        "\uD722": "$\\mbfitEta$",  # MATHEMATICAL BOLD ITALIC CAPITAL ETA
        "\uD723": "$\\mbfitTheta$",  # MATHEMATICAL BOLD ITALIC CAPITAL THETA
        "\uD724": "$\\mbfitIota$",  # MATHEMATICAL BOLD ITALIC CAPITAL IOTA
        "\uD725": "$\\mbfitKappa$",  # MATHEMATICAL BOLD ITALIC CAPITAL KAPPA
        "\uD726": "$\\mbfitLambda$",  # MATHEMATICAL BOLD ITALIC CAPITAL LAMDA
        "\uD727": "$\\mbfitMu$",  # MATHEMATICAL BOLD ITALIC CAPITAL MU
        "\uD728": "$\\mbfitNu$",  # MATHEMATICAL BOLD ITALIC CAPITAL NU
        "\uD729": "$\\mbfitXi$",  # MATHEMATICAL BOLD ITALIC CAPITAL XI
        "\uD72A": "$\\mbfitOmicron$",  # MATHEMATICAL BOLD ITALIC CAPITAL OMICRON
        "\uD72B": "$\\mbfitPi$",  # MATHEMATICAL BOLD ITALIC CAPITAL PI
        "\uD72C": "$\\mbfitRho$",  # MATHEMATICAL BOLD ITALIC CAPITAL RHO
        "\uD72D": "$\\mathbit{O}$",  # MATHEMATICAL BOLD ITALIC CAPITAL THETA SYMBOL
        "\uD72E": "$\\mbfitSigma$",  # MATHEMATICAL BOLD ITALIC CAPITAL SIGMA
        "\uD72F": "$\\mbfitTau$",  # MATHEMATICAL BOLD ITALIC CAPITAL TAU
        "\uD730": "$\\mbfitUpsilon$",  # MATHEMATICAL BOLD ITALIC CAPITAL UPSILON
        "\uD731": "$\\mbfitPhi$",  # MATHEMATICAL BOLD ITALIC CAPITAL PHI
        "\uD732": "$\\mbfitChi$",  # MATHEMATICAL BOLD ITALIC CAPITAL CHI
        "\uD733": "$\\mbfitPsi$",  # MATHEMATICAL BOLD ITALIC CAPITAL PSI
        "\uD734": "$\\mbfitOmega$",  # MATHEMATICAL BOLD ITALIC CAPITAL OMEGA
        "\uD735": "$\\mbfitnabla$",  # MATHEMATICAL BOLD ITALIC NABLA
        "\uD736": "$\\mbfitalpha$",  # MATHEMATICAL BOLD ITALIC SMALL ALPHA
        "\uD737": "$\\mbfitbeta$",  # MATHEMATICAL BOLD ITALIC SMALL BETA
        "\uD738": "$\\mbfitgamma$",  # MATHEMATICAL BOLD ITALIC SMALL GAMMA
        "\uD739": "$\\mbfitdelta$",  # MATHEMATICAL BOLD ITALIC SMALL DELTA
        "\uD73A": "$\\mbfitepsilon$",  # MATHEMATICAL BOLD ITALIC SMALL EPSILON
        "\uD73B": "$\\mbfitzeta$",  # MATHEMATICAL BOLD ITALIC SMALL ZETA
        "\uD73C": "$\\mbfiteta$",  # MATHEMATICAL BOLD ITALIC SMALL ETA
        "\uD73D": "$\\mbfittheta$",  # MATHEMATICAL BOLD ITALIC SMALL THETA
        "\uD73E": "$\\mbfitiota$",  # MATHEMATICAL BOLD ITALIC SMALL IOTA
        "\uD73F": "$\\mbfitkappa$",  # MATHEMATICAL BOLD ITALIC SMALL KAPPA
        "\uD740": "$\\mbfitlambda$",  # MATHEMATICAL BOLD ITALIC SMALL LAMDA
        "\uD741": "$\\mbfitmu$",  # MATHEMATICAL BOLD ITALIC SMALL MU
        "\uD742": "$\\mbfitnu$",  # MATHEMATICAL BOLD ITALIC SMALL NU
        "\uD743": "$\\mbfitxi$",  # MATHEMATICAL BOLD ITALIC SMALL XI
        "\uD744": "$\\mbfitomicron$",  # MATHEMATICAL BOLD ITALIC SMALL OMICRON
        "\uD745": "$\\mbfitpi$",  # MATHEMATICAL BOLD ITALIC SMALL PI
        "\uD746": "$\\mbfitrho$",  # MATHEMATICAL BOLD ITALIC SMALL RHO
        "\uD747": "$\\mbfitvarsigma$",  # MATHEMATICAL BOLD ITALIC SMALL FINAL SIGMA
        "\uD748": "$\\mbfitsigma$",  # MATHEMATICAL BOLD ITALIC SMALL SIGMA
        "\uD749": "$\\mbfittau$",  # MATHEMATICAL BOLD ITALIC SMALL TAU
        "\uD74A": "$\\mbfitupsilon$",  # MATHEMATICAL BOLD ITALIC SMALL UPSILON
        "\uD74B": "$\\mbfitphi$",  # MATHEMATICAL BOLD ITALIC SMALL PHI
        "\uD74C": "$\\mbfitchi$",  # MATHEMATICAL BOLD ITALIC SMALL CHI
        "\uD74D": "$\\mbfitpsi$",  # MATHEMATICAL BOLD ITALIC SMALL PSI
        "\uD74E": "$\\mbfitomega$",  # MATHEMATICAL BOLD ITALIC SMALL OMEGA
        "\uD74F": "$\\mbfitpartial$",  # MATHEMATICAL BOLD ITALIC PARTIAL DIFFERENTIAL
        "\uD750": "$\\mbfitvarepsilon$",  # MATHEMATICAL BOLD ITALIC EPSILON SYMBOL
        "\uD751": "$\\mathbit{\\vartheta}$",  # MATHEMATICAL BOLD ITALIC THETA SYMBOL
        "\uD752": "$\\mathbit{\\varkappa}$",  # MATHEMATICAL BOLD ITALIC KAPPA SYMBOL
        "\uD753": "$\\mathbit{\\phi}$",  # MATHEMATICAL BOLD ITALIC PHI SYMBOL
        "\uD754": "$\\mathbit{\\varrho}$",  # MATHEMATICAL BOLD ITALIC RHO SYMBOL
        "\uD755": "$\\mathbit{\\varpi}$",  # MATHEMATICAL BOLD ITALIC PI SYMBOL
        "\uD756": "$\\mbfsansAlpha$",  # MATHEMATICAL SANS-SERIF BOLD CAPITAL ALPHA
        "\uD757": "$\\mbfsansBeta$",  # MATHEMATICAL SANS-SERIF BOLD CAPITAL BETA
        "\uD758": "$\\mbfsansGamma$",  # MATHEMATICAL SANS-SERIF BOLD CAPITAL GAMMA
        "\uD759": "$\\mbfsansDelta$",  # MATHEMATICAL SANS-SERIF BOLD CAPITAL DELTA
        "\uD75A": "$\\mbfsansEpsilon$",  # MATHEMATICAL SANS-SERIF BOLD CAPITAL EPSILON
        "\uD75B": "$\\mbfsansZeta$",  # MATHEMATICAL SANS-SERIF BOLD CAPITAL ZETA
        "\uD75C": "$\\mbfsansEta$",  # MATHEMATICAL SANS-SERIF BOLD CAPITAL ETA
        "\uD75D": "$\\mbfsansTheta$",  # MATHEMATICAL SANS-SERIF BOLD CAPITAL THETA
        "\uD75E": "$\\mbfsansIota$",  # MATHEMATICAL SANS-SERIF BOLD CAPITAL IOTA
        "\uD75F": "$\\mbfsansKappa$",  # MATHEMATICAL SANS-SERIF BOLD CAPITAL KAPPA
        "\uD760": "$\\mbfsansLambda$",  # MATHEMATICAL SANS-SERIF BOLD CAPITAL LAMDA
        "\uD761": "$\\mbfsansMu$",  # MATHEMATICAL SANS-SERIF BOLD CAPITAL MU
        "\uD762": "$\\mbfsansNu$",  # MATHEMATICAL SANS-SERIF BOLD CAPITAL NU
        "\uD763": "$\\mbfsansXi$",  # MATHEMATICAL SANS-SERIF BOLD CAPITAL XI
        "\uD764": "$\\mbfsansOmicron$",  # MATHEMATICAL SANS-SERIF BOLD CAPITAL OMICRON
        "\uD765": "$\\mbfsansPi$",  # MATHEMATICAL SANS-SERIF BOLD CAPITAL PI
        "\uD766": "$\\mbfsansRho$",  # MATHEMATICAL SANS-SERIF BOLD CAPITAL RHO
        "\uD767": "$\\mathsfbf{\\vartheta}$",  # MATHEMATICAL SANS-SERIF BOLD CAPITAL THETA SYMBOL
        "\uD768": "$\\mbfsansSigma$",  # MATHEMATICAL SANS-SERIF BOLD CAPITAL SIGMA
        "\uD769": "$\\mbfsansTau$",  # MATHEMATICAL SANS-SERIF BOLD CAPITAL TAU
        "\uD76A": "$\\mbfsansUpsilon$",  # MATHEMATICAL SANS-SERIF BOLD CAPITAL UPSILON
        "\uD76B": "$\\mbfsansPhi$",  # MATHEMATICAL SANS-SERIF BOLD CAPITAL PHI
        "\uD76C": "$\\mbfsansChi$",  # MATHEMATICAL SANS-SERIF BOLD CAPITAL CHI
        "\uD76D": "$\\mbfsansPsi$",  # MATHEMATICAL SANS-SERIF BOLD CAPITAL PSI
        "\uD76E": "$\\mbfsansOmega$",  # MATHEMATICAL SANS-SERIF BOLD CAPITAL OMEGA
        "\uD76F": "$\\mbfsansnabla$",  # MATHEMATICAL SANS-SERIF BOLD NABLA
        "\uD770": "$\\mbfsansalpha$",  # MATHEMATICAL SANS-SERIF BOLD SMALL ALPHA
        "\uD771": "$\\mbfsansbeta$",  # MATHEMATICAL SANS-SERIF BOLD SMALL BETA
        "\uD772": "$\\mbfsansgamma$",  # MATHEMATICAL SANS-SERIF BOLD SMALL GAMMA
        "\uD773": "$\\mbfsansdelta$",  # MATHEMATICAL SANS-SERIF BOLD SMALL DELTA
        "\uD774": "$\\mbfsansepsilon$",  # MATHEMATICAL SANS-SERIF BOLD SMALL EPSILON
        "\uD775": "$\\mbfsanszeta$",  # MATHEMATICAL SANS-SERIF BOLD SMALL ZETA
        "\uD776": "$\\mbfsanseta$",  # MATHEMATICAL SANS-SERIF BOLD SMALL ETA
        "\uD777": "$\\mbfsanstheta$",  # MATHEMATICAL SANS-SERIF BOLD SMALL THETA
        "\uD778": "$\\mbfsansiota$",  # MATHEMATICAL SANS-SERIF BOLD SMALL IOTA
        "\uD779": "$\\mbfsanskappa$",  # MATHEMATICAL SANS-SERIF BOLD SMALL KAPPA
        "\uD77A": "$\\mbfsanslambda$",  # MATHEMATICAL SANS-SERIF BOLD SMALL LAMDA
        "\uD77B": "$\\mbfsansmu$",  # MATHEMATICAL SANS-SERIF BOLD SMALL MU
        "\uD77C": "$\\mbfsansnu$",  # MATHEMATICAL SANS-SERIF BOLD SMALL NU
        "\uD77D": "$\\mbfsansxi$",  # MATHEMATICAL SANS-SERIF BOLD SMALL XI
        "\uD77E": "$\\mbfsansomicron$",  # MATHEMATICAL SANS-SERIF BOLD SMALL OMICRON
        "\uD77F": "$\\mbfsanspi$",  # MATHEMATICAL SANS-SERIF BOLD SMALL PI
        "\uD780": "$\\mbfsansrho$",  # MATHEMATICAL SANS-SERIF BOLD SMALL RHO
        "\uD781": "$\\mbfsansvarsigma$",  # MATHEMATICAL SANS-SERIF BOLD SMALL FINAL SIGMA
        "\uD782": "$\\mbfsanssigma$",  # MATHEMATICAL SANS-SERIF BOLD SMALL SIGMA
        "\uD783": "$\\mbfsanstau$",  # MATHEMATICAL SANS-SERIF BOLD SMALL TAU
        "\uD784": "$\\mbfsansupsilon$",  # MATHEMATICAL SANS-SERIF BOLD SMALL UPSILON
        "\uD785": "$\\mbfsansphi$",  # MATHEMATICAL SANS-SERIF BOLD SMALL PHI
        "\uD786": "$\\mbfsanschi$",  # MATHEMATICAL SANS-SERIF BOLD SMALL CHI
        "\uD787": "$\\mbfsanspsi$",  # MATHEMATICAL SANS-SERIF BOLD SMALL PSI
        "\uD788": "$\\mbfsansomega$",  # MATHEMATICAL SANS-SERIF BOLD SMALL OMEGA
        "\uD789": "$\\mbfsanspartial$",  # MATHEMATICAL SANS-SERIF BOLD PARTIAL DIFFERENTIAL
        "\uD78A": "$\\mbfsansvarepsilon$",  # MATHEMATICAL SANS-SERIF BOLD EPSILON SYMBOL
        "\uD78B": "$\\mathsfbf{\\vartheta}$",  # MATHEMATICAL SANS-SERIF BOLD THETA SYMBOL
        "\uD78C": "$\\mathsfbf{\\varkappa}$",  # MATHEMATICAL SANS-SERIF BOLD KAPPA SYMBOL
        "\uD78D": "$\\mathsfbf{\\phi}$",  # MATHEMATICAL SANS-SERIF BOLD PHI SYMBOL
        "\uD78E": "$\\mathsfbf{\\varrho}$",  # MATHEMATICAL SANS-SERIF BOLD RHO SYMBOL
        "\uD78F": "$\\mathsfbf{\\varpi}$",  # MATHEMATICAL SANS-SERIF BOLD PI SYMBOL
        "\uD790": "$\\mbfitsansAlpha$",  # MATHEMATICAL SANS-SERIF BOLD ITALIC CAPITAL ALPHA
        "\uD791": "$\\mbfitsansBeta$",  # MATHEMATICAL SANS-SERIF BOLD ITALIC CAPITAL BETA
        "\uD792": "$\\mbfitsansGamma$",  # MATHEMATICAL SANS-SERIF BOLD ITALIC CAPITAL GAMMA
        "\uD793": "$\\mbfitsansDelta$",  # MATHEMATICAL SANS-SERIF BOLD ITALIC CAPITAL DELTA
        "\uD794": "$\\mbfitsansEpsilon$",  # MATHEMATICAL SANS-SERIF BOLD ITALIC CAPITAL EPSILON
        "\uD795": "$\\mbfitsansZeta$",  # MATHEMATICAL SANS-SERIF BOLD ITALIC CAPITAL ZETA
        "\uD796": "$\\mbfitsansEta$",  # MATHEMATICAL SANS-SERIF BOLD ITALIC CAPITAL ETA
        "\uD797": "$\\mbfitsansTheta$",  # MATHEMATICAL SANS-SERIF BOLD ITALIC CAPITAL THETA
        "\uD798": "$\\mbfitsansIota$",  # MATHEMATICAL SANS-SERIF BOLD ITALIC CAPITAL IOTA
        "\uD799": "$\\mbfitsansKappa$",  # MATHEMATICAL SANS-SERIF BOLD ITALIC CAPITAL KAPPA
        "\uD79A": "$\\mbfitsansLambda$",  # MATHEMATICAL SANS-SERIF BOLD ITALIC CAPITAL LAMDA
        "\uD79B": "$\\mbfitsansMu$",  # MATHEMATICAL SANS-SERIF BOLD ITALIC CAPITAL MU
        "\uD79C": "$\\mbfitsansNu$",  # MATHEMATICAL SANS-SERIF BOLD ITALIC CAPITAL NU
        "\uD79D": "$\\mbfitsansXi$",  # MATHEMATICAL SANS-SERIF BOLD ITALIC CAPITAL XI
        "\uD79E": "$\\mbfitsansOmicron$",  # MATHEMATICAL SANS-SERIF BOLD ITALIC CAPITAL OMICRON
        "\uD79F": "$\\mbfitsansPi$",  # MATHEMATICAL SANS-SERIF BOLD ITALIC CAPITAL PI
        "\uD7A0": "$\\mbfitsansRho$",  # MATHEMATICAL SANS-SERIF BOLD ITALIC CAPITAL RHO
        "\uD7A1": "$\\mathsfbfsl{\\vartheta}$",  # MATHEMATICAL SANS-SERIF BOLD ITALIC CAPITAL THETA SYMBOL
        "\uD7A2": "$\\mbfitsansSigma$",  # MATHEMATICAL SANS-SERIF BOLD ITALIC CAPITAL SIGMA
        "\uD7A3": "$\\mbfitsansTau$",  # MATHEMATICAL SANS-SERIF BOLD ITALIC CAPITAL TAU
        "\uD7A4": "$\\mbfitsansUpsilon$",  # MATHEMATICAL SANS-SERIF BOLD ITALIC CAPITAL UPSILON
        "\uD7A5": "$\\mbfitsansPhi$",  # MATHEMATICAL SANS-SERIF BOLD ITALIC CAPITAL PHI
        "\uD7A6": "$\\mbfitsansChi$",  # MATHEMATICAL SANS-SERIF BOLD ITALIC CAPITAL CHI
        "\uD7A7": "$\\mbfitsansPsi$",  # MATHEMATICAL SANS-SERIF BOLD ITALIC CAPITAL PSI
        "\uD7A8": "$\\mbfitsansOmega$",  # MATHEMATICAL SANS-SERIF BOLD ITALIC CAPITAL OMEGA
        "\uD7A9": "$\\mbfitsansnabla$",  # MATHEMATICAL SANS-SERIF BOLD ITALIC NABLA
        "\uD7AA": "$\\mbfitsansalpha$",  # MATHEMATICAL SANS-SERIF BOLD ITALIC SMALL ALPHA
        "\uD7AB": "$\\mbfitsansbeta$",  # MATHEMATICAL SANS-SERIF BOLD ITALIC SMALL BETA
        "\uD7AC": "$\\mbfitsansgamma$",  # MATHEMATICAL SANS-SERIF BOLD ITALIC SMALL GAMMA
        "\uD7AD": "$\\mbfitsansdelta$",  # MATHEMATICAL SANS-SERIF BOLD ITALIC SMALL DELTA
        "\uD7AE": "$\\mbfitsansepsilon$",  # MATHEMATICAL SANS-SERIF BOLD ITALIC SMALL EPSILON
        "\uD7AF": "$\\mbfitsanszeta$",  # MATHEMATICAL SANS-SERIF BOLD ITALIC SMALL ZETA
        "\uD7B0": "$\\mbfitsanseta$",  # MATHEMATICAL SANS-SERIF BOLD ITALIC SMALL ETA
        "\uD7B1": "$\\mbfitsanstheta$",  # MATHEMATICAL SANS-SERIF BOLD ITALIC SMALL THETA
        "\uD7B2": "$\\mbfitsansiota$",  # MATHEMATICAL SANS-SERIF BOLD ITALIC SMALL IOTA
        "\uD7B3": "$\\mbfitsanskappa$",  # MATHEMATICAL SANS-SERIF BOLD ITALIC SMALL KAPPA
        "\uD7B4": "$\\mbfitsanslambda$",  # MATHEMATICAL SANS-SERIF BOLD ITALIC SMALL LAMDA
        "\uD7B5": "$\\mbfitsansmu$",  # MATHEMATICAL SANS-SERIF BOLD ITALIC SMALL MU
        "\uD7B6": "$\\mbfitsansnu$",  # MATHEMATICAL SANS-SERIF BOLD ITALIC SMALL NU
        "\uD7B7": "$\\mbfitsansxi$",  # MATHEMATICAL SANS-SERIF BOLD ITALIC SMALL XI
        "\uD7B8": "$\\mbfitsansomicron$",  # MATHEMATICAL SANS-SERIF BOLD ITALIC SMALL OMICRON
        "\uD7B9": "$\\mbfitsanspi$",  # MATHEMATICAL SANS-SERIF BOLD ITALIC SMALL PI
        "\uD7BA": "$\\mbfitsansrho$",  # MATHEMATICAL SANS-SERIF BOLD ITALIC SMALL RHO
        "\uD7BB": "$\\mbfitsansvarsigma$",  # MATHEMATICAL SANS-SERIF BOLD ITALIC SMALL FINAL SIGMA
        "\uD7BC": "$\\mbfitsanssigma$",  # MATHEMATICAL SANS-SERIF BOLD ITALIC SMALL SIGMA
        "\uD7BD": "$\\mbfitsanstau$",  # MATHEMATICAL SANS-SERIF BOLD ITALIC SMALL TAU
        "\uD7BE": "$\\mbfitsansupsilon$",  # MATHEMATICAL SANS-SERIF BOLD ITALIC SMALL UPSILON
        "\uD7BF": "$\\mbfitsansphi$",  # MATHEMATICAL SANS-SERIF BOLD ITALIC SMALL PHI
        "\uD7C0": "$\\mbfitsanschi$",  # MATHEMATICAL SANS-SERIF BOLD ITALIC SMALL CHI
        "\uD7C1": "$\\mbfitsanspsi$",  # MATHEMATICAL SANS-SERIF BOLD ITALIC SMALL PSI
        "\uD7C2": "$\\mbfitsansomega$",  # MATHEMATICAL SANS-SERIF BOLD ITALIC SMALL OMEGA
        "\uD7C3": "$\\mbfitsanspartial$",  # MATHEMATICAL SANS-SERIF BOLD ITALIC PARTIAL DIFFERENTIAL
        "\uD7C4": "$\\mbfitsansvarepsilon$",  # MATHEMATICAL SANS-SERIF BOLD ITALIC EPSILON SYMBOL
        "\uD7C5": "$\\mathsfbfsl{\\vartheta}$",  # MATHEMATICAL SANS-SERIF BOLD ITALIC THETA SYMBOL
        "\uD7C6": "$\\mathsfbfsl{\\varkappa}$",  # MATHEMATICAL SANS-SERIF BOLD ITALIC KAPPA SYMBOL
        "\uD7C7": "$\\mathsfbfsl{\\phi}$",  # MATHEMATICAL SANS-SERIF BOLD ITALIC PHI SYMBOL
        "\uD7C8": "$\\mathsfbfsl{\\varrho}$",  # MATHEMATICAL SANS-SERIF BOLD ITALIC RHO SYMBOL
        "\uD7C9": "$\\mathsfbfsl{\\varpi}$",  # MATHEMATICAL SANS-SERIF BOLD ITALIC PI SYMBOL
        "\uD7CE": "$\\mbfzero$",  # MATHEMATICAL BOLD DIGIT ZERO
        "\uD7CF": "$\\mbfone$",  # MATHEMATICAL BOLD DIGIT ONE
        "\uD7D0": "$\\mbftwo$",  # MATHEMATICAL BOLD DIGIT TWO
        "\uD7D1": "$\\mbfthree$",  # MATHEMATICAL BOLD DIGIT THREE
        "\uD7D2": "$\\mbffour$",  # MATHEMATICAL BOLD DIGIT FOUR
        "\uD7D3": "$\\mbffive$",  # MATHEMATICAL BOLD DIGIT FIVE
        "\uD7D4": "$\\mbfsix$",  # MATHEMATICAL BOLD DIGIT SIX
        "\uD7D5": "$\\mbfseven$",  # MATHEMATICAL BOLD DIGIT SEVEN
        "\uD7D6": "$\\mbfeight$",  # MATHEMATICAL BOLD DIGIT EIGHT
        "\uD7D7": "$\\mbfnine$",  # MATHEMATICAL BOLD DIGIT NINE
        "\uD7D8": "$\\Bbbzero$",  # MATHEMATICAL DOUBLE-STRUCK DIGIT ZERO
        "\uD7D9": "$\\Bbbone$",  # MATHEMATICAL DOUBLE-STRUCK DIGIT ONE
        "\uD7DA": "$\\Bbbtwo$",  # MATHEMATICAL DOUBLE-STRUCK DIGIT TWO
        "\uD7DB": "$\\Bbbthree$",  # MATHEMATICAL DOUBLE-STRUCK DIGIT THREE
        "\uD7DC": "$\\Bbbfour$",  # MATHEMATICAL DOUBLE-STRUCK DIGIT FOUR
        "\uD7DD": "$\\Bbbfive$",  # MATHEMATICAL DOUBLE-STRUCK DIGIT FIVE
        "\uD7DE": "$\\Bbbsix$",  # MATHEMATICAL DOUBLE-STRUCK DIGIT SIX
        "\uD7DF": "$\\Bbbseven$",  # MATHEMATICAL DOUBLE-STRUCK DIGIT SEVEN
        "\uD7E0": "$\\Bbbeight$",  # MATHEMATICAL DOUBLE-STRUCK DIGIT EIGHT
        "\uD7E1": "$\\Bbbnine$",  # MATHEMATICAL DOUBLE-STRUCK DIGIT NINE
        "\uD7E2": "$\\msanszero$",  # MATHEMATICAL SANS-SERIF DIGIT ZERO
        "\uD7E3": "$\\msansone$",  # MATHEMATICAL SANS-SERIF DIGIT ONE
        "\uD7E4": "$\\msanstwo$",  # MATHEMATICAL SANS-SERIF DIGIT TWO
        "\uD7E5": "$\\msansthree$",  # MATHEMATICAL SANS-SERIF DIGIT THREE
        "\uD7E6": "$\\msansfour$",  # MATHEMATICAL SANS-SERIF DIGIT FOUR
        "\uD7E7": "$\\msansfive$",  # MATHEMATICAL SANS-SERIF DIGIT FIVE
        "\uD7E8": "$\\msanssix$",  # MATHEMATICAL SANS-SERIF DIGIT SIX
        "\uD7E9": "$\\msansseven$",  # MATHEMATICAL SANS-SERIF DIGIT SEVEN
        "\uD7EA": "$\\msanseight$",  # MATHEMATICAL SANS-SERIF DIGIT EIGHT
        "\uD7EB": "$\\msansnine$",  # MATHEMATICAL SANS-SERIF DIGIT NINE
        "\uD7EC": "$\\mbfsanszero$",  # MATHEMATICAL SANS-SERIF BOLD DIGIT ZERO
        "\uD7ED": "$\\mbfsansone$",  # MATHEMATICAL SANS-SERIF BOLD DIGIT ONE
        "\uD7EE": "$\\mbfsanstwo$",  # MATHEMATICAL SANS-SERIF BOLD DIGIT TWO
        "\uD7EF": "$\\mbfsansthree$",  # MATHEMATICAL SANS-SERIF BOLD DIGIT THREE
        "\uD7F0": "$\\mbfsansfour$",  # MATHEMATICAL SANS-SERIF BOLD DIGIT FOUR
        "\uD7F1": "$\\mbfsansfive$",  # MATHEMATICAL SANS-SERIF BOLD DIGIT FIVE
        "\uD7F2": "$\\mbfsanssix$",  # MATHEMATICAL SANS-SERIF BOLD DIGIT SIX
        "\uD7F3": "$\\mbfsansseven$",  # MATHEMATICAL SANS-SERIF BOLD DIGIT SEVEN
        "\uD7F4": "$\\mbfsanseight$",  # MATHEMATICAL SANS-SERIF BOLD DIGIT EIGHT
        "\uD7F5": "$\\mbfsansnine$",  # MATHEMATICAL SANS-SERIF BOLD DIGIT NINE
        "\uD7F6": "$\\mttzero$",  # MATHEMATICAL MONOSPACE DIGIT ZERO
        "\uD7F7": "$\\mttone$",  # MATHEMATICAL MONOSPACE DIGIT ONE
        "\uD7F8": "$\\mtttwo$",  # MATHEMATICAL MONOSPACE DIGIT TWO
        "\uD7F9": "$\\mttthree$",  # MATHEMATICAL MONOSPACE DIGIT THREE
        "\uD7FA": "$\\mttfour$",  # MATHEMATICAL MONOSPACE DIGIT FOUR
        "\uD7FB": "$\\mttfive$",  # MATHEMATICAL MONOSPACE DIGIT FIVE
        "\uD7FC": "$\\mttsix$",  # MATHEMATICAL MONOSPACE DIGIT SIX
        "\uD7FD": "$\\mttseven$",  # MATHEMATICAL MONOSPACE DIGIT SEVEN
        "\uD7FE": "$\\mtteight$",  # MATHEMATICAL MONOSPACE DIGIT EIGHT
        "\uD7FF": "$\\mttnine$",  # MATHEMATICAL MONOSPACE DIGIT NINE
    }
    return ''.join((map(lambda c: uni2tex.get(c, c), text)))


def createBibtexContent(reference: Reference, pmid: str) -> str:
    """Creates bibtex contents with the bibliographic information given.

    Keyword arguments:
    reference: bibliographic data
    returns bibliographic entry in bibtex format
    """
    if len(reference.authors) > 0:
        authorsText = ' and '.join(map(formatAuthor, reference.authors))
    else:
        authorsText = ''

    if reference.endPage != '':
        pages = reference.startPage + '--' + reference.endPage
    else:
        pages = reference.startPage

    # month = monthToNumber(reference.pbmonth)
    if reference.journalAb != '':
        theJournal = reference.journalAb
    else:
        theJournal = reference.journal

    notes = StringIO()
    if reference.doi != '':
        notes.write('[DOI:\\href{https://dx.doi.org/')
        notes.write(reference.doi + '}{' + reference.doi + '}] [')
    else:
        notes.write('[')
    notes.write('PubMed:\\href{https://www.ncbi.nlm.nih.gov/pubmed/')
    notes.write(pmid + '}{' + pmid + '}')
    notes.write(']')

    result = StringIO()
    result.write(f'% {pmid}\n')
    result.write('@Article{pmid'+f'{pmid},\n')
    result.write('   title = "{' + sanitizeBibtexField(
        (reference.title)) + '}",\n')
    appendFormattedField(result, 'author', sanitizeBibtexField(authorsText))
    appendFormattedField(result, 'journal', sanitizeBibtexField(theJournal))
    appendFormattedField(result, 'volume', reference.volume)
    appendFormattedField(result, 'number', reference.issue)
    appendFormattedField(result, 'pages', pages)
    appendFormattedField(result, 'year', reference.pbyear)
    appendFormattedField(result, 'month', reference.pbmonth)
    if reference.issn != '':
        appendFormattedField(result, 'issn', reference.issn)
    if reference.copyright != '':
        appendFormattedField(result, 'copyright',
                             sanitizeBibtexField(reference.copyright))
    result.write('   abstract = "{')
    result.write(sanitizeBibtexField(reference.abstract))
    result.write('}",\n')
    result.write('   note = {' + notes.getvalue() + '}')
    result.write('\n}\n')
    return result.getvalue()


def createFile(filename: str, content: str) -> None:
    """Creates a file in the current path with the given content.

    Keyword arguments:
    filename -- the file name
    content  -- content to write in the file
    raises exception if output file can not be created
    Side effect: creates a file in the current path
    """
    try:
        with open(filename, 'w') as file_object:
            try:
                file_object.write(content)
            except (IOError, OSError):
                print(f'Error writing to file {filename}')
    except (FileNotFoundError, PermissionError, OSError):
        print(f'Error opening file {filename}')


def getTitle(bibtex_content: str) -> str:
    """Finds the title in the bibtex content.

    Keyword arguments:
    bibtex_content -- the bibliography in BibTeX
    returns the article title
    """
    title = (re.search(r'title = (.*?)\n', bibtex_content)
             .group()
             .lstrip('title = {')
             .rstrip('},\n')
             .translate({ord('{'): None, ord('}'): None}))
    return title


def fetchBibtex(doi: str) -> str:
    """Fetch the  bibliography for an article.

    Keyword arguments:
    doi -- the pubmed identifier for the article
    returns the bibtex bibliography for the doi
    raises an exception if the dx.doi.org service fails
    """
    accept = {'accept': 'application/x-bibtex'}
    # accept = {'accept': 'application/json'}
    url = f'http://dx.doi.org/{doi}'
    req = Request(url, headers=accept)
    try:
        with request.urlopen(req) as resp:
            if resp.code == 200:
                return resp.read().decode("utf-8")
    except URLError as error:
        print('Error downloading BibTeX entry from dx.doi.org.\n',
              error.reason)


def pmid2bibtex(pmid: str) -> None:
    """For the given pubmed identifier, creates a bibtex bibliographic entry.

    Keyword arguments:
    pmid -- a pubmed identifier (e.g 31726262)
    Side effect: creates a bibtex file in the current path
    """
    if len(pmid) < 1 or len(pmid) > 8:
        print('Wrong identifer length, it must have 1 to 8 digits')
        return
    if pmid[0] == '0':
        print('The identifier can not start with 0')
        return

    try:
        xml = fetchXML(pmid)
        reference = parseXML(pmid, xml)
        bibtex_content = createBibtexContent(reference, pmid)
        filename = sanitizeFileName(reference.title) + '.bib'
        createFile(filename, bibtex_content)
        print(f'File "{filename}" was created.')
    except Exception as err:
        print(f'Error processing {pmid}:\n {err}')


def doi2bibtex(doi: str) -> None:
    """Fetch the  bibliography for an article.

    Keyword arguments:
    doi -- the DOI identifier for the article
    returns the bibtex bibliography for the pmid
    raises an exception if there is failure
    """
    try:
        bibtex_content = fetchBibtex(doi)
        # print(bibtex_content)
        title = getTitle(bibtex_content)
        filename = sanitizeFileName(title) + '.bib'
        createFile(filename, bibtex_content)
        print(f'File "{filename}" was created.')
    except Exception as error:
        print(f'Error processing {doi}:\n {error.reason}')


def main():
    if len(sys.argv) == 2:
        paperId = sys.argv[1].strip()
        if '/' in paperId:
            doi2bibtex(paperId)
            return
        if paperId.isdigit():
            pmid2bibtex(paperId)
            return
        else:
            print('Paper identifier not supported. Only pmid and ' +
                  'DOI are allowed')
            return
    else:
        print('Usage: pid2bib paperId')
        print('e.g. pid2bib 31726262')
        print('e.g. pid2bib 10.1021/acs.jced.5b00684')
        print('will create a bibtex file named with the paper title' +
              ' in the current path')
        return


if __name__ == '__main__':
    main()
