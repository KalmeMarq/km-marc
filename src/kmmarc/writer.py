import json
import yaml
import io
import xml.etree.ElementTree as ET
from kmmarc.marc import Record
from kmmarc.constants import *

class MarcJsonWriter:
    def __init__(self, f, layout_format: int = 1, ignored_tags: list[str] | None = None, indent: int | None = None, sort_tags = False):
        self.f = f
        self.format = layout_format
        self.ignored_tags = [] if ignored_tags is None else ignored_tags
        self.indent = indent
        self.sort_tags = sort_tags

    def _write_format1(self, record: Record):
        obj = {
            'leader': str(record.leader),
            'fields': []
        }

        for field in record.get_control_fields(sorted=self.sort_tags):
            if self.ignored_tags.count(field.tag) > 0:
                continue

            obj['fields'].append({
                field.tag: field.data
            })

        for field in record.get_data_fields(sorted=self.sort_tags):
            if self.ignored_tags.count(field.tag) > 0:
                continue

            field_obj = {'ind1': field.ind1, 'ind2': field.ind2, 'subfields': []}

            for subfield in field.subfields:
                field_obj['subfields'].append({
                    subfield.code: subfield.data
                })

            obj['fields'].append({
                field.tag: field_obj
            })

        return obj

    def _write_format2(self, record: Record):
        obj = {
            'leader': str(record.leader),
            'fields': {}
        }

        for field in record.get_control_fields(sorted=self.sort_tags):
            if field.tag not in obj['fields']:
                obj['fields'][field.tag] = []

            obj['fields'][field.tag].append(field.data)

        for field in record.get_data_fields(sorted=self.sort_tags):
            if field.tag not in obj['fields']:
                obj['fields'][field.tag] = []

            field_obj = {'ind1': field.ind1, 'ind2': field.ind2, 'subfields': {}}

            for subfield in field.subfields:
                if subfield.code not in field_obj['subfields']:
                    field_obj['subfields'][subfield.code] = []

                field_obj['subfields'][subfield.code].append(subfield.data)

            obj['fields'][field.tag].append(field_obj)

        return obj

    def write(self, record: Record):
        if self.format == 1:
            obj = self._write_format1(record)
        else:
            obj = self._write_format2(record)

        json.dump(obj, self.f, indent=self.indent)

    def write_all(self, records: list[Record]):
        recs = []
        for record in records:
            if self.format == 1:
                recs.append(self._write_format1(record))
            else:
                recs.append(self._write_format2(record))

        json.dump(recs, self.f, indent=self.indent)


class MarcYamlWriter(MarcJsonWriter):
    def write(self, record: Record):
        if self.format == 1:
            obj = self._write_format1(record)
        else:
            obj = self._write_format2(record)

        yaml.dump(obj, self.f, indent=self.indent, sort_keys=False)

    def write_all(self, records: list[Record]):
        recs = []
        for record in records:
            if self.format == 1:
                recs.append(self._write_format1(record))
            else:
                recs.append(self._write_format2(record))

        yaml.dump(recs, self.f, indent=self.indent, sort_keys=False)


class MarcXmlWriter:
    def __init__(self, f, indent: int | None = None, ignored_tags: list[str] | None = None, xml_declaration=True, use_marc_namespace=False, sort_tags = False) -> None:
        self.f = f
        self.xml_declaration = xml_declaration
        self.indent = indent
        self.ignored_tags = [] if ignored_tags is None else ignored_tags
        self.namespace = 'marc:' if use_marc_namespace else ''
        self.collection_tag = ET.Element(f'{self.namespace}collection')
        self.sort_tags = sort_tags
        if use_marc_namespace:
            self.collection_tag.attrib['xmlns:marc'] = 'http://www.loc.gov/MARC21/slim'

    def write(self, record: Record):
        record_tag = ET.SubElement(self.collection_tag, 'record')
        leader_tag = ET.SubElement(record_tag, f'{self.namespace}leader')
        leader_tag.text = record.leader

        for field in record.get_control_fields(sorted=self.sort_tags):
            if self.ignored_tags.count(field.tag) > 0:
                continue

            field_tag = ET.SubElement(record_tag, f'{self.namespace}controlfield')
            field_tag.attrib['tag'] = field.tag
            field_tag.text = field.data

        for field in record.get_data_fields(sorted=self.sort_tags):
            if self.ignored_tags.count(field.tag) > 0:
                continue

            field_tag = ET.SubElement(record_tag, f'{self.namespace}datafield')
            field_tag.attrib['tag'] = field.tag
            field_tag.attrib['ind1'] = field.ind1
            field_tag.attrib['ind2'] = field.ind2

            for subfield in field.subfields:
                subfield_tag = ET.SubElement(field_tag, f'{self.namespace}subfield')
                subfield_tag.attrib['code'] = subfield.code
                subfield_tag.text = subfield.data

    def write_all(self, *records):
        for record in records:
            self.write(record)

    def flush(self):
        if self.indent is not None:
            ET.indent(self.collection_tag, space=''.join([" "] * self.indent))

        self.f.write(ET.tostring(self.collection_tag, xml_declaration=self.xml_declaration, encoding="unicode"))


class MarcStreamWriter:
    def __init__(self, f: io.FileIO, force_utf8_encoding=False, ignored_tags: list[str] | None = None, sort_tags = False) -> None:
        self.f = f
        self.ignored_tags = [] if ignored_tags is None else ignored_tags
        self.force_utf8_encoding = force_utf8_encoding
        self.sort_tags = sort_tags

    def write(self, record: Record):
        dir_buf = io.BytesIO()
        data_buf = io.BytesIO()

        previous = 0

        ldr = record.leader
        encoding = "iso8859-1"
        if self.force_utf8_encoding:
            ldr.char_coding_scheme = "a"
            encoding = 'utf-8'

        for field in record.get_control_fields(sorted=self.sort_tags):
            if self.ignored_tags.count(field.tag) > 0:
                continue

            data_buf.write(field.data.encode(encoding))
            data_buf.write(FT)
            dir_buf.write(f"{field.tag}{(data_buf.tell() - previous):04d}{previous:05d}".encode('iso8859-1'))
            previous = data_buf.tell()

        for field in record.get_data_fields(sorted=self.sort_tags):
            if self.ignored_tags.count(field.tag) > 0:
                continue

            data_buf.write(field.ind1.encode(encoding))
            data_buf.write(field.ind2.encode(encoding))
            for subfield in field.subfields:
                data_buf.write(US)
                data_buf.write(subfield.code.encode(encoding))
                data_buf.write(subfield.data.encode(encoding))
            data_buf.write(FT)
            dir_buf.write(f"{field.tag}{(data_buf.tell() - previous):04d}{previous:05d}".encode('iso8859-1'))
            previous = data_buf.tell()

        dir_buf.write(FT)

        base_address = 24 + dir_buf.tell()
        ldr.base_address_of_data = base_address
        record_len = ldr.base_address_of_data + data_buf.tell() + 1
        ldr.record_length = record_len

        self.f.write(f"{ldr.record_length:05d}".encode('iso8859-1'))
        self.f.write(f"{ldr.record_status}".encode('iso8859-1'))
        self.f.write(f"{ldr.type_of_record}".encode('iso8859-1'))
        self.f.write(f"{''.join(ldr.impl_defined1)}".encode('iso8859-1'))
        self.f.write(f"{ldr.char_coding_scheme}".encode('iso8859-1'))
        self.f.write(f"{str(ldr.indicator_count)}".encode('iso8859-1'))
        self.f.write(f"{str(ldr.subfield_length)}".encode('iso8859-1'))
        self.f.write(f"{ldr.base_address_of_data:05d}".encode('iso8859-1'))
        self.f.write(f"{''.join(ldr.impl_defined2)}".encode('iso8859-1'))
        self.f.write(f"{''.join(ldr.entry_map)}".encode('iso8859-1'))

        dir_buf.seek(0)
        data_buf.seek(0)
        self.f.write(dir_buf.read())
        self.f.write(data_buf.read())
        self.f.write(RT)

    def write_all(self, *records):
        for record in records:
            self.write(record)


def write_marc_json_to_path(path: str, records: list[Record] | Record, encoding = "utf-8", writer_getter = None):
    with open(path, "w", encoding=encoding) as f:
        writer = writer_getter(f) if writer_getter is not None else MarcJsonWriter(f)
        if isinstance(records, Record):
            writer.write(records)
        else:
            writer.write_all(records)


def write_marc_yaml_to_path(path: str, records: list[Record] | Record, encoding = "utf-8", writer_getter = None):
    with open(path, "w", encoding=encoding) as f:
        writer = writer_getter(f) if writer_getter is not None else MarcYamlWriter(f)
        if isinstance(records, Record):
            writer.write(records)
        else:
            writer.write_all(records)


def write_marc_xml_to_path(path: str, records: list[Record] | Record, encoding = "utf-8", writer_getter = None):
    with open(path, "w", encoding=encoding) as f:
        writer = writer_getter(f) if writer_getter is not None else MarcXmlWriter(f)
        if isinstance(records, Record):
            writer.write(records)
        else:
            writer.write_all(records)
        
        writer.flush()


def write_marc_stream_to_path(path: str, records: list[Record] | Record, writer_getter = None):
    with open(path, "wb") as f:
        writer = writer_getter(f) if writer_getter is not None else MarcStreamWriter(f)
        if isinstance(records, Record):
            writer.write(records)
        else:
            writer.write_all(records)