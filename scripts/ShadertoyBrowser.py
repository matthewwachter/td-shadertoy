import urllib.request
import json

from TDStoreTools import StorageManager
TDF = op.TDModules.mod.TDFunctions

class ShadertoyBrowser:
	"""
	ShadertoyBrowser description
	"""
	def __init__(self, ownerComp):
		# The component to which this extension is attached
		self.ownerComp = ownerComp
		self.dataComp = ownerComp.op('data')

		# stored items (persistent across saves and re-initialization):
		storedItems = [
			# Only 'name' is required...
			{'name': 'Shaders', 'default': None, 'dependable': True},
		]
		
		self.stored = StorageManager(self, self.dataComp, storedItems)

	def getShaders(self):
		apikey = self.ownerComp.par.Apikey.eval()
		query = self.ownerComp.par.Searchterm.eval()
		start_page = self.ownerComp.par.Start.eval()
		query_num = self.ownerComp.par.Results.eval()
		sort = self.ownerComp.par.Sort.eval()

		query_url = "https://www.shadertoy.com/api/v1/shaders/query/" + query + "?sort=" + sort + "&from=" + str(start_page) + "&num=" + str(query_num) + "&key=" + apikey
		all_url = "https://www.shadertoy.com/api/v1/shaders/query/?sort=" + sort + "&from=" + str(start_page) + "&num=" + str(query_num) + "&key=" + apikey

		
		if(query != ''):
			my_url = query_url
		else:
			my_url = all_url 

		num_shaders = 0

		try:
			myrequest = urllib.request.urlopen(my_url).read().decode("utf-8")
			shadertoy = json.loads(myrequest)
			num_shaders = shadertoy['Shaders']
			shader_ids = shadertoy['Results']

			self.stored['Shaders'] = shader_ids

			self.ownerComp.op('replicator1').par.recreateall.pulse()

		except:
			debug('search request failed')


			

