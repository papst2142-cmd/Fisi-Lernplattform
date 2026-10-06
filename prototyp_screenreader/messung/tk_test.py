import tkinter as tk, customtkinter as ctk, sys
root = ctk.CTk(); root.title("FISI Tk-Test")
ctk.CTkLabel(root, text="Updates").pack()
ctk.CTkButton(root, text="Nach Updates suchen").pack()
ctk.CTkSwitch(root, text="Beim Start automatisch nach Updates suchen").pack()
ctk.CTkEntry(root, placeholder_text="Name").pack()
tk.Button(root, text="Tk-Knopf nativ").pack()
root.after(int(sys.argv[1]) if len(sys.argv)>1 else 8000, root.destroy)
root.mainloop()
