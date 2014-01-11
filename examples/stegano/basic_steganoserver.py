#!/usr/bin/python
# -*- coding: utf-8 -*-

'''
Author: Robin David
License: GNU GPLv3
Repo: https://github.com/RobinDavid

Copyright (c) 2012 Robin David

PyStack is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or 
any later version http://www.gnu.org/licenses/. 
'''

from pystack.layers.tcp_session import TCPSession
from pystack.layers.tcp_application import TCPApplication
from pystack.pystack import PyStack

def binvalue(val, bitsize): #Return the binary value as a string of the given size 
    binval = bin(val)[2:] if isinstance(val, int) else bin(ord(val))[2:]
    if len(binval) > bitsize:
        raise "binary value larger than the expected size"
    while len(binval) < bitsize:
        binval = "0"+binval #Add as many 0 as needed to get the wanted size
    return binval

def nsplit(s, n):#Split a list into sublists of size "n"
    return [s[k:k+n] for k in xrange(0, len(s), n)]

def int_to_string(val, size):
    return ''.join([chr(int(x,2)) for x in nsplit(binvalue(val, size), 8)])


class SteganoApplication(TCPApplication):
    def __init__(self):
        TCPApplication.__init__(self)
        
        #For sending purposes
        self.hidden_to_stream = "The root password is qwerty" #String to send covertly
        self.position = 0
        self.streaming_finished = False
    
    def packet_received(self, packet, **kwargs):
        print("Regular data:",packet)

    def get_bytes(self, nb): #Return the given number of bytes in the string to send
        if not self.streaming_finished:
            #TODO: return NOne if finished and pad with 0 if needed
            s = self.hidden_to_stream[self.position:self.position+nb]
            while len(s) < nb:
                s+="\x00"
            bytes = int(''.join([binvalue(x,8) for x in s]),2)
            self.position += nb
            if self.position >= len(self.hidden_to_stream):
                self.streaming_finished = True
                return bytes, True
            else:
                return bytes, False
        else:
            return None, True
    
    def hook_incoming(self, packet, **kwargs):
        pass
    
    def hook_outgoing(self, packet, **kwargs):
        ''' Send data covertly, by using ISN, and IPID '''
        if not self.streaming_finished:
            if kwargs["TCP"]["flags"] in (2, 18):
                value,_ = self.get_bytes(4) #seqNb can hold 4 bytes
                if value:
                    kwargs["TCP"]["seq"] = value
                    self.lowerLayers["default"].seqNo = value
                    self.lowerLayers["default"].nextAck = value # !! A nicer way would have been to overwrite _send_SYN and _send_SYNACK methods
            value, res = self.get_bytes(2)
            if value:
                kwargs["IP"]["id"] = value
            if res:
                kwargs["IP"]["flags"] = 2
        return packet, kwargs
      

if __name__ =="__main__":
    stack = PyStack()
    
    steganoserver = SteganoApplication()
    stack.register_tcp_application(steganoserver)
    
    steganoserver.bind(7777, steganoserver, True)
    steganoserver.listen(5)
    
    stack.run(doreactor=True) #stack.stop() called when Ctrl+C 

    