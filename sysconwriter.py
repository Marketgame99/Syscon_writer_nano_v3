import serial
import os
import sys
import time
import argparse
import colorama
import serial.tools.list_ports

BLOCKSIZE = 1024
colorama.init()

DARKNESMONK = '''
  _________                                __      __        .__  __                
 /   _____/__.__. ______ ____  ____   ____/  \\    /  \\_______|__|/  |_  ___________ 
 \\_____  <   |  |/  ___// ___\\/  _ \\ /    \\   \\/\\/   /\\_  __ \\  \\   __\\/ __ \\_  __ \\
 /        \\___  |\\____ \\\\ \\__(  <_> )   |  \\        /  |  | \\/  ||  | \\  ___/|  | \\/
/_______  / ____/____  >\\___  >____/|___|  /\\__/\\  /   |__|  |__||__|  \\___  >__|   
        \\/\\/         \\/     \\/           \\/      \\/                        \\/     v1.7  
by DARKNESMONK
'''

def checksum(data):
    csum = 0
    for d in data:
        csum += d
        csum &= 255

    csum -= 1
    csum &= 255
    return csum

def write(port, file, full, rew_ocd, confirm):
    if rew_ocd:
        input('\x1b[31m\nWarning: OCD Flag (0x85) Will Be Written. Please Confirm... \x1b[37m')
    print('\n==============================================================\n')
    print ('Opening Serial Port: {}'.format(port))
    try:
        ser = serial.Serial(port, baudrate=115200, timeout=5)
    except serial.serialutil.SerialException as e:
        print('\nError: Unable to open serial port')
        print('\x1b[0m\nPress Enter to Exit...')
        input()
        sys.exit(1)

    seek = 0 if full else 393216
    end_seek = 524288 if full else 458752
    arg = 4 + (full << 1) + rew_ocd
    print('Waiting...')
    start_time = time.time()
    threshold = 120
    while 1:
        elapsed_time = time.time() - start_time
        if elapsed_time > threshold:
            print ('{0:60}'.format('\x1b[31m\nChip Timeout! Check Connections!\n'), '\r', end='')
            sys.stdout.flush()
            print('\x1b[0m\nPress Enter to Exit...')
            input()
            sys.exit(1)
        resp = ser.read(1)
        if resp == b'\xff':
            print('\n\x1b[33mConnected!')
            time.sleep(1)
            ser.write(bytes([arg]))
            continue
        if resp == b'\xee':
            print ('{0:60}'.format('\x1b[31m\nChip Unresponsive! Check Connections!\n'), '\r', end='')
            sys.stdout.flush()
            print('\x1b[0m\nPress Enter to Exit...')
            input()
            sys.exit(1)
        if resp == b'\xf3' or resp == b'\xf4':
            print('\x1b[31mCannot Unlock OCD! Potential Brick!')
            return 0
        if resp == b'\xf2':
            print('\n\x1b[32mOCD Unlocked!')
        if resp == b'U':
            print('\x1b[32mOCD Programming Started...\n')
        if resp == b'\x00':
            print('\n\x1b[32mChip Glitching!\n', '\r', end='')
            sys.stdout.flush()
        if resp == b'\x10':
            try:
                f = open(file, 'rb')
                f.seek(seek)
                counter = seek
            except IOError as e:
                print ('{0:60}'.format('\x1b[31m\nCannot Open File!\n'), '\r', end='')
                sys.stdout.flush()
                print('\x1b[0m\nPress Enter to Exit...')
                input()
                sys.exit(1)

            input('\x1b[31mWrite Process Will Begin. Please Confirm...')
            start_time = time.time()
            print(('\n\x1b[0mOpening File: {}\n\r\nErasing Blocks...\x1b[31m\n\nDo Not Touch Chip or Reader!\x1b[37m \n\r').format(file))
            print('==============================================================\n')
            while 1:
                counter += 512
                data = bytearray(f.read(512))
                c = checksum(data)
                data.append(c)
                while 1:
                    resp = ser.read(1)
                    if resp != b'\x01':
                        continue
                    ser.write(data)
                    resp = bytearray(ser.read(3))
                    if resp[2] == 17:
                        print (' {}Writing Offset: 0x{:06X}, Write Code: 0x{:02X}, Resp Code: 0x{:02X} \x1b[37m'.format('\x1b[32m' if resp[1] == 0 else '\x1b[31m', counter - 1, resp[0], resp[1]))
                        break
                    else:
                        print ('\x1b[31mError @ Offset: 0x{:06X}, Write Code: 0x{:02X}, Resp Code: 0x{:02X} \x1b[37m'.format(counter - 1, resp[0], resp[1]))

                if counter >= end_seek - 1:
                    print('')
                    print('\x1b[37mDone!')
                    break

            print(('\nElapsed time: {:0.4f} seconds').format(time.time() - start_time))
            if not confirm:
                print('\x1b[0m\nPress Enter to Exit...')
                input()
            ser.close()
            break

    if confirm:
        try:
            f = ['confirm.bin']
            for val in f:
                dump(val, port)

            with open(f[0], 'rb') as (file1):
                contents1 = file1.read()
            with open(file, 'rb') as (file2):
                contents2 = file2.read()
            comp = True
        except IOError as e:
            print ('{0:60}'.format('\x1b[31mCannot Compare File!\n'), '\r', end='')
            sys.stdout.flush()
            print('\x1b[0m\nPress Enter to Exit...')
            input()
            sys.exit(1)

        try:
            for i in range(len(contents1)):
                if i == 195:
                    continue
                if contents1[i] != contents2[i]:
                    comp = False
                    break

            print('==============================================================\n')
            print('Comparing Files (Except OCD Flag)....')
            if comp:
                print('\x1b[32m\nFiles Match!')
                print('\x1b[0m\nPress Enter to Exit...')
                input()
            else:
                print('\x1b[31m\nDanger! Files Do NOT Match!')
                print('\x1b[0m\nPress Enter to Exit...')
                input()
        except IndexError as e:
            print ('{0:60}'.format('\x1b[31mCannot Compare File!\n'), '\r', end='')
            sys.stdout.flush()
            print('\x1b[0m\nPress Enter to Exit...')
            input()
            sys.exit(1)

def dump(s, port):
    print('\n==============================================================\n')
    print('Verifying Successful Write....\n')
    print('Opening Serial Port: {}'.format(port))
    try:
        ser = serial.Serial(port, baudrate=115200, timeout=5)
    except serial.serialutil.SerialException as e:
        print('\nError: Unable to open serial port ' + port)
        print('\x1b[0m\nPress Enter to Exit...')
        input()
        sys.exit(1)

    print('Waiting...\n')
    time.sleep(2)
    ser.write(bytes([0]))
    size = 0
    start_time = time.time()
    threshold = 120
    while size == 0:
        elapsed_time = time.time() - start_time
        if elapsed_time > threshold:
            print ('{0:60}'.format('\x1b[31m\nChip Timeout! Check Connections!\n'), '\r', end='')
            sys.stdout.flush()
            print('\x1b[0m\nPress Enter to Exit...')
            input()
            sys.exit(1)
        resp = ser.read(1)
        if resp == b'\xee':
            print ('{0:60}'.format('\x1b[31m\nChip Unresponsive! Check Connections!\n'), '\r', end='')
            sys.stdout.flush()
            print('\x1b[0m\nPress Enter to Exit...')
            input()
            sys.exit(1)
        if resp == b'\x00':
            print ('{0:60}'.format('\x1b[33mGlitching...'), '\r', end='')
            sys.stdout.flush()
        if resp == b'\x91':
            print ('{0:60}'.format('\x1b[32mChip Responded 0x91 (OCD Connect CMD)'))
            while 1:
                resp = ser.read(1)
                if resp == b'\x94':
                    print('\x1b[32mChip Responded 0x94 (OCD EXEC CMD)\n')
                    print(('\x1b[0mSaving Dump As {}\n').format(s))
                    f = open(s, 'wb')
                    f.close()
                    size = BLOCKSIZE
                    counter = 0
                    ser.read(1)
                    break

    while 1:
        data = ser.read(size)
        counter += size
        size = BLOCKSIZE
        f = open(s, 'ab')
        data = str(data)
        f.write(data.encode('utf-8'))
        f.close()
        print (('\x1b[32mDumping: {}/512KB \x1b[37m').format(os.stat(s).st_size / 1023), '\r', end='')
        sys.stdout.flush()
        if counter >= BLOCKSIZE * 512:
            print ('\n\nDone!\n\nElapsed Time: {:0.4f} Seconds\n'.format(time.time() - start_time))
            ser.close()
            time.sleep(1)
            break

if __name__ == '__main__':
    os.system('cls' if os.name == 'nt' else 'clear')
    print(DARKNESMONK)
    ports = list(serial.tools.list_ports.comports())
    auto_ports = []
    for port in ports:
        if 'USB-SERIAL CH340' in port[1]:
            auto_ports.append(port[0])

    if auto_ports:
        if len(auto_ports) > 1:
            print("\x1b[33mMultiple Syscon Writers (Or CH340's) Found At " + (', ').join(auto_ports) + '\x1b[0m\n')
            port = input('Enter COM Port (Example COM4): ')
        else:
            print('\x1b[32mSyscon Writer Found At ' + auto_ports[0] + '\x1b[0m\n')
            port = auto_ports[0]
    else:
        port = input('Enter COM Port (Example COM4): ')
    if not port:
        print('\nError: No port specified. Exiting program.')
        print('\x1b[0m\nPress Enter to Exit...')
        input()
        sys.exit(1)
    file = input('Enter Syscon File Name (Example Syscon1.bin): ')
    if not file:
        print('\nError: No file specified. Exiting program.')
        print('\x1b[0m\nPress Enter to Exit...')
        input()
        sys.exit(1)
    full = input('Write Entire Chip Excluding Block 1? (y/n): ')
    if full.lower() == 'y':
        full = True
    else:
        full = False
    rew_ocd = input('Write Entire Chip Including Block 1 & Enable OCD (Unlock/Debug)? (y/n): ')
    if rew_ocd.lower() == 'y':
        rew_ocd = True
        full = True
    else:
        rew_ocd = False
    confirm = input('Confirm Dump After Writing? (y/n): ')
    if confirm == 'y':
        confirm = True
    else:
        confirm = False
    write(port, file, full, rew_ocd, confirm)
