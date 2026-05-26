"""
Script Name: read_colton_files (rcf)
Author: Carter Shirley
Date: February 14, 2024
Description: You input the row number that is in the file "C:/Data/All Scan Notes.xlsx" and it will look up the file name and import the 
data and return back a dataframe with the raw data and the phased data.
"""

import pandas as pd
import numpy as np
import os
from processors.public.colton_math_functions import phase_data, phase_data_experiemnt

# module-level cache
_data_cache = {}



'''
read_trans_data reads in the data and phases in accordance to the way the data is outputted.
'''
def read_data_simple(file_path):
    """
    Loads data and returns a dictionary of raw NumPy arrays.
    This is much less 'complicated' than passing DataFrames around.
    """
    if not os.path.exists(file_path):
        return None

    # Check modification time to see if file has changed since last load
    mtime = os.path.getmtime(file_path)
    if file_path in _data_cache:
        cached_mtime, cached_data = _data_cache[file_path]
        if cached_mtime == mtime:
            return cached_data

    # 1. Detect Header
    with open(file_path, 'r', encoding="utf-8", errors="ignore") as f:
        first_chunk = f.read(4000)
    
    is_double = False
    # Detect if we have 2 lock-ins or 1
    if "X810 (V)" in first_chunk:
        is_double = True
        header_str = "Digikrom Spectr.:0 (?)	X810 (V)	Y810 (V)	R810 (V)	X830 (V)	Y830 (V)	R830 (V)"
        print("Detected 2 lock-ins in file:", file_path)
    elif "X (V)" in first_chunk:
        header_str = "Digikrom Spectr.:0 (?)	X (V)	Y (V)	R (V)"
    else:
        # Fallback for other data types (like PMT or CCD)
        header_str = None 

    # 2. Load into temporary DataFrame
    if header_str:
        df = read_data_with_dynamic_header(file_path, header=header_str)
    else:
        # Generic load if header detection fails
        df = pd.read_csv(file_path, sep='\t', skiprows=15, skipfooter=3, engine='python')
        print("Warning: Could not detect header, loaded with generic settings. File:", file_path)
    
    # 3. Handle double lock-in selection
    if is_double:
        # --- MANUAL TOGGLES ---
        # Set one to True and the other to False to select the desired lock-in data
        USE_830 = True
        USE_810 = False
        # ----------------------

        wl_col = "Digikrom Spectr.:0 (?)"
        if USE_830:
            # Extract 830 data and rename to generic labels for processing
            df = df[[wl_col, "X830 (V)", "Y830 (V)", "R830 (V)"]].copy()
            df.columns = [wl_col, "X (V)", "Y (V)", "R (V)"]
        elif USE_810:
            # Extract 810 data and rename to generic labels for processing
            df = df[[wl_col, "X810 (V)", "Y810 (V)", "R810 (V)"]].copy()
            df.columns = [wl_col, "X (V)", "Y (V)", "R (V)"]

    # 4. Phase the data while it is still a DataFrame
    df = phase_data(df)

    # 5. Convert to a simple dictionary of NumPy arrays
    data_dict = {col: df[col].to_numpy() for col in df.columns}

    _data_cache[file_path] = (mtime, data_dict)
    return data_dict

# '''
# read_trans_data reads in the data and phases in accordance to the way the data is outputted.
# '''
# def read_trans_data_old(excel_row, sample = False):
#     filename, sample_name = get_filename(excel_row)
#     print(filename)
#     # read in the data and skip the starting lines and ending lines
#     row_skip = range(0,15) # The number of rows to skip is different for the data
#     data = pd.read_csv(filename, engine='python' ,skiprows=row_skip, skipfooter=3, sep='\t', dtype=float)

#     # Phases the data and makes another column with the phased data 
#     # data = phase_data_experiemnt(data)
#     data = phase_data(data)
    

#     if sample:
#         # Gives the same_name of the data 
#         return data, sample_name

#     return data


# def read_trans_average_data(excel_row, sample = False):
#     filename, sample_name = get_filename(excel_row)
#     print(filename)
#     # read in the data and skip the starting lines and ending lines
#     row_skip = range(0,15) # The number of rows to skip is different for the data
#     data = pd.read_csv(filename, engine='python' ,skiprows=row_skip, skipfooter=3, sep='\t', dtype=float)

#     # Phases the data and makes another column with the phased data 
#     data = phase_data(data, x_name='X Average (V)', y_name='Y Average (V)')
#     # print(data['X (V)'])
    

#     if sample:
#         # Gives the same_name of the data 
#         return data, sample_name

#     return data

# '''
# read_voltage_series_data reads in the data and phases all off the voltages at once. It then seperates all of the voltages into a different data frames
# and outputs them all in a dictionary with the voltage as the dictionary keys.
# '''
# def read_voltage_series_data(excel_row, sample = False):
#     filename, sample_name = get_filename(excel_row, excel_filename = 'C:/Data/All Scan Notes New.xlsx', remote=False)
    
#     # Removes the error by having the "Check Status.vi" be replaced
#     # delete_line(filename, 5)
#     data = read_data_with_dynamic_header(filename, header='O-scope 2024B:0 (?)	Digikrom Spectr.:0 (?)	X (V)	Y (V)	R (V)')

#     # Phases the data and makes another column with the phased data 
#     data = phase_data(data)
    
#     # Finds all of the voltages that were scanned over in the data
#     voltages = np.int16(np.unique(data['O-scope 2024B:0 (?)']))

#     # Initialize an empty dictionary
#     data_by_voltage = {}

#     # Making a dictionary variable for each voltage
#     for voltage in voltages:
#         data_by_voltage[voltage] = data[data['O-scope 2024B:0 (?)'].isin([voltage])]

#     print(data_by_voltage)
#     if sample:
#         # Gives the same_name of the data 
#         return data_by_voltage, sample_name
    
#     # Returns the data by voltage and a list of voltages to unpack the dictionary
#     return data_by_voltage

# '''
# read_lockin_Fluke_data reads in the data and phases in accordance to the way the data is outputted.
# '''
# def read_lockin_fluke_data(excel_row, sample = False):
#     filename, sample_name = get_filename(excel_row)

#     # read in the data and skip the starting lines and ending lines
#     row_skip = range(0,14) # The number of rows to skip is different for the data
#     data = pd.read_csv(filename, engine='python' ,skiprows=row_skip, skipfooter=3, sep='\t', dtype=float)

#     # Phases the data and makes another column with the phased data 
#     data = phase_data(data, x_name='X830 (V)', y_name='Y830 (V)')

    
#     if sample:
#         # Gives the same_name of the data 
#         return data, sample_name

#     return data

# '''
# read_lockin_keithley_data reads in the data and phases in accordance to the way the data is outputted.
# '''
# def read_lockin_keithley_data(excel_row, sample = False):
#     filename, sample_name = get_filename(excel_row)

#     # read in the data and skip the starting lines and ending lines
#     row_skip = range(0,16) # The number of rows to skip is different for the data
#     data = pd.read_csv(filename, engine='python' ,skiprows=row_skip, skipfooter=3, sep='\t', dtype=float)

#     # Phases the data and makes another column with the phased data 
#     data = phase_data(data, x_name='X830 (V)', y_name='Y830 (V)')


#     if sample:
#         # Gives the same_name of the data 
#         return data, sample_name

#     return data

# '''
# read_CCD data reads in the data which is to be understood as a raser scan.
# '''
# def read_CCD_data(excel_row, sample = False, remote=False):
#     # Gets the filename and sample name from the excel file
#     if remote:
#         filename, sample_name = get_filename(excel_row, excel_filename='//2.coltonlab.byu.edu/C$/Data/All Scan Notes New.xlsx', remote=True)
#     else:
#         filename, sample_name = get_filename(excel_row, excel_filename='C:/Data/All Scan Notes New.xlsx', remote=False)

#     # read in the data and skip the starting lines and ending lines
#     print(filename)
#     data = read_data_with_dynamic_header(file_path=filename, header='Wavelength	Processed Data')

#     if sample:
#         # Gives the same_name of the data 
#         return data, sample_name
    
#     return data




# '''
# read_PMT data reads in the data that the photon counter reads out.
# '''
# def read_PMT_data(excel_row, sample = False):
#     filename, sample_name = get_filename(excel_row)

#     # read in the data and skip the starting lines and ending lines
#     row_skip = range(0,9) # The number of rows to skip is different for the data
#     data = pd.read_csv(filename, engine='python' ,skiprows=row_skip, skipfooter=3, sep='\t', dtype=float)


#     if sample:
#         # Gives the same_name of the data 
#         return data, sample_name
    
#     print(filename)

#     return data


# '''
# read_PMT data reads in the data that the photon counter reads out.
# '''
# def read_impedance_data(excel_row, headers):
#     filename, sample_name = get_filename(excel_row)

#     # read in the data and skip the starting lines and ending lines
#     row_skip = range(0,3) # The number of rows to skip is different for the data
#     data = pd.read_csv(filename, engine='python' ,skiprows=row_skip, skipfooter=0, dtype=float, names=headers)
#     # data['sample'] = sample_name
    
#     print(filename)

#     return data

'''
This function reads in the data by looking at the "Digikrom Spectr.:0 (?)	X810 (V)	Y810 (V)	R810 (V)	X830 (V)	Y830 (V)	R830 (V)" before the data headers
'''
def read_data_with_dynamic_header(file_path, header):
    header_index = None
    # Efficiently find the header without loading the whole file into strings
    with open(file_path, "r", encoding="utf-8") as f:
        for i, line in enumerate(f):
            if header in line:
                header_index = i
                break

    if header_index is None:
        raise ValueError("Could not find header row")

    # Read the data into a DataFrame, skipping unnecessary lines
    # Using 'c' engine instead of 'python' is significantly faster for large files
    df = pd.read_csv(file_path, skiprows=header_index, sep='\t', dtype=np.float64, engine='python', skipfooter=3)
    return df

# '''
# read_lockin_Fluke_data reads in the data and phases in accordance to the way the data is outputted.
# '''
# def read_2lockin(excel_row, sample = False, remote=False, Old=False, switch=False):
#     if Old:
#         filename, sample_name = get_filename(excel_row, excel_filename='C:/Data/All Scan Notes Old.xlsx', remote=False)
#     else:
#         filename, sample_name = get_filename(excel_row, excel_filename='C:/Data/All Scan Notes New.xlsx', remote=False)
#     # 'C:/Data/All Scan Notes Old.xlsx'
#     # read in the data and skip the starting lines and ending lines
#     try:
#         df = read_data_with_dynamic_header(filename, header="Digikrom Spectr.:0 (?)	X810 (V)	Y810 (V)	R810 (V)	X830 (V)	Y830 (V)	R830 (V)")
#         # print(df)
#         print(filename)
#     except:
#         # delete_line_2lockin(filename)
#         df = read_data_with_dynamic_header(filename, header="Digikrom Spectr.:0 (?)	X810 (V)	Y810 (V)	R810 (V)	X830 (V)	Y830 (V)	R830 (V)")
#         print(filename, 'was adjusted for Check Status.vi')

#     data830 = {}
#     data810 = {}

#     data830["Digikrom Spectr.:0 (?)"] = df["Digikrom Spectr.:0 (?)"]
#     data830["X (V)"] = df["X830 (V)"]
#     data830["Y (V)"] = df["Y830 (V)"]
#     data830["R (V)"] = df["R830 (V)"]

#     data810["Digikrom Spectr.:0 (?)"] = df["Digikrom Spectr.:0 (?)"]
#     data810["X (V)"] = df["X810 (V)"]
#     data810["Y (V)"] = df["Y810 (V)"]
#     data810["R (V)"] = df["R810 (V)"]

#     data830['I (V)'] = df["R830 (V)"] + df["R810 (V)"]
#     data810['I (V)'] = df["R830 (V)"] + df["R810 (V)"]
#     # Phases the data and makes another column with the phased data 
#     data830 = phase_data(data830)
#     data810 = phase_data(data810)

#     if switch:
#         return data810, data830
#     return data830, data810

# '''
# rcf.read_TCSPC_data() data reads in the data which is to be understood as a raser scan.
# '''
# def read_TCSPC_data(excel_row):
#     filename, sample_name, temperature = get_filename(excel_row, excel_filename='//2.coltonlab.byu.edu/C$/Data/All Scan Notes New.xlsx', remote=True, temp=True)
#     data = {}

#     with open(filename, "r", encoding="utf-8") as file:
#         lines = file.readlines()

#     # Find the header line "Digikrom Spectr.:0 (?)	X810 (V)	Y810 (V)	R810 (V)	X830 (V)	Y830 (V)	R830 (V)"
#     header_index = None
#     for i, line in enumerate(lines):
#         if '#ns/bin' in line:
#             time_step_line = i+1  # time is 
                
#         if '#counts' in line:
#             Counts = i+1  # The header is this line
#             break

#     time_step = float(lines[time_step_line])#, dtype=float)
#     data['Counts'] = np.array(lines[Counts:-1], dtype=float)
#     data['Time'] = np.arange(len(data['Counts'])) * time_step

#     return data, sample_name, temperature



# def read_etch_a_sketch_data(excel_row, sample = False):
#     filename, sample_name = get_filename(excel_row)

#     # read in the data and skip the starting lines and ending lines
#     row_skip = range(0,0) # The number of rows to skip is different for the data
#     # data = pd.read_csv(filename, engine='python' ,skiprows=row_skip, skipfooter=0)#, dtype=float)
#     data = pd.read_csv(filename, skiprows=row_skip, skipfooter=3, sep='\t', dtype=float, engine='python')
#     # data['sample'] = sample_name
    
#     print(filename)

#     return data
