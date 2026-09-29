/*
 * ATTENTION: The "eval" devtool has been used (maybe by default in mode: "development").
 * This devtool is neither made for production nor for readable output files.
 * It uses "eval()" calls to create a separate source file in the browser devtools.
 * If you are trying to read the output file, select a different devtool (https://webpack.js.org/configuration/devtool/)
 * or disable the default devtool with "devtool: false".
 * If you are looking for production-ready output files, see mode: "production" (https://webpack.js.org/configuration/mode/).
 */
(function webpackUniversalModuleDefinition(root, factory) {
	if(typeof exports === 'object' && typeof module === 'object')
		module.exports = factory();
	else if(typeof define === 'function' && define.amd)
		define([], factory);
	else if(typeof exports === 'object')
		exports["WebSR"] = factory();
	else
		root["WebSR"] = factory();
})(self, () => {
return /******/ (() => { // webpackBootstrap
/******/ 	"use strict";
/******/ 	var __webpack_modules__ = ({

/***/ "./src/context.ts":
/*!************************!*\
  !*** ./src/context.ts ***!
  \************************/
/***/ (function(__unused_webpack_module, exports) {

{
var __awaiter = (this && this.__awaiter) || function (thisArg, _arguments, P, generator) {
    function adopt(value) { return value instanceof P ? value : new P(function (resolve) { resolve(value); }); }
    return new (P || (P = Promise))(function (resolve, reject) {
        function fulfilled(value) { try { step(generator.next(value)); } catch (e) { reject(e); } }
        function rejected(value) { try { step(generator["throw"](value)); } catch (e) { reject(e); } }
        function step(result) { result.done ? resolve(result.value) : adopt(result.value).then(fulfilled, rejected); }
        step((generator = generator.apply(thisArg, _arguments || [])).next());
    });
};
Object.defineProperty(exports, "__esModule", ({ value: true }));
class WebGPUContext {
    constructor(device, resolution, canvas, scale, debug) {
        this.device = device;
        this.canvas = canvas;
        this.resolution = resolution;
        this.textures = {};
        this.buffers = {};
        this.destroyed = false;
        this.scale = scale;
        this.debug = debug;
        let context = this.canvas.getContext('webgpu');
        if (context instanceof GPUCanvasContext) {
            this.context = context;
        }
        else {
            throw new Error("Unable to load WebGPU context");
        }
        this.context.configure({
            device: this.device,
            format: navigator.gpu.getPreferredCanvasFormat()
        });
        this.textureUsage = GPUTextureUsage.TEXTURE_BINDING | GPUTextureUsage.COPY_DST | GPUTextureUsage.RENDER_ATTACHMENT;
        this.bufferUsage = GPUBufferUsage.STORAGE | GPUBufferUsage.COPY_SRC | GPUBufferUsage.COPY_DST;
        if (this.debug) {
            // Read output pixel value
            this.textureUsage = this.textureUsage | GPUTextureUsage.COPY_SRC;
            this.bufferUsage = this.bufferUsage | GPUBufferUsage.COPY_SRC;
        }
        this.textures['output'] = this.context.getCurrentTexture();
    }
    readBuffer(bufferName) {
        return __awaiter(this, void 0, void 0, function* () {
            if (!this.buffers[bufferName])
                throw new Error(`No buffer with name ${bufferName}`);
            const readEncoder = this.device.createCommandEncoder({
                label: `Read ${bufferName} buffer encoder`,
            });
            const buffer = this.buffers[bufferName];
            const resultBuffer = this.device.createBuffer({
                label: 'result buffer',
                size: buffer.size,
                usage: GPUBufferUsage.MAP_READ | GPUBufferUsage.COPY_DST
            });
            readEncoder.copyBufferToBuffer(buffer, 0, resultBuffer, 0, resultBuffer.size);
            this.device.queue.submit([readEncoder.finish()]);
            yield resultBuffer.mapAsync(GPUMapMode.READ);
            let range = resultBuffer.getMappedRange();
            return new Float32Array(range);
        });
    }
    readTexture(textureName) {
        return __awaiter(this, void 0, void 0, function* () {
            if (!this.textures[textureName])
                throw new Error(`No texture with name ${textureName}`);
            const readEncoder = this.device.createCommandEncoder({
                label: `Read ${textureName} texture encoder`,
            });
            const texture = this.textures[textureName];
            let bitsPerPixel = 16;
            if (texture.format === 'rgba8unorm')
                bitsPerPixel = 4;
            if (texture.format === 'r32float')
                bitsPerPixel = 4;
            const resultBuffer = this.device.createBuffer({
                label: 'result buffer',
                size: texture.width * texture.height * bitsPerPixel,
                usage: GPUBufferUsage.MAP_READ | GPUBufferUsage.COPY_DST
            });
            readEncoder.copyTextureToBuffer({
                texture: this.textures[textureName],
            }, {
                buffer: resultBuffer,
                bytesPerRow: texture.width * bitsPerPixel
            }, {
                width: texture.width,
                height: texture.height,
                depthOrArrayLayers: 1,
            });
            this.device.queue.submit([readEncoder.finish()]);
            yield resultBuffer.mapAsync(GPUMapMode.READ);
            if (texture.format === 'r32float')
                return new Float32Array(resultBuffer.getMappedRange());
            else if (texture.format === 'rgba32float')
                return new Float32Array(resultBuffer.getMappedRange());
            else if (texture.format === 'rgba8unorm')
                return new Uint8ClampedArray(resultBuffer.getMappedRange());
            return new Float32Array(0);
        });
    }
    destroy() {
        this.device.destroy();
        this.destroyed = true;
    }
    buffer(key, options) {
        if (!this.buffers[key]) {
            options = options || {};
            const width = options.width || this.resolution.width;
            const height = options.height || this.resolution.height;
            const channels = options.channels || 4;
            const bitdepth = options.bitdepth || 4;
            this.buffers[key] = this.device.createBuffer({
                label: key,
                size: width * height * channels * bitdepth,
                usage: this.bufferUsage
            });
        }
        return this.buffers[key];
    }
    texture(key, options) {
        if (!this.textures[key]) {
            options = options || {};
            this.textures[key] = this.device.createTexture({
                label: key,
                size: [options.width || this.resolution.width, options.height || this.resolution.height],
                format: options.format || 'rgba32float',
                usage: this.textureUsage
            });
        }
        return this.textures[key];
    }
}
exports["default"] = WebGPUContext;


//# sourceURL=webpack://WebSR/./src/context.ts?
}

/***/ }),

/***/ "./src/layers/anime4k/conv2d-112x4.ts":
/*!********************************************!*\
  !*** ./src/layers/anime4k/conv2d-112x4.ts ***!
  \********************************************/
/***/ ((__unused_webpack_module, exports, __webpack_require__) => {

{
Object.defineProperty(exports, "__esModule", ({ value: true }));
const base_compute_layer_1 = __webpack_require__(/*! ../base_compute_layer */ "./src/layers/base_compute_layer.ts");
class Anime4KConv112x4 extends base_compute_layer_1.default {
    constructor(inputs, outputBuffer, weights, first) {
        super(inputs, outputBuffer, weights);
        this.label = "Anime4KConv112x4";
        const kernels = weights.weights;
        this.createUniform("kernels", "array<mat4x4f, 28>");
        let read_buffers = '';
        for (let i = 0; i < 7; i++) {
            if (first) {
                read_buffers += `
                let pixel_val${i} = inputBuffer${i}[buff_ind];
                result += kernels[${4 * i}]*max(pixel_val${i}, vec4f(0.0));
                result += kernels[${4 * i + 2}]*max(-1.0*pixel_val${i}, vec4f(0.0));
            `;
            }
            else {
                read_buffers += `
                let pixel_val${i} = inputBuffer${i}[buff_ind];
                result += kernels[${4 * i + 1}]*max(pixel_val${i}, vec4f(0.0));
                result += kernels[${4 * i + 3}]*max(-1.0*pixel_val${i}, vec4f(0.0));`;
            }
        }
        this.shader = this.createStandardShader(`
        
          @compute @workgroup_size(${this.num_work_groups}, ${this.num_work_groups}) fn main( @builtin(global_invocation_id) id: vec3<u32>) {
          
                let x = id.x;
                let y = id.y;
                
                let i = id.y*${this.resolution.width} + x;
                var result  = vec4f(0.0, 0.0, 0.0, 0.0);
                
                let coord = vec2<i32>( i32(x), i32(y));
               
                let buff_ind = coord.y*${this.resolution.width} + coord.x;
                ${read_buffers}
                
                outputBuffer[i] = result;
          }
        `);
        this.setUniform("kernels", new Float32Array(kernels));
        this.defaultSetup();
    }
    defaultPipelineConfig() {
        return {
            label: `${this.label}-pipeline`,
            layout: 'auto',
            compute: {
                module: this.shader,
                entryPoint: 'main',
            },
        };
    }
    defaultBindGroup() {
        const entries = [];
        this.inputs.forEach(function (input, i) {
            if (input instanceof GPUExternalTexture) {
                entries.push({ binding: i, resource: input });
            }
            else if (input instanceof GPUTexture) {
                entries.push({ binding: i, resource: input.createView() });
            }
            else if (input instanceof GPUBuffer) {
                entries.push({ binding: i, resource: { buffer: input } });
            }
        });
        this.uniforms.forEach((uniform, i) => {
            entries.push({
                binding: i + this.inputs.length,
                resource: {
                    buffer: this.buffers[uniform.name]
                }
            });
        });
        if (this.output instanceof GPUBuffer) {
            entries.push({
                binding: this.inputs.length + this.uniforms.length,
                resource: {
                    buffer: this.output
                }
            });
        }
        if (entries.length === 0)
            return null;
        return this.device.createBindGroup({
            layout: this.pipeline.getBindGroupLayout(0),
            entries
        });
    }
}
exports["default"] = Anime4KConv112x4;


//# sourceURL=webpack://WebSR/./src/layers/anime4k/conv2d-112x4.ts?
}

/***/ }),

/***/ "./src/layers/anime4k/conv2d-16x4.ts":
/*!*******************************************!*\
  !*** ./src/layers/anime4k/conv2d-16x4.ts ***!
  \*******************************************/
/***/ ((__unused_webpack_module, exports, __webpack_require__) => {

{
Object.defineProperty(exports, "__esModule", ({ value: true }));
const base_compute_layer_1 = __webpack_require__(/*! ../base_compute_layer */ "./src/layers/base_compute_layer.ts");
class Anime4KConv16x4 extends base_compute_layer_1.default {
    constructor(inputs, outputBuffer, weights) {
        super(inputs, outputBuffer, weights);
        this.label = "Anime4KConv16x4";
        const kernels = weights.weights;
        const bias = weights.bias;
        this.createUniform("kernel_offsets", "array<vec4f, 9>");
        this.createUniform("kernels", "array<mat4x4f, 36>");
        this.createUniform("bias", "vec4f");
        this.shader = this.createStandardShader(`
        
          @compute @workgroup_size(${this.num_work_groups}, ${this.num_work_groups}) fn main( @builtin(global_invocation_id) id: vec3<u32>) {
          
                let x = id.x;
                let y = id.y;
                
                let i = id.y*${this.resolution.width} + x;
                var result  = vec4f(0.0, 0.0, 0.0, 0.0);
                
                let coord = vec2<i32>( i32(x), i32(y));
                      
                 for(var i = 0u; i < 9; i++){
                   let pixel_loc = coord + vec2<i32>(kernel_offsets[i].xy);
                   let buff_ind = pixel_loc.y*${this.resolution.width} + pixel_loc.x;
                   
                   let pix_val0 = inputBuffer0[buff_ind];
                   let pix_val1 = inputBuffer1[buff_ind];
                  
                   result += kernels[i]*max(pix_val0, vec4f(0.0));
                   result += kernels[i+9]*max(pix_val1, vec4f(0.0));
                   result += kernels[i+18]*max(-1.0*pix_val0, vec4f(0.0));
                   result += kernels[i+27]*max(-1.0*pix_val1, vec4f(0.0));
                 } 
                 

                    
                result += bias;
                
                outputBuffer[i] = result;
          }
        `);
        this.setUniform("kernel_offsets", new Float32Array([
            -1, -1, 0, 0,
            -1, 0, 0, 0,
            -1, 1, 0, 0,
            0, -1, 0, 0,
            0, 0, 0, 0,
            0, 1, 0, 0,
            1, -1, 0, 0,
            1, 0, 0, 0,
            1, 1, 0, 0,
        ]));
        this.setUniform("kernels", new Float32Array(kernels));
        this.setUniform("bias", new Float32Array(bias));
        this.defaultSetup();
    }
}
exports["default"] = Anime4KConv16x4;


//# sourceURL=webpack://WebSR/./src/layers/anime4k/conv2d-16x4.ts?
}

/***/ }),

/***/ "./src/layers/anime4k/conv2d-3x4.ts":
/*!******************************************!*\
  !*** ./src/layers/anime4k/conv2d-3x4.ts ***!
  \******************************************/
/***/ ((__unused_webpack_module, exports, __webpack_require__) => {

{
Object.defineProperty(exports, "__esModule", ({ value: true }));
const base_compute_layer_1 = __webpack_require__(/*! ../base_compute_layer */ "./src/layers/base_compute_layer.ts");
class Anime4KConv3x4 extends base_compute_layer_1.default {
    constructor(inputTextures, outputBuffer, weights) {
        super(inputTextures, outputBuffer, weights);
        this.label = "Anime4KConv3x4";
        const kernels = weights.weights;
        const bias = weights.bias;
        this.createUniform("kernel_offsets", "array<vec4f, 9>");
        this.createUniform("kernels", "array<mat4x4f, 9>");
        this.createUniform("bias", "vec4f");
        // Set up pipeline in Lazy Load
        this.setUniform("kernel_offsets", new Float32Array([
            -1, -1, 0, 0,
            -1, 0, 0, 0,
            -1, 1, 0, 0,
            0, -1, 0, 0,
            0, 0, 0, 0,
            0, 1, 0, 0,
            1, -1, 0, 0,
            1, 0, 0, 0,
            1, 1, 0, 0,
        ]));
        this.setUniform("kernels", new Float32Array(kernels));
        this.setUniform("bias", new Float32Array(bias));
    }
    lazyLoadSetup() {
        const externalTexture = this.inputs[0] instanceof GPUExternalTexture;
        const textureLoad = externalTexture ? 'textureLoad(inputTexture0, coord + offset)' :
            'textureLoad(inputTexture0, coord + offset, 0)';
        this.shader = this.createStandardShader(`
        
          @compute @workgroup_size(${this.num_work_groups}, ${this.num_work_groups}) fn main( @builtin(global_invocation_id) id: vec3<u32>) {
          
                let x = id.x;
                let y = id.y;
                
                let i = id.y*${this.resolution.width} + x;
                var result  = vec4f(0.0, 0.0, 0.0, 0.0);
                
                let coord = vec2<i32>( i32(x), i32(y));
                      
                 for(var i = 0u; i < 9; i++){
                   let offset = vec2<i32>(kernel_offsets[i].xy);
                   result += kernels[i]*${textureLoad};
                 } 
                    
                result += bias;
                
                outputBuffer[i] = result;
          }
        `);
        this.pipeline = this.device.createComputePipeline(this.defaultPipelineConfig());
        this.bindGroup = this.defaultBindGroup();
    }
}
exports["default"] = Anime4KConv3x4;


//# sourceURL=webpack://WebSR/./src/layers/anime4k/conv2d-3x4.ts?
}

/***/ }),

/***/ "./src/layers/anime4k/conv2d-56x4.ts":
/*!*******************************************!*\
  !*** ./src/layers/anime4k/conv2d-56x4.ts ***!
  \*******************************************/
/***/ ((__unused_webpack_module, exports, __webpack_require__) => {

{
Object.defineProperty(exports, "__esModule", ({ value: true }));
const base_compute_layer_1 = __webpack_require__(/*! ../base_compute_layer */ "./src/layers/base_compute_layer.ts");
class Anime4KConv56x4 extends base_compute_layer_1.default {
    constructor(inputs, outputBuffer, weights) {
        super(inputs, outputBuffer, weights);
        this.label = "Anime4KConv56x4";
        const kernels = weights.weights;
        const bias = weights.bias;
        this.createUniform("kernels", "array<mat4x4f, 14>");
        this.createUniform("bias", "vec4f");
        let read_buffers = '';
        for (let i = 0; i < 7; i++) {
            read_buffers += `
            let pixel_val${i} = inputBuffer${i}[buff_ind];
            result += kernels[${2 * i}]*max(pixel_val${i}, vec4f(0.0));
            result += kernels[${2 * i + 1}]*max(-1.0*pixel_val${i}, vec4f(0.0));
            `;
        }
        this.shader = this.createStandardShader(`
        
          @compute @workgroup_size(${this.num_work_groups}, ${this.num_work_groups}) fn main( @builtin(global_invocation_id) id: vec3<u32>) {
          
                let x = id.x;
                let y = id.y;
                
                let i = id.y*${this.resolution.width} + x;
                var result  = vec4f(0.0, 0.0, 0.0, 0.0);
                
                let coord = vec2<i32>( i32(x), i32(y));
               
                let buff_ind = coord.y*${this.resolution.width} + coord.x;
                ${read_buffers}
                      
                result += bias;
                
                outputBuffer[buff_ind] = result;
          }
        `);
        this.setUniform("kernels", new Float32Array(kernels));
        this.setUniform("bias", new Float32Array(bias));
        this.defaultSetup();
    }
    defaultPipelineConfig() {
        return {
            label: `${this.label}-pipeline`,
            layout: 'auto',
            compute: {
                module: this.shader,
                entryPoint: 'main',
            },
        };
    }
    defaultBindGroup() {
        const entries = [];
        this.inputs.forEach(function (input, i) {
            if (input instanceof GPUExternalTexture) {
                entries.push({ binding: i, resource: input });
            }
            else if (input instanceof GPUTexture) {
                entries.push({ binding: i, resource: input.createView() });
            }
            else if (input instanceof GPUBuffer) {
                entries.push({ binding: i, resource: { buffer: input } });
            }
        });
        this.uniforms.forEach((uniform, i) => {
            entries.push({
                binding: i + this.inputs.length,
                resource: {
                    buffer: this.buffers[uniform.name]
                }
            });
        });
        if (this.output instanceof GPUBuffer) {
            entries.push({
                binding: this.inputs.length + this.uniforms.length,
                resource: {
                    buffer: this.output
                }
            });
        }
        if (entries.length === 0)
            return null;
        return this.device.createBindGroup({
            layout: this.pipeline.getBindGroupLayout(0),
            entries
        });
    }
}
exports["default"] = Anime4KConv56x4;


//# sourceURL=webpack://WebSR/./src/layers/anime4k/conv2d-56x4.ts?
}

/***/ }),

/***/ "./src/layers/anime4k/conv2d-8x4.ts":
/*!******************************************!*\
  !*** ./src/layers/anime4k/conv2d-8x4.ts ***!
  \******************************************/
/***/ ((__unused_webpack_module, exports, __webpack_require__) => {

{
Object.defineProperty(exports, "__esModule", ({ value: true }));
const base_compute_layer_1 = __webpack_require__(/*! ../base_compute_layer */ "./src/layers/base_compute_layer.ts");
class Anime4KConv8x4 extends base_compute_layer_1.default {
    constructor(inputs, outputBuffer, weights) {
        super(inputs, outputBuffer, weights);
        this.label = "Anime4KConv8x4";
        const kernels = weights.weights;
        const bias = weights.bias;
        this.createUniform("kernel_offsets", "array<vec4f, 9>");
        this.createUniform("kernels", "array<mat4x4f, 18>");
        this.createUniform("bias", "vec4f");
        this.shader = this.createStandardShader(`
        
          @compute @workgroup_size(${this.num_work_groups}, ${this.num_work_groups}) fn main( @builtin(global_invocation_id) id: vec3<u32>) {
          
                let x = id.x;
                let y = id.y;
                
                let i = id.y*${this.resolution.width} + x;
                var result  = vec4f(0.0, 0.0, 0.0, 0.0);
                
                let coord = vec2<i32>( i32(x), i32(y));
                      
                 for(var i = 0u; i < 9; i++){
                   let pixel_loc = coord + vec2<i32>(kernel_offsets[i].xy);
                   let buff_ind = pixel_loc.y*${this.resolution.width} + pixel_loc.x;
                   
                   let pix_val = inputBuffer0[buff_ind];
                  
                   result += kernels[i]*max(pix_val, vec4f(0.0));
                   result += kernels[i+9]*max(-1.0*pix_val, vec4f(0.0));
                 } 
                    
                result += bias;
                
                outputBuffer[i] = result;
          }
        `);
        this.setUniform("kernel_offsets", new Float32Array([
            -1, -1, 0, 0,
            -1, 0, 0, 0,
            -1, 1, 0, 0,
            0, -1, 0, 0,
            0, 0, 0, 0,
            0, 1, 0, 0,
            1, -1, 0, 0,
            1, 0, 0, 0,
            1, 1, 0, 0,
        ]));
        this.setUniform("kernels", new Float32Array(kernels));
        this.setUniform("bias", new Float32Array(bias));
        this.defaultSetup();
    }
}
exports["default"] = Anime4KConv8x4;


//# sourceURL=webpack://WebSR/./src/layers/anime4k/conv2d-8x4.ts?
}

/***/ }),

/***/ "./src/layers/anime4k/conv2d-concat2.ts":
/*!**********************************************!*\
  !*** ./src/layers/anime4k/conv2d-concat2.ts ***!
  \**********************************************/
/***/ ((__unused_webpack_module, exports, __webpack_require__) => {

{
Object.defineProperty(exports, "__esModule", ({ value: true }));
const base_compute_layer_1 = __webpack_require__(/*! ../base_compute_layer */ "./src/layers/base_compute_layer.ts");
class Anime4KConcat2 extends base_compute_layer_1.default {
    constructor(inputs, outputBuffer, weights) {
        super(inputs, outputBuffer, weights);
        this.label = "Anime4KConcat2";
        this.createUniform("bias", "vec4f");
        const bias = weights.bias;
        this.shader = this.createStandardShader(`
        
          @compute @workgroup_size(${this.num_work_groups}, ${this.num_work_groups}) fn main( @builtin(global_invocation_id) id: vec3<u32>) {
          
                let x = id.x;
                let y = id.y;
                
                let i = id.y*${this.resolution.width} + x;
                var result  = vec4f(0.0, 0.0, 0.0, 0.0);
                
                let coord = vec2<i32>( i32(x), i32(y));
               
                let buff_ind = coord.y*${this.resolution.width} + coord.x;
               
                outputBuffer[buff_ind] = inputBuffer0[buff_ind] + inputBuffer1[buff_ind] + bias;
          }
        `);
        this.setUniform("bias", new Float32Array(bias));
        this.defaultSetup();
    }
}
exports["default"] = Anime4KConcat2;


//# sourceURL=webpack://WebSR/./src/layers/anime4k/conv2d-concat2.ts?
}

/***/ }),

/***/ "./src/layers/anime4k/display.ts":
/*!***************************************!*\
  !*** ./src/layers/anime4k/display.ts ***!
  \***************************************/
/***/ ((__unused_webpack_module, exports, __webpack_require__) => {

{
Object.defineProperty(exports, "__esModule", ({ value: true }));
const base_render_layer_1 = __webpack_require__(/*! ../base_render_layer */ "./src/layers/base_render_layer.ts");
class DisplayLayer extends base_render_layer_1.default {
    constructor(inputs, output) {
        super(inputs, output);
        this.label = "DisplayLayer";
        this.vertexScale = {
            width: 1,
            height: 1
        };
        this.sampler = this.device.createSampler({
            addressModeU: "repeat",
            addressModeV: "repeat",
            magFilter: "linear",
            minFilter: "linear",
            mipmapFilter: "linear",
        });
    }
    lazyLoadSetup() {
        const externalTexture = this.inputs[1] instanceof GPUExternalTexture;
        const textureLoad = externalTexture ? 'textureSampleBaseClampToEdge(inputTexture, ourSampler, input.tex_coord)' :
            'textureSample(inputTexture, ourSampler, input.tex_coord)';
        this.shader = this.device.createShaderModule({
            label: `${this.label}-shader`,
            code: `
                
                   ${this.defaultVertexShader()}
                   @group(0) @binding(0) var<storage, read_write> inputBuffer0: array<vec4f>;
                   @group(0) @binding(1) var inputTexture: ${externalTexture ? 'texture_external' : 'texture_2d<f32>'};
                   @group(0) @binding(2) var ourSampler: sampler;
                  
                   @fragment fn fragmentMain(input: VertexShaderOutput) -> @location(0) vec4f {
                      
                        let x = ${this.resolution.width}.0*(input.tex_coord.x);
                        let y = ${this.resolution.height}.0*(input.tex_coord.y);
                        
                        let y2 = u32(floor(y));
                        let x2 = u32(floor(x));
                        
                        let i = y2*${Math.floor(this.resolution.width)} +  x2;
                       
                        let x_floor  = u32(fract(x)*2.0);
                        let y_floor  = u32(fract(y)*2.0);
                        
                        //I don t know, I think this is right? I found this by trial and error
                        let c_index: u32 = x_floor + y_floor*2;  
        
                        let value = inputBuffer0[i][c_index];
                        
                        let bicubic = ${textureLoad};
                        
                        return bicubic + vec4f(value);
                    
                      }            
            `
        });
        this.pipeline = this.device.createRenderPipeline(this.defaultPipelineConfig());
        this.bindGroup = this.defaultBindGroup();
        this.renderPassDescriptor = this.defaultRenderPassDescriptor();
    }
    defaultBindGroup() {
        const entries = [];
        this.inputs.forEach(function (input, i) {
            if (input instanceof GPUExternalTexture) {
                entries.push({ binding: i, resource: input });
            }
            else if (input instanceof GPUTexture) {
                entries.push({ binding: i, resource: input.createView() });
            }
            else if (input instanceof GPUBuffer) {
                entries.push({ binding: i, resource: { buffer: input } });
            }
        });
        entries.push({ binding: this.inputs.length, resource: this.sampler });
        return this.device.createBindGroup({
            layout: this.pipeline.getBindGroupLayout(0),
            entries
        });
    }
}
exports["default"] = DisplayLayer;


//# sourceURL=webpack://WebSR/./src/layers/anime4k/display.ts?
}

/***/ }),

/***/ "./src/layers/anime4k/display_1x.ts":
/*!******************************************!*\
  !*** ./src/layers/anime4k/display_1x.ts ***!
  \******************************************/
/***/ ((__unused_webpack_module, exports, __webpack_require__) => {

{
Object.defineProperty(exports, "__esModule", ({ value: true }));
const base_render_layer_1 = __webpack_require__(/*! ../base_render_layer */ "./src/layers/base_render_layer.ts");
class DisplayLayer extends base_render_layer_1.default {
    constructor(inputs, output) {
        super(inputs, output);
        this.label = "DisplayLayer";
        this.vertexScale = {
            width: 1,
            height: 1
        };
        this.sampler = this.device.createSampler({
            addressModeU: "repeat",
            addressModeV: "repeat",
            magFilter: "linear",
            minFilter: "linear",
            mipmapFilter: "linear",
        });
    }
    lazyLoadSetup() {
        const externalTexture = this.inputs[1] instanceof GPUExternalTexture;
        const textureLoad = externalTexture ? 'textureSampleBaseClampToEdge(inputTexture, ourSampler, input.tex_coord)' :
            'textureSample(inputTexture, ourSampler, input.tex_coord)';
        this.shader = this.device.createShaderModule({
            label: `${this.label}-shader`,
            code: `
                
                   ${this.defaultVertexShader()}
                   @group(0) @binding(0) var<storage, read_write> inputBuffer0: array<vec4f>;
                   @group(0) @binding(1) var inputTexture: ${externalTexture ? 'texture_external' : 'texture_2d<f32>'};
                   @group(0) @binding(2) var ourSampler: sampler;
                  
                   @fragment fn fragmentMain(input: VertexShaderOutput) -> @location(0) vec4f {
                      
                        let x = ${this.resolution.width}.0*(input.tex_coord.x);
                        let y = ${this.resolution.height}.0*(input.tex_coord.y);
                        
                        let y2 = u32(floor(y));
                        let x2 = u32(floor(x));
                        
                        let i = y2*${Math.floor(this.resolution.width)} +  x2;
      
                        let bicubic = ${textureLoad};
                        
                        return bicubic + inputBuffer0[i];
                    
                      }            
            `
        });
        this.pipeline = this.device.createRenderPipeline(this.defaultPipelineConfig());
        this.bindGroup = this.defaultBindGroup();
        this.renderPassDescriptor = this.defaultRenderPassDescriptor();
    }
    defaultBindGroup() {
        const entries = [];
        this.inputs.forEach(function (input, i) {
            if (input instanceof GPUExternalTexture) {
                entries.push({ binding: i, resource: input });
            }
            else if (input instanceof GPUTexture) {
                entries.push({ binding: i, resource: input.createView() });
            }
            else if (input instanceof GPUBuffer) {
                entries.push({ binding: i, resource: { buffer: input } });
            }
        });
        entries.push({ binding: this.inputs.length, resource: this.sampler });
        return this.device.createBindGroup({
            layout: this.pipeline.getBindGroupLayout(0),
            entries
        });
    }
}
exports["default"] = DisplayLayer;


//# sourceURL=webpack://WebSR/./src/layers/anime4k/display_1x.ts?
}

/***/ }),

/***/ "./src/layers/anime4k/display_3c.ts":
/*!******************************************!*\
  !*** ./src/layers/anime4k/display_3c.ts ***!
  \******************************************/
/***/ ((__unused_webpack_module, exports, __webpack_require__) => {

{
Object.defineProperty(exports, "__esModule", ({ value: true }));
const base_render_layer_1 = __webpack_require__(/*! ../base_render_layer */ "./src/layers/base_render_layer.ts");
class DisplayLayer3C extends base_render_layer_1.default {
    constructor(inputs, output) {
        super(inputs, output);
        this.label = "DisplayLayer3C";
        this.vertexScale = {
            width: 1,
            height: 1
        };
        this.sampler = this.device.createSampler({
            addressModeU: "repeat",
            addressModeV: "repeat",
            magFilter: "linear",
            minFilter: "linear",
            mipmapFilter: "linear",
        });
    }
    lazyLoadSetup() {
        const externalTexture = this.inputs[3] instanceof GPUExternalTexture;
        const textureLoad = externalTexture ? 'textureSampleBaseClampToEdge(inputTexture, ourSampler, input.tex_coord)' :
            'textureSample(inputTexture, ourSampler, input.tex_coord)';
        this.shader = this.device.createShaderModule({
            label: `${this.label}-shader`,
            code: `
                
                   ${this.defaultVertexShader()}
                   @group(0) @binding(0) var<storage, read_write> inputBuffer0: array<vec4f>;
                   @group(0) @binding(1) var<storage, read_write> inputBuffer1: array<vec4f>;
                   @group(0) @binding(2) var<storage, read_write> inputBuffer2: array<vec4f>;
                   @group(0) @binding(3) var inputTexture: ${externalTexture ? 'texture_external' : 'texture_2d<f32>'};
                   @group(0) @binding(4) var ourSampler: sampler;
                  
                   @fragment fn fragmentMain(input: VertexShaderOutput) -> @location(0) vec4f {
                      
                        let x = ${this.resolution.width}.0*(input.tex_coord.x);
                        let y = ${this.resolution.height}.0*(input.tex_coord.y);
                        
                        let y2 = u32(floor(y));
                        let x2 = u32(floor(x));
                        
                        let i = y2*${Math.floor(this.resolution.width)} +  x2;
                       
                        let x_floor  = u32(fract(x)*2.0);
                        let y_floor  = u32(fract(y)*2.0);
                        
                        //I don t know, I think this is right? I found this by trial and error
                        let c_index: u32 = x_floor + y_floor*2;  
        
                        let value = inputBuffer0[i][c_index];
                        let value1 = inputBuffer1[i][c_index];
                        let value2 = inputBuffer2[i][c_index];
                        
                        let bicubic = ${textureLoad};
                        
                        return bicubic + vec4f(value, value1, value2, value2);
                    
                      }            
            `
        });
        this.pipeline = this.device.createRenderPipeline(this.defaultPipelineConfig());
        this.bindGroup = this.defaultBindGroup();
        this.renderPassDescriptor = this.defaultRenderPassDescriptor();
    }
    defaultPipelineConfig() {
        return {
            label: `${this.label}-pipeline`,
            layout: 'auto',
            vertex: {
                module: this.shader,
                entryPoint: 'vertexMain',
            },
            fragment: {
                module: this.shader,
                entryPoint: 'fragmentMain',
                targets: [{ format: this.output.format }],
            },
        };
    }
    defaultBindGroup() {
        const entries = [];
        this.inputs.forEach(function (input, i) {
            if (input instanceof GPUExternalTexture) {
                entries.push({ binding: i, resource: input });
            }
            else if (input instanceof GPUTexture) {
                entries.push({ binding: i, resource: input.createView() });
            }
            else if (input instanceof GPUBuffer) {
                entries.push({ binding: i, resource: { buffer: input } });
            }
        });
        entries.push({ binding: this.inputs.length, resource: this.sampler });
        return this.device.createBindGroup({
            layout: this.pipeline.getBindGroupLayout(0),
            entries
        });
    }
}
exports["default"] = DisplayLayer3C;


//# sourceURL=webpack://WebSR/./src/layers/anime4k/display_3c.ts?
}

/***/ }),

/***/ "./src/layers/base_compute_layer.ts":
/*!******************************************!*\
  !*** ./src/layers/base_compute_layer.ts ***!
  \******************************************/
/***/ ((__unused_webpack_module, exports, __webpack_require__) => {

{
Object.defineProperty(exports, "__esModule", ({ value: true }));
const base_layer_1 = __webpack_require__(/*! ./base_layer */ "./src/layers/base_layer.ts");
class ComputeLayer extends base_layer_1.default {
    constructor(inputTextures, outputBuffer, weights) {
        super(inputTextures, outputBuffer, weights);
        this.num_work_groups = 8;
    }
    createStandardShader(computeShader) {
        return this.device.createShaderModule({
            label: `${this.label}-shader`,
            code: `
              
              ${this.computeShaderInputs()}
              
              ${computeShader}
        `
        });
    }
    computeShaderInputs() {
        const inputs = [];
        for (let i = 0; i < this.inputs.length; i++) {
            if (this.inputs[i] instanceof GPUTexture) {
                inputs.push(`@group(0) @binding(${i}) var inputTexture${i}: texture_2d<f32>;`);
            }
            else if (this.inputs[i] instanceof GPUExternalTexture) {
                inputs.push(`@group(0) @binding(${i}) var inputTexture${i}: texture_external;`);
            }
            else if (this.inputs[i] instanceof GPUBuffer) {
                inputs.push(`@group(0) @binding(${i}) var<storage, read_write> inputBuffer${i}: array<vec4f>;`);
            }
            else {
                console.log(this.inputs[i]);
                throw new Error("Input is undefined or non of the correct input type");
            }
        }
        //  console.log("This layer", this.label);
        // console.log(this.inputs.length);
        this.uniforms.forEach((uniform, i) => {
            inputs.push(`@group(0) @binding(${i + this.inputs.length}) var <uniform> ${uniform.name}: ${uniform.type};`);
        });
        inputs.push(`@group(0) @binding(${this.inputs.length + this.uniforms.length}) var <storage, read_write> outputBuffer: array<vec4f>;`);
        return inputs.join('\n');
    }
    defaultPipelineConfig() {
        return {
            label: `${this.label}-pipeline`,
            layout: 'auto',
            compute: {
                module: this.shader,
                entryPoint: 'main',
            },
        };
    }
    defaultSetup() {
        this.pipeline = this.device.createComputePipeline(this.defaultPipelineConfig());
        this.bindGroup = this.defaultBindGroup();
    }
    lazyLoadSetup() {
    }
    run() {
        const encoder = this.device.createCommandEncoder({ label: this.label });
        if (!this.pipeline)
            this.lazyLoadSetup();
        const pass = encoder.beginComputePass({ label: this.label });
        pass.setPipeline(this.pipeline);
        if (this.hasExternalTexture()) {
            this.bindGroup = this.defaultBindGroup();
        }
        if (this.bindGroup) {
            pass.setBindGroup(0, this.bindGroup);
        }
        // Dividing into work groups speeds up inference. If width or height aren't cleandly divided by work groups, we round to the nearest multiple of work-groups
        // Physically, this means shaving a few pixels (up to num_work_groups-1) off the bottom and right edges of the canvas but users shouldn't notice?
        pass.dispatchWorkgroups(Math.floor(this.resolution.width / this.num_work_groups), Math.floor(this.resolution.height / this.num_work_groups));
        pass.end();
        this.device.queue.submit([encoder.finish()]);
    }
}
exports["default"] = ComputeLayer;


//# sourceURL=webpack://WebSR/./src/layers/base_compute_layer.ts?
}

/***/ }),

/***/ "./src/layers/base_layer.ts":
/*!**********************************!*\
  !*** ./src/layers/base_layer.ts ***!
  \**********************************/
/***/ ((__unused_webpack_module, exports) => {

{
Object.defineProperty(exports, "__esModule", ({ value: true }));
class Layer {
    constructor(inputs, output, weights) {
        this.context = globalThis.context;
        this.device = this.context.device;
        this.resolution = this.context.resolution;
        this.inputs = inputs;
        this.output = output;
        this.uniforms = [];
        this.buffers = {};
        this.weights = weights;
    }
    createUniform(name, type) {
        this.uniforms.push({ name, type });
    }
    setUniform(name, value) {
        const buffer = this.device.createBuffer({
            label: `layer-${this.label}-buffer-${name}`,
            size: value.byteLength,
            usage: GPUBufferUsage.UNIFORM | GPUBufferUsage.COPY_DST,
        });
        this.device.queue.writeBuffer(buffer, /*bufferOffset=*/ 0, value);
        this.buffers[name] = buffer;
    }
    defaultBindGroup() {
        const entries = [];
        this.inputs.forEach(function (input, i) {
            if (input instanceof GPUExternalTexture) {
                entries.push({ binding: i, resource: input });
            }
            else if (input instanceof GPUTexture) {
                entries.push({ binding: i, resource: input.createView() });
            }
            else if (input instanceof GPUBuffer) {
                entries.push({ binding: i, resource: { buffer: input } });
            }
        });
        this.uniforms.forEach((uniform, i) => {
            entries.push({
                binding: i + this.inputs.length,
                resource: {
                    buffer: this.buffers[uniform.name]
                }
            });
        });
        if (this.output instanceof GPUBuffer) {
            entries.push({
                binding: this.inputs.length + this.uniforms.length,
                resource: {
                    buffer: this.output
                }
            });
        }
        if (entries.length === 0)
            return null;
        return this.device.createBindGroup({
            layout: this.pipeline.getBindGroupLayout(0),
            entries
        });
    }
    hasExternalTexture() {
        for (const input of this.inputs) {
            if (input instanceof GPUExternalTexture)
                return true;
        }
        return false;
    }
    lazyLoadSetup() { }
    run() { }
}
exports["default"] = Layer;


//# sourceURL=webpack://WebSR/./src/layers/base_layer.ts?
}

/***/ }),

/***/ "./src/layers/base_render_layer.ts":
/*!*****************************************!*\
  !*** ./src/layers/base_render_layer.ts ***!
  \*****************************************/
/***/ ((__unused_webpack_module, exports, __webpack_require__) => {

{
Object.defineProperty(exports, "__esModule", ({ value: true }));
const base_layer_1 = __webpack_require__(/*! ./base_layer */ "./src/layers/base_layer.ts");
class RenderLayer extends base_layer_1.default {
    constructor(inputs, output, weights) {
        super(inputs, output, weights);
        this.vertexScale = this.context.resolution;
    }
    defaultVertexShader() {
        return `
        
             struct VertexShaderOutput {
                @builtin(position) position: vec4f,
                @location(0) tex_coord: vec2f,
              };

            @vertex
            fn vertexMain( @builtin(vertex_index) vertexIndex : u32) ->  VertexShaderOutput{
                let pos = array(
                // 1st triangle
                vec2f( -1.0,  -1.0),  // center
                vec2f( 1.0,  -1.0),  // right, center
                vec2f( -1.0,  1.0),  // center, top
             
                // 2st triangle
                vec2f( -1.0,  1.0),  // center, top
                vec2f( 1.0,  -1.0),  // right, center
                vec2f( 1.0,  1.0),  // right, top
              );
             
              var vsOutput: VertexShaderOutput;
              let xy = pos[vertexIndex];
              vsOutput.position = vec4f(xy, 0.0, 1.0);
              vsOutput.tex_coord = xy*0.5 + 0.5;
              vsOutput.tex_coord.y = - 1.0* vsOutput.tex_coord.y  + 1.0;
               vsOutput.tex_coord.x =  vsOutput.tex_coord.x*${this.vertexScale.width};
               vsOutput.tex_coord.y =  vsOutput.tex_coord.y*${this.vertexScale.height};
              return vsOutput;
            }
        `;
    }
    defaultPipelineConfig() {
        return {
            label: `${this.label}-pipeline`,
            layout: 'auto',
            vertex: {
                module: this.shader,
                entryPoint: 'vertexMain',
            },
            fragment: {
                module: this.shader,
                entryPoint: 'fragmentMain',
                targets: [{ format: this.output.format }],
            },
        };
    }
    defaultSetup() {
        this.pipeline = this.device.createRenderPipeline(this.defaultPipelineConfig());
        this.bindGroup = this.defaultBindGroup();
        this.renderPassDescriptor = this.defaultRenderPassDescriptor();
    }
    defaultRenderPassDescriptor() {
        return {
            label: `${this.label}-render-pass`,
            colorAttachments: [
                {
                    view: this.output.createView(),
                    clearValue: [0, 0, 0, 1],
                    loadOp: 'clear',
                    storeOp: 'store',
                },
            ],
        };
    }
    createStandardShader(fragmentShader) {
        return this.device.createShaderModule({
            label: `${this.label}-shader`,
            code: `
          
              ${this.defaultVertexShader()}
              
              ${this.fragmentShaderInputs()}
              
              ${fragmentShader}
        `
        });
    }
    fragmentShaderInputs() {
        const inputs = [];
        for (let i = 0; i < this.inputs.length; i++) {
            let type = (this.inputs[i] instanceof GPUTexture) ? 'texture_2d<f32>' : 'texture_external';
            inputs.push(`@group(0) @binding(0) var inputTexture${i}: ${type};`);
        }
        this.uniforms.forEach((uniform, i) => {
            inputs.push(`@group(0) @binding(${i + this.inputs.length}) var <uniform> ${uniform.name}: ${uniform.type};`);
        });
        return inputs.join('\n');
    }
    run() {
        const encoder = this.device.createCommandEncoder({ label: this.label });
        if (!this.pipeline)
            this.lazyLoadSetup();
        const pass = encoder.beginRenderPass(this.renderPassDescriptor);
        pass.setPipeline(this.pipeline);
        if (this.hasExternalTexture()) {
            this.bindGroup = this.defaultBindGroup();
        }
        if (this.bindGroup) {
            pass.setBindGroup(0, this.bindGroup);
        }
        pass.draw(6); // call our vertex shader 6 times
        pass.end();
        this.device.queue.submit([encoder.finish()]);
    }
    setOutput(outputTexture) {
        this.output = outputTexture;
        this.renderPassDescriptor = this.defaultRenderPassDescriptor();
    }
}
exports["default"] = RenderLayer;


//# sourceURL=webpack://WebSR/./src/layers/base_render_layer.ts?
}

/***/ }),

/***/ "./src/layers/utils/gaussian.ts":
/*!**************************************!*\
  !*** ./src/layers/utils/gaussian.ts ***!
  \**************************************/
/***/ ((__unused_webpack_module, exports, __webpack_require__) => {

{
Object.defineProperty(exports, "__esModule", ({ value: true }));
const base_render_layer_1 = __webpack_require__(/*! ../base_render_layer */ "./src/layers/base_render_layer.ts");
class GuassianLayer extends base_render_layer_1.default {
    constructor(inputTextures, outputTexture) {
        super(inputTextures, outputTexture);
        this.label = "Gaussian";
        this.createUniform("gaussian", "array<vec3f, 3>");
        this.createUniform("kernel_offsets", "array<vec4f, 9>");
        this.shader = this.createStandardShader(`
        
                  @fragment fn fragmentMain(input: VertexShaderOutput) -> @location(0) vec4f {
                  
                     var val  = 0.0;
                      
                     for(var i = 0u; i < 3; i++){
                     
                        let a = vec3f(
                            textureLoad(inputTexture0, vec2<i32>(input.tex_coord + kernel_offsets[i*3].xy), 0).x,
                            textureLoad(inputTexture0, vec2<i32>(input.tex_coord + kernel_offsets[i*3].xy), 0).x,
                            textureLoad(inputTexture0, vec2<i32>(input.tex_coord + kernel_offsets[i*3].xy), 0).x
                        );
                        
                        val += dot(a, gaussian[i]);
                      
                    } 
                  
                    
                    return vec4f(val, val, val, 1.0);
                  }                 
        `);
        this.setUniform("gaussian", new Float32Array([
            0.0675, 0.125, 0.0675, 0.0,
            0.125, 0.250, 0.1250, 0.0,
            0.0675, 0.125, 0.0675, 0.0
        ]));
        this.setUniform("kernel_offsets", new Float32Array([
            -1, -1, 0, 0,
            0, -1, 0, 0,
            1, -1, 0, 0,
            -1, 0, 0, 0,
            0, 0, 0, 0,
            1, 0, 0, 0,
            -1, 1, 0, 0,
            0, 1, 0, 0,
            1, 1, 0, 0,
        ]));
        this.defaultSetup();
    }
}
exports["default"] = GuassianLayer;


//# sourceURL=webpack://WebSR/./src/layers/utils/gaussian.ts?
}

/***/ }),

/***/ "./src/layers/utils/rgb_2_yuv.ts":
/*!***************************************!*\
  !*** ./src/layers/utils/rgb_2_yuv.ts ***!
  \***************************************/
/***/ ((__unused_webpack_module, exports, __webpack_require__) => {

{
Object.defineProperty(exports, "__esModule", ({ value: true }));
const base_render_layer_1 = __webpack_require__(/*! ../base_render_layer */ "./src/layers/base_render_layer.ts");
class RGB2YUV extends base_render_layer_1.default {
    constructor(inputTextures, outputTexture) {
        super(inputTextures, outputTexture);
        this.createUniform("rgb2yuv", "mat3x3f");
        this.shader = this.createStandardShader(`
        
               @fragment fn fragmentMain(input: VertexShaderOutput) -> @location(0) vec4f {
              
                    let color = textureLoad(inputTexture0, vec2<i32>(input.tex_coord), 0);       
                    let yuv = rgb2yuv*color.xyz;
          
                return vec4f(yuv, 1.0);
              }     
        `);
        this.setUniform("rgb2yuv", new Float32Array([
            0.299, -0.1473, 0.615, 1.0,
            0.587, -.2886, -.51499, 1.0,
            0.114, 0.436, -.1001, 1.0
        ]));
        this.defaultSetup();
    }
}
exports["default"] = RGB2YUV;


//# sourceURL=webpack://WebSR/./src/layers/utils/rgb_2_yuv.ts?
}

/***/ }),

/***/ "./src/main.ts":
/*!*********************!*\
  !*** ./src/main.ts ***!
  \*********************/
/***/ (function(__unused_webpack_module, exports, __webpack_require__) {

{
var __awaiter = (this && this.__awaiter) || function (thisArg, _arguments, P, generator) {
    function adopt(value) { return value instanceof P ? value : new P(function (resolve) { resolve(value); }); }
    return new (P || (P = Promise))(function (resolve, reject) {
        function fulfilled(value) { try { step(generator.next(value)); } catch (e) { reject(e); } }
        function rejected(value) { try { step(generator["throw"](value)); } catch (e) { reject(e); } }
        function step(result) { result.done ? resolve(result.value) : adopt(result.value).then(fulfilled, rejected); }
        step((generator = generator.apply(thisArg, _arguments || [])).next());
    });
};
Object.defineProperty(exports, "__esModule", ({ value: true }));
const context_1 = __webpack_require__(/*! ./context */ "./src/context.ts");
const renderer_1 = __webpack_require__(/*! ./renderer */ "./src/renderer.ts");
const network_list_1 = __webpack_require__(/*! ./networks/network_list */ "./src/networks/network_list.ts");
const utils_1 = __webpack_require__(/*! ./utils */ "./src/utils.ts");
class WebSR {
    constructor(params) {
        this.initialized = false;
        if (!network_list_1.NetworkList[params.network_name])
            throw Error(`Network ${params.network_name} is not defined or implemented`);
        this.params = params;
        this.canvas = params.canvas;
        this.scale = network_list_1.NetworkScales[params.network_name];
        this.debug = params.debug;
        // If resolution is provided, initialize immediately
        if (params.resolution) {
            this.resolution = params.resolution;
            this.initialize();
        }
    }
    initialize() {
        if (!this.resolution) {
            throw new Error("Cannot initialize without resolution");
        }
        // Resize canvas to match output resolution
        this.canvas.width = this.resolution.width * this.scale;
        this.canvas.height = this.resolution.height * this.scale;
        // Create context
        this.context = new context_1.default(this.params.gpu, this.resolution, this.canvas, this.scale, this.debug);
        globalThis.context = this.context;
        // Create network
        this.network = new network_list_1.NetworkList[this.params.network_name](this.params.weights);
        // Create renderer
        this.renderer = new renderer_1.default(this.network);
        this.initialized = true;
    }
    updateResolution(newResolution) {
        var _a, _b;
        // Check if resolution actually changed
        if (this.resolution &&
            this.resolution.width === newResolution.width &&
            this.resolution.height === newResolution.height) {
            return; // No change needed
        }
        console.log(`Resolution changed from ${(_a = this.resolution) === null || _a === void 0 ? void 0 : _a.width}x${(_b = this.resolution) === null || _b === void 0 ? void 0 : _b.height} to ${newResolution.width}x${newResolution.height}`);
        this.resolution = newResolution;
        // Clean up old resources if they exist
        if (this.context) {
            this.context.destroy();
        }
        // Re-initialize with new resolution
        this.initialize();
    }
    switchNetwork(network, weights) {
        if (!network_list_1.NetworkList[network])
            throw Error(`Network ${network} is not defined or implemented`);
        this.network = new network_list_1.NetworkList[network](weights);
        if (this.renderer) {
            this.renderer.switchNetwork(this.network);
        }
    }
    static initWebGPU() {
        return __awaiter(this, void 0, void 0, function* () {
            if (!navigator.gpu)
                return false;
            const adapter = yield navigator.gpu.requestAdapter();
            if (!adapter)
                return false;
            const device = yield adapter.requestDevice();
            if (!device)
                return false;
            return device;
        });
    }
    render(source) {
        return __awaiter(this, void 0, void 0, function* () {
            if (!source) {
                throw new Error("render() requires a source parameter");
            }
            // Detect resolution from source
            const sourceResolution = {
                width: (0, utils_1.getSourceWidth)(source),
                height: (0, utils_1.getSourceHeight)(source)
            };
            // Initialize if not yet initialized, or update if resolution changed
            if (!this.initialized) {
                this.resolution = sourceResolution;
                this.initialize();
            }
            else if (sourceResolution.width !== this.resolution.width ||
                sourceResolution.height !== this.resolution.height) {
                this.updateResolution(sourceResolution);
            }
            yield this.renderer.render(source);
        });
    }
    destroy() {
        return __awaiter(this, void 0, void 0, function* () {
            if (this.context) {
                this.context.destroy();
            }
        });
    }
}
exports["default"] = WebSR;


//# sourceURL=webpack://WebSR/./src/main.ts?
}

/***/ }),

/***/ "./src/networks/anime4k/cnn-2x-l.ts":
/*!******************************************!*\
  !*** ./src/networks/anime4k/cnn-2x-l.ts ***!
  \******************************************/
/***/ (function(__unused_webpack_module, exports, __webpack_require__) {

{
var __awaiter = (this && this.__awaiter) || function (thisArg, _arguments, P, generator) {
    function adopt(value) { return value instanceof P ? value : new P(function (resolve) { resolve(value); }); }
    return new (P || (P = Promise))(function (resolve, reject) {
        function fulfilled(value) { try { step(generator.next(value)); } catch (e) { reject(e); } }
        function rejected(value) { try { step(generator["throw"](value)); } catch (e) { reject(e); } }
        function step(result) { result.done ? resolve(result.value) : adopt(result.value).then(fulfilled, rejected); }
        step((generator = generator.apply(thisArg, _arguments || [])).next());
    });
};
Object.defineProperty(exports, "__esModule", ({ value: true }));
const base_network_1 = __webpack_require__(/*! ../base_network */ "./src/networks/base_network.ts");
const conv2d_3x4_1 = __webpack_require__(/*! ../../layers/anime4k/conv2d-3x4 */ "./src/layers/anime4k/conv2d-3x4.ts");
const display_3c_1 = __webpack_require__(/*! ../../layers/anime4k/display_3c */ "./src/layers/anime4k/display_3c.ts");
const conv2d_16x4_1 = __webpack_require__(/*! ../../layers/anime4k/conv2d-16x4 */ "./src/layers/anime4k/conv2d-16x4.ts");
const conv2d_112x4_1 = __webpack_require__(/*! ../../layers/anime4k/conv2d-112x4 */ "./src/layers/anime4k/conv2d-112x4.ts");
const conv2d_concat2_1 = __webpack_require__(/*! ../../layers/anime4k/conv2d-concat2 */ "./src/layers/anime4k/conv2d-concat2.ts");
const utils_1 = __webpack_require__(/*! ../../utils */ "./src/utils.ts");
class Anime4KCNN2XL extends base_network_1.default {
    constructor(weights) {
        super(weights);
    }
    model() {
        const layers = [];
        const weights = this.weights.layers;
        const context = this.context;
        layers.push(new conv2d_3x4_1.default([context.input], context.buffer('conv2d_tf'), weights['conv2d_tf']));
        layers.push(new conv2d_3x4_1.default([context.input], context.buffer('conv2d_tf1'), weights['conv2d_tf1']));
        for (let i = 1; i < 7; i++) {
            let source = (i == 1) ? `conv2d_tf` : `conv2d_${i - 1}_tf`;
            layers.push(new conv2d_16x4_1.default([context.buffer(source), context.buffer(source + "1")], context.buffer(`conv2d_${i}_tf`), weights[`conv2d_${i}_tf`]));
            layers.push(new conv2d_16x4_1.default([context.buffer(source), context.buffer(source + "1")], context.buffer(`conv2d_${i}_tf1`), weights[`conv2d_${i}_tf1`]));
        }
        for (let c = 0; c < 3; c++) {
            const sources_0 = [];
            const sources_1 = [];
            for (let i = 0; i < 7; i++) {
                let source = (i == 0) ? `conv2d_tf` : `conv2d_${i}_tf`;
                sources_0.push(context.buffer(source));
                sources_1.push(context.buffer(source + "1"));
            }
            const dest = (c == 0) ? `conv2d_last_tf` : `conv2d_last_tf${c}`;
            layers.push(new conv2d_112x4_1.default(sources_0, context.buffer(`conv2d_last_${c}_pt1`), weights[dest], true));
            layers.push(new conv2d_112x4_1.default(sources_1, context.buffer(`conv2d_last_${c}_pt2`), weights[dest], false));
            layers.push(new conv2d_concat2_1.default([context.buffer(`conv2d_last_${c}_pt1`), context.buffer(`conv2d_last_${c}_pt2`)], context.buffer(dest), weights[dest]));
        }
        const paint = new display_3c_1.default([context.buffer('conv2d_last_tf'), context.buffer('conv2d_last_tf1'), context.buffer('conv2d_last_tf2'), context.input], context.texture('output'));
        layers.push(paint);
        return layers;
    }
    feedForward(source) {
        return __awaiter(this, void 0, void 0, function* () {
            if ((0, utils_1.isHTMLVideoElement)(source) || (0, utils_1.isVideoFrame)(source)) {
                this.context.input = this.context.device.importExternalTexture({ source });
            }
            else {
                const bitmap = (0, utils_1.isImageBitmap)(source) ? source : yield createImageBitmap(source);
                const width = (0, utils_1.getSourceWidth)(source);
                const height = (0, utils_1.getSourceHeight)(source);
                this.context.device.queue.copyExternalImageToTexture({ source: bitmap }, { texture: this.context.texture('input', { format: "rgba8unorm" }) }, [width, height]);
                this.context.input = this.context.texture('input');
            }
            this.layers[0].inputs[0] = this.context.input;
            this.layers[1].inputs[0] = this.context.input;
            this.layers[this.layers.length - 1].inputs[3] = this.context.input;
            this.layers[0].lazyLoadSetup();
            this.layers[1].lazyLoadSetup();
            this.layers[this.layers.length - 1].lazyLoadSetup();
            this.layers.forEach(function (layer) {
                layer.run();
            });
        });
    }
}
exports["default"] = Anime4KCNN2XL;


//# sourceURL=webpack://WebSR/./src/networks/anime4k/cnn-2x-l.ts?
}

/***/ }),

/***/ "./src/networks/anime4k/cnn-2x-m.ts":
/*!******************************************!*\
  !*** ./src/networks/anime4k/cnn-2x-m.ts ***!
  \******************************************/
/***/ (function(__unused_webpack_module, exports, __webpack_require__) {

{
var __awaiter = (this && this.__awaiter) || function (thisArg, _arguments, P, generator) {
    function adopt(value) { return value instanceof P ? value : new P(function (resolve) { resolve(value); }); }
    return new (P || (P = Promise))(function (resolve, reject) {
        function fulfilled(value) { try { step(generator.next(value)); } catch (e) { reject(e); } }
        function rejected(value) { try { step(generator["throw"](value)); } catch (e) { reject(e); } }
        function step(result) { result.done ? resolve(result.value) : adopt(result.value).then(fulfilled, rejected); }
        step((generator = generator.apply(thisArg, _arguments || [])).next());
    });
};
Object.defineProperty(exports, "__esModule", ({ value: true }));
const base_network_1 = __webpack_require__(/*! ../base_network */ "./src/networks/base_network.ts");
const conv2d_3x4_1 = __webpack_require__(/*! ../../layers/anime4k/conv2d-3x4 */ "./src/layers/anime4k/conv2d-3x4.ts");
const conv2d_8x4_1 = __webpack_require__(/*! ../../layers/anime4k/conv2d-8x4 */ "./src/layers/anime4k/conv2d-8x4.ts");
const conv2d_56x4_1 = __webpack_require__(/*! ../../layers/anime4k/conv2d-56x4 */ "./src/layers/anime4k/conv2d-56x4.ts");
const display_3c_1 = __webpack_require__(/*! ../../layers/anime4k/display_3c */ "./src/layers/anime4k/display_3c.ts");
const utils_1 = __webpack_require__(/*! ../../utils */ "./src/utils.ts");
class Anime4KCNN2XM extends base_network_1.default {
    constructor(weights) {
        super(weights);
    }
    model() {
        const layers = [];
        const weights = this.weights.layers;
        const context = this.context;
        const conv2d_tf = new conv2d_3x4_1.default([context.input], context.buffer('conv2d_tf'), weights['conv2d_tf']);
        const conv2d_1_tf = new conv2d_8x4_1.default([context.buffer('conv2d_tf')], context.buffer('conv2d_1_tf'), weights['conv2d_1_tf']);
        const conv2d_2_tf = new conv2d_8x4_1.default([context.buffer('conv2d_1_tf')], context.buffer('conv2d_2_tf'), weights['conv2d_2_tf']);
        const conv2d_3_tf = new conv2d_8x4_1.default([context.buffer('conv2d_2_tf')], context.buffer('conv2d_3_tf'), weights['conv2d_3_tf']);
        const conv2d_4_tf = new conv2d_8x4_1.default([context.buffer('conv2d_3_tf')], context.buffer('conv2d_4_tf'), weights['conv2d_4_tf']);
        const conv2d_5_tf = new conv2d_8x4_1.default([context.buffer('conv2d_4_tf')], context.buffer('conv2d_5_tf'), weights['conv2d_5_tf']);
        const conv2d_6_tf = new conv2d_8x4_1.default([context.buffer('conv2d_5_tf')], context.buffer('conv2d_6_tf'), weights['conv2d_6_tf']);
        const conv2d_7_tf = new conv2d_56x4_1.default([context.buffer('conv2d_tf'), context.buffer('conv2d_1_tf'), context.buffer('conv2d_2_tf'), context.buffer('conv2d_3_tf'), context.buffer('conv2d_4_tf'), context.buffer('conv2d_5_tf'), context.buffer('conv2d_6_tf')], context.buffer('conv2d_7_tf'), weights['conv2d_7_tf']);
        const conv2d_7_tf1 = new conv2d_56x4_1.default([context.buffer('conv2d_tf'), context.buffer('conv2d_1_tf'), context.buffer('conv2d_2_tf'), context.buffer('conv2d_3_tf'), context.buffer('conv2d_4_tf'), context.buffer('conv2d_5_tf'), context.buffer('conv2d_6_tf')], context.buffer('conv2d_7_tf1'), weights['conv2d_7_tf1']);
        const conv2d_7_tf2 = new conv2d_56x4_1.default([context.buffer('conv2d_tf'), context.buffer('conv2d_1_tf'), context.buffer('conv2d_2_tf'), context.buffer('conv2d_3_tf'), context.buffer('conv2d_4_tf'), context.buffer('conv2d_5_tf'), context.buffer('conv2d_6_tf')], context.buffer('conv2d_7_tf2'), weights['conv2d_7_tf2']);
        const paint = new display_3c_1.default([context.buffer('conv2d_7_tf'), context.buffer('conv2d_7_tf1'), context.buffer('conv2d_7_tf2'), context.input], context.texture('output'));
        layers.push(conv2d_tf, conv2d_1_tf, conv2d_2_tf, conv2d_3_tf, conv2d_4_tf, conv2d_5_tf, conv2d_6_tf, conv2d_7_tf, conv2d_7_tf1, conv2d_7_tf2, paint);
        return layers;
    }
    feedForward(source) {
        return __awaiter(this, void 0, void 0, function* () {
            if ((0, utils_1.isHTMLVideoElement)(source) || (0, utils_1.isVideoFrame)(source)) {
                this.context.input = this.context.device.importExternalTexture({ source });
            }
            else {
                const bitmap = (0, utils_1.isImageBitmap)(source) ? source : yield createImageBitmap(source);
                const width = (0, utils_1.getSourceWidth)(source);
                const height = (0, utils_1.getSourceHeight)(source);
                this.context.device.queue.copyExternalImageToTexture({ source: bitmap }, { texture: this.context.texture('input', { format: "rgba8unorm" }) }, [width, height]);
                this.context.input = this.context.texture('input');
            }
            this.layers[0].inputs[0] = this.context.input;
            this.layers[this.layers.length - 1].inputs[3] = this.context.input;
            this.layers[0].lazyLoadSetup();
            this.layers[this.layers.length - 1].lazyLoadSetup();
            this.layers.forEach(function (layer) {
                layer.run();
            });
        });
    }
}
exports["default"] = Anime4KCNN2XM;


//# sourceURL=webpack://WebSR/./src/networks/anime4k/cnn-2x-m.ts?
}

/***/ }),

/***/ "./src/networks/anime4k/cnn-2x-s.ts":
/*!******************************************!*\
  !*** ./src/networks/anime4k/cnn-2x-s.ts ***!
  \******************************************/
/***/ (function(__unused_webpack_module, exports, __webpack_require__) {

{
var __awaiter = (this && this.__awaiter) || function (thisArg, _arguments, P, generator) {
    function adopt(value) { return value instanceof P ? value : new P(function (resolve) { resolve(value); }); }
    return new (P || (P = Promise))(function (resolve, reject) {
        function fulfilled(value) { try { step(generator.next(value)); } catch (e) { reject(e); } }
        function rejected(value) { try { step(generator["throw"](value)); } catch (e) { reject(e); } }
        function step(result) { result.done ? resolve(result.value) : adopt(result.value).then(fulfilled, rejected); }
        step((generator = generator.apply(thisArg, _arguments || [])).next());
    });
};
Object.defineProperty(exports, "__esModule", ({ value: true }));
const base_network_1 = __webpack_require__(/*! ../base_network */ "./src/networks/base_network.ts");
const conv2d_3x4_1 = __webpack_require__(/*! ../../layers/anime4k/conv2d-3x4 */ "./src/layers/anime4k/conv2d-3x4.ts");
const conv2d_8x4_1 = __webpack_require__(/*! ../../layers/anime4k/conv2d-8x4 */ "./src/layers/anime4k/conv2d-8x4.ts");
const display_1 = __webpack_require__(/*! ../../layers/anime4k/display */ "./src/layers/anime4k/display.ts");
const utils_1 = __webpack_require__(/*! ../../utils */ "./src/utils.ts");
class Anime4KCNN2XS extends base_network_1.default {
    constructor(weights) {
        super(weights);
    }
    model() {
        const layers = [];
        const weights = this.weights.layers;
        const context = this.context;
        const conv2d_tf = new conv2d_3x4_1.default([context.input], context.buffer('conv2d_tf'), weights['conv2d_tf']);
        const conv2d_1_tf = new conv2d_8x4_1.default([context.buffer('conv2d_tf')], context.buffer('conv2d_1_tf'), weights['conv2d_1_tf']);
        const conv2d_2_tf = new conv2d_8x4_1.default([context.buffer('conv2d_1_tf')], context.buffer('conv2d_2_tf'), weights['conv2d_2_tf']);
        const conv2d_last_tf = new conv2d_8x4_1.default([context.buffer('conv2d_2_tf')], context.buffer('conv2d_last_tf'), weights['conv2d_last_tf']);
        const paint = new display_1.default([context.buffer('conv2d_last_tf'), context.input], context.texture('output'));
        layers.push(conv2d_tf, conv2d_1_tf, conv2d_2_tf, conv2d_last_tf, paint);
        return layers;
    }
    feedForward(source) {
        return __awaiter(this, void 0, void 0, function* () {
            if ((0, utils_1.isHTMLVideoElement)(source) || (0, utils_1.isVideoFrame)(source)) {
                this.context.input = this.context.device.importExternalTexture({ source });
            }
            else {
                const bitmap = (0, utils_1.isImageBitmap)(source) ? source : yield createImageBitmap(source);
                const width = (0, utils_1.getSourceWidth)(source);
                const height = (0, utils_1.getSourceHeight)(source);
                this.context.device.queue.copyExternalImageToTexture({ source: bitmap }, { texture: this.context.texture('input', { format: "rgba8unorm" }) }, [width, height]);
                this.context.input = this.context.texture('input');
            }
            this.layers[0].inputs[0] = this.context.input;
            this.layers[this.layers.length - 1].inputs[1] = this.context.input;
            this.layers[0].lazyLoadSetup();
            this.layers[this.layers.length - 1].lazyLoadSetup();
            this.layers.forEach(function (layer) {
                layer.run();
            });
        });
    }
}
exports["default"] = Anime4KCNN2XS;


//# sourceURL=webpack://WebSR/./src/networks/anime4k/cnn-2x-s.ts?
}

/***/ }),

/***/ "./src/networks/anime4k/cnn-restore-l.ts":
/*!***********************************************!*\
  !*** ./src/networks/anime4k/cnn-restore-l.ts ***!
  \***********************************************/
/***/ (function(__unused_webpack_module, exports, __webpack_require__) {

{
var __awaiter = (this && this.__awaiter) || function (thisArg, _arguments, P, generator) {
    function adopt(value) { return value instanceof P ? value : new P(function (resolve) { resolve(value); }); }
    return new (P || (P = Promise))(function (resolve, reject) {
        function fulfilled(value) { try { step(generator.next(value)); } catch (e) { reject(e); } }
        function rejected(value) { try { step(generator["throw"](value)); } catch (e) { reject(e); } }
        function step(result) { result.done ? resolve(result.value) : adopt(result.value).then(fulfilled, rejected); }
        step((generator = generator.apply(thisArg, _arguments || [])).next());
    });
};
Object.defineProperty(exports, "__esModule", ({ value: true }));
const base_network_1 = __webpack_require__(/*! ../base_network */ "./src/networks/base_network.ts");
const conv2d_3x4_1 = __webpack_require__(/*! ../../layers/anime4k/conv2d-3x4 */ "./src/layers/anime4k/conv2d-3x4.ts");
const conv2d_16x4_1 = __webpack_require__(/*! ../../layers/anime4k/conv2d-16x4 */ "./src/layers/anime4k/conv2d-16x4.ts");
const display_1x_1 = __webpack_require__(/*! ../../layers/anime4k/display_1x */ "./src/layers/anime4k/display_1x.ts");
const utils_1 = __webpack_require__(/*! ../../utils */ "./src/utils.ts");
class Anime4KCNNRL extends base_network_1.default {
    constructor(weights) {
        super(weights);
    }
    model() {
        const layers = [];
        const weights = this.weights.layers;
        const context = this.context;
        layers.push(new conv2d_3x4_1.default([context.input], context.buffer('conv2d_tf'), weights['conv2d_tf']));
        layers.push(new conv2d_3x4_1.default([context.input], context.buffer('conv2d_tf1'), weights['conv2d_tf1']));
        for (let i = 1; i < 4; i++) {
            let source = (i == 1) ? `conv2d_tf` : `conv2d_${i - 1}_tf`;
            layers.push(new conv2d_16x4_1.default([context.buffer(source), context.buffer(source + "1")], context.buffer(`conv2d_${i}_tf`), weights[`conv2d_${i}_tf`]));
            layers.push(new conv2d_16x4_1.default([context.buffer(source), context.buffer(source + "1")], context.buffer(`conv2d_${i}_tf1`), weights[`conv2d_${i}_tf1`]));
        }
        layers.push(new conv2d_16x4_1.default([context.buffer('conv2d_3_tf'), context.buffer('conv2d_3_tf1')], context.buffer(`conv2d_out_tf`), weights[`conv2d_out_tf`]));
        const paint = new display_1x_1.default([context.buffer('conv2d_out_tf'), context.input], context.texture('output'));
        layers.push(paint);
        return layers;
    }
    feedForward(source) {
        return __awaiter(this, void 0, void 0, function* () {
            if ((0, utils_1.isHTMLVideoElement)(source) || (0, utils_1.isVideoFrame)(source)) {
                this.context.input = this.context.device.importExternalTexture({ source });
            }
            else {
                const bitmap = (0, utils_1.isImageBitmap)(source) ? source : yield createImageBitmap(source);
                const width = (0, utils_1.getSourceWidth)(source);
                const height = (0, utils_1.getSourceHeight)(source);
                this.context.device.queue.copyExternalImageToTexture({ source: bitmap }, { texture: this.context.texture('input', { format: "rgba8unorm" }) }, [width, height]);
                this.context.input = this.context.texture('input');
            }
            this.layers[0].inputs[0] = this.context.input;
            this.layers[1].inputs[0] = this.context.input;
            this.layers[this.layers.length - 1].inputs[1] = this.context.input;
            this.layers.forEach(function (layer) {
                layer.run();
            });
        });
    }
}
exports["default"] = Anime4KCNNRL;


//# sourceURL=webpack://WebSR/./src/networks/anime4k/cnn-restore-l.ts?
}

/***/ }),

/***/ "./src/networks/anime4k/cnn-restore-m.ts":
/*!***********************************************!*\
  !*** ./src/networks/anime4k/cnn-restore-m.ts ***!
  \***********************************************/
/***/ (function(__unused_webpack_module, exports, __webpack_require__) {

{
var __awaiter = (this && this.__awaiter) || function (thisArg, _arguments, P, generator) {
    function adopt(value) { return value instanceof P ? value : new P(function (resolve) { resolve(value); }); }
    return new (P || (P = Promise))(function (resolve, reject) {
        function fulfilled(value) { try { step(generator.next(value)); } catch (e) { reject(e); } }
        function rejected(value) { try { step(generator["throw"](value)); } catch (e) { reject(e); } }
        function step(result) { result.done ? resolve(result.value) : adopt(result.value).then(fulfilled, rejected); }
        step((generator = generator.apply(thisArg, _arguments || [])).next());
    });
};
Object.defineProperty(exports, "__esModule", ({ value: true }));
const base_network_1 = __webpack_require__(/*! ../base_network */ "./src/networks/base_network.ts");
const conv2d_3x4_1 = __webpack_require__(/*! ../../layers/anime4k/conv2d-3x4 */ "./src/layers/anime4k/conv2d-3x4.ts");
const conv2d_8x4_1 = __webpack_require__(/*! ../../layers/anime4k/conv2d-8x4 */ "./src/layers/anime4k/conv2d-8x4.ts");
const conv2d_56x4_1 = __webpack_require__(/*! ../../layers/anime4k/conv2d-56x4 */ "./src/layers/anime4k/conv2d-56x4.ts");
const display_1x_1 = __webpack_require__(/*! ../../layers/anime4k/display_1x */ "./src/layers/anime4k/display_1x.ts");
const utils_1 = __webpack_require__(/*! ../../utils */ "./src/utils.ts");
class Anime4KCNNRM extends base_network_1.default {
    constructor(weights) {
        super(weights);
    }
    model() {
        const layers = [];
        const weights = this.weights.layers;
        const context = this.context;
        const conv2d_tf = new conv2d_3x4_1.default([context.input], context.buffer('conv2d_tf'), weights['conv2d_tf']);
        const conv2d_1_tf = new conv2d_8x4_1.default([context.buffer('conv2d_tf')], context.buffer('conv2d_1_tf'), weights['conv2d_1_tf']);
        const conv2d_2_tf = new conv2d_8x4_1.default([context.buffer('conv2d_1_tf')], context.buffer('conv2d_2_tf'), weights['conv2d_2_tf']);
        const conv2d_3_tf = new conv2d_8x4_1.default([context.buffer('conv2d_2_tf')], context.buffer('conv2d_3_tf'), weights['conv2d_3_tf']);
        const conv2d_4_tf = new conv2d_8x4_1.default([context.buffer('conv2d_3_tf')], context.buffer('conv2d_4_tf'), weights['conv2d_4_tf']);
        const conv2d_5_tf = new conv2d_8x4_1.default([context.buffer('conv2d_4_tf')], context.buffer('conv2d_5_tf'), weights['conv2d_5_tf']);
        const conv2d_6_tf = new conv2d_8x4_1.default([context.buffer('conv2d_5_tf')], context.buffer('conv2d_6_tf'), weights['conv2d_6_tf']);
        const conv2d_out_tf = new conv2d_56x4_1.default([context.buffer('conv2d_tf'), context.buffer('conv2d_1_tf'), context.buffer('conv2d_2_tf'), context.buffer('conv2d_3_tf'), context.buffer('conv2d_4_tf'), context.buffer('conv2d_5_tf'), context.buffer('conv2d_6_tf')], context.buffer('conv2d_out_tf'), weights['conv2d_out_tf']);
        const paint = new display_1x_1.default([context.buffer('conv2d_out_tf'), context.input], context.texture('output'));
        layers.push(conv2d_tf, conv2d_1_tf, conv2d_2_tf, conv2d_3_tf, conv2d_4_tf, conv2d_5_tf, conv2d_6_tf, conv2d_out_tf, paint);
        return layers;
    }
    feedForward(source) {
        return __awaiter(this, void 0, void 0, function* () {
            if ((0, utils_1.isHTMLVideoElement)(source) || (0, utils_1.isVideoFrame)(source)) {
                this.context.input = this.context.device.importExternalTexture({ source });
            }
            else {
                const bitmap = (0, utils_1.isImageBitmap)(source) ? source : yield createImageBitmap(source);
                const width = (0, utils_1.getSourceWidth)(source);
                const height = (0, utils_1.getSourceHeight)(source);
                this.context.device.queue.copyExternalImageToTexture({ source: bitmap }, { texture: this.context.texture('input', { format: "rgba8unorm" }) }, [width, height]);
                this.context.input = this.context.texture('input');
            }
            this.layers[0].inputs[0] = this.context.input;
            this.layers[1].inputs[0] = this.context.input;
            this.layers[this.layers.length - 1].inputs[1] = this.context.input;
            this.layers.forEach(function (layer) {
                layer.run();
            });
        });
    }
}
exports["default"] = Anime4KCNNRM;


//# sourceURL=webpack://WebSR/./src/networks/anime4k/cnn-restore-m.ts?
}

/***/ }),

/***/ "./src/networks/anime4k/cnn-restore-s.ts":
/*!***********************************************!*\
  !*** ./src/networks/anime4k/cnn-restore-s.ts ***!
  \***********************************************/
/***/ (function(__unused_webpack_module, exports, __webpack_require__) {

{
var __awaiter = (this && this.__awaiter) || function (thisArg, _arguments, P, generator) {
    function adopt(value) { return value instanceof P ? value : new P(function (resolve) { resolve(value); }); }
    return new (P || (P = Promise))(function (resolve, reject) {
        function fulfilled(value) { try { step(generator.next(value)); } catch (e) { reject(e); } }
        function rejected(value) { try { step(generator["throw"](value)); } catch (e) { reject(e); } }
        function step(result) { result.done ? resolve(result.value) : adopt(result.value).then(fulfilled, rejected); }
        step((generator = generator.apply(thisArg, _arguments || [])).next());
    });
};
Object.defineProperty(exports, "__esModule", ({ value: true }));
const base_network_1 = __webpack_require__(/*! ../base_network */ "./src/networks/base_network.ts");
const conv2d_3x4_1 = __webpack_require__(/*! ../../layers/anime4k/conv2d-3x4 */ "./src/layers/anime4k/conv2d-3x4.ts");
const conv2d_8x4_1 = __webpack_require__(/*! ../../layers/anime4k/conv2d-8x4 */ "./src/layers/anime4k/conv2d-8x4.ts");
const display_1x_1 = __webpack_require__(/*! ../../layers/anime4k/display_1x */ "./src/layers/anime4k/display_1x.ts");
const utils_1 = __webpack_require__(/*! ../../utils */ "./src/utils.ts");
class Anime4KCNNRS extends base_network_1.default {
    constructor(weights) {
        super(weights);
    }
    model() {
        const layers = [];
        const weights = this.weights.layers;
        const context = this.context;
        const conv2d_tf = new conv2d_3x4_1.default([context.input], context.buffer('conv2d_tf'), weights['conv2d_tf']);
        const conv2d_1_tf = new conv2d_8x4_1.default([context.buffer('conv2d_tf')], context.buffer('conv2d_1_tf'), weights['conv2d_1_tf']);
        const conv2d_2_tf = new conv2d_8x4_1.default([context.buffer('conv2d_1_tf')], context.buffer('conv2d_2_tf'), weights['conv2d_2_tf']);
        const conv2d_last_tf = new conv2d_8x4_1.default([context.buffer('conv2d_2_tf')], context.buffer('conv2d_out_tf'), weights['conv2d_out_tf']);
        const paint = new display_1x_1.default([context.buffer('conv2d_out_tf'), context.input], context.texture('output'));
        layers.push(conv2d_tf, conv2d_1_tf, conv2d_2_tf, conv2d_last_tf, paint);
        return layers;
    }
    feedForward(source) {
        return __awaiter(this, void 0, void 0, function* () {
            if ((0, utils_1.isHTMLVideoElement)(source) || (0, utils_1.isVideoFrame)(source)) {
                this.context.input = this.context.device.importExternalTexture({ source });
            }
            else {
                const bitmap = (0, utils_1.isImageBitmap)(source) ? source : yield createImageBitmap(source);
                const width = (0, utils_1.getSourceWidth)(source);
                const height = (0, utils_1.getSourceHeight)(source);
                this.context.device.queue.copyExternalImageToTexture({ source: bitmap }, { texture: this.context.texture('input', { format: "rgba8unorm" }) }, [width, height]);
                this.context.input = this.context.texture('input');
            }
            this.layers[0].inputs[0] = this.context.input;
            this.layers[this.layers.length - 1].inputs[1] = this.context.input;
            this.layers.forEach(function (layer) {
                layer.run();
            });
        });
    }
}
exports["default"] = Anime4KCNNRS;


//# sourceURL=webpack://WebSR/./src/networks/anime4k/cnn-restore-s.ts?
}

/***/ }),

/***/ "./src/networks/base_network.ts":
/*!**************************************!*\
  !*** ./src/networks/base_network.ts ***!
  \**************************************/
/***/ (function(__unused_webpack_module, exports) {

{
var __awaiter = (this && this.__awaiter) || function (thisArg, _arguments, P, generator) {
    function adopt(value) { return value instanceof P ? value : new P(function (resolve) { resolve(value); }); }
    return new (P || (P = Promise))(function (resolve, reject) {
        function fulfilled(value) { try { step(generator.next(value)); } catch (e) { reject(e); } }
        function rejected(value) { try { step(generator["throw"](value)); } catch (e) { reject(e); } }
        function step(result) { result.done ? resolve(result.value) : adopt(result.value).then(fulfilled, rejected); }
        step((generator = generator.apply(thisArg, _arguments || [])).next());
    });
};
Object.defineProperty(exports, "__esModule", ({ value: true }));
class NeuralNetwork {
    constructor(weights) {
        this.weights = weights;
        this.context = globalThis.context;
        this.layers = this.model();
    }
    model() {
        return [];
    }
    lastLayer() {
        return this.layers[this.layers.length - 1];
    }
    feedForward(source) {
        return __awaiter(this, void 0, void 0, function* () {
            this.layers.forEach(layer => {
                layer.run();
            });
        });
    }
}
exports["default"] = NeuralNetwork;


//# sourceURL=webpack://WebSR/./src/networks/base_network.ts?
}

/***/ }),

/***/ "./src/networks/network_list.ts":
/*!**************************************!*\
  !*** ./src/networks/network_list.ts ***!
  \**************************************/
/***/ ((__unused_webpack_module, exports, __webpack_require__) => {

{
Object.defineProperty(exports, "__esModule", ({ value: true }));
exports.NetworkScales = exports.NetworkList = void 0;
const cnn_2x_s_1 = __webpack_require__(/*! ./anime4k/cnn-2x-s */ "./src/networks/anime4k/cnn-2x-s.ts");
const cnn_2x_m_1 = __webpack_require__(/*! ./anime4k/cnn-2x-m */ "./src/networks/anime4k/cnn-2x-m.ts");
const cnn_2x_l_1 = __webpack_require__(/*! ./anime4k/cnn-2x-l */ "./src/networks/anime4k/cnn-2x-l.ts");
const cnn_restore_l_1 = __webpack_require__(/*! ./anime4k/cnn-restore-l */ "./src/networks/anime4k/cnn-restore-l.ts");
const cnn_restore_m_1 = __webpack_require__(/*! ./anime4k/cnn-restore-m */ "./src/networks/anime4k/cnn-restore-m.ts");
const cnn_restore_s_1 = __webpack_require__(/*! ./anime4k/cnn-restore-s */ "./src/networks/anime4k/cnn-restore-s.ts");
const poc_network_1 = __webpack_require__(/*! ./poc_network */ "./src/networks/poc_network.ts");
exports.NetworkList = {
    "anime4k/cnn-2x-s": cnn_2x_s_1.default,
    "anime4k/cnn-2x-m": cnn_2x_m_1.default,
    "anime4k/cnn-2x-l": cnn_2x_l_1.default,
    "anime4k/cnn-restore-s": cnn_restore_s_1.default,
    "anime4k/cnn-restore-m": cnn_restore_m_1.default,
    "anime4k/cnn-restore-l": cnn_restore_l_1.default,
    "sb2702/blur-poc": poc_network_1.default
};
exports.NetworkScales = {
    "anime4k/cnn-2x-s": 2,
    "anime4k/cnn-2x-m": 2,
    "anime4k/cnn-2x-l": 2,
    "anime4k/cnn-restore-s": 1,
    "anime4k/cnn-restore-m": 1,
    "anime4k/cnn-restore-l": 1,
    "sb2702/blur-poc": 1
};


//# sourceURL=webpack://WebSR/./src/networks/network_list.ts?
}

/***/ }),

/***/ "./src/networks/poc_network.ts":
/*!*************************************!*\
  !*** ./src/networks/poc_network.ts ***!
  \*************************************/
/***/ ((__unused_webpack_module, exports, __webpack_require__) => {

{
Object.defineProperty(exports, "__esModule", ({ value: true }));
const base_network_1 = __webpack_require__(/*! ./base_network */ "./src/networks/base_network.ts");
const rgb_2_yuv_1 = __webpack_require__(/*! ../layers/utils/rgb_2_yuv */ "./src/layers/utils/rgb_2_yuv.ts");
const gaussian_1 = __webpack_require__(/*! ../layers/utils/gaussian */ "./src/layers/utils/gaussian.ts");
class PoCNetwork extends base_network_1.default {
    constructor() {
        super();
    }
    model() {
        const layers = [];
        const context = this.context;
        layers.push(new rgb_2_yuv_1.default([context.texture('input')], context.texture('yuv')));
        layers.push(new gaussian_1.default([context.texture('yuv')], context.texture('output')));
        return layers;
    }
}
exports["default"] = PoCNetwork;


//# sourceURL=webpack://WebSR/./src/networks/poc_network.ts?
}

/***/ }),

/***/ "./src/renderer.ts":
/*!*************************!*\
  !*** ./src/renderer.ts ***!
  \*************************/
/***/ (function(__unused_webpack_module, exports, __webpack_require__) {

{
var __awaiter = (this && this.__awaiter) || function (thisArg, _arguments, P, generator) {
    function adopt(value) { return value instanceof P ? value : new P(function (resolve) { resolve(value); }); }
    return new (P || (P = Promise))(function (resolve, reject) {
        function fulfilled(value) { try { step(generator.next(value)); } catch (e) { reject(e); } }
        function rejected(value) { try { step(generator["throw"](value)); } catch (e) { reject(e); } }
        function step(result) { result.done ? resolve(result.value) : adopt(result.value).then(fulfilled, rejected); }
        step((generator = generator.apply(thisArg, _arguments || [])).next());
    });
};
Object.defineProperty(exports, "__esModule", ({ value: true }));
const display_1 = __webpack_require__(/*! ./layers/anime4k/display */ "./src/layers/anime4k/display.ts");
const base_render_layer_1 = __webpack_require__(/*! ./layers/base_render_layer */ "./src/layers/base_render_layer.ts");
const utils_1 = __webpack_require__(/*! ./utils */ "./src/utils.ts");
class WebSRRenderer {
    constructor(network, source) {
        this.context = globalThis.context;
        this.network = network;
        this.source = source;
        this.active = false;
    }
    switchNetwork(network) {
        this.network = network;
    }
    start() {
        return __awaiter(this, void 0, void 0, function* () {
            if (this.context.destroyed) {
                throw new Error("WebSR instance was destroyed");
            }
            this.active = true;
            yield this.renderStep();
        });
    }
    stop() {
        return __awaiter(this, void 0, void 0, function* () {
            this.active = false;
            if (this.vfc && this.source && (0, utils_1.isHTMLVideoElement)(this.source))
                this.source.cancelVideoFrameCallback(this.vfc);
        });
    }
    renderStep() {
        return __awaiter(this, void 0, void 0, function* () {
            const lastLayer = this.network.lastLayer();
            if (lastLayer instanceof display_1.default)
                lastLayer.setOutput(this.context.context.getCurrentTexture());
            yield this.render();
            if (this.active && this.source && (0, utils_1.isHTMLVideoElement)(this.source)) {
                this.vfc = this.source.requestVideoFrameCallback(this.renderStep.bind(this));
            }
        });
    }
    render(source) {
        return __awaiter(this, void 0, void 0, function* () {
            const lastLayer = this.network.lastLayer();
            if (lastLayer instanceof base_render_layer_1.default)
                lastLayer.setOutput(this.context.context.getCurrentTexture());
            yield this.network.feedForward(source ? source : this.source);
        });
    }
}
exports["default"] = WebSRRenderer;


//# sourceURL=webpack://WebSR/./src/renderer.ts?
}

/***/ }),

/***/ "./src/utils.ts":
/*!**********************!*\
  !*** ./src/utils.ts ***!
  \**********************/
/***/ ((__unused_webpack_module, exports) => {

{
Object.defineProperty(exports, "__esModule", ({ value: true }));
exports.isMainThread = isMainThread;
exports.isHTMLVideoElement = isHTMLVideoElement;
exports.isHTMLImageElement = isHTMLImageElement;
exports.isImageBitmap = isImageBitmap;
exports.isVideoFrame = isVideoFrame;
exports.isVideoSource = isVideoSource;
exports.isImageSource = isImageSource;
exports.getSourceWidth = getSourceWidth;
exports.getSourceHeight = getSourceHeight;
/**
 * Check if we're running on the main thread (not in a worker)
 */
function isMainThread() {
    return typeof HTMLVideoElement !== 'undefined';
}
/**
 * Check if a source is a video element (main thread only)
 */
function isHTMLVideoElement(source) {
    return typeof HTMLVideoElement !== 'undefined' && source instanceof HTMLVideoElement;
}
/**
 * Check if a source is an image element (main thread only)
 */
function isHTMLImageElement(source) {
    return typeof HTMLImageElement !== 'undefined' && source instanceof HTMLImageElement;
}
/**
 * Check if a source is an ImageBitmap (works in both contexts)
 */
function isImageBitmap(source) {
    return typeof ImageBitmap !== 'undefined' && source instanceof ImageBitmap;
}
/**
 * Check if a source is a VideoFrame (worker context)
 */
function isVideoFrame(source) {
    return typeof VideoFrame !== 'undefined' && source instanceof VideoFrame;
}
/**
 * Check if a source is any type of video source
 */
function isVideoSource(source) {
    return isHTMLVideoElement(source) || isVideoFrame(source);
}
/**
 * Check if a source is any type of image source
 */
function isImageSource(source) {
    return isHTMLImageElement(source) || isImageBitmap(source);
}
/**
 * Get the width of a media source
 */
function getSourceWidth(source) {
    if (isHTMLVideoElement(source))
        return source.videoWidth;
    if (isHTMLImageElement(source))
        return source.naturalWidth;
    if (isVideoFrame(source))
        return source.displayWidth;
    if (isImageBitmap(source))
        return source.width;
    return 0;
}
/**
 * Get the height of a media source
 */
function getSourceHeight(source) {
    if (isHTMLVideoElement(source))
        return source.videoHeight;
    if (isHTMLImageElement(source))
        return source.naturalHeight;
    if (isVideoFrame(source))
        return source.displayHeight;
    if (isImageBitmap(source))
        return source.height;
    return 0;
}


//# sourceURL=webpack://WebSR/./src/utils.ts?
}

/***/ })

/******/ 	});
/************************************************************************/
/******/ 	// The module cache
/******/ 	var __webpack_module_cache__ = {};
/******/ 	
/******/ 	// The require function
/******/ 	function __webpack_require__(moduleId) {
/******/ 		// Check if module is in cache
/******/ 		var cachedModule = __webpack_module_cache__[moduleId];
/******/ 		if (cachedModule !== undefined) {
/******/ 			return cachedModule.exports;
/******/ 		}
/******/ 		// Create a new module (and put it into the cache)
/******/ 		var module = __webpack_module_cache__[moduleId] = {
/******/ 			// no module.id needed
/******/ 			// no module.loaded needed
/******/ 			exports: {}
/******/ 		};
/******/ 	
/******/ 		// Execute the module function
/******/ 		__webpack_modules__[moduleId].call(module.exports, module, module.exports, __webpack_require__);
/******/ 	
/******/ 		// Return the exports of the module
/******/ 		return module.exports;
/******/ 	}
/******/ 	
/************************************************************************/
/******/ 	
/******/ 	// startup
/******/ 	// Load entry module and return exports
/******/ 	// This entry module is referenced by other modules so it can't be inlined
/******/ 	var __webpack_exports__ = __webpack_require__("./src/main.ts");
/******/ 	__webpack_exports__ = __webpack_exports__["default"];
/******/ 	
/******/ 	return __webpack_exports__;
/******/ })()
;
});