import filecmp
import serial
import os
import time
import sys

BLOCKSIZE = 1024

def dump(s, port):
    print("------------------------------------------")
    print(" OPEN SERIAL: {}".format(port.upper()))
    ser = serial.Serial(port, baudrate=115200, timeout=3)
    print(" -ESPERA...")
    time.sleep(2)
    ser.write(bytes([0x00]))
    size = 0
    start_time = time.time()
    while size == 0:
        resp = ser.read(1)
        if resp == b"\xEE":
            print("{0:60}".format(" -EL CHIP NO RESPONDE, COMPRUEBE LAS CONEXIONES Y PRESIONA EL BOTÓN DE RESET"), end='\r')
            sys.stdout.flush()
        if resp == b"\x00":
            print("{0:60}".format(" -[GLITCH]"), end='\r')
            sys.stdout.flush()
        if resp == b"\x91":
            print("{0:60}".format(" -OCD CONNECT CMD"))
            while True:
                resp = ser.read(1)
                if resp == b"\x94":
                    print(" -OCD EXEC CMD")
                    print(" -DUMP TO: {}".format(s))
                    with open(s, 'wb'):
                        pass
                    size = BLOCKSIZE
                    counter = 0
                    ser.read(1)
                    break
    while True:
        data = ser.read(size)
        counter += size
        size = BLOCKSIZE
        with open(s, 'ab') as f:
            data = str(data)
            f.write(data.encode())
        print("\033[32m -Dump: {}/512KB \033[37m".format(os.stat(s).st_size / 1023), end='\r')
        sys.stdout.flush()
        if counter >= (BLOCKSIZE * 512):
            print("\n\r Hecho. Tiempo transcurrido: {:0.4f} segundos".format(time.time() - start_time))
            ser.close()
            time.sleep(1)
            break

def main():
    os.system('cls' if os.name == 'nt' else 'clear')
    print("------------------------------------------")
    print("\033[37m SYSCON READER V2.2 BY DARKNESMONK")
    
    port = input("Por favor, ingrese el puerto COM (ejemplo: com3): ")
    
    if not port.startswith("com"):
        print("El formato del puerto COM no es válido. Debe comenzar con 'com' (ejemplo: com3).")
        return
    
    f = ["syscon1.bin", "syscon2.bin"]
    for val in f:
        dump(val, port)
    comp = filecmp.cmp(f[0], f[1])
    print("------------------------------------------")
    print(" COMPARAR ARCHIVOS:")
    if comp:
        print("\033[32m ALL RIGHT!")
    else:
        print("\033[31m ¡¡¡PELIGRO!!! los archivos no son identicos")
    print("\33[37m EXIT")

if __name__ == '__main__':
    main()
