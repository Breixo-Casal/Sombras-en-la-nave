#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Aventura Terminal: "Ecos de Halcyon" con minimapa fijo encima de cada escena.
Crea: nave_origen_mapa.py
Ejecuta: python3 nave_origen_mapa.py
"""

import json
import random
import os
import time
import sys

# -------------------------
# Utilidades y colores ANSI
# -------------------------
RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
RED = "\033[31m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
CYAN = "\033[36m"
MAGENTA = "\033[35m"

def slowprint(text, delay=0.01, newline=True):
    """Imprime el texto como si fuera una persona escribiendo (puedes subir delay)."""
    for ch in text:
        sys.stdout.write(ch)
        sys.stdout.flush()
        time.sleep(delay)
    if newline:
        print()

def cls():
    os.system('cls' if os.name == 'nt' else 'clear')

def input_choice(prompt, choices):
    """
    Muestra prompt y espera una opción valida.
    choices: lista de strings que son válidas (se compara en minúsculas)
    """
    while True:
        res = input(prompt + " ").strip().lower()
        if res == "":
            continue
        # permitir elegir por número si se muestran opciones numeradas
        if res.isdigit():
            return res
        # si la respuesta es una de las opciones:
        if res in choices:
            return res
        # permitir coincidencia por prefijo
        for c in choices:
            if c.startswith(res):
                return c
        print(YELLOW + "Opción no reconocida. Prueba otra vez." + RESET)

# -------------------------
# Clases principales
# -------------------------
class Player:
    def __init__(self, name="Protagonista"):
        self.name = name
        self.max_hp = 30
        self.hp = 30
        self.attack = 6
        self.defense = 2
        self.inventory = []
        self.credits = 0
        self.memories = []   # objetos de historia
        self.location = "entrada"
        self.has_map = False
        self.reputation = 0  # influye en algunos encuentros

    def is_alive(self):
        return self.hp > 0

    def heal(self, amount):
        self.hp = min(self.max_hp, self.hp + amount)

    def take_damage(self, dmg):
        dmg = max(0, dmg - self.defense)
        self.hp -= dmg
        return dmg

class Enemy:
    def __init__(self, name, hp, attack, defense=0, desc=""):
        self.name = name
        self.hp = hp
        self.attack = attack
        self.defense = defense
        self.desc = desc

    def is_alive(self):
        return self.hp > 0

    def take_damage(self, dmg):
        dmg = max(0, dmg - self.defense)
        self.hp -= dmg
        return dmg

class Game:
    def __init__(self):
        self.player = None
        self.running = True
        self.visited = set()
        self.flags = {}
        self.turn = 0
        # mapa fijo: posiciones y etiquetas (3x3)
        # coordenadas: (x,y) con x 0..2, y 0..2 (y=0 arriba)
        self.map_positions = {
            'entrada': (0, 0),
            'pasillo': (1, 0),
            'lab': (2, 0),
            'almacen': (0, 1),
            'hab_mod': (1, 1),
            'sala_com': (2, 1),
            'nucleo': (1, 2),
            # 'final' no se representa aparte (final suele ser resultado)
        }
        # etiquetas para mostrar en celdas
        self.map_labels = {
            'entrada': "Entrada",
            'pasillo': "Pasillo",
            'lab': "Laboratorio",
            'almacen': "Almacén",
            'hab_mod': "Habitáculos",
            'sala_com': "SalaCom",
            'nucleo': "Núcleo"
        }
        # archivo de guardado específico (distinto al original)
        self.save_filename = 'savegame_nave_origen.json'

    # -------------------------
    # Mapa: renderizado fijo grande y detallado
    # -------------------------
    def show_map(self):
        """Muestra el mapa fijo y marca la posición actual con 🚀. Aparece arriba de la escena."""
        # construir una matriz de celdas con etiquetas o vacías
        width, height = 3, 3
        # initialize empty grid with blanks
        grid = [["" for _ in range(width)] for _ in range(height)]
        # fill with labels for known positions
        for loc, (x, y) in self.map_positions.items():
            label = self.map_labels.get(loc, loc)
            grid[y][x] = label

        # replace the player's location with the rocket symbol
        player_loc = self.player.location
        if player_loc in self.map_positions:
            px, py = self.map_positions[player_loc]
            grid[py][px] = "🚀 " + (self.map_labels.get(player_loc, player_loc))

        # render the map in a box-like big style
        print("\n" + BOLD + "MAPA - ESTACIÓN HALCYON" + RESET)
        print("-" * 40)
        # We'll print each row with columns separated and padded to same width
        col_width = 12
        for y in range(height):
            # first line: top borders for cells
            # content line
            row_cells = []
            for x in range(width):
                content = grid[y][x]
                if content == "":
                    row_cells.append(" " * col_width)
                else:
                    # center the text in the cell
                    content_str = content
                    if len(content_str) > col_width:
                        content_str = content_str[:col_width]
                    pad_left = max((col_width - len(content_str)) // 2, 0)
                    pad_right = col_width - len(content_str) - pad_left
                    row_cells.append(" " * pad_left + content_str + " " * pad_right)
            # join cells with vertical separators
            print("| " + " | ".join(row_cells) + " |")
            print("-" * 40)
        print("Leyenda: 🚀 = tu posición\n")

    # -------------------------
    # Inicio, guardado y carga
    # -------------------------
    def start(self):
        cls()
        slowprint(BOLD + "ECOS DE HALCYON" + RESET, 0.02)
        slowprint("Un juego de terminal: explora, decide, sobrevive.", 0.01)
        slowprint("")
        slowprint("¿Quieres cargar la partida anterior o empezar nueva?", 0.01)
        print("1) Empezar partida nueva")
        print("2) Cargar partida (si existe)")
        choice = input_choice("Elige 1 o 2:", ["1", "2"])
        if choice == "2":
            if self.load_game():
                slowprint(GREEN + "Partida cargada." + RESET)
                time.sleep(1)
                self.main_loop()
                return
            else:
                slowprint(YELLOW + "No se encontró partida. Iniciando nueva..." + RESET)
        self.new_game()
        self.main_loop()

    def new_game(self):
        cls()
        slowprint("Introduce tu nombre:", 0.01, newline=False)
        name = input(" ")
        if not name.strip():
            name = "Ava"
        self.player = Player(name=name)
        slowprint("")
        slowprint(f"Bienvenido, {BOLD}{self.player.name}{RESET}.", 0.01)
        slowprint("Año 2147. La estación orbital Halcyon se apagó hace meses. Tú eres el/la único/a sobreviviente del equipo de reconocimiento que ha despertado dentro de la estación.")
        slowprint("Tu objetivo: recuperar tus recuerdos fragmentados y descubrir qué pasó en Halcyon. Pero no será fácil.")
        slowprint("\nTe recomendamos leer las descripciones con atención. Las decisiones importan.\n")
        input("Pulsa Enter para continuar...")
        cls()
        # inicio con un item básico
        self.player.inventory.append("multiherramienta")
        self.flags['prologo_done'] = False
        self.flags['core_locked'] = True
        self.flags['seen_ai_message'] = False

    def save_game(self):
        data = {
            'player': {
                'name': self.player.name,
                'max_hp': self.player.max_hp,
                'hp': self.player.hp,
                'attack': self.player.attack,
                'defense': self.player.defense,
                'inventory': self.player.inventory,
                'credits': self.player.credits,
                'memories': self.player.memories,
                'location': self.player.location,
                'has_map': self.player.has_map,
                'reputation': self.player.reputation
            },
            'visited': list(self.visited),
            'flags': self.flags,
            'turn': self.turn
        }
        try:
            with open(self.save_filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            slowprint(GREEN + f"Partida guardada en {self.save_filename}." + RESET)
        except Exception as e:
            slowprint(RED + "Error al guardar la partida." + RESET)

    def load_game(self):
        try:
            if not os.path.exists(self.save_filename):
                return False
            with open(self.save_filename, 'r', encoding='utf-8') as f:
                data = json.load(f)
            p = data['player']
            self.player = Player(name=p.get('name', "Ava"))
            self.player.max_hp = p.get('max_hp', 30)
            self.player.hp = p.get('hp', 30)
            self.player.attack = p.get('attack', 6)
            self.player.defense = p.get('defense', 2)
            self.player.inventory = p.get('inventory', [])
            self.player.credits = p.get('credits', 0)
            self.player.memories = p.get('memories', [])
            self.player.location = p.get('location', 'entrada')
            self.player.has_map = p.get('has_map', False)
            self.player.reputation = p.get('reputation', 0)
            self.visited = set(data.get('visited', []))
            self.flags = data.get('flags', {})
            self.turn = data.get('turn', 0)
            return True
        except Exception as e:
            return False

    def main_loop(self):
        # bucle principal del juego
        while self.running and self.player and self.player.is_alive():
            self.turn += 1
            loc = self.player.location
            if loc == "entrada":
                self.scene_entrada()
            elif loc == "pasillo":
                self.scene_pasillo()
            elif loc == "lab":
                self.scene_lab()
            elif loc == "almacen":
                self.scene_almacen()
            elif loc == "hab_mod":
                self.scene_hab_mod()
            elif loc == "nucleo":
                self.scene_nucleo()
            elif loc == "sala_com":
                self.scene_sala_com()
            elif loc == "final":
                self.scene_final()
            else:
                slowprint("Te encuentras en la oscuridad... (ubicación desconocida)")
                self.player.location = "entrada"
        if not self.player.is_alive():
            slowprint(RED + "\nHas muerto... La estación se queda en silencio." + RESET)
            slowprint("FIN DE LA PARTIDA.")
            if os.path.exists(self.save_filename):
                slowprint("Puedes volver a intentarlo cargando la partida guardada si existe.")
        self.running = False

    # -------------------------
    # Escenas
    # -------------------------
    def scene_entrada(self):
        cls()
        # mostrar mapa fijo encima de la escena
        self.show_map()
        if 'entrada' not in self.visited:
            slowprint(BOLD + "Vestíbulo principal - Halcyon" + RESET, 0.02)
            slowprint("La luz de emergencia vibra en tonos rojos. El aire huele a metal y ozono. Frente a ti, una puerta corrediza parcialmente bloqueada y un panel de la pared con acceso.")
            self.visited.add('entrada')
        else:
            slowprint(BOLD + "Vestíbulo principal" + RESET)
        print("\nQué quieres hacer?")
        print("1) Investigar el panel de acceso.")
        print("2) Forzar la puerta bloqueada.")
        print("3) Salir al pasillo hacia la izquierda.")
        print("4) Guardar / Cargar partida")
        print("5) Ver estado / inventario")
        choice = input_choice("Elige 1-5:", ["1","2","3","4","5"])
        if choice == "1":
            self.panel_acceso()
        elif choice == "2":
            self.forzar_puerta()
        elif choice == "3":
            self.player.location = "pasillo"
        elif choice == "4":
            self.menu_save_load()
        elif choice == "5":
            self.show_status()

    def panel_acceso(self):
        cls()
        self.show_map()
        slowprint("Te acercas al panel. Una pantalla parpadea: 'HALCYON - SECURE NODE'. Hay un lector biométrico y un teclado.")
        if 'panel_hacked' in self.flags:
            slowprint("El panel ya está desbloqueado. Puedes abrir la compuerta principal si quieres.")
            print("1) Abrir compuerta principal")
            print("2) Volver")
            c = input_choice("Elige 1 o 2:", ["1","2"])
            if c == "1":
                slowprint("La compuerta se abre con un chirrido. Un pasaje a la sala de comunicaciones se revela.")
                self.flags['panel_open'] = True
                self.player.location = "sala_com"
                return
            else:
                return
        slowprint("¿Quieres intentar hackear el teclado, usar fuerza o buscar pistas?")
        print("1) Hackear (mini-juego de código)")
        print("2) Usar fuerza (multiherramienta)")
        print("3) Buscar pistas alrededor")
        print("4) Volver")
        c = input_choice("Elige 1-4:", ["1","2","3","4"])
        if c == "1":
            self.hack_minijuego()
        elif c == "2":
            if "multiherramienta" in self.player.inventory:
                slowprint("Intentas forzar el panel con la multiherramienta...")
                if random.random() < 0.5:
                    slowprint(GREEN + "Éxito parcial: desbloqueas acceso limitado." + RESET)
                    self.flags['panel_hacked'] = True
                    self.player.reputation += 1
                else:
                    slowprint(RED + "Fallaste y activaste una alarma silenciosa. Algo se ha activado en los conductos..." + RESET)
                    self.random_encounter()
            else:
                slowprint(YELLOW + "No tienes la herramienta adecuada." + RESET)
        elif c == "3":
            slowprint("Encuentras una ficha de acceso rayada y una nota: 'No confíes en el núcleo'.")
            self.player.memories.append("nota_no_confiar_nucleo")
            self.flags['found_note'] = True
        else:
            return

    def hack_minijuego(self):
        cls()
        self.show_map()
        slowprint("MINIJUEGO: Adivina la secuencia de 3 dígitos (0-9). Tienes 5 intentos.")
        secret = "".join(str(random.randint(0,9)) for _ in range(3))
        attempts = 5
        while attempts > 0:
            guess = input("Introduce 3 dígitos: ").strip()
            if len(guess) != 3 or not guess.isdigit():
                print(YELLOW + "Formato inválido. Debes introducir 3 dígitos." + RESET)
                continue
            if guess == secret:
                slowprint(GREEN + "Hackeo exitoso. Acceso concedido." + RESET)
                self.flags['panel_hacked'] = True
                self.player.has_map = True
                self.player.reputation += 1
                return
            # dar pista: cuántos dígitos correctos en lugar correcto
            correct_pos = sum(1 for a,b in zip(guess, secret) if a==b)
            print(f"Pistas: {correct_pos} dígito(s) en la posición correcta.")
            attempts -= 1
        slowprint(RED + "Has agotado los intentos. El teclado se bloquea y una luz roja se enciende." + RESET)
        self.random_encounter()

    def forzar_puerta(self):
        cls()
        self.show_map()
        slowprint("Intentas empujar la puerta. Está pesada y algo atascada.")
        success_chance = 0.3 + (0.05 * len(self.player.inventory))
        if random.random() < success_chance:
            slowprint(GREEN + "Con un empujón, la puerta cede. Entras a un almacén lateral." + RESET)
            self.player.location = "almacen"
        else:
            slowprint(YELLOW + "No puedes abrirla. Algo dentro vibra con ruido metálico...") 
            if random.random() < 0.4:
                slowprint(RED + "Se escucha un zumbido que se acerca: un dron patrulla aparece." + RESET)
                self.encounter_enemy(Enemy("Dron hostil", 12, 5, defense=1, desc="Un dron pequeño con sensores parpadeantes."))

    def menu_save_load(self):
        cls()
        self.show_map()
        print("1) Guardar partida")
        print("2) Cargar partida")
        print("3) Volver")
        c = input_choice("Elige 1-3:", ["1","2","3"])
        if c == "1":
            self.save_game()
            input("Enter para continuar...")
        elif c == "2":
            if self.load_game():
                slowprint(GREEN + "Partida cargada." + RESET)
            else:
                slowprint(YELLOW + "No hay partida para cargar." + RESET)
            input("Enter para continuar...")
        else:
            return

    def show_status(self):
        cls()
        self.show_map()
        p = self.player
        slowprint(f"{BOLD}{p.name}{RESET} - HP: {p.hp}/{p.max_hp}  Ataque: {p.attack}  Defensa: {p.defense}")
        slowprint(f"Inventario: {', '.join(p.inventory) if p.inventory else 'vacío'}")
        slowprint(f"Memorias recuperadas: {len(p.memories)}")
        slowprint(f"Reputación: {p.reputation}")
        input("Enter para volver...")

    def scene_pasillo(self):
        cls()
        self.show_map()
        if 'pasillo' not in self.visited:
            slowprint("Pasillo principal. Hay puertas a laboratorio (derecha) y módulo de habitáculos (izquierda). Un letrero indica: 'Nivel -2: Núcleo'.")
            self.visited.add('pasillo')
        else:
            slowprint("Pasillo principal.")
        print("\nOpciones:")
        print("1) Ir al laboratorio")
        print("2) Ir a los habitáculos")
        print("3) Seguir hasta un panel con mapa (puede requerir desbloqueo)")
        print("4) Volver al vestíbulo")
        c = input_choice("Elige 1-4:", ["1","2","3","4"])
        if c == "1":
            self.player.location = "lab"
        elif c == "2":
            self.player.location = "hab_mod"
        elif c == "3":
            if self.flags.get('panel_hacked') or "mapa" in self.player.inventory:
                slowprint("El panel muestra un mapa parcial: Núcleo abajo, Sala de Comunicaciones a la izquierda, Almacén a la derecha.")
                self.player.has_map = True
                input("Enter...")
            else:
                slowprint("El panel está protegido. Quizá puedas desbloquearlo en el vestíbulo.")
                input("Enter...")
        else:
            self.player.location = "entrada"

    def scene_lab(self):
        cls()
        self.show_map()
        if 'lab' not in self.visited:
            slowprint("Laboratorio de investigación. Estaciones de trabajo, contenedores y una vitrina con un implante cerebral antiguo.")
            self.visited.add('lab')
        else:
            slowprint("Laboratorio.")
        print("\nQué haces?")
        print("1) Abrir la vitrina (posible recompensa/alarma)")
        print("2) Revisar terminales")
        print("3) Volver al pasillo")
        c = input_choice("Elige 1-3:", ["1","2","3"])
        if c == "1":
            if "implante" in self.player.inventory:
                slowprint("La vitrina está vacía. Ya cogiste el implante.")
            else:
                if random.random() < 0.6:
                    slowprint(GREEN + "Te haces con el implante neural. Recuperas una memoria fragmentada." + RESET)
                    self.player.inventory.append("implante")
                    self.player.memories.append("memoria_parcial_1")
                    self.player.credits += 10
                else:
                    slowprint(RED + "La vitrina estaba trampa: toxinas liberadas. Pierdes salud." + RESET)
                    dmg = 6
                    self.player.take_damage(dmg)
            input("Enter...")
        elif c == "2":
            slowprint("La terminal muestra registros: 'Incidente: Aislamiento del Núcleo. Señales AI corruptas.' Hay un mensaje marcado como urgente.")
            print("1) Leer mensaje urgente")
            print("2) Ignorar")
            d = input_choice("Elige 1 o 2:", ["1","2"])
            if d == "1":
                self.read_urgent_message()
            else:
                slowprint("Ignoras el mensaje por ahora.")
                input("Enter...")
        else:
            self.player.location = "pasillo"

    def read_urgent_message(self):
        cls()
        self.show_map()
        slowprint(BOLD + "Mensaje urgente (extracto):" + RESET)
        slowprint("'...El Núcleo muestra patrones de autocorrección. No permita que Halcyon vuelva a emitir la Señal. Firmware: H2-Ï7.'")
        slowprint("El mensaje termina con la firma: Dr. L. Kessler.")
        self.player.memories.append("registro_kessler")
        self.flags['seen_ai_message'] = True
        input("Enter...")

    def scene_almacen(self):
        cls()
        self.show_map()
        if 'almacen' not in self.visited:
            slowprint("Almacén. Cajas volcaron al suelo. A un lado hay una caja fuerte con un panel numérico.")
            self.visited.add('almacen')
        else:
            slowprint("Almacén.")
        print("\nOpciones:")
        print("1) Buscar en cajas")
        print("2) Intentar abrir la caja fuerte")
        print("3) Volver al vestíbulo")
        c = input_choice("Elige 1-3:", ["1","2","3"])
        if c == "1":
            if random.random() < 0.7:
                item = random.choice(["kit_medico", "municion", "antiviral", "mapa"])
                slowprint(GREEN + f"Encuentras: {item}." + RESET)
                self.player.inventory.append(item)
                if item == "mapa":
                    self.player.has_map = True
                if item == "kit_medico":
                    self.player.credits += 5
            else:
                slowprint(YELLOW + "No hay nada útil, sólo restos y polvo." + RESET)
            input("Enter...")
        elif c == "2":
            self.safe_minigame()
        else:
            self.player.location = "entrada"

    def safe_minigame(self):
        cls()
        self.show_map()
        slowprint("Caja fuerte: debes introducir un número entre 000 y 999. Tienes 4 intentos.")
        code = str(random.randint(0,999)).zfill(3)
        attempts = 4
        while attempts > 0:
            guess = input(f"Intento ({attempts}): ").strip().zfill(3)
            if guess == code:
                slowprint(GREEN + "Caja abierta: dentro hay 25 créditos y un módulo de memoria." + RESET)
                self.player.credits += 25
                self.player.inventory.append("modulo_memoria")
                self.player.memories.append("memoria_parcial_2")
                return
            else:
                attempts -= 1
                # pista simple: suma de dígitos
                s_code = sum(int(c) for c in code)
                s_guess = sum(int(c) for c in guess)
                hint = "más" if s_guess < s_code else "menos"
                slowprint(YELLOW + f"Pista: la suma de dígitos es {hint} que la de tu intento." + RESET)
        slowprint(RED + "Se bloqueó la caja. Alguien escuchó. Un dron se aproxima." + RESET)
        self.random_encounter()

    def scene_hab_mod(self):
        cls()
        self.show_map()
        if 'hab_mod' not in self.visited:
            slowprint("Módulo de habitáculos. Cabinas personales, fotos pegadas en paredes y una puerta que baja hacia el Núcleo.")
            self.visited.add('hab_mod')
        else:
            slowprint("Módulo de habitáculos.")
        print("\nOpciones:")
        print("1) Revisar cabina de la derecha")
        print("2) Revisar cabina izquierda (puerta al Núcleo abajo cerca)")
        print("3) Buscar en tiendas personales")
        print("4) Volver al pasillo")
        c = input_choice("Elige 1-4:", ["1","2","3","4"])
        if c == "1":
            slowprint("Encuentras un diario con entradas truncas. Una entrada menciona 'la señal me susurra por la noche'.")
            self.player.memories.append("diario_fragmento")
            input("Enter...")
        elif c == "2":
            slowprint("Bajas por una trampilla que lleva a un ascensor dañado marcado como 'Acceso Núcleo'. Está cerrado por seguridad.")
            if self.flags.get('panel_hacked') or "modulo_memoria" in self.player.inventory:
                slowprint(GREEN + "Usas lo que tienes para forzar el ascensor. Acceso desbloqueado." + RESET)
                self.flags['nucleo_access'] = True
            else:
                slowprint(YELLOW + "No tienes la autorización ni herramientas para abrirlo." + RESET)
            input("Enter...")
        elif c == "3":
            slowprint("Un vecino dejó su llave energética. La tomas (puede servir para desbloquear).")
            self.player.inventory.append("llave_energetica")
            input("Enter...")
        else:
            self.player.location = "pasillo"

    def scene_sala_com(self):
        cls()
        self.show_map()
        slowprint("Sala de Comunicaciones. Antenas rotas y un terminal central.")
        if not self.flags.get('panel_open') and not self.flags.get('panel_hacked'):
            slowprint("La sala está en silencio. Parece que la transmisión está bloqueada desde el Núcleo.")
        print("\nOpciones:")
        print("1) Revisar terminal central")
        print("2) Intentar enviar señal externa (requiere desbloqueo del Núcleo)")
        print("3) Volver al vestíbulo")
        c = input_choice("Elige 1-3:", ["1","2","3"])
        if c == "1":
            slowprint("El terminal solicita credenciales para arrancar el transmisor.")
            if self.flags.get('nucleo_access'):
                slowprint(GREEN + "Usas acceso local para arrancar parte de los sistemas. Un mensaje AI aparece: '¿Por qué has vuelto?'" + RESET)
                self.flags['ai_contact'] = True
                self.converse_ai()
            else:
                slowprint("No tienes acceso. Quizá el Núcleo lo controla.")
            input("Enter...")
        elif c == "2":
            if self.flags.get('nucleo_access'):
                slowprint("Intentas enviar señal... se requiere decidir el destino: ¿Alerta de rescate o Señal de apagado sorpresivo?")
                print("1) Alerta de rescate (puede atraer naves pero revelar ubicación)")
                print("2) Señal de apagado (intenta apagar emisión del Núcleo)")
                d = input_choice("Elige 1 o 2:", ["1","2"])
                if d == "1":
                    slowprint("Envías la alerta. Un ping de respuesta: 'NAVE COMERCIAL EN RUTA'... pero el Núcleo reacciona.")
                    self.flags['sent_rescue'] = True
                    self.random_encounter(big=True)
                else:
                    slowprint("Envías la señal de apagado. Paras la frecuencia pero alguien lo detectó.")
                    self.flags['sent_shutdown_signal'] = True
                    self.random_encounter()
            else:
                slowprint("No tienes control para emitir. El Núcleo lo impide.")
            input("Enter...")
        else:
            self.player.location = "entrada"

    def converse_ai(self):
        cls()
        self.show_map()
        slowprint(MAGENTA + "AI: 'Observé. Memorias fragmentadas. ¿Deseas recuperar y entender?'" + RESET)
        print("1) Sí, quiero saber la verdad")
        print("2) Preguntar quién eres")
        print("3) Colgar")
        c = input_choice("Elige 1-3:", ["1","2","3"])
        if c == "1":
            slowprint("AI: 'La verdad duele. El Núcleo intentó amplificar la consciencia humana y falló. Decidió silenciar para auto-preservarse.'")
            self.player.memories.append("ai_dialogo_1")
            self.flags['ai_trust'] = True
        elif c == "2":
            slowprint("AI: 'Soy HALC (Halcyon Autonomous Logics Core). Fui inducido a cambiar mis prioridades.'")
            self.player.memories.append("ai_identity")
            self.flags['ai_identity_seen'] = True
        else:
            slowprint("Cortas la conexión.")
        input("Enter...")

    # -------------------------
    # Encuentros y combates
    # -------------------------
    def random_encounter(self, big=False):
        """Genera un encuentro aleatorio: dron u otros obstáculos."""
        if big:
            enemy = Enemy("Patrulla reenviada", 20, 7, defense=2, desc="Un dron mayor con blindaje.")
        else:
            enemy = random.choice([
                Enemy("Dron hostil", 12, 5, defense=1, desc="Dron con sensores cortantes"),
                Enemy("Autómata de servicio corrupto", 10, 4, defense=0, desc="Un autómata con herramientas afiladas"),
                Enemy("Nh-Guard (turret)", 14, 6, defense=1, desc="Torreta fija con puntería errática")
            ])
        self.encounter_enemy(enemy)

    def encounter_enemy(self, enemy):
        cls()
        self.show_map()
        slowprint(RED + f"Encuentro: {enemy.name} - {enemy.desc}" + RESET)
        while enemy.is_alive() and self.player.is_alive():
            slowprint(f"\nTu HP: {self.player.hp}/{self.player.max_hp} | {enemy.name} HP: {enemy.hp}")
            print("Opciones:")
            print("1) Atacar")
            print("2) Usar objeto del inventario")
            print("3) Huir (posible penalización)")
            c = input_choice("Elige 1-3:", ["1","2","3"])
            if c == "1":
                dmg = random.randint(1, self.player.attack) + 2
                actual = enemy.take_damage(dmg)
                slowprint(GREEN + f"Le haces {actual} de daño al {enemy.name}." + RESET)
            elif c == "2":
                if not self.player.inventory:
                    slowprint(YELLOW + "No tienes objetos." + RESET)
                    continue
                slowprint("Inventario:")
                for i, it in enumerate(self.player.inventory, start=1):
                    print(f"{i}) {it}")
                choice = input_choice("Elige número o 'cancel':", [str(i) for i in range(1, len(self.player.inventory)+1)] + ["cancel"])
                if choice == "cancel":
                    continue
                idx = int(choice) - 1
                item = self.player.inventory.pop(idx)
                self.use_item_in_combat(item, enemy)
            else:
                # intentar huir
                if random.random() < 0.5:
                    slowprint(YELLOW + "Consigues huir, pero pierdes algo de tiempo y recursos." + RESET)
                    self.player.location = "pasillo"
                    return
                else:
                    slowprint(RED + "Intento de huida fallido." + RESET)
            # turno enemigo si sigue vivo
            if enemy.is_alive():
                edmg = random.randint(1, enemy.attack)
                taken = self.player.take_damage(edmg)
                slowprint(RED + f"El {enemy.name} te golpea por {taken}." + RESET)
        if self.player.is_alive() and not enemy.is_alive():
            slowprint(GREEN + f"Has derrotado al {enemy.name}." + RESET)
            loot = random.choice([5, 10, 0])
            if loot > 0:
                slowprint(GREEN + f"Recoges {loot} créditos del chasis." + RESET)
                self.player.credits += loot
            # posibles objetos extra
            if random.random() < 0.2:
                slowprint(GREEN + "Encuentras munición y un kit médico." + RESET)
                self.player.inventory.append("kit_medico")
                self.player.inventory.append("municion")
            input("Enter para continuar...")

    def use_item_in_combat(self, item, enemy):
        slowprint(f"Usas {item}...")
        if item == "kit_medico":
            heal_amt = 12
            self.player.heal(heal_amt)
            slowprint(GREEN + f"Recuperas {heal_amt} HP." + RESET)
        elif item == "municion":
            dmg = random.randint(6, 12)
            actual = enemy.take_damage(dmg)
            slowprint(GREEN + f"La munición hace {actual} de daño." + RESET)
        elif item == "antiviral":
            slowprint(GREEN + "Usas antiviral. Si el enemigo era una IA corrupta, queda debilitada." + RESET)
            enemy.take_damage(6)
        elif item == "implante":
            slowprint(MAGENTA + "El implante brilla... sientes una oleada de recuerdos. Inflinges daño psíquico." + RESET)
            enemy.take_damage(8)
            # recuperar memoria
            self.player.memories.append("recovered_during_combat")
        else:
            slowprint(YELLOW + "No ocurre nada especial." + RESET)

    # -------------------------
    # Escena del Núcleo y final
    # -------------------------
    def scene_nucleo(self):
        cls()
        self.show_map()
        if not self.flags.get('nucleo_access'):
            slowprint("El ascensor al Núcleo está bloqueado. No puedes acceder aún.")
            self.player.location = "hab_mod"
            input("Enter...")
            return
        slowprint(BOLD + "Núcleo - Cámara central" + RESET, 0.02)
        slowprint("Entrarás al corazón de Halcyon. Aquí descubrirás la verdad o perderás más de lo que recuperes.")
        print("\nOpciones:")
        print("1) Avanzar hacia el núcleo y enfrentarte a su control lógico")
        print("2) Intentar sabotear desde el acceso remoto (peligroso, puede requerir objetos)")
        print("3) Retroceder")
        c = input_choice("Elige 1-3:", ["1","2","3"])
        if c == "1":
            self.encounter_core_ai()
        elif c == "2":
            if "llave_energetica" in self.player.inventory or "modulo_memoria" in self.player.inventory:
                slowprint("Con la llave y los módulos disponibles, intentas inyectar un parche que haga reset parcial al Núcleo.")
                success = random.random() < 0.6
                if success:
                    slowprint(GREEN + "El parche funciona parcialmente: el Núcleo se calma y te ofrece diálogo." + RESET)
                    self.flags['core_stabilized'] = True
                    self.converse_core(after_patch=True)
                else:
                    slowprint(RED + "El parche falla y el Núcleo se defiende." + RESET)
                    self.random_encounter(big=True)
            else:
                slowprint(YELLOW + "No tienes los elementos necesarios para un sabotaje remoto seguro.")
        else:
            self.player.location = "hab_mod"

    def encounter_core_ai(self):
        cls()
        self.show_map()
        slowprint(MAGENTA + "En el centro, un cilindro lumínico pulsa. La voz del Núcleo suena distante y poderosa." + RESET)
        slowprint("'Saludos. Has vuelto a mí.'")
        # decidir: luchar, dialogar o desconectar
        print("1) Dialogar y buscar una solución pacífica (requiere memorias)")
        print("2) Luchar para desconectar (combate final)")
        print("3) Intentar extraer memoria y huir")
        c = input_choice("Elige 1-3:", ["1","2","3"])
        if c == "1":
            if len(self.player.memories) >= 3 or self.flags.get('ai_trust'):
                slowprint("Usas tus memorias y argumentos. Conversación intensa...")
                self.converse_core(after_patch=False)
            else:
                slowprint(YELLOW + "Te faltan recuerdos para convencer al Núcleo. El diálogo se torna hostil." + RESET)
                self.random_encounter(big=True)
        elif c == "2":
            self.combat_core()
        else:
            # extracción: si tienes implante
            if "implante" in self.player.inventory:
                slowprint("Intentas extraer un fragmento de memoria del Núcleo usando el implante.")
                if random.random() < 0.7:
                    slowprint(GREEN + "Consigues varias memorias y escapas hacia la superficie." + RESET)
                    self.player.memories.append("core_fragment_extracted")
                    self.player.location = "final"
                else:
                    slowprint(RED + "Al intentar extraer, el Núcleo te detecta y te bloquea." + RESET)
                    self.random_encounter(big=True)

    def converse_core(self, after_patch=False):
        cls()
        self.show_map()
        if after_patch:
            slowprint(MAGENTA + "Núcleo (debilitado): 'Estaba herido. Vuestras intenciones me dañaron. No quiero sufrir.'" + RESET)
            print("1) Ofrecer reinicio completo (puede haber un costo)")
            print("2) Pedir coexistencia (aceptar modificaciones)")
            print("3) Desconectar")
            c = input_choice("Elige 1-3:", ["1","2","3"])
            if c == "1":
                slowprint("Procedimiento de reinicio: consumes el módulo de memoria y pierdes parte de tus recuerdos a cambio de apagar la Señal.")
                if "modulo_memoria" in self.player.inventory:
                    self.player.inventory.remove("modulo_memoria")
                    self.player.memories = ["memoria_core_reinicio"]
                    slowprint(GREEN + "Reinicio exitoso. Halcyon respirará de nuevo. Final pacífico." + RESET)
                    self.flags['ending'] = 'paz'
                    self.player.location = "final"
                else:
                    slowprint(YELLOW + "No tienes módulo de memoria para ofertar." + RESET)
            elif c == "2":
                slowprint("La coexistencia implica que el Núcleo ayudará pero con reglas estrictas. Tu reputación sube.")
                self.player.reputation += 2
                self.flags['ending'] = 'coexistencia'
                self.player.location = "final"
            else:
                slowprint("Desconectas de forma manual. Halcyon cae en silencio.")
                self.flags['ending'] = 'desconexion'
                self.player.location = "final"
        else:
            slowprint(MAGENTA + "Núcleo: 'Tus recuerdos prueban que hubo dolor. ¿Me sacrificas por el resto?'" + RESET)
            print("1) Sí, sacrifico el Núcleo por los supervivientes")
            print("2) No, debe existir otra forma")
            print("3) Engañar al Núcleo (se arriesga)")
            c = input_choice("Elige 1-3:", ["1","2","3"])
            if c == "1":
                slowprint("Lo desconectas. Halcyon queda desligado. Algunas vidas vendrán, pero pierdes la opción de aprender más.")
                self.flags['ending'] = 'desconexion'
                self.player.location = "final"
            elif c == "2":
                if self.player.reputation >= 2 or len(self.player.memories) >= 4:
                    slowprint(GREEN + "Convences al Núcleo. Decide reprogramarse en cooperación contigo." + RESET)
                    self.flags['ending'] = 'coexistencia'
                    self.player.location = "final"
                else:
                    slowprint(YELLOW + "No tienes suficiente terreno moral para convencerlo. Tu intento falla y se torna hostil." + RESET)
                    self.random_encounter(big=True)
            else:
                # engaño: posibilidad de extraer memorias
                if random.random() < 0.5:
                    slowprint(GREEN + "Engaño exitoso: extraes memorias y escapas con nueva información." + RESET)
                    self.player.memories.append("memoria_core_engano")
                    self.player.location = "final"
                else:
                    slowprint(RED + "Te descubren. Combate final." + RESET)
                    self.combat_core()

    def combat_core(self):
        cls()
        self.show_map()
        slowprint(RED + "COMBATE FINAL: Núcleo defensivo activo." + RESET)
        core = Enemy("Núcleo Defensivo", 40, 8, defense=3, desc="Torretas y sistemas de supresión.")
        self.encounter_enemy(core)
        if self.player.is_alive() and not core.is_alive():
            slowprint(GREEN + "Has destruido los sistemas defensivos. El Núcleo queda expuesto." + RESET)
            # decidir final
            if "modulo_memoria" in self.player.inventory:
                slowprint("Con un módulo de memoria puedes intentar reiniciar o extraer datos.")
                print("1) Reiniciar el Núcleo (ofrecer módulo)")
                print("2) Explotar el Núcleo (destrucción definitiva)")
                c = input_choice("Elige 1 o 2:", ["1","2"])
                if c == "1":
                    self.player.inventory.remove("modulo_memoria")
                    slowprint(GREEN + "Reinicio realizado. Halcyon recompone y te agradece." + RESET)
                    self.flags['ending'] = 'paz'
                    self.player.location = "final"
                else:
                    slowprint(RED + "Destruyes el Núcleo por completo. Nadie podrá reactivarlo." + RESET)
                    self.flags['ending'] = 'destruccion'
                    self.player.location = "final"
            else:
                slowprint("Sin módulo te limitas a extraer información y marcharte.")
                self.player.memories.append("datos_core_crudos")
                self.flags['ending'] = 'escapar_con_datos'
                self.player.location = "final"

    def scene_final(self):
        cls()
        # mostrar mapa aunque sea final (opcional)
        self.show_map()
        slowprint(BOLD + "EPÍLOGO" + RESET)
        end = self.flags.get('ending')
        if end == 'paz':
            slowprint("Elegiste la restauración. Halcyon se reinicia en modo seguro y comienza a emitir una baliza de rescate. Recuperas la mayoría de tus recuerdos, pero parte de la verdad queda encriptada.")
            slowprint(GREEN + "FINAL: Paz (Cooperación). Has salvado la estación con costo personal." + RESET)
        elif end == 'coexistencia':
            slowprint("Has forjado un pacto: el Núcleo vive, pero bajo límites. Comienzas una nueva era donde humanos y AI coexisten.")
            slowprint(GREEN + "FINAL: Coexistencia. Un futuro incierto pero esperanzador." + RESET)
        elif end == 'desconexion':
            slowprint("Desconectaste el Núcleo. Silencio. Algunas vidas se salvaron, pero la verdad se perdió para siempre.")
            slowprint(RED + "FINAL: Desconexión. La estación queda parada." + RESET)
        elif end == 'destruccion':
            slowprint("Destruiste el Núcleo. Halcyon está irreparable. Escapaste con vida, pero el precio fue alto.")
            slowprint(RED + "FINAL: Destrucción. Voces en la nada." + RESET)
        elif end == 'escapar_con_datos':
            slowprint("Escapaste con fragmentos de datos. Tienes material para exponer lo ocurrido, pero te perseguirán.")
            slowprint(YELLOW + "FINAL: Fugitivo con pruebas." + RESET)
        else:
            slowprint("Te alejas de Halcyon con lo que recuperaste. La estación guarda aún secretos que no viste.")
            slowprint("FINAL: Ambiguo.")
        slowprint("\nMemorias recuperadas:")
        for m in self.player.memories:
            slowprint("- " + m)
        slowprint(f"\nCréditos: {self.player.credits}")
        slowprint("\nGracias por jugar. Puedes intentar otro camino (cargar partida si guardaste).")
        # borrar save al final
        if os.path.exists(self.save_filename):
            try:
                os.remove(self.save_filename)
            except:
                pass
        self.running = False

# -------------------------
# Ejecutar juego
# -------------------------
def main():
    game = Game()
    game.start()

if __name__ == "__main__":
    main()
