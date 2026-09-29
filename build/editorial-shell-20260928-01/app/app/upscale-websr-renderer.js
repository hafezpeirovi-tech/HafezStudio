'use strict';
let engine,device,inputCanvas,inputContext,width,height,target,readback,pitch,outW,outH,resized,resizePipeline,resizeBind;
window.localUpscale.onRequest(async request=>{
 try {
  if(request.type==='init'){
   const adapter=await navigator.gpu?.requestAdapter({powerPreference:'high-performance'});
   if(!adapter || adapter.info?.isFallbackAdapter)throw Error('WebGPU hardware adapter unavailable; no software fallback.');
   device=await adapter.requestDevice();
   width=request.width;height=request.height;
   inputCanvas=new OffscreenCanvas(width,height);inputContext=inputCanvas.getContext('2d');
   outW=request.outputWidth;outH=request.outputHeight;
   engine=new WebSR({network_name:'anime4k/cnn-2x-l',weights:request.weights,gpu:device,canvas:document.getElementById('gpu'),resolution:{width,height}});
   // Read a persistent render target, not a hidden canvas swapchain which can
   // be cleared by the compositor before CPU readback.
   target=device.createTexture({size:[width*2,height*2],format:'rgba8unorm',usage:GPUTextureUsage.RENDER_ATTACHMENT|GPUTextureUsage.TEXTURE_BINDING});
   engine.network.lastLayer().setOutput(target);
   resized=device.createTexture({size:[outW,outH],format:'rgba8unorm',usage:GPUTextureUsage.RENDER_ATTACHMENT|GPUTextureUsage.COPY_SRC});
   const shader=device.createShaderModule({code:`
    struct Vertex { @builtin(position) position:vec4f, @location(0) uv:vec2f };
    @vertex fn vs(@builtin(vertex_index) id:u32)->Vertex {
     let p=array<vec2f,3>(vec2f(-1,-1),vec2f(3,-1),vec2f(-1,3));
     var v:Vertex;v.position=vec4f(p[id],0,1);v.uv=vec2f((p[id].x+1)*.5,(1-p[id].y)*.5);return v;
    }
    @group(0) @binding(0) var source:texture_2d<f32>;
    @group(0) @binding(1) var resizeSampler:sampler;
    @fragment fn fs(v:Vertex)->@location(0) vec4f {return vec4f(textureSample(source,resizeSampler,v.uv).rgb,1);}
   `});
   const compilation=await shader.getCompilationInfo();
   const errors=compilation.messages.filter(m=>m.type==='error');if(errors.length)throw Error(errors.map(e=>e.message).join('; '));
   resizePipeline=await device.createRenderPipelineAsync({layout:'auto',vertex:{module:shader,entryPoint:'vs'},fragment:{module:shader,entryPoint:'fs',targets:[{format:'rgba8unorm'}]}});
   resizeBind=device.createBindGroup({layout:resizePipeline.getBindGroupLayout(0),entries:[{binding:0,resource:target.createView()},{binding:1,resource:device.createSampler({minFilter:'linear',magFilter:'linear'})}]});
   pitch=Math.ceil(outW*4/256)*256;
   readback=device.createBuffer({size:pitch*outH,usage:GPUBufferUsage.COPY_DST|GPUBufferUsage.MAP_READ});
   window.localUpscale.reply({id:request.id,ok:true,adapter:adapter.info?.description||adapter.info?.device||'WebGPU'});
  }else{
   device.pushErrorScope('validation');
   inputContext.putImageData(new ImageData(new Uint8ClampedArray(request.bytes),width,height),0,0);
   const bitmap=await createImageBitmap(inputCanvas);
   try{await engine.network.feedForward(bitmap);}finally{bitmap.close();}
   const commands=device.createCommandEncoder();
   const pass=commands.beginRenderPass({colorAttachments:[{view:resized.createView(),loadOp:'clear',storeOp:'store'}]});
   pass.setPipeline(resizePipeline);pass.setBindGroup(0,resizeBind);pass.draw(3);pass.end();
   commands.copyTextureToBuffer({texture:resized},{buffer:readback,bytesPerRow:pitch},{width:outW,height:outH});
   device.queue.submit([commands.finish()]);
   await readback.mapAsync(GPUMapMode.READ);
   const mapped=new Uint8Array(readback.getMappedRange()),rgba=new Uint8ClampedArray(outW*outH*4);
   for(let row=0;row<outH;row++)rgba.set(mapped.subarray(row*pitch,row*pitch+outW*4),row*outW*4);
   readback.unmap();
   const error=await device.popErrorScope();if(error)throw Error(error.message);
   window.localUpscale.reply({id:request.id,ok:true,bytes:rgba.buffer});
  }
 }catch(error){window.localUpscale.reply({id:request.id,ok:false,error:error.message});}
});
