import random
import tkinter as tk
from datetime import timedelta, datetime
from itertools import cycle


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
        result += "Empty cells: %d\n" % none_cells
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
