#! /usr/bin/env python
# -*- coding: utf-8 -*-
####################

import indigo

import os
import sys
import datetime
import time
import requests
import json
import uuid
import copy
import io
from copy import deepcopy
from base64 import b64encode

from ghpu import GitHubPluginUpdater

CONTENT_TYPE = "application/json"
DEFAULT_UPDATE_FREQUENCY = 24 # frequency of update check
MAX_RESULTS = 10

emptyEVENT = {
	"eventType": "OCR",
	"txtOCR" : "",
	"txtLabel" : "",
	"txtNotLabel": "",
	"txtLabelScore" : "90", 
	"txtFaceScore" : "90",
	"enableDisable" : "0"
}

################################################################################
class Plugin(indigo.PluginBase):
	########################################
	def __init__(self, pluginId, pluginDisplayName, pluginVersion, pluginPrefs):
		super(Plugin, self).__init__(pluginId, pluginDisplayName, pluginVersion, pluginPrefs)
		self.debug = pluginPrefs.get("chkDebug", False)

		self.updater = GitHubPluginUpdater(self)
		self.updater.checkForUpdate(str(self.pluginVersion))
		self.lastUpdateCheck = datetime.datetime.now()
		self.pollingInterval = 60
		self.APIKey = pluginPrefs["txtAPIKey"]

		self.currentEventN = "0"

		if "EVENTS" in self.pluginPrefs:
			self.EVENTS = json.loads(self.pluginPrefs["EVENTS"])
		else:
			self.EVENTS =  {}


	########################################
	def startup(self):
		self.debugLog(u"startup called")


	def checkForUpdates(self):
		self.updater.checkForUpdate()

	def updatePlugin(self):
		self.updater.update()

	def shutdown(self):
		self.pluginPrefs["EVENTS"] = json.dumps(self.EVENTS)
		self.debugLog(u"shutdown called")

	def deviceStartComm(self, dev):
		self.debugLog(u"deviceStartComm: %s" % (dev.name,))

	########################################
	def validateDeviceConfigUi(self, valuesDict, typeId, devId):
		return (True, valuesDict)

	def updateConfig(self, valuesDict):
		return valuesDict

	def closedPrefsConfigUi(self, valuesDict, userCancelled):
		if not userCancelled:
			self.APIKey = valuesDict["txtAPIKey"]
			self.debug = valuesDict["chkDebug"]

	def eventConfigCallback(self, valuesDict,typeId=""):
		self.currentEventN=str(valuesDict["selectEvent"])

		if self.currentEventN =="0":
			errorDict = valuesDict
			return valuesDict
		
		if not self.currentEventN in self.EVENTS:
			self.EVENTS[self.currentEventN]= copy.deepcopy(emptyEVENT)
	
		valuesDict["eventType"] = str(self.EVENTS[self.currentEventN]["eventType"])
		valuesDict["txtOCR"] = str(self.EVENTS[self.currentEventN]["txtOCR"])
		valuesDict["txtLabel"] = str(self.EVENTS[self.currentEventN]["txtLabel"])
		valuesDict["txtNotLabel"] = str(self.EVENTS[self.currentEventN]["txtNotLabel"])
		valuesDict["txtLabelScore"] = str(self.EVENTS[self.currentEventN]["txtLabelScore"])
		valuesDict["txtFaceScore"]	= str(self.EVENTS[self.currentEventN]["txtFaceScore"])
		valuesDict["enableDisable"] = self.EVENTS[self.currentEventN]["enableDisable"]

		self.updatePrefs =True
		return valuesDict

	def getMenuActionConfigUiValues(self, menuId):
		#indigo.server.log(u'Called getMenuActionConfigUiValues(self, menuId):')
		#indigo.server.log(u'     (' + unicode(menuId) + u')')

		valuesDict = indigo.Dict()
		valuesDict["selectEvent"] = "0"
		valuesDict["eventType"] = "0"
		valuesDict["enableDisable"] = "0"
		errorMsgDict = indigo.Dict()
		return (valuesDict, errorMsgDict)


	def sendImageToGoogleForAnnotation(self, image):
		request = {}
		if image[:4].lower() == "http":
			request = {
					"requests": [
						{
							"image": {
								"source": {
									"imageUri": image
								}
							},
							"features": [
								{
									"type": "FACE_DETECTION",
									"maxResults": MAX_RESULTS
								},
								{
									"type": "LABEL_DETECTION",
									"maxResults": MAX_RESULTS
								},
								{
									"type": "TEXT_DETECTION",
									"maxResults": MAX_RESULTS
								}
							]
						}
					],
				}

		else:
			try:
				with io.open(image, 'rb') as image_file:
					content = image_file.read()
			except:
				self.logger.error("Error opening image to send to Google Vision")
				return

			request = {
					"requests": [
						{
							"image": {
								"content": b64encode(content)
							},
							"features": [
								{
									"type": "FACE_DETECTION",
									"maxResults": MAX_RESULTS
								},
								{
									"type": "LABEL_DETECTION",
									"maxResults": MAX_RESULTS
								},
								{
									"type": "TEXT_DETECTION",
									"maxResults": MAX_RESULTS
								}
							]
						}
					],
				}

		try:
			response = requests.post(
				url="https://vision.googleapis.com/v1/images:annotate?" + "key=" + self.APIKey,
				headers={
					"Content-Type": CONTENT_TYPE
				},
				data=json.dumps(request)
			)
			print('Response HTTP Status Code: {status_code}'.format(
				status_code=response.status_code))
			print('Response HTTP Response Body: {content}'.format(
				content=response.content))
		except requests.exceptions.RequestException:
			print('HTTP Request failed')

		return response.json()

	def sendImageToGoogleVisionAction(self, pluginAction, dev):
		indigo.server.log("sending " + pluginAction.props["location"] + " to Google Vision API")

		if pluginAction.props["locationOption"] == "static":
			image = pluginAction.props["location"]
		else:
			image = indigo.variables[int(pluginAction.props["locationVariable"])].value

		result = self.sendImageToGoogleForAnnotation(image)

		self.logger.debug(json.dumps(result))

		buildstr = ""

		if "labelAnnotations" in result["responses"][0]:
			for lbl in result["responses"][0]["labelAnnotations"]:
				buildstr += lbl["description"] + " (score:" + str(lbl["score"]) +"), "

		indigo.server.log("Label Results: " + buildstr[:-2])
		buildstr = ""

		if "textAnnotations" in result["responses"][0]:
			for ocr in result["responses"][0]["textAnnotations"]:
				if "locale" in ocr:
					buildstr += ocr["description"].replace('\n','') + " (language:" + ocr["locale"] +"), "
				else:
					buildstr += ocr["description"].replace('\n','') + ", "

			indigo.server.log("OCR Results: " + buildstr[:-2])
			buildstr = ""

		if "faceAnnotations" in result["responses"][0]:
			facecounter = 0
			for face in result["responses"][0]["faceAnnotations"]:
				facecounter += 1

				buildstr += "Face " + str(facecounter) + " with confidence of " + str(face["detectionConfidence"]) + ".  "

				buildstr += "joyLikelihood: " + str(face["joyLikelihood"]) + ", "
				buildstr += "sorrowLikelihood: " + str(face["sorrowLikelihood"]) + ", "
				buildstr += "angerLikelihood: " + str(face["angerLikelihood"]) + ", "
				buildstr += "surpriseLikelihood: " + str(face["surpriseLikelihood"]) + ", "
				buildstr += "underExposedLikelihood: " + str(face["underExposedLikelihood"]) + ", "
				buildstr += "blurredLikelihood: " + str(face["blurredLikelihood"]) + ", "
				buildstr += "headwearLikelihood: " + str(face["headwearLikelihood"]) + "; "


			buildstr = "Found a total of " + str(facecounter) + " face(s).  " + buildstr
			indigo.server.log("Face Results: " + buildstr[:-2])
			buildstr = ""


		for trigger in indigo.triggers.iter("self"):
			eventID = trigger.pluginTypeId[5:].strip()
			eventType = self.EVENTS[eventID]["eventType"]

			self.logger.debug("Evaluating trigger '" + trigger.name + "' (eventID: " + eventID + ", eventType: " + eventType + ")")

			if eventType == "OCR":
				ocrSearch = self.EVENTS[eventID]["txtOCR"]

				if "textAnnotations" in result["responses"][0]:
					for ocr in result["responses"][0]["textAnnotations"]:
						if ocrSearch.lower() in ocr["description"].lower():
							indigo.trigger.execute(trigger)
							break

			elif eventType == "Face":
				if "faceAnnotations" in result["responses"][0]:
					facecounter = 0
					for face in result["responses"][0]["faceAnnotations"]:
						if face["detectionConfidence"] >= float(self.EVENTS[eventID]["txtFaceScore"]):
							indigo.trigger.execute(trigger)
							break

			elif eventType == "Label":
				foundLabel = False
				foundNotLabel = False

				if "labelAnnotations" in result["responses"][0]:
					for lbl in result["responses"][0]["labelAnnotations"]:
						for lblSearch in self.EVENTS[eventID]["txtLabel"].split(","):
							if lblSearch == lbl["description"] and lbl["score"] >= float(self.EVENTS[eventID]["txtLabelScore"]):
								foundLabel = True

						for lblNotSearch in self.EVENTS[eventID]["txtNotLabel"].split(","):
							if lblNotSearch == lbl["description"] and lbl["score"] >= float(self.EVENTS[eventID]["txtLabelScore"]):
								foundNotLabel = True
								break

				if foundLabal and not foundNotLabel:
					indigo.trigger.execute(trigger)

########################################
	def buttonConfirmDevicesCALLBACK(self, valuesDict,typeId=""):
		errorDict=indigo.Dict()

		self.currentEventN=str(valuesDict["selectEvent"])

		if self.currentEventN == "0" or  self.currentEventN =="":
			return valuesDict

		if not self.currentEventN in self.EVENTS:
			self.EVENTS[self.currentEventN] = copy.deepcopy(emptyEVENT)

		if valuesDict["DeleteEvent"]:
			valuesDict["DeleteEvent"] = False

			valuesDict["eventType"] = "OCR"
			valuesDict["txtOCR"] = ""
			valuesDict["txtLabel"] = ""
			valuesDict["txtNotLabel"] = ""
			valuesDict["txtLabelScore"] = 0
			valuesDict["txtFaceScore"]	= 0
			valuesDict["enableDisable"] = False

			self.EVENTS[self.currentEventN] = copy.deepcopy(emptyEVENT)
			self.currentEventN ="0"
			valuesDict["selectEvent"] ="0"
			valuesDict["EVENT"] =json.dumps(self.EVENTS)
			return valuesDict

##### not delete
		if valuesDict["enableDisable"]      != "": self.EVENTS[self.currentEventN]["enableDisable"] = valuesDict["enableDisable"]
		else: self.EVENTS[self.currentEventN]["enableDisable"] = emptyEVENT["enableDisable"]; valuesDict["enableDisable"] =  emptyEVENT["enableDisable"];errorDict["enableDisable"]=emptyEVENT["enableDisable"]

		self.EVENTS[self.currentEventN]["eventType"] = valuesDict["eventType"]
		self.EVENTS[self.currentEventN]["txtOCR"] = valuesDict["txtOCR"]
		self.EVENTS[self.currentEventN]["txtLabel"] = valuesDict["txtLabel"]
		self.EVENTS[self.currentEventN]["txtNotLabel"] = valuesDict["txtNotLabel"]
		self.EVENTS[self.currentEventN]["txtFaceScore"] = valuesDict["txtFaceScore"]
		self.EVENTS[self.currentEventN]["enableDisable"] = valuesDict["enableDisable"]

		valuesDict["EVENTS"] = json.dumps(self.EVENTS)

		if len(errorDict) > 0: return  valuesDict, errorDict
		return  valuesDict

