import tkinter as tk
from datetime import timedelta, time, datetime

from matplotlib import dates as mdates
from matplotlib.backend_bases import key_press_handler
from matplotlib.backends._backend_tk import NavigationToolbar2Tk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

from timeparser import parse_duration, timedelta_to_str, time_to_str, parse_time


class TimeManager:
    """
    Keeps track of the time schedule
    """

    def __init__(self, master, on_schedule_changed=None):
        # configure the data variables
        self.on_schedule_changed = on_schedule_changed
        self.work_length = timedelta(minutes=30)
        self.start_time = time(hour=6, minute=30)
        self.break_durations = []
        self.modify_index = None

        self.master = master

        # configure the modifcation panel
        self.schedule_panel = tk.LabelFrame(master, text="Breaks")
        self.schedule_panel.pack(side=tk.LEFT, fill=tk.X, expand=True)

        self.configure_work_length_panel()
        self.configure_start_time_panel()

        self.configure_breaks_list()

        self.configure_update_break_panel()

        self.configure_create_break_panel()

        self.configure_schedule_visualization(master)

    def configure_create_break_panel(self):
        self.create_break_frame = tk.LabelFrame(self.schedule_panel, text="Create Break", relief='flat')
        self.create_break_frame.pack(fill=tk.X)
        self.create_break_value = tk.StringVar()
        self.create_break_value.trace_add("write", self.create_break_edit_callback)
        self.create_break_entry = tk.Entry(self.create_break_frame, textvariable=self.create_break_value)
        self.create_break_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.create_break_button = tk.Button(self.create_break_frame, text="Add Break",
                                             command=self.create_break_callback, state=tk.DISABLED)
        self.create_break_button.pack(side=tk.LEFT, expand=True, fill=tk.X)
        self.create_break_entry.bind("<Return>", lambda x: self.create_break_callback())
        self.create_break_button.bind("<Return>", lambda x: self.create_break_callback())

    def create_break_edit_callback(self, *args):
        break_duration = self.create_break_value.get()
        break_duration = parse_duration(break_duration)

        if break_duration is not None:
            self.create_break_button.configure(state=tk.NORMAL)
        else:
            self.create_break_button.configure(state=tk.DISABLED)

    def create_break_callback(self):
        break_duration = self.create_break_value.get()
        break_duration = parse_duration(break_duration)
        if break_duration is not None:
            self.break_durations.append(break_duration)
            self.breaks_list.insert(tk.END, timedelta_to_str(break_duration))
            self.create_break_value.set("")
            self.parameters_updated()

        self.create_break_edit_callback()

    def configure_update_break_panel(self):
        self.update_break_frame = tk.LabelFrame(self.schedule_panel, text="Update Break", relief='flat')
        self.update_break_frame.pack(fill=tk.X)

        self.update_break_value = tk.StringVar()
        self.update_break_original = None
        self.update_break_value.trace_add("write", self.update_break_edit_callback)

        self.update_break_entry = tk.Entry(self.update_break_frame, textvariable=self.update_break_value,
                                           state=tk.DISABLED)
        self.update_break_entry.pack(fill=tk.X)
        self.update_break_entry.bind("<Return>", lambda x: self.update_break_update_callback())

        self.update_break_panel = tk.Frame(self.update_break_frame)
        self.update_break_panel.pack(fill=tk.X, expand=True)

        self.update_break_update_button = tk.Button(self.update_break_panel, text="Update Break", state=tk.DISABLED,
                                                    command=self.update_break_update_callback)
        self.update_break_update_button.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.update_break_update_button.bind("<Return>", lambda x: self.update_break_update_callback())

        self.update_break_remove_button = tk.Button(self.update_break_panel, text="Delete Break", state=tk.DISABLED,
                                                    command=self.update_break_delete_callback)
        self.update_break_remove_button.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.update_break_remove_button.bind("<Return>", lambda x: self.update_break_delete_callback())

    def update_break_edit_callback(self, *args):
        self.update_modify_components_state()

    def update_break_update_callback(self):
        duration = self.update_break_value.get()
        duration = parse_duration(duration)
        if duration == self.update_break_original:
            duration = None

        if self.modify_index is not None and duration is not None:
            index = self.modify_index

            del self.break_durations[index]
            self.breaks_list.delete(index)

            self.break_durations.insert(index, duration)
            self.breaks_list.insert(index, timedelta_to_str(duration))

            self.update_break_original = duration
            self.parameters_updated()
        self.update_modify_components_state()

    def update_break_delete_callback(self):
        if self.modify_index is not None:
            index = self.modify_index
            del self.break_durations[index]
            self.breaks_list.delete(index)
            self.modify_index = None
            self.parameters_updated()
        self.update_modify_components_state()

    def configure_entry_for_modification(self, index):
        if index is not None and index < len(self.break_durations):
            self.modify_index = index
            self.update_break_original = self.break_durations[index]
            self.update_break_value.set(timedelta_to_str(self.update_break_original))
        else:
            self.modify_index = None

        self.update_modify_components_state()

    def update_modify_components_state(self):
        """
        Updates the states of all the components for modifing entries
        :return:
        """
        duration = self.update_break_value.get()
        duration = parse_duration(duration)

        if self.modify_index is None:
            self.update_break_entry.configure(state=tk.DISABLED)
            self.update_break_update_button.configure(state=tk.DISABLED)
            self.update_break_remove_button.configure(state=tk.DISABLED)

            self.update_break_value.set("")
            self.update_break_original = None
        elif duration is None or duration == self.update_break_original:
            self.update_break_entry.configure(state=tk.NORMAL)
            self.update_break_update_button.configure(state=tk.DISABLED)
            self.update_break_remove_button.configure(state=tk.NORMAL)
        else:
            self.update_break_entry.configure(state=tk.NORMAL)
            self.update_break_update_button.configure(state=tk.NORMAL)
            self.update_break_remove_button.configure(state=tk.NORMAL)

    def configure_breaks_list(self):
        self.breaks_list = tk.Listbox(self.schedule_panel)
        self.breaks_list.pack(fill=tk.X)
        self.breaks_list.bind('<<ListboxSelect>>', self.breaks_list_callback)

    def breaks_list_callback(self, evt):
        if evt.widget is self.breaks_list:
            selection = evt.widget.curselection()
            index = None
            if len(selection) > 0:
                index = int(selection[0])
            else:
                return

            self.configure_entry_for_modification(index)

    def configure_schedule_visualization(self, master):
        self.schedule_graph = tk.LabelFrame(master, text="Schedule Visualization")
        self.schedule_graph.pack(side=tk.LEFT, expand=True, fill=tk.BOTH)

        self.schedule_figure = Figure(figsize=(5, 4), dpi=100, tight_layout=True)
        self.schedule_axes = self.schedule_figure.add_axes([0.1, 0.1, 0.8, 0.8])
        self.schedule_date_plotter = mdates.DateFormatter('%H:%M')

        self.schedule_canvas = FigureCanvasTkAgg(self.schedule_figure, master=self.schedule_graph)
        self.schedule_canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        self.schedule_canvas._tkcanvas.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        self.schedule_toolbar = NavigationToolbar2Tk(self.schedule_canvas, self.schedule_graph)
        self.schedule_toolbar.update()

        def on_key_event(event):
            key_press_handler(event, self.schedule_canvas, self.schedule_toolbar)

        self.schedule_canvas.mpl_connect('key_press_event', on_key_event)

    def parameters_updated(self):
        self.schedule_axes.clear()

        # draw the data
        # create data
        start_date = datetime.now()
        start_date = datetime.combine(start_date, self.start_time)

        y = [int(br.total_seconds() // 60) for br in self.break_durations]
        x = []
        durations = []

        for br in self.break_durations:
            start_date = start_date + self.work_length
            duration = mdates.date2num(start_date + br) - mdates.date2num(start_date)
            x.append(mdates.date2num(start_date) + duration / 2)
            durations.append(duration)

            start_date = start_date + br

        self.schedule_axes.bar(x, y, width=durations)
        self.schedule_axes.xaxis_date()
        self.schedule_figure.autofmt_xdate()
        self.schedule_axes.get_xaxis().set_major_formatter(self.schedule_date_plotter)

        self.schedule_canvas.draw()
        if self.on_schedule_changed is not None:
            self.on_schedule_changed(self.start_time, self.work_length, list(self.break_durations))

    def configure_work_length_panel(self):
        self.work_length_panel = \
            tk.LabelFrame(self.schedule_panel, text="Work Interval Duration", relief='flat')
        self.work_length_panel.pack(side=tk.TOP, fill=tk.X)

        self.work_length_duration_value = tk.StringVar()
        self.work_length_duration_value.set(timedelta_to_str(self.work_length))
        self.work_length_duration_value.trace_add("write", self.work_length_duration_callback)
        self.work_length_duration_entry = \
            tk.Entry(self.work_length_panel, textvariable=self.work_length_duration_value)
        self.work_length_duration_entry.pack(side=tk.LEFT)
        self.work_length_duration_entry.bind("<Return>", lambda x: self.work_length_duration_update_callback())

        self.work_length_duration_update_button = \
            tk.Button(self.work_length_panel,
                      text="Update Interval",
                      command=self.work_length_duration_update_callback,
                      state=tk.DISABLED)
        self.work_length_duration_update_button.pack(side=tk.LEFT)
        self.work_length_duration_update_button.bind("<Return>", lambda x: self.work_length_duration_update_callback())

        self.work_length_duration_reset_button = \
            tk.Button(self.work_length_panel,
                      text="Reset Field",
                      command=self.work_length_duration_reset_callback,
                      state=tk.DISABLED)
        self.work_length_duration_reset_button.pack(side=tk.LEFT)
        self.work_length_duration_reset_button.bind("<Return>", lambda x: self.work_length_duration_reset_callback())

    def work_length_duration_callback(self, *args):
        duration = self.work_length_duration_value.get()
        duration = parse_duration(duration)
        if duration is not None and duration != self.work_length:
            self.work_length_duration_update_button.configure(state=tk.NORMAL)
            self.work_length_duration_reset_button.configure(state=tk.NORMAL)
        elif duration is not None and duration == self.work_length:
            self.work_length_duration_update_button.configure(state=tk.DISABLED)
            self.work_length_duration_reset_button.configure(state=tk.DISABLED)
        else:
            self.work_length_duration_update_button.configure(state=tk.DISABLED)
            self.work_length_duration_reset_button.configure(state=tk.NORMAL)

    def work_length_duration_update_callback(self):
        duration = self.work_length_duration_value.get()
        duration = parse_duration(duration)
        if duration is not None and duration != self.work_length:
            self.work_length = duration
            self.parameters_updated()

        self.work_length_duration_callback()

    def work_length_duration_reset_callback(self):
        self.work_length_duration_value.set(timedelta_to_str(self.work_length))

        self.work_length_duration_callback()

    def configure_start_time_panel(self):
        self.start_time_panel = \
            tk.LabelFrame(self.schedule_panel, text="Start Time", relief='flat')
        self.start_time_panel.pack(side=tk.TOP, fill=tk.X)

        self.start_time_value = tk.StringVar()
        self.start_time_value.set(time_to_str(self.start_time))
        self.start_time_value.trace_add("write", self.start_time_callback)
        self.start_time_entry = \
            tk.Entry(self.start_time_panel, textvariable=self.start_time_value)
        self.start_time_entry.pack(side=tk.LEFT, expand=True, fill=tk.X)
        self.start_time_entry.bind("<Return>", lambda x: self.start_time_update_callback())

        self.start_time_update_button = \
            tk.Button(self.start_time_panel,
                      text="Update Time",
                      command=self.start_time_update_callback,
                      state=tk.DISABLED)
        self.start_time_update_button.pack(side=tk.LEFT, expand=True, fill=tk.X)
        self.start_time_update_button.bind("<Return>", lambda x: self.start_time_update_callback())

        self.start_time_reset_button = \
            tk.Button(self.start_time_panel,
                      text="Reset Field",
                      command=self.start_time_reset_callback,
                      state=tk.DISABLED)
        self.start_time_reset_button.pack(side=tk.LEFT, expand=True, fill=tk.X)
        self.start_time_reset_button.bind("<Return>", lambda x: self.start_time_reset_callback())

    def start_time_callback(self, *args):
        time_value = self.start_time_value.get()
        time_value = parse_time(time_value)
        if time_value is not None and time_value != self.start_time:
            self.start_time_update_button.configure(state=tk.NORMAL)
            self.start_time_reset_button.configure(state=tk.NORMAL)
        elif time_value is not None and time_value == self.start_time:
            self.start_time_update_button.configure(state=tk.DISABLED)
            self.start_time_reset_button.configure(state=tk.DISABLED)
        else:
            self.start_time_update_button.configure(state=tk.DISABLED)
            self.start_time_reset_button.configure(state=tk.NORMAL)

    def start_time_update_callback(self):
        time_value = self.start_time_value.get()
        time_value = parse_time(time_value)
        if time_value is not None and time_value != self.start_time:
            self.start_time = time_value
            self.parameters_updated()

        self.start_time_callback()

    def start_time_reset_callback(self):
        self.start_time_value.set(time_to_str(self.start_time))

        self.start_time_callback()

    def set_state(self, breaks, work_interval, start_time):
        self.breaks_list.delete(0, tk.END)
        for br in breaks:
            self.breaks_list.insert(tk.END, timedelta_to_str(br))
        self.break_durations = breaks

        self.create_break_value.set("")
        self.update_break_value.set("")

        self.work_length = work_interval
        self.start_time = start_time
        self.work_length_duration_value.set(timedelta_to_str(work_interval))
        self.start_time_value.set(time_to_str(start_time))

        self.start_time_callback()
        self.work_length_duration_callback()

        self.parameters_updated()
        self.create_break_edit_callback()