# coding: utf-8
"""
Utility functions for PDF library.
"""
import os as _os
import io as _io
import inspect as _insp
from hashlib import md5 as _md5
import struct as _s

ENCODING_UTF8 = 'utf-8'
ENCODING_UTF16 = 'utf-16'
ENCODING_UTF16BE = 'utf-16be'
DELIMITERS = b'()<>[]{}/%'

_HIGHTLIGHTEN = False


def algorithm_33(owner_pwd, user_pwd, rev, keylen):
    """Implementation of algorithm 3.3 of the PDF standard security handler,
    section 3.5.2 of the PDF 1.6 reference."""
    # steps 1 - 4
    key = algorithm_33_1(owner_pwd, rev, keylen)
    # 5. Pad or truncate the user password string as described in step 1 of
    # algorithm 3.2.
    user_pwd = (user_pwd + _encryption_padding)[:32]
    # 6. Encrypt the result of step 5, using an RC4 encryption function with
    # the encryption key obtained in step 4.
    val = rc4_encrypt(key, user_pwd)
    # 7. (Revision 3 or greater) Do the following 19 times: Take the output
    # from the previous invocation of the RC4 function and pass it as input to
    # a new invocation of the function; use an encryption key generated by
    # taking each byte of the encryption key obtained in step 4 and performing
    # an XOR operation between that byte and the single-byte value of the
    # iteration counter (from 1 to 19).
    if rev >= 3:
        for i in range(1, 20):
            new_key = ''
            for j in range(len(key)):
                new_key += chr(ord(key[j:j + 1]) ^ i)
            val = rc4_encrypt(new_key, val)
    # 8. Store the output from the final invocation of the RC4 as the value of
    # the /O entry in the encryption dictionary.
    return val


def algorithm_33_1(password, rev, keylen):
    """Steps 1-4 of algorithm 3.3"""
    # 1. Pad or truncate the owner password string as described in step 1 of
    # algorithm 3.2.  If there is no owner password, use the user password
    # instead.
    password = (password + _encryption_padding)[:32]
    # 2. Initialize the MD5 hash function and pass the result of step 1 as
    # input to this function.
    m = _md5(password)
    # 3. (Revision 3 or greater) Do the following 50 times: Take the output
    # from the previous MD5 hash and pass it as input into a new MD5 hash.
    md5_hash = m.digest()
    if rev >= 3:
        for i in range(50):
            md5_hash = _md5(md5_hash).digest()
    # 4. Create an RC4 encryption key using the first n bytes of the output
    # from the final MD5 hash, where n is always 5 for revision 2 but, for
    # revision 3 or greater, depends on the value of the encryption
    # dictionary's /Length entry.
    key = md5_hash[:keylen]
    return key


def algorithm_32(password, rev, keylen, owner_entry, p_entry, id1_entry, metadata_encrypt=True):
    """Implementation of algorithm 3.2 of the PDF standard security handler,
    section 3.5.2 of the PDF 1.6 reference."""
    # 1. Pad or truncate the password string to exactly 32 bytes.  If the
    # password string is more than 32 bytes long, use only its first 32 bytes;
    # if it is less than 32 bytes long, pad it by appending the required number
    # of additional bytes from the beginning of the padding string
    # (_encryption_padding).
    password = (password + _encryption_padding)[:32]
    # 2. Initialize the MD5 hash function and pass the result of step 1 as
    # input to this function.
    m = _md5(password)
    # 3. Pass the value of the encryption dictionary's /O entry to the MD5 hash
    # function.
    m.update(owner_entry)
    # 4. Treat the value of the /P entry as an unsigned 4-byte integer and pass
    # these bytes to the MD5 hash function, low-order byte first.
    p_entry = _s.pack('<i', p_entry)
    m.update(p_entry)
    # 5. Pass the first element of the file's file identifier array to the MD5
    # hash function.
    m.update(id1_entry)
    # 6. (Revision 3 or greater) If document metadata is not being encrypted,
    # pass 4 bytes with the value 0xFFFFFFFF to the MD5 hash function.
    if rev >= 3 and not metadata_encrypt:
        m.update(b'\xff\xff\xff\xff')
    # 7. Finish the hash.
    md5_hash = m.digest()
    # 8. (Revision 3 or greater) Do the following 50 times: Take the output
    # from the previous MD5 hash and pass the first n bytes of the output as
    # input into a new MD5 hash, where n is the number of bytes of the
    # encryption key as defined by the value of the encryption dictionary's
    # /Length entry.
    if rev >= 3:
        for i in range(50):
            md5_hash = _md5(md5_hash[:keylen]).digest()
    # 9. Set the encryption key to the first n bytes of the output from the
    # final MD5 hash, where n is always 5 for revision 2 but, for revision 3 or
    # greater, depends on the value of the encryption dictionary's /Length
    # entry.
    return md5_hash[:keylen]


def algorithm_34(password, owner_entry, p_entry, id1_entry):
    """Implementation of algorithm 3.4 of the PDF standard security handler,
    section 3.5.2 of the PDF 1.6 reference."""
    # 1. Create an encryption key based on the user password string, as
    # described in algorithm 3.2.
    key = algorithm_32(password, 2, 5, owner_entry, p_entry, id1_entry)
    # 2. Encrypt the 32-byte padding string shown in step 1 of algorithm 3.2,
    # using an RC4 encryption function with the encryption key from the
    # preceding step.
    u = rc4_encrypt(key, _encryption_padding)
    # 3. Store the result of step 2 as the value of the /U entry in the
    # encryption dictionary.
    return u, key


def algorithm_35(password, rev, keylen, owner_entry, p_entry, id1_entry, _metadata_encrypt):
    """Implementation of algorithm 3.4 of the PDF standard security handler,
    section 3.5.2 of the PDF 1.6 reference."""
    # 1. Create an encryption key based on the user password string, as
    # described in Algorithm 3.2.
    key = algorithm_32(password, rev, keylen, owner_entry, p_entry, id1_entry)
    # 2. Initialize the MD5 hash function and pass the 32-byte padding string
    # shown in step 1 of Algorithm 3.2 as input to this function. 
    m = _md5()
    m.update(bytes(_encryption_padding, ENCODING_UTF8))
    # 3. Pass the first element of the file's file identifier array (the value
    # of the ID entry in the document's trailer dictionary; see Table 3.13 on
    # page 73) to the hash function and finish the hash.  (See implementation
    # note 25 in Appendix H.) 
    m.update(id1_entry)
    md5_hash = m.digest()
    # 4. Encrypt the 16-byte result of the hash, using an RC4 encryption
    # function with the encryption key from step 1. 
    val = rc4_encrypt(key, md5_hash)
    # 5. Do the following 19 times: Take the output from the previous
    # invocation of the RC4 function and pass it as input to a new invocation
    # of the function; use an encryption key generated by taking each byte of
    # the original encryption key (obtained in step 2) and performing an XOR
    # operation between that byte and the single-byte value of the iteration
    # counter (from 1 to 19). 
    for _i in range(1, 20):
        new_key = ''
        for j in range(len(key)):
            new_key += chr(ord(key[j:j + 1]) ^ _i)
        val = rc4_encrypt(new_key, val)
    # 6. Append 16 bytes of arbitrary padding to the output from the final
    # invocation of the RC4 function and store the 32-byte result as the value
    # of the U entry in the encryption dictionary. 
    # (implementator note: I don't know what "arbitrary padding" is supposed to
    # mean, so I have used null bytes.  This seems to match a few other
    # people's implementations)
    return val + ('\x00' * 16), key


def encrypt(encrypt_key, pack1, pack2):
    key = encrypt_key + pack1 + pack2
    assert len(key) == (len(encrypt_key) + 5)
    md5_hash = _md5(key).digest()
    key = md5_hash[:min(16, len(encrypt_key) + 5)]
    return key


def debug(*_args):
    if not _HIGHTLIGHTEN:
        _super_print(*_args)


def stacktrace_debug():
    print('-' * 32, 'tracing', '-' * 32)
    prefix = '>' * 2
    trace_format = '{} [{:PATH} - {:LINE}] {}'
    path_width = 0
    line_width = 0
    lines = []
    for frame in _insp.stack()[1:]:
        info = _insp.getframeinfo(frame[0])
        dirname, basename = _os.path.split(info.filename)
        dirname = _os.path.basename(dirname)
        path = _os.path.join(dirname, basename)
        lines.append([path, info.lineno, info.function, info.code_context])
        path_width = len(path) if len(path) > path_width else path_width
        line_width = len(str(info.lineno)) if len(str(info.lineno)) > line_width else line_width
    trace_format = trace_format.replace('PATH', str(path_width))
    trace_format = trace_format.replace('LINE', str(line_width))
    for path, line, func, context in lines:
        print(trace_format.format(
            prefix, path, line, func,
        ))
        for code in context:
            if code.endswith('\n'):
                code = code[:-1]
            print('{} {}'.format(prefix, code))


def hightlight_debug(*_args):
    global _HIGHTLIGHTEN
    _HIGHTLIGHTEN = True
    print('>' * 32, 'hightlighted', '<' * 32)
    _super_print(*_args)


def _super_print(*args):
    info = _insp.getframeinfo(_insp.stack()[2][0])
    dirname, basename = _os.path.split(info.filename)
    dirname = _os.path.basename(dirname)
    print('[{}] {} [{}]'.format(_os.path.join(dirname, basename), info.function, info.lineno), *args)


def s2b(s: str):
    return bytes(s, ENCODING_UTF8)


def read_hex_bytes_from(stream):
    stream.read(1)
    txt = b''
    x = b''
    while True:
        tok = read_non_whitespace(stream)
        if tok == b'>':
            break
        x += tok
        if len(x) == 2:
            txt += s2b(chr(int(x, base=16)))
            x = b''
    if len(x) == 1:
        x += b'0'
    if len(x) == 2:
        txt += s2b(chr(int(x, base=16)))
    return txt


def read_bytes_from(stream):
    _tok = stream.read(1)
    parens = 1
    txt = b''
    while True:
        tok = stream.read(1)
        if tok in b'(':
            parens += 1
        elif tok in b')':
            parens -= 1
            if parens == 0:
                break
        elif tok in b'\\':
            tok = stream.read(1)
            if tok in b'n':
                tok = b'\n'
            elif tok in b'r':
                tok = b'\r'
            elif tok in b't':
                tok = b'\t'
            elif tok in b'b':
                tok = b'\b'
            elif tok in b'f':
                tok = b'\f'
            elif tok in b'()\\':
                pass
            elif tok.isdigit():
                # "The number ddd may consist of one, two, or three
                # octal digits; high-order overflow shall be ignored.
                # Three octal digits shall be used, with leading zeros
                # as needed, if the next character of the string is also
                # a digit." (PDF reference 7.3.4.2, p 16)
                for _i in range(2):
                    ntok = stream.read(1)
                    if ntok.isdigit():
                        tok += ntok
                    else:
                        break
                tok = s2b(chr(int(tok, base=8)))
            elif tok in b'\n\r':
                # This case is  hit when a backslash followed by a line
                # break occurs.  If it's a multi-char EOL, consume the
                # second character:
                tok = stream.read(1)
                if tok not in b'\n\r':
                    stream.seek(-1, _io.SEEK_CUR)
                # Then don't add anything to the actual string, since this
                # line break was escaped:
                tok = b''
            else:
                raise PdfReadError("Unexpected escaped string")
        txt += tok
    return txt


def read_until_whitespace(stream, maxchars=None):
    txt = b''
    while True:
        tok = stream.read(1)
        if tok.isspace() or not tok:
            break
        txt += tok
        if len(txt) == maxchars:
            break
    return txt


def read_non_whitespace(stream: _io.BufferedReader, seek_back: bool = False):
    tok = b' '
    while tok in b'\n\r\t ' and len(tok) > 0:
        tok = stream.read(1)
    if seek_back:
        stream.seek(-1, _io.SEEK_CUR)
    return tok


def seek_token(stream):
    return read_non_whitespace(stream, True)


def rc4_encrypt(key, plaintext):
    s = [i for i in range(256)]
    j = 0
    for i in range(256):
        j = (j + s[i] + ord(key[i % len(key)])) % 256
        s[i], s[j] = s[j], s[i]
    i, j = 0, 0
    retval = ""
    for x in range(len(plaintext)):
        i = (i + 1) % 256
        j = (j + s[i]) % 256
        s[i], s[j] = s[j], s[i]
        t = s[(s[i] + s[j]) % 256]
        retval += chr(ord(plaintext[x]) ^ t)
    return retval


def matrix_multiply(a, b):
    return [[sum([float(i) * float(j)
                  for i, j in zip(row, col)]
                 ) for col in zip(*b)]
            for row in a]


class PyPdfError(Exception):
    pass


class PdfReadError(PyPdfError):
    pass


class PageSizeNotDefinedError(PyPdfError):
    pass


def encode_pdf_doc_encoding(unicode_string):
    retval = ''
    for c in unicode_string:
        try:
            retval += chr(_PDF_DOC_ENCODING_REVERSED[c])
        except KeyError:
            raise UnicodeEncodeError("pdfdocencoding", c, -1, -1, "does not exist in translation table")
    return retval


def decode_pdf_doc_encoding(byte_array: bytes):
    retval = u''
    for b in byte_array:
        c = _PDF_DOC_ENCODING[b]
        if c == u'\u0000':
            raise UnicodeDecodeError("pdfdocencoding", bytes([b]), -1, -1, "does not exist in translation table")
        retval += c
    return retval


# ref: pdf1.8 spec section 3.5.2 algorithm 3.2
_encryption_padding = '\x28\xbf\x4e\x5e\x4e\x75\x8a\x41\x64\x00\x4e\x56' + \
                      '\xff\xfa\x01\x08\x2e\x2e\x00\xb6\xd0\x68\x3e\x80\x2f\x0c' + \
                      '\xa9\xfe\x64\x53\x69\x7a'

_PDF_DOC_ENCODING = (
    u'\u0000', u'\u0000', u'\u0000', u'\u0000', u'\u0000', u'\u0000', u'\u0000', u'\u0000',
    u'\u0000', u'\u0000', u'\u0000', u'\u0000', u'\u0000', u'\u0000', u'\u0000', u'\u0000',
    u'\u0000', u'\u0000', u'\u0000', u'\u0000', u'\u0000', u'\u0000', u'\u0000', u'\u0000',
    u'\u02d8', u'\u02c7', u'\u02c6', u'\u02d9', u'\u02dd', u'\u02db', u'\u02da', u'\u02dc',
    u'\u0020', u'\u0021', u'\u0022', u'\u0023', u'\u0024', u'\u0025', u'\u0026', u'\u0027',
    u'\u0028', u'\u0029', u'\u002a', u'\u002b', u'\u002c', u'\u002d', u'\u002e', u'\u002f',
    u'\u0030', u'\u0031', u'\u0032', u'\u0033', u'\u0034', u'\u0035', u'\u0036', u'\u0037',
    u'\u0038', u'\u0039', u'\u003a', u'\u003b', u'\u003c', u'\u003d', u'\u003e', u'\u003f',
    u'\u0040', u'\u0041', u'\u0042', u'\u0043', u'\u0044', u'\u0045', u'\u0046', u'\u0047',
    u'\u0048', u'\u0049', u'\u004a', u'\u004b', u'\u004c', u'\u004d', u'\u004e', u'\u004f',
    u'\u0050', u'\u0051', u'\u0052', u'\u0053', u'\u0054', u'\u0055', u'\u0056', u'\u0057',
    u'\u0058', u'\u0059', u'\u005a', u'\u005b', u'\u005c', u'\u005d', u'\u005e', u'\u005f',
    u'\u0060', u'\u0061', u'\u0062', u'\u0063', u'\u0064', u'\u0065', u'\u0066', u'\u0067',
    u'\u0068', u'\u0069', u'\u006a', u'\u006b', u'\u006c', u'\u006d', u'\u006e', u'\u006f',
    u'\u0070', u'\u0071', u'\u0072', u'\u0073', u'\u0074', u'\u0075', u'\u0076', u'\u0077',
    u'\u0078', u'\u0079', u'\u007a', u'\u007b', u'\u007c', u'\u007d', u'\u007e', u'\u0000',
    u'\u2022', u'\u2020', u'\u2021', u'\u2026', u'\u2014', u'\u2013', u'\u0192', u'\u2044',
    u'\u2039', u'\u203a', u'\u2212', u'\u2030', u'\u201e', u'\u201c', u'\u201d', u'\u2018',
    u'\u2019', u'\u201a', u'\u2122', u'\ufb01', u'\ufb02', u'\u0141', u'\u0152', u'\u0160',
    u'\u0178', u'\u017d', u'\u0131', u'\u0142', u'\u0153', u'\u0161', u'\u017e', u'\u0000',
    u'\u20ac', u'\u00a1', u'\u00a2', u'\u00a3', u'\u00a4', u'\u00a5', u'\u00a6', u'\u00a7',
    u'\u00a8', u'\u00a9', u'\u00aa', u'\u00ab', u'\u00ac', u'\u0000', u'\u00ae', u'\u00af',
    u'\u00b0', u'\u00b1', u'\u00b2', u'\u00b3', u'\u00b4', u'\u00b5', u'\u00b6', u'\u00b7',
    u'\u00b8', u'\u00b9', u'\u00ba', u'\u00bb', u'\u00bc', u'\u00bd', u'\u00be', u'\u00bf',
    u'\u00c0', u'\u00c1', u'\u00c2', u'\u00c3', u'\u00c4', u'\u00c5', u'\u00c6', u'\u00c7',
    u'\u00c8', u'\u00c9', u'\u00ca', u'\u00cb', u'\u00cc', u'\u00cd', u'\u00ce', u'\u00cf',
    u'\u00d0', u'\u00d1', u'\u00d2', u'\u00d3', u'\u00d4', u'\u00d5', u'\u00d6', u'\u00d7',
    u'\u00d8', u'\u00d9', u'\u00da', u'\u00db', u'\u00dc', u'\u00dd', u'\u00de', u'\u00df',
    u'\u00e0', u'\u00e1', u'\u00e2', u'\u00e3', u'\u00e4', u'\u00e5', u'\u00e6', u'\u00e7',
    u'\u00e8', u'\u00e9', u'\u00ea', u'\u00eb', u'\u00ec', u'\u00ed', u'\u00ee', u'\u00ef',
    u'\u00f0', u'\u00f1', u'\u00f2', u'\u00f3', u'\u00f4', u'\u00f5', u'\u00f6', u'\u00f7',
    u'\u00f8', u'\u00f9', u'\u00fa', u'\u00fb', u'\u00fc', u'\u00fd', u'\u00fe', u'\u00ff'
)

assert len(_PDF_DOC_ENCODING) == 256

_PDF_DOC_ENCODING_REVERSED = {}
for __idx in range(256):
    char = _PDF_DOC_ENCODING[__idx]
    if char == u"\u0000":
        continue
    assert char not in _PDF_DOC_ENCODING_REVERSED
    _PDF_DOC_ENCODING_REVERSED[char] = __idx
if __name__ == "__main__":
    # test RC4
    out = rc4_encrypt("Key", "Plaintext")
    print(repr(out))
    pt = rc4_encrypt("Key", out)
    print(repr(pt))
