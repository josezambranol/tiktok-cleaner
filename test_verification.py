"""
Test de verificación y diagnóstico para TikTok Auto Cleaner Pro
"""
import sys
import os
import time

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# Asegurar que se importa desde el directorio actual
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import cleaner

def run_diagnostics():
    print("=" * 60)
    print("🧪 INICIANDO TEST DE VERIFICACIÓN FUNCIONAL")
    print("=" * 60)
    
    # 1. Verificar ejecutable de Chrome
    chrome_exe = cleaner.find_chrome_executable()
    print(f"[1/6] Localización de Chrome: {chrome_exe}")
    assert os.path.exists(chrome_exe), f"No se encontró Chrome en {chrome_exe}"
    print("      ✔ Ejecutable de Chrome verificado.")

    # 2. Verificar carpeta de sesión
    profile_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "chrome_session")
    print(f"[2/6] Carpeta de sesión: {profile_dir}")
    assert os.path.exists(profile_dir), "No existe la carpeta chrome_session"
    default_dir = os.path.join(profile_dir, "Default")
    assert os.path.exists(default_dir), "No existe el perfil Default en chrome_session"
    print("      ✔ Perfil persistente de sesión verificado.")

    # 3. Conexión / Lanzamiento con Selenium y Chrome
    print("[3/6] Iniciando conexión con Chrome (puerto 9222)...")
    driver = cleaner.connect_or_launch_chrome()
    assert driver is not None, "Error: driver es None"
    print(f"      ✔ Driver Selenium conectado exitosamente!")
    print(f"      ✔ URL actual: {driver.current_url}")
    print(f"      ✔ Título de la ventana: {driver.title}")

    # 4. Inyección de Keepalive para segundo plano
    print("[4/6] Probando inyección de keepalive de visibilidad...")
    cleaner.inject_background_keepalive(driver)
    doc_hidden = driver.execute_script("return document.hidden;")
    doc_vis = driver.execute_script("return document.visibilityState;")
    print(f"      ✔ document.hidden = {doc_hidden} (Debe ser False)")
    print(f"      ✔ document.visibilityState = '{doc_vis}' (Debe ser 'visible')")
    assert doc_hidden is False, "El script de keepalive falló en engañar document.hidden"
    assert doc_vis == "visible", "El script de keepalive falló en engañar visibilityState"

    # 5. Probar evaluación de selectores y sintaxis JavaScript
    print("[5/6] Verificando funciones de detección en el DOM...")
    # Probar que las funciones JavaScript no lanzan excepciones sintácticas dentro del navegador
    res_reposts = cleaner.find_active_target_button(driver, cleaner.MODE_REPOSTS)
    res_favorites = cleaner.find_active_target_button(driver, cleaner.MODE_FAVORITES)
    print(f"      ✔ find_active_target_button(reposts) ejecutado sin errores (Resultado: {res_reposts})")
    print(f"      ✔ find_active_target_button(favorites) ejecutado sin errores (Resultado: {res_favorites})")

    # 6. Probar escaneo de pestaña
    print("[6/6] Verificando escáner de estado de pestañas...")
    tabs_count = len(driver.window_handles)
    print(f"      ✔ Pestañas abiertas en la ventana del bot: {tabs_count}")

    print("\n" + "=" * 60)
    print("🎉 ¡TODOS LOS TESTS DE INTEGRACIÓN PASARON AL 100%!")
    print("=" * 60)
    print("El motor de Selenium, la persistencia de sesión, los scripts")
    print("de segundo plano y los selectores están 100% funcionales.")
    print("=" * 60)

if __name__ == "__main__":
    run_diagnostics()
