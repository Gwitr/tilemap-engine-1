import struct
import warnings

class Serializable():
    
    def __init__(self, name, *, exclude=[]):
        self.exclude = exclude
        self.cls = None
        self.name = name

    def __call__(self, cls):
        global FIELD_SERIALIZABLES

        if not hasattr(cls, "__init_deserialize__"):
            raise AttributeError("__init_deserialize__ missing")
        
        FIELD_SERIALIZABLES.append(self)
        
        self.cls = cls
        return cls

def UserSerializable(name):
    def decorator(f):
        global USER_SERIALIZABLES
        nonlocal name

        USER_SERIALIZABLES[f] = name
        
        return f

    return decorator

FIELD_SERIALIZABLES = []
USER_SERIALIZABLES = {}
def serialize(obj):
    if type(obj) is int:
        # return b"i" + struct.pack("<i", obj)
        if obj >= 0:
            # Efficiently pack number
            ilist = []
            while obj > 0:
                ilist.append(obj & 0b01111111)
                obj >>= 7
            if len(ilist) == 0:
                ilist.append(0)
                
            return b"I" + bytes([i | 0b10000000 for i in ilist[:-1]] + [ilist[-1]])
        else:
            return b"i" + struct.pack("i", obj)

    if type(obj) is float:
        return b"f" + struct.pack("<f", obj)

    if type(obj) is str:
        d = obj.encode("utf8")
        return b"s" + serialize(len(d)) + d

    if type(obj) is bytes:
        return b"b" + serialize(len(obj)) + obj

    if obj is True:
        return b"t"

    if obj is False:
        return b"F"

    if obj is None:
        return b"N"

    if type(obj) in {list, set, tuple}:
        if type(obj) is list:  res = b"L"
        if type(obj) is tuple: res = b"T"
        if type(obj) is set:   res = b"S"
        res += serialize(len(obj))
        for i in obj:
            res += serialize(i)
        return res

    if type(obj) is dict:
        res = b"D"
        res += serialize(len(obj))
        for k, v in obj.items():
            res += serialize(k)
            res += serialize(v)
        return res

    if type(obj) in USER_SERIALIZABLES:
        res = b"U"
        res += serialize(USER_SERIALIZABLES[type(obj)])
        
        raw = obj.dump()
        res += serialize(len(raw))
        res += raw

        return res
    
    for entry in FIELD_SERIALIZABLES:
        if entry.cls is type(obj):
            res = b"O"
            res += serialize(entry.name)
            d = {i: getattr(obj, i) for i in obj.__slots__ if i not in entry.exclude}
            res += serialize(d)

            return res

    raise ValueError("can't serialize type %s" % type(obj).__name__)


def deserialize(data, offs):
    dtype = data[offs]
    offs += 1
    if dtype in b"I":
        # sz = struct.calcsize("i")
        # res = struct.unpack("i", data[offs:offs+sz])[0]
        # offs += sz
        ilist = []
        while data[offs] & 0b10000000:
            ilist.append(data[offs])
            offs += 1
        ilist.append(data[offs])
        offs += 1

        res = 0
        for i, x in enumerate(ilist):
            res |= (x & 0b01111111) << (7 * i)
        
        return res, offs

    if dtype in b"i":
        sz = struct.calcsize("i")
        res = struct.unpack("i", data[offs:offs+sz])[0]
        offs += sz

        return res, offs

    if dtype in b"f":
        sz = struct.calcsize("f")
        res = struct.unpack("f", data[offs:offs+sz])[0]
        offs += sz
        return res, offs

    if dtype in b"sb":
        sz, offs = deserialize(data, offs)
        if type(sz) is not int:
            raise ValueError("at offset %d: size must be int" % offs)
        if sz < 0:
            raise ValueError("at offset %d: size must be positive" % offs)

        res = data[offs:offs+sz]
        offs += sz

        if dtype in b"s":
            return res.decode("utf8"), offs
        return res, offs

    if dtype in b"t":
        return True, offs

    if dtype in b"F":
        return False, offs

    if dtype in b"N":
        return None, offs

    if dtype in b"LTS":
        length, offs = deserialize(data, offs)
        if type(length) is not int:
            raise ValueError("at offset %d: length must be int" % offs)
        if length < 0:
            raise ValueError("at offset %d: length must be positive" % offs)

        res = []
        for _ in range(length):
            element, offs = deserialize(data, offs)
            res.append(element)

        if dtype in b"T":
            return tuple(res), offs
        if dtype in b"S":
            return set(res), offs
        return res, offs

    if dtype in b"D":
        length, offs = deserialize(data, offs)
        if type(length) is not int:
            raise ValueError("at offset %d: length must be int" % offs)
        if length < 0:
            raise ValueError("at offset %d: length must be positive" % offs)

        res = {}
        for _ in range(length):
            key, offs = deserialize(data, offs)
            value, offs = deserialize(data, offs)
            if type(key) is list:
                warnings.warn(UserWarning("key is list, coercing into tuple"))
                key = tuple(key)
            res[key] = value
        return res, offs

    if dtype in b"O":
        objname, offs = deserialize(data, offs)
        if type(objname) is not str:
            raise ValueError("at offset %d: objname must be str" % offs)

        objdict, offs = deserialize(data, offs)
        if type(objdict) is not dict:
            raise ValueError("at offset %d: objdict must be dict" % offs)

        for entry in FIELD_SERIALIZABLES:
            if entry.name == objname:
                break
        else:
            raise ValueError("at offset %d: unknown Serializable \"%s\"" % (offs, objname))

        res = entry.cls.__new__(entry.cls)
        for key in objdict:
            if type(key) is not str:
                raise ValueError("at offset %d: object attribute name must be str" % (offs))
            setattr(res, key, objdict[key])

        res.__init_deserialize__()
        
        return res, offs

    if dtype in b"U":
        objname, offs = deserialize(data, offs)
        if type(objname) is not str:
            raise ValueError("at offset %d: objname must be str" % offs)

        sz, offs = deserialize(data, offs)
        if type(sz) is not int:
            raise ValueError("at offset %d: size must be int" % offs)
        if sz < 0:
            raise ValueError("at offset %d: size must be positive" % offs)

        for key in USER_SERIALIZABLES:
            if USER_SERIALIZABLES[key] == objname:
                break
        else:
            raise ValueError("at offset %d: unknown UserSerializable \"%s\"" % (offs, objname))

        return key.load(data[offs:offs+sz]), offs + sz

    raise ValueError("unknown type %d" % dtype)
