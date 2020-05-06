"""Webshare module."""
import logging
import sys
import unicodedata
import re
import xml.etree.ElementTree as eltree
import hashlib
import requests_html as requests
import urllib3
from passlib import hash as plhash

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

LOGGER = logging.getLogger('WSOSAC.WEBSHARE')


class Webshare:
    """Class for Webshare service."""

    webshare_url = 'https://webshare.cz'

    def __init__(self):
        self.session = requests.HTMLSession()
        self.token = None
        self.datalist = list()
        self.headers_data = {
            'Host': 'webshare.cz',
            'Referer': Webshare.webshare_url + '/',
            'Origin': Webshare.webshare_url,
            'X-Requested-With': 'XMLHttpRequest',
            'Accept': 'text/xml; charset=UTF-8'
        }

    def _get_salt(self, username, password):
        """Get salt to hash password."""
        request_data = {
            'username_or_email': username,
            'wst': ''
        }

        data = self.session.post(Webshare.webshare_url + '/api/salt/',
                                 data=request_data,
                                 headers=self.headers_data)
        LOGGER.debug('Salt resp: %s', data.text)

        xml = eltree.fromstring(data.text)
        if not xml.find('status').text == 'OK':
            LOGGER.fatal('Salt not provided, exiting.')
            sys.exit(1)

        salt = xml.find('salt').text or ''
        LOGGER.debug('Salt collected from xml response: %s', salt)

        dec = plhash.md5_crypt.encrypt(password, salt=salt)
        LOGGER.debug('dec: %s', dec)
        password = hashlib.sha1(dec.encode('utf-8')).hexdigest()

        return password

    def login(self, username=None, password=None):
        """Login to the service."""

        LOGGER.debug('Logging in as %s', username)
        password = self._get_salt(username, password)
        LOGGER.debug('Salted password::: %s', password)

        request_data = {
            'username_or_email': username,
            'password': password,
            'keep_logged_in': "0",
            'wst': ''
        }

        login = self.session.post(Webshare.webshare_url + '/api/login/',
                                  headers=self.headers_data,
                                  data=request_data)
        LOGGER.debug('Login status code: %s', login.status_code)
        LOGGER.debug('Login content resp: %s', login.content)
        LOGGER.debug('Login headers resp: %s', login.headers)

        xml = eltree.fromstring(login.text)
        if not xml.find('status').text == 'OK':
            LOGGER.fatal('Login failed, exiting.')
            sys.exit(1)

        self.token = xml.find('token').text
        LOGGER.debug('Token obtained from xml response: %s', self.token)
        if not self.token:
            return False
        return True

    def search_content(self, what, size_limit=5, category=None):
        """Search the content."""
        LOGGER.debug('Searching content: category > %s, content > %s', category, what)

        request_data = {
            'category': category,
            'what': what.replace(' ', '%20'),
            'sort': '',
            'offset': '0',
            'limit': '15',
            'wst': self.token
        }

        LOGGER.debug('Data transmitted: %s', request_data)

        self.headers_data['Cookie'] = 'wst=' + self.token
        self.headers_data['Content-type'] = 'application/x-www-form-urlencoded; charset=UTF-8'

        response = self.session.post(Webshare.webshare_url + '/api/search/',
                                     headers=self.headers_data,
                                     data=request_data)
        LOGGER.debug('Content search response text: %s', response.text)

        if not response:
            return False

        xml = eltree.fromstring(response.text)
        if not xml.find('status').text == 'OK':
            LOGGER.fatal('Content search failed, exiting.')
            sys.exit(1)

        name_length_format = 0
        for item in xml.findall('file'):
            name = item.find('name').text
            name = len(name)
            if name > name_length_format:
                name_length_format = name

        if name_length_format == 0:
            LOGGER.error('No content found.')
            sys.exit(1)

        print('-' * (21 + int(name_length_format)))
        print('{:6} | {:{}} | {}'.format('INDEX', 'NAME',
                                         name_length_format, 'SIZE (GB)'))
        print('-' * (21 + int(name_length_format)))

        for index, datafile in enumerate(xml.findall('file')):
            name = datafile.find('name').text
            size = round(int(datafile.find('size').text) / 1024 / 1024 / 1024, 2)
            if size_limit is not None:
                if size < size_limit and size > 0.1:
                    self.datalist.append({'index': index, 'name': name, 'size': size})
                else:
                    continue

        datalist_processed = self._process_output(what)
        if not datalist_processed:
            return False

        for item in datalist_processed:
            print('{:6} | {:{}} | {}'.format(item[1]['index'], item[1]['name'],
                                             name_length_format, item[1]['size']))

        print('-' * (21 + int(name_length_format)))
        selected = input('Please select the item by its index: ')

        return xml, selected

    @staticmethod
    def _remove_accents(input_str):
        """Remove diacritics.
        Parameters:
        input_str (str): String to process upon
        """
        nfkd_form = unicodedata.normalize('NFKD', input_str)
        return u"".join([c for c in nfkd_form if not unicodedata.combining(c)])

    def _process_output(self, what):
        """Get rid of nonsense.
        Parameters:
        what (str): search string
        """
        sname = what.split(' ')
        datalist_processed = list()
        for datafile in self.datalist:
            LOGGER.debug('Processing datafile: %s', datafile)
            df_normalized = Webshare._remove_accents(datafile['name'].lower()).replace('.', ' ')
            LOGGER.debug('name wihouth/with diacritics: %s <--> %s', df_normalized, datafile['name'])
            rank = 0
            for word in sname:
                word_diafree = Webshare._remove_accents(word)
                wmatch = re.match(r'.*(' + word_diafree.lower() + ').*', df_normalized)
                digitmatch = re.match(r'.*[\s|0]' + word_diafree + '\s.*', df_normalized)
                seriesmatch = re.match(r'.*\s' + word_diafree + '\s.*', df_normalized)
                if wmatch and len(word) > 3:
                    LOGGER.debug('2rank word: %s in %s', word, datafile['name'])
                    rank += 2
                elif digitmatch:
                    LOGGER.debug('2rank digitmatch: %s', digitmatch)
                    rank += 2
                if seriesmatch:
                    LOGGER.debug('1rank seriesmatch: %s', seriesmatch)
                    rank += 1

            if rank == 0:
                # LOGGER.warning('Datafile is not included in the result: %s',
                #                datafile['name'])
                continue

            match1 = re.match(r'.*([1][9][4-9][0-9]}).*', datafile['name'])
            match2 = re.match(r'.*([2][0][0-3][0-9]).*', datafile['name'])

            if match1:
                LOGGER.debug('1rank match: %s', match1)
                rank += 1
            elif match2:
                LOGGER.debug('1rank match: %s', match2)
                rank += 1
            if 'trailer' in datafile['name'].lower():
                LOGGER.debug('-1rank word: %s', trailer)
                rank -= 1
            if 'cz' or 'sk' in datafile['name'].lower():
                LOGGER.debug('1rank word: %s', 'cz/sk')
                rank += 1

            result = (rank, datafile)
            datalist_processed.append(result)

        def sortf(rule):
            """Sort helper function."""
            return(rule[0])
        datalist_processed.sort(key=sortf, reverse=True)

        # for entry in datalist_processed:
        #     link = self._get_file_link(entry[1]['ident'])
        #     entry[1]['file_link'] = link

        return datalist_processed

    def get_file(self, xml_resp, selection):
        """Get file."""

        for index, datafile in enumerate(xml_resp.findall('file')):
            if index == int(selection):
                name = datafile.find('name').text
                ident = datafile.find('ident').text
                break

        request_data = {
            'ident': ident,
            'password': '',
            'wst': self.token
        }

        LOGGER.debug('File name: %s \n Ident: %s', name, ident)

        download_file = self.session.post(Webshare.webshare_url + '/api/file_link/',
                                          headers=self.headers_data,
                                          data=request_data)

        xml = eltree.fromstring(download_file.text)
        if not xml.find('status').text == 'OK':
            LOGGER.fatal('Data not provided, exiting.')
            sys.exit(1)

        link = xml.find('link')
        LOGGER.debug('Link obtained: %s', link)

        return link.text
