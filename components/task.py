import tkinter as tk
from typing import List, Tuple


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
            return name, score

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
            return name, score

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