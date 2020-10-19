import meat.processor_functions as proc
from tkinter import *
from tkinter import filedialog

import tkinter.font as font

# Base Pop up window
root = Tk(className="Choose Data Processing Program")

# Controls Size of Button Font
myFont = font.Font(size=25)

def exec_cycling_proc(): # Function ran if Process Cycling is chosen
    # Get the correct file locations
    csv_filename = filedialog.askopenfilename(initialdir='U:\\Cell Testing\\Cycle Data', title='Pick Your Base CSV File.')
    out_path = filedialog.askdirectory(initialdir='U:\\Cell Testing\\Cycle Data', title='Where Do You Want Your Processed Data?')
    nda_path = filedialog.askdirectory(initialdir='U:\\Cell Testing\\Cycle Data', title='Where Are Your NDA Files?')

    # If given a location for every needed file, run the processor
    # otherwise no processing and give an error message
    if (csv_filename != '' and out_path != '' and nda_path != ''):

        proc.process_long_term_cycling_new(csv_filename, out_path, nda_path)
        root.destroy()
        man_close = input("Press Close to Exit")
    else:
        print("Ya Jibroney'd it")
        root.destroy()
        man_close = input("Press Close to Exit")

def exec_formation_proc():

    csv_filename = filedialog.askopenfilename(initialdir='U:\\Cell Testing\\Formation Data', title='Pick Your Base CSV File.')
    out_path = filedialog.askdirectory(initialdir='U:\\Cell Testing\\Formation Data', title='Where Do You Want Your Processed Data?')
    nda_path = filedialog.askdirectory(initialdir='U:\\Cell Testing\\Formation Data', title='Where Are Your NDA Files?')

    if (csv_filename != '' and out_path != '' and nda_path != ''):
        root.destroy()
        proc.process_formation(csv_filename, out_path, nda_path)
        man_close = input("Press Close to Exit")
    else:
        root.destroy()
        print("Ya Jibroney'd it")
        man_close = input("Press Close to Exit")

def exec_olip_proc():

    csv_filename = filedialog.askopenfilename(initialdir='U:\\Cell Testing\\OLiP Data\\Processed Data', title='Pick Your Base CSV File.')
    out_path = filedialog.askdirectory(initialdir='U:\\Cell Testing\\OLiP Data\\Processed Data', title='Where Do You Want Your Processed Data?')
    nda_path = filedialog.askdirectory(initialdir='U:\\Cell Testing\\OLiP Data\\Processed Data', title='Where Are Your NDA Files?')

    if (csv_filename != '' and out_path != '' and nda_path != ''):
        root.destroy()
        cycle_num = int(input("What cycle would you like to normalize to... ") or "2")
        proc.process_olip(csv_filename, out_path, nda_path, cycle_num)
        man_close = input("Press Close to Exit")
    else:
        root.destroy()
        print("Ya Jibroney'd it")
        man_close = input("Press Close to Exit")

b1 = Button(root, command=exec_cycling_proc, text="Process Cycling", height="2", width="15")
b2 = Button(root, command=exec_formation_proc, text="Process Formation", height="2", width="15")
b3 = Button(root, command=exec_olip_proc, text= "Process\nNormalized Cycling", height="2", width="15")

b1['font'] = myFont
b2['font'] = myFont
b3['font'] = myFont

b1.pack(side=LEFT, padx=25, pady=25)
b2.pack(side=LEFT, padx=25, pady=25)
b3.pack(side=LEFT, padx=25, pady=25)

root.mainloop()