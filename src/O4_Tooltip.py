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


# testing ...
#if __name__ == '__main__':
#    root = tk.Tk()
#    btn1 = tk.Button(root, text="Test Button 1")
#    btn1.pack(padx=10, pady=5)
#    button1_ttp = ToolTip(btn1, "[NOT WORTH TRYING UNTIL SOME RENDERING BUG (submitted 11/2017) IN X-PLANE CODE IS CORRECTED - BORDER_TEX mistakenly affects the normal map in addition to the albedo, which yields crazy roughness values]\n\n Replaces X-Plane water by a custom normal map over ortho-imagery (requires XP11). A low res imagery is used for the sea, and masking textures are unaffected. The value 0 corresponds to legacy X-Plane water, 1 replaces it for inland water only, 2 over sea water only, and 3 over both.  This experimental feature has two strong downsides: 1) the waves are static rather dynamical (would require a plugin to update the normal_map as X-Plane does) and 2) the wave height is no longer weather dependent. On the other hand, waves might have less repetitive patterns and some blinking in water reflections might be improved too; users are welcome to improve the provided water_normal_map.dds (Gimp can be used to edit the mipmaps individually).")

#    btn2 = tk.Button(root, text="Test button 2")
#    btn2.pack(padx=10, pady=5)
#    button2_ttp = ToolTip(btn2, "This is button 2")

#    root.mainloop()