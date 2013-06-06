#!/usr/bin/env python
# Manipulate intel hex files - loading & saving as .bin
# See http://en.wikipedia.org/wiki/Intel_HEX for details on the format

import argparse

class IHex(object):
    '''Class to read an Intel HEX file and parse it'''
    def __init__(self, file):
        fd = open(file, 'r')
        self.data = fd.readlines()
        fd.close()
        self.segments = {}

    def get_segments(self):
        '''Reads the segments from the file and returns them'''
        # FIXME: Check CRC
        if len(self.segments) > 0:
            return self.segments
        addr_offset = 0
        for line in self.data:
            line = line.strip()
            if line[0] != ':':
                continue
            type = int(line[7:9], 16)
            if type == 4: # Extended linear address record
                addr_offset = int(line[9:13], 16) << 16
            if type != 0:
                continue
            length = int(line[1:3], 16)
            addr = int(line[3:7], 16) + addr_offset
            data = []
            for pos in range(length):
                off = 9 + pos * 2
                data.append(int(line[off:off + 2], 16))
            self.segments[addr] = data
        return self.segments

    def dump_binary(self, file, flip):
        '''Convert the .ihex file into a .bin file'''
        segments = self.get_segments()
        fd = open(file, 'wb')
        pos = 0
        for addr in sorted(segments):
            data = self.segments[addr]
            # Fill in any blank places with 0xff
            if addr > pos:
                while pos < addr:
                    fd.write('\xff')
                    pos+=1
            for d in data:
                if flip:
                    d = int('{:08b}'.format(d)[::-1], 2)
                fd.write(chr(d))
            pos = addr + len(data)
        fd.close()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Convert .ihex to .bin (with optional flipping)')
    parser.add_argument('-i', '--image', help='Input intel hex file', required = True)
    parser.add_argument('-o', '--output', help='Output .bin file', required = True)
    parser.add_argument('-f', '--flip', help="Flip the MSB/LSB ordering of each byte", action='store_true')
    args = parser.parse_args()

    print "Reading in", args.image
    f = IHex(args.image)
    print "Writing", args.output
    f.dump_binary(args.output, args.flip)

