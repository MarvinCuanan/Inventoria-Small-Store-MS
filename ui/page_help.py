import tkinter as tk
from tkinter import ttk

from ui import theme
from ui.theme import Page

COMMON = [
    ("Getting started", [
        "Use the dark menu on the left to move between screens. The highlighted item is where you are.",
        "Your name and role are shown at the top right. Click 'Change password' there to set your own password.",
        "Anything that goes wrong shows a message in plain words. Nothing is saved until you press Save / Submit.",
    ]),
    ("Record stock coming IN (deliveries, restocking)", [
        "1. Click Stock in the menu (or 'Add Stock' on the Dashboard).",
        "2. Make sure the 'Add Stock' tab is blue. Type part of the product name in the search box and pick it from the list.",
        "3. Type the quantity received, add a remark if you like (e.g. supplier name), then press Submit.",
    ]),
    ("Record stock going OUT (sales, damaged, used)", [
        "1. Click Stock, then the 'Remove Stock' tab.",
        "2. Pick the product, type the quantity, press Submit.",
        "3. If you try to remove more than is available, the system refuses and tells you how many are left.",
    ]),
    ("Check what needs restocking", [
        "The Dashboard lists every product at or below its alert level in red, with its current stock.",
        "The 'Low Stock' card counts them. The page refreshes by itself every 30 seconds.",
    ]),
    ("Find a product", [
        "Open Products and type any part of a name, SKU or category. The list filters as you type.",
        "Click a column title to sort by it.",
    ]),
]

STAFF = [
    ("What you can do as Staff", [
        "View and search products, record Stock In and Stock Out, and see your own transactions.",
        "Adding or changing products, reports and user accounts are done by an Admin. Ask your Admin if you need one.",
    ]),
    ("See what you recorded", [
        "Open Transactions. Use the filters (type, product, dates) and press Search. Green = stock in, red = stock out.",
    ]),
]

ADMIN = [
    ("Add a product", [
        "1. Products > + Add Product. Enter the name, choose a category, the price and the alert level.",
        "2. 'Opening stock' is the quantity on the shelf today. Leave the SKU blank and the system makes one.",
        "3. Need a new category? Products > Categories, type a name and click Add new.",
    ]),
    ("Edit or delete a product", [
        "Select the row, then Edit (or double-click). To change the quantity use Stock instead, so the history stays correct.",
        "Delete hides the product but keeps its history. Tick 'Show deleted products' and press Restore to bring it back.",
    ]),
    ("Reports", [
        "Reports > choose From and To dates (YYYY-MM-DD) > Generate. Export CSV opens in Excel.",
        "'Total Stock' is the quantity now; 'Stock In' and 'Total Sold' count movements inside the dates you chose.",
    ]),
    ("Manage people (Users)", [
        "People can create their own account on the login screen; they start as Staff. Promote them with Change role.",
        "+ Add User creates an account for someone directly. Deactivate stops a person logging in without deleting history.",
        "Reset password sets a new one if someone forgets theirs. Role permissions lets you decide what each role may do.",
        "Safety rules: you cannot change or deactivate your own account, and the last Admin is always protected.",
    ]),
    ("Audit Log", [
        "Every login, add, change and delete is recorded. Double-click a row to see the before and after values.",
    ]),
]

TIPS = [("Good habits", [
    "Change the default admin password on day one.",
    "Record stock movements as they happen, so the numbers on the Dashboard are always trustworthy.",
    "If MySQL is not running you will see 'Cannot reach MySQL' - start it in the XAMPP Control Panel.",
])]


class HelpPage(Page):
    title = "Help & Guide"

    def get_subtitle(self):
        role = self.app.session.current_user["role"]
        return f"Step-by-step instructions for your role ({role}). Scroll down for more."

    def build(self):
        sections = COMMON + (ADMIN if self.app.session.is_admin() else STAFF) + TIPS
        box = tk.Frame(self.body, bg="white", highlightthickness=1, highlightbackground=theme.BORDER)
        box.pack(fill="both", expand=True)
        text = tk.Text(box, wrap="word", relief="flat", bg="white", fg=theme.TEXT, padx=18, pady=12,
                       font=theme.font(11), spacing1=2, spacing3=2, cursor="arrow")
        bar = ttk.Scrollbar(box, command=text.yview)
        text.configure(yscrollcommand=bar.set)
        bar.pack(side="right", fill="y")
        text.pack(side="left", fill="both", expand=True)
        text.tag_configure("h", font=theme.font(13, "bold"), foreground=theme.BLUE, spacing1=14, spacing3=4)
        text.tag_configure("p", lmargin1=8, lmargin2=22)
        for heading, lines in sections:
            text.insert("end", heading + "\n", "h")
            for line in lines:
                text.insert("end", line + "\n", "p")
        text.config(state="disabled")
