const {contextBridge,ipcRenderer}=require('electron');
contextBridge.exposeInMainWorld('localUpscale',{
 onRequest:callback=>ipcRenderer.on('websr:request',(_,request)=>callback(request)),
 reply:result=>ipcRenderer.send('websr:reply',result)
});
