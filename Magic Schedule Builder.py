"""
Owen's Magic Schedule Builder and Conflict Detector
===================================================

This Python script implements a simple graphical scheduling application
using Tkinter.  It allows you to manage a list of employees, record their
availability for each day of the week, assign shifts, detect conflicts
between scheduled shifts and availability, and export the resulting
schedule to a CSV file.  The application is intended as a starting
point—you can extend it to handle multiple weeks, different shift types,
or persistent storage.

Features
--------

* **Add employees** with first name, last name, and availability for
  Saturday–Friday.
* **Add or update schedules** for each employee via a simple form.
* **Detect conflicts** where a shift is assigned on a day marked
  “UNAVAILABLE” in the employee’s availability.
* **Export to CSV** with one row per employee and columns for each
  day of the week.
* Highlights rows with conflicts using a red background.

Usage
-----

Run the script with Python 3 on macOS (or any platform with Tkinter):

```
python3 schedule_builder_gui.py
```

The main window will appear with buttons to add employees and schedules,
check for conflicts, and export the schedule.

Limitations
-----------

* The schedule grid covers a single week (Saturday through Friday).  To
  extend it for multiple weeks, you could add additional columns or
  implement a tabbed interface.
* Data is stored in memory only; if you exit the program, your data is
  lost unless you export to CSV.

"""

from __future__ import annotations

import csv
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, filedialog
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from datetime import date, datetime, timedelta

# Days of week used in the schedule and availability
DAY_NAMES = [
    "Saturday",
    "Sunday",
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
]

# Possible shift options derived from the original spreadsheet's drop‑down menus.
# The first value is intentionally left empty to allow a blank selection.  You
# can customise this list if your organisation uses different shift names or
# wants to include more options.  The 'Store Schedule' option appears only
# in some cells of the original document, but it is included here for
# completeness.
SHIFT_OPTIONS: List[str] = [
    "",  # blank option
    "7-12", "8-1", "9-2", "10-3", "11-4", "12-5",
    "1-6", "2-7", "3-8", "4-9", "5-10", "6-11",
    "8-5", "9-6", "10-7", "11-8", "12-9", "1-10",
    "OFF", "RTO", "Store Schedule",
]

# Availability options derived from the spreadsheet's drop‑down menus.  The first
# blank entry allows leaving a day unspecified.  "OPEN AVAILABILITY" should
# indicate completely open availability (outside of business hours), whereas
# "UNAVAILABLE" indicates no availability on that day.
AVAILABILITY_OPTIONS: List[str] = [
    "",  # blank option
    "UNAVAILABLE",
    "OPEN AVAILABILITY",
    "7-12", "8-1", "9-2", "10-3", "11-4", "12-5",
    "1-6", "2-7", "3-8", "4-9", "5-10", "6-11",
    "Open after 10", "Open after 11", "Open after 12",
    "Open after 1", "Open after 2", "Open after 3", "Open after 4",
]


@dataclass
class Employee:
    """Represent an employee with a name, availability and schedule."""
    last_name: str
    first_name: str
    availability: Dict[str, str] = field(default_factory=dict)
    schedule: Dict[str, str] = field(default_factory=dict)

    def conflicts(self, schedule_dates: List[date]) -> List[str]:
        """
        Return a list of human‑readable labels (date strings) where the schedule
        conflicts with availability.  A conflict occurs when a shift is
        scheduled (not OFF/RTO/blank) and the availability for that day of
        the week is UNAVAILABLE.  The schedule_dates list should contain the
        dates (in order) covering the schedule.
        """
        # Compute a list of labels for dates where the employee is scheduled
        # on a day that their weekly availability marks as UNAVAILABLE.
        conflict_labels: List[str] = []
        for idx, dt in enumerate(schedule_dates):
            # Retrieve the shift for this specific calendar date (using ISO format key).
            shift = self.schedule.get(dt.isoformat(), "").strip()
            # If there is no shift or it is marked OFF or RTO, skip conflict check.
            if not shift or shift.upper() in {"OFF", "RTO"}:
                continue
            # Determine the day of the week relative to the start of the schedule.
            # We use modulo to map the index into our 7‑day availability list (Saturday–Friday).
            day_index = idx % len(DAY_NAMES)
            day_name = DAY_NAMES[day_index]
            # Look up the employee's availability for that day; default to open.
            avail = self.availability.get(day_name, "OPEN AVAILABILITY").strip()
            # If marked UNAVAILABLE, record this date as a conflict.
            if avail.upper() == "UNAVAILABLE":
                conflict_labels.append(dt.strftime("%a %m/%d/%Y"))
        return conflict_labels

    def conflict_indices(self, schedule_dates: List[date]) -> List[int]:
        """
        Return a list of indices (0‑based) into the schedule_dates list
        corresponding to dates where the employee is scheduled on a day that
        conflicts with their weekly availability.  This is useful for
        highlighting specific cells in the schedule grid.
        """
        indices: List[int] = []
        for idx, dt in enumerate(schedule_dates):
            shift = self.schedule.get(dt.isoformat(), "").strip()
            if not shift or shift.upper() in {"OFF", "RTO"}:
                continue
            day_index = idx % len(DAY_NAMES)
            day_name = DAY_NAMES[day_index]
            avail = self.availability.get(day_name, "OPEN AVAILABILITY").strip()
            if avail.upper() == "UNAVAILABLE":
                indices.append(idx)
        return indices


class ScheduleApp(tk.Tk):
    """Main application window for Owen's Magic Schedule Builder."""

    def __init__(self) -> None:
        super().__init__()
        self.title("Owen's Magic Schedule Builder and Conflict Detector")
        # Set a reasonable default window size.  This prevents the window from
        # expanding to accommodate all 21 columns; instead, scrollbars will be
        # used to view content beyond the visible area.
        self.geometry("900x600")
        self.resizable(True, True)

        # Data storage: list of Employee objects
        self.employees: List[Employee] = []

        # Mapping from tree item IDs to employee objects for deletion. This
        # dictionary is rebuilt each time the tree is refreshed.
        self._item_to_employee: Dict[str, Employee] = {}

        # The schedule spans three weeks (21 days) starting from a user‑chosen date.
        # These attributes will be set after the user selects a start date or
        # uploads a CSV.
        self.schedule_dates: List[date] = []
        self.column_ids: List[str] = []
        self.date_labels: List[str] = []

        # Show the start dialog to allow the user to choose how to begin.  We
        # deliberately do not withdraw the main window here; instead, the start
        # dialog will appear on top of an otherwise blank window.  After the
        # user chooses to create a new schedule or upload a CSV, the
        # appropriate callbacks will build the interface and populate data.
        self._show_start_dialog()

    def _build_widgets(self) -> None:
        """Create and pack all widgets based on current schedule dates."""
        # If widgets already exist (e.g. when rebuilding after CSV upload), destroy them
        # to avoid duplicating UI elements and scrollbars.
        if hasattr(self, 'tree'):
            self.tree.destroy()
        if hasattr(self, 'hscroll'):
            self.hscroll.destroy()
        if hasattr(self, 'vscroll'):
            self.vscroll.destroy()
        if hasattr(self, 'tree_frame'):
            self.tree_frame.destroy()
        if hasattr(self, 'btn_frame'):
            self.btn_frame.destroy()

        # Frame for buttons
        btn_frame = tk.Frame(self)
        btn_frame.pack(side=tk.TOP, fill=tk.X, padx=10, pady=5)
        # Keep a reference to this frame for potential future destruction
        self.btn_frame = btn_frame
        tk.Button(btn_frame, text="Add Employee", command=self._add_employee_dialog).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Add/Update Schedule", command=self._add_schedule_dialog).pack(side=tk.LEFT, padx=5)
        # New button to edit availability for existing employees
        tk.Button(btn_frame, text="Edit Availability", command=self._edit_availability_dialog).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Check Conflicts", command=self._check_conflicts).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Export to CSV", command=self._export_to_csv).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Remove Employee", command=self._remove_employee).pack(side=tk.LEFT, padx=5)

        # Determine dynamic columns based on schedule dates.  Use simple IDs for
        # each day column for internal reference.  If no column IDs exist,
        # generate them according to the length of the schedule_dates list.
        if not self.column_ids:
            self.column_ids = [f"day_{i}" for i in range(len(self.schedule_dates))]

        columns = ["last_name", "first_name"] + self.column_ids
        # Frame for tree and vertical scrollbar
        tree_frame = tk.Frame(self)
        tree_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=10, pady=5)
        self.tree_frame = tree_frame
        # Create Treeview inside the frame
        self.tree = ttk.Treeview(tree_frame, columns=columns, show="headings")
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        # Create a vertical scrollbar linked to the Treeview
        self.vscroll = tk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        self.vscroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.configure(yscrollcommand=self.vscroll.set)
        # Create a horizontal scrollbar below the tree (attached to the same frame)
        self.hscroll = tk.Scrollbar(tree_frame, orient="horizontal", command=self.tree.xview)
        self.hscroll.pack(side=tk.BOTTOM, fill=tk.X)
        self.tree.configure(xscrollcommand=self.hscroll.set)

        # Define headings for each column
        self.tree.heading("last_name", text="Last Name")
        self.tree.heading("first_name", text="First Name")
        for idx, col_id in enumerate(self.column_ids):
            label = self.date_labels[idx] if idx < len(self.date_labels) else f"Day {idx+1}"
            self.tree.heading(col_id, text=label)

        # Set column widths and alignment.  Disable stretching so that horizontal
        # scrolling is used when the total width exceeds the viewport.  This
        # prevents columns from compressing when the window is resized.
        self.tree.column("last_name", width=100, anchor="w", stretch=False)
        self.tree.column("first_name", width=100, anchor="w", stretch=False)
        for col_id in self.column_ids:
            self.tree.column(col_id, width=100, anchor="center", stretch=False)

    def _refresh_tree(self) -> None:
        """Refresh the Treeview to reflect current employees and schedules."""
        # Remove all existing rows from the tree.
        for item in self.tree.get_children():
            self.tree.delete(item)
        # Clear the mapping from tree item IDs to Employee objects.
        self._item_to_employee.clear()
        # Determine whether we have schedule dates (21‑day schedule) defined.
        use_dates = bool(self.schedule_dates)
        # Insert one row per employee with schedule values for each date.
        for emp in self.employees:
            # Build the row: compute shifts with conflict markers when schedule dates are defined.
            tags: List[str] = []
            if use_dates:
                # Identify indices of conflict dates
                conflict_idxs = emp.conflict_indices(self.schedule_dates)
                # Build shifts with a warning marker for each conflict cell
                row_shifts = []
                for idx, dt in enumerate(self.schedule_dates):
                    val = emp.schedule.get(dt.isoformat(), "")
                    if idx in conflict_idxs and val:
                        val = "⚠ " + val
                    row_shifts.append(val)
                # Prefix last name with a warning symbol if there is any conflict
                last_name_display = ("⚠ " + emp.last_name) if conflict_idxs else emp.last_name
                # Tag the row as a conflict row if needed
                if conflict_idxs:
                    tags.append("conflict_row")
            else:
                # Fallback to using the 7 standard day names if no schedule dates are set
                row_shifts = [emp.schedule.get(day, "") for day in DAY_NAMES]
                last_name_display = emp.last_name
            values = [last_name_display, emp.first_name] + row_shifts
            # Insert into tree and record mapping from item to employee.
            item_id = self.tree.insert("", "end", values=values, tags=tags)
            self._item_to_employee[item_id] = emp
        # Apply a light red background to rows that have conflicts.
        self.tree.tag_configure("conflict_row", background="#f8d7da")

    def _add_employee_dialog(self) -> None:
        """Show a dialog to add a new employee with availability."""
        dialog = tk.Toplevel(self)
        dialog.title("Add Employee")
        dialog.transient(self)
        dialog.grab_set()

        tk.Label(dialog, text="Last Name:").grid(row=0, column=0, sticky="e", padx=5, pady=3)
        last_name_var = tk.StringVar()
        tk.Entry(dialog, textvariable=last_name_var).grid(row=0, column=1, padx=5, pady=3)

        tk.Label(dialog, text="First Name:").grid(row=1, column=0, sticky="e", padx=5, pady=3)
        first_name_var = tk.StringVar()
        tk.Entry(dialog, textvariable=first_name_var).grid(row=1, column=1, padx=5, pady=3)

        # Availability inputs
        avail_vars: Dict[str, tk.StringVar] = {}
        row_offset = 2
        tk.Label(dialog, text="Availability (choose or leave blank for OPEN AVAILABILITY)").grid(row=row_offset, column=0, columnspan=2, pady=(10, 2))
        for idx, day in enumerate(DAY_NAMES):
            tk.Label(dialog, text=f"{day}:").grid(row=row_offset + 1 + idx, column=0, sticky="e", padx=5, pady=2)
            var = tk.StringVar(value="OPEN AVAILABILITY")
            # Use a Combobox for selecting availability options
            combo = ttk.Combobox(dialog, textvariable=var, values=AVAILABILITY_OPTIONS)
            combo.grid(row=row_offset + 1 + idx, column=1, padx=5, pady=2)
            combo['state'] = 'normal'  # allow typing custom values
            avail_vars[day] = var

        def save_employee() -> None:
            last_name = last_name_var.get().strip()
            first_name = first_name_var.get().strip()
            if not last_name or not first_name:
                messagebox.showerror("Error", "First and last names are required.")
                return
            # Normalise availability: blank means OPEN AVAILABILITY
            availability = {}
            for day in DAY_NAMES:
                val = avail_vars[day].get().strip()
                availability[day] = val if val else "OPEN AVAILABILITY"
            self.employees.append(Employee(last_name=last_name, first_name=first_name, availability=availability))
            self._refresh_tree()
            dialog.destroy()

        btn_frame = tk.Frame(dialog)
        btn_frame.grid(row=row_offset + 1 + len(DAY_NAMES), column=0, columnspan=2, pady=10)
        tk.Button(btn_frame, text="Cancel", command=dialog.destroy).pack(side=tk.RIGHT, padx=5)
        tk.Button(btn_frame, text="Save", command=save_employee).pack(side=tk.RIGHT, padx=5)

    def _add_schedule_dialog(self) -> None:
        """Show a dialog to add or update schedule for a selected employee."""
        # Ensure there is at least one employee before adding schedules.
        if not self.employees:
            messagebox.showinfo("No Employees", "Please add an employee first.")
            return
        # Prompt the user to select which employee's schedule to edit using a simple list with indices.
        names = [f"{emp.first_name} {emp.last_name}" for emp in self.employees]
        index = simpledialog.askinteger(
            "Select Employee",
            "Enter the number of the employee to edit schedule:\n" +
            "\n".join(f"{i+1}. {name}" for i, name in enumerate(names)),
            parent=self,
            minvalue=1,
            maxvalue=len(names)
        )
        if index is None:
            return
        emp = self.employees[index - 1]
        # Build a dialog window for editing the schedule of the selected employee.
        dialog = tk.Toplevel(self)
        dialog.title(f"Schedule for {emp.first_name} {emp.last_name}")
        dialog.transient(self)
        dialog.grab_set()
        tk.Label(dialog, text=(
            "Select or enter a shift for each date.\n"
            "Leave blank to keep the existing value or indicate no shift."
        )).grid(row=0, column=0, columnspan=2, pady=(0, 5))
        # Prepare input variables keyed by ISO date string.
        inputs: Dict[str, tk.StringVar] = {}
        # If schedule dates are defined, use them; otherwise fall back to 7‑day list.
        if self.schedule_dates:
            date_iterable = self.schedule_dates
            label_iterable = self.date_labels
        else:
            # Use current day names and treat them as one week; use dummy dates for keys.
            # Create a list of (key, label) pairs.
            date_iterable = [day for day in DAY_NAMES]
            label_iterable = DAY_NAMES
        # Create entry widgets for each date or day.
        for idx, label in enumerate(label_iterable):
            # Determine the key used to store this schedule entry.
            if self.schedule_dates:
                dt = date_iterable[idx]
                key = dt.isoformat()
                default_val = emp.schedule.get(key, "")
            else:
                day = date_iterable[idx]
                key = day
                default_val = emp.schedule.get(day, "")
            tk.Label(dialog, text=f"{label}:").grid(row=1 + idx, column=0, sticky="e", padx=5, pady=2)
            var = tk.StringVar(value=default_val)
            combo = ttk.Combobox(dialog, textvariable=var, values=SHIFT_OPTIONS)
            combo.grid(row=1 + idx, column=1, padx=5, pady=2)
            combo['state'] = 'normal'  # allow typing custom values
            inputs[key] = var
        # Function to save schedule changes back to the employee.
        def save_schedule() -> None:
            # Iterate over all inputs and update the employee's schedule dictionary.
            for key, var in inputs.items():
                val = var.get().strip()
                if val:
                    emp.schedule[key] = val
                elif key in emp.schedule:
                    # If the cell was cleared, remove the key from the schedule.
                    emp.schedule.pop(key)
            self._refresh_tree()
            dialog.destroy()
        # Buttons for cancel and save actions.
        btn_frame = tk.Frame(dialog)
        btn_frame.grid(row=1 + len(label_iterable), column=0, columnspan=2, pady=10)
        tk.Button(btn_frame, text="Cancel", command=dialog.destroy).pack(side=tk.RIGHT, padx=5)
        tk.Button(btn_frame, text="Save", command=save_schedule).pack(side=tk.RIGHT, padx=5)

    def _check_conflicts(self) -> None:
        """Update row colouring based on conflict detection and show a summary."""
        # Refresh the Treeview to update conflict highlighting before summarising.
        self._refresh_tree()
        # Accumulate conflict summaries for each employee using current schedule dates.
        messages: List[str] = []
        for emp in self.employees:
            if self.schedule_dates:
                conflict_days = emp.conflicts(self.schedule_dates)
            else:
                # If schedule dates are not set, there is no basis for conflict detection.
                conflict_days = []
            if conflict_days:
                messages.append(f"{emp.first_name} {emp.last_name}: {', '.join(conflict_days)}")
        # Display appropriate message based on whether conflicts exist.
        if messages:
            messagebox.showwarning("Conflicts Detected", "The following conflicts were found:\n\n" + "\n".join(messages))
        else:
            messagebox.showinfo("No Conflicts", "No scheduling conflicts were detected.")

    def _export_to_csv(self) -> None:
        """Export the current schedule to a CSV file."""
        # Do not proceed if there is no data to export.
        if not self.employees:
            messagebox.showinfo("No Data", "There is no data to export.")
            return
        # Prompt user for file path.
        file_path = filedialog.asksaveasfilename(
            parent=self,
            title="Save Schedule as CSV",
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
        )
        if not file_path:
            return
        try:
            with open(file_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                # Construct header: Last Name, First Name, then each date string.
                if self.schedule_dates:
                    header = ["Last Name", "First Name"] + [dt.strftime("%m/%d/%Y") for dt in self.schedule_dates]
                else:
                    # Fallback to 7‑day header if schedule dates are not defined.
                    header = ["Last Name", "First Name"] + DAY_NAMES
                # Append availability column headers so that availability can be saved and reloaded.
                header += [f"Availability {day}" for day in DAY_NAMES]
                writer.writerow(header)
                # Write one row per employee with schedule values and availability values.
                for emp in self.employees:
                    if self.schedule_dates:
                        schedule_vals = [emp.schedule.get(dt.isoformat(), "") for dt in self.schedule_dates]
                    else:
                        schedule_vals = [emp.schedule.get(day, "") for day in DAY_NAMES]
                    # Append availability values for each day of the week.
                    avail_vals = [emp.availability.get(day, "OPEN AVAILABILITY") for day in DAY_NAMES]
                    row = [emp.last_name, emp.first_name] + schedule_vals + avail_vals
                    writer.writerow(row)
            messagebox.showinfo("Export Successful", f"Schedule exported to {file_path}")
        except Exception as e:
            messagebox.showerror("Export Failed", f"An error occurred while exporting:\n{e}")

    # ---- Start‑up methods ----
    def _show_start_dialog(self) -> None:
        """
        Display a modal dialog at launch, giving the user a choice to
        create a new schedule (selecting a start date) or upload an
        existing schedule from a CSV file.  This function blocks until
        a choice is made or the dialog is cancelled.  If the user
        cancels, the application will exit.
        """
        dialog = tk.Toplevel(self)
        dialog.title("Start Owen's Schedule Builder")
        dialog.transient(self)
        dialog.grab_set()
        tk.Label(dialog, text="Welcome to Owen's Magic Schedule Builder!\n\nChoose how you'd like to begin.").pack(padx=20, pady=10)

        def on_new() -> None:
            # User opts to create a new schedule.  After selecting a start date,
            # build the interface and refresh the display.
            dialog.destroy()
            self._select_start_date()
            if self.schedule_dates:
                # Rebuild tree to reflect the selected schedule dates.
                if hasattr(self, "tree"):
                    self.tree.destroy()
                self._build_widgets()
                self._refresh_tree()
                self.deiconify()

        def on_upload() -> None:
            # User opts to upload an existing schedule CSV.
            dialog.destroy()
            self._upload_csv()
            # After loading, the UI will already be built by _load_csv().
            # Ensure the main window is visible.
            self.deiconify()

        def on_cancel() -> None:
            dialog.destroy()
            self.destroy()

        btn_frame = tk.Frame(dialog)
        btn_frame.pack(pady=10)
        tk.Button(btn_frame, text="Create New Schedule", command=on_new).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Upload CSV", command=on_upload).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Cancel", command=on_cancel).pack(side=tk.LEFT, padx=5)
        # Wait until the user makes a selection
        self.wait_window(dialog)

    def _select_start_date(self) -> None:
        """
        Present a simple date selection dialog using Comboboxes for year,
        month and day.  Once the user selects a valid date, set up
        schedule dates for three weeks and finish the start‑up process.
        """
        sel = tk.Toplevel(self)
        sel.title("Select Schedule Start Date")
        sel.transient(self)
        sel.grab_set()
        tk.Label(sel, text="Select the first day of the three‑week schedule").grid(row=0, column=0, columnspan=3, pady=(10, 5))
        # Year, month, day comboboxes
        today = date.today()
        years = [str(today.year + i) for i in range(0, 3)]
        months = [f"{i:02d}" for i in range(1, 13)]
        days = [f"{i:02d}" for i in range(1, 32)]
        year_var = tk.StringVar(value=str(today.year))
        month_var = tk.StringVar(value=f"{today.month:02d}")
        day_var = tk.StringVar(value=f"{today.day:02d}")
        ttk.Combobox(sel, values=years, textvariable=year_var, width=5).grid(row=1, column=0, padx=5)
        ttk.Combobox(sel, values=months, textvariable=month_var, width=3).grid(row=1, column=1, padx=5)
        ttk.Combobox(sel, values=days, textvariable=day_var, width=3).grid(row=1, column=2, padx=5)

        def on_ok() -> None:
            try:
                y = int(year_var.get())
                m = int(month_var.get())
                d = int(day_var.get())
                start_dt = date(y, m, d)
            except Exception:
                messagebox.showerror("Invalid Date", "Please select a valid date.", parent=sel)
                return
            sel.destroy()
            self._setup_schedule_dates(start_dt)

        def on_cancel() -> None:
            sel.destroy()
            self.destroy()

        btn_f = tk.Frame(sel)
        btn_f.grid(row=2, column=0, columnspan=3, pady=10)
        tk.Button(btn_f, text="Cancel", command=on_cancel).pack(side=tk.RIGHT, padx=5)
        tk.Button(btn_f, text="OK", command=on_ok).pack(side=tk.RIGHT, padx=5)
        self.wait_window(sel)

    def _setup_schedule_dates(self, start_dt: date) -> None:
        """
        Given a start date, set up the internal list of schedule dates
        covering three weeks (21 days).  This also constructs column IDs
        and human‑readable labels for headings.
        """
        self.schedule_dates = [start_dt + timedelta(days=i) for i in range(21)]
        self.column_ids = [f"day_{i}" for i in range(len(self.schedule_dates))]
        # Format each date as 'Sat 07/26/2023'
        self.date_labels = [dt.strftime("%a %m/%d/%Y") for dt in self.schedule_dates]

    # CSV upload helpers
    def _upload_csv(self) -> None:
        """
        Prompt the user to select a CSV file and load employees, schedule
        dates and schedule data from it.  The CSV is expected to have a
        header row with 'Last Name', 'First Name' followed by 21 date
        columns in a recognisable format (e.g. MM/DD/YYYY).  Each
        subsequent row should contain names followed by shift values.
        Availability information is not imported (default OPEN AVAILABILITY
        is assumed); you can update availability manually after import.
        """
        file_path = filedialog.askopenfilename(
            parent=self,
            title="Open Schedule CSV",
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
        )
        if not file_path:
            # If the user cancels, show a brief message and return to the start dialog.
            messagebox.showinfo("Cancelled", "No file selected. Please choose another option.")
            # Relaunch the start dialog to allow a new selection.
            self._show_start_dialog()
            return
        try:
            self._load_csv(file_path)
        except Exception as exc:
            messagebox.showerror("Import Error", f"Failed to load CSV:\n{exc}")
            # Return to start dialog on failure
            self._show_start_dialog()

    def _load_csv(self, file_path: str) -> None:
        """
        Load schedule data from a CSV file.  The first row should contain
        headers: 'Last Name', 'First Name' followed by 21 date strings.  For
        each subsequent row, the first two values are names and the
        remaining 21 values are shift assignments.  All employees are
        imported with OPEN AVAILABILITY for every day.
        """
        with open(file_path, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            all_rows = list(reader)
        # Remove completely blank rows to avoid misinterpreting empty lines
        rows = [row for row in all_rows if any(cell.strip() for cell in row)]
        if not rows:
            raise ValueError("CSV is empty")
        # Identify the header row.  Look for the first row whose first two cells
        # (case‑insensitive) match 'last name' and 'first name'.  This makes
        # the importer robust to extra explanatory rows or blank lines at the top.
        header_idx = None
        for i, row in enumerate(rows):
            if len(row) >= 2 and row[0].strip().lower() == "last name" and row[1].strip().lower() == "first name":
                header_idx = i
                break
        if header_idx is None:
            raise ValueError("CSV does not contain a valid header row")
        header = rows[header_idx]
        # Trim the rows list to only the data rows following the header
        rows = rows[header_idx + 1:]
        # Ensure the header has at least three columns: last name, first name, and one date
        if len(header) < 3:
            raise ValueError("CSV header must contain at least three columns")
        # Extract and clean the potential date strings from the header (skip first two columns).
        # Ignore any empty strings.  Later we will parse only the first 21 valid dates.
        date_strs = [s.strip() for s in header[2:] if s.strip()]
        if len(date_strs) < 21:
            raise ValueError("CSV must contain at least 21 date columns")
        # Parse the first 21 date strings using several common formats.
        schedule_dates: List[date] = []
        for ds in date_strs[:21]:
            parsed: Optional[date] = None
            for fmt in ("%m/%d/%Y", "%m/%d/%y", "%Y-%m-%d"):
                try:
                    parsed = datetime.strptime(ds, fmt).date()
                    break
                except Exception:
                    continue
            if not parsed:
                raise ValueError(f"Could not parse date '{ds}' in header")
            schedule_dates.append(parsed)
        # Set schedule dates and labels
        self.schedule_dates = schedule_dates
        self.column_ids = [f"day_{i}" for i in range(len(schedule_dates))]
        self.date_labels = [dt.strftime("%a %m/%d/%Y") for dt in schedule_dates]
        # Reset employees list
        self.employees = []
        # Import employee rows
        for row in rows[1:]:
            if not row or all(not cell.strip() for cell in row):
                continue
            last_name = row[0].strip()
            first_name = row[1].strip()
            if not last_name and not first_name:
                continue
            emp = Employee(last_name=last_name, first_name=first_name)
            # Default all availability to OPEN AVAILABILITY
            emp.availability = {day: "OPEN AVAILABILITY" for day in DAY_NAMES}
            # Read shifts for each schedule date
            for idx, dt in enumerate(schedule_dates):
                cell_index = 2 + idx
                if cell_index < len(row):
                    shift_val = row[cell_index].strip()
                    if shift_val:
                        emp.schedule[dt.isoformat()] = shift_val
            # Read availability values if they exist beyond the schedule columns.  Each
            # subsequent column corresponds to a day of the week, in order of
            # DAY_NAMES.  If a value is blank, leave the default OPEN AVAILABILITY.
            avail_start = 2 + len(schedule_dates)
            for i, day in enumerate(DAY_NAMES):
                col_index = avail_start + i
                if col_index < len(row):
                    avail_val = row[col_index].strip()
                    if avail_val:
                        emp.availability[day] = avail_val
            self.employees.append(emp)
        # After loading, (re)build widgets to reflect the imported schedule dates
        # and refresh the tree.  Rebuilding ensures that the columns and headings
        # match the new schedule_dates.  If a Treeview already exists, we destroy
        # it and create a new one.
        if hasattr(self, 'tree'):
            # Remove existing tree widget from the layout
            self.tree.destroy()
        self._build_widgets()
        self._refresh_tree()
        # Ensure the main window becomes visible after loading a CSV.
        try:
            # If the window is currently withdrawn, deiconify it.
            if not self.winfo_viewable():
                self.deiconify()
        except Exception:
            pass

    def _remove_employee(self) -> None:
        """Remove the selected employee(s) from the list and refresh the view."""
        selected_items = self.tree.selection()
        if not selected_items:
            messagebox.showinfo("Remove Employee", "Please select a row to remove.")
            return
        # Confirm deletion
        if not messagebox.askyesno("Confirm Deletion", "Are you sure you want to remove the selected employee(s)?"):
            return
        # Remove each selected employee
        for item_id in selected_items:
            emp = self._item_to_employee.get(item_id)
            if emp and emp in self.employees:
                self.employees.remove(emp)
        self._refresh_tree()

    def _edit_availability_dialog(self) -> None:
        """Show a dialog to edit the availability of an existing employee."""
        if not self.employees:
            messagebox.showinfo("No Employees", "Please add an employee first.")
            return
        # Prompt the user to select which employee's availability to edit
        names = [f"{emp.first_name} {emp.last_name}" for emp in self.employees]
        index = simpledialog.askinteger(
            "Select Employee",
            "Enter the number of the employee to edit availability:\n" +
            "\n".join(f"{i+1}. {name}" for i, name in enumerate(names)),
            parent=self,
            minvalue=1,
            maxvalue=len(names)
        )
        if index is None:
            return
        emp = self.employees[index - 1]
        # Create dialog window
        dialog = tk.Toplevel(self)
        dialog.title(f"Edit Availability for {emp.first_name} {emp.last_name}")
        dialog.transient(self)
        dialog.grab_set()
        tk.Label(dialog, text="Select new availability for each day. Leave blank for OPEN AVAILABILITY.").grid(row=0, column=0, columnspan=2, pady=(0, 5))
        # Dict to store variables for each day
        avail_vars: Dict[str, tk.StringVar] = {}
        for idx, day in enumerate(DAY_NAMES):
            tk.Label(dialog, text=f"{day}:").grid(row=1 + idx, column=0, sticky="e", padx=5, pady=2)
            var = tk.StringVar(value=emp.availability.get(day, "OPEN AVAILABILITY"))
            combo = ttk.Combobox(dialog, textvariable=var, values=AVAILABILITY_OPTIONS)
            combo.grid(row=1 + idx, column=1, padx=5, pady=2)
            combo['state'] = 'normal'
            avail_vars[day] = var
        # Save function
        def save_availability() -> None:
            for day in DAY_NAMES:
                val = avail_vars[day].get().strip()
                if val:
                    emp.availability[day] = val
                else:
                    emp.availability[day] = "OPEN AVAILABILITY"
            self._refresh_tree()
            dialog.destroy()
        # Buttons
        btn_frame = tk.Frame(dialog)
        btn_frame.grid(row=1 + len(DAY_NAMES), column=0, columnspan=2, pady=10)
        tk.Button(btn_frame, text="Cancel", command=dialog.destroy).pack(side=tk.RIGHT, padx=5)
        tk.Button(btn_frame, text="Save", command=save_availability).pack(side=tk.RIGHT, padx=5)


def main() -> None:
    app = ScheduleApp()
    app.mainloop()


if __name__ == "__main__":
    main()
