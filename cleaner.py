"""
==============================================================================
TIKTOK AUTO CLEANER PRO (Terminal Edition)
Automatización segura para eliminar publicaciones COMPARTIDAS (Reposts)
y videos GUARDADOS (Favoritos / Bookmarks) en TikTok Web.
==============================================================================
"""

import os
import sys
import time
import socket
import random
import subprocess
import msvcrt
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

TIKTOK_URL = "https://www.tiktok.com"
DEBUG_PORT = 9222

# Configuración de ritmo seguro para segundo plano (Anti-Rate Limit)
BATCH_SIZE = 30           # Cantidad de elementos eliminados antes de enfriamiento
COOLDOWN_SECONDS = 25     # Segundos de pausa entre lotes
MIN_VIDEO_DELAY = 1.8     # Tiempo mínimo entre videos (segundos)
MAX_VIDEO_DELAY = 2.8     # Tiempo máximo entre videos (segundos)

MODE_REPOSTS = "reposts"
MODE_FAVORITES = "favorites"


def print_banner():
    print("=" * 76)
    print("       ⚡ TIKTOK AUTO CLEANER PRO - MODO TERMINAL + SEGUNDO PLANO ⚡")
    print("=" * 76)
    print("  Eliminador inteligente de COMPARTIDOS (Reposts) y GUARDADOS (Favoritos)")
    print("  Conserva tu sesión activa en Chrome y opera en segundo plano.")
    print("=" * 76)
    print()


def show_main_menu():
    print("-" * 76)
    print("  MENÚ PRINCIPAL - ¿Qué deseas limpiar hoy?")
    print("-" * 76)
    print("    [1] 🟡 Eliminar publicaciones COMPARTIDAS (Reposts)")
    print("    [2] 🔖 Eliminar videos GUARDADOS (Favoritos / Bookmarks)")
    print("    [3] 🚀 Limpieza DÚO (Primero Compartidos y luego Guardados)")
    print("    [0] ❌ Salir")
    print("-" * 76)
    while True:
        choice = input(">> Selecciona una opción (1, 2, 3 o 0): ").strip()
        if choice in ("1", "2", "3", "0"):
            return choice
        print("  [!] Opción inválida. Ingresa 1, 2, 3 o 0.")


def is_port_open(port):
    """Comprueba si ya hay un navegador Chrome escuchando en el puerto de depuración."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.8)
        return s.connect_ex(("127.0.0.1", port)) == 0


def find_chrome_executable():
    """Localiza el ejecutable de Google Chrome en Windows."""
    candidates = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
        os.path.expandvars(r"%PROGRAMFILES%\Google\Chrome\Application\chrome.exe"),
    ]
    for path in candidates:
        if os.path.exists(path):
            return path
    return "chrome.exe"


def connect_or_launch_chrome():
    """
    Se conecta a una ventana de Chrome ya abierta (puerto 9222).
    Si no existe ninguna con el puerto activo, abre una ventana persistente
    con el perfil local 'chrome_session' y flags anti-bloqueo de fondo.
    """
    if is_port_open(DEBUG_PORT):
        print(f"[+] ¡Navegador detectado en puerto {DEBUG_PORT}! Conectando a tu sesión activa...")
    else:
        print("[+] Abriendo ventana de Chrome persistente para TikTok...")
        script_dir = os.path.dirname(os.path.abspath(__file__))
        profile_dir = os.path.join(script_dir, "chrome_session")
        os.makedirs(profile_dir, exist_ok=True)
        chrome_exe = find_chrome_executable()

        cmd = [
            chrome_exe,
            f"--remote-debugging-port={DEBUG_PORT}",
            f"--user-data-dir={profile_dir}",
            "--start-maximized",
            # Flags críticos para funcionamiento en SEGUNDO PLANO (sin pausar timers)
            "--disable-background-timer-throttling",
            "--disable-backgrounding-occluded-windows",
            "--disable-renderer-backgrounding",
            "--disable-features=CalculateNativeWinOcclusion,IntensiveWakeUpThrottling",
            "--disable-blink-features=AutomationControlled",
            TIKTOK_URL,
        ]
        subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        # Esperar a que el puerto esté disponible
        for _ in range(30):
            if is_port_open(DEBUG_PORT):
                break
            time.sleep(0.3)

    options = webdriver.ChromeOptions()
    options.add_experimental_option("debuggerAddress", f"127.0.0.1:{DEBUG_PORT}")
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    return driver


def inject_background_keepalive(driver):
    """
    Inyecta scripts para que TikTok Web considere la pestaña como siempre activa y visible.
    """
    js_keepalive = """
    try {
        Object.defineProperty(document, 'hidden', { get: () => false, configurable: true });
        Object.defineProperty(document, 'visibilityState', { get: () => 'visible', configurable: true });
        window.dispatchEvent(new Event('visibilitychange'));
    } catch (e) {}
    """
    try:
        driver.execute_script(js_keepalive)
    except Exception:
        pass


def scan_and_verify_ready(driver, mode):
    """
    Escanea pestañas de Chrome, verifica TikTok y si hay un video abierto listo para limpiar.
    """
    mode_name = "COMPARTIDOS (Reposts)" if mode == MODE_REPOSTS else "GUARDADOS (Favoritos)"
    tab_hint = "Compartidos (Reposts)" if mode == MODE_REPOSTS else "Guardados / Favoritos"

    while True:
        print("\n" + "-" * 76)
        print(f"  🔍 ESCANEANDO PESTAÑAS PARA MODO: {mode_name}...")
        print("-" * 76)

        tiktok_handle = None
        best_status = None

        try:
            handles = driver.window_handles
        except Exception:
            print("  [!] La ventana de Chrome se desconectó. Intentando reconectar...")
            try:
                driver = connect_or_launch_chrome()
                handles = driver.window_handles
            except Exception as e2:
                print(f"  [✘] Error al reconectar: {e2}")
                return False

        for handle in handles:
            try:
                driver.switch_to.window(handle)
                url = driver.current_url or ""
                if "tiktok.com" in url.lower():
                    status = driver.execute_script("""
                    return (function() {
                        const url = window.location.href;
                        const bodyText = document.body ? document.body.innerText : '';
                        const is403 = bodyText.includes('HTTP ERROR 403') || bodyText.includes('Se ha denegado el acceso');

                        const arrowBtn = document.querySelector(
                            'button[data-e2e="arrow-right"], button[data-e2e="arrow-down"], button[data-e2e="nav-arrow-down"]'
                        );
                        const videoContainer = document.querySelector(
                            '[data-e2e="browse-video"], [data-e2e="detail-video"], video'
                        );
                        const hasUrlVideo = url.includes('/video/') || url.includes('/photo/');
                        const hasArrowVisible = !!(arrowBtn && arrowBtn.getBoundingClientRect().width > 0);
                        const hasVideoVisible = !!(videoContainer && videoContainer.getBoundingClientRect().width > 0);

                        return {
                            url: url,
                            is403: is403,
                            inVideoMode: hasArrowVisible || (hasUrlVideo && hasVideoVisible)
                        };
                    })();
                    """)
                    tiktok_handle = handle
                    best_status = status
                    if status.get("inVideoMode"):
                        break
            except Exception:
                continue

        if not tiktok_handle or not best_status:
            print("  [✘] No se encontró ninguna pestaña con TikTok abierto.")
            print(f"  👉 Abre https://www.tiktok.com, ve a tu Perfil -> {tab_hint}")
            print("     abre el PRIMER video y presiona [ENTER].")
        else:
            driver.switch_to.window(tiktok_handle)
            inject_background_keepalive(driver)

            url_short = best_status["url"][:65] + ("..." if len(best_status["url"]) > 65 else "")
            print(f"  [✔] Pestaña de TikTok detectada: {url_short}")

            if best_status.get("is403"):
                print("  [✘] TikTok muestra bloqueo HTTP 403. Espera 1-2 minutos y recarga la página.")
            elif best_status.get("inVideoMode"):
                print(f"  [✔] Video en modo detalle y controles detectados para {mode_name}.")
                print("  [✔] Protección de segundo plano inyectada.")
                print("-" * 76)
                print(f"  [🚀] ¡Todo listo! Iniciando limpieza de {mode_name} en 2 segundos...\n")
                time.sleep(2.0)
                return True
            else:
                print(f"  [✘] Estás en TikTok, pero NO has abierto ningún video de {tab_hint}.")
                print("-" * 76)
                print("  👉 PASOS REQUERIDOS:")
                print(f"     1. Ve a tu Perfil -> Pestaña '{tab_hint}'.")
                if mode == MODE_REPOSTS:
                    print("        (Tip: Si no ves la pestaña Compartidos, comparte un video cualquiera y aparecerá).")
                print("     2. Haz clic sobre el PRIMER video para abrirlo en grande.")
                print("     3. Presiona [ENTER] aquí para continuar.")

        print()
        user_in = input(">> Presiona [ENTER] para re-escanear (o escribe 'q' y presiona ENTER para volver al menú): ").strip().lower()
        if user_in == 'q':
            return False


# ==============================================================================
# DETECCIÓN DE BOTONES: REPOSTS (COMPARTIDOS) Y FAVORITES (GUARDADOS)
# ==============================================================================

def find_active_target_button(driver, mode):
    """
    Localiza el botón de acción correspondiente según el modo seleccionado:
    - MODE_REPOSTS: botón amarillo de 'Remove repost' / 'Eliminar publicación compartida'.
    - MODE_FAVORITES: botón amarillo/dorado de 'Eliminar de favoritos' / 'Guardado'.
    Retorna el elemento Web si está ACTIVO (listo para ser desmarcado), o None.
    """
    if mode == MODE_REPOSTS:
        js_find = """
        return (function() {
            const candidates = document.querySelectorAll(
                '#icon-element-repost, [data-e2e="video-share-repost"], [aria-label]'
            );
            for (const el of candidates) {
                const label = ((el.getAttribute('aria-label') || '') + ' ' + (el.getAttribute('title') || '')).toLowerCase().trim();
                if (
                    label.includes('remove repost') ||
                    label.includes('eliminar la publicación compartida') ||
                    label.includes('eliminar la publicacion compartida') ||
                    label.includes('eliminar publicación compartida') ||
                    label.includes('quitar compartido')
                ) {
                    const rect = el.getBoundingClientRect();
                    if (rect.width > 0 && rect.height > 0) {
                        return el.closest('button, [role="button"]') || el;
                    }
                }
            }
            return null;
        })();
        """
    else:  # MODE_FAVORITES
        js_find = """
        return (function() {
            function isYellowColor(str) {
                if (!str) return false;
                if (/#(face15|f5c344|ffcc00|ffd700|eab308|facc15|f7b500|ffbe00|e6a800|d97706)/i.test(str)) return true;
                const m = str.match(/rgba?\\((\\d+),\\s*(\\d+),\\s*(\\d+)/i);
                if (m) {
                    const r = parseInt(m[1], 10);
                    const g = parseInt(m[2], 10);
                    const b = parseInt(m[3], 10);
                    if (r > 190 && g > 140 && b < 100) return true;
                }
                return false;
            }

            const selectors = [
                'button[data-e2e="browse-favorite-icon"]',
                'button[data-e2e="favorite-icon"]',
                'button[data-e2e="undefined-icon"]',
                '[data-e2e="video-share-favorite"]',
                'span[data-e2e="browse-favorite-icon"]',
                'span[data-e2e="undefined-icon"]',
                'button[aria-label*="favorit" i]',
                'button[aria-label*="guardad" i]',
                'button[aria-label*="bookmark" i]'
            ];

            const candidates = document.querySelectorAll(selectors.join(', '));
            for (const item of candidates) {
                const btn = item.closest('button, [role="button"]') || item;
                if (btn.closest('[data-e2e="comment-list"], [class*="CommentList"], [class*="comment-list"]')) {
                    continue;
                }
                const rect = btn.getBoundingClientRect();
                if (rect.width === 0 || rect.height === 0) continue;

                const label = ((btn.getAttribute('aria-label') || '') + ' ' + (btn.getAttribute('title') || '')).toLowerCase();

                const isRemoveLabel = (
                    label.includes('eliminar de favoritos') ||
                    label.includes('quitar de favoritos') ||
                    label.includes('eliminar de los favoritos') ||
                    label.includes('quitar de los favoritos') ||
                    label.includes('remove from favorites') ||
                    label.includes('remove favorite') ||
                    label.includes('unsave') ||
                    label.includes('added to favorites') ||
                    label.includes('guardado en favoritos')
                );

                const isPressed = btn.getAttribute('aria-pressed') === 'true' || btn.getAttribute('data-active') === 'true';

                let hasYellow = false;
                const style = window.getComputedStyle(btn);
                if (isYellowColor(style.color) || isYellowColor(style.fill) || isYellowColor(style.backgroundColor)) {
                    hasYellow = true;
                }
                const svgs = btn.querySelectorAll('svg, path, circle');
                for (const svg of svgs) {
                    const s = window.getComputedStyle(svg);
                    const fill = svg.getAttribute('fill') || s.fill || '';
                    const stroke = svg.getAttribute('stroke') || s.stroke || '';
                    const col = s.color || '';
                    if (isYellowColor(fill) || isYellowColor(stroke) || isYellowColor(col)) {
                        hasYellow = true;
                        break;
                    }
                }

                if (isRemoveLabel || isPressed || hasYellow) {
                    return btn;
                }
            }

            // Respaldo secundario por texto aria-label explícito
            const allBtns = document.querySelectorAll('button, [role="button"]');
            for (const b of allBtns) {
                if (b.closest('[data-e2e="comment-list"], [class*="CommentList"]')) continue;
                const l = ((b.getAttribute('aria-label') || '') + ' ' + (b.getAttribute('title') || '')).toLowerCase();
                if (
                    l.includes('eliminar de favoritos') ||
                    l.includes('quitar de favoritos') ||
                    l.includes('remove from favorites') ||
                    l.includes('guardado en favoritos') ||
                    l.includes('added to favorites')
                ) {
                    const r = b.getBoundingClientRect();
                    if (r.width > 0 && r.height > 0) return b;
                }
            }

            return null;
        })();
        """

    try:
        return driver.execute_script(js_find)
    except Exception:
        return None


def physical_click(driver, element):
    """
    Realiza un clic físico seguro sobre el botón de acción.
    """
    try:
        actions = ActionChains(driver)
        actions.move_to_element(element).pause(0.12).click().perform()
        return True
    except Exception:
        pass

    try:
        driver.execute_script("""
            const el = arguments[0];
            const rect = el.getBoundingClientRect();
            const x = rect.left + rect.width / 2;
            const y = rect.top + rect.height / 2;
            const opts = { bubbles: true, cancelable: true, view: window, clientX: x, clientY: y };
            el.dispatchEvent(new PointerEvent('pointerdown', opts));
            el.dispatchEvent(new MouseEvent('mousedown', opts));
            el.dispatchEvent(new PointerEvent('pointerup', opts));
            el.dispatchEvent(new MouseEvent('mouseup', opts));
            el.dispatchEvent(new MouseEvent('click', opts));
        """, element)
        return True
    except Exception as e:
        print(f"Error en clic: {e}")
        return False


def go_to_next_video(driver):
    """
    Avanza al siguiente video mediante la flecha abajo o tecla Down Arrow.
    """
    prev_url = driver.current_url

    js_find_down_arrow = """
    return (function() {
        const selectors = [
            'button[data-e2e="arrow-right"]',
            'button[data-e2e="arrow-down"]',
            'button[data-e2e="nav-arrow-down"]',
            'button[aria-label*="siguiente" i]',
            'button[aria-label*="next" i]'
        ];
        for (const s of selectors) {
            const btn = document.querySelector(s);
            if (btn && btn.getBoundingClientRect().width > 0 && !btn.disabled) {
                return btn;
            }
        }
        return null;
    })();
    """
    try:
        down_btn = driver.execute_script(js_find_down_arrow)
        if down_btn:
            try:
                ActionChains(driver).move_to_element(down_btn).pause(0.05).click().perform()
            except Exception:
                driver.execute_script("arguments[0].click();", down_btn)
            time.sleep(0.5)
            if driver.current_url != prev_url:
                return True
    except Exception:
        pass

    try:
        ActionChains(driver).send_keys(Keys.ARROW_DOWN).perform()
        time.sleep(0.5)
        if driver.current_url != prev_url:
            return True
    except Exception:
        pass

    return driver.current_url != prev_url


def check_keyboard_command():
    """
    Comprueba si el usuario presionó [P], [R] o [Q] en la consola sin bloquear.
    """
    if msvcrt.kbhit():
        key = msvcrt.getch().decode('utf-8', errors='ignore').lower()
        return key
    return None


def wait_in_pause_menu(driver, mode):
    """
    Menú interactivo de pausa en terminal.
    """
    print("\n" + "-" * 76)
    print("  ⏸  BOT EN PAUSA (Tu ventana de Chrome sigue abierta)")
    print("     -> Puedes acomodar el video en Chrome, recargar (F5) o descansar.")
    print("     -> Presiona [P] para REANUDAR, [R] para RE-ESCANEAR, o [Q] para SALIR.")
    print("-" * 76)

    while True:
        cmd = check_keyboard_command()
        if cmd == 'p':
            print("\n[▶] Reanudando ejecución...\n")
            inject_background_keepalive(driver)
            return 'resume'
        elif cmd == 'r':
            print("\n[🔄] Re-escaneando pestaña...\n")
            if scan_and_verify_ready(driver, mode):
                return 'restart'
            return 'quit'
        elif cmd == 'q':
            return 'quit'
        time.sleep(0.1)


def run_cooldown(driver, mode, seconds, reason="Lote completado"):
    """
    Pausa de enfriamiento anti-rate limit con cuenta regresiva en vivo.
    """
    print(f"\n[❄️] {reason}: Pausa de enfriamiento anti-rate limit ({seconds}s)...")
    print("    Permite que los servidores de TikTok recarguen tu cuota en segundo plano.")
    for remaining in range(seconds, 0, -1):
        cmd = check_keyboard_command()
        if cmd == 'q':
            return 'quit'
        elif cmd == 'p':
            action = wait_in_pause_menu(driver, mode)
            if action == 'quit':
                return 'quit'
            break
        elif cmd == 'r':
            if scan_and_verify_ready(driver, mode):
                return 'restart'
            return 'quit'
        print(f"\r    ⏳ Reanudando en {remaining}s... (Toca [P] pausar, [Q] salir)   ", end="", flush=True)
        time.sleep(1)
    print("\r[▶] ¡Enfriamiento completado! Continuando con el proceso...               \n")
    return 'ok'


# ==============================================================================
# BUCLE PRINCIPAL DE LIMPIEZA
# ==============================================================================

def run_cleaning_session(driver, mode):
    """
    Ejecuta una sesión completa de limpieza para el modo especificado.
    """
    mode_title = "COMPARTIDOS (Reposts)" if mode == MODE_REPOSTS else "GUARDADOS (Favoritos)"
    btn_name = "botón amarillo de Repost" if mode == MODE_REPOSTS else "botón dorado de Guardado"

    if not scan_and_verify_ready(driver, mode):
        print(f"\n[⏹] Sesión cancelada para {mode_title}.")
        return 0, 0

    print("=" * 76)
    print(f"  INICIANDO LIMPIEZA DE: {mode_title}")
    print("=" * 76)
    print(f"  [+] Ritmo de trabajo: {MIN_VIDEO_DELAY}s a {MAX_VIDEO_DELAY}s por video.")
    print(f"  [+] Pausa anti-bloqueo: cada {BATCH_SIZE} eliminados descansa {COOLDOWN_SECONDS}s.")
    print("  [+] Comandos en vivo: [P] Pausar | [R] Re-escanear | [Q] Salir")
    print("=" * 76 + "\n")

    deleted_count = 0
    skipped_count = 0
    video_index = 0
    consecutive_fails = 0

    while True:
        # 1. Comandos de teclado en vivo
        cmd = check_keyboard_command()
        if cmd == 'p':
            action = wait_in_pause_menu(driver, mode)
            if action == 'quit':
                break
            elif action == 'restart':
                video_index = 0
                continue
        elif cmd == 'r':
            print(f"\n[🔄] Re-escaneando pestaña para {mode_title}...\n")
            if not scan_and_verify_ready(driver, mode):
                break
            continue
        elif cmd == 'q':
            print("\n[⏹] Comando [Q] detectado. Deteniendo este modo...")
            break

        inject_background_keepalive(driver)
        video_index += 1
        print(f"[#{video_index}] Buscando {btn_name}...", end=" ", flush=True)

        # 2. Localizar el botón activo
        target_btn = None
        for _ in range(14):
            target_btn = find_active_target_button(driver, mode)
            if target_btn:
                break
            time.sleep(0.1)

        if target_btn:
            physical_click(driver, target_btn)
            time.sleep(0.75)  # Esperar respuesta de TikTok

            # Verificar si se desmarcó
            still_active = find_active_target_button(driver, mode)
            if not still_active:
                deleted_count += 1
                consecutive_fails = 0
                tag = "🟡 COMPARTIDO RETIRADO" if mode == MODE_REPOSTS else "🔖 GUARDADO RETIRADO"
                print(f"-> {tag} ¡Éxito! (Total: {deleted_count})")

                if deleted_count % BATCH_SIZE == 0:
                    res = run_cooldown(driver, mode, COOLDOWN_SECONDS, f"Lote de {deleted_count} completado")
                    if res == 'quit':
                        break
            else:
                consecutive_fails += 1
                print("-> ⚠️ No se desmarcó (posible lag o rechazo de TikTok). Avanzando...")
                if consecutive_fails >= 3:
                    print("\n[⚠️] 3 rechazos consecutivos detectados (Rate Limit temporal preventivo).")
                    res = run_cooldown(driver, mode, 45, "Pausa de seguridad por Rate Limit")
                    if res == 'quit':
                        break
                    consecutive_fails = 0
        else:
            skipped_count += 1
            print("-> ⏭️ Ya retirado o no activo (Omitido)")

        # Comprobar comandos antes de avanzar
        cmd = check_keyboard_command()
        if cmd in ('p', 'r', 'q'):
            if cmd == 'p':
                action = wait_in_pause_menu(driver, mode)
                if action == 'quit':
                    break
                continue
            elif cmd == 'r':
                if not scan_and_verify_ready(driver, mode):
                    break
                continue
            elif cmd == 'q':
                break

        # 3. Avanzar al siguiente video
        moved = go_to_next_video(driver)
        if not moved:
            time.sleep(0.6)
            moved = go_to_next_video(driver)
            if not moved:
                print(f"\n[!] Fin de la lista cargada o no se pudo avanzar.")
                print(f"    Entrando en pausa (tu navegador permanece abierto).")
                print(f"    -> Recarga (F5), abre el siguiente video y pulsa [P] o [R].")
                action = wait_in_pause_menu(driver, mode)
                if action == 'quit':
                    break
                continue

        delay = random.uniform(MIN_VIDEO_DELAY, MAX_VIDEO_DELAY)
        time.sleep(delay)

    print("\n" + "-" * 76)
    print(f"  🏁 RESUMEN {mode_title}:")
    print(f"     - Eliminados con éxito: {deleted_count}")
    print(f"     - Omitidos / Ya quitados: {skipped_count}")
    print("-" * 76)
    return deleted_count, skipped_count


def main():
    print_banner()
    driver = None
    try:
        driver = connect_or_launch_chrome()

        while True:
            choice = show_main_menu()
            if choice == "0":
                print("\n[👋] ¡Hasta luego! Tu navegador Chrome permanece abierto con tu sesión intacta.")
                break

            elif choice == "1":
                run_cleaning_session(driver, MODE_REPOSTS)

            elif choice == "2":
                run_cleaning_session(driver, MODE_FAVORITES)

            elif choice == "3":
                print("\n" + "=" * 76)
                print("  🚀 MODO LIMPIEZA DÚO: FASE 1 -> COMPARTIDOS")
                print("=" * 76)
                run_cleaning_session(driver, MODE_REPOSTS)

                print("\n" + "=" * 76)
                print("  🚀 MODO LIMPIEZA DÚO: FASE 2 -> GUARDADOS (Favoritos)")
                print("=" * 76)
                print("  👉 Por favor, ve a tu Perfil -> Pestaña 'Guardados' (Favoritos)")
                print("     y abre el primer video.")
                input(">> Presiona [ENTER] cuando tengas el video listo... ")
                run_cleaning_session(driver, MODE_FAVORITES)

            print()
            user_again = input(">> ¿Deseas volver al menú principal? (s/n): ").strip().lower()
            if user_again != 's':
                print("\n[👋] Finalizado. Tu sesión de Chrome permanece activa.")
                break

    except KeyboardInterrupt:
        print("\n\n[!] Detenido por el usuario (Ctrl + C). Tu Chrome sigue abierto.")
    except Exception as e:
        print(f"\n[!] Error imprevisto: {e}")


if __name__ == "__main__":
    main()
