import datetime

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

def find_start_byte(filename):
    with open(filename, "rb") as f:
        f.seek(64)
        file_chunk = f.read(4)  # Changed from 2 to 4 bytes
        start_index = int.from_bytes(file_chunk, byteorder='little')
    return start_index

# Processes an NDA file.  Returns the full data structure of processed data.
# File output is now handled by the calling function.
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

path = "U:\\Cell Testing\\Cycle Data\\Raw Data Files\\240014-7-2-2818573436.nda"
byte_one = find_start_byte(path)
sample = process_nda(path, byte_one)

# print(sample);

def txt_out(dict):
    with open('sample.txt','w') as f:
        for item in dict:
            print(item, file=f)

txt_out(sample)