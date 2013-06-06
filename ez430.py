#!/usr/bin/env python
# Program MSP430 chips using the spi-by-wire programming available from
# the EZ430-F2013
# http://focus.ti.com/docs/toolsw/folders/print/ez430-f2013.html
# Spy-bi-wire pinout:
#   Pin 1 = Vcc (3.6v)
#       2 = SBWTCK
#       3 = SBWTDIO
#       4 = GND
# See http://gitorious.org/fetproxy/pages/CommandSpecification for
# more details
# See also http://mspdebug.sourceforge.net/usb.html

import serial
import argparse

from ihex import IHex
from titxt import TITxt

class EZ430(object):
    '''Class to talk to the MSP430 over the Spy-by-wire interface using
    the ez430 development hardware.
    See also: http://gitorious.org/fetproxy/pages/CommandSpecification'''
    def __init__(self, tty, mvolts = 2700):
        self.tty = tty
        self.serial = None
        self.spy_bi_wire = True
        self.m_volts = mvolts

    def open(self):
        self.serial = serial.Serial(self.tty, 460800)
        self.serial.open()

        # Initialise the connection
        data = [ 0x01, 0x01 ]
        self.send(data)
        data = self.read()
        #print "init", map(lambda x : hex(ord(x)), data)

        # Configure to use Spy-bi-wire / 4-wire
        spy_by_wire = 0x00
        if self.spy_bi_wire: spy_by_wire = 0x01
        data = [ 0x05, 0x02, 0x02, 0x00, 0x08, 0x00, 0x00, 0x00, spy_by_wire,
          0x00, 0x00, 0x00 ]
        self.send(data)
        self.read()

        # Set the voltage
        data = [ 0x06, 0x02, 0x01, 0x00, self.m_volts & 0xff,
          (self.m_volts>>8) & 0xff, 0x00, 0x00 ]
        #print map(lambda x : hex(x), data)
        self.send(data)
        data = self.read()
        #print map(lambda x : hex(ord(x)), data)

    def send(self, data):
        print "Sending %s" % (data)
        FRAME_BOUNDRY = chr(0x7E)
        crc = self.crc16(data)

        # Send the frame to the MSP430
        self.serial.write(chr(len(data) + 4))
        self.serial.write(FRAME_BOUNDRY)
        for ch in data:
            self.serial.write(chr(ch))
        self.serial.write(chr(crc & 0xff))
        self.serial.write(chr((crc >> 8) & 0xff))
        self.serial.write(FRAME_BOUNDRY)

    def read(self):
        print "About to read"
        # Read the length of the data
        head = self.serial.read(2)
        len = ord(head[0]) | (ord(head[1]) << 8)

        # Read the length of the data
        data = self.serial.read(len - 2)

        # Read the CRC
        crc = self.serial.read(2)
        print "read",map(lambda x : hex(ord(x)), data),"crc",crc

        assert (ord(crc[1]) << 8) | ord(crc[0]) == self.crc16(data)
        return data

    def close(self):
        self.serial.close()
        self.serial = None

    def identify(self):
        U = 0x00
        data = [ 0x03, 0x02, 0x02, 0x00, 0x50, 0x00, 0x00, 0x00, U, 0x00,
          0x00, 0x00 ]
        self.send(data)
        data = self.read()
        error = ord(data[2]) << 8 | ord(data[3])
        #print map(lambda x : hex(ord(x)), data)
        if error == 0xff04:
            raise SystemError, "MSP430 device not found on Spi-by-wire bus"
        elif error != 0:
            raise SystemError, "MSP430 error: Unknown code: 0x%x" % (error)
        part = data[12:45]

        main_mem_start_addr = ord(data[44]) | ord(data[45]) << 8
        main_mem_end_addr = ord(data[74]) | ord(data[75]) << 8

        info_mem_start_addr = ord(data[46]) | ord(data[47]) << 8
        info_mem_end_addr = ord(data[72]) | ord(data[73]) << 8

        ram_end_addr = ord(data[48]) | ord(data[49]) << 8
        ram_start_addr = ord(data[51]) | ord(data[50]) << 8

        chip_type = data[10]

        vmax = ord(data[62]) | ord(data[63]) << 8
        vmin = ord(data[64]) | ord(data[65]) << 8

        print "\tPart:", part
        print '\tMain memory: 0x%x-0x%x' % (main_mem_start_addr, main_mem_end_addr)
        print '\tInfo memory: 0x%x-0x%x' % (info_mem_start_addr, info_mem_end_addr)
        print '\tRam: 0x%x-0x%x' % (ram_start_addr, ram_end_addr)
        print '\tChip Type:', hex(ord(chip_type))
        print '\tVoltage: %.3f-%.3f' % (vmin / 1000.0, vmax / 1000.0)
        #print map(lambda x : hex(ord(x)), data)

    def identify2(self):
        data = [0x28, 0x02, 0x03, 0x00, 0x00, 0x00, 0x00, 0x00,
                0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]
        self.send(data)
        data = self.read()
        # Doesn't seem to be lining up with the docs I've got

        #print "Identify2", map(lambda x : hex(ord(x)), data)

    def erase_flash_all(self):
        tt = 0x02
        al = 0x00
        ah = 0x10
        ml = 0x00
        mh = 0x01
        data = [ 0x0c, 0x02, 0x03, 0x00, tt, 0x00, 0x00, 0x00, al, ah, 0x00,
          0x00, ml, mh, 0x00, 0x00]
        self.send(data)
        data = self.read()
        #print map(lambda x: hex(ord(x)), data)

    def reset(self, failure = True):
        puc = 1 << 0
        rst = 1 << 1
        vcc = 1 << 2

        if failure:
            a = 1
        else:
            a = 0

        data = [0x07, 0x02, 0x03, 0x00,
                puc | rst | vcc, 0x00, 0x00, 0x00,
                a, 0x00, 0x00, 0x00,
                a, 0x00, 0x00, 0x00]
        self.send(data)
        data = self.read()
        #print map(lambda x: hex(ord(x)), data)

    def read_mem(self, addr, length):
        al = addr & 0xff
        ah = (addr >> 8) & 0xff
        ll = length & 0xff
        lh = (length >> 8) & 0xff
        data = [0x0d, 0x02, 0x02, 0x00, al, ah, 0x00, 0x00, ll, lh, 0x00, 0x00 ]
        self.send(data)
        data = self.read()

        length = ord(data[4]) | ord(data[5]) << 8
        mem = map(ord, data[8:])
        #assert len(mem) == length

        return mem

    def write_mem(self, segments):
        for addr in sorted(segments):
            length = len(segments[addr])
            al = addr & 0xff
            ah = (addr >> 8) & 0xff
            ll = length & 0xff
            lh = (length >> 8) & 0xff

            data = [ 0x0e, 0x04, 0x01, 0x00, al, ah, 0x00, 0x00, ll, lh, 0x00,
              0x00 ]
            data += segments[addr]
            self.send(data)
            data = self.read()
            #print "Wrote %d bytes @ %x" % (length, addr)
            #print map(lambda x: hex(ord(x)), data)

    def verify_mem(self, segments):
        for addr in sorted(segments):
            data = self.read_mem(addr, len(segments[addr]))
            if data != segments[addr]:
                return False
        return True

    def crc16(self, s):
        crcValue=0xffff
        crc16tab = [
            0x00000000,      0x00001189,      0x00002312,      0x0000329b,
            0x00004624,      0x000057ad,      0x00006536,      0x000074bf,
            0x00008c48,      0x00009dc1,      0x0000af5a,      0x0000bed3,
            0x0000ca6c,      0x0000dbe5,      0x0000e97e,      0x0000f8f7,
            0x00001081,      0x00000108,      0x00003393,      0x0000221a,
            0x000056a5,      0x0000472c,      0x000075b7,      0x0000643e,
            0x00009cc9,      0x00008d40,      0x0000bfdb,      0x0000ae52,
            0x0000daed,      0x0000cb64,      0x0000f9ff,      0x0000e876,
            0x00002102,      0x0000308b,      0x00000210,      0x00001399,
            0x00006726,      0x000076af,      0x00004434,      0x000055bd,
            0x0000ad4a,      0x0000bcc3,      0x00008e58,      0x00009fd1,
            0x0000eb6e,      0x0000fae7,      0x0000c87c,      0x0000d9f5,
            0x00003183,      0x0000200a,      0x00001291,      0x00000318,
            0x000077a7,      0x0000662e,      0x000054b5,      0x0000453c,
            0x0000bdcb,      0x0000ac42,      0x00009ed9,      0x00008f50,
            0x0000fbef,      0x0000ea66,      0x0000d8fd,      0x0000c974,
            0x00004204,      0x0000538d,      0x00006116,      0x0000709f,
            0x00000420,      0x000015a9,      0x00002732,      0x000036bb,
            0x0000ce4c,      0x0000dfc5,      0x0000ed5e,      0x0000fcd7,
            0x00008868,      0x000099e1,      0x0000ab7a,      0x0000baf3,
            0x00005285,      0x0000430c,      0x00007197,      0x0000601e,
            0x000014a1,      0x00000528,      0x000037b3,      0x0000263a,
            0x0000decd,      0x0000cf44,      0x0000fddf,      0x0000ec56,
            0x000098e9,      0x00008960,      0x0000bbfb,      0x0000aa72,
            0x00006306,      0x0000728f,      0x00004014,      0x0000519d,
            0x00002522,      0x000034ab,      0x00000630,      0x000017b9,
            0x0000ef4e,      0x0000fec7,      0x0000cc5c,      0x0000ddd5,
            0x0000a96a,      0x0000b8e3,      0x00008a78,      0x00009bf1,
            0x00007387,      0x0000620e,      0x00005095,      0x0000411c,
            0x000035a3,      0x0000242a,      0x000016b1,      0x00000738,
            0x0000ffcf,      0x0000ee46,      0x0000dcdd,      0x0000cd54,
            0x0000b9eb,      0x0000a862,      0x00009af9,      0x00008b70,
            0x00008408,      0x00009581,      0x0000a71a,      0x0000b693,
            0x0000c22c,      0x0000d3a5,      0x0000e13e,      0x0000f0b7,
            0x00000840,      0x000019c9,      0x00002b52,      0x00003adb,
            0x00004e64,      0x00005fed,      0x00006d76,      0x00007cff,
            0x00009489,      0x00008500,      0x0000b79b,      0x0000a612,
            0x0000d2ad,      0x0000c324,      0x0000f1bf,      0x0000e036,
            0x000018c1,      0x00000948,      0x00003bd3,      0x00002a5a,
            0x00005ee5,      0x00004f6c,      0x00007df7,      0x00006c7e,
            0x0000a50a,      0x0000b483,      0x00008618,      0x00009791,
            0x0000e32e,      0x0000f2a7,      0x0000c03c,      0x0000d1b5,
            0x00002942,      0x000038cb,      0x00000a50,      0x00001bd9,
            0x00006f66,      0x00007eef,      0x00004c74,      0x00005dfd,
            0x0000b58b,      0x0000a402,      0x00009699,      0x00008710,
            0x0000f3af,      0x0000e226,      0x0000d0bd,      0x0000c134,
            0x000039c3,      0x0000284a,      0x00001ad1,      0x00000b58,
            0x00007fe7,      0x00006e6e,      0x00005cf5,      0x00004d7c,
            0x0000c60c,      0x0000d785,      0x0000e51e,      0x0000f497,
            0x00008028,      0x000091a1,      0x0000a33a,      0x0000b2b3,
            0x00004a44,      0x00005bcd,      0x00006956,      0x000078df,
            0x00000c60,      0x00001de9,      0x00002f72,      0x00003efb,
            0x0000d68d,      0x0000c704,      0x0000f59f,      0x0000e416,
            0x000090a9,      0x00008120,      0x0000b3bb,      0x0000a232,
            0x00005ac5,      0x00004b4c,      0x000079d7,      0x0000685e,
            0x00001ce1,      0x00000d68,      0x00003ff3,      0x00002e7a,
            0x0000e70e,      0x0000f687,      0x0000c41c,      0x0000d595,
            0x0000a12a,      0x0000b0a3,      0x00008238,      0x000093b1,
            0x00006b46,      0x00007acf,      0x00004854,      0x000059dd,
            0x00002d62,      0x00003ceb,      0x00000e70,      0x00001ff9,
            0x0000f78f,      0x0000e606,      0x0000d49d,      0x0000c514,
            0x0000b1ab,      0x0000a022,      0x000092b9,      0x00008330,
            0x00007bc7,      0x00006a4e,      0x000058d5,      0x0000495c,
            0x00003de3,      0x00002c6a,      0x00001ef1,      0x00000f78,
        ]
        for ch in s:
            if type(ch) == type(''):
                ch = ord(ch)
            tmp=crcValue^(ch)
            crcValue=(crcValue>> 8)^crc16tab[(tmp & 0xff)]

        return 0xffff - crcValue

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Program MSP430 via the EZ430-F2013 ')
    parser.add_argument('-i', '--image', help='Image to program (.a43 = IHex, .txt = TI TXT)')
    parser.add_argument('-u', '--uart', help='TTY UART to attach to MSP430 ezUSB', default='/dev/ttyUSB1')
    parser.add_argument('-r', '--reset', help="Reset MSP when finished programming", action='store_true')
    parser.add_argument('-v', '--verify', help="Verfiy image after programming", action='store_true')
    args = parser.parse_args()

    msp = EZ430(args.uart)
    msp.open()
    # We need to call identify() to stop the MSP430
    print "Identify"
    msp.identify()
    msp.identify2()

    # If we've specified a file name, then parse it & program it in
    if args.image:
        suffix = args.image[-4:].lower()
        if suffix == '.a43':
            prog = IHex(args.image)
            segments = prog.get_segments()
        elif suffix == '.txt':
            prog = TITxt(args.image)
            segments = prog.get_segments(32)
        else:
            raise SystemError, "Invalid HEX file suffix: %s" % (suffix)

        print "Erasing flash..."
        msp.erase_flash_all()
        print "Writing image..."
        msp.write_mem(segments)
        if args.verify:
            print "Verifying image..."
            if not msp.verify_mem(segments):
                raise SystemError, "Failed to verify memory"

    if args.reset:
        print "Reseting MSP430..."
        msp.reset()
    msp.close()

