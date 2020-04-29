import postgres
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

errorString = ''
emailOptions = config['email']
wfsList = config['wfs']
search = config['search']
timeouts = config['timeouts']

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


# SEARCH TABLE
connTabular = postgres.getConn('tabular')
rows = postgres.query(connTabular, "SELECT wfs_url, id, type, type_id, field_name, field_name_alias, muni_field_name, roll_number_field, run_schedule, priority, last_run, last_run_minutes FROM public.tbl_search_layers where run_schedule = 'ALWAYS' order by type;")
for row in rows:
    wfsUrl = row['wfs_url'] + "&count=1"
    typeId = row['type_id']
    nameField = row['field_name']
    muniField = row['muni_field_name']
    aliasField = row['field_name_alias']
    print(typeId)

    # JSON REQUEST
    try:
        r = requests.get(url=wfsUrl)
        data = r.json()

        # GET FEATURES
        features = data['features']

        # CHECK FIELD NAMES
        if len(features) > 0:
            feature = features[0]
            props = feature['properties']

            # CHECK NAME FIELD
            try:
                val = props[nameField]
            except:
                print(typeId + " has invalid search name field.")
                errorString += typeId + " search name field not found.<br/>"
            
            # CHECK MUNI FIELD
            if (muniField != None):
                try:
                    val = props[muniField]
                except:
                    print(typeId + " has invalid search muni field.")
                    errorString += typeId + " muni name field not found.<br/>"

            # CHECK ALIAS FIELD
            if (aliasField != None):
                try:
                    val = props[aliasField]
                except:
                    print(typeId + " has invalid search alias field.")
                    errorString += typeId + " alias name field not found.<br/>"
                        
    except:
        print(typeId + " URL is broken.")
        errorString += "Search table Broken URL - " + typeId + "<br/>" + wfsUrl + "<br/><br/>"
        continue
    
    
# CHECK TIMEOUTS
for item in timeouts:
    name = item['name']
    url = item['url']
    timeoutMs = item['timeoutMs']

    # JSON REQUEST
    try:
        startTime = datetime.now()
        r = requests.get(url=url, timeout=timeoutMs)

        # 404 NOT FOUND
        if r.status_code == 404:
            print(name + " URL is broken.")
            errorString += "Broken URL - " + name + "<br/>" + url + "<br/><br/>"
            continue

        endTime = datetime.now()
        ms = (endTime - startTime).total_seconds() * 1000
        print("timeout (ms): " + str(ms))
        if ms > timeoutMs:
            errorString += "URL is slow: " + url + "<br/>Expected ms: " + \
                str(timeoutMs) + "<br/>Actual ms: " + str(ms) + "<br/><br/>"

    except:
        print(name + " URL is broken.")
        errorString += "Broken URL - " + name + "<br/>" + url + "<br/><br/>"
        continue


# CHECK ALL OF THE WFS URLS
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
    if len(features) > 0:
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
