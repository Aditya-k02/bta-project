import tkinter as tk
from tkinter import ttk
import math

# ==========================================================
# CORE LOGIC CLASSES
# ==========================================================

class Node:
    """ Represents a single general/process in the simulation. """
    def __init__(self, node_id, x, y):
        self.id = node_id
        self.x = x
        self.y = y
        self.radius = 30
        
        self.is_sender = False
        self.is_faulty = False
        
        # Key: "0-1-2" (path), Value: "Attack"
        self.message_log = {}
        self.final_decision = None

    def get_faulty_value(self, original_value, target_node_id):
        """ If faulty, send a conflicting value. """
        if not self.is_faulty:
            return original_value  # Honest nodes always tell the truth

        # Byzantine logic: send "Attack" to even, "Retreat" to odd
        return 'Attack' if target_node_id % 2 == 0 else 'Retreat'

    def run_decision(self, F, sender_node_id):
        """ Starts the recursive decision process. """
        initial_path = [sender_node_id]
        self.final_decision = self.resolve_decision(initial_path, F)

    def resolve_decision(self, path, f):
        """ The recursive "majority" function from the OM(F) algorithm. """
        path_str = '-'.join(map(str, path))
        v = self.message_log.get(path_str) # Value from this path

        # OM(0) base case
        if f == 0:
            return v

        # Recursive step
        values = [v]  # Start with the value from the current "sender"
        
        # Collect values from all "lieutenants"
        global_nodes = app.nodes # Access the global list of nodes
        for node in global_nodes:
            if node.id != self.id and node.id not in path:
                child_path = path + [node.id]
                child_path_str = '-'.join(map(str, child_path))
                
                if child_path_str in self.message_log:
                    # Recurse: OM(f-1)
                    values.append(self.resolve_decision(child_path, f - 1))
        
        return get_majority(values)

    def draw(self, canvas):
        """ Draws the node on the tkinter canvas. """
        x0, y0 = self.x - self.radius, self.y - self.radius
        x1, y1 = self.x + self.radius, self.y + self.radius
        
        # Determine color
        if self.is_sender:
            fill = '#90EE90'  # Light Green
        elif self.is_faulty:
            fill = '#F08080'  # Light Red
        else:
            fill = '#ADD8E6'  # Light Blue
            
        canvas.create_oval(x0, y0, x1, y1, fill=fill, outline='black', width=2)
        
        # Draw Node ID
        canvas.create_text(self.x, self.y - 10, text=str(self.id), 
                           font=('Helvetica', 16, 'bold'))
        
        # Draw Final Decision
        if self.final_decision:
            color = '#B22222' if self.final_decision == 'Attack' else '#00008B'
            canvas.create_text(self.x, self.y + 15, text=self.final_decision,
                               font=('Helvetica', 12), fill=color)

class Message:
    """ Represents a message in transit for animation. """
    def __init__(self, from_node, to_node, value, path):
        self.from_node = from_node
        self.to_node = to_node
        self.value = value
        self.path = path
    
    def draw(self, canvas):
        """ Draws the message line on the canvas. """
        color = '#C80000' if self.value == 'Attack' else '#0000C8'
        
        canvas.create_line(self.from_node.x, self.from_node.y,
                           self.to_node.x, self.to_node.y,
                           fill=color, width=1.5, arrow=tk.LAST)

def get_majority(values):
    """ Global helper function to find the majority in a list of values. """
    counts = {'Attack': 0, 'Retreat': 0}
    for v in values:
        if v == 'Attack':
            counts['Attack'] += 1
        elif v == 'Retreat':
            counts['Retreat'] += 1
            
    # The 'default' value is 'Retreat' in case of a tie or no clear winner
    if counts['Attack'] > len(values) / 2:
        return 'Attack'
    return 'Retreat' # Default to Retreat

# ==========================================================
# MAIN GUI APPLICATION
# ==========================================================

class ByzantineGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Byzantine Broadcast (OM) Demo")
        self.geometry("900x650")

        # Simulation state
        self.nodes = []
        self.messages = []
        self.max_faulty = 1
        self.total_nodes = 4
        self.current_faulty = 0
        self.sender_id = 0
        self.current_round = 0
        self.simulation_state = 'setup' # 'setup', 'ready', 'running', 'finished'

        # --- Control Panel (Left) ---
        self.control_frame = ttk.Frame(self, padding=20)
        self.control_frame.pack(side=tk.LEFT, fill=tk.Y)

        ttk.Label(self.control_frame, text="Controls", 
                  font=('Helvetica', 16, 'bold')).pack(pady=10)

        # F (Faulty Nodes)
        f_frame = ttk.Frame(self.control_frame)
        ttk.Label(f_frame, text="Faulty Nodes (F):").pack(side=tk.LEFT, padx=5)
        self.f_var = tk.IntVar(value=1)
        self.f_combo = ttk.Combobox(f_frame, textvariable=self.f_var, 
                                    values=[1, 2], width=5, state='readonly')
        self.f_combo.pack(side=tk.LEFT)
        # Bind the F change event
        self.f_combo.bind('<<ComboboxSelected>>', self.on_f_changed)
        f_frame.pack(fill=tk.X, pady=5)

        # N (Total Nodes) - CHANGED TO ENTRY
        n_frame = ttk.Frame(self.control_frame)
        ttk.Label(n_frame, text="Total Nodes (N):").pack(side=tk.LEFT, padx=5)
        self.n_var = tk.StringVar(value='4') # Use StringVar
        self.n_entry = ttk.Entry(n_frame, textvariable=self.n_var, width=7)
        self.n_entry.pack(side=tk.LEFT)
        n_frame.pack(fill=tk.X, pady=5)

        # Sender Value
        val_frame = ttk.LabelFrame(self.control_frame, text="Sender (Node 0) Value")
        self.sender_value_var = tk.StringVar(value='Attack')
        ttk.Radiobutton(val_frame, text="Attack", variable=self.sender_value_var, 
                        value='Attack').pack(anchor=tk.W)
        ttk.Radiobutton(val_frame, text="Retreat", variable=self.sender_value_var, 
                        value='Retreat').pack(anchor=tk.W)
        val_frame.pack(fill=tk.X, pady=10)

        # Buttons
        self.setup_button = ttk.Button(self.control_frame, text="Setup / Reset", 
                                       command=self.setup_simulation)
        self.setup_button.pack(fill=tk.X, pady=5)
        
        self.next_round_button = ttk.Button(self.control_frame, text="Next Round", 
                                            command=self.run_next_round)
        self.next_round_button.pack(fill=tk.X, pady=5)

        ttk.Separator(self.control_frame, orient='horizontal').pack(fill=tk.X, pady=10)

        # Info Panel
        info_frame = ttk.Frame(self.control_frame)
        ttk.Label(info_frame, text="Click nodes to make them faulty.", 
                  font=('Helvetica', 10, 'italic')).pack()
        ttk.Label(info_frame, text="(Sender Node 0 cannot be faulty)", 
                  font=('Helvetica', 10, 'italic')).pack()
        self.faulty_count_label = ttk.Label(info_frame, text="Faulty: 0 / 1")
        self.faulty_count_label.pack(pady=5)
        info_frame.pack(fill=tk.X, pady=10)

        ttk.Separator(self.control_frame, orient='horizontal').pack(fill=tk.X, pady=10)

        # Status Panel
        status_frame = ttk.LabelFrame(self.control_frame, text="Status")
        self.sim_state_label = ttk.Label(status_frame, text="State: setup")
        self.sim_state_label.pack(anchor=tk.W)
        self.round_num_label = ttk.Label(status_frame, text="Round: 0")
        self.round_num_label.pack(anchor=tk.W)
        status_frame.pack(fill=tk.X, pady=10)

        # --- Canvas (Right) ---
        self.canvas = tk.Canvas(self, width=600, height=600, bg='white', 
                                borderwidth=2, relief='sunken')
        self.canvas.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, 
                         padx=20, pady=20)
        self.canvas.bind('<Button-1>', self.on_canvas_click)

        # Initial setup
        self.on_f_changed() # Set initial N and call setup_simulation

    def on_f_changed(self, event=None):
        """ Updates N entry when F is changed. """
        self.max_faulty = self.f_var.get()
        min_n = 3 * self.max_faulty + 1
        # Set the N var to the minimum, user can override
        self.n_var.set(str(min_n))
        self.setup_simulation() # Reset when F is changed

    def setup_simulation(self):
        """ Resets and initializes the simulation based on controls. """
        self.max_faulty = self.f_var.get()
        
        # --- VALIDATION BLOCK ---
        min_n = 3 * self.max_faulty + 1
        try:
            n_input = int(self.n_var.get())
            if n_input < min_n:
                self.sim_state_label.config(text=f"State: Error! N must be >= {min_n}")
                self.canvas.delete(tk.ALL) # Clear canvas
                self.nodes = []
                self.messages = []
                return # Stop setup
            self.total_nodes = n_input
        except ValueError:
            self.sim_state_label.config(text="State: Error! N must be a number")
            self.canvas.delete(tk.ALL) # Clear canvas
            self.nodes = []
            self.messages = []
            return # Stop setup
        # --- END VALIDATION ---
            
        self.sender_value = self.sender_value_var.get()
        
        self.nodes = []
        self.messages = []
        self.current_round = 0
        self.current_faulty = 0
        self.simulation_state = 'ready'

        # Create nodes in a circle
        center_x, center_y = 300, 300
        layout_radius = 250
        
        for i in range(self.total_nodes):
            angle = 2 * math.pi * i / self.total_nodes - math.pi / 2
            x = center_x + layout_radius * math.cos(angle)
            y = center_y + layout_radius * math.sin(angle)
            self.nodes.append(Node(i, x, y))
        
        self.nodes[self.sender_id].is_sender = True
        
        self.update_ui_state()
        self.draw_canvas()

    def run_next_round(self):
        """ Runs one round of the message-passing algorithm. """
        if self.simulation_state == 'finished' or self.simulation_state != 'running':
             # Prevent running if not 'running' (e.g., if in 'ready' or 'error')
            if self.simulation_state == 'ready':
                self.simulation_state = 'running' # Start the simulation
            else:
                return
            
        self.current_round += 1
        self.messages = [] # Clear previous round's messages

        if self.current_round == 1:
            # === ROUND 1 (OM(F)): Sender sends to all Lieutenants ===
            sender = self.nodes[self.sender_id]
            path = [sender.id]
            
            for node in self.nodes:
                if node.id == sender.id:
                    continue
                # Get the value (could be a lie if sender is faulty)
                value_to_send = sender.get_faulty_value(self.sender_value, node.id)
                self.messages.append(Message(sender, node, value_to_send, path))
        
        elif self.current_round <= self.max_faulty + 1:
            # === ROUNDS 2 to F+1 (OM(F-1) ... OM(0)): Relays ===
            for sender_node in self.nodes:
                # Find messages sender_node received in the *previous* round
                for path_str, value in sender_node.message_log.items():
                    path = list(map(int, path_str.split('-')))
                    
                    if len(path) == self.current_round - 1:
                        # Relay this value
                        for receiver_node in self.nodes:
                            if receiver_node.id != sender_node.id and receiver_node.id not in path:
                                value_to_send = sender_node.get_faulty_value(value, receiver_node.id)
                                new_path = path + [sender_node.id]
                                self.messages.append(Message(sender_node, receiver_node, value_to_send, new_path))
        
        # Deliver all messages after creating them
        self.deliver_messages()

        # Check if simulation is over
        if self.current_round > self.max_faulty:
            self.simulation_state = 'finished'
            # All rounds are done, now everyone decides
            for node in self.nodes:
                if not node.is_faulty:
                    node.run_decision(self.max_faulty, self.sender_id)
        
        self.update_ui_state()
        self.draw_canvas()

    def deliver_messages(self):
        """ Moves animated messages into the nodes' message logs. """
        for msg in self.messages:
            path_string = '-'.join(map(str, msg.path))
            msg.to_node.message_log[path_string] = msg.value

    def update_ui_state(self):
        """ Updates all text labels and button states. """
        # Don't overwrite error messages
        if "Error" not in self.sim_state_label.cget("text"):
             self.sim_state_label.config(text=f"State: {self.simulation_state}")
             
        self.faulty_count_label.config(text=f"Faulty: {self.current_faulty} / {self.max_faulty}")
        self.round_num_label.config(text=f"Round: {self.current_round}")

        if self.simulation_state == 'ready':
            self.next_round_button.config(text="Start (Round 1)", state=tk.NORMAL)
            self.setup_button.config(state=tk.NORMAL)
        elif self.simulation_state == 'running':
            next_text = f"Next (Round {self.current_round + 1})"
            if self.current_round > self.max_faulty:
                next_text = "Show Decision"
            self.next_round_button.config(text=next_text, state=tk.NORMAL)
            self.setup_button.config(state=tk.DISABLED)
        elif self.simulation_state == 'finished':
            self.next_round_button.config(text="Finished", state=tk.DISABLED)
            self.setup_button.config(state=tk.NORMAL)
        else: # Error state
            self.next_round_button.config(state=tk.DISABLED)
            self.setup_button.config(state=tk.NORMAL)


    def on_canvas_click(self, event):
        """ Handles clicking on nodes to toggle their faulty status. """
        if self.simulation_state != 'ready':
            return # Can only change faulty status during setup
            
        for node in self.nodes:
            dist_sq = (event.x - node.x)**2 + (event.y - node.y)**2
            if dist_sq <= node.radius**2:
                if node.is_sender:
                    return # Sender cannot be faulty
                
                if node.is_faulty:
                    node.is_faulty = False
                    self.current_faulty -= 1
                elif self.current_faulty < self.max_faulty:
                    node.is_faulty = True
                    self.current_faulty += 1
                
                self.update_ui_state()
                self.draw_canvas() # Redraw to show color change
                break

    def draw_canvas(self):
        """ Clears and redraws the entire canvas. """
        self.canvas.delete(tk.ALL)
        
        # Draw messages first (so they are "under" the nodes)
        for msg in self.messages:
            msg.draw(self.canvas)
            
        # Draw all nodes
        for node in self.nodes:
            node.draw(self.canvas)
            
    def run(self):
        self.mainloop()

# ==========================================================
# RUN THE APPLICATION
# ==========================================================

if __name__ == "__main__":
    app = ByzantineGUI()
    app.run()
