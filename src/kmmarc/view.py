from kmmarc.marc import *


def format_record_as_unimarc_view(record: Record):
    res = f"MFN: 0\nEstado: UNK   Tipo: UNK   Nível hierárquico: UNK  Nível de cod: UNK\n"
    for ctrl_field in sorted(record.control_fields, key=lambda cs : cs.tag):
        res += f"\n{ctrl_field.tag}:{ctrl_field.data}"
    for data_field in sorted(record.data_fields, key=lambda sf : sf.tag):
        res += f"\n{data_field.tag}:{data_field.ind1}{data_field.ind2}"

        for subfield in data_field.subfields:
            res += f"^{subfield.code}{subfield.data}"
    return res


def format_record_as_isbd_view(record: Record):
    res = "[X]\n\n"
    res += f"{record['700'][0]['a'][0].data}, {record['700'][0]['b'][0].data}\n"
    res += f"{record['Title']} / {record['200'][0]['f'][0].data}"
    res += "\n\nCDU: 00"
    return res