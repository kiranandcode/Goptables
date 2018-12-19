import tkinter as tk

import matplotlib

from components.timetable import TimetablePlanner


matplotlib.use('TkAgg')


def main():
    root = tk.Tk()
    app = TimetablePlanner(root)
    root.mainloop()


if __name__ == '__main__':
    main()
