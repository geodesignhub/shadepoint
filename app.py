#!/usr/bin/env python3
from flask import Flask, url_for
from flask import render_template

from flask import request, Response
import  json, GeodesignHub
import  config
import  json
import utils
from conn import get_redis
import os



redis = get_redis()

from rq import Queue
from worker import conn

q = Queue(connection=conn)

# Imports

app = Flask(__name__)

@app.route('/', methods = ['GET'])
def home():
	return render_template('home.html')

@app.route('/diagram_shadow', methods = ['GET'])
def api_root():
	''' This is the root of the webservice, upon successful authentication a text will be displayed in the browser '''
	try:
		projectid = request.args.get('projectid')
		apitoken = request.args.get('apitoken')
		diagramid = request.args.get('diagramid')

	except KeyError as e:
		msg = json.dumps({"message":"Could not parse Projectid, Diagram ID or API Token ID. One or more of these were not found in your JSON request."})
		return Response(msg, status=400, mimetype='application/json')

	if projectid and diagramid and apitoken:
		# Initialize the API
		myAPIHelper = GeodesignHub.GeodesignHubClient(url = config.apisettings['serviceurl'], project_id=projectid, token=apitoken)
		# Download Data		
		s = myAPIHelper.get_systems()
		b = myAPIHelper.get_project_bounds()
		d = myAPIHelper.get_diagrams()
		
		# Check responses / data
		try:
			assert r.status_code == 200
		except AssertionError as ae:			
			print("Invalid reponse %s" % ae)
		else:
			finalsynthesis = json.loads(r.text)
			
		try:
			assert s.status_code == 200
		except AssertionError as ae:
			print("Invalid reponse %s" % ae)
		else:
			systems = json.loads(s.text)
			
		try:
			assert d.status_code == 200
		except AssertionError as ae:
			print("Invalid reponse %s" % ae)
		else:
			diagrams = json.loads(d.text)
		# Loop over features and add to corpus and Corpus Dictionary
		myBagofWordsGenerator = utils.BagofWordsGenerator()

		try:
			assert b.status_code == 200
		except AssertionError as ae:
			print("Invalid reponse %s" % ae)
		else:
			bounds = json.loads(b.text)
			bounds = bounds['bounds']

		designdata = {'systems':systems ,'bounds':bounds,'diagrams':diagrams}
		msg = {"status":1,"message":"Data from Geodesignhub retrieved","data":designdata}
		# return Response(msg, status=400, mimetype='application/json')
	else:
	
		msg = {"status":0, "message":"Could not parse Project ID, Diagram ID or API Token ID. One or more of these were not found in your JSON request."}
		# return Response(msg, status=400, mimetype='application/json')

	return render_template('diagram_shadow.html', op = msg)

if __name__ == '__main__':
	app.debug = True
	port = int(os.environ.get("PORT", 5001))
	app.run(port =5001)
