# %% Import and intro

from hawk import SBW
import numpy as np
import matplotlib.pyplot as plt

# %% Basic usage

# %% Downloading the header file

data_dir = "./hawk_data"
data = SBW(data_dir)
data.describe()

# %% Explore the data

data.explore()

# %% Accessing a test series

series = 'BR_AR' # i.e Burst-random amplitude-ramp 
rep = '01'
test_series = data[f"LMS/{series}/{rep}"]
test_series.explore()


# %% Accessing the test setup (self describing)

test_series.describe()

# %% Grabbing data from a sensor

sensor = "LLC-07"  # Lower leading edge centre position 7 (wing tip)
sensor_data = test_series[sensor]
sensor_data.explore()


# %% Plotting some data (finally)

signal = "frequencyResponseFunction"
frfs = sensor_data[signal]
print(frfs.shape) # (spectralLines, Nrepeats)

# Grab the frequency information from the xData group
fs = data['LMS/xData/freq'] 

plt.figure()
plt.semilogy(fs[:], np.abs(frfs[:]))
# note that the units can be pulled directly from the data
plt.xlabel(f"{fs.attrs['measurement']} ({fs.attrs['units']})") 
plt.ylabel(f"{frfs.attrs['measurement']} ({frfs.attrs['units']})")
plt.show()

# %% Shorthand tricks

# note that we can access data directly from its path
frfs = data['/LMS/BR_AR/01/LLC-01/frf']
# or even
frfs = data[f'/LMS/{series}/{rep}/{sensor}/{signal}']

# %% Self describing 2

frfs.describe()

# %% Accessing some time domain data

ts = data['NI/xData/time']
accs = data['NI/RPH_AR/01/LLC-01/acc']
print(accs.shape) # (timePoints, Nrepeats)

plt.figure()
plt.plot(ts[:], accs[:])
plt.xlabel(f"{ts.attrs['measurement']} ({ts.attrs['units']})") 
plt.ylabel(f"{accs.attrs['measurement']} ({accs.attrs['units']})")
plt.show()

# Can access a full description of the test setup
accs.describe()

# Finally close the dataset
data.close()

# %% Advanced usage intro

# %% Context manager

with SBW(data_dir) as data:

    frfs = data['/LMS/BR_AR/01/LLC-01/frf']
    frfs_numpy = np.array(data['/LMS/BR_AR/01/LLC-01/frf'])

try:
    data['/LMS/BR_AR/01/LLC-01/frf'].shape # This fails because the file is now closed
except ValueError:
    pass

frfs.shape # this is ok because the variable frfs is still referenced BUT internal references may be broken
frfs_numpy.shape # this will always be ok ans should be considered best practice

# %% Casting data to numpy arrays

with SBW(data_dir) as data:

    frf1 = data['/LMS/BR_AR/01/LLC-01/frf']
    frf2 = np.array(data['/LMS/BR_AR/01/LLC-01/frf']) # return np.ndarray
    frf3 = data['/LMS/BR_AR/01/LLC-01/frf'][:] # also returns np.ndarray

print(type(frf1))
print(type(frf2))
print(type(frf3))

# %% Best practice

# context manager
# cast all required data to np.ndarray before performing any analysis / plotting
# leave the context manager

