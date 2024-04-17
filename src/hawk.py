import hashlib
import os
from urllib.request import urlretrieve
import posixpath as pp
import h5py
import pandas as pd
import numpy as np
from hawk_lut_sbw import lut as lut_sbw
from hawk_lut_fst import lut as lut_fst

# %% Misc declarations

hdf5_group_getter = h5py.Group.__getitem__

lut = lut_sbw | lut_fst

# %% Exceptions


class BadDownloadError(Exception):
    pass


# %% Helper functions


def get_data_if_missing(key, data_dir):
    fname = os.path.join(data_dir, key + ".hdf5")
    if not os.path.isfile(fname) or key not in lut:
        url = f"https://figshare.com/ndownloader/files/{lut[key]['id']}"
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
    try:
        pth = pp.join(self.path, pp.normpath(args[0]))
    except AttributeError:
        pth = pp.normpath(args[0])
        self.data_dir = ""
    if pth.startswith("/"):
        pth = pth[1:]

    # print(pth)

    key = "_".join(pth.split("/")[:3])

    if key.startswith("LMS") or key.startswith("NI"):
        key = "_".join(key.split("_")[1:])

    # print(pth, key)

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
    get_data_if_missing("SBW_header", data_dir)
    obj = h5py.File(pth, "r")
    obj.data_dir = data_dir
    obj.path = ""
    return obj


def FST(data_dir="./hawk_data"):
    if not os.path.isdir(data_dir):
        os.makedirs(data_dir)
    pth = os.path.join(data_dir, "FST_header.hdf5")
    get_data_if_missing("FST_header", data_dir)
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


def explore2(obj, depth=10, out=None):
    opath = obj.path
    if obj.path == "":
        opath = "/"
    if out is None:
        out = {}
    new = {}
    for k in obj.keys():
        pth = pp.join(opath, k)
        link = obj.get(k, getlink=True)
        if isinstance(link, h5py.ExternalLink):
            new |= {pth: "(undownloaded)"}
        else:
            o = obj.get(k)
            if isinstance(o, h5py.Dataset):
                new |= {
                    pth: f"Dataset: {o.attrs['measurement']} ({o.attrs['units']}) {o.shape}"
                }
            elif depth > 1:
                new |= explore2(o, depth=depth - 1)
            else:
                new |= {pth: "..."}
    out |= {opath: new}
    return out


def visit_linked(obj, func):
    func(obj.name, obj)
    if not isinstance(obj, h5py.Dataset):
        for item in obj.values():
            visit_linked(item, func)


def describe(obj, setup=1):
    if isinstance(obj, h5py.File):
        return "Header file for Hawk dataset.  See documentation for details."
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


# %% Advanced slicing for the Hawk FST


def get_FST_metadata(data_dir="./"):
    """Load the FST metadata as two pandas dfs. One for the tests and another for the sensors"""
    sensor_fname = os.path.join(data_dir, "Hawk_FST_sensor_meta.csv")
    if not os.path.isfile(sensor_fname):
        sensor_url = "https://figshare.com/ndownloader/files/43971009"
        urlretrieve(sensor_url, sensor_fname)
    sensor_data = pd.read_csv(os.path.join(data_dir, sensor_fname))

    test_fname = os.path.path.join(data_dir, "Hawk_FST_test_meta.csv")
    if not os.isfile(test_fname):
        test_url = "https://figshare.com/ndownloader/files/43971012"
        urlretrieve(test_url, test_fname)
    test_data = pd.read_csv(os.path.join(data_dir, test_fname))

    return test_data, sensor_data

def slice_from_dfs(data, tests=[], channels=[]):
    out = []
    paths = tests["testID"] + "/" + tests["testNumber"].astype(str).str.zfill(2)
    for test in paths:
        test_out = []
        for signal, sensor in zip(channels["signal"], channels["sensorID"]):
            reps = data[test][sensor][signal][:]
            test_out.append(reps.T)
        out.append(test_out)
    try:
        arr = np.array(out).transpose(3, 2, 0, 1)
    except ValueError as e:
        print(e)
        print("Ragged arrays detected, returning nested lists")
        arr = out
    return arr

# %% Horrible monkey patches

h5py.Group.__getitem__ = Group_getter_wrapped

h5py.Group.setup = setup
h5py.Dataset.setup = setup

h5py.Group.explore = explore2
h5py.Dataset.explore = explore2

h5py.File.describe = describe
h5py.Group.describe = describe
h5py.Dataset.describe = describe
