import json
import io
import xml.etree.ElementTree as ET
from kmmarc.marc import Record, ControlField, DataField, SubField, Leader
from kmmarc.constants import *


class MarcJsonReader:
    def __init__(self, f) -> None:
        self.json = json.load(f)
        if not isinstance(self.json, list):
            self.json = [self.json]

    def __next(self, i):
        record_obj = self.json[i]
        record = Record(record_obj['leader'])

        if isinstance(record_obj['fields'], list):
            for field_obj in record_obj['fields']:
                tag = list(field_obj.keys())[0]

                if int(tag) < 10:
                    field = ControlField(tag, field_obj[tag])
                    record.control_fields.append(field)
                else:
                    field = DataField(tag, field_obj[tag]['ind1'], field_obj[tag]['ind2'])
                    
                    for subfield_obj in field_obj[tag]['subfields']:
                        code = list(subfield_obj.keys())[0]
                        field.subfields.append(SubField(code, subfield_obj[code]))

                    record.data_fields.append(field)
        else:
            for tag in record_obj['fields']:
                for field_obj in record_obj['fields']['tag']:
                    if int(tag) < 10:
                        field = ControlField(tag, field_obj)

                        record.control_fields.append(field)
                    else:
                        field = DataField(tag, field_obj['ind1'], field_obj['ind2'])

                        for code in field_obj['subfields']:
                            for subfield_obj in field_obj['subfields'][code]:
                                subfield = SubField(code, subfield_obj)
                                field.subfields.append(subfield)

                        record.data_fields.append(field)

        return record

    def __iter__(self):
        for i in range(len(self.json)):
            yield self.__next(i)


class MarcXmlReader:
    def __init__(self, data) -> None:
        self.root = data if isinstance(data, str) else ET.fromstringlist(data.readlines())
        self.record_tags = list(self.root)

    def __find(self, tag, path) -> ET.Element | None:
        res = tag.find(f"{'{http://www.loc.gov/MARC21/slim}'}{path}")
        if res is None:
            res = tag.find(f"{path}")
        return res
    
    def __findall(self, tag, path) -> list[ET.Element] :
        res = tag.findall(f"{'{http://www.loc.gov/MARC21/slim}'}{path}")
        if res is None or len(res) == 0:
            res = tag.findall(f"{path}")
        return res

    def __next(self, i):
        record_tag: ET.Element = self.record_tags[i]
        record = Record(self.__find(record_tag, "leader").text)

        for ctrl_field_tag in self.__findall(record_tag, "controlfield"):
            field = ControlField(ctrl_field_tag.attrib['tag'], ctrl_field_tag.text)
            record.control_fields.append(field)

        for data_field_tag in self.__findall(record_tag, "datafield"):
            field = DataField(data_field_tag.attrib['tag'], data_field_tag.attrib['ind1'], data_field_tag.attrib['ind2'])
            
            for subfield_tag in self.__findall(data_field_tag, "subfield"):
                subfield = SubField(subfield_tag.attrib['code'], subfield_tag.text)
                field.subfields.append(subfield)
            
            record.data_fields.append(field)

        return record

    def __iter__(self):
        for i in range(len(self.record_tags)):
            yield self.__next(i)


class MarcStreamReader:
    def __init__(self, f, force_utf8_encoding = False) -> None:
        self.__f = f
        self.__bytes: bytes = f.read()
        self.__bytes_len = len(self.__bytes) 
        self.__buf = io.BytesIO(self.__bytes)
        self.force_utf8_encoding = force_utf8_encoding

    def __parse_leader(self, leader_bytes: bytes):
        leader = Leader()
        
        leader_str = leader_bytes.decode("iso-8859-1")
        leader.record_length = int(leader_str[0:5])

        leader.record_status = leader_str[5:6]
        leader.type_of_record = leader_str[6:7]
        leader.impl_defined1 = leader_str[7:9]
        leader.char_coding_scheme = leader_str[9:10]
        leader.indicator_count = int(leader_str[10:11])
        leader.subfield_length = int(leader_str[11:12])
        leader.base_address_of_data = int(leader_str[12:17])
        leader.impl_defined2 = leader_str[17:20]
        leader.entry_map = leader_str[20:24]

        return leader
    
    def __parse_subfield_length(self, buf: io.BytesIO):
        global US
        global FT

        cur_bak = buf.tell()
        bytes_read = 0

        i = 0
        while True:
            if i >= 9999:
                buf.seek(cur_bak)
                return bytes_read

            r = buf.read(1)

            match r:
                case b'\x1f':
                    buf.seek(cur_bak)
                    return bytes_read
                case b'\x1e':
                    buf.seek(cur_bak)
                    return bytes_read
                case b'':
                    buf.seek(cur_bak)
                    raise Exception('Subfield not terminated')
                case _:
                    bytes_read += 1

            i += 1


    
    def __parse_data_field(self, tag, field_bytes: bytes, encoding: str):
        buf = io.BytesIO(field_bytes)

        field = DataField(tag, buf.read(1).decode(encoding), buf.read(1).decode(encoding))

        while True:
            read_byte = buf.read(1)
            if read_byte < b'\x00':
                break

            if read_byte == US:
                code = buf.read(1)
                if code < b'\x00':
                    raise Exception("Unexpected end of data field")
                
                if code == FT:
                    continue

                size = self.__parse_subfield_length(buf)
                data = buf.read(size)

                subfield = SubField(code.decode(encoding), data.decode(encoding))
                field.subfields.append(subfield)
                
                continue
            elif read_byte == FT:
                continue

        return field

    def __parse_record(self, leader_bytes: bytes, rec_bytes: bytes):
        leader = self.__parse_leader(leader_bytes)

        encoding = 'iso8859-1'
        if leader.char_coding_scheme == 'a' or self.force_utf8_encoding:
            encoding = 'utf-8'

        rec_buff = io.BytesIO(rec_bytes)

        directory_len = leader.base_address_of_data - (24 + 1)

        size = int(directory_len / 12)

        tags = [' '] * size
        lengths = [0] * size
        starts = [0] * size
        unsorted_start_index = {} 

        record = Record(leader)

        for i in range(size):
            tags[i] = rec_buff.read(3).decode("iso-8859-1")
            lengths[i] = int(rec_buff.read(4).decode("iso-8859-1"))
            starts[i] = int(rec_buff.read(5).decode("iso-8859-1"))
            unsorted_start_index[starts[i]] = i

        if rec_buff.read(1) != FT:
            raise Exception("Expected field terminator at end of directory")

        starts.sort()

        for s in range(size):
            i = unsorted_start_index[starts[s]]

            if int(tags[i]) < 10:
                eba = rec_buff.read(lengths[i] - 1)

                if rec_buff.read(1) != FT:
                    raise Exception("Expected field terminator at the end of field")

                record.control_fields.append(ControlField(tags[i], eba.decode(encoding)))
            else:
                eba = rec_buff.read(lengths[i])
                record.data_fields.append(self.__parse_data_field(tags[i], eba, encoding))
        
        if rec_buff.read(1) != RT:
            raise Exception("Expected record terminator at the end of record")

        return record

    def read_next(self):
        leader_bytes = self.__buf.read(24)

        rec_len = int(leader_bytes[0:5].decode("iso-8859-1"))
        return self.__parse_record(leader_bytes, self.__buf.read(rec_len - 24))

    def __iter__(self):
        while self.__buf.tell() < self.__bytes_len:
            yield self.read_next()
