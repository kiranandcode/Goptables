import os
import tkinter as tk
from tkinter import filedialog
from datetime import timedelta, time, datetime
from itertools import cycle
from typing import List, Tuple

import httplib2
import matplotlib
import matplotlib.dates as mdates
import random
import sys
import json
from apiclient import discovery
from google.oauth2 import credentials
from oauth2client import client,tools
from oauth2client.file import Storage


google_colours = {
    '1','2','3','4','5','6','7','8'
}
#
grid_colours = [
    '#%02x%02x%02x' % (0x1C, 0x77, 0xC3),
    '#%02x%02x%02x' % (0x39, 0xA9, 0xDB),
    '#%02x%02x%02x' % (0x40, 0xBC, 0xD8),
    '#%02x%02x%02x' % (0xE3, 0x92, 0x37),
    '#%02x%02x%02x' % (0xD6, 0x32, 0x30),
    '#%02x%02x%02x' % (0x1D, 0xD3, 0xB0),
    '#%02x%02x%02x' % (0xAF, 0xFC, 0x41),
    '#%02x%02x%02x' % (0xB2, 0xfF, 0x9E),
    '#%02x%02x%02x' % (0x6D, 0x72, 0xC3),
    "red",
    "green",
    "blue",
    "cyan",
    "yellow",
    "magenta"
]

matplotlib.use('TkAgg')

from matplotlib.backends.backend_tkagg import FigureCanvasAgg, NavigationToolbar2Tk, FigureCanvasTkAgg
from matplotlib.backend_bases import key_press_handler

from matplotlib.figure import Figure

from timeparser import *


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


class TimetablePlanner:
    def __init__(self, master):
        self.color_map = {}
        self.description_map = {}
        self.master = master
        self.stats_manager = None
        self.export_window = None
        self.google_credentials = None

        self.configure_menu()

        # construct the task manager
        self.task_frame = tk.LabelFrame(self.master, text="Tasks")
        self.task_frame.grid(column=0, row=0, rowspan=3, columnspan=1, padx=3, pady=3, sticky=tk.N + tk.S + tk.W + tk.E)
        self.task_frame.columnconfigure(1, weight=1)
        self.task_manager = TaskManager(self.task_frame, on_tasks_changed=self.on_tasks_changed)

        # construct the time manager
        self.time_frame = tk.LabelFrame(self.master, text="Schedule")
        self.time_frame.grid(column=0, row=3, columnspan=4, rowspan=1, sticky=tk.N + tk.S + tk.W + tk.E)
        self.time_manager = TimeManager(self.time_frame, on_schedule_changed=self.on_schedule_changed)

        # construct the table manager
        self.table_frame = tk.LabelFrame(self.master, text="Timetable")
        self.table_frame.grid(column=1, row=0, rowspan=3, columnspan=3, sticky=tk.N + tk.S + tk.W + tk.E)
        self.table_manager = TableManager(self.table_frame, on_stats_change=self.on_table_stats_change)

        self.stats_panel = tk.LabelFrame(self.master, text="Statistics")
        self.stats_panel.grid(column=4, row=0, columnspan=1, rowspan=4, sticky=tk.N + tk.S + tk.W + tk.E)
        self.stats_manager = StatsManager(self.stats_panel)

    def configure_menu(self):
        self.menubar = tk.Menu(self.master)
        self.master.config(menu=self.menubar)

        self.file_menu = tk.Menu(self.menubar)
        self.file_menu.add_command(label="Save", command=self.on_save)
        self.file_menu.add_command(label="Load", command=self.on_load)
        self.file_menu.add_command(label="Exit", command=self.on_exit)
        self.menubar.add_cascade(label="File", menu=self.file_menu)

        self.export_menu = tk.Menu(self.menubar)
        self.export_menu.add_command(label="Export", command=self.on_export)
        self.menubar.add_cascade(label="Export", menu=self.export_menu)

        self.about_menu = tk.Menu(self.menubar)
        self.about_menu.add_command(label="About", command=self.about)
        self.menubar.add_cascade(label="About", menu=self.about_menu)

    def show_dialog_box(self, text):
        window = tk.Toplevel(self.master)
        tk.Label(window, text=text).pack(padx=5, pady=5)

        def on_delete():
            window.destroy()

        tk.Button(window, text="Ok", command=on_delete).pack(padx=5, pady=5)

    def about(self):
        window = tk.Toplevel(self.master)
        tk.Label(window, text="About Goptable").pack(padx=5, pady=5)
        tk.Label(window, text="By Gopiandcode").pack(padx=5, pady=5)

        def on_delete():
            window.destroy()

        tk.Button(window, text="Ok", command=on_delete).pack(padx=5, pady=5)

    def on_exit(self):
        sys.exit()

    def on_save(self):
        # retrieve the state object
        encoded = {}

        encoded['tasks'] = list(self.task_manager.tasks)

        encoded['breaks'] = [timedelta_to_str(br) for br in self.time_manager.break_durations]
        encoded['work_interval'] = timedelta_to_str(self.time_manager.work_length)
        encoded['start_time'] = time.strftime(self.time_manager.start_time, "%H:%M")

        encoded['start_date'] = datetime.strftime(self.table_manager.start_date, "%d-%m-%Y")
        encoded['days'] = self.table_manager.no_days

        grid = []
        for row in self.table_manager.grid:
            values = []
            for (option, val) in row:
                values.append(val.get())
            grid.append(values)

        encoded['table'] = grid

        encoded = json.dumps(encoded)
        file_path = filedialog.asksaveasfilename(
            defaultextension=".json",
            title="Save timetable file as",
            filetypes=[("json", "*.json")],
            parent=self.master
        )
        if file_path is not None:
            with open(file_path, "w") as f:
                f.write(encoded)

    def on_load(self):
        file_path = filedialog.askopenfilename(
            #            defaultextension=".json",
            title="Open timetable",
            filetypes=[("json", "*.json")],
            # parent=self.master
        )
        loaded = None
        try:
            with open(file_path, "r") as f:
                loaded = f.read()
        except FileNotFoundError:
            self.show_dialog_box("ERROR: File %s not found" % file_path)
            return

        try:
            loaded = json.loads(loaded)
        except json.decoder.JSONDecodeError:
            self.show_dialog_box("ERROR: Invalid JSON file format")
            return

        result = self.validate_json(loaded)
        if not result:
            self.show_dialog_box("ERROR: Invalid Goptable file format")
            return

        ## pass the attributes to each of the components

        self.task_manager.set_state(result['tasks'])

        self.time_manager.set_state(result['breaks'], result['work_interval'], result['start_time'])

        self.table_manager.set_state(result['start_date'], result['days'], result['table'])

    def validate_json(self, loaded):
        if not loaded:
            return None
        if 'tasks' not in loaded or not isinstance(loaded['tasks'], list):
            return None
        if 'breaks' not in loaded or not isinstance(loaded['breaks'], list):
            return None
        if 'work_interval' not in loaded or not isinstance(loaded['work_interval'], str):
            return None
        if 'start_time' not in loaded or not isinstance(loaded['start_time'], str):
            return None
        if 'start_date' not in loaded or not isinstance(loaded['start_date'], str):
            return None
        if 'days' not in loaded or not isinstance(loaded['days'], int):
            return None
        if 'table' not in loaded or not isinstance(loaded['table'], list):
            return None
        result = {}
        result['tasks'] = []
        for (name, score) in loaded['tasks']:
            result['tasks'].append((name, score))

        result['breaks'] = []
        for br in loaded['breaks']:
            br_dur = parse_duration(br)

            if br_dur is None:
                return None
            else:
                result['breaks'].append(br_dur)

        wk_dur = parse_duration(loaded['work_interval'])
        if not wk_dur:
            return None
        else:
            result['work_interval'] = wk_dur

        st_tm = parse_time(loaded['start_time'])
        if not st_tm:
            return None
        else:
            result['start_time'] = st_tm

        try:
            result['start_date'] = datetime.strptime(loaded['start_date'], "%d-%m-%Y")
        except ValueError:
            return None

        result['days'] = loaded['days']
        result['table'] = loaded['table']

        return result

    def on_export(self):
        SCOPES = 'https://www.googleapis.com/auth/calendar'
        CLIENT_SECRET_FILE = 'client_secret.json'
        APPLICATION_NAME = 'Goptable Timetabler'

        def export_on_delete():
            try:
                self.export_window.destroy()
            except:
                pass
            self.export_window = None

        def load_google_credentials():
            """Gets valid user credentials from storage.

            If nothing has been stored, or if the stored credentials are invalid,
            the OAuth2 flow is completed to obtain the new credentials.

            Returns:
                Credentials, the obtained credential.
            """
            home_dir = os.path.expanduser('~')
            credential_dir = os.path.join(home_dir, '.credentials')
            if not os.path.exists(credential_dir):
                os.makedirs(credential_dir)
            credential_path = os.path.join(credential_dir,
                                           'calendar-python-quickstart.json')
            secret_path = os.path.join(credential_dir,
                                           CLIENT_SECRET_FILE)

            store = Storage(credential_path)
            credentials = store.get()
            if not credentials or credentials.invalid:
                secret_path = filedialog.askopenfilename(
                            title="Open Google credentials.json",
                            filetypes=[("json", "*.json")],
                )
                if secret_path is not None:
                    flow = client.flow_from_clientsecrets(secret_path, SCOPES)
                    flow.user_agent = APPLICATION_NAME
                    credentials = tools.run_flow(flow, store)

            if credentials is not None or credentials.invalid:
                self.google_credentials = credentials

                self.google_calander_import_button.configure(state=tk.NORMAL)
            else:
                self.google_credentials = None
                self.google_calander_import_button.configure(state=tk.DISABLED)

            self.google_label_status_value.set("Google Credentials: %s" % (self.google_credentials is not None))


        def retrieve_schedule():
            start_time = self.time_manager.start_time
            break_durations = list(self.time_manager.break_durations)
            work_length = self.time_manager.work_length

            schedule_intervals = []
            current_time = datetime.now()
            current_time = datetime.combine(current_time, start_time)
            schedule_intervals.append((current_time, current_time + work_length, 5))
            current_time = current_time + work_length

            for br in break_durations:
                reminder = int(br.total_seconds() // 60)
                current_time = current_time + br
                schedule_intervals.append((current_time, current_time + work_length, reminder))
                current_time = current_time + work_length

            return schedule_intervals


        def construct_event(service, title,
                            start_hour, start_minute, start_day, end_hour, end_minute,
                            end_day=None, description=None,
                            start_month='11', start_year='2018',
                            end_month=None, end_year=None,
                            reminder_time=5,
                            location="London"):
            calander_id = self.google_calander_api_entry_value.get()
            if not end_day:
                end_day = start_day
            if not end_month:
                end_month = start_month
            if not end_year:
                end_year= start_year

            color_id = '8'
            description = ''
            if title in self.color_map:
                color_id = self.color_map[title].get()
            if title in self.description_map:
                description = self.description_map[title].get()


            event = {
                'summary': str(title),
                'location': str(location),
                'description': str(description),
                'start': {
                    'dateTime': '{}-{:0>2}-{:0>2}T{:0>2}:{:0>2}:00'.format(start_year, start_month, start_day, start_hour, start_minute),
                    'timeZone': 'UTC',
                },
                'end': {
                    'dateTime': '{}-{:0>2}-{:0>2}T{:0>2}:{:0>2}:00'.format(end_year, end_month, end_day, end_hour, end_minute),
                    'timeZone': 'UTC',
                },
                'recurrence': [],
                'attendees': [],
                'reminders': {
                    'useDefault': False,
                    'overrides': [
                        {'method': 'popup', 'minutes': reminder_time},
                    ],
                },
                'colorId': color_id
            }

            try:
                event = service.events().insert(calendarId=calander_id, body=event).execute()
            except Exception as e:
                self.show_dialog_box("ERROR: Error while constructing event %s" % e)


        def upload_table_to_google_cal():
            if not self.google_credentials:
                return
            http = self.google_credentials.authorize(httplib2.Http())
            service = discovery.build('calendar', 'v3', http=http)

            schedule = retrieve_schedule()
            for (i, (start_date, end_date, remainder_time)) in enumerate(schedule):
                if remainder_time is None:
                    remainder_time = 5

                start_hour = start_date.hour
                start_minute = start_date.minute

                end_hour = end_date.hour
                end_minute = end_date.minute

                temp_start_date = start_date
                temp_end_date = end_date
                for j in range(self.table_manager.no_days):
                    start_day = temp_start_date.day
                    start_month = temp_start_date.month
                    start_year = temp_start_date.year

                    end_day = temp_end_date.day
                    end_month = temp_end_date.month
                    end_year = temp_end_date.year

                    title = self.table_manager.grid[i][j][1].get()
                    if title != 'None':
                        construct_event(service, title, start_hour, start_minute, start_day, end_hour, end_minute, end_day=end_day, description=None, start_month=start_month, start_year=start_year, end_month=end_month, end_year=end_year, reminder_time=remainder_time)

                    temp_start_date = temp_start_date + timedelta(days=1)
                    temp_end_date = temp_end_date + timedelta(days=1)




        if self.export_window is None:
            self.color_map = {}
            self.description_map = {}

            self.export_window = tk.Toplevel(self.master)
            self.export_window.title("Goptable Export")
            self.export_window.protocol("WM_DELETE_WINDOW", export_on_delete)

            self.google_export = tk.LabelFrame(self.export_window, text="Google Export")
            self.google_export.pack(fill=tk.BOTH, expand=True)

            self.google_label_panel = tk.Frame(self.google_export)
            self.google_label_panel.pack(fill=tk.X, expand=True)

            self.google_label_status_value = tk.StringVar()
            self.google_label_status_value.set("Google Credentials: %s" % (self.google_credentials is not None))
            self.google_label_status = tk.Label(self.google_label_panel, textvariable=self.google_label_status_value)
            self.google_label_status.pack(side=tk.LEFT, fill=tk.X, expand=True)
            self.google_credentials_load = tk.Button(self.google_label_panel, text="Get Credentials", command=load_google_credentials)
            self.google_credentials_load.pack(fill=tk.X, expand=True)

            self.google_calander_api_panel= tk.Frame(self.google_export)
            self.google_calander_api_panel.pack(fill=tk.X, expand=True)

            self.google_calander_api_label = tk.Label(self.google_calander_api_panel, text="Google Calander API:")
            self.google_calander_api_label.pack(side=tk.LEFT, fill=tk.X, expand=True)

            self.google_calander_api_entry_value = tk.StringVar()
            self.google_calander_api_entry_value.set("")
            self.google_calander_api_entry = tk.Entry(self.google_calander_api_panel, textvariable=self.google_calander_api_entry_value)
            self.google_calander_api_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)

            self.google_calander_import_button = tk.Button(self.google_export, text="Upload to calander", state=tk.DISABLED, command=upload_table_to_google_cal)
            self.google_calander_import_button.pack(fill=tk.BOTH, expand=True)



            # self.color_map = {}
            # self.description_map = {}
            self.meta_panel = tk.LabelFrame(self.export_window, text="Event Meta-Information")
            self.meta_panel.pack(fill=tk.BOTH, expand=True)
            tasks = list(self.task_manager.tasks)
            for (task, score) in tasks:
                t_frame = tk.LabelFrame(self.meta_panel, text="%s Configuration" % task, relief='flat')
                t_frame.pack(fill=tk.X, expand=True)
                task_colourvar = tk.StringVar()
                task_colourvar.set('8')
                task_descvar = tk.StringVar()
                task_descvar.set('')
                tk.Label(t_frame, text="Task Colour:").pack(side=tk.LEFT, expand=True,fill=tk.BOTH)
                tk.OptionMenu(t_frame, task_colourvar, *google_colours).pack(side=tk.LEFT, expand=True,fill=tk.BOTH)

                tk.Label(t_frame, text="Task Description:").pack(side=tk.LEFT, expand=True,fill=tk.BOTH)
                tk.Entry(t_frame, textvariable=task_descvar).pack(side=tk.LEFT, expand=True,fill=tk.BOTH)

                self.color_map[task] = task_colourvar
                self.description_map[task] = task_descvar




    def on_tasks_changed(self, tasks):
        self.table_manager.set_tasks(tasks)

    def on_schedule_changed(self, start_time, work_length, break_durations):
        work_intervals = []
        current_time = datetime.now()
        current_time = datetime.combine(current_time, start_time)
        work_intervals.append("%s-%s" % (
        datetime.strftime(current_time, "%H:%M"), datetime.strftime(current_time + work_length, "%H:%M")))
        current_time = current_time + work_length

        for br in break_durations:
            current_time = current_time + br
            work_intervals.append("%s-%s" % (
            datetime.strftime(current_time, "%H:%M"), datetime.strftime(current_time + work_length, "%H:%M")))
            current_time = current_time + work_length

        self.table_manager.set_work_intervals(work_intervals)

    def on_table_stats_change(self, text):
        if self.stats_manager is not None:
            self.stats_manager.set_text(text)


class TableManager:
    """
    Synthesises information from the schedule and the tasks to construct a schedule
    """

    def set_tasks(self, tasks):
        self.tasks = tasks
        self.parameters_changed()

    def set_work_intervals(self, work_intervals):
        self.work_intervals = work_intervals
        self.parameters_changed()

    def parameters_changed(self):
        days = []
        date = self.start_date
        for i in range(self.no_days):
            days.append(date)
            date = date + timedelta(days=1)

        self.days = days

        self.task_choices = set(task[0] for task in self.tasks)
        self.task_choices.add('None')

        self.colouring = dict(zip(sorted(task[0] for task in self.tasks), cycle(grid_colours)))
        self.colouring["None"] = "#A4A9AD"

        self.old_grid = self.grid
        self.grid = [[None for i in range(self.no_days)] for i in range(len(self.work_intervals))]

        self.construct_grid()
        self.stats_change()

    def construct_grid(self):

        if self.grid_panel is not None:
            self.grid_panel.pack_forget()

        self.grid_panel = tk.Frame(self.master)
        self.grid_panel.pack(fill=tk.BOTH, expand=True)

        for i in range(len(self.work_intervals)):
            tk.Label(self.grid_panel, text=self.work_intervals[i]).grid(row=i + 1, column=0, columnspan=1, rowspan=1)

        for j in range(len(self.days)):
            tk.Label(self.grid_panel, text=datetime.strftime(self.days[j], "%a")).grid(row=0, column=j + 1,
                                                                                       columnspan=1, rowspan=1)

        for i in range(len(self.work_intervals)):
            for j in range(len(self.days)):
                grid_i = i + 1
                grid_j = j + 1
                value = "None"

                if self.old_grid is not None:
                    if i < len(self.old_grid):
                        if j < len(self.old_grid[i]):
                            if self.old_grid[i][j] is not None:
                                old_value = self.old_grid[i][j][1].get()
                                if old_value in self.task_choices:
                                    value = old_value

                namevar = tk.StringVar()
                namevar.set(value)
                namevar.trace_add("write", lambda *args, i=i, j=j: self.grid_box_change(i, j))
                option_menu = tk.OptionMenu(self.grid_panel, namevar,
                                            command=lambda i=i, j=j: self.grid_box_change(i, j),
                                            *self.task_choices)
                color = self.colouring[value]
                self.grid[i][j] = (option_menu, namevar)
                self.grid[i][j][0].configure(bg=color)
                self.grid[i][j][0].grid(row=grid_i, column=grid_j, columnspan=1, rowspan=1,
                                        stick=tk.N + tk.S + tk.E + tk.W)
        self.old_grid = None

    def grid_box_change(self, i, j):
        colour = self.colouring["None"]
        label = self.grid[i][j][1].get()

        if label in self.colouring:
            colour = self.colouring[label]

        self.grid[i][j][0].configure(bg=colour)
        self.stats_change()

    def stats_change(self):
        result = ""

        # come up with statistics
        total_cells = len(self.work_intervals) * self.no_days

        total_cost = 0
        cost = {}
        assigned_count = {}
        aimed_count = {}
        none_cells = 0

        for task in self.tasks:
            assigned_count[task[0]] = 0
            cost[task[0]] = task[1]
            total_cost += task[1]

        if total_cost > 0:
            for task in self.tasks:
                cost[task[0]] = cost[task[0]] / total_cost
                aimed_count[task[0]] = total_cells * cost[task[0]]

        for i in range(len(self.work_intervals)):
            for j in range(len(self.days)):
                task = self.grid[i][j][1].get()
                if task != 'None':
                    assigned_count[task] += 1
                else:
                    none_cells += 1

        result += "Total sessions: %d\n" % total_cells
        if total_cells > 0:
            result += "Proportion filled: %.1f (%d/%d)\n" % (
            (total_cells - none_cells) / total_cells, total_cells - none_cells, total_cells)
        result += "Empty cells: %d\n" % (none_cells)
        result += "Tasks:\n"
        for (task, name) in self.tasks:
            assigned = assigned_count[task]
            aimed = aimed_count[task]
            if aimed > 0:
                result += " - %s: %.1f (%d/%.1f) \n" % (task, assigned / aimed, assigned, aimed)
            else:
                result += " - %s: ~ (%d/%.1f) \n" % (task, assigned, aimed)

        if self.on_stats_change is not None:
            self.on_stats_change(result)

    def populate_table(self):
        total_cells = len(self.work_intervals) * self.no_days
        total_cost = 0
        cost = {}
        assigned_count = {}
        aimed_count = {}

        for task in self.tasks:
            assigned_count[task[0]] = 0
            cost[task[0]] = task[1]
            total_cost += task[1]

        if total_cost <= 0:
            return

        for task in self.tasks:
            cost[task[0]] = cost[task[0]] / total_cost
            aimed_count[task[0]] = total_cells * cost[task[0]]

        for i in range(self.no_days):
            choices_to_allocate = []

            # first we allocate the choices we need to assign this round
            for (task, score) in self.tasks:
                remaining = aimed_count[task] - assigned_count[task]
                to_add = min(int(cost[task] * len(self.work_intervals)), int(remaining))

                for i_ in range(min(int(to_add), int(len(self.work_intervals) - len(choices_to_allocate)))):
                    choices_to_allocate.append(task)

            # if we have space remaining, then allocate by the tasks that have been least assigned
            if len(choices_to_allocate) < len(self.work_intervals):
                remaining_no = len(self.work_intervals) - len(choices_to_allocate)

                # collate a list of the tasks, proportion that have been assigned
                remains = []
                for (task, assigned) in assigned_count.items():
                    if aimed_count[task] > 0:
                        remains.append((task, assigned / aimed_count[task]))

                # invert the list so that the lowest proportions have the largest values
                max_prop = max(remains, key=lambda task: task[1])[1]
                remains = sorted(((task, max_prop - prop) for (task, prop) in remains), key=lambda task: -task[1])
                total = sum(task[1] for task in remains)

                # do random roulette wheel selection for these ones
                for i_ in range(remaining_no):
                    score = random.uniform(0, total)
                    cumscore = 0
                    ind = 0
                    while cumscore < score and ind < len(remains):
                        cumscore += remains[ind][1]
                        ind += 1
                    if ind < len(remains):
                        choices_to_allocate.append(remains[ind][0])

            for task in choices_to_allocate:
                assigned_count[task] += 1

            random.shuffle(choices_to_allocate)
            for j, task in zip(range(len(self.work_intervals)), choices_to_allocate):
                wdgt = self.grid[j][i][1]
                wdgt.set(task)

        self.stats_change()

    def __init__(self, master, on_stats_change=None):
        self.master = master
        self.on_stats_change = on_stats_change
        self.start_date = datetime.now()
        self.no_days = 1

        self.work_intervals = []
        self.days = []
        self.tasks = []
        self.grid = []

        self.table_customisation_panel = tk.LabelFrame(self.master, text="Timetable Parameters")
        self.table_customisation_panel.pack(fill=tk.X, expand=True, side=tk.TOP)

        self.configure_days_customisation_panel()

        self.configure_start_date_customisation_panel()

        tk.Button(self.table_customisation_panel, text="Populate", command=self.populate_table).pack(fill=tk.BOTH,
                                                                                                     expand=True)

        self.grid_panel = None

        self.parameters_changed()

    def configure_start_date_customisation_panel(self):
        self.table_start_date_customisation_panel = tk.Frame(self.table_customisation_panel)
        self.table_start_date_customisation_panel.pack(side=tk.LEFT, expand=True, fill=tk.X)

        tk.Label(self.table_start_date_customisation_panel, text="Start Date:").pack(side=tk.LEFT)

        self.table_start_date_value = tk.StringVar()
        self.table_start_date_value.set(datetime.strftime(self.start_date, "%d-%m-%Y"))
        self.table_start_date_value.trace_add("write", self.table_start_date_edit_callback)

        self.table_start_date_entry = tk.Entry(self.table_start_date_customisation_panel,
                                               textvariable=self.table_start_date_value)
        self.table_start_date_entry.pack(side=tk.LEFT, expand=True, fill=tk.X)

        self.table_start_date_update_button = tk.Button(self.table_start_date_customisation_panel, text="Update Date",
                                                        state=tk.DISABLED,
                                                        command=self.table_start_date_update_callback)
        self.table_start_date_update_button.pack(side=tk.LEFT, expand=True, fill=tk.X)

        self.table_start_date_delete_button = tk.Button(self.table_start_date_customisation_panel, text="Reset Field",
                                                        state=tk.DISABLED,
                                                        command=self.table_start_date_delete_callback)
        self.table_start_date_delete_button.pack(side=tk.LEFT, expand=True, fill=tk.X)

    def retrieve_submitted_start_date(self):
        dstr = self.table_start_date_value.get()
        try:
            date = datetime.strptime(dstr, "%d-%m-%Y")
        except ValueError:
            date = None

        if date is not None:
            return date
        else:
            return None

    def table_start_date_edit_callback(self, *args):
        dt = self.retrieve_submitted_start_date()
        if dt is not None and dt != self.start_date:
            self.table_start_date_update_button.configure(state=tk.NORMAL)
            self.table_start_date_delete_button.configure(state=tk.NORMAL)
        elif dt is not None and dt == self.start_date:
            self.table_start_date_update_button.configure(state=tk.DISABLED)
            self.table_start_date_delete_button.configure(state=tk.DISABLED)
        else:
            self.table_start_date_update_button.configure(state=tk.DISABLED)
            self.table_start_date_delete_button.configure(state=tk.NORMAL)

    def table_start_date_update_callback(self):
        dt = self.retrieve_submitted_start_date()
        if dt is not None and dt != self.start_date:
            self.start_date = dt
            self.parameters_changed()

        self.table_start_date_edit_callback()

    def table_start_date_delete_callback(self):
        self.table_start_date_value.set(datetime.strftime(self.start_date, "%d-%m-%Y"))
        self.table_start_date_edit_callback()

    def configure_days_customisation_panel(self):
        self.table_days_customisation_panel = tk.Frame(self.table_customisation_panel)
        self.table_days_customisation_panel.pack(side=tk.LEFT, expand=True, fill=tk.X)
        tk.Label(self.table_days_customisation_panel, text="Days:").pack(side=tk.LEFT)
        self.table_days_customisation_counter = tk.Spinbox(
            self.table_days_customisation_panel,
            command=self.table_days_modification,
            from_=1,
            to=10000
        )
        self.table_days_customisation_counter.pack(side=tk.LEFT, expand=True, fill=tk.X)
        self.table_days_customisation_update_button = tk.Button(self.table_days_customisation_panel, text="Update Days",
                                                                state=tk.DISABLED,
                                                                command=self.table_days_customisation_update_callback)
        self.table_days_customisation_update_button.pack(side=tk.LEFT, expand=True, fill=tk.X)

    def retrieve_submitted_days(self):
        days = None
        try:
            days = int(self.table_days_customisation_counter.get())
        except ValueError:
            days = None
        return days

    def table_days_customisation_update_callback(self):
        days = self.retrieve_submitted_days()

        if days is not None and days != self.no_days:
            self.no_days = days
            self.parameters_changed()

        self.table_days_modification()

    def table_days_modification(self):
        days = self.retrieve_submitted_days()

        if days is not None and days != self.no_days:
            self.table_days_customisation_update_button.configure(state=tk.NORMAL)
        else:
            self.table_days_customisation_update_button.configure(state=tk.DISABLED)

    def set_state(self, start_date, no_days, grid_values):
        self.no_days = no_days
        self.table_days_customisation_counter.delete(0, tk.END)
        self.table_days_customisation_counter.insert(tk.INSERT, str(no_days))
        self.parameters_changed()
        self.table_days_modification()

        self.start_date = start_date
        self.table_start_date_value.set(datetime.strftime(start_date, "%d-%m-%Y"))
        self.parameters_changed()
        self.table_start_date_edit_callback()

        self.old_grid = None

        for i in range(len(self.work_intervals)):
            for j in range(self.no_days):
                label = None
                if i < len(grid_values):
                    if j < len(grid_values[i]):
                        label = grid_values[i][j]
                self.grid[i][j][1].set(label)
        self.parameters_changed()


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


class TaskManager:
    """
        Keeps track of the current types of tasks and their importance
    """

    def __init__(self, master, on_tasks_changed=None):
        self.on_tasks_changed = on_tasks_changed
        self.padding_options = {'padx': 5, 'pady': 5}
        self.master = master
        self.tasks: List[Tuple[str, float]] = []

        self.listbox = tk.Listbox(self.master)
        self.listbox.pack(fill=tk.X, **self.padding_options)
        self.listbox.bind('<<ListboxSelect>>', self.task_list_callback)

        self.modify_entries_parent = tk.LabelFrame(self.master, text="Modify Task", relief='flat')
        self.modify_entries_parent.pack(fill=tk.X, **self.padding_options)

        self.modify_entries = tk.Frame(self.modify_entries_parent)
        self.modify_entries.pack(fill=tk.X, pady=5)

        self.modify_index = None
        self.modify_name_value = tk.StringVar()
        self.modify_score_value = tk.StringVar()
        self.modify_name_original = None
        self.modify_score_original = None

        tk.Label(self.modify_entries, text="Name:").pack(side=tk.LEFT, padx=2)
        self.modify_name = tk.Entry(
            self.modify_entries,
            textvariable=self.modify_name_value,
            state=tk.DISABLED
        )
        self.modify_name.pack(side=tk.LEFT)
        self.modify_name.bind("<Return>", lambda x: self.modify_update_callback())

        tk.Label(self.modify_entries, text="Weight:").pack(side=tk.LEFT, padx=2)
        self.modify_score = tk.Entry(
            self.modify_entries,
            textvariable=self.modify_score_value,
            state=tk.DISABLED
        )
        self.modify_score.pack(side=tk.LEFT)
        self.modify_score.bind("<Return>", lambda x: self.modify_update_callback())

        self.modify_name_value.trace_add("write", self.modify_name_callback)
        self.modify_score_value.trace_add("write", self.modify_score_callback)

        self.modify_update_button = tk.Button(
            self.modify_entries_parent,
            text="Update Task",
            state=tk.DISABLED,
            command=self.modify_update_callback
        )
        self.modify_update_button.pack(fill=tk.X, pady=2)
        self.modify_update_button.bind("<Return>", lambda x: self.modify_update_callback())

        self.modify_delete_button = tk.Button(
            self.modify_entries_parent,
            text="Delete Task",
            state=tk.DISABLED,
            command=self.modify_delete_callback
        )
        self.modify_delete_button.pack(fill=tk.X, pady=2)
        self.modify_delete_button.bind("<Return>", lambda x: self.modify_delete_callback())

        self.create_entries_parent = tk.LabelFrame(self.master, text="Create Task", relief='flat')
        self.create_entries_parent.pack(fill=tk.X, **self.padding_options)
        self.create_entries = tk.Frame(self.create_entries_parent)
        self.create_entries.pack(fill=tk.X, pady=5)

        tk.Label(self.create_entries, text="Name:").pack(side=tk.LEFT, padx=2)
        self.create_name_value = tk.StringVar()
        self.create_name = tk.Entry(self.create_entries, textvariable=self.create_name_value)
        self.create_name.pack(side=tk.LEFT)
        self.create_name.bind("<Return>", lambda x: self.create_task_callback())

        tk.Label(self.create_entries, text="Weight:").pack(side=tk.LEFT, padx=2)
        self.create_score_value = tk.StringVar()
        self.create_score = tk.Entry(self.create_entries, textvariable=self.create_score_value)
        self.create_score.pack(side=tk.LEFT)
        self.create_score.bind("<Return>", lambda x: self.create_task_callback())

        self.create_name_value.trace_add("write", self.create_name_callback)
        self.create_score_value.trace_add("write", self.create_score_callback)

        self.create_button = tk.Button(
            self.create_entries_parent,
            text="Create Task",
            state=tk.DISABLED,
            command=self.create_task_callback
        )
        self.create_button.pack(fill=tk.X, pady=2)
        self.create_button.bind("<Return>", lambda x: self.create_task_callback())

    def modify_delete_callback(self):
        if self.modify_index is not None:
            index = self.modify_index
            del self.tasks[index]
            self.listbox.delete(index)
            self.modify_index = None
            self.parameters_changed()

        self.update_modify_components_state()

    def modify_update_callback(self):
        update = self.retrieve_modify_values()
        if self.modify_index is not None and update is not None:
            new_name, new_score = update
            index = self.modify_index
            del self.tasks[index]
            self.listbox.delete(index)
            self.tasks.insert(index, (new_name, new_score))
            self.listbox.insert(index, "%s : %s" % (new_name, new_score))
            self.modify_score_original = new_score
            self.modify_name_original = new_name
            self.parameters_changed()

        self.update_modify_components_state()

    def task_list_callback(self, evt):
        if evt.widget is self.listbox:
            selection = evt.widget.curselection()
            index = None
            if len(selection) > 0:
                index = int(selection[0])
            else:
                return

            self.configure_entry_for_modification(index)

    def configure_entry_for_modification(self, index):
        if index is not None and index < len(self.tasks):
            self.modify_index = index
            self.modify_name_original = self.tasks[index][0]
            self.modify_score_original = self.tasks[index][1]
            self.modify_name_value.set(self.modify_name_original)
            self.modify_score_value.set(self.modify_score_original)
        else:
            self.modify_index = None

        self.update_modify_components_state()

    def modify_name_callback(self, *args):
        """
         Callback which updates the state of the modify entry components when the
        fields are changed
        :param args:  required to match the signature of the callback
        """
        self.update_modify_components_state()

    def modify_score_callback(self, *args):
        """
         Callback which updates the state of the modify entry components when the
        fields are changed
        :param args:  required to match the signature of the callback
        """
        self.update_modify_components_state()

    def update_modify_components_state(self):
        """
        Updates the states of all the components for modifing entries
        :return:
        """
        if self.modify_index is None:
            self.modify_name.configure(state=tk.DISABLED)
            self.modify_score.configure(state=tk.DISABLED)
            self.modify_update_button.configure(state=tk.DISABLED)
            self.modify_delete_button.configure(state=tk.DISABLED)

            self.modify_name_value.set("")
            self.modify_score_value.set("")
            self.modify_name_original = None
            self.modify_score_original = None

        elif self.retrieve_modify_values() is None:
            self.modify_name.configure(state=tk.NORMAL)
            self.modify_score.configure(state=tk.NORMAL)
            self.modify_update_button.configure(state=tk.DISABLED)
            self.modify_delete_button.configure(state=tk.NORMAL)
        else:
            self.modify_name.configure(state=tk.NORMAL)
            self.modify_score.configure(state=tk.NORMAL)
            self.modify_update_button.configure(state=tk.NORMAL)
            self.modify_delete_button.configure(state=tk.NORMAL)

    def retrieve_modify_values(self):
        """
        Retrieves the current values in the modify boxes if they are valid
        :return: (str,float) if the values are valid
        """
        name = self.modify_name_value.get()
        score = self.modify_score_value.get()

        try:
            score = float(score)
        except ValueError:
            score = None

        if score is None:
            return None
        if name == self.modify_name_original and score == self.modify_score_original:
            return None

        duplicated_name = any(x for x in self.tasks if x[0] == name)
        modified_name = name != self.modify_name_original

        if duplicated_name and modified_name:
            return None
        else:
            return (name, score)

    def create_task_callback(self):
        values = self.retrieve_create_values()
        if values is not None:
            name, score = values
            self.tasks.append((name, score))
            self.listbox.insert(tk.END, "%s : %s" % (name, score))
            self.parameters_changed()
            self.clear_create_entries()

    def create_name_callback(self, *args):
        """
         Callback which updates the state of the create entry components when the
        fields are changed
        :param args:  required to match the signature of the callback
        """
        self.update_create_button_state()

    def create_score_callback(self, *args):
        """
        Callback which updates the state of the create entry components when the
        fields are changed
        :param args:  required to match the signature of the callback
        """
        self.update_create_button_state()

    def retrieve_create_values(self):
        """
        Retrieves the current values in the create boxes if they are valid
        :return: (str,float) if the values are valid
        """
        name = self.create_name_value.get()
        score = self.create_score_value.get()
        try:
            score = float(score)
        except ValueError:
            score = None
        if any(x for x in self.tasks if x[0] == name) or score is None:
            return None
        else:
            return (name, score)

    def update_create_button_state(self):
        """
        Enables or disables the create entry button based on whether the values in the
        corresponding fields are valid
        """
        if self.retrieve_create_values() is not None:
            self.create_button.configure(state=tk.NORMAL)
        else:
            self.create_button.configure(state=tk.DISABLED)

    def clear_create_entries(self):
        """
        Clears the corresponding add entry fields and updates the corresponding button states
        """
        self.create_name_value.set("")
        self.create_score_value.set("")
        self.update_create_button_state()

    def parameters_changed(self):
        if self.on_tasks_changed is not None:
            self.on_tasks_changed(list(self.tasks))

    def set_state(self, tasks):
        self.listbox.delete(0, tk.END)

        self.clear_create_entries()

        self.modify_index = None
        self.update_modify_components_state()

        self.tasks = tasks
        for (name, score) in self.tasks:
            self.listbox.insert(tk.END, "%s : %s" % (name, score))

        self.parameters_changed()


def main():
    root = tk.Tk()
    app = TimetablePlanner(root)
    root.mainloop()


main()
