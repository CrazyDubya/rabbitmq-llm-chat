#import os
import tkinter as tk
from tkinter import filedialog, simpledialog

class ChatLogger:
    def __init__(self):
        self.chat_log = ""
        self.chat_participants = {
            1: "ChatGPT",
            2: "Claude-Opus",
            3: "Mixtral",
            4: "Mistral",
            5: "Human"
        }
        self.chat_file_path = ""

    def start_new_chat(self):
        if tk.messagebox.askyesno("New Chat", "Are you sure you want to start a new chat? This will clear chat log."):
            self.chat_log = ""
            self.chat_file_path = ""
            self.update_chat_display()

    def load_previous_chat(self):
        file_path = filedialog.askopenfilename(filetypes=[("Text Files", "*.txt")])
        if file_path:
            with open(file_path, "r") as file:
                self.chat_log = file.read()
            self.chat_file_path = file_path
            self.update_chat_display()

    def select_participant(self):
        participant_window = tk.Toplevel(root)
        participant_window.title("Select Chat Participant")

        selected_participant = tk.StringVar(participant_window)
        selected_participant.set(next(iter(self.chat_participants.values())))  # Set default selection

        tk.Label(participant_window, text="Select a chat participant:").pack()
        participant_dropdown = tk.OptionMenu(participant_window, selected_participant, *self.chat_participants.values())
        participant_dropdown.pack()

        def confirm_participant():
            participant = selected_participant.get()
            participant_window.destroy()
            self.add_chat_entry(participant)

        tk.Button(participant_window, text="Confirm", command=confirm_participant).pack()

    def add_chat_entry(self, participant):
        entry = simpledialog.askstring("Chat Entry", f"Enter the chat entry for {participant}:")
        if entry:
            self.chat_log += f"{participant}: {entry}\n"
            self.update_chat_display()
            self.save_chat_log()

    def update_chat_display(self):
        chat_display.config(state=tk.NORMAL)
        chat_display.delete("1.0", tk.END)
        chat_display.insert(tk.END, self.chat_log)
        chat_display.config(state=tk.DISABLED)

    def save_chat_log(self):
        if not self.chat_file_path:
            self.chat_file_path = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Text Files", "*.txt")])
        if self.chat_file_path:
            with open(self.chat_file_path, "w") as file:
                file.write(self.chat_log)


# Create the main window
root = tk.Tk()
root.title("Chat Logger")


# Create an instance of the ChatLogger class
chat_logger = ChatLogger()

# Create buttons for starting a new chat and loading a previous chat
new_chat_button = tk.Button(root, text="New Chat", command=chat_logger.start_new_chat)
new_chat_button.pack()

load_chat_button = tk.Button(root, text="Load Chat", command=chat_logger.load_previous_chat)
load_chat_button.pack()

# Create a button for selecting the chat participant and adding an entry
select_participant_button = tk.Button(root, text="Add Chat Entry", command=chat_logger.select_participant)
select_participant_button.pack()

# Create a text box for displaying the chat log
chat_display = tk.Text(root, height=20, width=50, state=tk.DISABLED)
chat_display.pack()

# Run the main event loop
root.mainloop()
