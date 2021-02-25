# coding: utf-8
"""
A pure-Python PDF library with very minimal capabilities.  It was designed to
be able to split and merge PDF files by page, and that's about all it can do.
It may be a solid base for future PDF file work in Python.
"""
__author__ = "Mathieu Fenniak"
__author_email__ = "biziqe@mathieu.fenniak.net"

import math
import struct
from hashlib import md5
from io import StringIO

import pdf.filters
import pdf.utils as utils
from pdf.generic import *
from pdf.utils import read_non_whitespace, read_until_whitespace, ConvertFunctionsToVirtualList


##
# This class supports writing PDF files out, given pages produced by another
# class (typically {@link #PdfFileReader PdfFileReader}).
class PdfFileWriter(object):
    def __init__(self):
        self._ID = None
        self._encrypt = None
        self._encrypt_key = None
        self.stack = []

        self._header = "%PDF-1.3"
        self._objects = []  # array of indirect objects

        # The root of our page tree node.
        pages = DictionaryObject()
        pages.update({
            NameObject("/Type"): NameObject("/Pages"),
            NameObject("/Count"): NumberObject(0),
            NameObject("/Kids"): ArrayObject(),
        })
        self._pages = self._add_object(pages)

        # info object
        info = DictionaryObject()
        info.update({
            NameObject("/Producer"): create_string_object(u"Python PDF Library - http://pybrary.net/pyPdf/")
        })
        self._info = self._add_object(info)

        # root object
        root = DictionaryObject()
        root.update({
            NameObject("/Type"): NameObject("/Catalog"),
            NameObject("/Pages"): self._pages,
        })
        self._root = self._add_object(root)

    def _add_object(self, obj):
        self._objects.append(obj)
        return IndirectObject(len(self._objects), 0, self)

    def get_object(self, ido):
        if ido.pdf != self:
            raise ValueError("pdf must be self")
        return self._objects[ido.idnum - 1]

    ##
    # Common method for inserting or adding a page to this PDF file.
    #
    # @param page The page to add to the document.  This argument should be
    #             an instance of {@link #PageObject PageObject}.
    # @param action The function which will insert the page in the dictionnary.
    #               Takes: page list, page to add.
    def _add_page(self, page, action):
        assert page["/Type"] == "/Page"
        page[NameObject("/Parent")] = self._pages
        page = self._add_object(page)
        pages = self.get_object(self._pages)
        action(pages["/Kids"], page)
        pages[NameObject("/Count")] = NumberObject(pages["/Count"] + 1)

    ##
    # Adds a page to this PDF file.  The page is usually acquired from a
    # {@link #PdfFileReader PdfFileReader} instance.
    # <p>
    # Stability: Added in v1.0, will exist for all v1.x releases.
    #
    # @param page The page to add to the document.  This argument should be
    #             an instance of {@link #PageObject PageObject}.
    def add_page(self, page):
        self._add_page(page, list.append)

    ##
    # Insert a page in this PDF file.  The page is usually acquired from a
    # {@link #PdfFileReader PdfFileReader} instance.
    #
    # @param page The page to add to the document.  This argument should be
    #             an instance of {@link #PageObject PageObject}.
    # @param index Position at which the page will be inserted.
    def insert_page(self, page, index=0):
        self._add_page(page, lambda l, p: l.insert(index, p))

    ##
    # Retrieves a page by number from this PDF file.
    # @return Returns a {@link #PageObject PageObject} instance.
    def get_page(self, page_number):
        pages = self.get_object(self._pages)
        # XXX: crude hack
        return pages["/Kids"][page_number].get_object()

    ##
    # Return the number of pages.
    # @return The number of pages.
    def get_num_pages(self):
        pages = self.get_object(self._pages)
        return int(pages[NameObject("/Count")])

    ##
    # Append a blank page to this PDF file and returns it. If no page size
    # is specified, use the size of the last page; throw
    # PageSizeNotDefinedError if it doesn't exist.
    # @param width The width of the new page expressed in default user
    # space units.
    # @param height The height of the new page expressed in default user
    # space units.
    def add_blank_page(self, width=None, height=None):
        page = PageObject.create_blank_page(self, width, height)
        self.add_page(page)
        return page

    ##
    # Insert a blank page to this PDF file and returns it. If no page size
    # is specified, use the size of the page in the given index; throw
    # PageSizeNotDefinedError if it doesn't exist.
    # @param width  The width of the new page expressed in default user
    #               space units.
    # @param height The height of the new page expressed in default user
    #               space units.
    # @param index  Position to add the page.
    def insert_blank_page(self, width=None, height=None, index=0):
        if width is None or height is None and \
                (self.get_num_pages() - 1) >= index:
            oldpage = self.get_page(index)
            width = oldpage.mediaBox.get_width()
            height = oldpage.mediaBox.get_height()
        page = PageObject.create_blank_page(self, width, height)
        self.insert_page(page, index)
        return page

    ##
    # Encrypt this PDF file with the PDF Standard encryption handler.
    # @param user_pwd The "user password", which allows for opening and reading
    # the PDF file with the restrictions provided.
    # @param owner_pwd The "owner password", which allows for opening the PDF
    # files without any restrictions.  By default, the owner password is the
    # same as the user password.
    # @param use_128bit Boolean argument as to whether to use 128bit
    # encryption.  When false, 40bit encryption will be used.  By default, this
    # flag is on.
    def encrypt(self, user_pwd, owner_pwd=None, use_128bit=True):
        import time
        import random
        if owner_pwd is None:
            owner_pwd = user_pwd
        if use_128bit:
            v = 2
            rev = 3
            keylen = 128 / 8
        else:
            v = 1
            rev = 2
            keylen = 40 / 8
        # permit everything:
        p = -1
        o = ByteStringObject(_alg33(owner_pwd, user_pwd, rev, keylen))
        id_1 = md5(bytes(repr(time.time()), 'utf-8')).digest()
        id_2 = md5(bytes(repr(random.random()), 'utf-8')).digest()
        self._ID = ArrayObject((ByteStringObject(id_1), ByteStringObject(id_2)))
        if rev == 2:
            u, key = _alg34(user_pwd, o, p, id_1)
        else:
            assert rev == 3
            u, key = _alg35(user_pwd, rev, keylen, o, p, id_1, False)
        encrypt = DictionaryObject()
        encrypt[NameObject("/Filter")] = NameObject("/Standard")
        encrypt[NameObject("/V")] = NumberObject(v)
        if v == 2:
            encrypt[NameObject("/Length")] = NumberObject(keylen * 8)
        encrypt[NameObject("/R")] = NumberObject(rev)
        encrypt[NameObject("/O")] = ByteStringObject(o)
        encrypt[NameObject("/U")] = ByteStringObject(u)
        encrypt[NameObject("/P")] = NumberObject(p)
        self._encrypt = self._add_object(encrypt)
        self._encrypt_key = key

    ##
    # Writes the collection of pages added to this object out as a PDF file.
    # <p>
    # Stability: Added in v1.0, will exist for all v1.x releases.
    # @param stream An object to write the file to.  The object must support
    # the write method, and the tell method, similar to a file object.
    def write(self, stream):
        import struct

        external_reference_map = {}

        # PDF objects sometimes have circular references to their /Page objects
        # inside their object tree (for example, annotations).  Those will be
        # indirect references to objects that we've recreated in this PDF.  To
        # address this problem, PageObject's store their original object
        # reference number, and we add it to the external reference map before
        # we sweep for indirect references.  This forces self-page-referencing
        # trees to reference the correct new object location, rather than
        # copying in a new copy of the page object.
        for objIndex in range(len(self._objects)):
            obj = self._objects[objIndex]
            if isinstance(obj, PageObject) and obj.indirectRef is not None:
                data = obj.indirectRef
                if data.pdf not in external_reference_map:
                    external_reference_map[data.pdf] = {}
                if data.generation not in external_reference_map[data.pdf]:
                    external_reference_map[data.pdf][data.generation] = {}
                external_reference_map[data.pdf][data.generation][data.idnum] = IndirectObject(objIndex + 1, 0, self)

        self.stack = []
        self._sweep_indirect_references(external_reference_map, self._root)
        del self.stack

        # Begin writing:
        object_positions = []
        stream.write(self._header + "\n")
        for i in range(len(self._objects)):
            idnum = (i + 1)
            obj = self._objects[i]
            object_positions.append(stream.tell())
            stream.write(str(idnum) + " 0 obj\n")
            key = None
            if hasattr(self, "_encrypt") and idnum != self._encrypt.idnum:
                pack1 = struct.pack("<i", i + 1)[:3]
                pack2 = struct.pack("<i", 0)[:2]
                key = _encrypt(self._encrypt_key, pack1, pack2)
            obj.write_to_stream(stream, key)
            stream.write("\nendobj\n")

        # xref table
        xref_location = stream.tell()
        stream.write("xref\n")
        stream.write("0 %s\n" % (len(self._objects) + 1))
        stream.write("%010d %05d f \n" % (0, 65535))
        for offset in object_positions:
            stream.write("%010d %05d n \n" % (offset, 0))

        # trailer
        stream.write("trailer\n")
        trailer = DictionaryObject()
        trailer.update({
            NameObject("/Size"): NumberObject(len(self._objects) + 1),
            NameObject("/Root"): self._root,
            NameObject("/Info"): self._info,
        })
        if hasattr(self, "_ID"):
            trailer[NameObject("/ID")] = self._ID
        if hasattr(self, "_encrypt"):
            trailer[NameObject("/Encrypt")] = self._encrypt
        trailer.write_to_stream(stream, None)

        # eof
        stream.write("\nstartxref\n%s\n%%%%EOF\n" % xref_location)

    def _sweep_indirect_references(self, extern_map, data):
        if isinstance(data, DictionaryObject):
            for key, value in data.items():
                _origvalue = value
                value = self._sweep_indirect_references(extern_map, value)
                if isinstance(value, StreamObject):
                    # a dictionary value is a stream.  streams must be indirect
                    # objects, so we need to change this value.
                    value = self._add_object(value)
                data[key] = value
            return data
        elif isinstance(data, ArrayObject):
            for i in range(len(data)):
                value = self._sweep_indirect_references(extern_map, data[i])
                if isinstance(value, StreamObject):
                    # an array value is a stream.  streams must be indirect
                    # objects, so we need to change this value
                    value = self._add_object(value)
                data[i] = value
            return data
        elif isinstance(data, IndirectObject):
            # internal indirect references are fine
            if data.pdf == self:
                if data.idnum in self.stack:
                    return data
                else:
                    self.stack.append(data.idnum)
                    realdata = self.get_object(data)
                    self._sweep_indirect_references(extern_map, realdata)
                    self.stack.pop()
                    return data
            else:
                newobj = extern_map.get(data.pdf, {}).get(data.generation, {}).get(data.idnum, None)
                if newobj is None:
                    newobj = data.pdf.get_object(data)
                    self._objects.append(None)  # placeholder
                    idnum = len(self._objects)
                    newobj_ido = IndirectObject(idnum, 0, self)
                    if data.pdf not in extern_map:
                        extern_map[data.pdf] = {}
                    if data.generation not in extern_map[data.pdf]:
                        extern_map[data.pdf][data.generation] = {}
                    extern_map[data.pdf][data.generation][data.idnum] = newobj_ido
                    newobj = self._sweep_indirect_references(extern_map, newobj)
                    self._objects[idnum - 1] = newobj
                    return newobj_ido
                return newobj
        else:
            return data


##
# Initializes a PdfFileReader object.  This operation can take some time, as
# the PDF stream's cross-reference tables are read into memory.
# <p>
# Stability: Added in v1.0, will exist for all v1.x releases.
#
# @param stream An object that supports the standard read and seek methods
#               similar to a file object.
class PdfFileReader(object):
    def __init__(self, stream):
        self.xref = {}
        self.xref_objStm = {}
        self.trailer = None
        self._namedDests = None
        self.flattenedPages = None
        self.resolvedObjects = {}
        self.read(stream)
        self.stream = stream
        self._override_encryption = False

    ##
    # Retrieves the PDF file's document information dictionary, if it exists.
    # Note that some PDF files use metadata streams instead of docinfo
    # dictionaries, and these metadata streams will not be accessed by this
    # function.
    # <p>
    # Stability: Added in v1.6, will exist for all future v1.x releases.
    # @return Returns a {@link #DocumentInformation DocumentInformation}
    #         instance, or None if none exists.
    def get_document_info(self):
        if "/Info" not in self.trailer:
            return None
        obj = self.trailer['/Info']
        retval = DocumentInformation()
        retval.update(obj)
        return retval

    ##
    # Read-only property that accesses the {@link
    # #PdfFileReader.getDocumentInfo getDocumentInfo} function.
    # <p>
    # Stability: Added in v1.7, will exist for all future v1.x releases.
    documentInfo = property(lambda self: self.get_document_info(), None, None)

    ##
    # Retrieves XMP (Extensible Metadata Platform) data from the PDF document
    # root.
    # <p>
    # Stability: Added in v1.12, will exist for all future v1.x releases.
    # @return Returns a {@link #generic.XmpInformation XmlInformation}
    # instance that can be used to access XMP metadata from the document.
    # Can also return None if no metadata was found on the document root.
    def get_xmp_metadata(self):
        try:
            self._override_encryption = True
            return self.trailer["/Root"].get_xmp_metadata()
        finally:
            self._override_encryption = False

    ##
    # Read-only property that accesses the {@link #PdfFileReader.getXmpData
    # getXmpData} function.
    # <p>
    # Stability: Added in v1.12, will exist for all future v1.x releases.
    xmpMetadata = property(lambda self: self.get_xmp_metadata(), None, None)

    ##
    # Calculates the number of pages in this PDF file.
    # <p>
    # Stability: Added in v1.0, will exist for all v1.x releases.
    # @return Returns an integer.
    def get_num_pages(self):
        if self.flattenedPages is None:
            self._flatten()
        return len(self.flattenedPages)

    ##
    # Read-only property that accesses the {@link #PdfFileReader.getNumPages
    # getNumPages} function.
    # <p>
    # Stability: Added in v1.7, will exist for all future v1.x releases.
    numPages = property(lambda self: self.get_num_pages(), None, None)

    ##
    # Retrieves a page by number from this PDF file.
    # <p>
    # Stability: Added in v1.0, will exist for all v1.x releases.
    # @return Returns a {@link #PageObject PageObject} instance.
    def get_page(self, page_number):
        # ensure that we're not trying to access an encrypted PDF
        # assert not self.trailer.has_key("/Encrypt")
        if self.flattenedPages is None:
            self._flatten()
        return self.flattenedPages[page_number]

    ##
    # Read-only property that accesses the 
    # {@link #PdfFileReader.getNamedDestinations 
    # getNamedDestinations} function.
    # <p>
    # Stability: Added in v1.10, will exist for all future v1.x releases.
    namedDestinations = property(lambda self:
                                 self.get_named_destinations(), None, None)

    ##
    # Retrieves the named destinations present in the document.
    # <p>
    # Stability: Added in v1.10, will exist for all future v1.x releases.
    # @return Returns a dict which maps names to {@link #Destination
    # destinations}.
    def get_named_destinations(self, tree=None, retval=None):
        if retval is None:
            retval = {}
            catalog = self.trailer["/Root"]

            # get the name tree
            if "/Dests" in catalog:
                tree = catalog["/Dests"]
            elif "/Names" in catalog:
                names = catalog['/Names']
                if "/Dests" in names:
                    tree = names['/Dests']

        if tree is None:
            return retval

        if "/Kids" in tree:
            # recurse down the tree
            for kid in tree["/Kids"]:
                self.get_named_destinations(kid.get_object(), retval)

        if "/Names" in tree:
            names = tree["/Names"]
            for i in range(0, len(names), 2):
                key = names[i].get_object()
                val = names[i + 1].get_object()
                if isinstance(val, DictionaryObject) and '/D' in val:
                    val = val['/D']
                dest = self._build_destination(key, val)
                if dest is not None:
                    retval[key] = dest

        return retval

    ##
    # Read-only property that accesses the {@link #PdfFileReader.getOutlines
    # getOutlines} function.
    # <p>
    # Stability: Added in v1.10, will exist for all future v1.x releases.
    outlines = property(lambda self: self.get_outlines(), None, None)

    ##
    # Retrieves the document outline present in the document.
    # <p>
    # Stability: Added in v1.10, will exist for all future v1.x releases.
    # @return Returns a nested list of {@link #Destination destinations}.
    def get_outlines(self, node=None, outlines=None):
        if outlines is None:
            outlines = []
            catalog = self.trailer["/Root"]

            # get the outline dictionary and named destinations
            if "/Outlines" in catalog:
                lines = catalog["/Outlines"]
                if "/First" in lines:
                    node = lines["/First"]
            self._namedDests = self.get_named_destinations()

        if node is None:
            return outlines

        # see if there are any more outlines
        while 1:
            outline = self._build_outline(node)
            if outline:
                outlines.append(outline)

            # check for sub-outlines
            if "/First" in node:
                sub_outlines = []
                self.get_outlines(node["/First"], sub_outlines)
                if sub_outlines:
                    outlines.append(sub_outlines)

            if "/Next" not in node:
                break
            node = node["/Next"]

        return outlines

    @staticmethod
    def _build_destination(title, array):
        page, typ = array[0:2]
        array = array[2:]
        return Destination(title, page, typ, *array)

    def _build_outline(self, node):
        dest, title, outline = None, None, None

        if "/A" in node and "/Title" in node:
            # Action, section 8.5 (only type GoTo supported)
            title = node["/Title"]
            action = node["/A"]
            if action["/S"] == "/GoTo":
                dest = action["/D"]
        elif "/Dest" in node and "/Title" in node:
            # Destination, section 8.2.1
            title = node["/Title"]
            dest = node["/Dest"]

        # if destination found, then create outline
        if dest:
            if isinstance(dest, ArrayObject):
                outline = self._build_destination(title, dest)
            # FIXME elif dest in isinstance(dest, unicode) and self._namedDests:
            elif dest in isinstance(dest, str) and self._namedDests:
                outline = self._namedDests[dest]
                outline[NameObject("/Title")] = title
            else:
                raise pdf.utils.PdfReadError("Unexpected destination %r" % dest)
        return outline

    ##
    # Read-only property that emulates a list based upon the {@link
    # #PdfFileReader.getNumPages getNumPages} and {@link #PdfFileReader.getPage
    # getPage} functions.
    # <p>
    # Stability: Added in v1.7, and will exist for all future v1.x releases.
    pages = property(lambda self: ConvertFunctionsToVirtualList(self.get_num_pages, self.get_page),
                     None, None)

    def _flatten(self, pages=None, inherit=None, indirect_ref=None):
        inheritable_page_attributes = (
            NameObject("/Resources"), NameObject("/MediaBox"),
            NameObject("/CropBox"), NameObject("/Rotate")
        )
        if inherit is None:
            inherit = dict()
        if pages is None:
            self.flattenedPages = []
            catalog = self.trailer["/Root"].get_object()
            pages = catalog["/Pages"].get_object()
        t = pages["/Type"]
        if t == "/Pages":
            for attr in inheritable_page_attributes:
                if attr in pages:
                    inherit[attr] = pages[attr]
            for page in pages["/Kids"]:
                addt = {}
                if isinstance(page, IndirectObject):
                    addt["indirectRef"] = page
                self._flatten(page.get_object(), inherit, **addt)
        elif t == "/Page":
            for attr, value in inherit.items():
                # if the page has it's own value, it does not inherit the
                # parent's value:
                if attr not in pages:
                    pages[attr] = value
            page_obj = PageObject(self, indirect_ref)
            page_obj.update(pages)
            self.flattenedPages.append(page_obj)

    def get_object(self, indirect_reference):
        retval = self.resolvedObjects.get(indirect_reference.generation, {}).get(indirect_reference.idnum, None)
        if retval is not None:
            return retval
        if indirect_reference.generation == 0 and indirect_reference.idnum in self.xref_objStm:
            # indirect reference to object in object stream
            # read the entire object stream into memory
            stmnum, idx = self.xref_objStm[indirect_reference.idnum]
            obj_stm = IndirectObject(stmnum, 0, self).get_object()
            assert obj_stm['/Type'] == '/ObjStm'
            assert idx < obj_stm['/N']
            stream_data = StringIO(obj_stm.get_data())
            for i in range(obj_stm['/N']):
                objnum = NumberObject.read_from_stream(stream_data)
                read_non_whitespace(stream_data)
                stream_data.seek(-1, 1)
                offset = NumberObject.read_from_stream(stream_data)
                read_non_whitespace(stream_data)
                stream_data.seek(-1, 1)
                t = stream_data.tell()
                stream_data.seek(obj_stm['/First'] + offset, 0)
                obj = read_object(stream_data, self)
                self.resolvedObjects[0][objnum] = obj
                stream_data.seek(t, 0)
            return self.resolvedObjects[0][indirect_reference.idnum]
        start = self.xref[indirect_reference.generation][indirect_reference.idnum]
        self.stream.seek(start, 0)
        idnum, generation = self.read_object_header(self.stream)
        assert idnum == indirect_reference.idnum
        assert generation == indirect_reference.generation
        retval = read_object(self.stream, self)

        # override encryption is used for the /Encrypt dictionary
        if not self._override_encryption and self.isEncrypted:
            # if we don't have the encryption key:
            if not hasattr(self, '_decryption_key'):
                raise Exception("file has not been decrypted")
            # otherwise, decrypt here...
            import struct
            pack1 = struct.pack("<i", indirect_reference.idnum)[:3]
            pack2 = struct.pack("<i", indirect_reference.generation)[:2]
            key = _encrypt(self._decryption_key, pack1, pack2)
            retval = self._decrypt_object(retval, key)

        self.cache_indirect_object(generation, idnum, retval)
        return retval

    def _decrypt_object(self, obj, key):
        if isinstance(obj, ByteStringObject) or isinstance(obj, TextStringObject):
            obj = create_string_object(utils.rc4_encrypt(key, obj.original_bytes))
        elif isinstance(obj, StreamObject):
            obj.set_data(utils.rc4_encrypt(key, obj.get_data()))
        elif isinstance(obj, DictionaryObject):
            for dictkey, value in obj.items():
                obj[dictkey] = self._decrypt_object(value, key)
        elif isinstance(obj, ArrayObject):
            for i in range(len(obj)):
                obj[i] = self._decrypt_object(obj[i], key)
        return obj

    @staticmethod
    def read_object_header(stream):
        # Should never be necessary to read out whitespace, since the
        # cross-reference table should put us in the right spot to read the
        # object header.  In reality... some files have stupid cross reference
        # tables that are off by whitespace bytes.
        read_non_whitespace(stream)
        stream.seek(-1, 1)
        idnum = read_until_whitespace(stream)
        generation = read_until_whitespace(stream)
        _obj = stream.read(3)
        read_non_whitespace(stream)
        stream.seek(-1, 1)
        return int(idnum), int(generation)

    def cache_indirect_object(self, generation, idnum, obj):
        if generation not in self.resolvedObjects:
            self.resolvedObjects[generation] = {}
        self.resolvedObjects[generation][idnum] = obj

    def read(self, stream):
        # start at the end:
        stream.seek(-1, 2)
        line = ''
        while not line:
            line = self.read_next_end_line(stream)
        if line[:5] != "%%EOF":
            raise utils.PdfReadError("EOF marker not found")

        # find startxref entry - the location of the xref table
        line = self.read_next_end_line(stream)
        startxref = int(line)
        line = self.read_next_end_line(stream)
        if line[:9] != "startxref":
            raise utils.PdfReadError("startxref not found")

        # read all cross reference tables and their trailers
        self.xref = {}
        self.xref_objStm = {}
        self.trailer = DictionaryObject()
        while 1:
            # load the xref table
            stream.seek(startxref, 0)
            x = stream.read(1)
            if x == "x":
                # standard cross-reference table
                ref = stream.read(4)
                if ref[:3] != "ref":
                    raise utils.PdfReadError("xref table read error")
                read_non_whitespace(stream)
                stream.seek(-1, 1)
                while 1:
                    num = read_object(stream, self)
                    read_non_whitespace(stream)
                    stream.seek(-1, 1)
                    size = read_object(stream, self)
                    read_non_whitespace(stream)
                    stream.seek(-1, 1)
                    cnt = 0
                    while cnt < size:
                        line = stream.read(20)
                        # It's very clear in section 3.4.3 of the PDF spec
                        # that all cross-reference table lines are a fixed
                        # 20 bytes.  However... some malformed PDF files
                        # use a single character EOL without a preceeding
                        # space.  Detect that case, and seek the stream
                        # back one character.  (0-9 means we've bled into
                        # the next xref entry, t means we've bled into the
                        # text "trailer"):
                        if line[-1] in "0123456789t":
                            stream.seek(-1, 1)
                        offset, generation = line[:16].split(" ")
                        offset, generation = int(offset), int(generation)
                        if generation not in self.xref:
                            self.xref[generation] = {}
                        if num in self.xref[generation]:
                            # It really seems like we should allow the last
                            # xref table in the file to override previous
                            # ones. Since we read the file backwards, assume
                            # any existing key is already set correctly.
                            pass
                        else:
                            self.xref[generation][num] = offset
                        cnt += 1
                        num += 1
                    read_non_whitespace(stream)
                    stream.seek(-1, 1)
                    trailertag = stream.read(7)
                    if trailertag != "trailer":
                        # more xrefs!
                        stream.seek(-7, 1)
                    else:
                        break
                read_non_whitespace(stream)
                stream.seek(-1, 1)
                new_trailer = read_object(stream, self)
                for key, value in new_trailer.items():
                    if key not in self.trailer:
                        self.trailer[key] = value
                if "/Prev" in new_trailer:
                    startxref = new_trailer["/Prev"]
                else:
                    break
            elif x.isdigit():
                # PDF 1.5+ Cross-Reference Stream
                stream.seek(-1, 1)
                idnum, generation = self.read_object_header(stream)
                xrefstream = read_object(stream, self)
                assert xrefstream["/Type"] == "/XRef"
                self.cache_indirect_object(generation, idnum, xrefstream)
                stream_data = StringIO(xrefstream.get_data())
                idx_pairs = xrefstream.get("/Index", [0, xrefstream.get("/Size")])
                entry_sizes = xrefstream.get("/W")
                for num, size in self._pairs(idx_pairs):
                    cnt = 0
                    xref_type = None
                    byte_offset = None
                    objstr_num = None
                    obstr_idx = None
                    while cnt < size:
                        for i in range(len(entry_sizes)):
                            d = stream_data.read(entry_sizes[i])
                            di = convert_to_int(d, entry_sizes[i])
                            if i == 0:
                                xref_type = di
                            elif i == 1:
                                if xref_type == 0:
                                    _next_free_object = di
                                elif xref_type == 1:
                                    byte_offset = di
                                elif xref_type == 2:
                                    objstr_num = di
                            elif i == 2:
                                if xref_type == 0:
                                    _next_generation = di
                                elif xref_type == 1:
                                    generation = di
                                elif xref_type == 2:
                                    obstr_idx = di
                        if xref_type == 0:
                            pass
                        elif xref_type == 1:
                            if generation not in self.xref:
                                self.xref[generation] = {}
                            if num not in self.xref[generation]:
                                self.xref[generation][num] = byte_offset
                        elif xref_type == 2:
                            if num not in self.xref_objStm:
                                self.xref_objStm[num] = [objstr_num, obstr_idx]
                        cnt += 1
                        num += 1
                trailer_keys = "/Root", "/Encrypt", "/Info", "/ID"
                for key in trailer_keys:
                    if key in xrefstream and key not in self.trailer:
                        self.trailer[NameObject(key)] = xrefstream.raw_get(key)
                if "/Prev" in xrefstream:
                    startxref = xrefstream["/Prev"]
                else:
                    break
            else:
                # bad xref character at startxref.  Let's see if we can find
                # the xref table nearby, as we've observed this error with an
                # off-by-one before.
                stream.seek(-11, 1)
                tmp = stream.read(20)
                xref_loc = tmp.find("xref")
                if xref_loc != -1:
                    startxref -= (10 - xref_loc)
                    continue
                else:
                    # no xref table found at specified location
                    assert False

    @staticmethod
    def _pairs(array):
        i = 0
        while True:
            yield array[i], array[i + 1]
            i += 2
            if (i + 1) >= len(array):
                break

    @staticmethod
    def read_next_end_line(stream):
        line = ""
        while True:
            x = stream.read(1)
            stream.seek(-2, 1)
            if x == '\n' or x == '\r':
                while x == '\n' or x == '\r':
                    x = stream.read(1)
                    stream.seek(-2, 1)
                stream.seek(1, 1)
                break
            else:
                line = x + line
        return line

    ##
    # When using an encrypted / secured PDF file with the PDF Standard
    # encryption handler, this function will allow the file to be decrypted.
    # It checks the given password against the document's user password and
    # owner password, and then stores the resulting decryption key if either
    # password is correct.
    # <p>
    # It does not matter which password was matched.  Both passwords provide
    # the correct decryption key that will allow the document to be used with
    # this library.
    # <p>
    # Stability: Added in v1.8, will exist for all future v1.x releases.
    #
    # @return 0 if the password failed, 1 if the password matched the user
    # password, and 2 if the password matched the owner password.
    #
    # @exception NotImplementedError Document uses an unsupported encryption
    # method.
    def decrypt(self, password):
        self._override_encryption = True
        try:
            return self._decrypt(password)
        finally:
            self._override_encryption = False

    def _decrypt(self, password):
        encrypt = self.trailer['/Encrypt'].get_object()
        if encrypt['/Filter'] != '/Standard':
            raise NotImplementedError("only Standard PDF encryption handler is available")
        if not (encrypt['/V'] in (1, 2)):
            raise NotImplementedError("only algorithm code 1 and 2 are supported")
        user_password, key = self._authenticate_user_password(password)
        if user_password:
            self._decryption_key = key
            return 1
        else:
            rev = encrypt['/R'].get_object()
            if rev == 2:
                keylen = 5
            else:
                keylen = encrypt['/Length'].get_object() / 8
            key = _alg33_1(password, rev, keylen)
            real_o = encrypt["/O"].get_object()
            if rev == 2:
                userpass = utils.rc4_encrypt(key, real_o)
            else:
                val = real_o
                for i in range(19, -1, -1):
                    new_key = ''
                    for j in range(len(key)):
                        new_key += chr(ord(key[j:j + 1]) ^ i)
                    val = utils.rc4_encrypt(new_key, val)
                userpass = val
            owner_password, key = self._authenticate_user_password(userpass)
            if owner_password:
                self._decryption_key = key
                return 2
        return 0

    def _authenticate_user_password(self, password):
        encrypt = self.trailer['/Encrypt'].get_object()
        rev = encrypt['/R'].get_object()
        owner_entry = encrypt['/O'].get_object().original_bytes
        p_entry = encrypt['/P'].get_object()
        id_entry = self.trailer['/ID'].get_object()
        id1_entry = id_entry[0].get_object()
        u = None
        key = None
        if rev == 2:
            u, key = _alg34(password, owner_entry, p_entry, id1_entry)
        elif rev >= 3:
            u, key = _alg35(password, rev,
                            encrypt["/Length"].get_object() / 8, owner_entry,
                            p_entry, id1_entry,
                            encrypt.get("/EncryptMetadata", BooleanObject(False)).get_object())
        real_u = encrypt['/U'].get_object().original_bytes
        return u == real_u, key

    def get_is_encrypted(self):
        return "/Encrypt" in self.trailer

    ##
    # Read-only boolean property showing whether this PDF file is encrypted.
    # Note that this property, if true, will remain true even after the {@link
    # #PdfFileReader.decrypt decrypt} function is called.
    isEncrypted = property(lambda self: self.get_is_encrypted(), None, None)


def get_rectangle(self, name, defaults):
    retval = self.get(name)
    if isinstance(retval, RectangleObject):
        return retval
    if retval is None:
        for d in defaults:
            retval = self.get(d)
            if retval is not None:
                break
    if isinstance(retval, IndirectObject):
        retval = self.pdf.get_object(retval)
    retval = RectangleObject(retval)
    set_rectangle(self, name, retval)
    return retval


def set_rectangle(self, name, value):
    if not isinstance(name, NameObject):
        name = NameObject(name)
    self[name] = value


def delete_rectangle(self, name):
    del self[name]


def create_rectangle_accessor(name, fallback):
    return \
        property(
            lambda self: get_rectangle(self, name, fallback),
            lambda self, value: set_rectangle(self, name, value),
            lambda self: delete_rectangle(self, name)
        )


##
# This class represents a single page within a PDF file.  Typically this object
# will be created by accessing the {@link #PdfFileReader.getPage getPage}
# function of the {@link #PdfFileReader PdfFileReader} class, but it is
# also possible to create an empty page with the createBlankPage static
# method.
# @param pdf PDF file the page belongs to (optional, defaults to None).
class PageObject(DictionaryObject):
    def __init__(self, _pdf=None, indirect_ref=None):
        DictionaryObject.__init__(self)
        self.pdf = _pdf
        # Stores the original indirect reference to this object in its source PDF
        self.indirectRef = indirect_ref

    ##
    # Returns a new blank page.
    # If width or height is None, try to get the page size from the
    # last page of pdf. If pdf is None or contains no page, a
    # PageSizeNotDefinedError is raised.
    # @param pdf    PDF file the page belongs to
    # @param width  The width of the new page expressed in default user
    #               space units.
    # @param height The height of the new page expressed in default user
    #               space units.
    def create_blank_page(_pdf=None, width=None, height=None):
        page = PageObject(pdf)

        # Creates a new page (cf PDF Reference  7.7.3.3)
        page.__setitem__(NameObject('/Type'), NameObject('/Page'))
        page.__setitem__(NameObject('/Parent'), NullObject())
        page.__setitem__(NameObject('/Resources'), DictionaryObject())
        if width is None or height is None:
            if _pdf is not None and _pdf.get_num_pages() > 0:
                lastpage = _pdf.get_page(_pdf.get_num_pages() - 1)
                width = lastpage.mediaBox.get_width()
                height = lastpage.mediaBox.get_height()
            else:
                raise utils.PageSizeNotDefinedError()
        page.__setitem__(NameObject('/MediaBox'),
                         RectangleObject([0, 0, width, height]))

        return page

    create_blank_page = staticmethod(create_blank_page)

    ##
    # Rotates a page clockwise by increments of 90 degrees.
    # <p>
    # Stability: Added in v1.1, will exist for all future v1.x releases.
    # @param angle Angle to rotate the page.  Must be an increment of 90 deg.
    def rotate_clockwise(self, angle):
        assert angle % 90 == 0
        self._rotate(angle)
        return self

    ##
    # Rotates a page counter-clockwise by increments of 90 degrees.
    # <p>
    # Stability: Added in v1.1, will exist for all future v1.x releases.
    # @param angle Angle to rotate the page.  Must be an increment of 90 deg.
    def rotate_counter_clockwise(self, angle):
        assert angle % 90 == 0
        self._rotate(-angle)
        return self

    def _rotate(self, angle):
        current_angle = self.get("/Rotate", 0)
        self[NameObject("/Rotate")] = NumberObject(current_angle + angle)

    def _merge_resources(res1, res2, resource):
        new_res = DictionaryObject()
        new_res.update(res1.get(resource, DictionaryObject()).get_object())
        page2_res = res2.get(resource, DictionaryObject()).get_object()
        rename_res = {}
        for key in page2_res.keys():
            if key in new_res and new_res[key] != page2_res[key]:
                newname = NameObject(key + "renamed")
                rename_res[key] = newname
                new_res[newname] = page2_res[key]
            elif key not in new_res:
                new_res[key] = page2_res.raw_get(key)
        return new_res, rename_res

    _merge_resources = staticmethod(_merge_resources)

    def _content_stream_rename(stream, rename, _pdf):
        if not rename:
            return stream
        stream = ContentStream(stream, _pdf)
        for operands, operator in stream.operations:
            for i in range(len(operands)):
                op = operands[i]
                if isinstance(op, NameObject):
                    operands[i] = rename.get(op, op)
        return stream

    _content_stream_rename = staticmethod(_content_stream_rename)

    def _push_pop_gs(contents, _pdf):
        # adds a graphics state "push" and "pop" to the beginning and end
        # of a content stream.  This isolates it from changes such as 
        # transformation matricies.
        stream = ContentStream(contents, _pdf)
        stream.operations.insert(0, [[], "q"])
        stream.operations.append([[], "Q"])
        return stream

    _push_pop_gs = staticmethod(_push_pop_gs)

    def _add_transformation_matrix(contents, _pdf, ctm):
        # adds transformation matrix at the beginning of the given
        # contents stream.
        a, b, c, d, e, f = ctm
        contents = ContentStream(contents, _pdf)
        contents.operations.insert(0, [[FloatObject(a), FloatObject(b),
                                        FloatObject(c), FloatObject(d), FloatObject(e),
                                        FloatObject(f)], " cm"])
        return contents

    _add_transformation_matrix = staticmethod(_add_transformation_matrix)

    ##
    # Returns the /Contents object, or None if it doesn't exist.
    # /Contents is optionnal, as described in PDF Reference  7.7.3.3
    def get_contents(self):
        if "/Contents" in self:
            return self["/Contents"].get_object()
        else:
            return None

    ##
    # Merges the content streams of two pages into one.  Resource references
    # (i.e. fonts) are maintained from both pages.  The mediabox/cropbox/etc
    # of this page are not altered.  The parameter page's content stream will
    # be added to the end of this page's content stream, meaning that it will
    # be drawn after, or "on top" of this page.
    # <p>
    # Stability: Added in v1.4, will exist for all future 1.x releases.
    # @param page2 An instance of {@link #PageObject PageObject} to be merged
    #              into this one.
    def merge_page(self, page2):
        self._merge_page(page2)

    ##
    # Actually merges the content streams of two pages into one. Resource
    # references (i.e. fonts) are maintained from both pages. The
    # mediabox/cropbox/etc of this page are not altered. The parameter page's
    # content stream will be added to the end of this page's content stream,
    # meaning that it will be drawn after, or "on top" of this page.
    #
    # @param page2 An instance of {@link #PageObject PageObject} to be merged
    #              into this one.
    # @param page2transformation A fuction which applies a transformation to
    #                            the content stream of page2. Takes: page2
    #                            contents stream. Must return: new contents
    #                            stream. If omitted, the content stream will
    #                            not be modified.
    def _merge_page(self, page2, page2transformation=None):
        # First we work on merging the resource dictionaries.  This allows us
        # to find out what symbols in the content streams we might need to
        # rename.

        new_resources = DictionaryObject()
        rename = {}
        original_resources = self["/Resources"].get_object()
        page2_resources = page2["/Resources"].get_object()

        for res in "/ExtGState", "/Font", "/XObject", "/ColorSpace", "/Pattern", "/Shading", "/Properties":
            new, newrename = PageObject._merge_resources(original_resources, page2_resources, res)
            if new:
                new_resources[NameObject(res)] = new
                rename.update(newrename)

        # Combine /ProcSet sets.
        new_resources[NameObject("/ProcSet")] = ArrayObject(
            frozenset(original_resources.get("/ProcSet", ArrayObject()).get_object()).union(
                frozenset(page2_resources.get("/ProcSet", ArrayObject()).get_object())
            )
        )

        new_content_array = ArrayObject()

        original_content = self.get_contents()
        if original_content is not None:
            new_content_array.append(PageObject._push_pop_gs(
                original_content, self.pdf))

        page2_content = page2.get_contents()
        if page2_content is not None:
            if page2transformation is not None:
                page2_content = page2transformation(page2_content)
            page2_content = PageObject._content_stream_rename(
                page2_content, rename, self.pdf)
            page2_content = PageObject._push_pop_gs(page2_content, self.pdf)
            new_content_array.append(page2_content)

        self[NameObject('/Contents')] = ContentStream(new_content_array, self.pdf)
        self[NameObject('/Resources')] = new_resources

    ##
    # This is similar to mergePage, but a transformation matrix is
    # applied to the merged stream.
    #
    # @param page2 An instance of {@link #PageObject PageObject} to be merged.
    # @param ctm   A 6 elements tuple containing the operands of the
    #              transformation matrix
    def merge_transformed_page(self, page2, ctm):
        self._merge_page(page2, lambda page2_content: PageObject._add_transformation_matrix(
            page2_content, page2.pdf, ctm
        ))

    ##
    # This is similar to mergePage, but the stream to be merged is scaled
    # by appling a transformation matrix.
    #
    # @param page2 An instance of {@link #PageObject PageObject} to be merged.
    # @param factor The scaling factor
    def merge_scaled_page(self, page2, factor):
        # CTM to scale : [ sx 0 0 sy 0 0 ]
        return self.merge_transformed_page(page2, [factor, 0,
                                                   0, factor,
                                                   0, 0])

    ##
    # This is similar to mergePage, but the stream to be merged is rotated
    # by appling a transformation matrix.
    #
    # @param page2 An instance of {@link #PageObject PageObject} to be merged.
    # @param rotation The angle of the rotation, in degrees
    def merge_rotated_page(self, page2, rotation):
        rotation = math.radians(rotation)
        return self.merge_transformed_page(page2,
                                           [math.cos(rotation), math.sin(rotation),
                                            -math.sin(rotation), math.cos(rotation),
                                            0, 0])

    ##
    # This is similar to mergePage, but the stream to be merged is translated
    # by appling a transformation matrix.
    #
    # @param page2 An instance of {@link #PageObject PageObject} to be merged.
    # @param tx    The translation on X axis
    # @param tx    The translation on Y axis
    def merge_translated_page(self, page2, tx, ty):
        return self.merge_transformed_page(page2, [1, 0,
                                                   0, 1,
                                                   tx, ty])

    ##
    # This is similar to mergePage, but the stream to be merged is rotated
    # and scaled by appling a transformation matrix.
    #
    # @param page2 An instance of {@link #PageObject PageObject} to be merged.
    # @param rotation The angle of the rotation, in degrees
    # @param factor The scaling factor
    def merge_rotated_scaled_page(self, page2, rotation, scale):
        ctm = _create_rotation_scaling_matrix(rotation, scale)

        return self.merge_transformed_page(page2,
                                           [ctm[0][0], ctm[0][1],
                                            ctm[1][0], ctm[1][1],
                                            ctm[2][0], ctm[2][1]])

    ##
    # This is similar to mergePage, but the stream to be merged is translated
    # and scaled by appling a transformation matrix.
    #
    # @param page2 An instance of {@link #PageObject PageObject} to be merged.
    # @param scale The scaling factor
    # @param tx    The translation on X axis
    # @param tx    The translation on Y axis
    def merge_scaled_translated_page(self, page2, scale, tx, ty):
        scaling = [[scale, 0, 0],
                   [0, scale, 0],
                   [0, 0, 1]]
        return self._translate_and_merge(scaling, tx, ty, page2)

    ##
    # This is similar to mergePage, but the stream to be merged is translated,
    # rotated and scaled by appling a transformation matrix.
    #
    # @param page2 An instance of {@link #PageObject PageObject} to be merged.
    # @param tx    The translation on X axis
    # @param ty    The translation on Y axis
    # @param rotation The angle of the rotation, in degrees
    # @param scale The scaling factor
    def merge_rotated_scaled_translated_page(self, page2, rotation, scale, tx, ty):
        ctm = _create_rotation_scaling_matrix(rotation, scale)
        return self._translate_and_merge(ctm, tx, ty, page2)

    def _translate_and_merge(self, ctm, tx, ty, page2):
        translation = [[1, 0, 0],
                       [0, 1, 0],
                       [tx, ty, 1]]
        ctm = utils.matrix_multiply(ctm, translation)

        return self.merge_transformed_page(page2, [ctm[0][0], ctm[0][1],
                                                   ctm[1][0], ctm[1][1],
                                                   ctm[2][0], ctm[2][1]])

    ##
    # Applys a transformation matrix the page.
    #
    # @param ctm   A 6 elements tuple containing the operands of the
    #              transformation matrix
    def add_transformation(self, ctm):
        original_content = self.get_contents()
        if original_content is not None:
            new_content = PageObject._add_transformation_matrix(
                original_content, self.pdf, ctm)
            new_content = PageObject._push_pop_gs(new_content, self.pdf)
            self[NameObject('/Contents')] = new_content

    ##
    # Scales a page by the given factors by appling a transformation
    # matrix to its content and updating the page size.
    #
    # @param sx The scaling factor on horizontal axis
    # @param sy The scaling factor on vertical axis
    def scale(self, sx, sy):
        self.add_transformation([sx, 0,
                                 0, sy,
                                 0, 0])
        self.mediaBox = RectangleObject([
            float(self.mediaBox.get_lower_left_x()) * sx,
            float(self.mediaBox.get_lower_left_y()) * sy,
            float(self.mediaBox.get_upper_right_x()) * sx,
            float(self.mediaBox.get_upper_right_y()) * sy])

    ##
    # Scales a page by the given factor by appling a transformation
    # matrix to its content and updating the page size.
    #
    # @param factor The scaling factor
    def scale_by(self, factor):
        self.scale(factor, factor)

    ##
    # Scales a page to the specified dimentions by appling a
    # transformation matrix to its content and updating the page size.
    #
    # @param width The new width
    # @param height The new heigth
    def scale_to(self, width, height):
        sx = width / (self.mediaBox.get_upper_right_x() -
                      self.mediaBox.get_lower_left_x())
        sy = height / (self.mediaBox.get_upper_right_y() -
                       self.mediaBox.get_lower_left_x())
        self.scale(sx, sy)

    ##
    # Compresses the size of this page by joining all content streams and
    # applying a FlateDecode filter.
    # <p>
    # Stability: Added in v1.6, will exist for all future v1.x releases.
    # However, it is possible that this function will perform no action if
    # content stream compression becomes "automatic" for some reason.
    def compress_content_streams(self):
        content = self.get_contents()
        if content is not None:
            if not isinstance(content, ContentStream):
                content = ContentStream(content, self.pdf)
            self[NameObject("/Contents")] = content.flate_encode()

    ##
    # Locate all text drawing commands, in the order they are provided in the
    # content stream, and extract the text.  This works well for some PDF
    # files, but poorly for others, depending on the generator used.  This will
    # be refined in the future.  Do not rely on the order of text coming out of
    # this function, as it will change if this function is made more
    # sophisticated.
    # <p>
    # Stability: Added in v1.7, will exist for all future v1.x releases.  May
    # be overhauled to provide more ordered text in the future.
    # @return a unicode string object
    def extract_text(self):
        text = u""
        content = self["/Contents"].get_object()
        if not isinstance(content, ContentStream):
            content = ContentStream(content, self.pdf)
        # Note: we check all strings are TextStringObjects.  ByteStringObjects
        # are strings where the byte->string encoding was unknown, so adding
        # them to the text here would be gibberish.
        for operands, operator in content.operations:
            if operator == "Tj":
                _text = operands[0]
                if isinstance(_text, TextStringObject):
                    text += _text
            elif operator == "T*":
                text += "\n"
            elif operator == "'":
                text += "\n"
                _text = operands[0]
                if isinstance(_text, TextStringObject):
                    text += operands[0]
            elif operator == '"':
                _text = operands[2]
                if isinstance(_text, TextStringObject):
                    text += "\n"
                    text += _text
            elif operator == "TJ":
                for i in operands[0]:
                    if isinstance(i, TextStringObject):
                        text += i
        return text

    ##
    # A rectangle (RectangleObject), expressed in default user space units,
    # defining the boundaries of the physical medium on which the page is
    # intended to be displayed or printed.
    # <p>
    # Stability: Added in v1.4, will exist for all future v1.x releases.
    mediaBox = create_rectangle_accessor("/MediaBox", ())

    ##
    # A rectangle (RectangleObject), expressed in default user space units,
    # defining the visible region of default user space.  When the page is
    # displayed or printed, its contents are to be clipped (cropped) to this
    # rectangle and then imposed on the output medium in some
    # implementation-defined manner.  Default value: same as MediaBox.
    # <p>
    # Stability: Added in v1.4, will exist for all future v1.x releases.
    cropBox = create_rectangle_accessor("/CropBox", ("/MediaBox",))

    ##
    # A rectangle (RectangleObject), expressed in default user space units,
    # defining the region to which the contents of the page should be clipped
    # when output in a production enviroment.
    # <p>
    # Stability: Added in v1.4, will exist for all future v1.x releases.
    bleedBox = create_rectangle_accessor("/BleedBox", ("/CropBox", "/MediaBox"))

    ##
    # A rectangle (RectangleObject), expressed in default user space units,
    # defining the intended dimensions of the finished page after trimming.
    # <p>
    # Stability: Added in v1.4, will exist for all future v1.x releases.
    trimBox = create_rectangle_accessor("/TrimBox", ("/CropBox", "/MediaBox"))

    ##
    # A rectangle (RectangleObject), expressed in default user space units,
    # defining the extent of the page's meaningful content as intended by the
    # page's creator.
    # <p>
    # Stability: Added in v1.4, will exist for all future v1.x releases.
    artBox = create_rectangle_accessor("/ArtBox", ("/CropBox", "/MediaBox"))


class ContentStream(DecodedStreamObject):
    def __init__(self, stream, _pdf, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.pdf = _pdf
        self.operations = []
        # stream may be a StreamObject or an ArrayObject containing
        # multiple StreamObjects to be cat'd together.
        stream = stream.get_object()
        if isinstance(stream, ArrayObject):
            data = ""
            for s in stream:
                data += s.get_object().get_data()
            stream = StringIO(data)
        else:
            stream = StringIO(stream.get_data())
        self.__parse_content_stream(stream)

    def __parse_content_stream(self, stream):
        # file("f:\\tmp.txt", "w").write(stream.read())
        stream.seek(0, 0)
        operands = []
        while True:
            peek = read_non_whitespace(stream)
            if peek == '':
                break
            stream.seek(-1, 1)
            if peek.isalpha() or peek == "'" or peek == '"':
                operator = ""
                while True:
                    tok = stream.read(1)
                    if tok.isspace() or tok in NameObject.delimiterCharacters:
                        stream.seek(-1, 1)
                        break
                    elif tok == '':
                        break
                    operator += tok
                if operator == "BI":
                    # begin inline image - a completely different parsing
                    # mechanism is required, of course... thanks buddy...
                    assert operands == []
                    ii = self._read_inline_image(stream)
                    self.operations.append((ii, "INLINE IMAGE"))
                else:
                    self.operations.append((operands, operator))
                    operands = []
            elif peek == '%':
                # If we encounter a comment in the content stream, we have to
                # handle it here.  Typically, readObject will handle
                # encountering a comment -- but readObject assumes that
                # following the comment must be the object we're trying to
                # read.  In this case, it could be an operator instead.
                while peek not in ('\r', '\n'):
                    peek = stream.read(1)
            else:
                operands.append(read_object(stream, None))

    def _read_inline_image(self, stream):
        # begin reading just after the "BI" - begin image
        # first read the dictionary of settings.
        settings = DictionaryObject()
        while True:
            tok = read_non_whitespace(stream)
            stream.seek(-1, 1)
            if tok == "I":
                # "ID" - begin of image data
                break
            key = read_object(stream, self.pdf)
            _tok = read_non_whitespace(stream)
            stream.seek(-1, 1)
            value = read_object(stream, self.pdf)
            settings[key] = value
        # left at beginning of ID
        tmp = stream.read(3)
        assert tmp[:2] == "ID"
        data = ""
        while True:
            tok = stream.read(1)
            if tok == "E":
                _next = stream.read(1)
                if _next == "I":
                    break
                else:
                    stream.seek(-1, 1)
                    data += tok
            else:
                data += tok
        _x = read_non_whitespace(stream)
        stream.seek(-1, 1)
        return {"settings": settings, "data": data}

    def _get_data(self):
        newdata = StringIO()
        for operands, operator in self.operations:
            if operator == "INLINE IMAGE":
                newdata.write("BI")
                dicttext = StringIO()
                operands["settings"].write_to_stream(dicttext, None)
                newdata.write(dicttext.getvalue()[2:-2])
                newdata.write("ID ")
                newdata.write(operands["data"])
                newdata.write("EI")
            else:
                for op in operands:
                    op.write_to_stream(newdata, None)
                    newdata.write(" ")
                newdata.write(operator)
            newdata.write("\n")
        return newdata.getvalue()

    def _set_data(self, value):
        self.__parse_content_stream(StringIO(value))

    _data = property(_get_data, _set_data)


##
# A class representing the basic document metadata provided in a PDF File.
# <p>
# As of pyPdf v1.10, all text properties of the document metadata have two
# properties, eg. author and author_raw.  The non-raw property will always
# return a TextStringObject, making it ideal for a case where the metadata is
# being displayed.  The raw property can sometimes return a ByteStringObject,
# if pyPdf was unable to decode the string's text encoding; this requires
# additional safety in the caller and therefore is not as commonly accessed.
class DocumentInformation(DictionaryObject):
    def __init__(self):
        DictionaryObject.__init__(self)

    def get_text(self, key):
        retval = self.get(key, None)
        if isinstance(retval, TextStringObject):
            return retval
        return None

    ##
    # Read-only property accessing the document's title.  Added in v1.6, will
    # exist for all future v1.x releases.  Modified in v1.10 to always return a
    # unicode string (TextStringObject).
    # @return A unicode string, or None if the title is not provided.
    title = property(lambda self: self.get_text("/Title"))
    title_raw = property(lambda self: self.get("/Title"))

    ##
    # Read-only property accessing the document's author.  Added in v1.6, will
    # exist for all future v1.x releases.  Modified in v1.10 to always return a
    # unicode string (TextStringObject).
    # @return A unicode string, or None if the author is not provided.
    author = property(lambda self: self.get_text("/Author"))
    author_raw = property(lambda self: self.get("/Author"))

    ##
    # Read-only property accessing the subject of the document.  Added in v1.6,
    # will exist for all future v1.x releases.  Modified in v1.10 to always
    # return a unicode string (TextStringObject).
    # @return A unicode string, or None if the subject is not provided.
    subject = property(lambda self: self.get_text("/Subject"))
    subject_raw = property(lambda self: self.get("/Subject"))

    ##
    # Read-only property accessing the document's creator.  If the document was
    # converted to PDF from another format, the name of the application (for
    # example, OpenOffice) that created the original document from which it was
    # converted.  Added in v1.6, will exist for all future v1.x releases.
    # Modified in v1.10 to always return a unicode string (TextStringObject).
    # @return A unicode string, or None if the creator is not provided.
    creator = property(lambda self: self.get_text("/Creator"))
    creator_raw = property(lambda self: self.get("/Creator"))

    ##
    # Read-only property accessing the document's producer.  If the document
    # was converted to PDF from another format, the name of the application
    # (for example, OSX Quartz) that converted it to PDF.  Added in v1.6, will
    # exist for all future v1.x releases.  Modified in v1.10 to always return a
    # unicode string (TextStringObject).
    # @return A unicode string, or None if the producer is not provided.
    producer = property(lambda self: self.get_text("/Producer"))
    producer_raw = property(lambda self: self.get("/Producer"))


##
# A class representing a destination within a PDF file.
# See section 8.2.1 of the PDF 1.6 reference.
# Stability: Added in v1.10, will exist for all v1.x releases.
class Destination(DictionaryObject):
    def __init__(self, title, page, typ, *args):
        DictionaryObject.__init__(self)
        self[NameObject("/Title")] = title
        self[NameObject("/Page")] = page
        self[NameObject("/Type")] = typ

        # from table 8.2 of the PDF 1.6 reference.
        if typ == "/XYZ":
            (self[NameObject("/Left")], self[NameObject("/Top")],
             self[NameObject("/Zoom")]) = args
        elif typ == "/FitR":
            (self[NameObject("/Left")], self[NameObject("/Bottom")],
             self[NameObject("/Right")], self[NameObject("/Top")]) = args
        elif typ in ["/FitH", "FitBH"]:
            self[NameObject("/Top")], = args
        elif typ in ["/FitV", "FitBV"]:
            self[NameObject("/Left")], = args
        elif typ in ["/Fit", "FitB"]:
            pass
        else:
            raise utils.PdfReadError("Unknown Destination Type: %r" % typ)

    ##
    # Read-only property accessing the destination title.
    # @return A string.
    title = property(lambda self: self.get("/Title"))

    ##
    # Read-only property accessing the destination page.
    # @return An integer.
    page = property(lambda self: self.get("/Page"))

    ##
    # Read-only property accessing the destination type.
    # @return A string.
    typ = property(lambda self: self.get("/Type"))

    ##
    # Read-only property accessing the zoom factor.
    # @return A number, or None if not available.
    zoom = property(lambda self: self.get("/Zoom", None))

    ##
    # Read-only property accessing the left horizontal coordinate.
    # @return A number, or None if not available.
    left = property(lambda self: self.get("/Left", None))

    ##
    # Read-only property accessing the right horizontal coordinate.
    # @return A number, or None if not available.
    right = property(lambda self: self.get("/Right", None))

    ##
    # Read-only property accessing the top vertical coordinate.
    # @return A number, or None if not available.
    top = property(lambda self: self.get("/Top", None))

    ##
    # Read-only property accessing the bottom vertical coordinate.
    # @return A number, or None if not available.
    bottom = property(lambda self: self.get("/Bottom", None))


def convert_to_int(d, size):
    if size > 8:
        raise utils.PdfReadError("invalid size in convertToInt")
    d = "\x00\x00\x00\x00\x00\x00\x00\x00" + d
    d = d[-8:]
    return struct.unpack(">q", d)[0]


# ref: pdf1.8 spec section 3.5.2 algorithm 3.2
_encryption_padding = '\x28\xbf\x4e\x5e\x4e\x75\x8a\x41\x64\x00\x4e\x56' + \
                      '\xff\xfa\x01\x08\x2e\x2e\x00\xb6\xd0\x68\x3e\x80\x2f\x0c' + \
                      '\xa9\xfe\x64\x53\x69\x7a'


# Implementation of algorithm 3.2 of the PDF standard security handler,
# section 3.5.2 of the PDF 1.6 reference.
def _alg32(password, rev, keylen, owner_entry, p_entry, id1_entry, metadata_encrypt=True):
    # 1. Pad or truncate the password string to exactly 32 bytes.  If the
    # password string is more than 32 bytes long, use only its first 32 bytes;
    # if it is less than 32 bytes long, pad it by appending the required number
    # of additional bytes from the beginning of the padding string
    # (_encryption_padding).
    password = (password + _encryption_padding)[:32]
    # 2. Initialize the MD5 hash function and pass the result of step 1 as
    # input to this function.
    import struct
    m = md5(password)
    # 3. Pass the value of the encryption dictionary's /O entry to the MD5 hash
    # function.
    m.update(owner_entry)
    # 4. Treat the value of the /P entry as an unsigned 4-byte integer and pass
    # these bytes to the MD5 hash function, low-order byte first.
    p_entry = struct.pack('<i', p_entry)
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
            md5_hash = md5(md5_hash[:keylen]).digest()
    # 9. Set the encryption key to the first n bytes of the output from the
    # final MD5 hash, where n is always 5 for revision 2 but, for revision 3 or
    # greater, depends on the value of the encryption dictionary's /Length
    # entry.
    return md5_hash[:keylen]


# Implementation of algorithm 3.3 of the PDF standard security handler,
# section 3.5.2 of the PDF 1.6 reference.
def _alg33(owner_pwd, user_pwd, rev, keylen):
    # steps 1 - 4
    key = _alg33_1(owner_pwd, rev, keylen)
    # 5. Pad or truncate the user password string as described in step 1 of
    # algorithm 3.2.
    user_pwd = (user_pwd + _encryption_padding)[:32]
    # 6. Encrypt the result of step 5, using an RC4 encryption function with
    # the encryption key obtained in step 4.
    val = utils.rc4_encrypt(key, user_pwd)
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
            val = utils.rc4_encrypt(new_key, val)
    # 8. Store the output from the final invocation of the RC4 as the value of
    # the /O entry in the encryption dictionary.
    return val


# Steps 1-4 of algorithm 3.3
def _alg33_1(password, rev, keylen):
    # 1. Pad or truncate the owner password string as described in step 1 of
    # algorithm 3.2.  If there is no owner password, use the user password
    # instead.
    password = (password + _encryption_padding)[:32]
    # 2. Initialize the MD5 hash function and pass the result of step 1 as
    # input to this function.
    m = md5(password)
    # 3. (Revision 3 or greater) Do the following 50 times: Take the output
    # from the previous MD5 hash and pass it as input into a new MD5 hash.
    md5_hash = m.digest()
    if rev >= 3:
        for i in range(50):
            md5_hash = md5(md5_hash).digest()
    # 4. Create an RC4 encryption key using the first n bytes of the output
    # from the final MD5 hash, where n is always 5 for revision 2 but, for
    # revision 3 or greater, depends on the value of the encryption
    # dictionary's /Length entry.
    key = md5_hash[:keylen]
    return key


# Implementation of algorithm 3.4 of the PDF standard security handler,
# section 3.5.2 of the PDF 1.6 reference.
def _alg34(password, owner_entry, p_entry, id1_entry):
    # 1. Create an encryption key based on the user password string, as
    # described in algorithm 3.2.
    key = _alg32(password, 2, 5, owner_entry, p_entry, id1_entry)
    # 2. Encrypt the 32-byte padding string shown in step 1 of algorithm 3.2,
    # using an RC4 encryption function with the encryption key from the
    # preceding step.
    u = utils.rc4_encrypt(key, _encryption_padding)
    # 3. Store the result of step 2 as the value of the /U entry in the
    # encryption dictionary.
    return u, key


# Implementation of algorithm 3.4 of the PDF standard security handler,
# section 3.5.2 of the PDF 1.6 reference.
def _alg35(password, rev, keylen, owner_entry, p_entry, id1_entry, _metadata_encrypt):
    # 1. Create an encryption key based on the user password string, as
    # described in Algorithm 3.2.
    key = _alg32(password, rev, keylen, owner_entry, p_entry, id1_entry)
    # 2. Initialize the MD5 hash function and pass the 32-byte padding string
    # shown in step 1 of Algorithm 3.2 as input to this function. 
    m = md5()
    m.update(bytes(_encryption_padding, 'utf-8'))
    # 3. Pass the first element of the file's file identifier array (the value
    # of the ID entry in the document's trailer dictionary; see Table 3.13 on
    # page 73) to the hash function and finish the hash.  (See implementation
    # note 25 in Appendix H.) 
    m.update(id1_entry)
    md5_hash = m.digest()
    # 4. Encrypt the 16-byte result of the hash, using an RC4 encryption
    # function with the encryption key from step 1. 
    val = utils.rc4_encrypt(key, md5_hash)
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
        val = utils.rc4_encrypt(new_key, val)
    # 6. Append 16 bytes of arbitrary padding to the output from the final
    # invocation of the RC4 function and store the 32-byte result as the value
    # of the U entry in the encryption dictionary. 
    # (implementator note: I don't know what "arbitrary padding" is supposed to
    # mean, so I have used null bytes.  This seems to match a few other
    # people's implementations)
    return val + ('\x00' * 16), key


def _encrypt(encrypt_key, pack1, pack2):
    key = encrypt_key + pack1 + pack2
    assert len(key) == (len(encrypt_key) + 5)
    md5_hash = md5(key).digest()
    key = md5_hash[:min(16, len(encrypt_key) + 5)]
    return key


def _create_rotation_scaling_matrix(rotation, scale):
    rotation = math.radians(rotation)
    rotating = [[math.cos(rotation), math.sin(rotation), 0],
                [-math.sin(rotation), math.cos(rotation), 0],
                [0, 0, 1]]
    scaling = [[scale, 0, 0],
               [0, scale, 0],
               [0, 0, 1]]
    ctm = utils.matrix_multiply(rotating, scaling)
    return ctm

# if __name__ == "__main__":
#    output = PdfFileWriter()
#
#    input1 = PdfFileReader(file("test\\5000-s1-05e.pdf", "rb"))
#    page1 = input1.getPage(0)
#
#    input2 = PdfFileReader(file("test\\PDFReference16.pdf", "rb"))
#    page2 = input2.getPage(0)
#    page3 = input2.getPage(1)
#    page1.mergePage(page2)
#    page1.mergePage(page3)
#
#    input3 = PdfFileReader(file("test\\cc-cc.pdf", "rb"))
#    page1.mergePage(input3.getPage(0))
#
#    page1.compressContentStreams()
#
#    output.addPage(page1)
#    output.write(file("test\\merge-test.pdf", "wb"))
