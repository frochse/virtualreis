#!/usr/bin/env python

"""
Author: Max Kiffen
Date: 04-11-2021
Flask script for contacting API's and reading data
"""

# Import requirements
from datetime import datetime, timedelta
from flask import Flask
from flask import request
from flask import json 

# Import modules with API's
from hotelapi import hotelapi
from NS_API import NsTrip
from skyscannerAPI import run_skyscannerAPI
from sqlconnection import db_interactions

# dictionary met de coordinated, landcodes en vliegveldcodes per stad
citytocoordinates = {
    "BARCELONA": (41.385063,2.173404, "ES", "BCN"),
    "PARIJS": (48.856613,2.352222, "FR", "CDG"),
    "ROME":	(41.902782,12.49636, "IT", "FCO"),
    "MILAAN": (45.463619,9.188120, "IT", "MXP"),
    "MADRID": (40.416775,-3.703790, "SP", "MAD"),
    "BERLIJN": (52.520008,13.404954, "DE", "BER"),
    "HAMBURG": (53.551086,9.993682, "DE", "HAM"),
    "LISSABON": (38.736946,-9.142685, "PT", "LIS"),
    "ATHENE": (37.983810,23.727539, "GR", "ATH"),
    "LONDEN": (51.509865,-0.118092, "UK", "LHR"),
   }


# methode voor het samenvoegen van de informatie uit de API's
def sorteren(vlucht_heen,ns_heen,vlucht_terug,ns_terug,hotels):
    heenreisdict = {"heenreis":[vlucht_heen,ns_heen]}
    terugreisdict = {"terugreis":[vlucht_terug,ns_terug]}
    reisdict = {"reis":[heenreisdict,terugreisdict,hotels]}
    return reisdict

app = Flask(__name__)

# lege route, gives usage of flask API
@app.route("/")
def index():
    usagestr = 'Usage full program: -X GET "http://<hostname>[:<port>]/api?maxopties=<maxopties>&reispersonen=<reispersonen>&reisdatumheen=<reisdatumheen>&reisdatumterug=<reisdatumterug>&reisbestemming=<reisbestemming>&reisvertrek=<reisvertrek>" \n'
    usagestr = usagestr + 'Usage hotelAPI only: -X GET "http://<hostname>[:<port>]/hotelapi?maxopties=<maxopties>&reisbestemming=<reisbestemming>" \n'
    usagestr = usagestr + 'Usage NSAPI only: -X GET "http://<hostname>[:<port>]/nsapi?maxopties=<maxopties>&reisvertrek=<reisvertrek>&reisvliegveld=<reisvliegveld>&tijd=<tijd>" \n'
    usagestr = usagestr + 'Usage skyscannerAPI only: -X GET "http://<hostname>[:<port>]/vluchtapi?reispersonen=<reispersonen>&reisdatumheen=<reisdatumheen>&reisdatumterug=<reisdatumterug>&reisbestemming=<reisbestemming>&maxopties=<maxopties>" \n'
    usagestr = usagestr + 'Usage selectdb: -X GET "http://<hostname>[:<port>]/selectdb?reisid=<reisid>'
    return usagestr

# Hotel API. Heeft een aantal opties en bestemming nodig
@app.route("/hotelapi", methods=['GET','POST'])
def hotelreach():
    # aanvragen van variabelen
    if request.method == 'POST':
        maxopties = request.form['maxopties']
        reisbestemming = request.form['reisbestemming']
    else:
        maxopties = request.args.get('maxopties', 5)
        reisbestemming = request.args.get("reisbestemming", "BARCELONA")
    
    # error handeling van de variabelen
    try:
        maxopties = int(maxopties)
    except (ValueError,TypeError):
        return "maxopties moet een getal zijn in de vorm van een integer. \n"
    if maxopties <= 0:
        return "maxopties moet groter zijn dan 0. \n"
    reisbestemming = reisbestemming.upper()
    if reisbestemming in citytocoordinates.keys():
        pass
    else:
        return "Opgeven bestemming staat niet in de dictionary. \n"
    
    # vertalen van de opgegeven stad naar coordinaten
    reiscodlat = str(citytocoordinates[reisbestemming][0])
    reiscodlong = str(citytocoordinates[reisbestemming][1])

    # uitvoering van de hotelapi
    status, hotelresult = hotelapi(maxopties, reiscodlat, reiscodlong)
    hotelresult = json.dumps(hotelresult)
    hotelresult = json.loads(hotelresult)

    response = app.response_class(status=200,mimetype="application/json",response=str(hotelresult))
    if status == 0:
        pass
    elif status == 1:
        return "geen werkende verbinding met hotel API. \n"
    elif status == 2:
        return "geen informatie gevonden met hotel API. \n"
    elif status == 4:
        return "te veel requests, probeer het opnieuw. \n"
    else:
        return "Hotel API is niet werkend. \n"
    return response



# NS API. Heeft vertrekplaats, aankomstplaats en vertrektijd nodig
@app.route("/nsapi", methods=['GET','POST'])
def nsreach():
    # aanvragen van de variabelen
    if request.method == 'POST':
        maxopties = request.form["maxopties"]
        reisvertrek = request.form["reisvertrek"]
        reisvliegveld = request.form["reisvliegveld"]
        tijd = request.form["tijd"]
    else:
        maxopties = request.args.get("maxopties", 5)
        reisvertrek = request.args.get("reisvertrek", "Barendrecht")
        reisvliegveld = request.args.get("reisvliegveld", "Rotterdam_Centraal")
        tijd = request.args.get("tijd", "2021-11-29T16:00:00")
    
    # error handeling van de input
    try:
        maxopties = int(maxopties)
    except (ValueError,TypeError):
        return "maxopties moet een getal zijn in de vorm van een integer. \n"
    if maxopties <= 0:
        return "maxopties moet groter zijn dan 0. \n"
    if reisvliegveld.find("-") != None:
        reisvliegveld = reisvliegveld.replace("-","_")
    else:
        pass
    try:
        tijd = datetime.strptime(tijd,"%Y-%m-%dT%H:%M:%S")
        if tijd < datetime.now():
            return "kan niet in het verleden boeken. \n"
        tijd = str(tijd)
    except (TypeError,ValueError):
        return "tijd moet in format van 'YYYY'-'MM'-'DD'T'HH':'MM':'SS'. \n"
    
    # aanmaken van object trip van classe NsTrip
    nstrip = NsTrip(reisvertrek,reisvliegveld,tijd)
    
    # zetten van opties trip
    status = NsTrip.retrieveTripOptions(nstrip,int(maxopties))
    if status == 0 :
        pass
    elif status == 1:
        return "geen werkende verbinding met NS API. \n"
    elif status == 2:
        return "geen informatie gevonden met NS API. \n"
    elif status == 3:
        return "opgegeven station is niet erkend door de NS API. \n"
    else:
        return "NS API is niet werkend. \n"

    # terugvragen van opties trip van de NS api
    nsresult  = NsTrip.getTripOptions(nstrip)
    nsresult  = json.dumps(nsresult, sort_keys=False)
    nsresult = json.loads(nsresult)
    
    response        = app.response_class(status=200,mimetype="application/json",response=str(nsresult))

    return response

# Skyscanner API. Neemt de informatie van de user en verandert deze voor de informatie naar de andere API's
@app.route("/vluchtapi", methods=['GET','POST'])
def vluchtreach():
    # ontvangen van de variabelen van de user en error handeling hiervan
    if request.method == "POST":
        reispersonen = request.form["reispersonen"]
        maxopties = request.form["maxopties"]
        reisdatumheen = request.form["reisdatumheen"]
        reisdatumterug = request.form["reisdatumterug"]
        reisbestemming = request.form["reisbestemming"]
    else:
        reispersonen = request.args.get("reispersonen", 1)
        maxopties = request.args.get("maxopties", 3)
        reisdatumheen = request.args.get("reisdatumheen", "2022-05-30")
        reisdatumterug = request.args.get("reisdatumterug", "2022-06-02")
        reisbestemming = request.args.get("reisbestemming", "BERLIJN")
    try:
        reispersonen = int(reispersonen)
        maxopties = int(maxopties)
    except (ValueError,TypeError):
        return "maxopties en reispersonen moeten een getal zijn in de vorm van een integer. \n"
    if reispersonen <= 0 or maxopties <= 0:
        return "reispersonen en maxopties moeten groter zijn dan 0. \n"
    elif reispersonen > 10:
        return "kan geen vlucht boeken voor meer dan 10 personen per keer. \n"
    try:
        reisdatumheen = datetime.strptime(reisdatumheen,"%Y-%m-%d")
        reisdatumterug = datetime.strptime(reisdatumterug,"%Y-%m-%d")
        if reisdatumheen < datetime.now() or reisdatumterug < datetime.now():
            return "mag niet in het verleden boeken. \n"
        elif reisdatumterug < reisdatumheen:
            return "datum terug is eerder dan datum heen. \n"
        reisdatumterug = datetime.strftime(reisdatumterug,"%Y-%m-%d")
        reisdatumheen = datetime.strftime(reisdatumheen,"%Y-%m-%d")
    except (TypeError,ValueError):
        return "reisdatumheen en reisdatumterug moeten een datum zijn in het formaat 'YYYY'-'MM'-'DD'. \n"
    reisbestemming = reisbestemming.upper()
    if reisbestemming in citytocoordinates.keys():
        pass
    else:
        return "Opgeven bestemming staat niet in de dictionary. \n"
    reislandbestemming = str(citytocoordinates[reisbestemming][2])
    reisbestemmingvlucht = str(citytocoordinates[reisbestemming][3])
    land = "NL"
    reisvertrek = "AMS"
    
    # contact leggen met de API's via skyscannerAPI.py
    result_heen, error = run_skyscannerAPI(reispersonen, land, reisdatumheen, reisbestemmingvlucht, maxopties, reisvertrek)
    result_terug, error = run_skyscannerAPI(reispersonen, reislandbestemming, reisdatumterug, reisvertrek, maxopties, reisbestemmingvlucht)
    if error == 0:
        pass
    elif error == 1:
        return "geen verbinding met de skyscanner API. \n"
    elif error == 2:
        return "geen informatie uit de skyscanner API verkregen. \n"
    elif error == 3:
        return "skyscanner API heeft een fout gevonden in de input. \n"
    result_heen = json.loads(result_heen)
    result_terug = json.loads(result_terug)

    # resultaten combineren
    resultaat = str(result_heen) + str(result_terug)
    response = app.response_class(status=200,mimetype="application/json",response=resultaat)

    return response

# Combinatie van alle API in sequentie
@app.route("/api", methods=['GET','POST'])
def totalapi():
    # vaststellen van alle parameters
    if request.method == "POST":
        reispersonen = request.form["reispersonen"]
        maxopties = request.form["maxopties"]
        reisdatumheen = request.form["reisdatumheen"]
        reisdatumterug = request.form["reisdatumterug"]
        reisbestemming = request.form["reisbestemming"]
        reisvertrek = request.form["reisvertrek"]
    else:
        reispersonen = request.args.get('reispersonen', 1)
        maxopties = request.args.get('maxopties', 3)
        reisdatumheen = request.args.get('reisdatumheen',"2022-05-30")
        reisdatumterug = request.args.get('reisdatumterug',"2022-06-02")
        reisbestemming = request.args.get('reisbestemming',"BERLIJN")
        reisvertrek = request.args.get('reisvertrek',"Utrecht_Centraal")
    
    # error handeling
    try:
        reispersonen = int(reispersonen)
        maxopties = int(maxopties)
    except (ValueError,TypeError):
        return "maxopties en reispersonen moeten een getal zijn in de vorm van een integer. \n"
    if reispersonen <= 0 or maxopties <= 0:
        return "reispersonen en maxopties moeten groter zijn dan 0. \n"
    elif reispersonen > 50:
        return "kan geen reis boeken voor meer dan 50 personen per keer. \n"
    try:
        reisdatumheen = datetime.strptime(reisdatumheen,"%Y-%m-%d")
        reisdatumterug = datetime.strptime(reisdatumterug,"%Y-%m-%d")
        if reisdatumheen < datetime.now() or reisdatumterug < datetime.now():
            return "mag niet in het verleden boeken. \n"
        reisdatumterug = datetime.strftime(reisdatumterug,"%Y-%m-%d")
        reisdatumheen = datetime.strftime(reisdatumheen,"%Y-%m-%d")
    except (TypeError,ValueError):
        return "reisdatumheen en reisdatumterug moeten een datum zijn in het formaat 'YYYY'-'MM'-'DD'. \n"
    reisbestemming = reisbestemming.upper()
    if reisbestemming in citytocoordinates.keys():
        pass
    else:
        return "Opgeven bestemming staat niet in de dictionary. \n"
    if reisvertrek.find("-") != None:
        reisvliegveld = reisvertrek.replace("-","_")
    else:
        pass
    
    # parameters die we parsen
    reiscodlat = str(citytocoordinates[reisbestemming][0])
    reiscodlong = str(citytocoordinates[reisbestemming][1])
    reisland = str(citytocoordinates[reisbestemming][2])
    reisbestemmingvlucht = str(citytocoordinates[reisbestemming][3])
    reisvliegveld = "Schiphol"

    # aanroepen skyscannerapi
    result_heen, error = run_skyscannerAPI(reispersonen, "NL", reisdatumheen, reisbestemmingvlucht, str(maxopties), "AMS")
    result_terug, error = run_skyscannerAPI(reispersonen, reisland, reisdatumterug, "AMS", str(maxopties), reisbestemmingvlucht)

    if error == 0:
        pass
    elif error == 1:
        return "geen verbinding met de skyscanner API. \n"
    elif error == 2:
        return "geen informatie uit de skyscanner API verkregen. \n"
    elif error == 3:
        return "skyscanner API heeft een fout gevonden in de input. \n"

    result_heen = json.loads(result_heen)
    result_terug = json.loads(result_terug)

    # veranderen van de opgegeven vertrektijd met de nieuwe waarde uit de skyscanner api
    vertrektijd = result_heen["vlucht"][0]["vluchtvertrektijd"]
    aankomsttijd = result_terug["vlucht"][0]["vluchtaankomsttijd"]

    # aanroepen van NSapi voor vertrek
    vertrekdatetime = datetime.strptime(vertrektijd,'%Y-%m-%dT%H:%M:%S')
    vertrekdatetime = vertrekdatetime - timedelta(hours=2)
    vertrektijd = str(vertrekdatetime)
    nstrip = NsTrip(reisvertrek,reisvliegveld,vertrektijd)
    
    # error handeling NS API
    status = NsTrip.retrieveTripOptions(nstrip,int(maxopties))
    if status == 0 :
        pass
    elif status == 1:
        return "geen werkende verbinding met NS API. \n"
    else:
        return "NS API is niet werkend. \n"
    nsresult_heen = NsTrip.getTripOptions(nstrip)
    nsresult_heen = json.dumps(nsresult_heen, sort_keys=False)
    nsresult_heen = json.loads(nsresult_heen)
    
    # aanroepen van NSapi voor terugreis
    aankomstdatetime = datetime.strptime(aankomsttijd,'%Y-%m-%dT%H:%M:%S')
    aankomstdatetime = aankomstdatetime - timedelta(hours=2)
    aankomsttijd = str(aankomstdatetime)
    nstrip = NsTrip(reisvliegveld,reisvertrek,aankomsttijd)

    # error handeling NS API
    status = NsTrip.retrieveTripOptions(nstrip,int(maxopties))
    if status == 0 :
        pass
    elif status == 1:
        return "geen werkende verbinding met NS API. \n"
    elif status == 2:
        return "geen informatie van de NS API gevonden. \n"
    elif status == 3:
        return "opgegeven vertrekstation is niet erkend door de NS API. \n"
    else:
        return "NS API is niet werkend. \n"
    nsresult_terug = NsTrip.getTripOptions(nstrip)
    nsresult_terug = json.dumps(nsresult_terug, sort_keys=False)
    nsresult_terug = json.loads(nsresult_terug)

    # aanroepen van hotelapi
    status, hotelresult = hotelapi(maxopties, reiscodlat, reiscodlong)
    hotelresult = json.dumps(hotelresult)
    hotelresult = json.loads(hotelresult)

    if status == 0:
        pass
    elif status == 1:
        return "geen werkende verbinding met hotel API. \n"
    elif status == 2:
        return "geen informatie gevonden met hotel API. \n"
    elif status == 4:
        return "te veel requests, probeer het opnieuw. \n"
    else:
        return "Hotel API is niet werkend. \n"

    # combineren van resultaten
    resultaat = sorteren(result_heen,nsresult_heen,result_terug,nsresult_terug,hotelresult)
    response = app.response_class(status=200,mimetype="application/json",response=str(resultaat))
    
    op_te_slaan_reis_db = (reisvertrek, reisbestemming, reisvliegveld, reisdatumheen, reisdatumterug, reispersonen)
    db_interactions.insertInformation(conn, resultaat, op_te_slaan_reis_db)
    return response

    
@app.route("/selectdb", methods=['GET','POST'])
def databasereach():
    # aanvragen van variabelen
    if request.method == 'POST':
        reis_id = request.form['reisid']
    else:
        reis_id = request.args.get("reisid")

    #  error handeling van de variabelen
    if reis_id == None:
        return "geen reis_id ingegeven"
    
    #check if reis_id is an int
    try:
        reis_id = eval(reis_id)
    except:
        return "reis_id moet in een integer zijn, bv. /selectdb?reisid=1"

    if type(reis_id) != int:
        return "reis_id moet een integer zijn"

    dataIsFound, data = db_interactions.getDataFromDb(conn, reis_id)

    if dataIsFound == False:
        return "Geen data gevonden for ingegeven reis_id"

    data = json.dumps(data, default=str)
    data = json.loads(data)
    response = app.response_class(status=200,mimetype="application/json",response=str(data))

    return response

def mysql():
    connection, status = db_interactions.sqlConnect()

    return connection, status

conn, st = mysql() 
if st > 0:
    raise SystemExit


app.run(host="0.0.0.0")