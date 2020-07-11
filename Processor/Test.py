from tkinter import *
from tkinter import filedialog

import tkinter.font as font

# def get_file_path():
# 	root = Tk()
# 	root.withdraw() # hides tk window

# 	path_name = filedialog.askopenfilename()

# 	root.quit() # exits without destroying widgets

# 	return path_name

# def get_dir_path():
# 	root = Tk()
# 	root.withdraw() # hides tk window

# 	dir_path = filedialog.askdirectory()

# 	root.quit()
# 	return dir_path

# def formation():
# 	global


root = Tk(className=" Choose Data Processing Program")
# root.geometry("400x400")

myFont = font.Font(size=25)

b1 = Button(root, command=root.quit, text="Process Cycling", height="2", width="15")
b2 = Button(root, command=root.quit, text="Process Formation", height="2", width="15")

b1['font'] = myFont
b2['font'] = myFont

b1.pack(side=LEFT, padx=25, pady=25)
b2.pack(side=LEFT, padx=25, pady=25)

root.mainloop()
