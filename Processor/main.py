import Processor
from tkinter import *
from tkinter import filedialog

import tkinter.font as font

root = Tk(className=" Choose Data Processing Program")

myFont = font.Font(size=25)

def exec_cycling_proc():
    butt_select = "Cycling"
    csv_filename = filedialog.askopenfilename(title='Pick Your Base CSV File.')
    out_path = filedialog.askdirectory(title='Where Do You Want Your Processed Data?')
    nda_path = filedialog.askdirectory(title='Where Are Your NDA Files?')

    if (csv_filename != '' and out_path != '' and nda_path != ''):
        Processor.process_long_term_cycling_new(csv_filename, out_path, nda_path)
        root.destroy()
    else:
    	print("Ya Jibroney'd it")
    	root.destroy()

def exec_formation_proc():
    butt_select = "Cycling"
    csv_filename = filedialog.askopenfilename(title='Pick Your Base CSV File.')
    out_path = filedialog.askdirectory(title='Where Do You Want Your Processed Data?')
    nda_path = filedialog.askdirectory(title='Where Are Your NDA Files?')

    if (csv_filename != '' and out_path != '' and nda_path != ''):
        Processor.process_formation(csv_filename, out_path, nda_path)
        root.destroy()
    else:
    	print("Ya Jibroney'd it")
    	root.destroy()

b1 = Button(root, command=exec_cycling_proc, text="Process Cycling", height="2", width="15")
b2 = Button(root, command=exec_formation_proc, text="Process Formation", height="2", width="15")

b1['font'] = myFont
b2['font'] = myFont

b1.pack(side=LEFT, padx=25, pady=25)
b2.pack(side=LEFT, padx=25, pady=25)

root.mainloop()
