import tkinter as tk


class StatsManager(object):

    def __init__(self, master):
        self.master = master
        self.stats_text = tk.Text(self.master, state=tk.DISABLED)
        self.stats_text.pack(fill=tk.BOTH, expand=True)

        self.set_text("None")

    def clear_text_area(self):
        self.stats_text.configure(state=tk.NORMAL)
        self.stats_text.delete('1.0', tk.END)
        self.stats_text.configure(state=tk.DISABLED)

    def set_text(self, text):
        self.clear_text_area()
        self.stats_text.configure(state=tk.NORMAL)
        self.stats_text.insert(tk.END, text)
        self.stats_text.configure(state=tk.DISABLED)