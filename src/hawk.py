import hashlib
import os
from urllib.request import urlretrieve
import posixpath as pp
import h5py
from hawk_lut import lut

# %% Misc declarations

hdf5_group_getter = h5py.Group.__getitem__

_pcode = "88e34cc543ff5aeeb9f4"

# %% Exceptions


class BadDownloadError(Exception):
    pass


# %% Helper functions


def get_data_if_missing(key, data_dir, pcode=_pcode):
    fname = os.path.join(data_dir, key + ".hdf5")
    if not os.path.isfile(fname) or not key in lut:
        url = f"https://figshare.com/ndownloader/files/{lut[key]['id']}?private_link={pcode}"
        print(
            f"Downloading test data {key} from ORDA into {data_dir}", end="", flush=True
        )
        fn, _ = urlretrieve(url, fname)
        print(" [DONE] checking md5 hash", end="", flush=True)
        with open(fn, "rb") as f:
            md5 = hashlib.md5(f.read()).hexdigest()
            if not md5 == lut[key]["md5"]:
                raise BadDownloadError(
                    "md5 checksum missmatch, check network connection and attempt to redownload"
                )
            else:
                print(" [DONE]")
                return key


# %% Wrappers


def Group_getter_wrapped(self, *args, **kwargs):
    pth = pp.join(self.path, pp.normpath(args[0]))
    if pth.startswith("/"):
        pth = pth[1:]
    key = "_".join(pth.split("/")[1:3])
    try:
        item = hdf5_group_getter(self, *args, **kwargs)
    except KeyError as err:
        if not get_data_if_missing(key, self.data_dir):
            raise err
        else:
            item = hdf5_group_getter(self, *args, **kwargs)
    item.path = pth
    item.data_dir = self.data_dir
    return item


# %% API


def SBW(data_dir="./hawk_data"):
    if not os.path.isdir(data_dir):
        os.makedirs(data_dir)
    pth = os.path.join(data_dir, "SBW_header.hdf5")
    get_data_if_missing("SBW_header", data_dir, pcode=_pcode)
    obj = h5py.File(pth, "r")
    obj.data_dir = data_dir
    obj.path = ""
    return obj


def setup(obj, out=None):
    if out is None:
        out = {}
    out |= obj.attrs
    if not obj.name == "/":
        pf = obj.file
        # these objects are not persistent and so no need to track these
        pf.data_dir = ""
        pf.path = ""
        parent = pf.get(pp.dirname(obj.name))
        out |= setup(parent, out)
    return out


def explore(obj):
    if "excitationType" in obj.attrs:
        print(f"{obj.path} ({obj.attrs['excitationType']})")
    else:
        print(obj.path)
    for k, o in obj.items():
        if isinstance(o, h5py.Dataset):
            print(f"    {k} ({o.attrs['units']})")
        elif o is not None:
            explore(o)
        else:
            print(f"{obj.path}/{k} (undownloaded)")


def describe(obj, setup=1):
    if isinstance(obj, h5py.File):
        return f"Header file for Hawk SBW dataset. DOI 10.15131/shef.data.22710040. See documentation for details."
    else:
        s = [
            "testCampaign",
            "testSeries",
            "testRepeat",
            "sensorID",
            "singalType",
        ]
        out = {s: n for s, n in zip(s, obj.path.split("/"))} 
        if setup:
            out |= obj.setup()
        return out

# %% Horrible monkey patches

h5py.Group.__getitem__ = Group_getter_wrapped

h5py.Group.setup = setup
h5py.Dataset.setup = setup

h5py.Group.explore = explore
h5py.Dataset.explore = explore

h5py.File.describe = describe
h5py.Group.describe = describe
h5py.Dataset.describe = describe


if __name__ == '__main__':

    data_dir = "./hawk_data"
    data = SBW(data_dir)
    series = 'BR_AR' # i.e Burst-random amplitude-ramp 
    rep = '01'
    test_series = data["LMS"][series][rep]
    test_series.explore()
