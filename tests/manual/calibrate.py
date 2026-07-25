import time

from app.hardware.servo_pico import PicoController


def test_direction():
    print("--- КАЛІБРУВАННЯ НАПРЯМКУ ---")
    pico = PicoController()
    
    # 1. Центр
    print("1. Ставлю в ЦЕНТР (90, 90)...")
    pico.send_cmd(90, 90)
    time.sleep(2)
    
    # 2. Тест PAN (Горизонталь)
    print("2. Повертаю PAN на 120 (збільшую кут)...")
    pico.send_cmd(120, 90)
    print(">>> ПОДИВИСЬ НА РОБОТА <<<")
    print("Куди повернулась камера (об'єктив)?")
    print("Варіант А: ВЛІВО (відносно корпусу робота)")
    print("Варіант Б: ВПРАВО (відносно корпусу робота)")
    
    time.sleep(3)
    
    # 3. Тест TILT (Вертикаль)
    print("3. Повертаю TILT на 120 (збільшую кут)...")
    pico.send_cmd(90, 120)
    print(">>> ПОДИВИСЬ НА РОБОТА <<<")
    print("Куди подивилась камера?")
    print("Варіант А: ВНИЗ (в підлогу)")
    print("Варіант Б: ВВЕРХ (в стелю)")

    pico.close()

if __name__ == "__main__":
    test_direction()