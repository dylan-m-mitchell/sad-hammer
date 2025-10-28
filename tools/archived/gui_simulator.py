#!/usr/bin/env python3
"""A small Tkinter GUI to load a BattleScribe roster and run the interactive simulator.

This is intentionally lightweight and depends only on the standard library plus
the project's existing modules (`battlescribe_parser.py` and
`interactive_simulator.py`). The simulator is executed in a background thread
and its stdout is captured and displayed in the text area.
"""

import io
import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from contextlib import redirect_stdout

# Ensure local imports work when running from the project root
import os
ROOT = os.path.abspath(os.path.dirname(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from battlescribe_parser import parse_battlescribe_html
import interactive_simulator as sim_mod


class SimulatorGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title('Sad Hammer  Solo Simulator')
        self.geometry('900x600')

        # Top frame: roster controls
        top = ttk.Frame(self)
        top.pack(fill='x', padx=8, pady=6)

        ttk.Label(top, text='Roster:').pack(side='left')
        self.roster_var = tk.StringVar()
        self.roster_entry = ttk.Entry(top, textvariable=self.roster_var, width=60)
        self.roster_entry.pack(side='left', padx=(6, 6))
        ttk.Button(top, text='Browse', command=self.browse_roster).pack(side='left')
        ttk.Button(top, text='Load', command=self.load_roster).pack(side='left', padx=6)

        # Middle frame: units and controls
        mid = ttk.Frame(self)
        mid.pack(fill='both', expand=True, padx=8, pady=6)

        left = ttk.Frame(mid)
        left.pack(side='left', fill='y')
        ttk.Label(left, text='Player Units').pack()
        self.unit_list = tk.Listbox(left, width=40, height=20)
        self.unit_list.pack(side='left', fill='y')
        # Add placeholder so the GUI isn't visually empty on first open
        self.unit_list.insert(tk.END, 'No roster loaded  click Browse and Load to import a BattleScribe HTML roster')

        right = ttk.Frame(mid)
        right.pack(side='left', fill='both', expand=True)

        # simulation controls
        ctrl = ttk.Frame(right)
        ctrl.pack(fill='x')
        ttk.Label(ctrl, text='Turns:').pack(side='left')
        self.turns_var = tk.IntVar(value=5)
        ttk.Spinbox(ctrl, from_=1, to=50, textvariable=self.turns_var, width=5).pack(side='left', padx=6)
        ttk.Label(ctrl, text='Seed:').pack(side='left')
        self.seed_var = tk.IntVar(value=1)
        ttk.Entry(ctrl, textvariable=self.seed_var, width=8).pack(side='left', padx=(6, 12))

        self.run_btn = ttk.Button(ctrl, text='Run Simulation', command=self.run_simulation)
        self.run_btn.pack(side='left')
        ttk.Button(ctrl, text='Clear Log', command=self.clear_log).pack(side='left', padx=6)

        # log text widget
        self.log = tk.Text(right, wrap='word')
        self.log.pack(fill='both', expand=True, pady=(8, 0))
        self.log.configure(state='disabled')

        # internal state
        self.player_units = []
        self.ai_units = []
        self._sim_thread = None
        # initial log instruction
        self.append_log('Welcome  load a roster (Browse -> Load) and press Run Simulation.')

    def browse_roster(self):
        path = filedialog.askopenfilename(title='Select BattleScribe HTML roster', filetypes=[('HTML files', '*.html'), ('All files', '*.*')])
        if path:
            self.roster_var.set(path)

    def load_roster(self):
        path = self.roster_var.get().strip()
        if not path:
            messagebox.showwarning('No roster', 'Please select a roster file first')
            return
        try:
            units = parse_battlescribe_html(path)
        except Exception as e:
            messagebox.showerror('Parse error', f'Failed to parse roster: {e}')
            return

        # build interactive_simulator.Unit instances
        self.player_units = []
        for u in units:
            unit = sim_mod.Unit(u['name'], models=u.get('models', 1), wounds_per_model=u.get('wounds_per_model', 1),
                                attacks=u.get('attacks', 1), to_hit=u.get('to_hit', 4), to_wound=u.get('to_wound', 4),
                                save=u.get('save', 6))
            setattr(unit, 'weapons', u.get('weapons', []))
            self.player_units.append(unit)

        # fill listbox
        self.unit_list.delete(0, tk.END)
        for u in self.player_units:
            self.unit_list.insert(tk.END, f"{u.name}  {u.models_remaining} models, {u.current_wounds} wounds")

        # populate AI units with sample armies for now
        _, self.ai_units = sim_mod.sample_armies()
        self.append_log(f'Loaded {len(self.player_units)} player units from {os.path.basename(path)}')

    def append_log(self, text: str):
        self.log.configure(state='normal')
        self.log.insert('end', text + '\n')
        self.log.see('end')
        self.log.configure(state='disabled')

    def clear_log(self):
        self.log.configure(state='normal')
        self.log.delete('1.0', 'end')
        self.log.configure(state='disabled')

    def _sim_worker(self, turns: int, seed: int):
        # Run the simulator with a structured event callback
        if not self.player_units:
            self.append_log('No player units loaded  aborting simulation')
            return

        def event_cb(ev: dict):
            # Schedule GUI updates on the main thread via `after`
            self.after(0, self._handle_event, ev)

        try:
            sim_mod.run_simulation(self.player_units, self.ai_units, turns=turns, seed=seed, auto=True, event_callback=event_cb)
        except Exception as e:
            self.after(0, self.append_log, f'Simulation error: {e}')

    def _handle_event(self, ev: dict):
        # Central handler for structured events emitted by the simulator
        etype = ev.get('type')
        if etype in ('aggression_check', 'ai_action', 'combat', 'player_attack'):
            self.append_log(ev.get('text', str(ev)))
        elif etype == 'summary':
            # a summary event contains multiple lines
            for line in ev.get('lines', []):
                self.append_log(line)
        elif etype == 'finished':
            self.append_log(ev.get('text', 'Simulation finished.'))
        else:
            # generic fallback
            self.append_log(str(ev))

    def run_simulation(self):
        if self._sim_thread and self._sim_thread.is_alive():
            messagebox.showinfo('Simulation running', 'A simulation is already running')
            return

        turns = int(self.turns_var.get())
        seed = int(self.seed_var.get())

        self.append_log(f'Starting simulation: turns={turns} seed={seed}')
        self._sim_thread = threading.Thread(target=self._sim_worker, args=(turns, seed), daemon=True)
        self._sim_thread.start()


def main():
    app = SimulatorGUI()
    app.mainloop()


if __name__ == '__main__':
    main()
