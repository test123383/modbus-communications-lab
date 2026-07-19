#!/usr/bin/env python
"""
Pymodbus Synchronous Server Simulation for DIN Rail Measuring Device UMG 103-CBM
--------------------------------------------------------------------------

"""
# --------------------------------------------------------------------------- #
# import the various server implementations
# --------------------------------------------------------------------------- #
from pymodbus.server.sync import StartSerialServer
from pymodbus.server.sync import StartTcpServer
from pymodbus.device import ModbusDeviceIdentification
from pymodbus.datastore import ModbusSparseDataBlock
from pymodbus.datastore import ModbusSlaveContext, ModbusServerContext

from pymodbus.transaction import ModbusRtuFramer
# --------------------------------------------------------------------------- #
# configure the service logging
# --------------------------------------------------------------------------- #
import logging
FORMAT = ('%(asctime)-15s %(threadName)-15s'
          ' %(levelname)-8s %(module)-15s:%(lineno)-8s %(message)s')
logging.basicConfig(format=FORMAT)
log = logging.getLogger()
log.setLevel(logging.DEBUG)

# --------------------------------------------------------------------------- #
# Use Big-endian achitecture 
# --------------------------------------------------------------------------- #
ListToSend = {  ####  Voltage V #######
                19000: 0x4366,          # Voltage L1-N MSB      V1 = 230.5V
                19001: 0x8000,          # Voltage L1-N LSB
                19002: 0x4367,          # Voltage L2-N MSB      V2 = 231.5V
                19003: 0x8000,          # Voltage L2-N LSB    
                19004: 0x4368,          # Voltage L3-N MSB      V3 = 232.5V
                19005: 0x8000,          # Voltage L3-N LSB     
                19006: 0x43c8,          # Voltage L1-L2 MSB     U1 = 400.5V
                19007: 0x4000,          # Voltage L1-L2 LSB
                19008: 0x43c8,          # Voltage L2-L3 MSB     U2 = 401.5V
                19009: 0xc000,          # Voltage L2-L3 LSB
                19010: 0x43c9,          # Voltage L3-L1 MSB     U3 = 402.5V
                19011: 0x4000,          # Voltage L3-L1 LSB   

                ####  Current A  #######
                19012: 0x4128,          # Apparent current L1-N MSB     I1 = 10.51A
                19013: 0x28f6,          # Apparent current L1-N LSB
                19014: 0x4138,          # Apparent current L2-N MSB     I2 = 11.52A
                19015: 0x51ec,          # Apparent current L2-N LSB               
                19016: 0x4148,          # Apparent current L3-N MSB     I3 = 12.53A
                19017: 0x7ae1,          # Apparent current L3-N LSB
                19018: 0x0000,          # Current In MSB        In = 0.0A
                19019: 0x0000,          # Current In LSB

                ####  Real power W  #######
                19020: 0x42f0,          # Real power L1-N MSB       P1 = 120.23W	
                19021: 0x75c3,          # Real power L1-N LSB
                19022: 0x42fb,          # Real power L2-N MSB       P2 = 125.72W	
                19023: 0x70a4,          # Real power L2-N LSB
                19024: 0x4302,          # Real power L3-N MSB       P3 = 130.22W	
                19025: 0x3852,          # Real power L3-N LSB
                19026: 0x43bc,          # Psum3=P1+P2+P3 MSB        Psum3 = 376.17W
                19027: 0x15c3,          # Psum3=P1+P2+P3 LSB

                ####  Apparent power VA	  #######
                19028: 0x4300,          # Apparent power L1-N MSB       S1 = 128.7 VA
                19029: 0xb333,          # Apparent power L1-N LSB
                19030: 0x4302,          # Apparent power L2-N MSB       S2 = 130.23 VA
                19031: 0x3ae1,          # Apparent power L2-N LSB
                19032: 0x42ef,          # Apparent power L3-N MSB       S3 = 119.52 VA
                19033: 0x0a3d,          # Apparent power L3-N LSB
                19034: 0x43bd,          # Sum; Ssum3=S1+S2+S3 MSB       Ssum3 = 378.45 VA
                19035: 0x399a,          # Sum; Ssum3=S1+S2+S3 LSB  

                ####  Reactive power var	  #######
                19036: 0x4389,          # Reactive power (mains frequ.) L1 MSB      Q1 = 247.45 var
                19037: 0x399a,          # Reactive power (mains frequ.) L1 LSB
                19038: 0x438c,          # Reactive power (mains frequ.) L2 MSB      Q2 = 280.3 var
                19039: 0x2666,          # Reactive power (mains frequ.) L2 LSB
                19040: 0x4382,          # Reactive power (mains frequ.) L3 MSB      Q3 = 260.15 var
                19041: 0x1333,          # Reactive power (mains frequ.) L3 LSB
                19042: 0x4444,          # Sum; Qsum3=Q1+Q2+Q3 MSB       Qsum3 = 787.9 var
                19043: 0xf99a,          # Sum; Qsum3=Q1+Q2+Q3 LSB

                ####  CosPhi	  #######
                19044: 0x3f23,          # Fund.power factor, CosPhi; UL1 IL1 MSB        CosPhi1 = 0.64
                19045: 0xd70a,          # Fund.power factor, CosPhi; UL1 IL1 LSB
                19046: 0x3f47,          # Fund.power factor, CosPhi; UL2 IL2 MSB        CosPhi2 = 0.78
                19047: 0xae14,          # Fund.power factor, CosPhi; UL2 IL2 LSB
                19048: 0x3f57,          # Fund.power factor, CosPhi; UL3 IL3 MSB        CosPhi3 = 0.84
                19049: 0x0a3d,          # Fund.power factor, CosPhi; UL3 IL3 LSB

                ####  Measured frequency Hz		  #######
                19050: 0x4248,          # Measured frequency MSB        F = 50 Hz
                19051: 0x0000,          # Measured frequency LSB

                ####  Active energy Wh		  #######
                19054: 0x440e,          # Active energy L1 MSB        APP Energy1 = 570.53 Wh
                19055: 0xa1ec,          # Active energy L1 LSB 
                19056: 0x442f,          # Active energy L2 MSB        APP Energy2 = 700.3 Wh
                19057: 0x1333,          # Active energy L2 LSB                
                19058: 0x441e,          # Active energy L3 MSB        APP Energy3 = 635.23 Wh
                19059: 0xceb8,          # Active energy L3 LSB
                19060: 0x44ee,          # Active energy L1..L3 MSB    Sum APP Energy = 1906.06 Wh
                19061: 0x41ec,          # Active energy L1..L3 LSB

                ####  Apparent energy VAh		  #######
                19078: 0x440e,          # Apparent energy L1 MSB        APP Energy1 = 570.53 VAh
                19079: 0xa1ec,          # Apparent energy L1 LSB 
                19080: 0x442f,          # Apparent energy L2 MSB        APP Energy2 = 700.3 VAh
                19081: 0x1333,          # Apparent energy L2 LSB                
                19082: 0x441e,          # Apparent energy L3 MSB        APP Energy3 = 635.23 VAh
                19083: 0xceb8,          # Apparent energy L3 LSB
                19084: 0x44ee,          # Apparent energy L1..L3 MSB    Sum APP Energy = 1906.06 VAh
                19085: 0x41ec,          # Apparent energy L1..L3 LSB              
                
                ####  Reaktive energy varh		  #######
                19086: 0x436d,          # Reactive energy L1 MSB        Reac. Energy1 = 237.78 varh
                19087: 0xc7ae,          # Reactive energy L1 LSB 
                19088: 0x4330,          # Reactive energy L2 MSB        Reac. Energy2 = 176.3 varh
                19089: 0x4ccd,          # Reactive energy L2 LSB                
                19090: 0x4348,          # Reactive energy L3 MSB        Reac. Energy3 = 200.63  varh
                19091: 0xa148,          # Reactive energy L3 LSB
                19092: 0x44ee,          # Reactive energy L3 MSB        Sum Reac Energy = 1906.06 varh
                19093: 0x41ec,          # Reactive energy L3 LSB

                ####  Harmonic, THD %		  #######
                19110: 0x4191,          # Harmonic, THD,U L1-N MSB      THD1 = 18.13 %	
                19111: 0x0a3d,          # Harmonic, THD,U L1-N LSB
                19112: 0x4146,          # Harmonic, THD,U L2-N MSB      THD2 = 12.38 %	
                19113: 0x147b,          # Harmonic, THD,U L2-N LSB
                19114: 0x418f,          # Harmonic, THD,U L3-N MSB      THD3 = 17.96 %12.38	
                19115: 0xae14,          # Harmonic, THD,U L3-N LSB

                19116: 0x4204,          # Harmonic, THD,I L1 MSB       THDI1 = 33.15 %	
                19117: 0x999a,          # Harmonic, THD,I L1 LSB
                19118: 0x41ca,          # Harmonic, THD,I L2 MSB       THDI2 = 25.28 %	
                19119: 0x3d71,          # Harmonic, THD,I L2 LSB
                19120: 0x41f0,          # Harmonic, THD,I L3 MSB       THDI3 = 30.1 %	
                19121: 0xcccd           # Harmonic, THD,I L3 LSB
               }
def run_server():
    # ----------------------------------------------------------------------- #
    # initialize your data store
    # ----------------------------------------------------------------------- #
    store = ModbusSlaveContext(
        hr=ModbusSparseDataBlock(ListToSend),zero_mode=True)   
    context = ModbusServerContext(slaves=store, single=True)

    # ----------------------------------------------------------------------- #
    # initialize the server information
    # ----------------------------------------------------------------------- #
    identity = ModbusDeviceIdentification()
    identity.VendorName = 'Janitza electronics GmbH'
    identity.ProductCode = 'UMG 103-CBM'
    identity.VendorUrl = 'http://www.janitza.com'
    identity.ProductName = 'DIN Rail Measuring Device'
    identity.ModelName = 'DIN Rail Measuring Device UMG 103-CBM'
    identity.MajorMinorRevision = '2.x'

    # ----------------------------------------------------------------------- #
    # run the server : UMG-103-CBM use Modbsu RTU
    # ----------------------------------------------------------------------- #
    # Tcp:
    StartTcpServer(context, identity=identity, address=("0.0.0.0", 504))

    # TCP with different framer
    # StartTcpServer(context, identity=identity,
    #                framer=ModbusRtuFramer, address=("0.0.0.0", 5020))

    # RTU:
    #StartSerialServer(context, framer=ModbusRtuFramer, identity=identity,
    #                 port='/dev/ttyp0', timeout=.005, baudrate=9600)



if __name__ == "__main__":
    run_server()


