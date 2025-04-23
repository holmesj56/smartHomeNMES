import tkinter as tk
from tkinter import ttk, messagebox
import pandas as pd
import os
import subprocess

class NMESApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("NMES Controller")
        self.current_user = None
        self.setup_ui()
        self.check_data_files()
        
    def check_data_files(self):
        if not os.path.exists('user_ids.xlsx'):
            data = {'UserID': ['NMES001', 'NMES002', 'NMES003', 'TEST123']}
            pd.DataFrame(data).to_excel('user_ids.xlsx', index=False)

    def setup_ui(self):
        self.root.geometry("800x600")
        self.root.configure(bg='#0077cc')
        
        self.container = tk.Frame(self.root, bg='#0077cc')
        self.container.pack(expand=True, fill='both', padx=20, pady=20)
        
        # Create all pages
        self.start_page = StartPage(self.container, self)
        self.login_page = LoginPage(self.container, self)
        self.muscle_page = MuscleGroupPage(self.container, self)
        self.forearms_page = ForearmsGamesPage(self.container, self)
        self.biceps_page = BicepsGamesPage(self.container, self)
        
        for page in (self.start_page, self.login_page, self.muscle_page, 
                    self.forearms_page, self.biceps_page):
            page.grid(row=0, column=0, sticky="nsew")
        
        self.show_page(self.start_page)
    
    def show_page(self, page):
        page.tkraise()
        if hasattr(page, 'update_welcome_message') and hasattr(self, 'current_user'):
            page.update_welcome_message(self.current_user)
    
    def verify_user(self, user_id):
        try:
            df = pd.read_excel('user_ids.xlsx')
            if user_id in df['UserID'].values:
                self.current_user = user_id
                self.show_page(self.muscle_page)
                return True
            messagebox.showerror("Error", "Invalid User ID")
            return False
        except Exception as e:
            messagebox.showerror("Error", f"Database error: {str(e)}")
            return False
    
    def select_muscle_group(self, muscle_group):
        if muscle_group == "forearms":
            self.show_page(self.forearms_page)
        elif muscle_group == "biceps":
            self.show_page(self.biceps_page)
    
    def launch_game(self, game_script):
        try:
            subprocess.Popen(["python", game_script])
        except Exception as e:
            messagebox.showerror("Error", f"Failed to launch game: {str(e)}")

    def run(self):
        self.root.mainloop()

class StartPage(tk.Frame):
    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent, bg='#0077cc')
        self.controller = controller
        
        # Title
        self.title_label = tk.Label(
            self, text="NMES Controller", 
            font=('Arial', 24, 'bold'), bg='#0077cc', fg='white'
        )
        self.title_label.pack(pady=(50, 30))
        
        # Status frame
        self.status_frame = tk.Frame(self, bg='#0077cc')
        self.status_frame.pack(pady=20)
        
        self.status_label = tk.Label(
            self.status_frame, text="Status:", 
            font=('Arial', 16), bg='#0077cc', fg='white'
        )
        self.status_label.pack(side='left')
        
        self.status_indicator = tk.Label(
            self.status_frame, text="Disconnected", 
            font=('Arial', 16), bg='red', fg='white', width=15
        )
        self.status_indicator.pack(side='left', padx=10)
        
        # Connection button (demo)
        self.connect_btn = tk.Button(
            self, text="Connect Device", 
            font=('Arial', 14), bg='#4CAF50', fg='white',
            command=self.toggle_connection
        )
        self.connect_btn.pack(pady=20)
        
        # Start button
        self.start_btn = tk.Button(
            self, text="START", 
            font=('Arial', 18, 'bold'), bg='#2196F3', fg='white',
            width=15, height=2,
            command=lambda: controller.show_page(controller.login_page)
        )
        self.start_btn.pack(pady=30)
    
    def toggle_connection(self):
        current = self.status_indicator.cget('text')
        if current == "Disconnected":
            self.status_indicator.config(text="Connected", bg='green')
            self.start_btn.config(state='normal')
        else:
            self.status_indicator.config(text="Disconnected", bg='red')
            self.start_btn.config(state='disabled')

class LoginPage(tk.Frame):
    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent, bg='#0077cc')
        self.controller = controller
        
        # Title
        self.title_label = tk.Label(
            self, text="User Login", 
            font=('Arial', 24, 'bold'), bg='#0077cc', fg='white'
        )
        self.title_label.pack(pady=(50, 30))
        
        # User ID entry
        self.user_frame = tk.Frame(self, bg='#0077cc')
        self.user_frame.pack(pady=20)
        
        tk.Label(
            self.user_frame, text="User ID:", 
            font=('Arial', 16), bg='#0077cc', fg='white'
        ).pack(side='left')
        
        self.user_entry = ttk.Entry(self.user_frame, font=('Arial', 16), width=15)
        self.user_entry.pack(side='left', padx=10)
        self.user_entry.focus()
        
        # Login button
        self.login_btn = tk.Button(
            self, text="LOGIN", 
            font=('Arial', 16), bg='#4CAF50', fg='white',
            command=self.verify_user
        )
        self.login_btn.pack(pady=30)
        
        # Back button
        self.back_btn = tk.Button(
            self, text="Back", 
            font=('Arial', 12), bg='#f44336', fg='white',
            command=lambda: controller.show_page(controller.start_page)
        )
        self.back_btn.pack()
        
        # Sample IDs
        tk.Label(
            self, text="Sample IDs: NMES001, NMES002, NMES003, TEST123", 
            font=('Arial', 12), bg='#0077cc', fg='white'
        ).pack(pady=20)
    
    def verify_user(self):
        user_id = self.user_entry.get()
        if user_id:
            self.controller.verify_user(user_id)
        else:
            messagebox.showerror("Error", "Please enter a User ID")

class MuscleGroupPage(tk.Frame):
    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent, bg='#0077cc')
        self.controller = controller
        
        # Welcome message
        self.welcome_var = tk.StringVar()
        self.welcome_var.set("Welcome")
        
        self.welcome_label = tk.Label(
            self, textvariable=self.welcome_var, 
            font=('Arial', 18), bg='#0077cc', fg='white'
        )
        self.welcome_label.pack(pady=(30, 10))
        
        # Title
        tk.Label(
            self, text="Select Muscle Group", 
            font=('Arial', 20, 'bold'), bg='#0077cc', fg='white'
        ).pack(pady=20)
        
        # Buttons frame
        self.btn_frame = tk.Frame(self, bg='#0077cc')
        self.btn_frame.pack(pady=30)
        
        # Forearms button
        tk.Button(
            self.btn_frame, text="FOREARMS", 
            font=('Arial', 16, 'bold'), bg='#FF9800', fg='white',
            width=15, height=2,
            command=lambda: controller.select_muscle_group("forearms")
        ).pack(pady=10)
        
        # Biceps button
        tk.Button(
            self.btn_frame, text="BICEPS", 
            font=('Arial', 16, 'bold'), bg='#2196F3', fg='white',
            width=15, height=2,
            command=lambda: controller.select_muscle_group("biceps")
        ).pack(pady=10)
        
        # Back button
        tk.Button(
            self, text="Back", 
            font=('Arial', 12), bg='#f44336', fg='white',
            command=lambda: controller.show_page(controller.login_page)
        ).pack(pady=20)
    
    def update_welcome_message(self, user_id):
        self.welcome_var.set(f"Welcome, {user_id}")

class BaseGamesPage(tk.Frame):
    def __init__(self, parent, controller, muscle_group):
        tk.Frame.__init__(self, parent, bg='#0077cc')
        self.controller = controller
        self.muscle_group = muscle_group
        
        # Title
        tk.Label(
            self, text=f"{muscle_group.upper()} GAMES", 
            font=('Arial', 20, 'bold'), bg='#0077cc', fg='white'
        ).pack(pady=(30, 20))
        
        # Games frame
        self.games_frame = tk.Frame(self, bg='#0077cc')
        self.games_frame.pack(pady=20)
        
        # Back button
        tk.Button(
            self, text="Back to Muscle Groups", 
            font=('Arial', 12), bg='#f44336', fg='white',
            command=lambda: controller.show_page(controller.muscle_page)
        ).pack(pady=20)
    
    def create_game_button(self, frame, text, command, color):
        return tk.Button(
            frame, text=text, 
            font=('Arial', 14, 'bold'), bg=color, fg='white',
            width=20, height=2, command=command
        )

class ForearmsGamesPage(BaseGamesPage):
    def __init__(self, parent, controller):
        super().__init__(parent, controller, "forearms")
        
        # Game 1 - Trainer
        self.create_game_button(
            self.games_frame, "Forearm Trainer", 
            lambda: controller.launch_game("forearm_trainer.py"),
            "#4CAF50"
        ).pack(pady=10)
        
        # Game 2 - Balloon Game
        self.create_game_button(
            self.games_frame, "Balloon Game", 
            lambda: controller.launch_game("forearm_balloon.py"),
            "#FF9800"
        ).pack(pady=10)

class BicepsGamesPage(BaseGamesPage):
    def __init__(self, parent, controller):
        super().__init__(parent, controller, "biceps")
        
        # Game 1 - Strength Meter
        self.create_game_button(
            self.games_frame, "Strength Meter", 
            lambda: controller.launch_game("biceps_strength.py"),
            "#2196F3"
        ).pack(pady=10)
        
        # Game 2 - Pong Game
        self.create_game_button(
            self.games_frame, "Arm Pong Game", 
            lambda: controller.launch_game("biceps_pong.py"),
            "#9C27B0"
        ).pack(pady=10)

if __name__ == "__main__":
    app = NMESApp()
    app.run()