import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import customtkinter as ctk
import numpy as np
import os
import csv
import json

# === SOLUCIÓN DE BACKEND PARA EVITAR CONGELAMIENTOS ===
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.patches as patches

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

CSV_FILENAME = "materiales.csv"

def aplicar_tema_treeview():
    """Aplica tema oscuro consistente a todos los widgets ttk.Treeview."""
    style = ttk.Style()
    style.theme_use("clam")
    style.configure("Treeview",
        background="#1E1E1E", foreground="#E0E0E0",
        fieldbackground="#1E1E1E", bordercolor="#2A2A2A",
        rowheight=26, font=("Segoe UI", 10))
    style.configure("Treeview.Heading",
        background="#1F3A5F", foreground="white",
        font=("Segoe UI", 10, "bold"), relief="flat", padding=4)
    style.map("Treeview",
        background=[("selected", "#1F6AA5")],
        foreground=[("selected", "white")])

class AcousticApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        aplicar_tema_treeview()

        self.title("Suite de Diagnóstico Acústico — CBFK Tools")
        self.geometry("1540x960")
        self.minsize(1280, 840)

        # Variables de estado y persistencia en memoria
        self.tipo_grafico_bonello = "Barras"
        self.modo_seleccionado = None
        self.lista_modos = []
        self._colorbar_planta = None  # Referencia al colorbar activo del mapa de presión

        # Posiciones arrastrables: se inicializan en ejecutar_diagnostico()
        self.pos_monitor_l = None   # (x, y) Monitor izquierdo
        self.pos_monitor_r = None   # (x, y) Monitor derecho
        self.pos_sweet_spot = None  # (x, y) Posición de escucha
        self._drag_target = None    # Qué punto está siendo arrastrado ('L', 'R', 'SS')
        self.bandas_octava = ["125Hz", "250Hz", "500Hz", "1kHz", "2kHz", "4kHz"]
        self.materiales_aplicados = []
        self.diccionario_stock_materiales = {}

        # Asegurar inventario de stock real ajustado
        self.asegurar_csv_materiales()
        self.cargar_dict_materiales_desde_csv()

        # --- GRID PRINCIPAL ---
        self.grid_columnconfigure(0, weight=0, minsize=310) 
        self.grid_columnconfigure(1, weight=1)              
        self.grid_rowconfigure(0, weight=1)

        # --- PANEL DE CONTROL (IZQUIERDA) ---
        self.sidebar = ctk.CTkScrollableFrame(self, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        
        self.title_label = ctk.CTkLabel(
            self.sidebar,
            text="⚙  Configuración de Sala",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color="#38BDF8"
        )
        self.title_label.pack(padx=10, pady=(12, 4))

        ctk.CTkLabel(self.sidebar, text="Dimensiones de la Sala",
            font=ctk.CTkFont(size=12, weight="bold"), text_color="#94A3B8"
        ).pack(fill="x", padx=10, pady=(8, 2))

        self.entry_largo = self.crear_input("Largo (m) [Eje X]:", "4.50")
        self.entry_ancho = self.crear_input("Ancho (m) [Eje Y]:", "3.50")
        self.entry_alto = self.crear_input("Alto (m) [Eje Z]:", "2.60")

        ctk.CTkLabel(self.sidebar, text="Materiales Base de Estructura:", font=ctk.CTkFont(weight="bold", size=13), text_color="#1F6AA5").pack(fill="x", padx=10, pady=(10, 5))
        
        lista_nombres_stock = list(self.diccionario_stock_materiales.keys())
        
        self.combo_frontal = self.crear_selector_cara("Pared Frontal (Muro X=0):", lista_nombres_stock, "Ladrillo o Bloque denso")
        self.combo_trasera = self.crear_selector_cara("Pared Trasera (Muro X=L):", lista_nombres_stock, "Ladrillo o Bloque denso")
        self.combo_izquierda = self.crear_selector_cara("Pared Izquierda (Muro Y=0):", lista_nombres_stock, "Placa de Yeso (Drywall)")
        self.combo_derecha = self.crear_selector_cara("Pared Derecha (Muro Y=W):", lista_nombres_stock, "Placa de Yeso (Drywall)")
        self.combo_techo = self.crear_selector_cara("Techo (Z=H):", lista_nombres_stock, "Placa de Yeso (Drywall)")
        self.combo_piso = self.crear_selector_cara("Piso (Z=0):", lista_nombres_stock, "Hormigón o Concreto Rígido")

        self.btn_calcular = ctk.CTkButton(
            self.sidebar,
            text="▶  Calcular Diagnóstico",
            font=ctk.CTkFont(weight="bold", size=13),
            height=38,
            fg_color="#1F6AA5",
            hover_color="#155A8A",
            command=self.ejecutar_diagnostico
        )
        self.btn_calcular.pack(fill="x", padx=10, pady=15)

        self.session_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        self.session_frame.pack(fill="x", padx=10, pady=5)
        
        self.btn_guardar_json = ctk.CTkButton(self.session_frame, text="Guardar Config.", width=130, height=30, fg_color="#1F6AA5", command=self.guardar_configuracion_json)
        self.btn_guardar_json.pack(side="left", expand=True, padx=(0,2))
        
        self.btn_cargar_json = ctk.CTkButton(self.session_frame, text="Cargar Config.", width=130, height=30, fg_color="#1F6AA5", command=self.cargar_configuracion_json)
        self.btn_cargar_json.pack(side="right", expand=True, padx=(2,0))

        self.info_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        self.info_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        self.lbl_volumen = ctk.CTkLabel(self.info_frame, text="📐  Volumen: -- m³", anchor="w", font=ctk.CTkFont(size=11))
        self.lbl_volumen.pack(fill="x", pady=2)
        self.lbl_superficie = ctk.CTkLabel(self.info_frame, text="📏  Superficie Total: -- m²", anchor="w", font=ctk.CTkFont(size=11))
        self.lbl_superficie.pack(fill="x", pady=2)
        self.lbl_modos_count = ctk.CTkLabel(self.info_frame, text="🎵  Modos (<200Hz): --", anchor="w", font=ctk.CTkFont(size=11))
        self.lbl_modos_count.pack(fill="x", pady=2)
        self.lbl_bonello_status = ctk.CTkLabel(self.info_frame, text="Bonello: --", anchor="w", font=ctk.CTkFont(weight="bold", size=12))
        self.lbl_bonello_status.pack(fill="x", pady=(6, 2))

        # --- PESTAÑAS (DERECHA) ---
        self.tabview = ctk.CTkTabview(self)
        self.tabview.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
        
        self.tab_geometria = self.tabview.add("Geometría y Sweet Spot")
        self.tab_criterios = self.tabview.add("Criterios de Calidad (Bolt/Bonello)")
        self.tab_materiales = self.tabview.add("Absorción Sabine y Paneles")

        self.configurar_tab_geometria()
        self.configurar_tab_criterios()
        self.configurar_tab_materiales()

        self.ejecutar_diagnostico()

    def crear_input(self, texto, valor_defecto):
        lbl = ctk.CTkLabel(self.sidebar, text=texto, anchor="w")
        lbl.pack(fill="x", padx=10, pady=(2, 0))
        entry = ctk.CTkEntry(self.sidebar)
        entry.insert(0, valor_defecto)
        entry.pack(fill="x", padx=10, pady=(0, 3))
        return entry

    def crear_selector_cara(self, texto, opciones, por_defecto):
        lbl = ctk.CTkLabel(self.sidebar, text=texto, anchor="w", font=ctk.CTkFont(size=11))
        lbl.pack(fill="x", padx=10, pady=(3, 0))
        combo = ctk.CTkComboBox(self.sidebar, values=opciones, height=26, font=ctk.CTkFont(size=11))
        if por_defecto in opciones: combo.set(por_defecto)
        elif opciones: combo.set(opciones[0])
        combo.pack(fill="x", padx=10, pady=(0, 3))
        return combo

    def asegurar_csv_materiales(self):
        if not os.path.exists(CSV_FILENAME):
            datos_defecto = [
                ["Nombre", "125Hz", "250Hz", "500Hz", "1kHz", "2kHz", "4kHz"],
                ["Hormigón o Concreto Rígido", "0.02", "0.02", "0.02", "0.03", "0.04", "0.05"],
                ["Ladrillo o Bloque denso", "0.04", "0.04", "0.03", "0.04", "0.05", "0.06"],
                ["Placa de Yeso (Drywall)", "0.10", "0.08", "0.05", "0.04", "0.06", "0.07"],
                ["Vidrio de Ventana", "0.18", "0.12", "0.10", "0.08", "0.06", "0.04"],
                ["Madera delgada o Tarima", "0.15", "0.11", "0.10", "0.09", "0.09", "0.10"],
                ["Fibra de Vidrio (75mm - Alta Densidad)", "0.50", "0.80", "0.99", "0.99", "0.99", "0.99"],
                ["Espuma Acústica Estándar (50mm)", "0.15", "0.25", "0.55", "0.80", "0.90", "0.95"]
            ]
            with open(CSV_FILENAME, mode='w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerows(datos_defecto)

    def cargar_dict_materiales_desde_csv(self):
        self.diccionario_stock_materiales = {}
        if os.path.exists(CSV_FILENAME):
            with open(CSV_FILENAME, mode='r', encoding='utf-8') as f:
                reader = csv.reader(f)
                next(reader) 
                for row in reader:
                    if row:
                        nombre = row[0]
                        alfas = [float(v) for v in row[1:]]
                        self.diccionario_stock_materiales[nombre] = alfas

    def configurar_tab_geometria(self):
        self.tab_geometria.grid_rowconfigure(0, weight=5)
        self.tab_geometria.grid_rowconfigure(1, weight=4)
        self.tab_geometria.grid_columnconfigure(0, weight=1)

        self.plot_frame = ctk.CTkFrame(self.tab_geometria)
        self.plot_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=(0, 10))
        
        self.fig_planta = plt.Figure(figsize=(6, 4), facecolor='#2B2B2B')
        self.ax_planta = self.fig_planta.add_subplot(111)
        self.canvas_planta = FigureCanvasTkAgg(self.fig_planta, master=self.plot_frame)
        self.canvas_planta.get_tk_widget().pack(fill="both", expand=True, padx=10, pady=10)

        # Conectar eventos de drag-and-drop para monitores y sweet spot
        self.canvas_planta.mpl_connect('button_press_event',   self._on_planta_press)
        self.canvas_planta.mpl_connect('motion_notify_event',  self._on_planta_motion)
        self.canvas_planta.mpl_connect('button_release_event', self._on_planta_release)

        self.table_frame = ctk.CTkFrame(self.tab_geometria)
        self.table_frame.grid(row=1, column=0, sticky="nsew", padx=5, pady=0)
        
        self.tree_scroll = ctk.CTkScrollbar(self.table_frame)
        self.tree_scroll.pack(side="right", fill="y")

        self.tree = ttk.Treeview(self.table_frame, columns=("frec", "tipo", "indices"), show="headings", height=5)
        self.tree.heading("frec", text="Frecuencia (Hz)")
        self.tree.heading("tipo", text="Tipo de Modo")
        self.tree.heading("indices", text="Índices (p, q, r)")
        self.tree.column("frec", anchor="center", width=150)
        self.tree.column("tipo", anchor="center", width=200)
        self.tree.column("indices", anchor="center", width=150)
        self.tree.pack(fill="both", expand=True, padx=15, pady=(5, 15))
        self.tree_scroll.configure(command=self.tree.yview)
        self.tree.bind("<<TreeviewSelect>>", self.on_modo_seleccionado)

    def configurar_tab_criterios(self):
        self.tab_criterios.grid_rowconfigure(0, weight=0)
        self.tab_criterios.grid_rowconfigure(1, weight=1)
        self.tab_criterios.grid_columnconfigure(0, weight=1)
        self.tab_criterios.grid_columnconfigure(1, weight=1)

        self.toolbar_bonello = ctk.CTkFrame(self.tab_criterios, fg_color="transparent")
        self.toolbar_bonello.grid(row=0, column=1, sticky="ne", padx=15, pady=5)
        
        self.seg_btn_bonello = ctk.CTkSegmentedButton(self.toolbar_bonello, values=["Barras", "Puntos"], command=self.cambiar_vista_bonello)
        self.seg_btn_bonello.set("Barras")
        self.seg_btn_bonello.pack(side="left", padx=5)

        self.bolt_frame = ctk.CTkFrame(self.tab_criterios)
        self.bolt_frame.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)
        self.fig_bolt = plt.Figure(figsize=(5, 5), facecolor='#2B2B2B')
        self.ax_bolt = self.fig_bolt.add_subplot(111)
        self.canvas_bolt = FigureCanvasTkAgg(self.fig_bolt, master=self.bolt_frame)
        self.canvas_bolt.get_tk_widget().pack(fill="both", expand=True, padx=10, pady=10)

        self.bonello_frame = ctk.CTkFrame(self.tab_criterios)
        self.bonello_frame.grid(row=1, column=1, sticky="nsew", padx=5, pady=5)
        self.fig_bonello = plt.Figure(figsize=(5, 5), facecolor='#2B2B2B')
        self.ax_bonello = self.fig_bonello.add_subplot(111)
        self.canvas_bonello = FigureCanvasTkAgg(self.fig_bonello, master=self.bonello_frame)
        self.canvas_bonello.get_tk_widget().pack(fill="both", expand=True, padx=10, pady=10)

    def configurar_tab_materiales(self):
        self.tab_materiales.grid_columnconfigure(0, weight=4) 
        self.tab_materiales.grid_columnconfigure(1, weight=3) 
        self.tab_materiales.grid_rowconfigure(0, weight=1)

        self.left_mat_frame = ctk.CTkFrame(self.tab_materiales, fg_color="transparent")
        self.left_mat_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        
        # Grid interno para albergar las secciones cómodamente
        self.left_mat_frame.grid_rowconfigure(0, weight=3) 
        self.left_mat_frame.grid_rowconfigure(1, weight=2) 
        self.left_mat_frame.grid_rowconfigure(2, weight=3) 
        self.left_mat_frame.grid_rowconfigure(3, weight=2) # Nueva Fila para el predictor inverso
        self.left_mat_frame.grid_columnconfigure(0, weight=1)

        # 1. Inventario de Materiales
        self.stock_frame = ctk.CTkFrame(self.left_mat_frame)
        self.stock_frame.grid(row=0, column=0, sticky="nsew", pady=(0,5))
        ctk.CTkLabel(self.stock_frame, text="1. Selecciona un Material de Absorción para tus Paneles:", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=10, pady=2)
        
        self.tree_mat = ttk.Treeview(self.stock_frame, columns=("nombre", "125", "250", "500", "1k", "2k", "4k"), show="headings", height=5)
        self.tree_mat.heading("nombre", text="Material en Inventario")
        for b in self.bandas_octava:
            self.tree_mat.heading(b.replace("Hz",""), text=b)
            self.tree_mat.column(b.replace("Hz",""), anchor="center", width=60)
        self.tree_mat.column("nombre", anchor="w", width=200)
        self.tree_mat.pack(fill="both", expand=True, padx=10, pady=5)

        # 2. Configurar parches/paneles
        self.calc_panel_frame = ctk.CTkFrame(self.left_mat_frame)
        self.calc_panel_frame.grid(row=1, column=0, sticky="nsew", pady=5)
        ctk.CTkLabel(self.calc_panel_frame, text="2. Tipea las Dimensiones de los Paneles Físicos:", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, columnspan=4, sticky="w", padx=10, pady=2)
        
        ctk.CTkLabel(self.calc_panel_frame, text="Cantidad:").grid(row=1, column=0, padx=5, pady=2, sticky="e")
        self.ent_cant = ctk.CTkEntry(self.calc_panel_frame, width=70)
        self.ent_cant.insert(0, "5")
        self.ent_cant.grid(row=1, column=1, padx=5, pady=2, sticky="w")

        ctk.CTkLabel(self.calc_panel_frame, text="Largo (m):").grid(row=1, column=2, padx=5, pady=2, sticky="e")
        self.ent_p_largo = ctk.CTkEntry(self.calc_panel_frame, width=80, placeholder_text="0.82")
        self.ent_p_largo.grid(row=1, column=3, padx=5, pady=2, sticky="w")

        ctk.CTkLabel(self.calc_panel_frame, text="Ancho (m):").grid(row=2, column=0, padx=5, pady=2, sticky="e")
        self.ent_p_ancho = ctk.CTkEntry(self.calc_panel_frame, width=70, placeholder_text="0.44")
        self.ent_p_ancho.grid(row=2, column=1, padx=5, pady=2, sticky="w")

        ctk.CTkLabel(self.calc_panel_frame, text="Cara Destino:").grid(row=2, column=2, padx=5, pady=2, sticky="e")
        self.combo_donde = ctk.CTkComboBox(self.calc_panel_frame, values=["Pared Frontal", "Pared Trasera", "Pared Izquierda", "Pared Derecha", "Techo", "Piso"], width=130)
        self.combo_donde.set("Pared Izquierda")
        self.combo_donde.grid(row=2, column=3, padx=5, pady=2, sticky="w")

        self.btn_aplicar_sala = ctk.CTkButton(self.calc_panel_frame, text="Agregar Paneles y Descontar de esa Cara Específica", font=ctk.CTkFont(weight="bold"), fg_color="#2A8C55", hover_color="#1E633C", command=self.añadir_paneles_a_sala)
        self.btn_aplicar_sala.grid(row=3, column=0, columnspan=4, padx=10, pady=8, sticky="ew")

        # 3. Tratamiento colocado en la sala
        self.sala_actual_frame = ctk.CTkFrame(self.left_mat_frame)
        self.sala_actual_frame.grid(row=2, column=0, sticky="nsew", pady=5)
        
        header_sala = ctk.CTkFrame(self.sala_actual_frame, fg_color="transparent")
        header_sala.pack(fill="x", padx=10, pady=2)
        ctk.CTkLabel(header_sala, text="3. Acondicionamiento Instalado:", font=ctk.CTkFont(weight="bold")).pack(side="left")
        
        self.btn_limpiar_sala = ctk.CTkButton(header_sala, text="Resetear Sala", width=90, height=22, fg_color="#FF5555", hover_color="#992222", command=self.resetear_tratamiento_sala)
        self.btn_limpiar_sala.pack(side="right")

        self.tree_sala = ttk.Treeview(self.sala_actual_frame, columns=("desc", "donde", "area"), show="headings", height=3)
        self.tree_sala.heading("desc", text="Descripción del Panel")
        self.tree_sala.heading("donde", text="Cara Intervenida")
        self.tree_sala.heading("area", text="Área Ocupada (m²)")
        self.tree_sala.column("desc", anchor="w", width=250)
        self.tree_sala.column("donde", anchor="center", width=120)
        self.tree_sala.column("area", anchor="center", width=100)
        self.tree_sala.pack(fill="both", expand=True, padx=10, pady=(0,5))

        # 4. NUEVO PANEL: MOTOR DE PREDICCIÓN INVERSA AUTOMÁTICA
        self.predictor_frame = ctk.CTkFrame(self.left_mat_frame, fg_color="#1E293B", border_width=1, border_color="#334155")
        self.predictor_frame.grid(row=3, column=0, sticky="nsew", pady=(5,0))
        
        ctk.CTkLabel(self.predictor_frame, text="4. Predicción Inversa de Área Requerida:", font=ctk.CTkFont(weight="bold", size=13), text_color="#38BDF8").grid(row=0, column=0, columnspan=4, sticky="w", padx=10, pady=2)
        
        ctk.CTkLabel(self.predictor_frame, text="RT60 Objetivo (s):").grid(row=1, column=0, padx=5, pady=2, sticky="e")
        self.ent_rt_target = ctk.CTkEntry(self.predictor_frame, width=70)
        self.ent_rt_target.insert(0, "0.35")
        self.ent_rt_target.grid(row=1, column=1, padx=5, pady=2, sticky="w")

        ctk.CTkLabel(self.predictor_frame, text="Frec. Pivote:").grid(row=1, column=2, padx=5, pady=2, sticky="e")
        self.combo_frec_pivote = ctk.CTkComboBox(self.predictor_frame, values=["125Hz", "250Hz", "500Hz", "1kHz", "2kHz", "4kHz"], width=90)
        self.combo_frec_pivote.set("500Hz")
        self.combo_frec_pivote.grid(row=1, column=3, padx=5, pady=2, sticky="w")

        self.btn_predecir_area = ctk.CTkButton(self.predictor_frame, text="Calcular m² Absorbente Requeridos", font=ctk.CTkFont(weight="bold"), fg_color="#0284C7", hover_color="#0369A1", command=self.ejecutar_calculo_predictivo_inverso)
        self.btn_predecir_area.grid(row=2, column=0, columnspan=4, padx=10, pady=6, sticky="ew")

        self.lbl_resultado_prediccion = ctk.CTkLabel(self.predictor_frame, text="Resultado: Configura los parámetros y presiona Calcular", font=ctk.CTkFont(size=11, slant="italic"), text_color="#94A3B8")
        self.lbl_resultado_prediccion.grid(row=3, column=0, columnspan=4, padx=10, pady=(0,4), sticky="w")

        # Curva RT60
        self.rt_frame = ctk.CTkFrame(self.tab_materiales)
        self.rt_frame.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)
        
        self.fig_rt = plt.Figure(figsize=(5, 4), facecolor='#2B2B2B')
        self.ax_rt = self.fig_rt.add_subplot(111)
        self.canvas_rt = FigureCanvasTkAgg(self.fig_rt, master=self.rt_frame)
        self.canvas_rt.get_tk_widget().pack(fill="both", expand=True, padx=10, pady=10)

        self.cargar_materiales_desde_csv()

    def guardar_configuracion_json(self):
        filepath = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("Archivos JSON", "*.json")])
        if not filepath: return
        
        config_data = {
            "sala": {
                "largo": self.entry_largo.get(), "ancho": self.entry_ancho.get(), "alto": self.entry_alto.get(),
                "frontal": self.combo_frontal.get(), "trasera": self.combo_trasera.get(),
                "izquierda": self.combo_izquierda.get(), "derecha": self.combo_derecha.get(),
                "techo": self.combo_techo.get(), "piso": self.combo_piso.get()
            },
            "materiales_aplicados": self.materiales_aplicados
        }
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=4, ensure_ascii=False)
            messagebox.showinfo("Sesión Guardada", "Exportado con éxito.")
        except Exception as e:
            messagebox.showerror("Error", f"Fallo: {str(e)}")

    def cargar_configuracion_json(self):
        filepath = filedialog.askopenfilename(filetypes=[("Archivos JSON", "*.json")])
        if not filepath: return
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
            
            self.entry_largo.delete(0, tk.END); self.entry_largo.insert(0, config_data["sala"]["largo"])
            self.entry_ancho.delete(0, tk.END); self.entry_ancho.insert(0, config_data["sala"]["ancho"])
            self.entry_alto.delete(0, tk.END); self.entry_alto.insert(0, config_data["sala"]["alto"])

            self.combo_frontal.set(config_data["sala"]["frontal"])
            self.combo_trasera.set(config_data["sala"]["trasera"])
            self.combo_izquierda.set(config_data["sala"]["izquierda"])
            self.combo_derecha.set(config_data["sala"]["derecha"])
            self.combo_techo.set(config_data["sala"]["techo"])
            self.combo_piso.set(config_data["sala"]["piso"])

            self.materiales_aplicados = config_data["materiales_aplicados"]
            
            for item in self.tree_sala.get_children(): self.tree_sala.delete(item)
            for panel in self.materiales_aplicados:
                self.tree_sala.insert("", "end", values=(panel["desc"], panel["donde"], f"{panel['area_total']:.2f} m²"))
            
            self.ejecutar_diagnostico()
            messagebox.showinfo("Sesión Cargada", "Restaurado con éxito.")
        except Exception as e:
            messagebox.showerror("Error", f"Fallo al restaurar: {str(e)}")

    def cargar_materiales_desde_csv(self):
        for item in self.tree_mat.get_children(): self.tree_mat.delete(item)
        if os.path.exists(CSV_FILENAME):
            with open(CSV_FILENAME, mode='r', encoding='utf-8') as f:
                reader = csv.reader(f)
                next(reader) 
                for row in reader:
                    if row: self.tree_mat.insert("", "end", values=row)

    def añadir_paneles_a_sala(self):
        selected_item = self.tree_mat.selection()
        if not selected_item:
            messagebox.showerror("Error", "Primero debes seleccionar un material del Inventario superior.")
            return

        valores_material = self.tree_mat.item(selected_item[0])['values']
        nombre_mat = valores_material[0]
        alfas = [float(v) for v in valores_material[1:]]

        try:
            cantidad = int(self.ent_cant.get())
            largo_p = float(self.ent_p_largo.get())
            ancho_p = float(self.ent_p_ancho.get())
            if cantidad <= 0 or largo_p <= 0 or ancho_p <= 0: raise ValueError
        except ValueError:
            messagebox.showerror("Error", "Ingresa dimensiones numéricas válidas mayores a cero.")
            return

        area_grupo = cantidad * (largo_p * ancho_p)
        donde_va = self.combo_donde.get()
        descripcion = f"{cantidad} ud. de {largo_p:.2f}m x {ancho_p:.2f}m ({nombre_mat})"

        self.materiales_aplicados.append({
            "nombre": nombre_mat, "alfas": alfas, "area_total": area_grupo, "donde": donde_va, "desc": descripcion
        })

        self.tree_sala.insert("", "end", values=(descripcion, donde_va, f"{area_grupo:.2f} m²"))
        self.calcular_rt60_dinamico()

    def resetear_tratamiento_sala(self):
        self.materiales_aplicados = []
        for item in self.tree_sala.get_children(): self.tree_sala.delete(item)
        self.calcular_rt60_dinamico()

    # ─── DRAG & DROP: Monitores y Sweet Spot ────────────────────────────────────

    def _hit_test_planta(self, xd, yd):
        """Devuelve 'L', 'R' o 'SS' si el click está cerca de algún marcador, None si no."""
        if self.modo_seleccionado is not None: return None
        if None in (self.pos_monitor_l, self.pos_monitor_r, self.pos_sweet_spot): return None
        try:
            L = float(self.entry_largo.get())
            W = float(self.entry_ancho.get())
        except ValueError:
            return None
        # Radio de tolerancia: 5% del rango visible
        tol = max(L, W) * 0.05
        candidatos = {
            'L':  self.pos_monitor_l,
            'R':  self.pos_monitor_r,
            'SS': self.pos_sweet_spot,
        }
        for key, (px, py) in candidatos.items():
            if abs(xd - px) < tol and abs(yd - py) < tol:
                return key
        return None

    def _on_planta_press(self, event):
        if event.inaxes != self.ax_planta: return
        self._drag_target = self._hit_test_planta(event.xdata, event.ydata)

    def _on_planta_motion(self, event):
        if self._drag_target is None: return
        if event.inaxes != self.ax_planta: return
        try:
            L = float(self.entry_largo.get())
            W = float(self.entry_ancho.get())
        except ValueError:
            return
        # Clamp dentro de los límites de la sala con margen
        mx = max(0.05, min(event.xdata, L - 0.05))
        my = max(0.05, min(event.ydata, W - 0.05))
        if   self._drag_target == 'L':  self.pos_monitor_l  = [mx, my]
        elif self._drag_target == 'R':  self.pos_monitor_r  = [mx, my]
        elif self._drag_target == 'SS': self.pos_sweet_spot = [mx, my]
        self.dibujar_planta_o_mapa()

    def _on_planta_release(self, event):
        self._drag_target = None

    # ────────────────────────────────────────────────────────────────────────────

    def calcular_modos(self, L, W, H):
        c = 343.0
        modos = []
        lim_p = int((200 * 2 * L) / c) + 1
        lim_q = int((200 * 2 * W) / c) + 1
        lim_r = int((200 * 2 * H) / c) + 1

        for p in range(lim_p):
            for q in range(lim_q):
                for r in range(lim_r):
                    if p == 0 and q == 0 and r == 0: continue
                    f = (c / 2) * np.sqrt((p / L)**2 + (q / W)**2 + (r / H)**2)
                    if f <= 200.0:
                        ceros = [p, q, r].count(0)
                        tipo = "Axial" if ceros == 2 else "Tangencial" if ceros == 1 else "Oblicuo"
                        modos.append({"frec": round(f, 1), "tipo": tipo, "indices": (p, q, r)})
        return sorted(modos, key=lambda k: k['frec'])

    def analizar_bonello(self, modos):
        bandas_centros = [16, 20, 25, 31.5, 40, 50, 63, 80, 100, 125, 160, 200]
        conteos = []
        for fc in bandas_centros:
            f_inf = fc / (2**(1/6))
            f_sup = fc * (2**(1/6))
            num_modos = sum(1 for m in modos if f_inf <= m['frec'] <= f_sup)
            conteos.append((fc, num_modos))
        monotono = True
        for i in range(1, len(conteos)):
            if conteos[i][1] < conteos[i-1][1]:
                monotono = False
                break
        return conteos, monotono

    def dibujar_planta_o_mapa(self):
        try:
            L = float(self.entry_largo.get())
            W = float(self.entry_ancho.get())
            # Limpiar colorbar anterior para evitar acumulación visual
            if self._colorbar_planta is not None:
                try:
                    self._colorbar_planta.remove()
                except Exception:
                    pass
                self._colorbar_planta = None
            self.ax_planta.clear()
            
            if self.modo_seleccionado is None:
                ss_x, ss_y   = self.pos_sweet_spot
                sp1_x, sp1_y = self.pos_monitor_l
                sp2_x, sp2_y = self.pos_monitor_r

                # Fondo de sala
                rect = patches.Rectangle((0, 0), L, W, linewidth=2.5,
                    edgecolor='#1F6AA5', facecolor='#1F6AA5', alpha=0.08)
                self.ax_planta.add_patch(rect)

                # Líneas de tiro monitor → sweet spot
                self.ax_planta.plot([sp1_x, ss_x], [sp1_y, ss_y], color='#FF5555', linestyle=':', alpha=0.8, linewidth=1.5)
                self.ax_planta.plot([sp2_x, ss_x], [sp2_y, ss_y], color='#FF5555', linestyle=':', alpha=0.8, linewidth=1.5)

                # Calcular ángulo de escucha (ángulo entre los dos monitores visto desde el SS)
                import math
                ang_l  = math.degrees(math.atan2(sp1_y - ss_y, sp1_x - ss_x))
                ang_r  = math.degrees(math.atan2(sp2_y - ss_y, sp2_x - ss_x))
                angulo = abs(ang_l - ang_r)
                if angulo > 180: angulo = 360 - angulo
                dist_l = math.hypot(ss_x - sp1_x, ss_y - sp1_y)
                dist_r = math.hypot(ss_x - sp2_x, ss_y - sp2_y)
                simetria = abs(dist_l - dist_r)

                # Zona de primeras reflexiones (referencial entre monitores y SS)
                ref_lat_x = (sp1_x + ss_x) / 2
                zona_p_inf = patches.Rectangle((ref_lat_x - 0.4, 0),       0.8, 0.10, color='#A8552A', alpha=0.6, label="Zona Primeras Reflexiones")
                zona_p_sup = patches.Rectangle((ref_lat_x - 0.4, W - 0.10), 0.8, 0.10, color='#A8552A', alpha=0.6)
                self.ax_planta.add_patch(zona_p_inf)
                self.ax_planta.add_patch(zona_p_sup)

                # Marcadores con tamaño mayor para facilitar el drag
                self.ax_planta.plot(sp1_x, sp1_y, marker='s', color='#FF5555', markersize=12,
                    zorder=5, label="Monitor L  (arrastra)", markeredgecolor='white', markeredgewidth=0.8)
                self.ax_planta.plot(sp2_x, sp2_y, marker='s', color='#FF8855', markersize=12,
                    zorder=5, label="Monitor R  (arrastra)", markeredgecolor='white', markeredgewidth=0.8)
                self.ax_planta.plot(ss_x,  ss_y,  marker='*', color='#FFCC00', markersize=16,
                    zorder=5, label="Sweet Spot  (arrastra)", markeredgecolor='#AA8800', markeredgewidth=0.6)

                # Info en tiempo real: ángulo y simetría
                color_ang  = '#2A8C55' if 55 <= angulo <= 65 else '#FF5555'
                color_sim  = '#2A8C55' if simetria < 0.05 else '#FFAA00'
                self.ax_planta.set_title(
                    f"Plano de Planta — Ángulo de escucha: {angulo:.1f}°  |  Asimetría: {simetria*100:.1f} cm",
                    color=color_ang, pad=8, fontsize=10
                )
            else:
                p, q, r = self.modo_seleccionado['indices']
                frec = self.modo_seleccionado['frec']
                tipo = self.modo_seleccionado['tipo']
                
                self.ax_planta.set_title(f"Mapa de Presión: Modo {tipo} ({p},{q},{r}) @ {frec} Hz", color='white', fontsize=11)
                x = np.linspace(0, L, 150)
                y = np.linspace(0, W, 150)
                X, Y = np.meshgrid(x, y)
                Z = np.abs(np.cos((p * np.pi * X) / L) * np.cos((q * np.pi * Y) / W))
                mesh = self.ax_planta.pcolormesh(X, Y, Z, cmap='jet', shading='auto', vmin=0, vmax=1)
                cb = self.fig_planta.colorbar(mesh, ax=self.ax_planta, fraction=0.03, pad=0.02)
                cb.set_label("Presión Relativa", color='white', fontsize=8)
                cb.ax.yaxis.set_tick_params(color='white', labelcolor='white')
                self._colorbar_planta = cb
                
            self.ax_planta.set_xlabel("Largo - Eje X (m)", color='white')
            self.ax_planta.set_ylabel("Ancho - Eje Y (m)", color='white')
            self.ax_planta.set_xlim(-0.2, L + 0.2)
            self.ax_planta.set_ylim(-0.2, W + 0.2)
            self.ax_planta.grid(True, linestyle='--', alpha=0.3, color='#555555')
            self.ax_planta.set_aspect('equal')
            self.ax_planta.tick_params(colors='white')
            self.ax_planta.set_facecolor('#1E1E1E')
            self.ax_planta.legend(facecolor='#1A1A1A', edgecolor='none', labelcolor='white', loc='upper right', fontsize=9)
            
            self.fig_planta.tight_layout()
            self.canvas_planta.draw()
        except ValueError:
            pass

    def calcular_rt60_dinamico(self):
        """ALGORITMO DE EYRING-NORRIS COMPLETO: Escala dinámica en Y y acople físico realista"""
        try:
            L = float(self.entry_largo.get())
            W = float(self.entry_ancho.get())
            H = float(self.entry_alto.get())
            V = L * W * H
            
            areas_caras = {
                "Pared Frontal": W * H, "Pared Trasera": W * H,
                "Pared Izquierda": L * H, "Pared Derecha": L * H,
                "Techo": L * W, "Piso": L * W
            }
            S_total = sum(areas_caras.values())
            m_aire = np.array([0.0, 0.0, 0.0001, 0.00025, 0.0008, 0.0028])

            materiales_base_caras = {
                "Pared Frontal": self.combo_frontal.get(), "Pared Trasera": self.combo_trasera.get(),
                "Pared Izquierda": self.combo_izquierda.get(), "Pared Derecha": self.combo_derecha.get(),
                "Techo": self.combo_techo.get(), "Piso": self.combo_piso.get()
            }
            
            areas_restadas_por_cara = {k: 0.0 for k in areas_caras.keys()}
            absorcion_paneles_sabine = np.zeros(6)
            
            for panel in self.materiales_aplicados:
                area = panel["area_total"]
                cara_destino = panel["donde"]
                cara_normalizada = cara_destino.replace("Muros (Paredes)", "").replace(" (Paredes)", "").strip()

                if cara_normalizada in areas_restadas_por_cara:
                    areas_restadas_por_cara[cara_normalizada] += area
                absorcion_paneles_sabine += area * np.array(panel["alfas"])

            absorcion_base_total = np.zeros(6)
            for cara, area_total in areas_caras.items():
                area_libre = max(0.0, area_total - areas_restadas_por_cara[cara])
                nombre_mat_base = materiales_base_caras[cara]
                alfas_mat_base = np.array(self.diccionario_stock_materiales.get(nombre_mat_base, [0.04]*6))
                
                # Sincronización Acústica: Limitación elástica para emular pérdidas reales en obra gris
                if "Drywall" in nombre_mat_base or "Placa" in nombre_mat_base:
                    alfas_mat_base[0] = 0.04  
                    alfas_mat_base[1] = 0.04  

                alfas_mat_base = np.clip(alfas_mat_base, 0.03, 1.0)
                absorcion_base_total += area_libre * alfas_mat_base

            # --- MODELADO DE SALA TRATADA (EYRING) ---
            A_total_sala = absorcion_base_total + absorcion_paneles_sabine
            alfa_promedio_tratada = A_total_sala / S_total
            alfa_promedio_tratada = np.clip(alfa_promedio_tratada, 0.001, 0.99)
            RT60_actual = (0.161 * V) / (-S_total * np.log(1 - alfa_promedio_tratada) + (4 * m_aire * V))
            
            # --- MODELADO DE SALA VACÍA ---
            A_vacia = np.zeros(6)
            for cara, area_total in areas_caras.items():
                nombre_mat_base = materiales_base_caras[cara]
                alfas_mat_base = np.array(self.diccionario_stock_materiales.get(nombre_mat_base, [0.04]*6))
                if "Drywall" in nombre_mat_base or "Placa" in nombre_mat_base:
                    alfas_mat_base[0] = 0.04
                    alfas_mat_base[1] = 0.04
                alfas_mat_base = np.clip(alfas_mat_base, 0.03, 1.0)
                A_vacia += area_total * alfas_mat_base
                
            alfa_promedio_vacia = A_vacia / S_total
            alfa_promedio_vacia = np.clip(alfa_promedio_vacia, 0.001, 0.99)
            RT60_vacia = (0.161 * V) / (-S_total * np.log(1 - alfa_promedio_vacia) + (4 * m_aire * V))

            # Guardar estados en memoria para el predictor inverso
            self.S_total_actual = S_total
            self.V_actual = V
            self.A_total_sala_actual = A_total_sala
            self.materiales_base_caras_actual = materiales_base_caras

            # Actualizar textos informativos de la GUI
            self.lbl_superficie.configure(text=f"📏  Superficie Total: {S_total:.2f} m²")

            # --- REDIBUJAR GRÁFICA AUTO-ESCALABLE ---
            self.ax_rt.clear()
            self.ax_rt.set_title("Análisis Físico del Tiempo de Reverberación ($RT_{60}$)", color='white', fontsize=11)
            
            self.ax_rt.plot(self.bandas_octava, RT60_vacia, linestyle='--', marker='o', color='#FF5555', alpha=0.6, label="Sala Vacía (Estructura)")
            self.ax_rt.plot(self.bandas_octava, RT60_actual, marker='s', color='#2A8C55', linewidth=2.5, label="Sala Tratada")
            self.ax_rt.axhspan(0.2, 0.4, color='#1F6AA5', alpha=0.15, label="Rango Óptimo Mezcla")
            
            self.ax_rt.set_xlabel("Bandas de Octava", color='white')
            self.ax_rt.set_ylabel("Tiempo de Reverberación (Segundos)", color='white')
            
            # Auto-ajuste dinámico del eje Y basado en su propio pico
            max_tiempo_real = max(max(RT60_vacia), max(RT60_actual))
            self.ax_rt.set_ylim(0, max_tiempo_real + 0.2)
            
            self.ax_rt.grid(True, linestyle='--', alpha=0.3, color='#444444')
            self.ax_rt.tick_params(colors='white')
            self.ax_rt.legend(facecolor='#1A1A1A', edgecolor='none', labelcolor='white', loc='upper right')
            self.ax_rt.set_facecolor('#1E1E1E')
            self.fig_rt.tight_layout()
            self.canvas_rt.draw()
            
        except ValueError:
            pass

    def ejecutar_calculo_predictivo_inverso(self):
        """INGENIERÍA INVERSA: Calcula los m² requeridos para alcanzar un RT60 objetivo"""
        selected_item = self.tree_mat.selection()
        if not selected_item:
            messagebox.showerror("Error", "Primero debes seleccionar en el Inventario (Paso 1) qué material deseas que el programa calcule.")
            return

        valores_material = self.tree_mat.item(selected_item[0])['values']
        nombre_mat_nuevo = valores_material[0]
        alfas_mat_nuevo = [float(v) for v in valores_material[1:]]

        try:
            rt_objetivo = float(self.ent_rt_target.get())
            if rt_objetivo <= 0.05 or rt_objetivo > 2.0: raise ValueError
        except ValueError:
            messagebox.showerror("Error", "Ingresa un RT60 objetivo realista (entre 0.1s y 1.5s).")
            return

        frec_pivote_str = self.combo_frec_pivote.get()
        idx_banda = self.bandas_octava.index(frec_pivote_str)

        # Cargar datos geométricos del estado actual en memoria
        V = self.V_actual
        S_t = self.S_total_actual
        m_aire_banda = np.array([0.0, 0.0, 0.0001, 0.00025, 0.0008, 0.0028])[idx_banda]

        # 1. Despejar los Sabines totales requeridos aplicando Eyring a la inversa
        denominador_objetivo = (0.161 * V) / rt_objetivo
        termino_absorcion_superficie = denominador_objetivo - (4 * m_aire_banda * V)

        if termino_absorcion_superficie <= 0:
            self.lbl_resultado_prediccion.configure(text="Resultado: Imposible. El aire absorbe más que la meta.", text_color="#FF5555")
            return

        alfa_promedio_necesario = 1 - np.exp(-termino_absorcion_superficie / S_t)
        Sabines_necesarios_total = S_t * alfa_promedio_necesario

        # 2. Restar la absorción que ya tiene la sala actualmente instalada
        Sabines_actuales = self.A_total_sala_actual[idx_banda]
        deficit_sabines = Sabines_necesarios_total - Sabines_actuales

        if deficit_sabines <= 0:
            self.lbl_resultado_prediccion.configure(text="Resultado: ¡Tu sala ya cumple o supera la meta en esa frecuencia!", text_color="#2A8C55")
            return

        # 3. Evaluar el coeficiente neto sumando la sustitución (alfa_nuevo - alfa_base)
        # Asumiremos la cara por defecto elegida en el Step 2 para saber qué material se va a cubrir
        cara_referencia = self.combo_donde.get()
        nombre_mat_base_cubierto = self.materiales_base_caras_actual[cara_referencia]
        alfa_base_removido = self.diccionario_stock_materiales.get(nombre_mat_base_cubierto, [0.04]*6)[idx_banda]
        
        if "Drywall" in nombre_mat_base_cubierto or "Placa" in nombre_mat_base_cubierto:
            if idx_banda in [0, 1]: alfa_base_removido = 0.04 # Ajuste de rigidez real

        alfa_nuevo = alfas_mat_nuevo[idx_banda]
        coeficiente_neto_intercambio = alfa_nuevo - alfa_base_removido

        if coeficiente_neto_intercambio <= 0.05:
            self.lbl_resultado_prediccion.configure(text="Resultado: El material seleccionado no absorbe lo suficiente en esta banda.", text_color="#FF5555")
            return

        # 4. Despejar área final en m²
        area_requerida_m2 = deficit_sabines / coeficiente_neto_intercambio

        # Validar si el área requerida supera la superficie física de la sala
        if area_requerida_m2 > S_t:
            self.lbl_resultado_prediccion.configure(text=f"Resultado: Requiere {area_requerida_m2:.1f}m². Supera la superficie del cuarto.", text_color="#FF5555")
        else:
            self.lbl_resultado_prediccion.configure(
                text=f"Resultado: Necesitas instalar {area_requerida_m2:.2f} m² de {nombre_mat_nuevo} en {cara_referencia}.", 
                text_color="#38BDF8"
            )

    def on_modo_seleccionado(self, event):
        selected_item = self.tree.selection()
        if not selected_item:
            self.modo_seleccionado = None
            self.dibujar_planta_o_mapa()
            return
        item_idx = self.tree.index(selected_item[0])
        if item_idx < len(self.lista_modos):
            self.modo_seleccionado = self.lista_modos[item_idx]
            self.dibujar_planta_o_mapa()

    def cambiar_vista_bonello(self, value):
        self.tipo_grafico_bonello = value
        if self.lista_modos:
            conteos, _ = self.analizar_bonello(self.lista_modos)
            self.graficar_bonello(conteos)

    def graficar_bolt(self, L, W, H):
        self.ax_bolt.clear()
        self.ax_bolt.set_title("Criterio de Proporciones de Bolt", color='white', fontsize=12)
        bolt_x = [1.2, 1.4, 1.5, 1.6, 1.4, 1.2, 1.1, 1.2]
        bolt_y = [1.7, 2.1, 2.2, 2.0, 1.5, 1.4, 1.5, 1.7]
        self.ax_bolt.fill(bolt_x, bolt_y, color='#2A8C55', alpha=0.3, label="Región Óptima")
        self.ax_bolt.plot(W / H, L / H, marker='o', color='#FF5555', markersize=10, label="Tu Sala")
        self.ax_bolt.set_xlabel("Ancho / Alto", color='white')
        self.ax_bolt.set_ylabel("Largo / Alto", color='white')
        self.ax_bolt.set_xlim(0.5, 2.5)
        self.ax_bolt.set_ylim(1.0, 3.0)
        self.ax_bolt.grid(True, linestyle='--', alpha=0.3, color='#444444')
        self.ax_bolt.legend(facecolor='#1A1A1A', edgecolor='none', labelcolor='white')
        self.ax_bolt.tick_params(colors='white')
        self.ax_bolt.set_facecolor('#1E1E1E')
        self.fig_bolt.tight_layout()
        self.canvas_bolt.draw()

    def graficar_bonello(self, conteos_bonello):
        self.ax_bonello.clear()
        self.ax_bonello.set_title("Criterio de Bonello (1/3 de Octava)", color='white', fontsize=12)
        bandas = [str(c[0]) for c in conteos_bonello]
        valores = [c[1] for c in conteos_bonello]
        
        if self.tipo_grafico_bonello == "Barras":
            barras = self.ax_bonello.bar(bandas, valores, color='#1F6AA5', edgecolor='white', alpha=0.8)
            for i in range(1, len(valores)):
                if valores[i] < valores[i-1]: barras[i].set_color('#FF5555')
        else:
            self.ax_bonello.plot(bandas, valores, marker='o', linewidth=2, color='#1F6AA5', markersize=7)
            for i in range(1, len(valores)):
                if valores[i] < valores[i-1]:
                    self.ax_bonello.plot(bandas[i], valores[i], marker='o', color='#FF5555', markersize=9)
        self.ax_bonello.set_xlabel("Frecuencia Central de Banda (Hz)", color='white')
        self.ax_bonello.set_ylabel("Cantidad de Modos", color='white')
        self.ax_bonello.grid(True, linestyle='--', alpha=0.3, color='#444444')
        self.ax_bonello.tick_params(colors='white', axis='x', rotation=45)
        self.ax_bonello.set_facecolor('#1E1E1E')
        self.fig_bonello.tight_layout()
        self.canvas_bonello.draw()

    def ejecutar_diagnostico(self):
        try:
            L = float(self.entry_largo.get())
            W = float(self.entry_ancho.get())
            H = float(self.entry_alto.get())
            if L <= 0 or W <= 0 or H <= 0: raise ValueError

            self.lbl_volumen.configure(text=f"📐  Volumen de la Sala: {L*W*H:.2f} m³")
            self.lista_modos = self.calcular_modos(L, W, H)
            self.lbl_modos_count.configure(text=f"🎵  Modos (<200Hz): {len(self.lista_modos)}")

            # Inicializar posiciones arrastrables con valores por defecto acústicos
            # Se resetean siempre que cambian las dimensiones de la sala
            self.pos_sweet_spot  = [L * 0.38, W / 2]
            self.pos_monitor_l   = [0.50, W / 2 - W * 0.20]
            self.pos_monitor_r   = [0.50, W / 2 + W * 0.20]
            
            for item in self.tree.get_children(): self.tree.delete(item)
            for m in self.lista_modos:
                self.tree.insert("", "end", values=(f"{m['frec']} Hz", m['tipo'], f"({m['indices'][0]}, {m['indices'][1]}, {m['indices'][2]})"))

            self.modo_seleccionado = None
            self.dibujar_planta_o_mapa()

            conteos, cumple_bonello = self.analizar_bonello(self.lista_modos)
            if cumple_bonello:
                self.lbl_bonello_status.configure(text="✅  Bonello: CUMPLE (Monótono)", text_color="#2A8C55")
            else:
                self.lbl_bonello_status.configure(text="⚠️  Bonello: NO CUMPLE (Coloración)", text_color="#FF5555")

            self.graficar_bolt(L, W, H)
            self.graficar_bonello(conteos)
            self.calcular_rt60_dinamico()

        except ValueError:
            messagebox.showerror("Error", "Ingresa dimensiones válidas numéricas mayores a cero.")

if __name__ == "__main__":
    app = AcousticApp()
    app.mainloop()