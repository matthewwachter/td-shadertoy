# td-shadertoy

**td-shadertoy.toe** contains a collection of components that can be used to load Shadertoy shaders into TouchDesigner. This is made possible through the use of the Shadertoy API which allows users to search for shaders and download a json dictionary of the shader's code and sampler data.

[Shadertoy API Documentation](https://www.shadertoy.com/howto)

![Screenshot1](images/screenshot1.JPG)

Not all shaders are made available in the API as the shader's creator must choose to allow the shader to be available in the API when they publish it. Most of the available shaders will load in without any issues with the exception of those that rely on specific sampler wrap and filter conditions. In Shadertoy, users are allowed to set these settings individually for each shader's input channel but the glsl TOP in TouchDesigner only allows the user set this globally. Generally this isn't an issue but some shaders fail to display correctly because of this.

There are a few differences in the way a glsl shader is written in Shadertoy vs TouchDesigner. The shadertoyConverter component requests the json object from the API, modifies the shader's code, generates the samplers, and routes them to their respective destinations. 

There are several conversion issues in the shader's code that the shadertoyConverter component addresses:

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

- If an additional **common** file is used, a reference must be included.

```
code += textwrap.dedent('''
#include <../common>
''')
```