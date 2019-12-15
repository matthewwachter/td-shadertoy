# td-shadertoy

The .toe scene in this repo contains a collection of components that can be used to load Shadertoy shaders into TouchDesigner. This is made possible through the use of the Shadertoy API which allows users to search for shaders as well as download json dictionary of the requested shader's code and sampler data.

Not all shaders are available in the API as the shader's creator must choose to allow the shader to be available in the API when they publish it.

There are a few main difference in the way a glsl shader is written in Shadertoy vs TouchDesigner. The shadertoyConverter component modifies the code for each shaders respective image and buffer shaders. As well, samplers for each shader are created and routed to their corresponding shader inputs.

There are several conversion issues that the shadertoyConverter component address:

- ShaderToy provides a default set of useful uniforms. These can simply be prepended to each shader's code and added in the uniform pages of the glsl TOP. 

	```
	uniform vec3      iResolution;           // viewport resolution (in pixels)
	uniform float     iTime;                 // shader playback time (in seconds)
	uniform float     iTimeDelta;            // render time (in seconds)
	uniform int       iFrame;                // shader playback frame
	uniform float     iChannelTime[4];       // channel playback time (in seconds)
	uniform vec4      iMouse;                // mouse pixel coords. xy: current (if MLB down), zw: click
	uniform vec4      iDate;                 // (year, month, day, time in seconds)
	uniform float     iSampleRate;           // sound sample rate (i.e., 44100)
	```

- The Main loop is called mainImage(). This can be addressed by appending the following code which calls the mainImage() function and passes it the color buffer as well as the expected pixel coordinates. 

	```
	layout (location = 0) out vec4 TDColor;
	void main()
	{
		mainImage(TDColor, vUV.st*iResolution.xy);
	}
	```

- In TouchDesigner, samplers are provided as array objects called sTD2DInputs and sTDCubeInputs for cubemaps. Shadertoy refers to all types of samplers as iChannel so the names must be substituted according to the sampler type. 

	```
	if ctype == 'cubemap':
		code = code.replace('iChannel' + str(channel), 'sTDCubeInputs[' + str(channel) + ']')
		code = code.replace('iChannelResolution[' + str(channel) + ']', 'vec2(uTDCubeInfos[' + str(channel) + '].res.zw)')
	else:
		code = code.replace('iChannel' + str(channel), 'sTD2DInputs[' + str(channel) + ']')
		code = code.replace('iChannelResolution[' + str(channel) + ']', 'vec2(uTD2DInfos[' + str(channel) + '].res.zw)')
	```

- iChannelResolution must also be modified to use the TouchDesigner provided texture info array object.

	```
	code = re.sub(r'iChannelResolution\[(\d)\]', r'vec2(uTD2DInfos[\1].res.zw)', code)
	```

- If an additional common file is used it must be added to the shader code.

	```
	code += textwrap.dedent('''
	#include <../common>
	''')
	```

- Sampler objects must be generated and routed. This is done using a pre-made sampler component that can easily be set to load the desired source
	```
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
	```