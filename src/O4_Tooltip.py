'''
Allows Tkinter widget to display a tooltip
'''
import tkinter as tk

class ToolTip(object):
    def __init__(self, widget, text='TK Widget', xoffset=75, yoffset=75, wraplength=300):
        self.widget = widget
        self.widget.xoffset = xoffset
        self.widget.yoffset = yoffset
        self.widget.wraplength = wraplength
        self.text = text
        self.widget.bind("<Enter>", self.mouseover)
        self.widget.bind("<Leave>", self.mousedown)


    def mouseover(self, event=None):
        x = y = 0
        x, y, cx, cy = self.widget.bbox("insert")

        x += self.widget.winfo_rootx() + self.widget.xoffset
        y += self.widget.winfo_rooty() + self.widget.yoffset

        # creates a toplevel window
        self.tw = tk.Toplevel(self.widget)

        # Leaves only the label and removes the app window
        self.tw.wm_overrideredirect(True)
        self.tw.wm_geometry("+%d+%d" % (x, y))

        label = tk.Label(self.tw, text=self.text, justify='left', wraplength=self.widget.wraplength,
                       background='light yellow', relief='solid', borderwidth=1,
                       font=("arial", "10", "normal"))

        label.pack(ipadx=1)


    def mousedown(self, event=None):
        if self.tw:
            self.tw.destroy()
