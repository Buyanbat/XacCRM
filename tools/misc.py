# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>).
#    Copyright (C) 2010 OpenERP s.a. (<http://openerp.com>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

"""
Miscelleanous tools used by OpenERP.
"""

import os, time, sys
import inspect
from datetime import datetime

from config import config

import zipfile
import release
import socket
import logging
import re
from itertools import islice
import threading
from which import which

import smtplib
from email.MIMEText import MIMEText
from email.MIMEBase import MIMEBase
from email.MIMEMultipart import MIMEMultipart
from email.Header import Header
from email.Utils import formatdate, COMMASPACE
from email.Utils import formatdate, COMMASPACE
from email import Encoders
import netsvc

if sys.version_info[:2] < (2, 4):
    from threadinglocal import local
else:
    from threading import local

from itertools import izip

_logger = logging.getLogger('tools')

# initialize a database with base/base.sql
def init_db(cr):
    import addons
    f = addons.get_module_resource('base', 'base.sql')
    for line in file_open(f).read().split(';'):
        if (len(line)>0) and (not line.isspace()):
            cr.execute(line)
    cr.commit()

    for i in addons.get_modules():
        mod_path = addons.get_module_path(i)
        if not mod_path:
            continue

        info = addons.load_information_from_description_file(i)

        if not info:
            continue
        categs = info.get('category', 'Uncategorized').split('/')
        p_id = None
        while categs:
            if p_id is not None:
                cr.execute('select id \
                           from ir_module_category \
                           where name=%s and parent_id=%s', (categs[0], p_id))
            else:
                cr.execute('select id \
                           from ir_module_category \
                           where name=%s and parent_id is NULL', (categs[0],))
            c_id = cr.fetchone()
            if not c_id:
                cr.execute('select nextval(\'ir_module_category_id_seq\')')
                c_id = cr.fetchone()[0]
                cr.execute('insert into ir_module_category \
                        (id, name, parent_id) \
                        values (%s, %s, %s)', (c_id, categs[0], p_id))
            else:
                c_id = c_id[0]
            p_id = c_id
            categs = categs[1:]

        active = info.get('active', False)
        installable = info.get('installable', True)
        if installable:
            if active:
                state = 'to install'
            else:
                state = 'uninstalled'
        else:
            state = 'uninstallable'
        cr.execute('select nextval(\'ir_module_module_id_seq\')')
        id = cr.fetchone()[0]
        cr.execute('insert into ir_module_module \
                (id, author, website, name, shortdesc, description, \
                    category_id, state, certificate) \
                values (%s, %s, %s, %s, %s, %s, %s, %s, %s)', (
            id, info.get('author', ''),
            info.get('website', ''), i, info.get('name', False),
            info.get('description', ''), p_id, state, info.get('certificate') or None))
        cr.execute('insert into ir_model_data \
            (name,model,module, res_id, noupdate) values (%s,%s,%s,%s,%s)', (
                'module_meta_information', 'ir.module.module', i, id, True))
        dependencies = info.get('depends', [])
        for d in dependencies:
            cr.execute('insert into ir_module_module_dependency \
                    (module_id,name) values (%s, %s)', (id, d))
        cr.commit()

def find_in_path(name):
    try:
        return which(name)
    except IOError:
        return None

def find_pg_tool(name):
    path = None
    if config['pg_path'] and config['pg_path'] != 'None':
        path = config['pg_path']
    try:
        return which(name, path=path)
    except IOError:
        return None

def exec_pg_command(name, *args):
    prog = find_pg_tool(name)
    if not prog:
        raise Exception('Couldn\'t find %s' % name)
    args2 = (os.path.basename(prog),) + args
    return os.spawnv(os.P_WAIT, prog, args2)

def exec_pg_command_pipe(name, *args):
    prog = find_pg_tool(name)
    if not prog:
        raise Exception('Couldn\'t find %s' % name)
    if os.name == "nt":
        cmd = '"' + prog + '" ' + ' '.join(args)
    else:
        cmd = prog + ' ' + ' '.join(args)
    return os.popen2(cmd, 'b')

def exec_command_pipe(name, *args):
    prog = find_in_path(name)
    if not prog:
        raise Exception('Couldn\'t find %s' % name)
    if os.name == "nt":
        cmd = '"'+prog+'" '+' '.join(args)
    else:
        cmd = prog+' '+' '.join(args)
    return os.popen2(cmd, 'b')

#----------------------------------------------------------
# File paths
#----------------------------------------------------------
#file_path_root = os.getcwd()
#file_path_addons = os.path.join(file_path_root, 'addons')

def file_open(name, mode="r", subdir='addons', pathinfo=False):
    """Open a file from the OpenERP root, using a subdir folder.

    >>> file_open('hr/report/timesheer.xsl')
    >>> file_open('addons/hr/report/timesheet.xsl')
    >>> file_open('../../base/report/rml_template.xsl', subdir='addons/hr/report', pathinfo=True)

    @param name: name of the file
    @param mode: file open mode
    @param subdir: subdirectory
    @param pathinfo: if True returns tupple (fileobject, filepath)

    @return: fileobject if pathinfo is False else (fileobject, filepath)
    """
    import addons
    adps = addons.ad_paths
    rtp = os.path.normcase(os.path.abspath(config['root_path']))

    if name.replace(os.path.sep, '/').startswith('addons/'):
        subdir = 'addons'
        name = name[7:]

    # First try to locate in addons_path
    if subdir:
        subdir2 = subdir
        if subdir2.replace(os.path.sep, '/').startswith('addons/'):
            subdir2 = subdir2[7:]

        subdir2 = (subdir2 != 'addons' or None) and subdir2

        for adp in adps:
          try:
            if subdir2:
                fn = os.path.join(adp, subdir2, name)
            else:
                fn = os.path.join(adp, name)
            fn = os.path.normpath(fn)
            fo = file_open(fn, mode=mode, subdir=None, pathinfo=pathinfo)
            if pathinfo:
                return fo, fn
            return fo
          except IOError, e:
            pass

    if subdir:
        name = os.path.join(rtp, subdir, name)
    else:
        name = os.path.join(rtp, name)

    name = os.path.normpath(name)

    # Check for a zipfile in the path
    head = name
    zipname = False
    name2 = False
    while True:
        head, tail = os.path.split(head)
        if not tail:
            break
        if zipname:
            zipname = os.path.join(tail, zipname)
        else:
            zipname = tail
        if zipfile.is_zipfile(head+'.zip'):
            from cStringIO import StringIO
            zfile = zipfile.ZipFile(head+'.zip')
            try:
                fo = StringIO()
                fo.write(zfile.read(os.path.join(
                    os.path.basename(head), zipname).replace(
                        os.sep, '/')))
                fo.seek(0)
                if pathinfo:
                    return fo, name
                return fo
            except:
                name2 = os.path.normpath(os.path.join(head + '.zip', zipname))
                pass
    for i in (name2, name):
        if i and os.path.isfile(i):
            fo = file(i, mode)
            if pathinfo:
                return fo, i
            return fo
    if os.path.splitext(name)[1] == '.rml':
        raise IOError, 'Report %s doesn\'t exist or deleted : ' %str(name)
    raise IOError, 'File not found : '+str(name)


#----------------------------------------------------------
# iterables
#----------------------------------------------------------
def flatten(list):
    """Flatten a list of elements into a uniqu list
    Author: Christophe Simonis (christophe@tinyerp.com)

    Examples:
    >>> flatten(['a'])
    ['a']
    >>> flatten('b')
    ['b']
    >>> flatten( [] )
    []
    >>> flatten( [[], [[]]] )
    []
    >>> flatten( [[['a','b'], 'c'], 'd', ['e', [], 'f']] )
    ['a', 'b', 'c', 'd', 'e', 'f']
    >>> t = (1,2,(3,), [4, 5, [6, [7], (8, 9), ([10, 11, (12, 13)]), [14, [], (15,)], []]])
    >>> flatten(t)
    [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15]
    """

    def isiterable(x):
        return hasattr(x, "__iter__")

    r = []
    for e in list:
        if isiterable(e):
            map(r.append, flatten(e))
        else:
            r.append(e)
    return r

def reverse_enumerate(l):
    """Like enumerate but in the other sens
    >>> a = ['a', 'b', 'c']
    >>> it = reverse_enumerate(a)
    >>> it.next()
    (2, 'c')
    >>> it.next()
    (1, 'b')
    >>> it.next()
    (0, 'a')
    >>> it.next()
    Traceback (most recent call last):
      File "<stdin>", line 1, in <module>
    StopIteration
    """
    return izip(xrange(len(l)-1, -1, -1), reversed(l))

#----------------------------------------------------------
# Emails
#----------------------------------------------------------
email_re = re.compile(r"""
    ([a-zA-Z][\w\.-]*[a-zA-Z0-9]     # username part
    @                                # mandatory @ sign
    [a-zA-Z0-9][\w\.-]*              # domain must start with a letter ... Ged> why do we include a 0-9 then?
     \.
     [a-z]{2,3}                      # TLD
    )
    """, re.VERBOSE)
res_re = re.compile(r"\[([0-9]+)\]", re.UNICODE)
command_re = re.compile("^Set-([a-z]+) *: *(.+)$", re.I + re.UNICODE)
reference_re = re.compile("<.*-openobject-(\\d+)@(.*)>", re.UNICODE)

priorities = {
        '1': '1 (Highest)',
        '2': '2 (High)',
        '3': '3 (Normal)',
        '4': '4 (Low)',
        '5': '5 (Lowest)',
    }

def html2plaintext(html, body_id=None, encoding='utf-8'):
    ## (c) Fry-IT, www.fry-it.com, 2007
    ## <peter@fry-it.com>
    ## download here: http://www.peterbe.com/plog/html2plaintext


    """ from an HTML text, convert the HTML to plain text.
    If @body_id is provided then this is the tag where the
    body (not necessarily <body>) starts.
    """

    html = ustr(html)

    from lxml.etree import Element, tostring
    try:
        from lxml.html.soupparser import fromstring
        kwargs = {}
    except ImportError:
        _logger.debug('tools.misc.html2plaintext: cannot use BeautifulSoup, fallback to lxml.etree.HTMLParser')
        from lxml.etree import fromstring, HTMLParser
        kwargs = dict(parser=HTMLParser())

    tree = fromstring(html, **kwargs)

    if body_id is not None:
        source = tree.xpath('//*[@id=%s]'%(body_id,))
    else:
        source = tree.xpath('//body')
    if len(source):
        tree = source[0]

    url_index = []
    i = 0
    for link in tree.findall('.//a'):
        title = link.text
        url = link.get('href')
        if url:
            i += 1
            link.tag = 'span'
            link.text = '%s [%s]' % (link.text, i)
            url_index.append(url)

    html = ustr(tostring(tree, encoding=encoding))

    html = html.replace('<strong>','*').replace('</strong>','*')
    html = html.replace('<b>','*').replace('</b>','*')
    html = html.replace('<h3>','*').replace('</h3>','*')
    html = html.replace('<h2>','**').replace('</h2>','**')
    html = html.replace('<h1>','**').replace('</h1>','**')
    html = html.replace('<em>','/').replace('</em>','/')
    html = html.replace('<tr>', '\n')
    html = html.replace('</p>', '\n')
    html = re.sub('<br\s*/?>', '\n', html)
    html = re.sub('<.*?>', ' ', html)
    html = html.replace(' ' * 2, ' ')

    # strip all lines
    html = '\n'.join([x.strip() for x in html.splitlines()])
    html = html.replace('\n' * 2, '\n')

    for i, url in enumerate(url_index):
        if i == 0:
            html += '\n\n'
        html += ustr('[%s] %s\n') % (i+1, url)

    return html

def _email_send(smtp_from, smtp_to_list, message, openobject_id=None, ssl=False, debug=False):
    """Low-level method to send directly a Message through the configured smtp server.
        :param smtp_from: RFC-822 envelope FROM (not displayed to recipient)
        :param smtp_to_list: RFC-822 envelope RCPT_TOs (not displayed to recipient)
        :param message: an email.message.Message to send
        :param debug: True if messages should be output to stderr before being sent,
                      and smtplib.SMTP put into debug mode.
        :return: True if the mail was delivered successfully to the smtp,
                 else False (+ exception logged)
    """
    if openobject_id:
        message['Message-Id'] = "<%s-openobject-%s@%s>" % (time.time(), openobject_id, socket.gethostname())

    try:
        smtp_server = config['smtp_server']

        if smtp_server.startswith('maildir:/'):
            from mailbox import Maildir
            maildir_path = smtp_server[8:]
            mdir = Maildir(maildir_path,factory=None, create = True)
            mdir.add(msg.as_string(True))
            return True

        oldstderr = smtplib.stderr
        if not ssl: ssl = config.get('smtp_ssl', False)
        s = smtplib.SMTP()
        try:
            # in case of debug, the messages are printed to stderr.
            if debug:
                smtplib.stderr = WriteToLogger()

            s.set_debuglevel(int(bool(debug)))  # 0 or 1
            s.connect(smtp_server, config['smtp_port'])
            if ssl:
                s.ehlo()
                s.starttls()
                s.ehlo()

            if config['smtp_user'] or config['smtp_password']:
                s.login(config['smtp_user'], config['smtp_password'])

            s.sendmail(smtp_from, smtp_to_list, message.as_string())
        finally:
            try:
                s.quit()
                if debug:
                    smtplib.stderr = oldstderr
            except:
                # ignored, just a consequence of the previous exception
                pass

    except Exception, e:
        _logger.error('could not deliver email', exc_info=True)
        return False

    return True


def email_send(email_from, email_to, subject, body, email_cc=None, email_bcc=None, reply_to=False,
               attach=None, openobject_id=False, ssl=False, debug=False, subtype='plain', x_headers=None, priority='3'):

    """Send an email.

    Arguments:

    `email_from`: A string used to fill the `From` header, if falsy,
                  config['email_from'] is used instead.  Also used for
                  the `Reply-To` header if `reply_to` is not provided

    `email_to`: a sequence of addresses to send the mail to.
    """
    if x_headers is None:
        x_headers = {}


    if not (email_from or config['email_from']):
        raise ValueError("Sending an email requires either providing a sender "
                         "address or having configured one")

    if not email_from: email_from = config.get('email_from', False)

    if not email_cc: email_cc = []
    if not email_bcc: email_bcc = []
    if not body: body = u''
    try: email_body = body.encode('utf-8')
    except (UnicodeEncodeError, UnicodeDecodeError):
        email_body = body

    try:
        email_text = MIMEText(email_body.encode('utf8') or '',_subtype=subtype,_charset='utf-8')
    except:
        email_text = MIMEText(email_body or '',_subtype=subtype,_charset='utf-8')

    if attach: msg = MIMEMultipart()
    else: msg = email_text

    msg['Subject'] = Header(ustr(subject), 'utf-8')
    msg['From'] = email_from
    del msg['Reply-To']
    if reply_to:
        msg['Reply-To'] = reply_to
    else:
        msg['Reply-To'] = msg['From']
    msg['To'] = COMMASPACE.join(email_to)
    if email_cc:
        msg['Cc'] = COMMASPACE.join(email_cc)
    if email_bcc:
        msg['Bcc'] = COMMASPACE.join(email_bcc)
    msg['Date'] = formatdate(localtime=True)

    msg['X-Priority'] = priorities.get(priority, '3 (Normal)')

    # Add dynamic X Header
    for key, value in x_headers.iteritems():
        msg['%s' % key] = str(value)

    if attach:
        msg.attach(email_text)
        for (fname,fcontent) in attach:
            part = MIMEBase('application', "octet-stream")
            part.set_payload( fcontent )
            Encoders.encode_base64(part)
            part.add_header('Content-Disposition', 'attachment; filename="%s"' % (fname,))
            msg.attach(part)

    class WriteToLogger(object):
        def __init__(self):
            self.logger = netsvc.Logger()

        def write(self, s):
            self.logger.notifyChannel('email_send', netsvc.LOG_DEBUG, s)

    return _email_send(email_from, flatten([email_to, email_cc, email_bcc]), msg, openobject_id=openobject_id, ssl=ssl, debug=debug)

#----------------------------------------------------------
# SMS
#----------------------------------------------------------
# text must be latin-1 encoded
def sms_send(user, password, api_id, text, to):
    import urllib
    url = "http://api.urlsms.com/SendSMS.aspx"
    #url = "http://196.7.150.220/http/sendmsg"
    params = urllib.urlencode({'UserID': user, 'Password': password, 'SenderID': api_id, 'MsgText': text, 'RecipientMobileNo':to})
    f = urllib.urlopen(url+"?"+params)
    # FIXME: Use the logger if there is an error
    return True

#---------------------------------------------------------
# Class that stores an updateable string (used in wizards)
#---------------------------------------------------------
class UpdateableStr(local):

    def __init__(self, string=''):
        self.string = string

    def __str__(self):
        return str(self.string)

    def __repr__(self):
        return str(self.string)

    def __nonzero__(self):
        return bool(self.string)


class UpdateableDict(local):
    '''Stores an updateable dict to use in wizards'''

    def __init__(self, dict=None):
        if dict is None:
            dict = {}
        self.dict = dict

    def __str__(self):
        return str(self.dict)

    def __repr__(self):
        return str(self.dict)

    def clear(self):
        return self.dict.clear()

    def keys(self):
        return self.dict.keys()

    def __setitem__(self, i, y):
        self.dict.__setitem__(i, y)

    def __getitem__(self, i):
        return self.dict.__getitem__(i)

    def copy(self):
        return self.dict.copy()

    def iteritems(self):
        return self.dict.iteritems()

    def iterkeys(self):
        return self.dict.iterkeys()

    def itervalues(self):
        return self.dict.itervalues()

    def pop(self, k, d=None):
        return self.dict.pop(k, d)

    def popitem(self):
        return self.dict.popitem()

    def setdefault(self, k, d=None):
        return self.dict.setdefault(k, d)

    def update(self, E, **F):
        return self.dict.update(E, F)

    def values(self):
        return self.dict.values()

    def get(self, k, d=None):
        return self.dict.get(k, d)

    def has_key(self, k):
        return self.dict.has_key(k)

    def items(self):
        return self.dict.items()

    def __cmp__(self, y):
        return self.dict.__cmp__(y)

    def __contains__(self, k):
        return self.dict.__contains__(k)

    def __delitem__(self, y):
        return self.dict.__delitem__(y)

    def __eq__(self, y):
        return self.dict.__eq__(y)

    def __ge__(self, y):
        return self.dict.__ge__(y)

    def __gt__(self, y):
        return self.dict.__gt__(y)

    def __hash__(self):
        return self.dict.__hash__()

    def __iter__(self):
        return self.dict.__iter__()

    def __le__(self, y):
        return self.dict.__le__(y)

    def __len__(self):
        return self.dict.__len__()

    def __lt__(self, y):
        return self.dict.__lt__(y)

    def __ne__(self, y):
        return self.dict.__ne__(y)


# Don't use ! Use res.currency.round()
class currency(float):

    def __init__(self, value, accuracy=2, rounding=None):
        if rounding is None:
            rounding=10**-accuracy
        self.rounding=rounding
        self.accuracy=accuracy

    def __new__(cls, value, accuracy=2, rounding=None):
        return float.__new__(cls, round(value, accuracy))

    #def __str__(self):
    #   display_value = int(self*(10**(-self.accuracy))/self.rounding)*self.rounding/(10**(-self.accuracy))
    #   return str(display_value)


def is_hashable(h):
    try:
        hash(h)
        return True
    except TypeError:
        return False

class cache(object):
    """
    Use it as a decorator of the function you plan to cache
    Timeout: 0 = no timeout, otherwise in seconds
    """

    __caches = []

    def __init__(self, timeout=None, skiparg=2, multi=None):
        assert skiparg >= 2 # at least self and cr
        if timeout is None:
            self.timeout = config['cache_timeout']
        else:
            self.timeout = timeout
        self.skiparg = skiparg
        self.multi = multi
        self.lasttime = time.time()
        self.cache = {}
        self.fun = None
        cache.__caches.append(self)


    def _generate_keys(self, dbname, kwargs2):
        """
        Generate keys depending of the arguments and the self.mutli value
        """

        def to_tuple(d):
            pairs = d.items()
            pairs.sort(key=lambda (k,v): k)
            for i, (k, v) in enumerate(pairs):
                if isinstance(v, dict):
                    pairs[i] = (k, to_tuple(v))
                if isinstance(v, (list, set)):
                    pairs[i] = (k, tuple(v))
                elif not is_hashable(v):
                    pairs[i] = (k, repr(v))
            return tuple(pairs)

        if not self.multi:
            key = (('dbname', dbname),) + to_tuple(kwargs2)
            yield key, None
        else:
            multis = kwargs2[self.multi][:]
            for id in multis:
                kwargs2[self.multi] = (id,)
                key = (('dbname', dbname),) + to_tuple(kwargs2)
                yield key, id

    def _unify_args(self, *args, **kwargs):
        # Update named arguments with positional argument values (without self and cr)
        kwargs2 = self.fun_default_values.copy()
        kwargs2.update(kwargs)
        kwargs2.update(dict(zip(self.fun_arg_names, args[self.skiparg-2:])))
        return kwargs2

    def clear(self, dbname, *args, **kwargs):
        """clear the cache for database dbname
            if *args and **kwargs are both empty, clear all the keys related to this database
        """
        if not args and not kwargs:
            keys_to_del = [key for key in self.cache.keys() if key[0][1] == dbname]
        else:
            kwargs2 = self._unify_args(*args, **kwargs)
            keys_to_del = [key for key, _ in self._generate_keys(dbname, kwargs2) if key in self.cache.keys()]

        for key in keys_to_del:
            self.cache.pop(key)

    @classmethod
    def clean_caches_for_db(cls, dbname):
        for c in cls.__caches:
            c.clear(dbname)

    def __call__(self, fn):
        if self.fun is not None:
            raise Exception("Can not use a cache instance on more than one function")
        self.fun = fn

        argspec = inspect.getargspec(fn)
        self.fun_arg_names = argspec[0][self.skiparg:]
        self.fun_default_values = {}
        if argspec[3]:
            self.fun_default_values = dict(zip(self.fun_arg_names[-len(argspec[3]):], argspec[3]))

        def cached_result(self2, cr, *args, **kwargs):
            if time.time()-int(self.timeout) > self.lasttime:
                self.lasttime = time.time()
                t = time.time()-int(self.timeout)
                old_keys = [key for key in self.cache.keys() if self.cache[key][1] < t]
                for key in old_keys:
                    self.cache.pop(key)

            kwargs2 = self._unify_args(*args, **kwargs)

            result = {}
            notincache = {}
            for key, id in self._generate_keys(cr.dbname, kwargs2):
                if key in self.cache:
                    result[id] = self.cache[key][0]
                else:
                    notincache[id] = key

            if notincache:
                if self.multi:
                    kwargs2[self.multi] = notincache.keys()

                result2 = fn(self2, cr, *args[:self.skiparg-2], **kwargs2)
                if not self.multi:
                    key = notincache[None]
                    self.cache[key] = (result2, time.time())
                    result[None] = result2
                else:
                    for id in result2:
                        key = notincache[id]
                        self.cache[key] = (result2[id], time.time())
                    result.update(result2)

            if not self.multi:
                return result[None]
            return result

        cached_result.clear_cache = self.clear
        return cached_result

def to_xml(s):
    return s.replace('&','&amp;').replace('<','&lt;').replace('>','&gt;')

def get_encodings(hint_encoding='utf-8'):
    fallbacks = {
        'latin1': 'latin9',
        'iso-8859-1': 'iso8859-15',
        'cp1252': '1252',
    }
    if hint_encoding:
        yield hint_encoding
        if hint_encoding.lower() in fallbacks:
            yield fallbacks[hint_encoding.lower()]

    # some defaults (also taking care of pure ASCII)
    for charset in ['utf8','latin1']:
        if not (hint_encoding) or (charset.lower() != hint_encoding.lower()):
            yield charset

    from locale import getpreferredencoding
    prefenc = getpreferredencoding()
    if prefenc and prefenc.lower() != 'utf-8':
        yield prefenc
        prefenc = fallbacks.get(prefenc.lower())
        if prefenc:
            yield prefenc


def ustr(value, hint_encoding='utf-8'):
    """This method is similar to the builtin `str` method, except
       it will return unicode() string.

    @param value: the value to convert
    @param hint_encoding: an optional encoding that was detected
                          upstream and should be tried first to
                          decode ``value``.

    @rtype: unicode
    @return: unicode string
    """
    if isinstance(value, Exception):
        return exception_to_unicode(value)

    if isinstance(value, unicode):
        return value

    if not isinstance(value, basestring):
        try:
            return unicode(value)
        except Exception:
            raise UnicodeError('unable de to convert %r' % (value,))

    for ln in get_encodings(hint_encoding):
        try:
            return unicode(value, ln)
        except Exception:
            pass
    raise UnicodeError('unable de to convert %r' % (value,))


def exception_to_unicode(e):
    if (sys.version_info[:2] < (2,6)) and hasattr(e, 'message'):
        return ustr(e.message)
    if hasattr(e, 'args'):
        return "\n".join((ustr(a) for a in e.args))
    try:
        return ustr(e)
    except:
        return u"Unknown message"


# to be compatible with python 2.4
import __builtin__
if not hasattr(__builtin__, 'all'):
    def all(iterable):
        for element in iterable:
            if not element:
                return False
        return True

    __builtin__.all = all
    del all

if not hasattr(__builtin__, 'any'):
    def any(iterable):
        for element in iterable:
            if element:
                return True
        return False

    __builtin__.any = any
    del any

def get_iso_codes(lang):
    if lang.find('_') != -1:
        if lang.split('_')[0] == lang.split('_')[1].lower():
            lang = lang.split('_')[0]
    return lang

def get_languages():
    languages={
        'ab_RU': u'Abkhazian (RU)',
        'ar_AR': u'Arabic / الْعَرَبيّة',
        'bg_BG': u'Bulgarian / български',
        'bs_BS': u'Bosnian / bosanski jezik',
        'ca_ES': u'Catalan / Català',
        'cs_CZ': u'Czech / Čeština',
        'da_DK': u'Danish / Dansk',
        'de_DE': u'German / Deutsch',
        'el_GR': u'Greek / Ελληνικά',
        'en_CA': u'English (CA)',
        'en_GB': u'English (UK)',
        'en_US': u'English (US)',
        'es_AR': u'Spanish (AR) / Español (AR)',
        'es_ES': u'Spanish / Español',
        'et_EE': u'Estonian / Eesti keel',
        'fa_IR': u'Persian / فارس',
        'fi_FI': u'Finland / Suomi',
        'fr_BE': u'French (BE) / Français (BE)',
        'fr_CH': u'French (CH) / Français (CH)',
        'fr_FR': u'French / Français',
        'gl_ES': u'Galician / Galego',
        'gu_IN': u'Gujarati / India',
        'hi_IN': u'Hindi / India',
        'hr_HR': u'Croatian / hrvatski jezik',
        'hu_HU': u'Hungarian / Magyar',
        'id_ID': u'Indonesian / Bahasa Indonesia',
        'it_IT': u'Italian / Italiano',
        'iu_CA': u'Inuktitut / Canada',
        'ja_JP': u'Japanese / Japan',
        'ko_KP': u'Korean / Korea, Democratic Peoples Republic of',
        'ko_KR': u'Korean / Korea, Republic of',
        'lt_LT': u'Lithuanian / Lietuvių kalba',
        'lv_LV': u'Latvian / Latvia',
        'ml_IN': u'Malayalam / India',
        'mn_MN': u'Mongolian / Mongolia',
        'nb_NO': u'Norwegian Bokmål / Norway',
        'nl_NL': u'Dutch / Nederlands',
        'nl_BE': u'Dutch (Belgium) / Nederlands (Belgïe)',
        'oc_FR': u'Occitan (post 1500) / France',
        'pl_PL': u'Polish / Język polski',
        'pt_BR': u'Portugese (BR) / português (BR)',
        'pt_PT': u'Portugese / português',
        'ro_RO': u'Romanian / limba română',
        'ru_RU': u'Russian / русский язык',
        'si_LK': u'Sinhalese / Sri Lanka',
        'sl_SI': u'Slovenian / slovenščina',
        'sk_SK': u'Slovak / Slovenský jazyk',
        'sq_AL': u'Albanian / Shqipëri',
        'sr_RS': u'Serbian / Serbia',
        'sv_SE': u'Swedish / svenska',
        'te_IN': u'Telugu / India',
        'tr_TR': u'Turkish / Türkçe',
        'vi_VN': u'Vietnam / Cộng hòa xã hội chủ nghĩa Việt Nam',
        'uk_UA': u'Ukrainian / украї́нська мо́ва',
        'ur_PK': u'Urdu / Pakistan',
        'zh_CN': u'Chinese (CN) / 简体中文',
        'zh_HK': u'Chinese (HK)',
        'zh_TW': u'Chinese (TW) / 正體字',
        'th_TH': u'Thai / ภาษาไทย',
        'tlh_TLH': u'Klingon',
    }
    return languages

def scan_languages():
#    import glob
#    file_list = [os.path.splitext(os.path.basename(f))[0] for f in glob.glob(os.path.join(config['root_path'],'addons', 'base', 'i18n', '*.po'))]
#    ret = [(lang, lang_dict.get(lang, lang)) for lang in file_list]
    # Now it will take all languages from get languages function without filter it with base module languages
    lang_dict = get_languages()
    ret = [(lang, lang_dict.get(lang, lang)) for lang in list(lang_dict)]
    ret.sort(key=lambda k:k[1])
    return ret


def get_user_companies(cr, user):
    def _get_company_children(cr, ids):
        if not ids:
            return []
        cr.execute('SELECT id FROM res_company WHERE parent_id IN %s', (tuple(ids),))
        res = [x[0] for x in cr.fetchall()]
        res.extend(_get_company_children(cr, res))
        return res
    cr.execute('SELECT company_id FROM res_users WHERE id=%s', (user,))
    user_comp = cr.fetchone()[0]
    if not user_comp:
        return []
    return [user_comp] + _get_company_children(cr, [user_comp])

def mod10r(number):
    """
    Input number : account or invoice number
    Output return: the same number completed with the recursive mod10
    key
    """
    codec=[0,9,4,6,8,2,7,1,3,5]
    report = 0
    result=""
    for digit in number:
        result += digit
        if digit.isdigit():
            report = codec[ (int(digit) + report) % 10 ]
    return result + str((10 - report) % 10)


def human_size(sz):
    """
    Return the size in a human readable format
    """
    if not sz:
        return False
    units = ('bytes', 'Kb', 'Mb', 'Gb')
    if isinstance(sz,basestring):
        sz=len(sz)
    s, i = float(sz), 0
    while s >= 1024 and i < len(units)-1:
        s = s / 1024
        i = i + 1
    return "%0.2f %s" % (s, units[i])

def logged(f):
    from tools.func import wraps

    @wraps(f)
    def wrapper(*args, **kwargs):
        import netsvc
        from pprint import pformat

        vector = ['Call -> function: %r' % f]
        for i, arg in enumerate(args):
            vector.append('  arg %02d: %s' % (i, pformat(arg)))
        for key, value in kwargs.items():
            vector.append('  kwarg %10s: %s' % (key, pformat(value)))

        timeb4 = time.time()
        res = f(*args, **kwargs)

        vector.append('  result: %s' % pformat(res))
        vector.append('  time delta: %s' % (time.time() - timeb4))
        netsvc.Logger().notifyChannel('logged', netsvc.LOG_DEBUG, '\n'.join(vector))
        return res

    return wrapper

class profile(object):
    def __init__(self, fname=None):
        self.fname = fname

    def __call__(self, f):
        from tools.func import wraps

        @wraps(f)
        def wrapper(*args, **kwargs):
            class profile_wrapper(object):
                def __init__(self):
                    self.result = None
                def __call__(self):
                    self.result = f(*args, **kwargs)
            pw = profile_wrapper()
            import cProfile
            fname = self.fname or ("%s.cprof" % (f.func_name,))
            cProfile.runctx('pw()', globals(), locals(), filename=fname)
            return pw.result

        return wrapper

def debug(what):
    """
        This method allow you to debug your code without print
        Example:
        >>> def func_foo(bar)
        ...     baz = bar
        ...     debug(baz)
        ...     qnx = (baz, bar)
        ...     debug(qnx)
        ...
        >>> func_foo(42)

        This will output on the logger:

            [Wed Dec 25 00:00:00 2008] DEBUG:func_foo:baz = 42
            [Wed Dec 25 00:00:00 2008] DEBUG:func_foo:qnx = (42, 42)

        To view the DEBUG lines in the logger you must start the server with the option
            --log-level=debug

    """
    import netsvc
    from inspect import stack
    import re
    from pprint import pformat
    st = stack()[1]
    param = re.split("debug *\((.+)\)", st[4][0].strip())[1].strip()
    while param.count(')') > param.count('('): param = param[:param.rfind(')')]
    what = pformat(what)
    if param != what:
        what = "%s = %s" % (param, what)
    netsvc.Logger().notifyChannel(st[3], netsvc.LOG_DEBUG, what)


icons = map(lambda x: (x,x), ['STOCK_ABOUT', 'STOCK_ADD', 'STOCK_APPLY', 'STOCK_BOLD',
'STOCK_CANCEL', 'STOCK_CDROM', 'STOCK_CLEAR', 'STOCK_CLOSE', 'STOCK_COLOR_PICKER',
'STOCK_CONNECT', 'STOCK_CONVERT', 'STOCK_COPY', 'STOCK_CUT', 'STOCK_DELETE',
'STOCK_DIALOG_AUTHENTICATION', 'STOCK_DIALOG_ERROR', 'STOCK_DIALOG_INFO',
'STOCK_DIALOG_QUESTION', 'STOCK_DIALOG_WARNING', 'STOCK_DIRECTORY', 'STOCK_DISCONNECT',
'STOCK_DND', 'STOCK_DND_MULTIPLE', 'STOCK_EDIT', 'STOCK_EXECUTE', 'STOCK_FILE',
'STOCK_FIND', 'STOCK_FIND_AND_REPLACE', 'STOCK_FLOPPY', 'STOCK_GOTO_BOTTOM',
'STOCK_GOTO_FIRST', 'STOCK_GOTO_LAST', 'STOCK_GOTO_TOP', 'STOCK_GO_BACK',
'STOCK_GO_DOWN', 'STOCK_GO_FORWARD', 'STOCK_GO_UP', 'STOCK_HARDDISK',
'STOCK_HELP', 'STOCK_HOME', 'STOCK_INDENT', 'STOCK_INDEX', 'STOCK_ITALIC',
'STOCK_JUMP_TO', 'STOCK_JUSTIFY_CENTER', 'STOCK_JUSTIFY_FILL',
'STOCK_JUSTIFY_LEFT', 'STOCK_JUSTIFY_RIGHT', 'STOCK_MEDIA_FORWARD',
'STOCK_MEDIA_NEXT', 'STOCK_MEDIA_PAUSE', 'STOCK_MEDIA_PLAY',
'STOCK_MEDIA_PREVIOUS', 'STOCK_MEDIA_RECORD', 'STOCK_MEDIA_REWIND',
'STOCK_MEDIA_STOP', 'STOCK_MISSING_IMAGE', 'STOCK_NETWORK', 'STOCK_NEW',
'STOCK_NO', 'STOCK_OK', 'STOCK_OPEN', 'STOCK_PASTE', 'STOCK_PREFERENCES',
'STOCK_PRINT', 'STOCK_PRINT_PREVIEW', 'STOCK_PROPERTIES', 'STOCK_QUIT',
'STOCK_REDO', 'STOCK_REFRESH', 'STOCK_REMOVE', 'STOCK_REVERT_TO_SAVED',
'STOCK_SAVE', 'STOCK_SAVE_AS', 'STOCK_SELECT_COLOR', 'STOCK_SELECT_FONT',
'STOCK_SORT_ASCENDING', 'STOCK_SORT_DESCENDING', 'STOCK_SPELL_CHECK',
'STOCK_STOP', 'STOCK_STRIKETHROUGH', 'STOCK_UNDELETE', 'STOCK_UNDERLINE',
'STOCK_UNDO', 'STOCK_UNINDENT', 'STOCK_YES', 'STOCK_ZOOM_100',
'STOCK_ZOOM_FIT', 'STOCK_ZOOM_IN', 'STOCK_ZOOM_OUT',
'terp-account', 'terp-crm', 'terp-mrp', 'terp-product', 'terp-purchase',
'terp-sale', 'terp-tools', 'terp-administration', 'terp-hr', 'terp-partner',
'terp-project', 'terp-report', 'terp-stock', 'terp-calendar', 'terp-graph',
'terp-check','terp-go-month','terp-go-year','terp-go-today','terp-document-new','terp-camera_test',
'terp-emblem-important','terp-gtk-media-pause','terp-gtk-stop','terp-gnome-cpu-frequency-applet+',
'terp-dialog-close','terp-gtk-jump-to-rtl','terp-gtk-jump-to-ltr','terp-accessories-archiver',
'terp-stock_align_left_24','terp-stock_effects-object-colorize','terp-go-home','terp-gtk-go-back-rtl',
'terp-gtk-go-back-ltr','terp-personal','terp-personal-','terp-personal+','terp-accessories-archiver-minus',
'terp-accessories-archiver+','terp-stock_symbol-selection','terp-call-start','terp-dolar',
'terp-face-plain','terp-folder-blue','terp-folder-green','terp-folder-orange','terp-folder-yellow',
'terp-gdu-smart-failing','terp-go-week','terp-gtk-select-all','terp-locked','terp-mail-forward',
'terp-mail-message-new','terp-mail-replied','terp-rating-rated','terp-stage','terp-stock_format-scientific',
'terp-dolar_ok!','terp-idea','terp-stock_format-default','terp-mail-','terp-mail_delete'
])

def extract_zip_file(zip_file, outdirectory):
    import zipfile
    import os

    zf = zipfile.ZipFile(zip_file, 'r')
    out = outdirectory
    for path in zf.namelist():
        tgt = os.path.join(out, path)
        tgtdir = os.path.dirname(tgt)
        if not os.path.exists(tgtdir):
            os.makedirs(tgtdir)

        if not tgt.endswith(os.sep):
            fp = open(tgt, 'wb')
            fp.write(zf.read(path))
            fp.close()
    zf.close()

def detect_ip_addr():
    """Try a very crude method to figure out a valid external
       IP or hostname for the current machine. Don't rely on this
       for binding to an interface, but it could be used as basis
       for constructing a remote URL to the server.
    """
    def _detect_ip_addr():
        from array import array
        import socket
        from struct import pack, unpack

        try:
            import fcntl
        except ImportError:
            fcntl = None

        ip_addr = None

        if not fcntl: # not UNIX:
            host = socket.gethostname()
            ip_addr = socket.gethostbyname(host)
        else: # UNIX:
            # get all interfaces:
            nbytes = 128 * 32
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            names = array('B', '\0' * nbytes)
            #print 'names: ', names
            outbytes = unpack('iL', fcntl.ioctl( s.fileno(), 0x8912, pack('iL', nbytes, names.buffer_info()[0])))[0]
            namestr = names.tostring()

            # try 64 bit kernel:
            for i in range(0, outbytes, 40):
                name = namestr[i:i+16].split('\0', 1)[0]
                if name != 'lo':
                    ip_addr = socket.inet_ntoa(namestr[i+20:i+24])
                    break

            # try 32 bit kernel:
            if ip_addr is None:
                ifaces = filter(None, [namestr[i:i+32].split('\0', 1)[0] for i in range(0, outbytes, 32)])

                for ifname in [iface for iface in ifaces if iface != 'lo']:
                    ip_addr = socket.inet_ntoa(fcntl.ioctl(s.fileno(), 0x8915, pack('256s', ifname[:15]))[20:24])
                    break

        return ip_addr or 'localhost'

    try:
        ip_addr = _detect_ip_addr()
    except:
        ip_addr = 'localhost'
    return ip_addr

# RATIONALE BEHIND TIMESTAMP CALCULATIONS AND TIMEZONE MANAGEMENT:
#  The server side never does any timestamp calculation, always
#  sends them in a naive (timezone agnostic) format supposed to be
#  expressed within the server timezone, and expects the clients to
#  provide timestamps in the server timezone as well.
#  It stores all timestamps in the database in naive format as well,
#  which also expresses the time in the server timezone.
#  For this reason the server makes its timezone name available via the
#  common/timezone_get() rpc method, which clients need to read
#  to know the appropriate time offset to use when reading/writing
#  times.
def get_win32_timezone():
    """Attempt to return the "standard name" of the current timezone on a win32 system.
       @return: the standard name of the current win32 timezone, or False if it cannot be found.
    """
    res = False
    if (sys.platform == "win32"):
        try:
            import _winreg
            hklm = _winreg.ConnectRegistry(None,_winreg.HKEY_LOCAL_MACHINE)
            current_tz_key = _winreg.OpenKey(hklm, r"SYSTEM\CurrentControlSet\Control\TimeZoneInformation", 0,_winreg.KEY_ALL_ACCESS)
            res = str(_winreg.QueryValueEx(current_tz_key,"StandardName")[0])  # [0] is value, [1] is type code
            _winreg.CloseKey(current_tz_key)
            _winreg.CloseKey(hklm)
        except Exception:
            pass
    return res

def detect_server_timezone():
    """Attempt to detect the timezone to use on the server side.
       Defaults to UTC if no working timezone can be found.
       @return: the timezone identifier as expected by pytz.timezone.
    """
    import time
    import netsvc
    try:
        import pytz
    except:
        netsvc.Logger().notifyChannel("detect_server_timezone", netsvc.LOG_WARNING,
            "Python pytz module is not available. Timezone will be set to UTC by default.")
        return 'UTC'

    # Option 1: the configuration option (did not exist before, so no backwards compatibility issue)
    # Option 2: to be backwards compatible with 5.0 or earlier, the value from time.tzname[0], but only if it is known to pytz
    # Option 3: the environment variable TZ
    sources = [ (config['timezone'], 'OpenERP configuration'),
                (time.tzname[0], 'time.tzname'),
                (os.environ.get('TZ',False),'TZ environment variable'), ]
    # Option 4: OS-specific: /etc/timezone on Unix
    if (os.path.exists("/etc/timezone")):
        tz_value = False
        try:
            f = open("/etc/timezone")
            tz_value = f.read(128).strip()
        except:
            pass
        finally:
            f.close()
        sources.append((tz_value,"/etc/timezone file"))
    # Option 5: timezone info from registry on Win32
    if (sys.platform == "win32"):
        # Timezone info is stored in windows registry.
        # However this is not likely to work very well as the standard name
        # of timezones in windows is rarely something that is known to pytz.
        # But that's ok, it is always possible to use a config option to set
        # it explicitly.
        sources.append((get_win32_timezone(),"Windows Registry"))

    for (value,source) in sources:
        if value:
            try:
                tz = pytz.timezone(value)
                netsvc.Logger().notifyChannel("detect_server_timezone", netsvc.LOG_INFO,
                    "Using timezone %s obtained from %s." % (tz.zone,source))
                return value
            except pytz.UnknownTimeZoneError:
                netsvc.Logger().notifyChannel("detect_server_timezone", netsvc.LOG_WARNING,
                    "The timezone specified in %s (%s) is invalid, ignoring it." % (source,value))

    netsvc.Logger().notifyChannel("detect_server_timezone", netsvc.LOG_WARNING,
        "No valid timezone could be detected, using default UTC timezone. You can specify it explicitly with option 'timezone' in the server configuration.")
    return 'UTC'

def get_server_timezone():
    # timezone detection is safe in multithread, so lazy init is ok here
    if (not config['timezone']):
        config['timezone'] = detect_server_timezone()
    return config['timezone']


DEFAULT_SERVER_DATE_FORMAT = "%Y-%m-%d"
DEFAULT_SERVER_DATETIME_FORMAT = DEFAULT_SERVER_DATE_FORMAT + " %H:%M:%S"

def server_to_local_timestamp(src_tstamp_str, src_format, dst_format, dst_tz_name,
        tz_offset=True, ignore_unparsable_time=True):
    """
    Convert a source timestamp string into a destination timestamp string, attempting to apply the
    correct offset if both the server and local timezone are recognized, or no
    offset at all if they aren't or if tz_offset is false (i.e. assuming they are both in the same TZ).

    WARNING: This method is here to allow formatting dates correctly for inclusion in strings where
             the client would not be able to format/offset it correctly. DO NOT use it for returning
             date fields directly, these are supposed to be handled by the client!!

    @param src_tstamp_str: the str value containing the timestamp in the server timezone.
    @param src_format: the format to use when parsing the server timestamp.
    @param dst_format: the format to use when formatting the resulting timestamp for the local/client timezone.
    @param dst_tz_name: name of the destination timezone (such as the 'tz' value of the client context)
    @param ignore_unparsable_time: if True, return False if src_tstamp_str cannot be parsed
                                   using src_format or formatted using dst_format.

    @return: local/client formatted timestamp, expressed in the local/client timezone if possible
            and if tz_offset is true, or src_tstamp_str if timezone offset could not be determined.
    """
    if not src_tstamp_str:
        return False

    res = src_tstamp_str
    if src_format and dst_format:
        # find out server timezone
        server_tz = get_server_timezone()
        try:
            # dt_value needs to be a datetime.datetime object (so no time.struct_time or mx.DateTime.DateTime here!)
            dt_value = datetime.strptime(src_tstamp_str, src_format)
            if tz_offset and dst_tz_name:
                try:
                    import pytz
                    src_tz = pytz.timezone(server_tz)
                    dst_tz = pytz.timezone(dst_tz_name)
                    src_dt = src_tz.localize(dt_value, is_dst=True)
                    dt_value = src_dt.astimezone(dst_tz)
                except Exception:
                    pass
            res = dt_value.strftime(dst_format)
        except Exception:
            # Normal ways to end up here are if strptime or strftime failed
            if not ignore_unparsable_time:
                return False
    return res


def split_every(n, iterable, piece_maker=tuple):
    """Splits an iterable into length-n pieces. The last piece will be shorter
       if ``n`` does not evenly divide the iterable length.
       @param ``piece_maker``: function to build the pieces
       from the slices (tuple,list,...)
    """
    iterator = iter(iterable)
    piece = piece_maker(islice(iterator, n))
    while piece:
        yield piece
        piece = piece_maker(islice(iterator, n))

if __name__ == '__main__':
    import doctest
    doctest.testmod()

class upload_data_thread(threading.Thread):
    def __init__(self, email, data, type):
        self.args = [('email',email),('type',type),('data',data)]
        super(upload_data_thread,self).__init__()
    def run(self):
        try:
            import urllib
            args = urllib.urlencode(self.args)
            fp = urllib.urlopen('http://www.openerp.com/scripts/survey.php', args)
            fp.read()
            fp.close()
        except:
            pass

def upload_data(email, data, type='SURVEY'):
    a = upload_data_thread(email, data, type)
    a.start()
    return True
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

