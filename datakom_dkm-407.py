#!/usr/bin/env python
"""
Pymodbus Synchronous Server Simulation for Power Analyser DATAKOM DKM-407
--------------------------------------------------------------------------

"""
# --------------------------------------------------------------------------- #
# import the various server implementations
# --------------------------------------------------------------------------- #
from pymodbus.server.sync import StartTcpServer
from pymodbus.server.sync import StartSerialServer

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
# Use Little-endian achitecture 
# --------------------------------------------------------------------------- #
ListToSend = {  ####  Voltage V coeff = 1 #######
                20480: 0xE600,          # Phase L1 voltage MSB      V1 = 230V
                20481: 0x0000,          # Phase L1 voltage LSB
                20482: 0xF000,          # Phase L2 voltage MSB      V2 = 240V
                20483: 0x0000,          # Phase L2 voltage LSB  
                20484: 0xFA00,          # Phase L3 voltage MSB      V3 = 250V
                20485: 0x0000,          # Phase L3 voltage LSB     
                20486: 0x9001,          # Phase L1-L2 voltage MSB       U1 = 400V
                20487: 0x0000,          # Phase L1-L2 voltage LSB
                20488: 0x9101,          # Phase L2-L3 voltage MSB       U2 = 401V
                20489: 0x0000,          # Phase L2-L3 voltage LSB
                20490: 0x9201,          # Phase L3-L1 voltage MSB       U3 = 402V
                20491: 0x0000,          # Phase L3-L1 voltage LSB  

                ####  Current A coeff = 0.1 #######
                20492: 0x3700,          # Phase L1 current MSB     I1 = 5.5 A
                20493: 0x0000,          # Phase L1 current LSB
                20494: 0x4100,          # Phase L2 current MSB     I2 = 6.5 A
                20495: 0x0000,          # Phase L2 current LSB               
                20496: 0x4B00,          # Phase L3 current MSB     I3 = 7.5 A
                20497: 0x0000,          # Phase L3 current LSB
                20498: 0x0100,          # Neutral current MSB     I0 = 0.1 A
                20499: 0x0000,          # neutral current LSB

                ####  Active power W  coeff = 0.1  #######
                20500: 0xB204,          # Real power L1-N MSB       P1 = 120.2 W	
                20501: 0x0000,          # Real power L1-N LSB
                20502: 0xE904,          # Real power L2-N MSB       P2 = 125.7 W	
                20503: 0x0000,          # Real power L2-N LSB
                20504: 0x1605,          # Real power L3-N MSB       P3 = 130.2 W	
                20505: 0x0000,          # Real power L3-N LSB
                20506: 0xB10E,          # Psum3=P1+P2+P3 MSB        Psum = 376.1 W
                20507: 0x0000,          # Psum3=P1+P2+P3 LSB

                ####  Reactive power var coeff = 0.1	  #######
                20508: 0xAA09,          # Phase L1 reactive power MSB     Q1 = 247.4 var
                20509: 0x0000,          # Phase L1 reactive power LSB
                20510: 0xF30A,          # Phase L2 reactive power MSB     Q2 = 280.3 var
                20511: 0x0000,          # Phase L2 reactive power) LSB
                20512: 0x290A,          # Phase L3 reactive power MSB     Q3 = 260.1 var
                20513: 0x0000,          # Phase L3 reactive power LSB
                20514: 0xC71E,          # Total reactive power MSB        Qsum = 787.9 var
                20515: 0x0000,          # Total reactive power LSB

                ####  Apparent power VA coeff = 0.1  #######
                20516: 0x0705,          # Phase L1 apparent power MSB       S1 = 128.7 VA
                20517: 0x0000,          # Phase L1 apparent power LSB
                20518: 0x1605,          # Phase L2 apparent power MSB       S2 = 130.2 VA
                20519: 0x0000,          # Phase L2 apparent power LSB
                20520: 0xAB04,          # Phase L3 apparent power MSB       S3 = 119.5 VA
                20521: 0x0000,          # Phase L3 apparent power LSB
                20522: 0xC90E,          # Total apparent power MSB       Ssum = 378.5 VA
                20523: 0x0000,          # Total apparent power LSB  

                ####  CosPhi Power factor  coeff = 0.001	  #######
                20524: 0x8002,          # Phase L1 power factor       CosPhi1 = 0.64
                20525: 0x0C03,          # Phase L2 power factor       CosPhi2 = 0.78
                20526: 0x4803,          # Phase L3 power factor       CosPhi3 = 0.84 
                20527: 0x8E03,          # Total power factor          CosTot = 0.91

                ####  Measured frequency Hz	coeff = 0.01	  #######
                20528: 0x8313,          # Measured frequency MSB        F = 49.95 Hz

                ####  Harmonic, THD coeff = 1	  #######
                20529: 0x1200,          # Phase L1 voltage THD      THD1 = 18 %	
                20530: 0x1300,          # Phase L2 voltage THD      THD2 = 19 %
                20531: 0x1400,          # Phase L3 voltage THD      THD2 = 20 %
                20532: 0x0C00,          # Phase L1-L2 voltage THD   THD12 = 12 %	
                20533: 0x0D00,          # Phase L2-L3 voltage THD   THD23 = 13 %
                20534: 0x0E00,          # Phase L3-L1 voltage THD   THD31 = 14 %

                20535: 0x1E00,          # Phase L1 current THD      THDI1 = 30 %
                20536: 0x2800,          # Phase L2 current THD      THDI2 = 40 %	
                20537: 0x3200,          # Phase L3 current THD      THDI2 = 50 %
                20538: 0x3C00,          # Neutral current THD       THDI2 = 60 %	

                ####   Energy KWh	coeff = 0.1	  #######
                20648: 0xEA18,          # Energy KWh  MSB           Energy1 = 637.8 KWh
                20649: 0x0000,          # Energy KWh  LSB

                ####  Reaktive energy varh coeff 0.1		  #######
                20650: 0x9E06,          # Reactive energy varh  MSB Energy1 = 169.4 kVArh
                20651: 0x0000,          # Reactive energy varh  LSB

                20656: 0x5055,          # Alarms status: 0x5550 (alarm on, alarm off)
                16384: 0x0000,          # Password register
                16386: 0x0000           # Reset register
                
                
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
    identity.VendorName = 'DATAKOM ELECTRONICS ENGINEERING A.S '
    identity.ProductCode = 'DATAKOM DKM-407'
    identity.VendorUrl = 'https://datakom.com.tr'
    identity.ProductName = 'Power Analyser'
    identity.ModelName = 'Power Analyser DATAKOM DKM-407'
    identity.MajorMinorRevision = '1.1'

    # ----------------------------------------------------------------------- #
    # run the server : UMG-604 use Modbsu RTU
    # ----------------------------------------------------------------------- #
    # Tcp:
    StartTcpServer(context, identity=identity, address=("0.0.0.0", 502))

    # TCP with different framer
    # StartTcpServer(context, identity=identity,
    #                framer=ModbusRtuFramer, address=("0.0.0.0", 5020))

    # RTU:
    #StartSerialServer(context, framer=ModbusRtuFramer, identity=identity,
    #                  port='COM2', timeout=.005, baudrate=19200)



if __name__ == "__main__":
    run_server()