#!/usr/bin/python
# Verifica se il server Rocrail e' in esecuzione.
# (c)2014 Stefano Fagnani http://ilplasticomodulare.blogspot.it
#
#     Version................... 1.0
#     Date...................... 29/01/2015


#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.

#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.

#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.


import sys
import fcntl, os
import psutil
import time
import errno
import string
from Adafruit_CharLCDPlate import Adafruit_CharLCDPlate  
 
import socket

CYCLE_DELAY = 2
rpi_SERVERUP = "Up&Run"
rpi_SERVERDOWN = "Stopped"
rpi_PWON = "Global power ON"
rpi_PWOFF = "Global power OFF"
rpi_AUTOON = ""
rpi_AUTOOFF = ""
rpi_WELCOME = "     RocPi\nRocrail on RasPi"
rpi_stat = rpi_SERVERUP
rpi_power = "OFF"
rpi_auto = "OFF"
rpi_server_name = 'rocrail'                                    
rpi_server_status = False 
rpi_socket_created = False 



#Ottiene il PID dal nome del processo, imposta la variabile globale process a true se esite.
def pid_from_name(name):
   pids = psutil.get_pid_list()
   global process
   for pid in pids:
     try:
       p = psutil.Process(pid)
     except psutil.NoSuchProcess:
       continue 	
     if p.name() == name:
       process = True
       return
     else:
       process = False

# Analizza la stringa in argomento e verifica lo stato del server in base al contenuto
def parse_socket(socket_received): 
   global rpi_power 
   global rpi_auto 
   if string.find(socket_received,"Global power ON") <> -1 or string.find(socket_received,"<state power=\"true\"") <> -1 :
      rpi_power = "ON"
      return 
   if string.find(socket_received,"Global power OFF") <> -1 or string.find(socket_received,"<state power=\"false\"") <> -1 :
      rpi_power = "OFF"	  
      return
   if string.find(socket_received,"Automatic mode is on.") <> -1 or string.find(socket_received,"<auto cmd=\"on\"/>") <> -1:
      rpi_auto = "ON"	  
      return
   if string.find(socket_received,"Automatic mode is off.") <> -1  or string.find(socket_received,"<auto cmd=\"off\"/>") <> -1:
      rpi_auto = "OFF"	  
      return
	  
	  
# compone il messaggio con gli header da inviare al server
def sendMsg( s, xmlType, xmlMsg ):
  s.send("<xmlh><xml size=\"%d\" name=\"%s\"/></xmlh>%s" %(len(xmlMsg), xmlType, xmlMsg))

  

# Initialize the LCD plate.  Should auto-detect correct I2C bus.  If not,
# pass '0' for early 256 MB Model B boards or '1' for all later versions

lcd = Adafruit_CharLCDPlate()

buttons = ( (lcd.SELECT, "NN",False),
            (lcd.LEFT,   "_POWER",False),
            (lcd.UP,     "_EBREAK",False),
            (lcd.DOWN,   "NN",False),
            (lcd.RIGHT,  "_AUTO",False) )
# Pulisce lo schermo LCD, mostra i saluti

lcd.clear()
lcd.backlight(lcd.ON)
lcd.message(rpi_WELCOME)

# Crea un nuovo socket
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

#Connessione al server rocrail con un socket non bloccante
try:
  print "Connection...."
  s.connect(('localhost', 8051))
  fcntl.fcntl(s, fcntl.F_SETFL, os.O_NONBLOCK) 
  #Richiede il plan completo
  rrMsg = "<model cmd=\"plan\"/>"
  sendMsg( s, "model", rrMsg )

except socket.error as err:
  #print err
  if err.errno == errno.ECONNREFUSED:
    rpi_stat = "No Conn"
         

# Imposta il ritardo per la esecuzione di comandi nel ciclo infinito, vengono eseguiti ogni 2 secondi.
current = time.time()
delay = current + CYCLE_DELAY

prev = -1
# Ciclo principale viene eseguito un controllo ogni 2 secondi per visualizzare a display 
while True:
    
   # azzera il contatore temporale
   current = time.time()
   
   #rimane in ascolto con un socket non bloccante e analizza le risposte
   try:
      r_request = s.recv(4096)
      parse_socket(r_request)
      #print r_request
   except socket.error, e:
      err = e.args[0]
      if err == errno.EAGAIN or err == errno.EWOULDBLOCK:
         pass
      else:
         # a "real" error occurred
         print e
         sys.exit(1)
   
  #Controlla lo stato dei pulsanti e invia i comandi relativi al server RR
   for button in buttons:
      
      if lcd.buttonPressed(button[0]):
        
           if button[1] == "_POWER" :
              print "btn Power"
              if rpi_power == "ON":
                 rrMsg = "<sys cmd=\"stop\"/>"
                 sendMsg( s, "sys", rrMsg )
                 #print "Power OFF"
              elif rpi_power == "OFF":
                 rrMsg = "<sys cmd=\"go\"/>"
                 sendMsg( s, "sys", rrMsg )
                 #print "Power ON"
           if button[1] == "_AUTO":
              print "btn Auto"
              if rpi_auto == "ON":
                 rrMsg = "<auto cmd=\"off\"/>"
                 sendMsg( s, "auto", rrMsg )
                 #print "auto OFF"
              elif rpi_auto == "OFF":
                 rrMsg = "<auto cmd=\"on\"/>"
                 sendMsg( s, "auto", rrMsg )
                 #print "Auto ON"
           if button[1] == "_EBREAK":
              rrMsg = "<sys cmd=\"ebreak\"/>"
              sendMsg( s, "sys", rrMsg )
              print "Ebreak"
       
      time.sleep(1)
   
# Aggiornamento visualizzazione LCD
   
   if current > delay:   
      pid_from_name(rpi_server_name)
      if process == True:
         rpi_stat = rpi_SERVERUP
         rpi_server_status=True
      else:
         rpi_stat = rpi_SERVERDOWN
         rpi_server_status=False
      
      LCDmessage = "Rocrail {0}\nDCC {1} Auto {2}".format(rpi_stat,rpi_power,rpi_auto)
      lcd.clear()
      lcd.message(LCDmessage)
      delay = current + 2
      #print LCDmessage
      
#EOF
