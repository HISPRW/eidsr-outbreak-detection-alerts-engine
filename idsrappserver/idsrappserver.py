#!/usr/bin/env python

import requests
import os
import string
import random
import json
import datetime
import pandas as pd
import numpy as np

import moment
from operator import itemgetter

class IdsrAppServer:
	def __init__(self):
		self.dataStore = "ugxzr_idsr_app"
		self.period = "LAST_7_DAYS"
		self.ALPHABET = '0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'
		self.ID_LENGTH = 11
		self.today = moment.now().format('YYYY-MM-DD')
		print("Epidemic/Outbreak Detection script started on %s" %self.today)

		self.path = os.path.abspath(os.path.dirname(__file__))
		newPath = self.path.split('/')
		newPath.pop(-1)
		newPath.pop(-1)

		self.fileDirectory = '/'.join(newPath)
		self.url = ""
		self.username = ''
		self.password = ''

		# programs
		self.programUid = ''
		self.outbreakProgram = ''


		# TE Attributes
		self.dateOfOnsetUid = ''
		self.conditionOrDiseaseUid = ''
		self.patientStatusOutcome = ''
		self.regPatientStatusOutcome = ''
		self.caseClassification = ''
		self.testResult=''
		self.testResultClassification=''

		self.epidemics = {}

		self.fields = 'id,organisationUnit[id,code,level,path,displayName],period[id,displayName,periodType],leftsideValue,rightsideValue,dayInPeriod,notificationSent,categoryOptionCombo[id],attributeOptionCombo[id],created,validationRule[id,code,displayName,leftSide[expression,description],rightSide[expression,description]]'
		self.eventEndPoint = 'analytics/events/query/'

	# Get Authentication details
	def getAuth(self):
		with open(os.path.join(self.fileDirectory,'.idsr.json'),'r') as jsonfile:
			auth = json.load(jsonfile)
			return auth


	def getIsoWeek(self,d):
		ddate = datetime.datetime.strptime(d,'%Y-%m-%d')
		return datetime.datetime.strftime(ddate, '%YW%W')

	def formatIsoDate(self,d):
		return moment.date(d).format('YYYY-MM-DD')

	def getDateDifference(self,d1,d2):
		if d1 and d2 :
			delta = moment.date(d1) - moment.date(d2)
			return delta.days
		else:
			return ""

	def addDays(self,d1,days):
		if d1:
			newDay = moment.date(d1).add(days=days)
			return newDay.format('YYYY-MM-DD')
		else:
			return ""
	# create aggregate threshold period
	# @param n number of years
	# @param m number of periods
	# @param type seasonal (SEASONAL) or Non-seasonal (NON_SEASONAL) or case based (CASE_BASED)
	def createAggThresholdPeriod(self,m,n,type):
		periods = []
		currentDate = moment.now().format('YYYY-MM-DD')
		currentYear = self.getIsoWeek(currentDate)
		if(type == 'SEASONAL'):

			for year in range(0,n,1):
				currentYDate = moment.date(currentDate).subtract(months=((year +1)*12)).format('YYYY-MM-DD')
				for week in range(0,m,1):
					currentWDate = moment.date(currentYDate).subtract(weeks=week).format('YYYY-MM-DD')
					pe = self.getIsoWeek(currentWDate)
					periods.append(pe)
		elif(type == 'NON_SEASONAL'):
			for week in range(0,(m+1),1):
				currentWDate = moment.date(currentDate).subtract(weeks=week).format('YYYY-MM-DD')
				pe = self.getIsoWeek(currentWDate)
				periods.append(pe)
		else:
			pe = 'LAST_7_DAYS'
			periods.append(pe)
		return periods

	def getHttpData(self,url,fields,username,password,params):
		url = url+fields+".json"
		data = requests.get(url, auth=(username, password),params=params)
		if(data.status_code == 200):
			return data.json()
		else:
			return 'HTTP_ERROR'

	def getHttpDataWithId(self,url,fields,idx,username,password,params):
		url = url + fields + "/"+ idx + ".json"
		data = requests.get(url, auth=(username, password),params=params)

		if(data.status_code == 200):
			return data.json()
		else:
			return 'HTTP_ERROR'

	# Post data
	def postJsonData(self,url,endPoint,username,password,data):
		url = url+endPoint
		submittedData = requests.post(url, auth=(username, password),json=data)
		return submittedData

	# Post data with parameters
	def postJsonDataWithParams(self,url,endPoint,username,password,data,params):
		url = url+endPoint
		submittedData = requests.post(url, auth=(username, password),json=data,params=params)
		return submittedData

	# Update data
	def updateJsonData(self,url,endPoint,username,password,data):
		url = url+endPoint
		submittedData = requests.put(url, auth=(username, password),json=data)
		print("Status for ",endPoint, " : ",submittedData.status_code)
		return submittedData

	# Get array from Object Array

	def getArrayFromObject(self,arrayObject):
		arrayObj = []
		for obj in arrayObject:
			arrayObj.append(obj['id'])
		return arrayObj

	# Check datastore existance

	def checkDataStore(self,url,fields,username,password,params):
		url = url+fields+".json"
		storesValues = {"exists": "false", "stores": []}
		httpData = requests.get(url, auth=(username, password),params=params)
		if(httpData.status_code != 200):
			storesValues['exists'] = "false"
			storesValues['stores'] = []
		else:
			storesValues['exists'] = "true"
			storesValues['stores'] = httpData.json()
		return storesValues

	# Get orgUnit
	def getOrgUnit(self,detectionOu,ous):
		ou = []
		if((ous !='undefined') and len(ous) > 0):
			for oux in ous:
				if(oux['id'] == detectionOu):
					return oux['ancestors']
		else:
			return ou

	# Get orgUnit value
	# @param type = { id,name,code}
	def getOrgUnitValue(self,detectionOu,ous,level,type):
		ou = []
		if((ous !='undefined') and len(ous) > 0):
			for oux in ous:
				if(oux['id'] == detectionOu):
					return oux['ancestors'][level][type]
		else:
			return ou


	# Generate code

	def generateCode(self,row=None,column=None,prefix='',sep=''):
		size = self.ID_LENGTH
		chars = string.ascii_uppercase + string.digits
		code = ''.join(random.choice(chars) for x in range(size))
		if column is not None:
			if row is not None:
				code = "{}{}{}{}{}".format(prefix,sep,row[column],sep,code)
			else:
				code = "{}{}{}{}{}".format(prefix,sep,column,sep,code)
		else:
			code = "{}{}{}".format(prefix,sep,code)
		return code

	def createMessage(self,outbreak=None,usergroups=[],type='EPIDEMIC'):
		message = []
		organisationUnits = []
		if usergroups is None:
			users = []
		if usergroups is not None:
			users = usergroups
		subject = ""
		text = ""

		if type == 'EPIDEMIC':
			subject = outbreak['disease'] + " outbreak in " + outbreak['orgUnitName']
			text = "Dear all," + type.lower() + " threshold for " + outbreak['disease'] + "  is reached at " + outbreak['orgUnitName'] + " of " + outbreak['reportingOrgUnitName']  + " on " + self.today
		elif type == 'ALERT':
			subject = outbreak['disease'] + " alert"
			text = "Dear all, Alert threshold for " + outbreak['disease'] + "  is reached at " + outbreak['orgUnitName'] + " of " + outbreak['reportingOrgUnitName'] + " on " + self.today
		else:
			subject = outbreak['disease'] + " reminder"
			text = "Dear all," + outbreak['disease'] + " outbreak at " + outbreak['orgUnitName'] + " of " + outbreak['reportingOrgUnitName'] + " is closing in 7 days"

		organisationUnits.append({"id": outbreak['orgUnit']})
		organisationUnits.append({"id": outbreak['reportingOrgUnit']})

		message.append(subject)
		message.append(text)
		message.append(users)
		message.append(organisationUnits)

		message = tuple(message)
		return pd.Series(message)

	def sendSmsAndEmailMessage(self,message):
		messageEndPoint = "messageConversations"
		sentMessages = self.postJsonData(self.url,messageEndPoint,self.username,self.password,message)
		print("Message sent: ",sentMessages)
		return sentMessages
		#return 0

	# create alerts data

	def createAlerts(self,userGroup,values,type):

		messageConversations = []
		messages = { "messageConversations": []}
		if type == 'EPIDEMIC':
			for val in values:
				messageConversations.append(self.createMessage(userGroup,val,type))
			messages['messageConversations'] = messageConversations
		elif type == 'ALERT':
			for val in values:
				messageConversations.append(self.createMessage(userGroup,val,type))
			messages['messageConversations'] = messageConversations
		elif type == 'REMINDER':
			for val in values:
				messageConversations.append(self.createMessage(userGroup,val,type))
			messages['messageConversations'] = messageConversations
		else:
			pass

		for message in messageConversations:
			msgSent = self.sendSmsAndEmailMessage(message)
			print("Message Sent status",msgSent)
		return messages

	# create columns from event data
	def createColumns(self,headers,type):
		cols = []
		for header in headers:
			if(type == 'EVENT'):
				if header['name'] == self.dateOfOnsetUid:
					cols.append('onSetDate')
				elif header['name'] == self.conditionOrDiseaseUid:
					cols.append('disease')
				elif header['name'] == self.regPatientStatusOutcome:
					cols.append('immediateOutcome')
				elif header['name'] == self.patientStatusOutcome:
					cols.append('statusOutcome')
				elif header['name'] == self.testResult:
					cols.append('testResult')
				elif header['name'] == self.testResultClassification:
					cols.append('testResultClassification')
				elif header['name'] == self.caseClassification:
					cols.append('caseClassification')
				else:
					cols.append(header['name'])
			elif (type == 'DATES'):
				cols.append(header['name'])
			else:
				cols.append(header['column'])

		return cols
	# Get start and end date
	def getStartEndDates(self,year, week):
		d = moment.date(year,1,1).date
		if(d.weekday() <= 3):
			d = d - datetime.timedelta(d.weekday())
		else:
			d = d + datetime.timedelta(7-d.weekday())
		dlt = datetime.timedelta(days = (week-1)*7)
		return [d + dlt,  d + dlt + datetime.timedelta(days=6)]

	# create Panda Data Frame from event data
	def createDataFrame(self,events,type=None):
		if type is None:
			if events is not None:
				#pd.DataFrame.from_records(events)
				dataFrame = pd.io.json.json_normalize(events)
			else:
				dataFrame = pd.DataFrame()
		else:
			cols = self.createColumns(events['headers'],type)
			dataFrame = pd.DataFrame.from_records(events['rows'],columns=cols)
		return dataFrame

	# Detect using aggregated indicators
	# Confirmed, Deaths,Suspected
	def detectOnAggregateIndicators(self,aggData,diseaseMeta,epidemics,ou,periods,mPeriods,nPeriods):
		dhis2Events = pd.DataFrame()
		detectionLevel = int(diseaseMeta['detectionLevel'])
		reportingLevel = int(diseaseMeta['reportingLevel'])
		m=mPeriods
		n=nPeriods
		if(aggData != 'HTTP_ERROR'):
			if((aggData != 'undefined') and (aggData['rows'] != 'undefined') and len(aggData['rows']) >0):

				df = self.createDataFrame(aggData,'AGGREGATE')
				dfColLength = len(df.columns)
				df1 = df.iloc[:,(detectionLevel+4):dfColLength]
				df.iloc[:,(detectionLevel+4):dfColLength] = df1.apply(pd.to_numeric,errors='coerce').fillna(0).astype(np.int64)
				# print(df.iloc[:,(detectionLevel+4):(detectionLevel+4+m)])	# cases, deaths

				### Make generic functions for math
				if diseaseMeta['epiAlgorithm'] == "NON_SEASONAL":
					# No need to do mean for current cases or deaths
					df['mean_current_cases'] = df.iloc[:,(detectionLevel+4)]
					df['mean_mn_cases'] = df.iloc[:,(detectionLevel+5):(detectionLevel+4+m)].mean(axis=1)
					df['stddev_mn_cases'] = df.iloc[:,(detectionLevel+5):(detectionLevel+4+m)].std(axis=1)
					df['mean20std_mn_cases'] = (df.mean_mn_cases + (2*df.stddev_mn_cases))
					df['mean15std_mn_cases'] = (df.mean_mn_cases + (1.5*df.stddev_mn_cases))

					df['mean_current_deaths'] = df.iloc[:,(detectionLevel+5+m)]
					df['mean_mn_deaths'] = df.iloc[:,(detectionLevel+6+m):(detectionLevel+6+(2*m))].mean(axis=1)
					df['stddev_mn_deaths'] = df.iloc[:,(detectionLevel+6+m):(detectionLevel+6+(2*m))].std(axis=1)
					df['mean20std_mn_deaths'] = (df.mean_mn_deaths + (2*df.stddev_mn_deaths))
					df['mean15std_mn_deaths'] = (df.mean_mn_deaths + (1.5*df.stddev_mn_deaths))
					# periods
					df['period']= periods[0]
					startOfMidPeriod = periods[0].split('W')
					startEndDates = self.getStartEndDates(int(startOfMidPeriod[0]),int(startOfMidPeriod[1]))
					df['dateOfOnSetWeek'] = moment.date(startEndDates[0]).format('YYYY-MM-DD')
					# First case date is the start date of the week where outbreak was detected
					df['firstCaseDate'] = moment.date(startEndDates[0]).format('YYYY-MM-DD')
					# Last case date is the end date of the week boundary.
					df['lastCaseDate'] = moment.date(startEndDates[1]).format('YYYY-MM-DD')
					df['endDate'] = ""
					df['closeDate'] = moment.date(startEndDates[1]).add(days=int(diseaseMeta['incubationDays'])).format('YYYY-MM-DD')

				if diseaseMeta['epiAlgorithm'] == "SEASONAL":
					df['mean_current_cases'] = df.iloc[:,(detectionLevel+4):(detectionLevel+3+m)].mean(axis=1)
					df['mean_mn_cases'] = df.iloc[:,(detectionLevel+3+m):(detectionLevel+3+m+(m*n))].mean(axis=1)
					df['stddev_mn_cases'] = df.iloc[:,(detectionLevel+3+m):(detectionLevel+3+m+(m*n))].std(axis=1)
					df['mean20std_mn_cases'] = (df.mean_mn_cases + (2*df.stddev_mn_cases))
					df['mean15std_mn_cases'] = (df.mean_mn_cases + (1.5*df.stddev_mn_cases))

					df['mean_current_deaths'] = df.iloc[:,(detectionLevel+3+m+(m*n)):(detectionLevel+3+(2*m)+(m*n))].mean(axis=1)
					df['mean_mn_deaths'] = df.iloc[:,(detectionLevel+3+(2*m)+(m*n)):dfColLength-1].mean(axis=1)
					df['stddev_mn_deaths'] = df.iloc[:,(detectionLevel+3+(2*m)+(m*n)):dfColLength-1].std(axis=1)
					df['mean20std_mn_deaths'] = (df.mean_mn_deaths + (2*df.stddev_mn_deaths))
					df['mean15std_mn_deaths'] = (df.mean_mn_deaths + (1.5*df.stddev_mn_deaths))
					# Mid period for seasonal = mean of range(1,(m+1)) where m = number of periods
					midPeriod = int(np.median(range(1,(m+1))))
					df['period']= periods[midPeriod]
					startOfMidPeriod = periods[midPeriod].split('W')
					startEndDates = self.getStartEndDates(int(startOfMidPeriod[0]),int(startOfMidPeriod[1]))
					df['dateOfOnSetWeek'] = moment.date(startEndDates[0]).format('YYYY-MM-DD')
					# First case date is the start date of the week where outbreak was detected
					df['firstCaseDate'] = moment.date(startEndDates[0]).format('YYYY-MM-DD')
					# Last case date is the end date of the week boundary.
					startOfEndPeriod = periods[(m+1)].split('W')
					endDates = moment.date(startEndDates[0] + datetime.timedelta(days=(m-1)*(7/2))).format('YYYY-MM-DD')
					df['lastCaseDate'] = moment.date(startEndDates[0] + datetime.timedelta(days=(m-1)*(7/2))).format('YYYY-MM-DD')
					df['endDate'] = ""
					df['closeDate'] = moment.date(startEndDates[0]).add(days=(m-1)*(7/2)+ int(diseaseMeta['incubationDays'])).format('YYYY-MM-DD')


				df['reportingOrgUnitName'] = df.iloc[:,reportingLevel-1]
				df['reportingOrgUnit'] = df.iloc[:,detectionLevel].apply(self.getOrgUnitValue,args=(ou,(reportingLevel-1),'id'))
				df['orgUnit'] = df.iloc[:,detectionLevel]
				df['orgUnitName'] = df.iloc[:,detectionLevel+1]
				df['orgUnitCode'] = df.iloc[:,detectionLevel+2]
				dropColumns = [col for idx,col in enumerate(df.columns.values.tolist()) if idx > (detectionLevel+4) and idx < (detectionLevel+4+(3*m))]
				df.drop(columns=dropColumns,inplace=True)
				df['confirmedValue'] = df.loc[:,'mean_current_cases']
				df['deathValue'] = df.loc[:,'mean_current_deaths']
				df['suspectedValue'] = df.loc[:,'mean_current_cases']
				df['disease'] = diseaseMeta['disease']
				df['incubationDays'] = diseaseMeta['incubationDays']

				checkEpidemic = "mean_current_cases >= mean20std_mn_cases & mean_current_cases != 0 & mean20std_mn_cases != 0"
				df.query(checkEpidemic,inplace=True)
				if df.empty is True:
					df['alert'] = "false"
				if df.empty is not True:
					df['epidemic'] = 'true'
					# Filter out those greater or equal to threshold
					df = df[df['epidemic'] == 'true']
					df['active'] = "true"
					df['alert'] = "true"
					df['reminder'] = "false"

					#df['epicode']=df['orgUnitCode'].str.cat('E',sep="_")
					df['epicode'] = df.apply(self.generateCode,args=('orgUnitCode','E','_'), axis=1)
					closedQuery = "df['epidemic'] == 'true' && df['active'] == 'true' && df['reminder'] == 'false'"
					closedVigilanceQuery = "df['epidemic'] == 'true' && df['active'] == 'true' && df['reminder'] == 'true'"

					df[['status','active','closeDate','reminderSent','dateReminderSent']] = df.apply(self.getEpidemicDetails,axis=1)
			else:
				# No data for cases found
				pass
			return df
		else:
			print("No outbreaks/epidemics for " + diseaseMeta['disease'])
			return dhis2Events

	# Replace all values with standard text
	def replaceText(self,df):

		df.replace(to_replace='Confirmed case',value='confirmedValue',regex=True,inplace=True)
		df.replace(to_replace='Suspected case',value='suspectedValue',regex=True,inplace=True)
		df.replace(to_replace='Confirmed',value='confirmedValue',regex=True,inplace=True)
		df.replace(to_replace='Suspected',value='suspectedValue',regex=True,inplace=True)
		df.replace(to_replace='confirmed case',value='confirmedValue',regex=True,inplace=True)
		df.replace(to_replace='suspected case',value='suspectedValue',regex=True,inplace=True)
		df.replace(to_replace='died',value='deathValue',regex=True,inplace=True)
		df.replace(to_replace='Died case',value='deathValue',regex=True,inplace=True)
		return df

	# Get Confirmed,suspected cases and deaths
	def getCaseStatus(self,row=None,columns=None,caseType='CONFIRMED'):
		if caseType == 'CONFIRMED':
			# if all(elem in columns.values for elem in ['confirmedValue']):
			if set(['confirmedValue']).issubset(columns.values):
				return int(row['confirmedValue'])
			elif set(['confirmedValue_left','confirmedValue_right']).issubset(columns.values):
				confirmedValue_left = row['confirmedValue_left']
				confirmedValue_right = row['confirmedValue_right']

				confirmedValue_left = confirmedValue_left if row['confirmedValue_left'] is not None else 0
				confirmedValue_right = confirmedValue_right if row['confirmedValue_right'] is not None else 0
				if confirmedValue_left <= confirmedValue_right:
					return confirmedValue_right
				else:
					return confirmedValue_left
			else:
				return 0
		elif caseType == 'SUSPECTED':
			if set(['suspectedValue','confirmedValue']).issubset(columns.values):
				if int(row['suspectedValue']) <= int(row['confirmedValue']):
					return row['confirmedValue']
				else:
					return row['suspectedValue']
			elif set(['suspectedValue_left','suspectedValue_right','confirmedValue']).issubset(columns.values):
				suspectedValue_left = row['suspectedValue_left']
				suspectedValue_right = row['suspectedValue_right']

				suspectedValue_left = suspectedValue_left if row['suspectedValue_left'] is not None else 0
				suspectedValue_right = suspectedValue_right if row['suspectedValue_right'] is not None else 0
				if (suspectedValue_left <= row['confirmedValue']) and (suspectedValue_right <= suspectedValue_left):
					return row['confirmedValue']
				elif (suspectedValue_left <= suspectedValue_right) and (row['confirmedValue'] <= suspectedValue_left):
					return suspectedValue_right
				else:
					return suspectedValue_left
			else:
				return 0
		elif caseType == 'DEATH':
			if set(['deathValue_left','deathValue_right']).issubset(columns.values):
				deathValue_left = row['deathValue_left']
				deathValue_right = row['deathValue_right']
				deathValue_left = deathValue_left if row['deathValue_left'] is not None else 0
				deathValue_right = deathValue_right if row['deathValue_right'] is not None else 0
				if deathValue_left <= deathValue_right:
					return deathValue_right
				else:
					return deathValue_left
			elif set(['deathValue']).issubset(columns.values):
				return row['deathValue']
			else:
				return 0

	# Check if epedimic is active or ended
	def getStatus(self,row=None,status=None):
		currentStatus = 'false'
		if status == 'active':
			if pd.to_datetime(self.today) < pd.to_datetime(row['endDate']):
				currentStatus='active'
			elif pd.to_datetime(row['endDate']) == (pd.to_datetime(self.today)):
				currentStatus='true'
			else:
				currentStatus='false'
		elif status == 'reminder':
			if row['reminderDate'] == pd.to_datetime(self.today):
				currentStatus='true'
			else:
				currentStatus='false'
		return pd.Series(currentStatus)
	# get onset date
	def getOnSetDate(self,row):
		if row['eventdate'] == '':
			return row['onSetDate']
		else:
			return moment.date(row['eventdate']).format('YYYY-MM-DD')
	# Get onset for TrackedEntityInstances
	def getTeiOnSetDate(self,row):
		if row['dateOfOnSet'] == '':
			return row['dateOfOnSet']
		else:
			return moment.date(row['created']).format('YYYY-MM-DD')


	# replace data of onset with event dates
	def replaceDatesWithEventData(self,row):

		if row['onSetDate'] == '':
			return pd.to_datetime(row['eventdate'])
		else:
			return pd.to_datetime(row['onSetDate'])

	# Get columns based on query or condition
	def getQueryValue(self,df,query,column,inplace=True):
		query = "{}={}".format(column,query)
		df.eval(query,inplace)
		return df
	# Get columns based on query or condition
	def queryValue(self,df,query,column=None,inplace=True):
		df.query(query)
		return df
	# Get epidemic, closure and status
	def getEpidemicDetails(self,row,columns=None):
		details = []
		if row['epidemic'] == "true" and row['active'] == "true" and row['reminder'] == "false":
		 	details.append('Closed')
		 	details.append('false')
		 	details.append(self.today)
		 	details.append('false')
		 	details.append('')
		 	# Send closure message

		elif row['epidemic'] == "true" and row['active'] == "true" and row['reminder'] == "true":
			details.append('Closed Vigilance')
			details.append('true')
			details.append(row['closeDate'])
			details.append('true')
			details.append(self.today)
			# Send Reminder for closure
		else:
			details.append('Confirmed')
			details.append('true')
			details.append('')
			details.append('false')
			details.append('')
		detailsSeries = tuple(details)
		return pd.Series(detailsSeries)

	# Get key id from dataelements
	def getDataElement(self,dataElements,key):
		for de in dataElements:
			if de['name'] == key:
				return de['id']
			else:
				pass


	# detect self.epidemics
	# Confirmed, Deaths,Suspected
	def detectBasedOnProgramIndicators(self,caseEvents,diseaseMeta,orgUnits,type,dateData):
		dhis2Events = pd.DataFrame()
		detectionLevel = int(diseaseMeta['detectionLevel'])
		reportingLevel = int(diseaseMeta['reportingLevel'])
		if(caseEvents != 'HTTP_ERROR'):
			if((caseEvents != 'undefined') and (caseEvents['rows'] != 'undefined') and caseEvents['height'] >0):
				df = self.createDataFrame(caseEvents,type)

				caseEventsColumnsById = df.columns
				dfColLength = len(df.columns)

				if(type =='EVENT'):
					# If date of onset is null, use eventdate
					#df['dateOfOnSet'] = np.where(df['onSetDate']== '',pd.to_datetime(df['eventdate']).dt.strftime('%Y-%m-%d'),df['onSetDate'])
					df['dateOfOnSet'] = df.apply(self.getOnSetDate,axis=1)
					# Replace all text with standard text

					df = self.replaceText(df)

					# Transpose and Aggregate values

					dfCaseClassification = df.groupby(['ouname','ou','disease','dateOfOnSet'])['caseClassification'].value_counts().unstack().fillna(0).reset_index()

					dfCaseImmediateOutcome = df.groupby(['ouname','ou','disease','dateOfOnSet'])['immediateOutcome'].value_counts().unstack().fillna(0).reset_index()

					dfTestResult = df.groupby(['ouname','ou','disease','dateOfOnSet'])['testResult'].value_counts().unstack().fillna(0).reset_index()

					dfTestResultClassification = df.groupby(['ouname','ou','disease','dateOfOnSet'])['testResultClassification'].value_counts().unstack().fillna(0).reset_index()

					dfStatusOutcome = df.groupby(['ouname','ou','disease','dateOfOnSet'])['statusOutcome'].value_counts().unstack().fillna(0).reset_index()

					combinedDf = pd.merge(dfCaseClassification,dfCaseImmediateOutcome,on=['ou','ouname','disease','dateOfOnSet'],how='left').merge(dfTestResultClassification,on=['ou','ouname','disease','dateOfOnSet'],how='left').merge(dfTestResult,on=['ou','ouname','disease','dateOfOnSet'],how='left').merge(dfStatusOutcome,on=['ou','ouname','disease','dateOfOnSet'],how='left')
					combinedDf.sort_values(['ouname','disease','dateOfOnSet'],ascending=[True,True,True])
					combinedDf['dateOfOnSetWeek'] = pd.to_datetime(combinedDf['dateOfOnSet']).dt.strftime('%YW%V')
					combinedDf['confirmedValue'] = combinedDf.apply(self.getCaseStatus,args=(combinedDf.columns,'CONFIRMED'),axis=1)
					combinedDf['suspectedValue'] = combinedDf.apply(self.getCaseStatus,args=(combinedDf.columns,'SUSPECTED'),axis=1)

					#combinedDf['deathValue'] = combinedDf.apply(self.getCaseStatus,args=(combinedDf.columns,'DEATH'),axis=1)

					dfConfirmed = combinedDf.groupby(['ouname','ou','disease','dateOfOnSetWeek'])['confirmedValue'].agg(['sum']).reset_index()

					dfConfirmed.rename(columns={'sum':'confirmedValue' },inplace=True)
					dfSuspected = combinedDf.groupby(['ouname','ou','disease','dateOfOnSetWeek'])['suspectedValue'].agg(['sum']).reset_index()
					dfSuspected.rename(columns={'sum':'suspectedValue' },inplace=True)
					dfFirstAndLastCaseDate = df.groupby(['ouname','ou','disease'])['dateOfOnSet'].agg(['min','max']).reset_index()
					dfFirstAndLastCaseDate.rename(columns={'min':'firstCaseDate','max':'lastCaseDate'},inplace=True)

					aggDf = pd.merge(dfConfirmed,dfSuspected,on=['ouname','ou','disease','dateOfOnSetWeek'],how='left').merge(dfFirstAndLastCaseDate,on=['ouname','ou','disease'],how='left')
					aggDf['reportingOrgUnitName'] = aggDf.loc[:,'ou'].apply(self.getOrgUnitValue,args=(orgUnits,(reportingLevel-1),'name'))
					aggDf['reportingOrgUnit'] = aggDf.loc[:,'ou'].apply(self.getOrgUnitValue,args=(orgUnits,(reportingLevel-1),'id'))
					aggDf['incubationDays'] = int(diseaseMeta['incubationDays'])
					aggDf['endDate'] = pd.to_datetime(pd.to_datetime(dfDates['lastCaseDate']) + pd.to_timedelta(pd.np.ceil(2*aggDf['incubationDays']), unit="D")).dt.strftime('%Y-%m-%d')
					aggDf['reminderDate'] = pd.to_datetime(pd.to_datetime(aggDf['lastCaseDate']) + pd.to_timedelta(pd.np.ceil(2*aggDf['incubationDays']-7), unit="D")).dt.strftime('%Y-%m-%d')
					aggDf.rename(columns={'ouname':'orgUnitName','ou':'orgUnit'},inplace=True);
					aggDf[['active']] =  aggDf.apply(self.getStatus,args=['active'],axis=1)
					aggDf[['reminder']] =  aggDf.apply(self.getStatus,args=['reminder'],axis=1)

				else:
					df1 = df.iloc[:,(detectionLevel+4):dfColLength]
					df.iloc[:,(detectionLevel+4):dfColLength] = df1.apply(pd.to_numeric,errors='coerce').fillna(0).astype(np.int64)
					if(dateData['height'] > 0):
						dfDates = self.createDataFrame(dateData,'DATES')
						dfDates.to_csv('aggDfDates.csv',encoding='utf-8')
						dfDates.rename(columns={dfDates.columns[7]:'disease',dfDates.columns[8]:'dateOfOnSet'},inplace=True)
						dfDates['dateOfOnSet'] = dfDates.apply(self.getTeiOnSetDate,axis=1)
						dfDates = dfDates.groupby(['ou','disease'])['dateOfOnSet'].agg(['min','max']).reset_index()
						dfDates.rename(columns={'min':'firstCaseDate','max':'lastCaseDate'},inplace=True)
						df = pd.merge(df,dfDates,right_on=['ou'],left_on=['organisationunitid'],how='left')
						df['incubationDays'] = int(diseaseMeta['incubationDays'])
						df['endDate'] = pd.to_datetime(pd.to_datetime(df['lastCaseDate']) + pd.to_timedelta(pd.np.ceil(2*df['incubationDays']), unit="D")).dt.strftime('%Y-%m-%d')
						df['reminderDate'] = pd.to_datetime(pd.to_datetime(df['lastCaseDate']) + pd.to_timedelta(pd.np.ceil(2*df['incubationDays']-7), unit="D")).dt.strftime('%Y-%m-%d')
						df.dropna(subset=['disease'],inplace=True)

						df[['active']] =  df.apply(self.getStatus,args=['active'],axis=1)
						df[['reminder']] =  df.apply(self.getStatus,args=['reminder'],axis=1)


					else:
						pass
					df.rename(columns={df.columns[10]:'confirmedValue' },inplace=True)
					df.rename(columns={df.columns[11]:'deathValue' },inplace=True)
					df.rename(columns={df.columns[12]:'suspectedValue' },inplace=True)
					df['reportingOrgUnitName'] = df.iloc[:,reportingLevel-1]
					df['reportingOrgUnit'] = df.loc[:,'organisationunitid'].apply(self.getOrgUnitValue,args=(orgUnits,(reportingLevel-1),'id'))
					df.rename(columns={'organisationunitname':'orgUnitName','organisationunitid':'orgUnit'},inplace=True);
					df['dateOfOnSetWeek'] = self.getIsoWeek(self.today)
					df["period"]= df['dateOfOnSetWeek']
					#df['disease'] = diseaseMeta['disease']
					aggDf = df

				aggDf['alertThreshold'] = int(diseaseMeta['alertThreshold'])
				aggDf['epiThreshold'] = int(diseaseMeta['epiThreshold'])

				#df['confirmed_suspected_cases'] = df[['confirmedValue','suspectedValue']].sum(axis=1)

				aggDf['epidemic'] = np.where(aggDf['confirmedValue'] >= aggDf['epiThreshold'],'true','false')

				alertQuery = (aggDf['confirmedValue'] < aggDf['epiThreshold']) & (aggDf['suspectedValue'].astype(np.int64) >= aggDf['alertThreshold'].astype(np.int64)) & (aggDf['endDate'] > self.today)
				aggDf['alert'] = np.where(alertQuery,'true','false')
				aggDf.to_csv('aggDf.csv',encoding='utf-8')
				return aggDf
			else:
				# No data for cases found
				pass
				return dhis2Events
		else:
			print("No outbreaks/epidemics for " + diseaseMeta['disease'])
			return dhis2Events

	# Transform updated to DHIS2 JSON events format
	# @param dataFrame df
	# @return dhis2Events object { 'events', 'datastore Events'}
	def createEventDatavalues(self,row=None,config=None,columns=None):
		dataElements = config
		event = []
		for key in columns.values: # for key in [*row]
			if key == 'suspectedValue':
		 		event.append({'dataElement': self.getDataElement(dataElements,'suspected'),'value':row['suspectedValue']})
			elif key == 'deathValue':
		 		event.append({'dataElement': self.getDataElement(dataElements,'deaths'),'value':row['deathValue']})
			elif key == 'confirmedValue':
		 		event.append({'dataElement': self.getDataElement(dataElements,'confirmed'),'value':row['confirmedValue']})
			elif key == 'firstCaseDate':
			 	event.append({'dataElement': self.getDataElement(dataElements,'firstCaseDate'),'value':row['firstCaseDate']})
			elif key == 'orgUnit':
			 	event.append({'dataElement': self.getDataElement(dataElements,'origin'),'value':row['orgUnit']})
			 	event.append({'dataElement': self.getDataElement(dataElements,'outbreakId'),'value':row['epicode']})
			elif key == 'disease':
			 	event.append({'dataElement': self.getDataElement(dataElements,'disease'),'value':row['disease']})
			elif key == 'endDate':
			 	event.append({'dataElement': self.getDataElement(dataElements,'endDate'),'value':row['endDate']})
			elif key == 'status':
			 	event.append({'dataElement': self.getDataElement(dataElements,'status'),'value':row['status']})
			else:
			 	pass
		#### Check epidemic closure
		if hasattr(row,'closeDate'):
			if(row['closeDate']) == self.today and row['status']=='Closed':
				event.append({'dataElement': key,'value':'Closed'})
				# Send closure message

		elif hasattr(row,'dateReminderSent'):
			if row['dateReminderSent']==self.today and row['status']== 'Closed Vigilance':
		 		event.append({'dataElement': key,'value':'Closed Vigilance'})
			# Send Reminder for closure
		else:
			pass
		return event
	# Replace existing outbreak code in the new epidemics for tracking
	'''
	check is the column to track e.g outbreak code
	keys is the columns to use as keys and must be a list
	row is the row in the dataFrame
	append is the column to use as a append column
	df is the dataframe to compare with
	'''
	def trackEpidemics(self,row=None,df=None,check=None,keys=None,append=None):
		if row is not None:
			# filter by keys and not closed
			query = ['{}{}{}{}'.format(key,' in "',row[key],'"') for key in keys]
			query = ' and '.join(query)
			query = '{}{}'.format(query,' and closeDate == ""')
			if df.empty:
				return self.generateCode(prefix='E',sep='_')
			else:
				filteredDf = df.query(query).sort_values(keys,inplace=True)
				if filteredDf is None:
					return self.generateCode(column=row[append],prefix='E',sep='_')
				else:
					checked =  [filteredDf.at[index,check] for index in filteredDf.index]
					if len(checked) > 0:
						row[check] = checked[0]
					else:
						row[check] = self.generateCode(column=row[append],prefix='E',sep='_')
					return row[check]
		else:
			return self.generateCode(prefix='E',sep='_')


	# Remove existing  and update with new from data store epidemics
	# Support meta data mapping format [{epiKey1:eventKey1},{epiKey2:eventKey2}] e.g [{'confirmedValue':'confirmedValue'},{'status':'status'}]
	# epidemics and events are dataframe
	def getDfUpdatedEpidemics(self,epidemics,events,mergeColumns=None,how='inner',track=False,epidemic=True):

		if epidemics.empty and events.empty == False:
			return events
		if epidemics.empty == False and events.empty:
			return epidemics
		else:
			if mergeColumns is not None:
				mergedDf=epidemics.merge(events,how=how,on=mergeColumns,suffixes=('_left','_right'),indicator=track)
				if epidemic:
					mergedDf['updated']= np.where(mergedDf["endDate"] == '',True,False)
					mergedDf['epitype']= np.where(mergedDf["endDate"] == '',"new","old")
					#epidemics['reminderSent']=np.where(epidemics['dateReminderSent'] == self.today, True,False)
					#epidemics['dateReminderSent']=np.where(epidemics["reminderDate"] == self.today, self.today,'')
					#epidemics['reminder']=np.where(epidemics["reminderDate"] == self.today, True,False)
					mergedDf['active']=np.where(pd.to_datetime(self.today) < pd.to_datetime(mergedDf["endDate"]),True,False)
			else:
				pass
			return mergedDf
		return epidemics

	def getRootOrgUnit(self):
		root = {};
		root = self.getHttpData(self.url,'organisationUnits',self.username,self.password,params={"paging":"false","filter":"level:eq:1"})
		return root['organisationUnits']
	# Drop columns
	def dropColumns(self,df=None,columns=None):
		if columns is not None:
			deleteColumns = [column for column in columns if column in df]
		else:
			deleteColumns =[]
		return deleteColumns
	# Get epidemics
	def getEpidemics(self,programConfig=None,detectedAggEpidemics=None,detectedMergedAlertsMessage=None,dfEpidemics=None,messageColumns=None,alertColumns=None,type='EPIDEMIC',notify=None):
		# New epidemics only
		newEpidemics = pd.DataFrame()
		# updated epidemics only
		updatedEpidemics = pd.DataFrame()
		# Existing epidemics only
		existsEpidemics = pd.DataFrame()
		if dfEpidemics.empty is not True:
			dfEpidemics['period'] =pd.to_datetime(dfEpidemics['firstCaseDate']).dt.strftime('%YW%V')
		if detectedAggEpidemics.empty:
			print("Nothing to update or detect. Proceeding to next disease")
			return
		allAggEpidemics = self.getDfUpdatedEpidemics(dfEpidemics,detectedAggEpidemics,mergeColumns=['orgUnit','disease','period'],how='outer',track=True,epidemic=False)
		remindersQuery = "{}{}{}'".format("reminderDate", "=='", self.today)
		# New epidemics
		if '_merge' in allAggEpidemics.columns:
			newEpidemics = allAggEpidemics.query("_merge == 'right_only'")
			newEpidemics.drop(list(newEpidemics.filter(regex = '_left')), axis = 1, inplace = True)
			newEpidemics.columns = newEpidemics.columns.str.replace('_right', '')
			# Existing epidemics and not updated
			existsEpidemics = allAggEpidemics.query("_merge == 'left_only'")
			existsEpidemics.drop(list(existsEpidemics.filter(regex = '_right')), axis = 1, inplace = True)
			existsEpidemics.columns = existsEpidemics.columns.str.replace('_left', '')
			# Updated epidemics
			updatedEpidemics =allAggEpidemics.query("_merge == 'both'")
			# Drop duplicated columns
			newEpidemics = newEpidemics.loc[:,~newEpidemics.columns.duplicated()]
			updatedEpidemics = updatedEpidemics.loc[:,~updatedEpidemics.columns.duplicated()]
			existsEpidemics = existsEpidemics.loc[:,~existsEpidemics.columns.duplicated()]
		if '_merge' not in allAggEpidemics.columns:
			newEpidemics = allAggEpidemics


		print("Number of New Epidemics ", len(newEpidemics.index))
		if( len(newEpidemics.index) > 0):
			epiCodesFields = "system/id"
			epiCodesParams = { "limit" : len(newEpidemics.index) }

			epiCodes = self.getHttpData(self.url,epiCodesFields,self.username,self.password,params=epiCodesParams)
			if(epiCodes != 'HTTP_ERROR'):
				epiCodesUids = epiCodes['codes']
				newEpidemics['event'] = epiCodesUids
			else:
				print("Failed to generated DHIS2 UID codes")
		else:
			print("Exiting no new outbreaks detected")
		print("Detecting and updating Outbreaks .... ")
		config =programConfig['reportingProgram']['programStage']['dataElements']
		if updatedEpidemics.empty is True:
			if type == 'EPIDEMIC':
				updatedEpidemics['dataValues'] = []
			else:
				pass
		if updatedEpidemics.empty is not True:
			if type == 'EPIDEMIC':
				updatedEpidemics['confirmedValue']= updatedEpidemics.apply(self.getCaseStatus,args=(updatedEpidemics.columns,'CONFIRMED'),axis=1)
				updatedEpidemics['suspectedValue']=updatedEpidemics.apply(self.getCaseStatus,args=(updatedEpidemics.columns,'SUSPECTED'),axis=1)
				updatedEpidemics['deathValue']=updatedEpidemics.apply(self.getCaseStatus,args=(updatedEpidemics.columns,'DEATH'),axis=1)
				updatedEpidemics.drop(list(updatedEpidemics.filter(regex = '_right')), axis = 1, inplace = True)
				deleteColumns = self.dropColumns(df=updatedEpidemics.columns,columns=['confirmedValue_left','suspectedValue_left','deathValue_left'])
				updatedEpidemics.drop(columns=deleteColumns,inplace=True)
				updatedEpidemics.columns = updatedEpidemics.columns.str.replace('_left', '')
				updatedEpidemics['dataValues'] = updatedEpidemics.apply( self.createEventDatavalues,args=(config,updatedEpidemics.columns),axis=1);
			else:
				pass

		if newEpidemics.empty is True:
			if type == 'EPIDEMIC':
				newEpidemics['dataValues'] = []
			else:
				pass
		if newEpidemics.empty is not True:
			if type == 'EPIDEMIC':
				newEpidemics.loc[:,'eventDate'] = newEpidemics['firstCaseDate']
				newEpidemics.loc[:,'status'] = 'COMPLETED'
				newEpidemics.loc[:,'program'] = str(programConfig['reportingProgram']['id'])
				newEpidemics.loc[:,'programStage'] = str(programConfig['reportingProgram']['programStage']['id'])
				newEpidemics.loc[:,'storedBy'] = 'idsr'
				newEpidemics['epicode']=newEpidemics.apply(self.trackEpidemics,args=(dfEpidemics,'epicode',['disease','orgUnit'],'orgUnitCode'),axis=1)
				newEpidemics['dataValues'] = newEpidemics.apply( self.createEventDatavalues,args=(config,newEpidemics.columns),axis=1)
				#newEpidemics = newEpidemics.loc[:,~newEpidemics.columns.duplicated()]
				detectedNewEpidemicsAlertsMessage = newEpidemics.filter(alertColumns)
				detectedNewEpidemicsAlertsMessage[messageColumns] = detectedNewEpidemicsAlertsMessage.apply(self.createMessage,args=(notify,'EPIDEMIC'),axis=1)
			else:
				#newEpidemics = newEpidemics.loc[:,~newEpidemics.columns.duplicated()]
				detectedNewEpidemicsAlertsMessage = newEpidemics.filter(alertColumns)
				detectedNewEpidemicsAlertsMessage[messageColumns] = detectedNewEpidemicsAlertsMessage.apply(self.createMessage,args=(notify,'ALERT'),axis=1)
			#mergedAlerts = pd.concat([detectedNewEpidemicsAlerts],sort=False)
			detectedMergedAlertsMessage = detectedMergedAlertsMessage.append(detectedNewEpidemicsAlertsMessage)
		# Merge updated, new and existing epidemics
		mergedEpidemics = pd.concat([existsEpidemics,updatedEpidemics,newEpidemics],sort=False)
		return [mergedEpidemics,detectedMergedAlertsMessage]

	def iterateDiseases(self,diseasesMeta,epidemics,alerts,type):
		newUpdatedEpis = []
		existingAlerts = alerts
		existingEpidemics = epidemics
		programConfig = diseasesMeta['config']
		mPeriods = programConfig['mPeriods']
		nPeriods = programConfig['nPeriods']
		rootOrgUnit = self.getRootOrgUnit()
		programStartDate = moment.date(self.today).subtract(days=8)
		programStartDate = moment.date(programStartDate).format('YYYY-MM-DD')
		# Epidemics in the datastore
		dfEpidemics = self.createDataFrame(epidemics)
		# Alerts in the datastore
		dfAlerts = self.createDataFrame(alerts)
		# New epidemics only
		detectedNewEpidemics = pd.DataFrame()
		# updated epidemics only
		detectedUpdatedEpidemics = pd.DataFrame()
		# Existing epidemics only
		detectedExistingEpidemics = pd.DataFrame()
		# Combine Existing,new and updated epidemics
		detectedMergedEpidemics = pd.DataFrame()
		# Combine Existing,new and updated alerts
		detectedMergedAlerts = pd.DataFrame()
		# New alerts messages
		detectedMergedAlertsMessage = pd.DataFrame()
		alertColumns = ['disease','orgUnit','orgUnitName','reportingOrgUnit','reportingOrgUnitName','confirmedValue','deathValue','suspectedValue','event','period','lastCaseDate','firstCaseDate','epicode','epidemic','alert','status']
		messageColumns = ['subject','text','users','organisationUnits']

		for diseaseMeta in diseasesMeta['diseases']:

			ouLevel = 'LEVEL-' + str(diseaseMeta['detectionLevel'])
			detectionXLevel = diseaseMeta['detectionLevel']
			ouFields = 'organisationUnits'
			ouParams = {"fields": "id,code,ancestors[id,code,name]","paging":"false","filter":"level:eq:"+ str(detectionXLevel)}
			epiReportingOrgUnit	= self.getHttpData(self.url,ouFields,self.username,self.password,params=ouParams)
			piSeparator =';'
			piIndicatorsArray = self.getArrayFromObject(diseaseMeta['programIndicators'])
			piIndicators = piSeparator.join(piIndicatorsArray)
			piFields = 'analytics'
			notifyUser = diseaseMeta['notifiableUserGroups']
			if diseaseMeta['epiAlgorithm'] == "CASE_BASED":
				print("Detecting for case based diseases")
				print ("Start outbreak detection for %s" %diseaseMeta['disease'])
				#LAST_7_DAYS

				eventsFields = 'analytics/events/query/' + self.programUid
				piFields = 'analytics'
				teiFields = 'trackedEntityInstances/query'
				# Get first case date: min and max is always the last case date registered
				### Get Cases or Disease Events
				#
				caseEventParams = { "dimension": ['pe:' + self.period,'ou:' + ouLevel,self.dateOfOnsetUid,self.conditionOrDiseaseUid + ":IN:" + diseaseMeta["code"],self.patientStatusOutcome,self.regPatientStatusOutcome,self.caseClassification,self.testResult,self.testResultClassification],"displayProperty":"NAME"}
				piEventParams = {"dimension": ["dx:"+ piIndicators,"ou:" + ouLevel],"filter": "pe:" + self.period,"displayProperty":"NAME","columns":"dx","rows":"ou","skipMeta":"false","hideEmptyRows":"true","skipRounding":"false","showHierarchy":"true"}

				cDisease = programConfig["notificationProgram"]["disease"]["id"]+":IN:" + diseaseMeta["code"]
				cOnset = programConfig["notificationProgram"]["dateOfOnSet"]["id"]
				rootOrgUnitId = rootOrgUnit[0]["id"]

				teiParams = {"ou":rootOrgUnitId,"program":self.programUid,"ouMode":"DESCENDANTS","programStatus":"ACTIVE","attribute": [cDisease,cOnset] ,"programStartDate":programStartDate,"skipPaging":"true"}

				if(type =='EVENT'):
					caseEvents = self.getHttpData(self.url,eventsFields,self.username,self.password,params=caseEventParams)
				if(type =='ANALYTICS'):
					caseEvents = self.getHttpData(self.url,piFields,self.username,self.password,params=piEventParams)
				if(( caseEvents != 'HTTP_ERROR') and (epiReportingOrgUnit != 'HTTP_ERROR')):
					orgUnits = epiReportingOrgUnit['organisationUnits']
					dateData = self.getHttpData(self.url,teiFields,self.username,self.password,params=teiParams)
					detectedAggEpidemics = self.detectBasedOnProgramIndicators(caseEvents,diseaseMeta,orgUnits,type,dateData)
					detectedAggAlerts = self.queryValue(detectedAggEpidemics,"alert == 'true'")
					# Creating epidemics alerts
					mergedAlerts =self.getEpidemics(programConfig=programConfig,detectedAggEpidemics=detectedAggAlerts,detectedMergedAlertsMessage=detectedMergedAlertsMessage,dfEpidemics=dfAlerts,messageColumns=messageColumns,alertColumns=alertColumns,type='ALERT',notify=notifyUser)
					if mergedAlerts is None:
						return
					detectedMergedAlertsMessage = mergedAlerts[1]
					detectedMergedAlerts =  detectedMergedAlerts.append(mergedAlerts[0])
					# Creating threshold alerts
					mergedEpidemics =self.getEpidemics(programConfig=programConfig,detectedAggEpidemics=detectedAggEpidemics,detectedMergedAlertsMessage=detectedMergedAlertsMessage,dfEpidemics=dfEpidemics,messageColumns=messageColumns,alertColumns=alertColumns,notify=notifyUser)
					if mergedEpidemics is None:
						return
					detectedMergedEpidemics = detectedMergedEpidemics.append(mergedEpidemics[0])
					detectedMergedAlertsMessage = mergedEpidemics[1]
					print ("Finished creating Outbreaks for %s" %diseaseMeta['disease'])
					# Reminders
					#reminders = self.queryValue(allAggEpidemics,remindersQuery)

				else:
					print("Failed to retrieve case events from analytics")

			elif diseaseMeta['epiAlgorithm'] == "SEASONAL":
				print("Detecting for seasonal")
				print ("Start outbreak detection for %s" %diseaseMeta['disease'])
				# periods are aggregate generated
				aggPeriod = self.createAggThresholdPeriod(mPeriods,nPeriods,'SEASONAL')
				aggPeriods = piSeparator.join(aggPeriod)

				aggParams = {"dimension": ["dx:"+ piIndicators,"ou:" + ouLevel,"pe:" + aggPeriods],"displayProperty":"NAME","tableLayout":"true","columns":"dx;pe","rows":"ou","skipMeta":"false","hideEmptyRows":"true","skipRounding":"false","showHierarchy":"true"}

				aggIndicators = self.getHttpData(self.url,piFields,self.username,self.password,params=aggParams)

				if(( aggIndicators != 'HTTP_ERROR') and (epiReportingOrgUnit != 'HTTP_ERROR')):
					aggData = aggIndicators
					aggOrgUnit = epiReportingOrgUnit['organisationUnits']
					detectedAggEpidemics = self.detectOnAggregateIndicators(aggData,diseaseMeta,epidemics,aggOrgUnit,aggPeriod,mPeriods,nPeriods)
					detectedAggEpidemics.to_csv('detectedAggEpidemics.csv',encoding='utf-8')
					detectedAggAlerts = self.queryValue(detectedAggEpidemics,"alert == 'true'")
					# Creating epidemics alerts
					mergedAlerts =self.getEpidemics(programConfig=programConfig,detectedAggEpidemics=detectedAggAlerts,detectedMergedAlertsMessage=detectedMergedAlertsMessage,dfEpidemics=dfAlerts,messageColumns=messageColumns,alertColumns=alertColumns,type='ALERT',notify=notifyUser)
					if mergedAlerts is None:
						return
					detectedMergedAlertsMessage = mergedAlerts[1]
					detectedMergedAlerts =  detectedMergedAlerts.append(mergedAlerts[0])
					# Creating threshold alerts
					mergedEpidemics =self.getEpidemics(programConfig=programConfig,detectedAggEpidemics=detectedAggEpidemics,detectedMergedAlertsMessage=detectedMergedAlertsMessage,dfEpidemics=dfEpidemics,messageColumns=messageColumns,alertColumns=alertColumns,notify=notifyUser)
					if mergedEpidemics is None:
						return
					detectedMergedEpidemics = detectedMergedEpidemics.append(mergedEpidemics[0])
					detectedMergedAlertsMessage = mergedEpidemics[1]
					print ("Finished creating Outbreaks for %s" %diseaseMeta['disease'])
					# Reminders
					#reminders = self.queryValue(allAggEpidemics,remindersQuery)
					### Send outbreak message


				else:
					print("Failed to retrieve case events from analytics")
			elif diseaseMeta['epiAlgorithm'] == "NON_SEASONAL":
				print("Detecting for non-seasonal")
				print ("Start outbreak detection for %s" %diseaseMeta['disease'])
				# periods are aggregate generated
				aggPeriod = self.createAggThresholdPeriod(mPeriods,nPeriods,'NON_SEASONAL')
				aggPeriods = piSeparator.join(aggPeriod)

				aggParams = {"dimension": ["dx:"+ piIndicators,"ou:" + ouLevel,"pe:" + aggPeriods],"displayProperty":"NAME","tableLayout":"true","columns":"dx;pe","rows":"ou","skipMeta":"false","hideEmptyRows":"true","skipRounding":"false","showHierarchy":"true"}

				aggIndicators = self.getHttpData(self.url,piFields,self.username,self.password,params=aggParams)

				if(( aggIndicators != 'HTTP_ERROR') and (epiReportingOrgUnit != 'HTTP_ERROR')):
					aggData = aggIndicators
					aggOrgUnit = epiReportingOrgUnit['organisationUnits']
					detectedAggEpidemics = self.detectOnAggregateIndicators(aggData,diseaseMeta,epidemics,aggOrgUnit,aggPeriod,mPeriods,nPeriods)
					detectedAggAlerts = self.queryValue(detectedAggEpidemics,"alert == 'true'")
					# Creating epidemics alerts
					mergedAlerts =self.getEpidemics(programConfig=programConfig,detectedAggEpidemics=detectedAggAlerts,detectedMergedAlertsMessage=detectedMergedAlertsMessage,dfEpidemics=dfAlerts,messageColumns=messageColumns,alertColumns=alertColumns,type='ALERT',notify=notifyUser)
					if mergedAlerts is None:
						return
					detectedMergedAlertsMessage = mergedAlerts[1]
					detectedMergedAlerts =  detectedMergedAlerts.append(mergedAlerts[0])
					# Creating threshold alerts
					mergedEpidemics =self.getEpidemics(programConfig=programConfig,detectedAggEpidemics=detectedAggEpidemics,detectedMergedAlertsMessage=detectedMergedAlertsMessage,dfEpidemics=dfEpidemics,messageColumns=messageColumns,alertColumns=alertColumns,notify=notifyUser)
					if mergedEpidemics is None:
						return
					detectedMergedEpidemics = detectedMergedEpidemics.append(mergedEpidemics[0])
					detectedMergedAlertsMessage = mergedEpidemics[1]
					print ("Finished creating Outbreaks for %s" %diseaseMeta['disease'])

					# Reminders
					#reminders = self.queryValue(allAggEpidemics,remindersQuery)
					### Send outbreak messages
				else:
					print("Failed to retrieve case events from analytics")
			else:
				pass

		# Transform mergedEpidemics to DHIS2 Events format
		eventColumns = ['event','eventDate','program','programStage','storedBy','status','orgUnit','dataValues']
		eventDropColumns =["suspectedValue","confirmedValue","deathValue", "period", "firstCaseDate","lastCaseDate","endDate","closeDate","dateReminderSent","reminderSent","epicode","status","disease","orgUnit","orgUnitName","orgUnitCode","reportingOrgUnit", "reportingOrgUnitName","event","program","programStage","incubationDays","storedBy","eventDate","active","updated"]
		epidemicsColumns = ["suspectedValue","confirmedValue","deathValue", "period", "firstCaseDate","lastCaseDate","endDate","closeDate","dateReminderSent","reminderSent","epicode","dataValues","status","disease","orgUnit","orgUnitName","orgUnitCode","reportingOrgUnit", "reportingOrgUnitName","event","program","programStage","incubationDays","storedBy","eventDate","active","updated"]
		try:
			detectedMergedEpidemics.drop_duplicates(subset=eventDropColumns,inplace=True)
		except KeyError:
			print("Key error in ", eventDropColumns)
		dhis2Events = detectedMergedEpidemics.filter(eventColumns)
		mergedEpidemicsEvents = detectedMergedEpidemics.filter(epidemicsColumns)
		events = {'events': json.loads(dhis2Events.to_json(orient='records',date_format='iso'))}
		print("Updating epidemics in the datastore online")
		epiUpdateDataStoreEndPoint  = 'dataStore/' + self.dataStore + '/epidemics'
		self.updateJsonData(self.url,epiUpdateDataStoreEndPoint,self.username,self.password,json.loads(mergedEpidemicsEvents.to_json(orient='records',date_format='iso')))
		print("Updating epidemics in the events online")
		epiUpdateEventEndPoint  = 'events?importStrategy=CREATE_AND_UPDATE'
		self.postJsonData(self.url,epiUpdateEventEndPoint,self.username,self.password,events)
		print ("Finished creating Outbreaks")
		print("Sending alerts and messages")
		try:
			detectedMergedAlertsMessage.drop_duplicates(subset=alertColumns,inplace=True)
		except KeyError:
			print("Key error in ",alertColumns)
		if detectedMergedAlertsMessage.empty is not True:
			messages = {'messageConversations': json.loads(detectedMergedAlertsMessage.to_json(orient='records')) }
			self.sendSmsAndEmailMessage(messages)
		
		mergedDataStoresMessages = detectedMergedAlerts.filter(alertColumns)
		try:
			mergedDataStoresMessages.drop_duplicates(subset=alertColumns,inplace=True)
		except KeyError:
			print("Key error in ",alertColumns)

		print("Save alerts in the datastore online")
		epiUpdateDataStoreEndPointAlert  = 'dataStore/' + self.dataStore + '/alerts'
		self.updateJsonData(self.url,epiUpdateDataStoreEndPointAlert,self.username,self.password,json.loads(mergedDataStoresMessages.to_json(orient='records',date_format='iso')))

		return "Done processing"

		# Start epidemic detection
	def startEpidemics(self):
		print ("Started detection for outbreaks/epidemics")
		# Get Disease Metadata
		diseaseFields = 'dataStore/' + self.dataStore + '/diseases'
		auth = self.getAuth()
		self.username = auth['username']
		self.password = auth['password']
		self.url = auth['url']
		diseasesMeta = self.getHttpData(self.url,diseaseFields,self.username,self.password,{})

		# Get Epidemics
		if(diseasesMeta != 'HTTP_ERROR'):
			diseaseConfig = diseasesMeta['config']['notificationProgram']

			# programs
			self.programUid = diseaseConfig['id']
			self.outbreakProgram = diseasesMeta['config']['reportingProgram']['id']

			# TE Attributes
			self.dateOfOnsetUid = diseaseConfig['dateOfOnSet']['id']
			self.conditionOrDiseaseUid = diseaseConfig['disease']['id']
			self.patientStatusOutcome = diseaseConfig['patientStatusOutcome']['id']
			self.regPatientStatusOutcome = diseaseConfig['regPatientStatusOutcome']['id']
			self.caseClassification = diseaseConfig['caseClassification']['id']
			self.testResult= diseaseConfig['testResult']['id']
			self.testResultClassification= diseaseConfig['testResultClassification']['id']

			epidemicsFields = 'dataStore/' + self.dataStore + '/epidemics'
			epidemicsData = self.getHttpData(self.url,epidemicsFields,self.username,self.password,{})

			alertsFields = 'dataStore/' + self.dataStore + '/alerts'
			alertsData = self.getHttpData(self.url,alertsFields,self.username,self.password,{})

			if(epidemicsData != 'HTTP_ERROR'):
				epidemicsProcessed = self.iterateDiseases(diseasesMeta,epidemicsData,alertsData,'ANALYTICS')
				print(epidemicsProcessed)
			else:
				print("Failed to load epidemics datastores")

				#loggedin = self.getHttpData(self.url,'me',self.username,self.password,{})
		else:
			print("Failed to get disease meta data")

# Start the idsr processing
if __name__ == "__main__":
	idsrAppSerlvet = IdsrAppServer()
	idsrAppSerlvet.startEpidemics()
#main()
