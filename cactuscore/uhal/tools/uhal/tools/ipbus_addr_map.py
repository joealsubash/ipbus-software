import uhal
import math
import sys
import unittest
import os
import re

BUS_REGEX = re.compile("(^|[,])\s*bus\s*([,]|$)");
SLAVE_REGEX = re.compile("(^|[,])\s*slave\s*([,]|$)");

def __isFIFO(node):
    if str(node.getMode()) == "NON_INCREMENTAL":
        return True
    else:
        return False

def __isMemory(node):
    if str(node.getMode()) == "INCREMENTAL":
        return True
    else:
        return False

def __isRegister(node):
    if str(node.getMode()) == "SINGLE":
        return True
    else:
        return False
    
def __getWidth(node):
    if __isFIFO(node) or __isRegister(node):
        return 0
    elif __isMemory(node):
        return int(math.ceil(math.log(node.getSize(),2)))
    elif __isModule(node):
        result = 0
        children = node.getNodes()
        minaddr = None
        maxaddr = None
        for name in children:
            if __isSlave(node.getNode(name)):
                raise Exception("Slave '%s' inside '%s' slave" % (name,node.getId()))
            addr = node.getNode(name).getAddress()
            if not minaddr or minaddr>addr:
                minaddr = addr
            if not maxaddr or maxaddr<addr:
                maxaddr = addr

        return int(math.ceil(math.log(maxaddr-minaddr+1,2)))
    else:
        return 0
    
def __isModule(node):
    if node.getNodes():
        return True
    else:
        return False

def __isBus(node):
    if BUS_REGEX.search(node.getTags()):
        return True
    else:
        return False
    
def __isSlave(node):
    if SLAVE_REGEX.search(node.getTags()):
        return True
    else:
        return False
        
def __getChildren(n):
    return n.getNodes("[^.]*")

def hex32(num):
    return "0x%08x" % num



def ipbus_addr_map(fn,verbose=False):
    '''
    Returns a vector with all the slaves, addresses, and addresses with for each bus.
    '''
    if verbose:
        uhal.setLogLevelTo(uhal.LogLevel.DEBUG)
    else:
        uhal.disableLogging()

    if fn.find("file://") == -1:
        fn = "file://"+fn

    try:
        d = uhal.getDevice("dummy","ipbusudp-1.3://localhost:12345",fn)
    except Exception:
        raise Exception("File '%s' does not exist or has incorrect format" % fn)
        

    result = []
    buses = ["__root__"]
    addrs = set()
    while (buses):
        bus = buses.pop(0)
        if bus == "__root__":
            parent = d
        else:
            parent = parent.getNode(bus)
            
        children = __getChildren(parent)
        slaves = []
        while (children):
            name = children.pop(0)
            child = parent.getNode(name)
            if __isBus(child):
                if __isSlave(child):
                    raise Exception("Node '%s' is tagged as slave and bus at the same time" % name)
                elif not __isModule(child):
                    raise Exception("Node '%s' is tagged as bus but it does not have children" % name)
                else:
                    buses.append(name)
            elif __isSlave(child):
                addr = child.getAddress()

                #remove duplicates (e.g. masks)
                if addr in addrs:
                    if verbose:
                        print "WARNING: Node '%s' has duplicate address %s. Ignoring slave..." % (name, hex32(addr))
                    continue
                addrs.add(addr)
                width = __getWidth(child)

                slaves.append((name,addr,width))
                
            elif __isModule(child):
                children += map(lambda x: "%s.%s" % (name,x),__getChildren(child))

        #sort by address        
        slaves.sort(lambda x,y: cmp(d.getNode(x[0]).getAddress(),d.getNode(y[0]).getAddress()))
        result.append((bus,slaves))

    return result

def get_vhdl_template(fn=None):
    if not fn:
        this_dir, this_filename = os.path.split(__file__)
        fn = os.path.join(this_dir, "templates", "ipbus_addr_decode.vhd")

    return open(fn).read()

class TestSimple(unittest.TestCase):
    def test_simple(self):
        this_dir, this_filename = os.path.split(__file__)
        simplefn = os.path.join(this_dir, "test_data","simple.xml")
        m = ipbus_addr_map(simplefn)

        #just a smoke test
        buses = [bus for bus,slaves in m]
        self.assertTrue(len(buses) == 3)
        self.assertTrue("__root__" in buses)
        self.assertTrue("SUBSYSTEM1" in buses)
        self.assertTrue("SUBSYSTEM2" in buses)

        sroot = dict(((name,(hex32(addr),width)) for name,addr,width in m[0][1]))
        print sroot
        self.assertTrue(len(sroot) == 6)
        self.assertTrue(sroot['REG'][0] == "0x00000000")
        self.assertTrue(sroot['REG'][1] == 0)
        self.assertTrue(sroot['MEM'][0] == "0x00100000")
        self.assertTrue(sroot['MEM'][1] == 18)
        self.assertTrue(sroot['FIFO'][0] == "0x00000100")
        self.assertTrue(sroot['FIFO'][1] == 0)

        sub2 = dict(((name,(hex32(addr),width)) for name,addr,width in m[2][1]))
        print sub2
        self.assertTrue(len(sub2) == 5)
        self.assertTrue(sub2['REG'][0] == "0x00500002")
        self.assertTrue(sub2['REG'][1] == 0)
        
def test():
     suite = unittest.TestLoader().loadTestsFromTestCase(TestSimple)
     unittest.TextTestRunner().run(suite)
     
if __name__ == '__main__':
    test()
