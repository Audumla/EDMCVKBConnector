import tkinter as tk

class ScrolledText(tk.Frame):
    """A simple scrolled text widget (drop-in for tkinter.scrolledtext.ScrolledText)."""
    def __init__(self, master=None, **kwargs):
        super().__init__(master)
        self.text = tk.Text(self, **kwargs)
        self.vsb = tk.Scrollbar(self, orient="vertical", command=self.text.yview)
        self.text.configure(yscrollcommand=self.vsb.set)
        self.vsb.pack(side="right", fill="y")
        self.text.pack(side="left", fill="both", expand=True)

    def __getattr__(self, name):
        # Delegate attribute access to the underlying Text widget
        return getattr(self.text, name)

    def pack(self, *args, **kwargs):
        super().pack(*args, **kwargs)

    def grid(self, *args, **kwargs):
        super().grid(*args, **kwargs)

    def place(self, *args, **kwargs):
        super().place(*args, **kwargs)