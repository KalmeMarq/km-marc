class VariableField:
    def __init__(self, tag: str) -> None:
        self.tag = tag

class ControlField(VariableField):
    def __init__(self, tag: str, data: str) -> None:
        super().__init__(tag)
        self.data = data

    def __str__(self) -> str:
        return f"{self.tag} {self.data}"

class SubField:
    def __init__(self, code: str, data: str) -> None:
        self.code = code
        self.data = data

    def __str__(self) -> str:
        return f"${self.code}{self.data}"


class DataField(VariableField):
    def __init__(self, tag: str, ind1: str, ind2: str) -> None:
        super().__init__(tag)
        self.ind1 = ind1
        self.ind2 = ind2
        self.subfields: list[SubField] = []

    def __getitem__(self, key) -> list[SubField] | None:
        res = []
        
        for subfield in self.subfields:
            if subfield.code == key:
                res.append(subfield)
        
        return res if len(res) > 0 else None 

    def __contains__(self, key) -> bool:
        for subfield in self.subfields:
            if subfield.code == key:
                return True

        return False

    def __str__(self) -> str:
        res = f"{self.tag} {self.ind1}{self.ind2}"
        for subfield in self.subfields:
            res += str(subfield)
        return res


class Leader:
    def __init__(self) -> None:
        self.record_length = 0
        self.record_status: str = ' '
        self.type_of_record: str = ' '
        self.impl_defined1 = []
        self.char_coding_scheme = []
        self.indicator_count = 0
        self.subfield_length = 0
        self.base_address_of_data = 0
        self.impl_defined2 = []
        self.entry_map: list[str] = []

    def __str__(self) -> str:
        return f"=LDR {self.record_length:05d}{self.record_status}{self.type_of_record}{''.join(self.impl_defined1)}{self.char_coding_scheme}{self.indicator_count}{self.subfield_length}{self.base_address_of_data:05d}{''.join(self.impl_defined2)}{''.join(self.entry_map)}"


class Record:
    def __init__(self, leader: Leader) -> None:
        self.leader = leader
        self.control_fields: list[ControlField] = []
        self.data_fields: list[DataField] = []

    def __getitem__(self, key) -> list[ControlField | DataField] | None:
        if key in Record.__custom_getters:
            try:
                return Record.__custom_getters[key](self)
            except:
                return None

        res = []
        
        for field in self.control_fields:
            if field.tag == key:
                res.append(field)

        for field in self.data_fields:
            if field.tag == key:
                res.append(field)
        
        return res if len(res) > 0 else None 
    
    def __contains__(self, key) -> bool:
        for field in self.control_fields:
            if field.tag == key:
                return True
            
        for field in self.data_fields:
            if field.tag == key:
                return True

        return False

    def __str__(self) -> str:
        res = f"{self.leader}"
        for field in sorted(self.control_fields, key=lambda cs : cs.tag):
            res += f"\n={field}"
        for field in sorted(self.data_fields, key=lambda sf : sf.tag):
            res += f"\n={field}"
        return res
    
    __custom_getters = {}
    
    @staticmethod
    def register_custom_getter(name: str, getter):
        Record.__custom_getters[name] = getter
