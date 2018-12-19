import json
import os
import sys
import tkinter as tk
from datetime import time, datetime, timedelta
from tkinter import filedialog

import httplib2
from googleapiclient import discovery
from googleapiclient.http import BatchHttpRequest
from oauth2client import client, tools
from oauth2client.file import Storage

from components.stats import StatsManager
from components.table import TableManager
from components.task import TaskManager
from components.time import TimeManager
from serialization import validate_json
from timeparser import timedelta_to_str

google_colours = {
    '1', '2', '3', '4', '5', '6', '7', '8'
}

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
        encoded = {'tasks': list(self.task_manager.tasks),
                   'breaks': [timedelta_to_str(br) for br in self.time_manager.break_durations],
                   'work_interval': timedelta_to_str(self.time_manager.work_length),
                   'start_time': time.strftime(self.time_manager.start_time, "%H:%M"),
                   'start_date': datetime.strftime(self.table_manager.start_date, "%d-%m-%Y"),
                   'days': self.table_manager.no_days}

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

        result = validate_json(loaded)
        if not result:
            self.show_dialog_box("ERROR: Invalid Goptable file format")
            return

        ## pass the attributes to each of the components

        self.task_manager.set_state(result['tasks'])

        self.time_manager.set_state(result['breaks'], result['work_interval'], result['start_time'])

        self.table_manager.set_state(result['start_date'], result['days'], result['table'])

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

        def construct_event(batch,service, title,
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
                end_year = start_year

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
                    'dateTime': '{}-{:0>2}-{:0>2}T{:0>2}:{:0>2}:00'.format(start_year, start_month, start_day,
                                                                           start_hour, start_minute),
                    'timeZone': 'UTC',
                },
                'end': {
                    'dateTime': '{}-{:0>2}-{:0>2}T{:0>2}:{:0>2}:00'.format(end_year, end_month, end_day, end_hour,
                                                                           end_minute),
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
                batch.add(service.events().insert(calendarId=calander_id, body=event))
                # event = service.events().insert(calendarId=calander_id, body=event).execute()
            except Exception as e:
                self.show_dialog_box("ERROR: Error while constructing event %s" % e)

        def upload_table_to_google_cal():
            if not self.google_credentials:
                return
            http = self.google_credentials.authorize(httplib2.Http())
            service = discovery.build('calendar', 'v3', http=http)
            batch = BatchHttpRequest()

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
                        construct_event(batch, service, title, start_hour, start_minute, start_day, end_hour, end_minute,
                                        end_day=end_day, description=None, start_month=start_month,
                                        start_year=start_year, end_month=end_month, end_year=end_year,
                                        reminder_time=remainder_time)

                    temp_start_date = temp_start_date + timedelta(days=1)
                    temp_end_date = temp_end_date + timedelta(days=1)
            try:
                batch.execute(http=http)
            except Exception as e:
                self.show_dialog_box("ERROR: Error while constructing event %s" % e)

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
            self.google_credentials_load = tk.Button(self.google_label_panel, text="Get Credentials",
                                                     command=load_google_credentials)
            self.google_credentials_load.pack(fill=tk.X, expand=True)

            self.google_calander_api_panel = tk.Frame(self.google_export)
            self.google_calander_api_panel.pack(fill=tk.X, expand=True)

            self.google_calander_api_label = tk.Label(self.google_calander_api_panel, text="Google Calander API:")
            self.google_calander_api_label.pack(side=tk.LEFT, fill=tk.X, expand=True)

            self.google_calander_api_entry_value = tk.StringVar()
            self.google_calander_api_entry_value.set("")
            self.google_calander_api_entry = tk.Entry(self.google_calander_api_panel,
                                                      textvariable=self.google_calander_api_entry_value)
            self.google_calander_api_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)

            self.google_calander_import_button = tk.Button(self.google_export, text="Upload to calander",
                                                           state=tk.DISABLED, command=upload_table_to_google_cal)
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
                tk.Label(t_frame, text="Task Colour:").pack(side=tk.LEFT, expand=True, fill=tk.BOTH)
                tk.OptionMenu(t_frame, task_colourvar, *google_colours).pack(side=tk.LEFT, expand=True, fill=tk.BOTH)

                tk.Label(t_frame, text="Task Description:").pack(side=tk.LEFT, expand=True, fill=tk.BOTH)
                tk.Entry(t_frame, textvariable=task_descvar).pack(side=tk.LEFT, expand=True, fill=tk.BOTH)

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