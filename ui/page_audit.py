import json
import tkinter as tk

from controllers import AuditLogController
from core.formatting import short_dt
from ui import theme
from ui.theme import Btn, ComboField, DataTable, Dialog, Field, Page


class DetailDialog(Dialog):
    def __init__(self, parent, row):
        self.row = row
        super().__init__(parent, f"Log #{row['log_id']}", 560, save_text=None)

    @staticmethod
    def _pretty(raw):
        if not raw:
            return "-"
        try:
            return json.dumps(json.loads(raw), indent=2, ensure_ascii=False)
        except (TypeError, ValueError):
            return str(raw)

    def build(self, body):
        r = self.row
        head = (f"{short_dt(r['created_at'])}   ·   {r['username']}   ·   {r['action']} {r['table_affected'] or ''}"
                f" #{r['record_id'] or '-'}   ·   {r['ip_address'] or ''}")
        tk.Label(body, text=head, bg="white", fg=theme.TEXT, font=theme.font(11, "bold"), wraplength=500,
                 justify="left").pack(anchor="w", pady=(0, 10))
        for title, raw in (("Before", r["old_values"]), ("After", r["new_values"])):
            tk.Label(body, text=title, bg="white", fg=theme.MUTED, font=theme.font(10, "bold")).pack(anchor="w")
            box = tk.Text(body, height=6, width=64, font=("Consolas", 10), bg=theme.SOFT, relief="flat")
            box.insert("1.0", self._pretty(raw))
            box.config(state="disabled")
            box.pack(fill="x", pady=(2, 10))


class AuditPage(Page):
    title = "Audit Log"
    subtitle = "A permanent record of who did what and when. Use the filters to narrow it down."

    def build(self):
        self.ctrl = AuditLogController()
        bar = tk.Frame(self.body, bg="white")
        bar.pack(fill="x")
        self.user = ComboField(bar, "User", [("All users", None)] + [(u["username"], u["user_id"]) for u in self.ctrl.list_users()], width=14)
        self.user.pack(side="left", padx=(0, 8))
        self.user.select_first()
        self.action = ComboField(bar, "Action", [("All", None)] + [(a, a) for a in ("LOGIN", "LOGOUT", "INSERT", "UPDATE", "DELETE")], width=10)
        self.action.pack(side="left", padx=(0, 8))
        self.action.select_first()
        self.d_from = Field(bar, "From (YYYY-MM-DD)", width=13)
        self.d_from.pack(side="left", padx=(0, 8))
        self.d_to = Field(bar, "To (YYYY-MM-DD)", width=13)
        self.d_to.pack(side="left", padx=(0, 8))
        Btn(bar, "Filter", self.refresh).pack(side="left", anchor="s")
        tk.Label(self.body, text="Double-click a row to see what changed (before / after).", bg="white",
                 fg=theme.MUTED).pack(anchor="w", pady=(8, 4))
        self.table = DataTable(self.body, [("d", "Date / time", 130, "w"), ("u", "User", 100, "w"),
                                           ("a", "Action", 70, "center"), ("t", "Table", 100, "w"),
                                           ("r", "Record", 60, "center"), ("x", "Details", 320, "w")], height=14)
        self.table.pack(fill="both", expand=True)
        self.table.on_double_click(self.show_detail)

    def refresh(self):
        self.rows = {str(r["log_id"]): r for r in
                     self.ctrl.list_logs(self.user.value(), self.action.value(), self.d_from.get(), self.d_to.get())}
        self.table.load([(lid, (short_dt(r["created_at"]), r["username"], r["action"], r["table_affected"] or "",
                                r["record_id"] or "", (r["new_values"] or r["old_values"] or "")[:90]), None)
                         for lid, r in self.rows.items()])

    def show_detail(self):
        row = self.rows.get(self.table.selected())
        if row:
            DetailDialog(self, row)
