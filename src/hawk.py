import hashlib
import os
from urllib.request import urlretrieve

import h5py
import hawk_lut

_pcode = "88e34cc543ff5aeeb9f4"

class BadDownloadError(Exception):
    pass

class file_wrapper(h5py.File):
    def __getitem__(self, *args, **kwargs):
        try:
            item = super().__getitem__(*args, **kwargs)
        except KeyError as err:
            pth = args[0]
            if pth.startswith("/"):
                pth = pth[1:]
            key = "_".join(pth.split("/")[1:3])
            print(key)
            if key in hawk_lut.lut:
                fn = get_hawk_data_from_key(key, self.data_dir)
                if fn is None:
                    raise err
                with open(fn, "rb") as f:
                    md5 = hashlib.md5(f.read()).hexdigest()
                    if not md5 == hawk_lut.lut[key]["md5"]:
                        raise BadDownloadError(
                            "md5 checksum missmatch, check network connection and attempt redownload"
                        )
                item = self.__getitem__(*args, **kwargs)
            else:
                raise err
        return item


def SBW(data_dir="./hawk_data"):
    if not os.path.isdir(data_dir):
        os.makedirs(data_dir)
    pth = os.path.join(data_dir, "SBW_header.hdf5")
    get_hawk_data_from_key("SBW_header", data_dir, pcode=_pcode)
    obj = file_wrapper(pth, "r")
    obj.data_dir = data_dir
    return obj


def describe(obj, out=None):
    if out is None:
        out = {}
    out |= obj.attrs
    if not obj == obj.parent:
        out |= describe(obj.parent, out)
    return out


def get_hawk_data_from_key(key, data_dir, pcode=_pcode):
    fname = os.path.join(data_dir, key + ".hdf5")
    if not os.path.isfile(fname):
        num = hawk_lut.lut[key]["id"]
        url = f"https://figshare.com/ndownloader/files/{num}?private_link={pcode}"
        print(
            f"Downloading test data {key} from ORDA into {data_dir}", end="", flush=True
        )
        fn, _ = urlretrieve(url, fname)
        print(" [DONE]")
        return fn
