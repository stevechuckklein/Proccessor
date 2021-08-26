import csv
import datetime
import numpy as np
import os.path
import pandas as pd

from tkinter import *
from tkinter import filedialog

# For step_id comparisons to determine if we are charging or discharging.
CHARGING_STEP_TYPE_IDS = [1, 3, 7]
DISCHARGING_STEP_TYPE_IDS = [2, 19, 20]

def find_start_byte(filename):
    with open(filename, "rb") as f:
        f.seek(64)
        file_chunk = f.read(4)  # Changed from 2 to 4 bytes
        start_index = int.from_bytes(file_chunk, byteorder='little')
    return start_index

def process_nda(inpath, start_byte, line_size=86, out_raw_binary=False):
    bad_lines = []
    datapoint_list = []
    with open(inpath, "rb") as f:
        f.seek(start_byte)
        byte_line = f.read(line_size)
        while byte_line:
            # If no data was read, break
            if byte_line == b'':
                break
            datapoint = process_byte_stream(byte_line, out_raw_binary)
            if datapoint['line_type'] == 170:
                bad_lines.append(datapoint)
            elif datapoint['line_type'] == 85:
                datapoint_list.append(datapoint)
            else:
                print("ERROR: Read a line that wasn't 'AA' or '55'. Offset: {}".format(f.tell()))
            byte_line = f.read(line_size)

    return datapoint_list

def process_byte_stream(byte_stream, out_raw_binary=False):
    curr_dict = {}

    # Line Type
    # 170 = "Error/Status Line"
    # 85 = "Regular Line
    # line_type = int.from_bytes(byte_stream[0:1],byteorder='little') # NOTE: bytes[0] returns an integer while
    #   bytes[0:1] returns a bytes object of length 1.
    line_type = byte_stream[0]  # Directly accessing byte when it is unsigned should speed up processing.
    curr_dict['line_type'] = line_type

    # current_step_range
    current_scale = int.from_bytes(byte_stream[78:80], byteorder='little')
    curr_dict['current_scale'] = current_scale
    if current_scale >= 1000:
        # print("Current_Scale = {} >= 1000".format(current_scale))
        current_scaling_factor = 10
    elif current_scale == 100:
        current_scaling_factor = 1
    # For Coin Cell Compatability
    # elif current_scale == 1:
    #    current_scaling_factor = 1
    else:
        if line_type == 85:
            print('WARNING: current_scale is not a known value')
        current_scaling_factor = 1
    # print("current_scaling_factor = {}".format(current_scaling_factor))
    # Record ID (seq_id)
    record_id = int.from_bytes(byte_stream[2:5], byteorder='little')
    curr_dict['record_id'] = record_id

    # Jump To is worthless....
    # jump_to = int.from_bytes(byte_stream[13:14], byteorder='little')
    jump_to = byte_stream[13]
    curr_dict['jump_to'] = jump_to

    # Step ID
    # The step number in the original step file.  Mostly used for tracking step changes.
    # Note: If step id is zero, there is funny behavior.
    # step_id = int.from_bytes(byte_stream[10:11], byteorder='little')
    step_id = byte_stream[10]
    curr_dict['step_id'] = step_id

    # Step type.
    # 4=REST. 1=CC_Chg. 7=CCCV_Chg. 2=CC_DChg.
    # step_type_id = int.from_bytes(byte_stream[12:13], byteorder='little')
    step_type_id = byte_stream[12]
    step_name = get_new_step_name(step_type_id)
    curr_dict['step_type_id'] = step_type_id
    curr_dict['step_name'] = step_name

    # Time in Step (4 bytes?)
    # For new systems, this is stored as an integer representing the elapsed time
    # in the current step in milliseconds.
    #
    # TODO: Need to verify if this is saved in 4 bytes or 8 bytes.  4 bytes allows for a max time in step of around 47
    #   days so this is probably a moot point.
    time_in_step_ms = int.from_bytes(byte_stream[14:18], byteorder='little')
    curr_dict['time_in_step_ms'] = time_in_step_ms
    curr_dict['time_in_step'] = time_in_step_ms / 1000

    # Voltage (Bytes 22-25)
    #   4 byte signed int
    #   Stored as mV*10. voltage/10/1000 = Volts).
    voltage = int.from_bytes(byte_stream[22:26], byteorder='little', signed=True)
    curr_dict['voltage'] = voltage

    # Current (Bytes 26-29)
    #   4 byte signed int
    #   Stored as mA*10. current/10/1000 = Amps
    current = int.from_bytes(byte_stream[26:30], byteorder='little', signed=True)
    curr_dict['current'] = current * current_scaling_factor

    # Capacity/Energy is different in new files.  Charge Capacity/Energy and Discharge Capacity/Energy
    #   are now kept in separate variables.

    # Charge Capacity (Bytes 38-45)
    #   8 byte unsigned int (assumed unsigned as negative capacity makes no sense...)
    #   Stored as mAs? charge_capacity/3600/10000 = Ah
    charge_Ah = int.from_bytes(byte_stream[38:46], byteorder='little')
    curr_dict['charge_Ah'] = charge_Ah * current_scaling_factor

    # Discharge Capacity (Bytes 46-53)
    #   8 byte unsigned int (assumed unsigned as negative capacity makes no sense...)
    #   Stored as mAs? discharge_capacity/3600/10000 = Ah
    discharge_Ah = int.from_bytes(byte_stream[46:54], byteorder='little')
    curr_dict['discharge_Ah'] = discharge_Ah * current_scaling_factor

    # Charge Energy (Bytes 54-61)
    #   8 byte unsigned int (assumed unsigned as negative energy makes no sense...)
    #   Stored as mWs? charge_energy/3600/10000 = Wh
    charge_Wh = int.from_bytes(byte_stream[54:62], byteorder='little')
    curr_dict['charge_Wh'] = charge_Wh * current_scaling_factor

    # Discharge Energy (Bytes 62-69)
    #   8 byte unsigned int (assumed unsigned as negative energy makes no sense...)
    #   Stored as mWs? charge_energy/3600/10000 = Wh
    discharge_Wh = int.from_bytes(byte_stream[62:70], byteorder='little')
    curr_dict['discharge_Wh'] = discharge_Wh * current_scaling_factor

    # For backwards compatibility...
    curr_dict['capacity_Ah'] = max(charge_Ah, discharge_Ah) * current_scaling_factor
    curr_dict['energy_Wh'] = max(charge_Wh, discharge_Wh) * current_scaling_factor

    # Time and date
    # Instead of storing as a timestamp, new NDA files store the date and time in individual
    # bytes.  This "timestamp" is only accurate to the nearest second.  All time-sensitive
    # calculations should be performed on the "time_in_step" parameter.
    year = int.from_bytes(byte_stream[70:72], byteorder='little')
    curr_dict['year'] = year
    # month = int.from_bytes(byte_stream[72:73],byteorder='little')
    month = byte_stream[72]
    curr_dict['month'] = month
    # day = int.from_bytes(byte_stream[73:74],byteorder='little')
    day = byte_stream[73]
    curr_dict['day'] = day
    # hour = int.from_bytes(byte_stream[74:75],byteorder='little')
    hour = byte_stream[74]
    curr_dict['hour'] = hour
    # minute = int.from_bytes(byte_stream[75:76],byteorder='little')
    minute = byte_stream[75]
    curr_dict['minute'] = minute
    # second = int.from_bytes(byte_stream[76:77],byteorder='little')
    second = byte_stream[76]
    curr_dict['second'] = second
    if not year == 0:
        timestamp = datetime.datetime(year, month, day, hour, minute, second)
    else:
        timestamp = datetime.datetime(2018, 1, 1, 1, 1, 1)
    curr_dict['timestamp'] = timestamp.strftime('%Y-%m-%d %H:%M:%S')

    # Raw binary available for bugfixing purposes only
    if out_raw_binary:
        raw_bin = str(binascii.hexlify(bytearray(byte_stream)))
        raw_bin = ' '.join(a + b for a, b in zip(raw_bin[::2], raw_bin[1::2]))
        curr_dict['RAW_BIN'] = raw_bin

    return curr_dict

def get_new_step_name(step_type_id):
    if step_type_id == 1:
        return "CC_Chg"
    elif step_type_id == 2:
        return "CC_Dchg"
    elif step_type_id == 3:
        return "CV_Chg"
    elif step_type_id == 4:
        return "Rest"
    elif step_type_id == 6:
        return "End"
    elif step_type_id == 7:
        return "CCCV_Chg"
    elif step_type_id == 19:
        return "CV_Dchg"
    elif step_type_id == 20:
        return "CCCV_Dchg"
    else:
        return str(step_type_id)

def process_datapoint_list(datapoint_list):
    """Mimics old data processor.  Will use this until I have time to create new object oriented analyzer."""
    current_cycle = {}
    current_cycle['datapoints'] = []
    cycle_list = [current_cycle]

    # variables for cumulative data
    test_time = 0
    cycle_start = 0
    cum_Ah = 0  # Used to track the cumulative capacity throughout all cycles.
    cum_Wh = 0  # Used to track the cumulative energy throughout all cycles.
    cyc_chg_Ah = 0  # Used to track the capacity within one cycle
    cyc_chg_Wh = 0  # Used to track the energy within one cycle
    cyc_dch_Ah = 0  # Used to track the capacity within one cycle
    cyc_dch_Wh = 0  # Used to track the energy within one cycle
    step_num = None
    current_step = None
    cycle_id = None
    charging = False

    for datapoint in datapoint_list:
        # If this is the first good point, initialize a bunch of stuff...
        if not cycle_id:
            cycle_id = 1
            step_num = 1
            current_step = datapoint.get('step_id')
            charging = (datapoint.get('step_type_id') in CHARGING_STEP_TYPE_IDS)
            # Special case when first step is a discharge
            # TODO: Handle case when first step is a rest
            if not charging:
                current_cycle['chg_time'] = 0
                current_cycle['chg_Ah'] = 0
                current_cycle['chg_Wh'] = 0
                # TODO: Initialize anything else...

        # If this is a new step ...
        #   Option 1: We've been charging and next step is not discharging
        #       Do not increment cycle counter.  Update cumulative counters.  Process as normal.
        #   Option 2: We've been charging and next step is discharging
        #       Do not increment cycle counter.  Update cumulative counters.  Process as normal.
        #   Option 3: We've been discharging and next step is not charging
        #       Do not increment cycle counter.  Update cumulative counters.  Process as normal.
        #   Option 4: We've been discharging and next step is charging
        #       Increment cycle counter.  Reset all cycle variables.
        if current_step != datapoint.get('step_id'):
            # Increment step number
            step_num += 1
            # Set new current step
            current_step = datapoint.get('step_id')
            # Update cumulative test time
            test_time += current_cycle['datapoints'][-1]['time_in_step']

            # New handling of rest steps.
            # TODO: Refactor this whole fucking section
            # if datapoint.get('step_type_id') not in DISCHARGING_STEP_TYPE_IDS:

            if (charging):
                if (datapoint.get('step_type_id') not in DISCHARGING_STEP_TYPE_IDS):
                    # We were charging and we're not discharging = stay in charge
                    cum_Ah += current_cycle['datapoints'][-1]['capacity_Ah']
                    cum_Wh += current_cycle['datapoints'][-1]['energy_Wh']
                    cyc_chg_Ah += current_cycle['datapoints'][-1]['capacity_Ah']
                    cyc_chg_Wh += current_cycle['datapoints'][-1]['energy_Wh']
                    # print("Charge Step {} Ended, staying in Charge Step {}".format(step_num-1,step_num))
                else:
                    # We were charging and now we're discharging = switch to discharge
                    # Do all the same stuff as staying in charge? Also update the cycle charge time.
                    cum_Ah += current_cycle['datapoints'][-1]['capacity_Ah']
                    cum_Wh += current_cycle['datapoints'][-1]['energy_Wh']
                    cyc_chg_Ah += current_cycle['datapoints'][-1]['capacity_Ah']
                    cyc_chg_Wh += current_cycle['datapoints'][-1]['energy_Wh']
                    current_cycle['chg_time'] = (test_time - cycle_start)
                    # print("Charge Step {} Ended, moving to Discharge Step {}".format(step_num-1,step_num))
            elif (not charging):
                if (datapoint.get('step_type_id') not in CHARGING_STEP_TYPE_IDS):
                    # We were discharging and we're not charging = stay in discharge
                    cum_Ah -= current_cycle['datapoints'][-1]['capacity_Ah']
                    cum_Wh -= current_cycle['datapoints'][-1]['energy_Wh']
                    # cyc_chg_Ah -= current_cycle['datapoints'][-1]['capacity_Ah']
                    # cyc_chg_Wh -= current_cycle['datapoints'][-1]['energy_Wh']
                    cyc_dch_Ah += current_cycle['datapoints'][-1]['capacity_Ah']
                    cyc_dch_Wh += current_cycle['datapoints'][-1]['energy_Wh']
                    # print("Discharge Step {} Ended, staying in Discharge Step {}".format(step_num-1,step_num))
                else:
                    # We were discharging and we're now charging = end of cycle
                    # Last stuff for the current cycle
                    cum_Ah -= current_cycle['datapoints'][-1]['capacity_Ah']
                    cum_Wh -= current_cycle['datapoints'][-1]['energy_Wh']
                    current_cycle['dch_time'] = (test_time - cycle_start) - current_cycle.get('chg_time', 0)
                    current_cycle['cycle_time'] = (test_time - cycle_start)
                    # Reset cycle stuff for new cycle
                    cyc_chg_Ah = 0
                    cyc_chg_Wh = 0
                    cyc_dch_Ah = 0
                    cyc_dch_Wh = 0
                    cycle_id += 1
                    cycle_start = test_time
                    current_cycle = {}
                    current_cycle["datapoints"] = []
                    cycle_list.append(current_cycle)
                    # print("End of Cycle {}".format(cycle_id))
            # 2019.06.19 - Check for new step_id being a rest
            if datapoint.get('step_type_id') != 4:
                charging = (datapoint.get('step_type_id') in CHARGING_STEP_TYPE_IDS)

        # Set the step number and cycle number on the datapoint level
        # TODO: With slightly more complicated data structure, memory use can be greatly reduced.
        datapoint['step_num'] = step_num
        datapoint['cycle_id'] = cycle_id
        datapoint['test_time'] = test_time + datapoint.get('time_in_step', 0)
        if charging:
            datapoint['cum_Ah'] = cum_Ah + datapoint.get('capacity_Ah', 0)
            datapoint['cum_Wh'] = cum_Wh + datapoint.get('energy_Wh', 0)
            datapoint['chg_Ah'] = cyc_chg_Ah + datapoint.get('capacity_Ah', 0)
            datapoint['chg_Wh'] = cyc_chg_Wh + datapoint.get('energy_Wh', 0)
            datapoint['dch_Ah'] = 0  # should always be zero when charging for Chg->Dch cycles
            datapoint['dch_Wh'] = 0  # should always be zero when charging for Chg->Dch cycles
        else:
            datapoint['cum_Ah'] = cum_Ah - datapoint.get('capacity_Ah', 0)
            datapoint['cum_Wh'] = cum_Wh - datapoint.get('energy_Wh', 0)
            # datapoint['chg_Ah'] = cyc_Ah
            # While discharging, Chg_Ah = previous datapoint's Chg_Ah
            # 2018.08.09 - The following line fails when the first step is a discharge.  Instead of looking at the
            # most recent datapoint, we'll now pull chg_Ah/chg_Wh from the cycle.
            # EXCEPT THAT WE CAN'T

            # Hacky way to handle rest step
            # This will probably break if the first step is a rest
            if datapoint.get('step_type_id', 0) == 4:
                # This is a rest
                if len(current_cycle['datapoints']) == 0:
                    # This is the first datapoint for this cycle
                    datapoint['chg_Ah'] = 0
                    datapoint['chg_Wh'] = 0
                    datapoint['dch_Ah'] = 0
                    datapoint['dch_Wh'] = 0
                else:
                    datapoint['chg_Ah'] = current_cycle['datapoints'][-1].get('chg_Ah', 0)
                    datapoint['chg_Wh'] = current_cycle['datapoints'][-1].get('chg_Wh', 0)
                    datapoint['dch_Ah'] = current_cycle['datapoints'][-1].get('dch_Ah', 0)
                    datapoint['dch_Wh'] = current_cycle['datapoints'][-1].get('dch_Wh', 0)
            else:
                # If this is the first datapoint of the cycle
                if len(current_cycle['datapoints']) == 0:
                    datapoint['chg_Ah'] = 0
                    datapoint['chg_Wh'] = 0
                    datapoint['dch_Ah'] = 0
                    datapoint['dch_Wh'] = 0
                else:
                    datapoint['chg_Ah'] = current_cycle['datapoints'][-1].get('chg_Ah', 0)
                    datapoint['chg_Wh'] = current_cycle['datapoints'][-1].get('chg_Wh', 0)
                # datapoint['chg_Ah'] = current_cycle.get('chg_Ah', 0)
                # datapoint['chg_Wh'] = current_cycle.get('chg_Wh', 0)
                datapoint['dch_Ah'] = cyc_dch_Ah + datapoint.get('capacity_Ah', 0)
                datapoint['dch_Wh'] = cyc_dch_Wh + datapoint.get('energy_Wh', 0)
        # Add Datapoint to the current cycle
        current_cycle['datapoints'].append(datapoint)

    return cycle_list

def process_cycle_list_new(cycle_list, normalize_to_cycle=1, electrode_area=np.nan):
    # Lists are passed by reference?  Kind of?
    # TODO: Error checking
    if normalize_to_cycle > len(cycle_list):
        print("Error: cycle_list length is less than normalizing cycle.")
        norm_dch_Ah = 0.0
    else:
        norm_dch_Ah = cycle_list[normalize_to_cycle - 1]['datapoints'][-1]['dch_Ah'] / 360000000
        # print("norm_dch_Ah is: " + str(norm_dch_Ah))
    # Assume first cycle is C/20 and find the first C/3 cycle
    ref_cycle_norm_ah = cycle_list[0]['datapoints'][-1]['dch_Ah'] / 360000000
    reg_cycle_norm_ah = get_first_reg_dch(cycle_list)
    # ref_cycle_nums = get_reference_cycle_list(cycle_list)
    ref_cycle_nums = get_reference_cycle_list_by_current(cycle_list, current_threshold=20000)

    for cycle in cycle_list:
        last_dp = cycle['datapoints'][-1]
        cycle['cycle_id'] = last_dp.get('cycle_id', 0)
        cycle['chg_Ah'] = last_dp.get('chg_Ah', 0) / 360000000
        cycle['dch_Ah'] = last_dp.get('dch_Ah', 0) / 360000000
        cycle['chg_Wh'] = last_dp.get('chg_Wh', 0) / 360000000
        cycle['dch_Wh'] = last_dp.get('dch_Wh', 0) / 360000000

        # If the chg_Ah is zero, then chg_Wh is zero
        if cycle['chg_Ah'] == 0:
            cycle['CE'] = 0
            cycle['chg_V'] = 0
        else:
            cycle['CE'] = cycle['dch_Ah'] / cycle['chg_Ah']
            cycle['chg_V'] = last_dp.get('chg_Wh', 0) / last_dp.get('chg_Ah', 0)
        if cycle['dch_Ah'] == 0:
            cycle['dch_V'] = 0
        else:
            cycle['dch_V'] = last_dp.get('dch_Wh', 0) / last_dp.get('dch_Ah', 0)
        cycle['delta_V'] = cycle['chg_V'] - cycle['dch_V']
        cycle['chg_mAh'] = cycle['chg_Ah'] * 1000
        cycle['dch_mAh'] = cycle['dch_Ah'] * 1000

        # normalizing stuff
        try:
            cycle['norm_dch'] = cycle['dch_Ah'] / norm_dch_Ah
            if cycle['cycle_id'] in ref_cycle_nums:
                cycle['ref_norm_dch'] = cycle['dch_Ah'] / ref_cycle_norm_ah
            else:
                cycle['reg_norm_dch'] = cycle['dch_Ah'] / reg_cycle_norm_ah
        except (ZeroDivisionError, TypeError, NameError):
            cycle['norm_dch'] = None

        if not np.isnan(electrode_area):
            # TODO: What units do we want? mAh/cm^2?
            cycle['area_cap'] = 1000 * cycle['dch_Ah'] / electrode_area

def get_first_reg_dch(cycle_list, cycle_time=14400):
    for cycle in cycle_list:
        if cycle.get('dch_time', 0) < cycle_time:
            return cycle['datapoints'][-1]['dch_Ah'] / 360000000
    return 0.0

def get_reference_cycle_list(cycle_list):
    """Given a cycle list, return a list of all cycles whose discharge time is greater than 4 hours.
    Assumes the usual C/20, C/3 Cycling protocol."""
    found_ref_cycles = []
    for cycle in cycle_list:
        if cycle.get('dch_time', 0) > 4 * 3600:
            found_ref_cycles.append(cycle['datapoints'][-1]['cycle_id'])
    return found_ref_cycles

def get_reference_cycle_list_by_current(cycle_list, current_threshold=2000):
    """Given a cycle list, return a list of all cycles whose discharge current is less than 200 mA."""
    found_ref_cycles = []
    for cycle in cycle_list:
        cycle_current = abs(cycle['datapoints'][-1].get('current', 0))
        if cycle_current == 0.0:
            continue
        elif cycle_current < current_threshold:
            found_ref_cycles.append(cycle['datapoints'][-1]['cycle_id'])
    return found_ref_cycles

def process_datapoints(cycle_list):
    for cycle in cycle_list:
        cycle['datapoints'][0]['dV'] = 0
        cycle['datapoints'][0]['dQ'] = 0
        cycle['datapoints'][0]['dVdQ'] = 0
        cycle['datapoints'][0]['dQdV'] = 0
        for last_dp, curr_dp, next_dp in zip(cycle['datapoints'], cycle['datapoints'][1:], cycle['datapoints'][2:]):
            curr_dp['dV'] = next_dp['voltage'] - last_dp['voltage']
            curr_dp['dQ'] = next_dp['cum_Ah'] - last_dp['cum_Ah']
            if curr_dp['step_type_id'] in DISCHARGING_STEP_TYPE_IDS:
                current_adj = -1
            else:
                current_adj = 1
            if next_dp['voltage'] - last_dp['voltage']:
                curr_dp['dQdV'] = current_adj * (10000 * (next_dp['cum_Ah'] - last_dp['cum_Ah']) / (
                        next_dp['voltage'] - last_dp['voltage'])) / 360000000
            else:
                curr_dp['dQdV'] = ''
            if next_dp['cum_Ah'] - last_dp['cum_Ah']:
                curr_dp['dVdQ'] = current_adj * (360000000 * (next_dp['voltage'] - last_dp['voltage']) / (
                        next_dp['cum_Ah'] - last_dp['cum_Ah'])) / 10000
            else:
                curr_dp['dVdQ'] = ''

def save_cycle_data(cycle_list, out_filename, csv_line_order=['cycle_id', 'chg_Ah', 'dch_Ah', 'CE',
                                                              'chg_Wh', 'dch_Wh', 'chg_V', 'dch_V', 'delta_V',
                                                              'norm_dch', 'chg_time', 'dch_time', 'cycle_time',
                                                              'chg_mAh', 'dch_mAh'],
                    omit_last_cycle=False, electrode_area=None):
    # Bunch of path stuff...
    out_file_path, out_file_basename = os.path.split(out_filename)
    out_file_rootname, out_file_ext = os.path.splitext(out_file_basename)
    # Protection for legacy file lists...
    if out_file_ext != ".csv":
        out_file_rootname += out_file_ext
        out_file_ext = ".csv"

    out_file_basename = out_file_rootname + " (Cycle Data)" + out_file_ext
    out_filename = os.path.join(out_file_path, out_file_basename)
    if not os.path.exists(os.path.dirname(out_filename)):
        try:
            os.makedirs(os.path.dirname(out_filename))
        except OSError as exc:  # Guard against race condition
            if exc.errno != errno.EEXIST:
                raise

    out_file = open(out_filename, 'w', newline="\n", encoding="utf-8")
    csv_out = csv.writer(out_file, delimiter=',', quotechar="\"")
    csv_out.writerow(csv_line_order)
    if omit_last_cycle: temp_cycle = cycle_list.pop()
    for cycle in cycle_list:
        csv_line = []
        for key in csv_line_order:
            if '_time' in key:
                seconds = cycle.get(key, 0)
                m, s = divmod(seconds, 60)
                h, m = divmod(m, 60)
                csv_line.append("%d:%02d:%02d" % (h, m, s))
                # csv_line.append("{:0.0f}:{:02.0f}:{:0.3f}".format(h, m, s))
            elif '_mAh' in key:
                # Hacky way to get mAh
                actual_key = key.replace("_mAh", "_Ah")
                csv_line.append(cycle.get(actual_key, 0) * 1000)
            else:
                csv_line.append(cycle.get(key, None))

        csv_out.writerow(csv_line)
    out_file.close()
    if omit_last_cycle: cycle_list.append(temp_cycle)

def get_norm_death(cycle_list, death_percent=0.8, consecutive_cycles=2):
    count = 0
    potential_found = []
    for cycle in cycle_list[:-1]:
        try:
            if cycle['norm_dch'] != None and cycle['norm_dch'] < death_percent:
                count += 1
                potential_found.append(cycle['cycle_id'])
                if count >= consecutive_cycles:
                    return potential_found[0]
            else:
                count = 0
                potential_found.clear()
        except KeyError:
            continue
    if count > 0:
        return potential_found[0]
    else:
        return np.nan

def get_reg_death(cycle_list, death_percent=0.8, consecutive_cycles=2):
    count = 0
    potential_found = []
    for cycle in cycle_list[:-1]:
        try:
            if cycle['reg_norm_dch'] < death_percent:
                count += 1
                potential_found.append(cycle['cycle_id'])
                if count >= consecutive_cycles:
                    return potential_found[0]
            else:
                count = 0
                potential_found.clear()
        except KeyError:
            continue
    if count > 0:
        return potential_found[0]
    else:
        return np.nan

def get_ref_death(cycle_list, death_percent=0.8, consecutive_cycles=2):
    count = 0
    potential_found = []
    for cycle in cycle_list[:-1]:
        try:
            if cycle['ref_norm_dch'] < death_percent:
                count += 1
                potential_found.append(cycle['cycle_id'])
                if count >= consecutive_cycles:
                    return potential_found[0]
            else:
                count = 0
                potential_found.clear()
        except KeyError:
            continue
    if count > 0:
        return potential_found[0]
    else:
        return np.nan

def save_datapoints(cycle_list, out_filename, csv_line_order=['record_id', 'test_time', 'timestamp',
                                                              'time_in_step', 'step_num', 'cycle_id', 'current',
                                                              'voltage', 'chg_Ah', 'dch_Ah',
                                                              'chg_Wh', 'dch_Wh', 'cum_Ah', 'cum_Wh', 'dQdV', 'dVdQ',
                                                              'chg_mAh', 'dch_mAh', 'cum_mAh'],
                    max_rows=1000000, formation=False):
    row_count = 0
    file_count = 0

    # Bunch of path stuff...
    out_file_path, out_file_basename = os.path.split(out_filename)
    out_file_rootname, out_file_ext = os.path.splitext(out_file_basename)
    # Protection for legacy file lists...
    if out_file_ext != ".csv":
        out_file_rootname += out_file_ext
        out_file_ext = ".csv"

    if formation:
        out_file_basename = out_file_rootname + " (Formation)" + out_file_ext
    else:
        out_file_basename = out_file_rootname + " (Data Points)" + out_file_ext

    out_filename = os.path.join(out_file_path, out_file_basename)
    if not os.path.exists(os.path.dirname(out_filename)):
        try:
            os.makedirs(os.path.dirname(out_filename))
        except OSError as exc:  # Guard against race condition
            if exc.errno != errno.EEXIST:
                raise

    outfile = open(out_filename, 'w', newline="\n", encoding="utf-8")
    csv_out = csv.writer(outfile, delimiter=',', quotechar="\"")
    csv_out.writerow(csv_line_order)
    for cycle in cycle_list:
        for dp in cycle['datapoints']:
            if row_count > max_rows:
                row_count = 0
                file_count += 1
                outfile.close()
                out_file_basename = out_file_rootname + "_{}".format(file_count) + out_file_ext
                out_filename = os.path.join(out_file_path, out_file_basename)
                outfile = open(out_filename, 'w', newline="\n", encoding="utf-8")
                csv_out = csv.writer(outfile, delimiter=',', quotechar="\"")
                csv_out.writerow(csv_line_order)

            csv_line = []
            for key in csv_line_order:
                if (key == 'time_in_step') or (key == 'test_time'):
                    seconds = dp.get(key)
                    m, s = divmod(seconds, 60)
                    h, m = divmod(m, 60)
                    # csv_line.append("%d:%02d:%02d" % (h, m, s))
                    csv_line.append("{:0.0f}:{:02.0f}:{:0.3f}".format(h, m, s))
                elif key == 'voltage':
                    csv_line.append(dp.get(key, 0) / 10000)
                elif key == 'current':
                    csv_line.append(dp.get(key, 0) / 100000)
                elif ('_Ah' in key) or ('_Wh' in key):
                    csv_line.append(dp.get(key, 0) / 360000000)
                elif '_mAh' in key:
                    # Quick and dirty way to get mAh columns
                    actual_key = key.replace("_mAh", "_Ah")
                    csv_line.append(dp.get(actual_key, 0) / 360000)
                else:
                    csv_line.append(str(dp.get(key)))
            csv_out.writerow(csv_line)
            row_count += 1
    outfile.close()


def process_long_term_cycling_new(csv_filename, out_path, nda_path, force_processing=False, output_datapoints=True):
    print("running")

    files_to_process = pd.read_csv(csv_filename)

    for index, row in files_to_process.iterrows():
        current_nda_filename = os.path.join(nda_path, str(row['nda_file']))
        if os.path.isfile(current_nda_filename):
            print('Processing: ', row['nda_file'])
            file_size = os.path.getsize(current_nda_filename)
            # New file last modified stuff
            file_last_modified = os.path.getmtime(current_nda_filename)
            # print(pd.to_datetime(file_last_modified,unit='s'))
            files_to_process.at[index, 'file_last_modified'] = pd.to_datetime(file_last_modified, unit='s')

            # print("file_size = {0}, row.get('nda_file_size',0) = {1}".format(file_size, row.get('nda_file_size', 0)))
            # If there is no stored nda file_size or if file is same size as previous pass
            if pd.isna(row.get('nda_file_size', 0)) or file_size != row.get('nda_file_size', 0) or force_processing:
                files_to_process.at[index, 'nda_file_size'] = file_size
                start_byte = find_start_byte(current_nda_filename)
                current_datapoint_list = process_nda(current_nda_filename, start_byte)
                current_cycle_list = process_datapoint_list(current_datapoint_list)
                normalize_cycle = row.get('normalize_cycle', 1)
                elec_area = row.get('electrode_area', np.nan)
                process_cycle_list_new(current_cycle_list, normalize_to_cycle=normalize_cycle, electrode_area=elec_area)
                process_datapoints(current_cycle_list)
                save_cycle_data(current_cycle_list, os.path.join(out_path, row['out_file']), omit_last_cycle=True)
                if not np.isnan(elec_area):
                    save_cycle_data(current_cycle_list, os.path.join(out_path, row['out_file']),
                                    csv_line_order=['cycle_id', 'chg_Ah', 'dch_Ah', 'CE', 'chg_Wh', 'dch_Wh', 'chg_V',
                                                    'dch_V', 'delta_V', 'norm_dch', 'chg_time', 'dch_time',
                                                    'cycle_time', 'area_cap'], omit_last_cycle=True)
                else:
                    save_cycle_data(current_cycle_list, os.path.join(out_path, row['out_file']), omit_last_cycle=True,
                                    csv_line_order=['cycle_id', 'chg_Ah','chg_mAh', 'dch_Ah', 'dch_mAh', 'CE', 'chg_Wh', 'dch_Wh', 'chg_V',
                                                    'dch_V', 'delta_V', 'norm_dch', 'chg_time', 'dch_time',
                                                    'cycle_time', 'reg_norm_dch', 'ref_norm_dch'])

                # Output last cycle number and last reference cycle
                files_to_process.at[index, 'last_cycle_number'] = len(current_cycle_list)
                try:  # Prevent an IndexError if processing a cell with not enough data.
                    files_to_process.at[index, 'last_norm_dch'] = current_cycle_list[-2]['norm_dch']
                except:
                    pass
                files_to_process.at[index, 'norm_death'] = get_norm_death(current_cycle_list)
                files_to_process.at[index, 'reg_death'] = get_reg_death(current_cycle_list)
                files_to_process.at[index, 'ref_death'] = get_ref_death(current_cycle_list)

                # Debug
                if output_datapoints:
                    save_datapoints(current_cycle_list, os.path.join(out_path, row['out_file']))
                print('Finished: ', row['nda_file'])
            else:
                print('Error: NDA file size has not changed since file last processed.  Skipping...')

        else:
            print('Error: Couldn\'t find file ' + str(row['nda_file']))
            if os.path.isfile(nda_path + 'Finished\\' + str(row['nda_file'])):
                print('   File ' + row['nda_file'] + ' is in Finished folder')

    files_to_process.to_csv(csv_filename, index=False)


def process_formation(csv_filename, out_path, nda_path):
    files_to_process = pd.read_csv(csv_filename)

    for index, row in files_to_process.iterrows():
        if row['nda_file'] == "Novonix":
            print("Skipping Novonix cell")
        else:
            # TODO: Check for blank lines
            current_nda_filename = os.path.join(nda_path, str(row['nda_file']))
            if os.path.isfile(current_nda_filename):
                print("Processing: ", row['nda_file'])
                start_byte = find_start_byte(current_nda_filename)
                current_datapoint_list = process_nda(current_nda_filename, start_byte)
                current_cycle_list = process_datapoint_list(current_datapoint_list)
                process_datapoints(current_cycle_list)
                process_cycle_list_new(current_cycle_list)

                save_datapoints(current_cycle_list, os.path.join(out_path, row['out_file']), formation=True)
                # Output cycle data if necessary
                # save_cycle_data(current_cycle_list, os.path.join(out_path, row['out_file']), omit_last_cycle=False)

                chg_Ah, dch_Ah = current_cycle_list[0]['chg_Ah'], current_cycle_list[0]['dch_Ah']
                chg_Wh, dch_Wh = current_cycle_list[0]['chg_Wh'], current_cycle_list[0]['dch_Wh']
                chg_V, dch_V = current_cycle_list[0]['chg_V'], current_cycle_list[0]['dch_V']
                # For cells where cycle 2 is actually the first cycle
                # chg_Ah, dch_Ah = current_cycle_list[1]['chg_Ah'], current_cycle_list[1]['dch_Ah']
                files_to_process.at[index, 'chg_Ah'] = chg_Ah
                files_to_process.at[index, 'dch_Ah'] = dch_Ah
                files_to_process.at[index, 'chg_mAh'] = chg_Ah * 1000
                files_to_process.at[index, 'dch_mAh'] = dch_Ah * 1000
                if chg_Ah != 0:
                    files_to_process.at[index, 'fce'] = dch_Ah / chg_Ah
                files_to_process.at[index, 'chg_Wh'] = chg_Wh
                files_to_process.at[index, 'dch_Wh'] = dch_Wh
                files_to_process.at[index, 'chg_V'] = chg_V
                files_to_process.at[index, 'dch_V'] = dch_V
            else:
                print('Error: Couldn\'t find file ' + str(row['nda_file']))
    files_to_process.to_csv(csv_filename, index=False)


def process_olip(csv_filename, out_path, nda_path, cycle_num):
    files_to_process = pd.read_csv(csv_filename)

    for index, row in files_to_process.iterrows():
        current_nda_filename = os.path.join(nda_path, row['nda_file'])
        if os.path.isfile(current_nda_filename):
            print("Processing: ", row['nda_file'])
            start_byte = find_start_byte(current_nda_filename)
            current_datapoint_list = process_nda(current_nda_filename, start_byte)
            current_cycle_list = process_datapoint_list(current_datapoint_list)
            normalize_cycle = row.get('normalize_cycle', cycle_num)
            print("Normalize Cycle = {}".format(normalize_cycle))
            process_cycle_list_new(current_cycle_list, normalize_to_cycle=normalize_cycle)
            save_cycle_data(current_cycle_list, os.path.join(out_path, row['out_file']))

            save_datapoints(current_cycle_list, os.path.join(out_path, row['out_file']))
            # Try to save the data points for just the first full cycle and the second to last cycle.
            # save_datapoints([current_cycle_list[e] for e in (1,-2)], os.path.join(out_path, row['out_file']))

            if len(current_cycle_list) > 2:
                first_ref_dch_Ah = current_cycle_list[normalize_cycle - 0]['dch_Ah']
                last_ref_dch_Ah = current_cycle_list[-2]['dch_Ah']
                last_norm_dch = last_ref_dch_Ah / first_ref_dch_Ah

            else:
                first_ref_dch_Ah = np.nan
                last_ref_dch_Ah = np.nan
                last_norm_dch = np.nan
            files_to_process.at[index, 'first_ref_dch_Ah'] = first_ref_dch_Ah
            files_to_process.at[index, 'last_ref_dch_Ah'] = last_ref_dch_Ah
            files_to_process.at[index, 'last_norm_dch'] = last_norm_dch

        else:
            print('Error: Couldn\'t find file ' + row['nda_file'])
    files_to_process.to_csv(csv_filename, index=False)