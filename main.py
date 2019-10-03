import sys
import json
import requests
from datetime import datetime
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# READ CONFIG
with open('config.json') as config_file:
    config = json.load(config_file)

emailOptions = config['email']
wfsList = config['wfs']
search = config['search']

# EMAIL FUNCTION


def sendEmail(subject, body):
    server = smtplib.SMTP('smtprelay.county.simcoe.on.ca')

    msg = MIMEMultipart()
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'html'))

    # SEND
    server.sendmail(emailOptions['fromAddress'],
                    emailOptions['toAddresses'], msg.as_string())
    server.quit()


# CHECK ALL OF THE WFS URLS
errorString = ''
for wfs in wfsList:
    name = wfs['name']
    url = wfs['url']
    minRecords = wfs['minRecords']
    fields = wfs['fields']
    enabled = wfs['enabled']

    if enabled == False:
        continue

    # JSON REQUEST
    try:
        r = requests.get(url=url)
        data = r.json()
    except:
        print(name + " URL is broken.")
        errorString += "Broken URL - " + name + "<br/>" + url + "<br/><br/>"
        continue

    # GET FEATURES
    features = data['features']

    # CHECK NUMBER OF RECORDS
    numFeatures = len(features)
    if numFeatures < minRecords:
        print(name + " is missing records.")
        errorString += name + " is missing records.<br/>" + url + "<br/>Min Records: " + \
            str(minRecords) + "<br/>Actual Records: " + \
            str(numFeatures) + "<br/><br/>"

    # CHECK FIELD NAMES
    feature = features[0]
    for fieldName in fields:
        props = feature['properties']
        try:
            val = props[fieldName]
        except:
            print(name + " is missing fields.")
            errorString += name + " is missing fields.<br/>" + \
                url + "<br/>Field Not Found: " + fieldName + "<br/><br/>"

# CHECK SEARCH
minMs = search['urlSearchMinSpeedMs']
url = search['urlSearch']
startTime = datetime.now()
try:
    r = requests.get(url=url)
    data = r.json()
    endTime = datetime.now()
    ms = (endTime - startTime).total_seconds() * 1000
    print("search (ms): " + str(ms))
    if ms > minMs:
        errorString += "Search Speed is slow <br/>Expected ms: " + \
            str(minMs) + "<br/>Actual ms: " + str(ms) + "<br/><br/>"
except:
    print("Search is returning unexpected results.")
    errorString += "Search is broken - " + url + "<br/><br/>"

minMs = search['urlLocationMinSpeedMs']
url = search['urlLocation']
startTime = datetime.now()
try:
    r = requests.get(url=url)
    data = r.json()
    endTime = datetime.now()
    ms = (endTime - startTime).total_seconds() * 1000
    print("search location (ms): " + str(ms))
    if ms > minMs:
        errorString += "Search Location Speed is slow <br/>Expected ms: " + \
            str(minMs) + "<br/>Actual ms: " + str(ms) + "<br/><br/>"
except:
    print("Search Location is returning unexpected results.")
    errorString += "Search Location is broken - " + url + "<br/><br/>"


# SEND EMAIL IF WE HAVE ERRORS
if len(errorString) > 0:
    sendEmail("Service Pinger Error", errorString)
