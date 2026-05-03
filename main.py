import sys


def main():
    try:
        from tkinterdnd2 import TkinterDnD
        import customtkinter as ctk
        ctk.CTk.__bases__ = (TkinterDnD.Tk,)
    except ImportError:
        pass

    from ui.app import App
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
