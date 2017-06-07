#!/usr/bin/python
import sys
import RPi.GPIO as GPIO
import Adafruit_DHT
import time
import random
import datetime
import telepot

sensor = Adafruit_DHT.DHT22
pin = 7
ledPin = 20
ledstate = False

GPIO.setmode(GPIO.BCM)
GPIO.setup(ledPin, GPIO.OUT)
GPIO.output(ledPin, GPIO.LOW)

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

def ler_log():
    message = ""
    file = open('bot_log.txt', 'r')
    lines = file.readlines()
    last_line = len(lines) - 1
    if last_line < 10:
        a = last_line 
    else:
        a = 10
    for i in range(last_line, last_line - a, -1):
        message = message + lines[i]
    file.close()
    return(message)

def handle(msg):
    chat_id = msg['chat']['id']
    command = msg['text']
    
    global ledstate
    
    if command == '/roll' or command == '/roll@ittalarmpi_bot':
        log_dados()
        bot.sendMessage(chat_id, random.randint(1,6))
    elif command == '/time' or command == '/time@ittalarmpi_bot':
        log_dados()
        bot.sendMessage(chat_id, str(datetime.datetime.now()))
    elif command == '/temp' or command == '/temp@ittalarmpi_bot':
        log_dados()
        humidity, temperature = Adafruit_DHT.read_retry(sensor, pin)
        bot.sendMessage(chat_id, 'Temperatura={0:0.1f}*C  Ãmidade={1:0.1f}%'.format(temperature, humidity))
    elif command == '/ledon' or command == '/ledon@ittalarmpi_bot':
        log_dados()
        if ledstate == False:
            GPIO.output(ledPin, GPIO.HIGH)
            ledstate = True
            bot.sendMessage(chat_id, 'Led vermelho ligado')
        else:
            bot.sendMessage(chat_id, 'O led vermelho jÃ¡ estÃ¡ ligado!')
    elif command == '/ledoff' or command == '/ledoff@ittalarmpi_bot':
        log_dados()
        if ledstate == True:
            GPIO.output(ledPin, GPIO.LOW)
            ledstate = False
            bot.sendMessage(chat_id, 'Led vermelho desligado')
        else:
            bot.sendMessage(chat_id, 'O led vermelho jÃ¡ estÃ¡ desligado!')
    elif command == '/read' or command == '/read@ittalarmpi_bot':
        log_dados()
        leitura = ler_log()
        bot.sendMessage(chat_id, leitura)
    elif command == '/circuit' or command == '/circuit@ittalarmpi_bot':
        log_dados()
        bot.sendPhoto(chat_id, photo = open('circuit.png', 'rb'), caption = 'Veja o circuito ligado na minha GPIO.') 
    elif command == '/help' or command == '/help@ittalarmpi_bot':
        log_dados()
        bot.sendMessage(chat_id, "VocÃª pode me enviar os seguitentes comandos:\n\n/temp - Medir a temperatura e Ãºmidade relativa do ar\n/read - Ver os dez Ãºltimos registros do log de eventos\n/ledon - Ligar led vermelho\n/ledoff - Desligar led vermelho\n/circuit - Mostrar o circuito ligado no meu GPIO\n/roll - Jogar o dado\n/time - Mostrar a data e hora atual")
    else:
        bot.sendMessage(chat_id, 'Eu nÃ£o entendo esse comando. Utilize /help@ittalarmpi_bot para verificar a lista de comandos disponÃ­veis.')

bot = telepot.Bot('Insert_Token_code_here')
bot.message_loop(handle)
print ('Aguardando comandos ...')
print ("Nome\t\tChat\t\tData\t\t\tComando")

while 1:
    time.sleep(10)
