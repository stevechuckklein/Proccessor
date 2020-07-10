from tkinter import *
from tkinter import filedialog

def get_file_path():
	root = Tk()
	root.withdraw() # hides tk window

	path_name = filedialog.askopenfilename()

	root.quit() # exits without destroying widgets

	return path_name

def get_dir_path():
	root = Tk()
	root.withdraw() # hides tk window

	dir_path = filedialog.askdirectory()

	root.quit()
	return dir_path


file_ex = filedialog.askopenfilename(title='Pick Your CSV')
print(file_ex)