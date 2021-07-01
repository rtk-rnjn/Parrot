from flask import Flask
from threading import Thread 

app = Flask('')

@app.route('/')
def home():
  return("Program is running! Status OK")

def run():
  app.run(host='0.0.0.0', port=8080)

def keep_alive():
  t = Thread(target=run)
  t.start()



#https://quickchart.io/qr?text=Ritik%20ranjan&size=200