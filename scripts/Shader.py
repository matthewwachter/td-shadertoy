
"""
Extension classes enhance TouchDesigner components with python. An
extension is accessed via ext.ExtensionClassName from any operator
within the extended component. If the extension is promoted via its
Promote Extension parameter, all its attributes with capitalized names
can be accessed externally, e.g. op('yourComp').PromotedFunction().

Help: search "Extensions" in wiki
"""
import requests
from json import loads
import textwrap


from TDStoreTools import StorageManager
TDF = op.TDModules.mod.TDFunctions

class Shader:
	"""
	Shader description
	"""
	def __init__(self, ownerComp):
		# The component to which this extension is attached
		self.ownerComp = ownerComp
		self.dataComp = ownerComp.op('data')

		self.common = ownerComp.op('common')
		self.imageComp = ownerComp.op('image')
		self.buffAComp = ownerComp.op('buffA')
		self.buffBComp = ownerComp.op('buffB')
		self.buffCComp = ownerComp.op('buffC')
		self.buffDComp = ownerComp.op('buffD')

		self.bufferComps = {
			'Buf A': self.buffAComp,
			'Buf B': self.buffBComp,
			'Buf C': self.buffCComp,
			'Buf D': self.buffDComp,
			'Buffer A': self.buffAComp,
			'Buffer B': self.buffBComp,
			'Buffer C': self.buffCComp,
			'Buffer D': self.buffDComp,
		}

		storedItems = [
			{'name': 'Shader', 'default': {}, 'dependable': True},
			{'name': 'Image', 'default': {}, 'dependable': True},
			{'name': 'Buffers', 'default': [], 'dependable': True},
			{'name': 'Common', 'default': [], 'dependable': True},
			{'name': 'Info', 'default': [], 'dependable': True},
			{'name': 'Ver', 'default': '', 'dependable': True},
		]
		
		self.stored = StorageManager(self, self.dataComp, storedItems)

	# Pulse Paramters

	def pulse_Load(self):
		self.Load()

	def pulse_Opensite(self):
		site_id = self.stored['Info']['id']

		ui.viewFile('https://www.shadertoy.com/view/' + str(site_id))

	def pulse_Resettime(self):
		self.ownerComp.op('speed1').par.resetpulse.pulse()

	def getShader(self):
		shader_id = self.ownerComp.par.Id.eval()
		apikey = self.ownerComp.par.Apikey.eval()

		try:
			shader_url = 'https://www.shadertoy.com/api/v1/shaders/' + shader_id + '?key=' + apikey
			headers = {
				'User-Agent': 'My User Agent 1.0',
			}			
			myrequest = requests.get(shader_url, headers=headers).content.decode("utf-8")
			myjson = loads(myrequest)
			self.stored['Shader'] = myjson['Shader']

		except Exception as e:
			debug(e)
			return False

		return True

	def Load(self):

		# request the shader from the api
		if not self.getShader():
			debug('shader api request failed')
			return

		for b in self.bufferComps:
			self.bufferComps[b].allowCooking = False

		shader = self.stored['Shader']
		#self.stored['Shader'] = {} #shader
		self.stored['Info'] = shader['info']
		self.stored['Ver'] = shader['ver']
		renderpass = shader['renderpass']

		image = {}
		buffers = []
		common = []

		for i in range(len(renderpass)):
			r = renderpass[i]
			
			r_type = r['type']

			if r_type == 'image':
				image = r
			elif r_type == 'buffer':
				buffers.append(r)
			elif r_type == 'common':
				common.append(r)

		self.stored['Image'] = image
		self.stored['Buffers'] = buffers
		self.stored['Common'] = common

		self.loadCommon()
		self.loadBuffers()
		self.loadImage()

		self.ownerComp.op('speed1').par.reset = True

		self.ownerComp.op('resetTime').run(delayFrames=1)

	def loadCommon(self):
		common = self.stored['Common']
		if len(common) > 0:
			raw_code = common[0]['code']
			conv_code = self.convertChannelInfo(raw_code, self.stored['Image']['inputs'])
			self.common.text = conv_code
		pass

	def loadBuffers(self):
		buffers = self.stored['Buffers']
		if len(buffers) > 0:
			for b in buffers:
				inputs = b['inputs']
				name = b['name']

				if name in self.bufferComps.keys():
					bComp = self.bufferComps[name]

					bComp.allowCooking = True

					raw_code = b['code']
					bComp.op('orig_pixel').text = raw_code

					samplers = b['inputs']
					conv_code = self.convertChannelInfo(raw_code, samplers)
					pixel_code = self.convertMainPixel(conv_code)
					bComp.op('pixel').text = pixel_code

					# vertex_code = self.generateVertex(raw_code)
					# bComp.op('vertex').text = vertex_code

					self.loadSamplers(bComp, samplers)

		pass

	def loadImage(self):
		for i in range(4):
			self.imageComp.op('select' + str(i)).par.top = ''
		
		image = self.stored['Image']

		raw_code = image['code']
		self.imageComp.op('orig_pixel').text = raw_code

		samplers = image['inputs']

		conv_code = self.convertChannelInfo(raw_code, samplers)
		pixel_code = self.convertMainPixel(conv_code)

		self.imageComp.op('pixel').text = pixel_code

		# vertex_code = self.generateVertex(raw_code)
		# self.imageComp.op('vertex').text = vertex_code


		self.loadSamplers(self.imageComp, samplers)

	def generateUniforms(self):
		# generate shadertoy style header

		uniforms = textwrap.dedent('''
		uniform vec3      iResolution;           // viewport resolution (in pixels)
		uniform float     iTime;                 // shader playback time (in seconds)
		uniform float     iTimeDelta;            // render time (in seconds)
		uniform int       iFrame;                // shader playback frame
		uniform float     iChannelTime[4];       // channel playback time (in seconds)
		uniform vec4      iMouse;                // mouse pixel coords. xy: current (if MLB down), zw: click
		uniform vec4      iDate;                 // (year, month, day, time in seconds)
		uniform float     iSampleRate;           // sound sample rate (i.e., 44100)

		''')
		return uniforms
	
	def generateDefines(self):
		""" Generate #defines for shadertoy shader
		"""
		
		defines = textwrap.dedent('''
		#define TD_SHADERTOY
		#define TOUCHDESIGNER

		''')
		return defines


	def convertChannelInfo(self, raw_code, samplers):

		code = raw_code

		for i in range(len(samplers)):
			#pprint(renderpass)
			s = samplers[i]
			
			channel = s['channel']
			ctype = s['ctype']

			if ctype == 'cubemap':
				code = code.replace('iChannel' + str(channel), 'sTDCubeInputs[' + str(channel) + ']')
				code = code.replace('iChannelResolution[' + str(channel) + ']', 'vec2(uTDCubeInfos[' + str(channel) + '].res.zw)')
			else:
				code = code.replace('iChannel' + str(channel), 'sTD2DInputs[' + str(channel) + ']')
				code = code.replace('iChannelResolution[' + str(channel) + ']', 'vec2(uTD2DInfos[' + str(channel) + '].res.zw)')



		# sub all iChannel with sTD2DInputs
		code = re.sub(r'iChannel(\d)', r'sTD2DInputs[\1]', code)

		# sub all iChannelResolution with TDTexInfo
		code = re.sub(r'iChannelResolution\[(\d)\]', r'vec2(uTD2DInfos[\1].res.zw)', code)

		return code	

	def convertMainPixel(self, raw_code):


		code = self.generateUniforms()
		code += self.generateDefines()
		
		if len(self.stored['Common']) > 0:
			code += textwrap.dedent('''
			#include <../common>
			''')

		# # restructure input and output declarations for main function
		# pixel_main_funct = textwrap.dedent(r'''
		# in vec2 \2;
		# layout (location = 0) out \1;
		# void main()
		# ''')

		# code += re.sub(r'void mainImage\w?\(.*out (.*),\s*i?n?\s?\S*\s(\S*)\s*\)', pixel_main_funct, raw_code)
		
		code += raw_code

		code  += textwrap.dedent('''
		layout (location = 0) out vec4 TDColor;
		void main()
		{
			mainImage(TDColor, vUV.st*iResolution.xy);
		}
		''')

		return code

	def generateVertex(self, raw_code):

		# create a vertex shader that uses the same declared fragcoord name
		vert_main_funct = textwrap.dedent('''
		uniform vec3 iResolution;
		
		out vec2 {};
		void main()
		{{
		  {} = uv[0].xy * iResolution.xy;
		  gl_Position = TDSOPToProj(vec4(P, 1.0));
		}}
		''')

		vert_text = re.findall(r'void mainImage\w?\(.*out (.*),\s*i?n?\s?\S*\s(\S*)\s*\)', raw_code)
		fc = vert_text[0][1]
		code = vert_main_funct.format(fc, fc)

		return code
		
	def loadSamplers(self, comp, samplers):
		for i in range(4):
			comp.op('select' + str(i)).par.top = ''
			comp.op('selectCube' + str(i)).par.top = 'defaultCube'

		for i in range(len(samplers)):
			#pprint(renderpass)
			s = samplers[i]

			sComp = comp.op('sampler' + str(i))
			sCompPars = sComp.par
			
			sCompPars.Channel = s['channel']
			sCompPars.Ctype = s['ctype']
			
			source = s['src']

			if source.startswith('/media/previz/buffer'):
				b = source.split('/')[-1].split('.')[0]
				buffers = {
					'buffer00': 'buffA',
					'buffer01': 'buffB',
					'buffer02': 'buffC',
					'buffer03': 'buffD',
				}

				if b in buffers.keys():
					source = buffers[b]
			sCompPars.Src = source
			
			sampler = s['sampler']
			
			sCompPars.Filter = sampler['filter']
			sCompPars.Internal = sampler['internal']
			sCompPars.Srgb = (sampler['srgb'] == 'true')
			sCompPars.Vflip = (sampler['vflip'] == 'true')
			sCompPars.Wrap = sampler['wrap']
			
			sComp.op('audiofilein1').bypass = not (s['ctype'] == 'music')

			channel = s['channel']

			if s['ctype'] == 'cubemap':
				comp.op('selectCube' + str(channel)).par.top = sComp.name + '/out1'
			else:
				comp.op('select' + str(channel)).par.top = sComp.name + '/out1'
