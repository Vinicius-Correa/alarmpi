#!/usr/bin/env python

# Como foi criado a tabela do banco de dados
# $ mysql -u pi -p
# MariaDB [(none)]> USE datalogger;
# MariaDB [datalogger]> CREATE TABLE sensores (data_hora DATETIME, dht22_t FLOAT, dht22_h FLOAT, bmp180_t FLOAT, bmp180_p FLOAT, seq INT);

import matplotlib
matplotlib.use('Agg')
import sys
import RPi.GPIO as GPIO
import Adafruit_DHT
import time
import datetime
import telepot
import picamera
from threading import Thread
import mysql.connector as mariadb
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd
from scipy import stats
from time import sleep
import Adafruit_BMP.BMP085 as BMP085

camera = picamera.PiCamera()
camera.vflip = True
camera.hflip = True

sensor2 = BMP085.BMP085(mode=BMP085.BMP085_ULTRAHIGHRES)
sensor = Adafruit_DHT.DHT22
pin = 7
ledPin = 20
ledstate = False

sequencia = 0
contador = 0
soma_dht22_t = 0.0
soma_dht22_h = 0.0
soma_bmp180_t = 0.0
soma_bmp180_p = 0.0
media_dht22_t = 0.0
media_dht22_h = 0.0
media_bmp180_t = 0.0
media_bmp180_p = 0.0

df2 = pd.DataFrame(columns={0 : 'Dht22-t', 1 : 'Dht22-h', 2 : 'Bmp180-t', 3 : 'Bmp180-p'})

GPIO.setmode(GPIO.BCM)
GPIO.setup(ledPin, GPIO.OUT)
GPIO.output(ledPin, GPIO.LOW)

class UpdateThread(Thread):
    def __init__(self):
        self.stopped = False
        Thread.__init__(self) # Call the super construcor (Thread's one)
    def run(self):
        while not self.stopped:
            self.mensureValue()
            time.sleep(60) # Periodo do Thread em segundos
    def stop(self):
        self.stopped = True
    def mensureValue(self): #Realiza as medicoes no periodo informado acima
        global contador, soma_dht22_t, soma_dht22_h, soma_bmp180_t, soma_bmp180_p, sequencia
        global media_dht22_t, media_dht22_h, media_bmp180_t, media_bmp180_p, df2
        contador = contador + 1
        df1 = pd.DataFrame(columns={0 : 'Dht22-t', 1 : 'Dht22-h', 2 : 'Bmp180-t', 3 : 'Bmp180-p'})
        for i in range(5):
            dht22_h, dht22_t = Adafruit_DHT.read_retry(sensor, pin)
            bmp180_t = sensor2.read_temperature()
            bmp180_p = sensor2.read_pressure()/100
            medidas = [dht22_t, dht22_h, bmp180_t, bmp180_p]
            df1.loc[len(df1)] = medidas
            time.sleep(0.3)
        medida_min = [stats.trim_mean(df1[0], 0.25), stats.trim_mean(df1[1], 0.25), stats.trim_mean(df1[2], 0.25), stats.trim_mean(df1[3], 0.25)]
        df2.loc[len(df2)] = medida_min
        if contador == 10: #Numero total de medicoes
            media_dht22_t = stats.trim_mean(df2[0], 0.25) #Calculo da media das medicoes
            media_dht22_h = stats.trim_mean(df2[1], 0.25)
            media_bmp180_t = stats.trim_mean(df2[2], 0.25)
            media_bmp180_p = stats.trim_mean(df2[3], 0.25)
            print("Media = ",stats.trim_mean(df2, 0.25))
            df2 = pd.DataFrame(columns={0 : 'Dht22-t', 1 : 'Dht22-h', 2 : 'Bmp180-t', 3 : 'Bmp180-p'})
            mariadb_connection = mariadb.connect(user='pi', password='pi', database='datalogger')
            cursor = mariadb_connection.cursor()
            cursor.execute ("INSERT INTO sensores VALUES (NOW(), %.2f, %.2f, %.2f, %.2f, %s )" % (media_dht22_t, media_dht22_h, media_bmp180_t, media_bmp180_p, sequencia))
            mariadb_connection.commit()
            cursor.execute("SELECT * FROM (SELECT * FROM sensores ORDER BY seq DESC LIMIT 144) sub ORDER BY seq ASC")
            results = cursor.fetchall()
            mariadb_connection.close()
            df = pd.DataFrame( [[ij for ij in i] for i in results] )
            df.rename(columns={0: 'Data', 1: 'Dht22_t', 2: 'Dht22_h', 3: 'Bmp180_t', 4: 'Bmp180_p', 5: 'Sequencia'}, inplace=True);
        
            fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(nrows=2, ncols=2)
            ax1.plot(df['Data'], df['Dht22_t'], 'r-')
            ax1.set_ylim(df[['Dht22_t'][0]].min()-3, df[['Dht22_t'][0]].max()+3)
            ax1.set(title='DHT22', ylabel='Temperatura (*C)')
            ax1.grid()

            ax3.plot(df['Data'], df['Dht22_h'], 'b-')
            ax3.set_ylim(df[['Dht22_h'][0]].min()-10, df[['Dht22_h'][0]].max()+10)
            ax3.set(ylabel='Umidade relativa (%)')
            ax3.grid()
            ax3.xaxis.set_major_formatter(mdates.DateFormatter("%d-%m %Hh"))

            ax2.plot(df['Data'], df['Bmp180_t'], 'r-')
            ax2.set_ylim(df[['Bmp180_t'][0]].min()-3, df[['Bmp180_t'][0]].max()+3)
            ax2.set(title='BMP180', ylabel='Temperatura (*C)')
            ax2.grid()

            ax4.plot(df['Data'], df['Bmp180_p'], 'g-')
            ax4.set_ylim(df[['Bmp180_p'][0]].min()-1, df[['Bmp180_p'][0]].max()+1)
            ax4.set(ylabel='Pressao atmosferica (hPa)')
            ax4.grid()
            ax4.xaxis.set_major_formatter(mdates.DateFormatter("%d-%m %Hh"))
            fig.autofmt_xdate()
            fig.set_size_inches(14, 9)
            fig.savefig("grafico.png", bbox_inches='tight')
            sequencia = sequencia + 1
            contador = 0
            soma_dht22_t = 0.0
            soma_dht22_h = 0.0
            soma_bmp180_t = 0.0
            soma_bmp180_p = 0.0

def transforma(valor):
    if valor < 10:
	    valor2 = "0" + str(valor)
    else:
        valor2 = str(valor)
    return(valor2)

def log_dados():
    updates = bot.getUpdates()
    username = updates[0]['message']['from']['first_name']
    chat_id = updates[0]['message']['chat']['id']
    if chat_id > 0:
        chat = updates[0]['message']['chat']['type']
    else:
        chat = updates[0]['message']['chat']['title']
    data = updates[0]['message']['date']
    data2 = time.localtime(data)
    mes = transforma(data2.tm_mon)
    dia = transforma(data2.tm_mday)
    hora = transforma(data2.tm_hour)
    minuto = transforma(data2.tm_min)
    segundo = transforma(data2.tm_sec)
    data3 = str(data2.tm_year) + "/" + mes + "/" + dia + " " + hora + ":" + minuto + ":" + segundo
    texto = updates[0]['message']['text']
    if len(chat) < 9:
        dados = username + "\t" + chat + "\t\t" + data3 + "\t" + texto
    else:
	    dados = username + "\t" + chat + "\t" + data3 + "\t" + texto
    print(dados)
    file = open('bot_log.txt', 'a')
    file.write(dados + "\n")
    file.close()

def handle(msg):
    chat_id = msg['chat']['id']
    command = msg['text']
    global media_dht22_t, media_dht22_h, media_bmp180_t, media_bmp180_p
    global ledstate
    
    if command == '/medir' or command == '/medir@ittalarmpi_bot':
        log_dados()
        bot.sendMessage(chat_id, 'Neste momento:\n\nDHT22:\nTemperatura = {0:0.1f} *C\nUmidade = {1:0.1f} %\n\nBMP180:\nTemperatura = {2:0.2f} *C\nPressao = {3:0.2f} hPa'.format(media_dht22_t, media_dht22_h, media_bmp180_t, media_bmp180_p))  
        bot.sendPhoto(chat_id, photo = open('grafico.png', 'rb'), caption = '')
    elif command == '/ledon' or command == '/ledon@ittalarmpi_bot':
        log_dados()
        if ledstate == False:
            GPIO.output(ledPin, GPIO.HIGH)
            ledstate = True
            bot.sendMessage(chat_id, 'Led vermelho ligado')
        else:
            bot.sendMessage(chat_id, 'O led vermelho ja esta ligado!')
    elif command == '/ledoff' or command == '/ledoff@ittalarmpi_bot':
        log_dados()
        if ledstate == True:
            GPIO.output(ledPin, GPIO.LOW)
            ledstate = False
            bot.sendMessage(chat_id, 'Led vermelho desligado')
        else:
            bot.sendMessage(chat_id, 'O led vermelho ja esta desligado!')
    elif command == '/picture' or command == '/picture@ittalarmpi_bot':
        log_dados()
        camera.capture('image1.jpg')
        bot.sendPhoto(chat_id, photo = open('image1.jpg', 'rb'), caption = ' ')
    elif command == '/help' or command == '/help@ittalarmpi_bot':
        log_dados()
        bot.sendMessage(chat_id, "Voce pode me enviar os seguitentes comandos:\n\n/medir - Verificar as medicoes realizadas pelos sensores instalados\n/ledon - Ligar led vermelho\n/ledoff - Desligar led vermelho\n/picture - Tirar uma foto\n\nEstou rodando o codigo hospedado no endereco https://github.com/Vinicius-Correa/alarmpi")
    else:
        bot.sendMessage(chat_id, 'Eu nao entendo esse comando. Utilize /help@ittalarmpi_bot para verificar a lista de comandos disponiveis.')

bot = telepot.Bot('378434389:AAGVOVAmRj8OBByMAvHe-lBktNWowuxYa3w')
bot.message_loop(handle)

while contador < 6:
    contador = contador + 1
    dht22_h, dht22_t = Adafruit_DHT.read_retry(sensor, pin)
    bmp180_t = sensor2.read_temperature()
    bmp180_p = sensor2.read_pressure()/100
    soma_dht22_t = soma_dht22_t + dht22_t 
    soma_dht22_h = soma_dht22_h + dht22_h
    soma_bmp180_t = soma_bmp180_t + bmp180_t
    soma_bmp180_p = soma_bmp180_p + bmp180_p
    if contador == 5: #Numero total de medicoes
        media_dht22_t = soma_dht22_t / contador #Calculo da media das medicoes
        media_dht22_h = soma_dht22_h / contador
        media_bmp180_t = soma_bmp180_t / contador
        media_bmp180_p = soma_bmp180_p / contador
        soma_dht22_t = 0.0
        soma_dht22_h = 0.0
        soma_bmp180_t = 0.0
        soma_bmp180_p = 0.0

mariadb_connection = mariadb.connect(user='pi', password='pi', database='datalogger')
cursor = mariadb_connection.cursor()
cursor.execute("SELECT MAX(seq) AS seq FROM sensores");
results = pd.DataFrame(cursor.fetchall())
cursor.execute("SELECT * FROM (SELECT * FROM sensores ORDER BY seq DESC LIMIT 144) sub ORDER BY seq ASC")
results2 = cursor.fetchall()
mariadb_connection.close()

sequencia = results[0][0] + 1

df = pd.DataFrame( [[ij for ij in i] for i in results2] )
df.rename(columns={0: 'Data', 1: 'Dht22_t', 2: 'Dht22_h', 3: 'Bmp180_t', 4: 'Bmp180_p', 5: 'Sequencia'}, inplace=True);
        
fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(nrows=2, ncols=2)
ax1.plot(df['Data'], df['Dht22_t'], 'r-')
ax1.set_ylim(df[['Dht22_t'][0]].min()-5, df[['Dht22_t'][0]].max()+5)
ax1.set(title='DHT22', ylabel='Temperatura (*C)')
ax1.grid()

ax3.plot(df['Data'], df['Dht22_h'], 'b-')
ax3.set_ylim(df[['Dht22_h'][0]].min()-10, df[['Dht22_h'][0]].max()+10)
ax3.set(ylabel='Umidade relativa (%)')
ax3.grid()
ax3.xaxis.set_major_formatter(mdates.DateFormatter("%d-%m %Hh"))

ax2.plot(df['Data'], df['Bmp180_t'], 'r-')
ax2.set_ylim(df[['Bmp180_t'][0]].min()-5, df[['Bmp180_t'][0]].max()+5)
ax2.set(title='BMP180', ylabel='Temperatura (*C)')
ax2.grid()

ax4.plot(df['Data'], df['Bmp180_p'], 'g-')
ax4.set_ylim(df[['Bmp180_p'][0]].min()-1, df[['Bmp180_p'][0]].max()+1)
ax4.set(ylabel='Pressao atmosferica (hPa)')
ax4.grid()
ax4.xaxis.set_major_formatter(mdates.DateFormatter("%d-%m %Hh"))
fig.autofmt_xdate()
fig.set_size_inches(14, 9)
fig.savefig("grafico.png", bbox_inches='tight')

contador = 0
myThread = UpdateThread()
myThread.start()

try:
    print ('Aguardando comandos ...')
    print ("Nome\t\tChat\t\tData\t\t\tComando")
    while True:
        time.sleep(10)

except KeyboardInterrupt:
    myThread.stop()
    GPIO.cleanup()  # Reset GPIO settings
    time.sleep(3)
