#!/usr/bin/env python
"""
Pymodbus Synchronous Server Simulation for Power Analyser EnergyTeam X-Meter
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
                7001: 0x4366,          # Voltage L1-N MSB      V1 = 230.5V
                7002: 0x8000,          # Voltage L1-N LSB
                7003: 0x4367,          # Voltage L2-N MSB      V2 = 231.5V
                7004: 0x8000,          # Voltage L2-N LSB    
                7005: 0x4368,          # Voltage L3-N MSB      V3 = 232.5V
                7006: 0x8000,          # Voltage L3-N LSB     
                7007: 0x43c8,          # Voltage L1-L2 MSB     U1 = 400.5V
                7008: 0x4000,          # Voltage L1-L2 LSB
                7009: 0x43c8,          # Voltage L2-L3 MSB     U2 = 401.5V
                7010: 0xc000,          # Voltage L2-L3 LSB
                7011: 0x43c9,          # Voltage L3-L1 MSB     U3 = 402.5V
                7012: 0x4000,          # Voltage L3-L1 LSB   

                ####  Current A  #######
                7013: 0x4128,          # Current I L1 MSB      I1 = 10.51A
                7014: 0x28f6,          # Current I L1 LSB
                7015: 0x4138,          # Current I L2 MSB      I2 = 11.52A
                7016: 0x51ec,          # Current I L2 LSB               
                7017: 0x4148,          # Current I L3 MSB      I3 = 12.53A
                7018: 0x7ae1,          # Current I L3 LSB
                7065: 0x0000,          # Current In MSB        In = 0.0A
                7066: 0x0000,          # Current In LSB

                ####  Real power W  #######
                7019: 0x42f0,          # Real power P1 L1N MSB     P1 = 120.23W	
                7020: 0x75c3,          # Real power P1 L1N LSB
                7021: 0x42fb,          # Real power P2 L2N MSB     P2 = 125.72W
                7022: 0x70a4,          # Real power P2 L2N LSB
                7023: 0x4302,          # Real power P3 L3N MSB     P3 = 130.22W 
                7024: 0x3852,          # Real power P3 L3N LSB
                7055: 0x43bc,          # Sum; Psum3=P1+P2+P3 MSB   Psum3 = 376.17W   
                7056: 0x15c3,          # Sum; Psum3=P1+P2+P3 LSB

                ####  Reactive power var	  #######
                7025: 0x4389,          # Reactive power Q1 L1N MSB       Q1 = 247.45 var
                7026: 0x399a,          # Reactive power Q1 L1N LSB
                7027: 0x438c,          # Reactive power Q2 L2N MSB       Q2 = 280.3 var
                7028: 0x2666,          # Reactive power Q2 L2N LSB
                7029: 0x4382,          # Reactive power Q3 L3N MSB       Q3 = 260.15 var
                7030: 0x1333,          # Reactive power Q3 L3N LSB
                7057: 0x4444,          # Sum; Qsum3=Q1+Q2+Q3 MSB               Qsum3 = 787.9 var
                7058: 0xf99a,          # Sum; Qsum3=Q1+Q2+Q3 LSB

                ####  Apparent power VA	  #######
                7037: 0x4300,          # Apparent power S1 L1N MSB     S1 = 128.7 VA
                7038: 0xb333,          # Apparent power S1 L1N LSB
                7039: 0x4302,          # Apparent power S2 L2N MSB     S2 = 130.23 VA 
                7040: 0x3ae1,          # Apparent power S2 L2N LSB
                7041: 0x42ef,          # Apparent power S3 L3N MSB     S3 = 119.52 VA
                7042: 0x0a3d,          # Apparent power S3 L3N LSB

                ####  PF	  #######
                7031: 0x3f23,          # PF; UL1 IL1 (fundamental comp.) MSB       PF1 = 0.64
                7032: 0xd70a,          # PF; UL1 IL1 (fundamental comp.) LSB
                7033: 0x3f47,          # PF; UL2 IL2 (fundamental comp.) MSB       PF2 = 0.78
                7034: 0xae14,          # PF; UL2 IL2 (fundamental comp.) LSB
                7035: 0x3f57,          # PF; UL3 IL3 (fundamental comp.) MSB       PF3 = 0.84      
                7036: 0x0a3d,          # PF; UL3 IL3 (fundamental comp.) LSB
                7059: 0x3f47,          # PF; UL3 IL3 (fundamental comp.) MSB       PFtot = 0.78      
                7060: 0xae14,          # PF; UL3 IL3 (fundamental comp.) LSB

                ####  Measured frequency Hz		  #######
                7061: 0x4247,          # Measured frequency MSB        F = 49.9 Hz
                7062: 0x999a,          # Measured frequency LSB

                ####  Active energy Wh		  #######
                7099: 0x440e,          # Active energy + MSB        APP Energy+ = 570.53 Wh
                7100: 0xa1ec,          # Active energy + LSB 
                7101: 0x442f,          # Active energy - MSB        APP Energy- = 700.3 Wh
                7102: 0x1333,          # Active energy - LSB                

                ####  Reaktive energy varh		  #######
                7013: 0x436d,          # Reactive energy + MSB        Reac. Energy+ = 237.78 varh
                7014: 0xc7ae,          # Reactive energy + LSB 
                7015: 0x4330,          # Reactive energy - MSB        Reac. Energy- = 176.3 varh
                7016: 0x4ccd,          # Reactive energy - LSB
                12345: 0x0000,         # Enable reset
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
    identity.VendorName = 'EnergyTeam'
    identity.ProductCode = 'X-Meter Base '
    identity.VendorUrl = 'https://www.energyteam.it/'
    identity.ProductName = 'Power Analyser'
    identity.ModelName = 'Power Analyser X-Meter'
    identity.MajorMinorRevision = '1.36'

    # ----------------------------------------------------------------------- #
    # run the server : UMG-RM use Modbsu RTU 
    #                  UMG-RM-EL use Modbsu TCP
    # ----------------------------------------------------------------------- #
    # Tcp:
    StartTcpServer(context, identity=identity, address=("0.0.0.0", 506))

    # TCP with different framer
    # StartTcpServer(context, identity=identity,
    #                framer=ModbusRtuFramer, address=("0.0.0.0", 5020))

    # RTU:
    # StartSerialServer(context, framer=ModbusRtuFramer, identity=identity,
    #                   port='/dev/ttyp0', timeout=.005, baudrate=9600)



if __name__ == "__main__":
    run_server()


