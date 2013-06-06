#!/usr/bin/env python

class TITxt(object):
    '''Class to read the TI .txt HEX files and parse it
    http://linux.die.net/man/5/srec_ti_txt
    http://www.ti.com/lit/pdf/slau101'''
    def __init__(self, file):
        fd = open(file, 'r')
        self.data = fd.readlines()
        fd.close()

    def get_segments(self, chunk_size=16):
        '''Read the chunks of the file & return them in chunks'''
        current_addr = 0
        data = []
        segments = {}
        for line in self.data:
            if line[0] == '@':
                if len(data) > 0:
                    segments[current_addr] = data
                current_addr = int(line[1:], 16)
            elif line[0] == 'q':
                break
            else:
                for d in line.strip().split(' '):
                    data.append(int(d, 16))
                    if len(data) >= chunk_size:
                        segments[current_addr] = data
                        current_addr += len(data)
                        data = []
        return segments


