import tkinter as tk
from tkinter import ttk, messagebox
import sqlite3
import shutil
import os
from datetime import datetime

# --- КОНФИГУРАЦИЯ СТИЛЯ (Приложение 2) ---
COLOR_MAIN_BG = "#FFFFFF"
COLOR_SECONDARY_BG = "#F4E8D3"
COLOR_ACCENT = "#67BA80"
FONT_MAIN = ("Segoe UI", 10)
FONT_HEADER = ("Segoe UI", 11, "bold")
DB_NAME = "repair_management.db"

class RepairApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("УК 'Комфорт' - Система управления")
        self.geometry("1100x700")
        self.configure(bg=COLOR_MAIN_BG)
        
        # Иконка приложения
        if os.path.exists("icon.ico"):
            try: self.iconbitmap("icon.ico")
            except: pass
        
        self.conn = sqlite3.connect(DB_NAME)
        self.conn.execute("PRAGMA foreign_keys = ON")
        
        self.setupStyles()
        self.buildUI()
        self.loadRequests()

    def setupStyles(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Treeview", background=COLOR_MAIN_BG, font=FONT_MAIN, rowheight=25)
        style.configure("Treeview.Heading", background=COLOR_SECONDARY_BG, font=FONT_HEADER)
        style.configure("Accent.TButton", background=COLOR_ACCENT, foreground="white", font=("Segoe UI", 9, "bold"))
        style.map("Accent.TButton", background=[('active', '#56a36f')])

    def buildUI(self):
        # --- Компактная Шапка ---
        headerFrame = tk.Frame(self, bg=COLOR_SECONDARY_BG)
        headerFrame.pack(fill=tk.X)
        
        # Маленький логотип
        if os.path.exists("logo.png"):
            try:
                self.logo_raw = tk.PhotoImage(file="logo.png")
                self.logo_small = self.logo_raw.subsample(20, 20) # Еще чуть меньше
                lblLogo = tk.Label(headerFrame, image=self.logo_small, bg=COLOR_SECONDARY_BG)
            except:
                lblLogo = tk.Label(headerFrame, text="🏠", bg=COLOR_SECONDARY_BG, font=FONT_HEADER)
        else:
            lblLogo = tk.Label(headerFrame, text="🏠", bg=COLOR_SECONDARY_BG, font=FONT_HEADER)
        
        lblLogo.pack(side=tk.LEFT, padx=10, pady=5)
        tk.Label(headerFrame, text="УК КОМФОРТ", bg=COLOR_SECONDARY_BG, font=FONT_HEADER).pack(side=tk.LEFT)

        # --- Кнопки навигации (как вы просили) ---
        navFrame = tk.Frame(headerFrame, bg=COLOR_SECONDARY_BG)
        navFrame.pack(side=tk.RIGHT, padx=10)

        ttk.Button(navFrame, text="Жилой фонд", command=lambda: self.openDataView("housing_stock")).pack(side=tk.LEFT, padx=3)
        ttk.Button(navFrame, text="Сотрудники", command=lambda: self.openDataView("users")).pack(side=tk.LEFT, padx=3)
        ttk.Button(navFrame, text="Задолженности", command=lambda: self.openDataView("debts")).pack(side=tk.LEFT, padx=3)
        ttk.Button(navFrame, text="Оплаты", command=lambda: self.openDataView("payments")).pack(side=tk.LEFT, padx=3)

        # --- Основная область: Таблица заявок ---
        mainFrame = tk.Frame(self, bg=COLOR_MAIN_BG)
        mainFrame.pack(fill=tk.BOTH, expand=True, padx=15, pady=5)

        topBar = tk.Frame(mainFrame, bg=COLOR_MAIN_BG)
        topBar.pack(fill=tk.X, pady=5)
        
        tk.Label(topBar, text="Журнал заявок на ремонт", font=FONT_HEADER, bg=COLOR_MAIN_BG).pack(side=tk.LEFT)
        
        self.entrySearch = tk.Entry(topBar, width=35)
        self.entrySearch.pack(side=tk.RIGHT, padx=5)
        self.entrySearch.insert(0, "Поиск по адресу или жильцу...")
        self.entrySearch.bind('<KeyRelease>', lambda e: self.loadRequests(self.entrySearch.get()))
        self.entrySearch.bind('<FocusIn>', lambda e: self.entrySearch.delete(0, tk.END))

        # Таблица (основной функционал)
        cols = ("ID", "Date", "Address", "Client", "Problem", "Status", "Master")
        self.tree = ttk.Treeview(mainFrame, columns=cols, show="headings")
        
        headings = ["№", "Дата", "Адрес", "Жилец", "Описание проблемы", "Статус", "Ответственный"]
        widths = [40, 100, 200, 150, 300, 120, 150]
        
        for col, head, w in zip(cols, headings, widths):
            self.tree.heading(col, text=head)
            self.tree.column(col, width=w)
        
        self.tree.pack(fill=tk.BOTH, expand=True)

        # Панель кнопок (CRUD)
        btnFrame = tk.Frame(mainFrame, bg=COLOR_MAIN_BG, pady=10)
        btnFrame.pack(fill=tk.X)

        ttk.Button(btnFrame, text="➕ Новая заявка", style="Accent.TButton", command=self.openAddForm).pack(side=tk.LEFT, padx=5)
        ttk.Button(btnFrame, text="📝 Редактировать", command=self.openEditForm).pack(side=tk.LEFT, padx=5)
        ttk.Button(btnFrame, text="❌ Удалить", command=self.deleteRequest).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(btnFrame, text="💾 Бэкап БД", command=self.createBackup).pack(side=tk.RIGHT, padx=5)
        ttk.Button(btnFrame, text="📊 История работ", command=self.openHistory).pack(side=tk.RIGHT, padx=5)

    def loadRequests(self, query=""):
        if query == "Поиск по адресу или жильцу...": query = ""
        for i in self.tree.get_children(): self.tree.delete(i)
        cursor = self.conn.cursor()
        sql = '''
            SELECT r.id, r.start_date, r.address, r.client_name, 
                   r.problem_description, s.name, u.fio
            FROM requests r
            LEFT JOIN statuses s ON r.status_id = s.id
            LEFT JOIN users u ON r.employee_id = u.id
            WHERE r.address LIKE ? OR r.client_name LIKE ?
            ORDER BY r.id DESC
        '''
        cursor.execute(sql, (f'%{query}%', f'%{query}%'))
        for row in cursor.fetchall():
            self.tree.insert("", tk.END, values=row)

    def openAddForm(self): EditWindow(self, self.conn, "add")
    def openEditForm(self):
        sel = self.tree.selection()
        if not sel: return
        reqId = self.tree.item(sel[0])['values'][0]
        EditWindow(self, self.conn, "edit", reqId)

    def deleteRequest(self):
        sel = self.tree.selection()
        if not sel: return
        if messagebox.askyesno("Удаление", "Вы уверены?"):
            self.conn.execute("DELETE FROM requests WHERE id=?", (self.tree.item(sel[0])['values'][0],))
            self.conn.commit()
            self.loadRequests()

    def openDataView(self, tableType): DataWindow(self, self.conn, tableType)
    def openHistory(self): HistoryWindow(self, self.conn)
    def createBackup(self):
        try:
            name = f"backup_{datetime.now().strftime('%d%m_%H%M')}.bak"
            shutil.copy2(DB_NAME, name)
            messagebox.showinfo("Успех", f"Копия создана: {name}")
        except: messagebox.showerror("Ошибка", "Не удалось создать бэкап")

# --- ОКНО РЕДАКТИРОВАНИЯ ---
class EditWindow(tk.Toplevel):
    def __init__(self, parent, conn, mode="add", reqId=None):
        super().__init__(parent)
        self.parent, self.conn, self.mode, self.reqId = parent, conn, mode, reqId
        self.title("Заявка")
        self.geometry("400x500")
        self.configure(bg=COLOR_MAIN_BG)
        self.buildForm()
        if mode == "edit": self.loadData()

    def buildForm(self):
        p = {'padx': 20, 'pady': 5}
        tk.Label(self, text="Адрес:", bg=COLOR_MAIN_BG).pack(anchor="w", **p)
        self.cbAddr = ttk.Combobox(self)
        self.cbAddr.pack(fill=tk.X, **p)
        cursor = self.conn.cursor()
        cursor.execute("SELECT address FROM housing_stock")
        self.cbAddr['values'] = [r[0] for r in cursor.fetchall()]

        tk.Label(self, text="Жилец:", bg=COLOR_MAIN_BG).pack(anchor="w", **p)
        self.entName = tk.Entry(self); self.entName.pack(fill=tk.X, **p)

        tk.Label(self, text="Суть проблемы:", bg=COLOR_MAIN_BG).pack(anchor="w", **p)
        self.txt = tk.Text(self, height=4); self.txt.pack(fill=tk.X, **p)

        tk.Label(self, text="Мастер:", bg=COLOR_MAIN_BG).pack(anchor="w", **p)
        self.cbEmp = ttk.Combobox(self, state="readonly")
        self.cbEmp.pack(fill=tk.X, **p)
        cursor.execute("SELECT id, fio FROM users")
        self.emps = {r[1]: r[0] for r in cursor.fetchall()}
        self.cbEmp['values'] = list(self.emps.keys())

        tk.Label(self, text="Статус:", bg=COLOR_MAIN_BG).pack(anchor="w", **p)
        self.cbSt = ttk.Combobox(self, state="readonly")
        self.cbSt.pack(fill=tk.X, **p)
        cursor.execute("SELECT id, name FROM statuses")
        self.stats = {r[1]: r[0] for r in cursor.fetchall()}
        self.cbSt['values'] = list(self.stats.keys())

        ttk.Button(self, text="СОХРАНИТЬ", style="Accent.TButton", command=self.save).pack(pady=20)

    def loadData(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT address, client_name, problem_description, status_id, employee_id FROM requests WHERE id=?", (self.reqId,))
        r = cursor.fetchone()
        if r:
            self.cbAddr.set(r[0]); self.entName.insert(0, r[1]); self.txt.insert("1.0", r[2])
            for k,v in self.stats.items(): 
                if v == r[3]: self.cbSt.set(k)
            for k,v in self.emps.items(): 
                if v == r[4]: self.cbEmp.set(k)

    def save(self):
        d = (self.cbAddr.get(), self.entName.get(), self.txt.get("1.0", tk.END).strip(), 
             self.stats.get(self.cbSt.get()), self.emps.get(self.cbEmp.get()))
        if self.mode == "add":
            self.conn.execute("INSERT INTO requests (address, client_name, problem_description, status_id, employee_id) VALUES (?,?,?,?,?)", d)
        else:
            self.conn.execute("UPDATE requests SET address=?, client_name=?, problem_description=?, status_id=?, employee_id=? WHERE id=?", d + (self.reqId,))
        self.conn.commit()
        self.parent.loadRequests()
        self.destroy()

# --- ВСПОМОГАТЕЛЬНЫЕ ОКНА ---



class DataWindow(tk.Toplevel):
    def __init__(self, parent, conn, tType):
        super().__init__(parent)
        self.title(f"Справочник: {tType}")
        self.geometry("800x400")
        tree = ttk.Treeview(self, show="headings")
        tree.pack(fill=tk.BOTH, expand=True)
        cursor = conn.cursor()

        if tType == "housing_stock":
            cols = ("Адрес", "Этажей", "Квартир", "Год")
            tree["columns"] = cols
            for c in cols: tree.heading(c, text=c)
            cursor.execute("SELECT address, floors, apartments_count, build_year FROM housing_stock")
        elif tType == "users":
            cols = ("ФИО", "Роль", "Телефон")
            tree["columns"] = cols
            for c in cols: tree.heading(c, text=c)
            cursor.execute("SELECT fio, role, phone FROM users")
        elif tType == "debts":
            cols = ("Адрес", "Кв.", "Владелец", "Долг Вода", "Долг Свет")
            tree["columns"] = cols
            for c in cols: tree.heading(c, text=c)
            cursor.execute("SELECT address, flat_number, owner_name, water_debt, electricity_debt FROM debts")
        elif tType == "payments":
            cols = ("Собственник", "Период", "Начислено", "Оплачено")
            tree["columns"] = cols
            for c in cols: tree.heading(c, text=c)
            cursor.execute("SELECT owner_name, period, amount_charged, amount_paid FROM payments")
            
        for r in cursor.fetchall(): tree.insert("", tk.END, values=r)

class HistoryWindow(tk.Toplevel):
    def __init__(self, parent, conn):
        super().__init__(parent)
        self.title("История выполнения")
        self.geometry("700x500")
        self.configure(bg=COLOR_MAIN_BG)

        # --- Блок статистики ---
        stats_frame = tk.Frame(self, bg=COLOR_MAIN_BG)
        stats_frame.pack(side=tk.TOP, fill=tk.X, pady=10)

        # Метка для отображения статистики зеленым цветом
        self.lbl_stats = tk.Label(
            stats_frame, 
            text="Подсчет...", 
            font=("Segoe UI", 12, "bold"), 
            fg="#2E8B57",  # Зеленый цвет
            bg=COLOR_MAIN_BG
        )
        self.lbl_stats.pack()

        # --- Таблица ---
        tree = ttk.Treeview(self, columns=("D", "A", "M", "S"), show="headings")
        
        headers = ("Дата", "Адрес", "Мастер", "Статус")
        cols = ("D", "A", "M", "S")
        
        for c, h in zip(cols, headers):
            tree.heading(c, text=h)
            tree.column(c, anchor="center")
            
        tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

        # --- Получение данных и подсчет ---
        cursor = conn.cursor()
        cursor.execute('''
            SELECT r.start_date, r.address, u.fio, s.name 
            FROM requests r 
            JOIN users u ON r.employee_id = u.id 
            JOIN statuses s ON r.status_id = s.id
            ORDER BY r.start_date DESC
        ''')
        
        rows = cursor.fetchall()
        
        completed_count = 0
        pending_count = 0

        for r in rows:
            status_name = r[3] # Название статуса из БД
            
            # Приводим к нижнему регистру для надежности проверки
            s_lower = status_name.lower()

            # Условие: если статус содержит "выполнено" ИЛИ "заявка закрыта"
            if "выполнено" in s_lower or "заявка закрыта" in s_lower:
                completed_count += 1
            else:
                pending_count += 1
            
            tree.insert("", tk.END, values=r)

        # Обновляем текст статистики
        self.lbl_stats.config(
            text=f"✅ Выполнено (закрыто): {completed_count}   |   ⏳ В работе: {pending_count}"
        )

if __name__ == "__main__":
    app = RepairApp()
    app.mainloop()