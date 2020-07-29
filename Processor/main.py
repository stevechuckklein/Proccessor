import meat.processor_functions as proc
from tkinter import *
from tkinter import filedialog

import tkinter.font as font

root = Tk(className=" Choose Data Processing Program")

myFont = font.Font(size=25)

def exec_cycling_proc():

    csv_filename = filedialog.askopenfilename(initialdir='U:\\Cell Testing\\Cycle Data', title='Pick Your Base CSV File.')
    out_path = filedialog.askdirectory(initialdir='U:\\Cell Testing\\Cycle Data', title='Where Do You Want Your Processed Data?')
    nda_path = filedialog.askdirectory(initialdir='U:\\Cell Testing\\Cycle Data', title='Where Are Your NDA Files?')

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

b1 = Button(root, command=exec_cycling_proc, text="Process Cycling", height="2", width="15")
b2 = Button(root, command=exec_formation_proc, text="Process Formation", height="2", width="15")

b1['font'] = myFont
b2['font'] = myFont

b1.pack(side=LEFT, padx=25, pady=25)
b2.pack(side=LEFT, padx=25, pady=25)

root.mainloop()