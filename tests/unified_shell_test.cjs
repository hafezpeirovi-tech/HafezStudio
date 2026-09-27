const {app,BrowserWindow}=require('electron');
const path=require('path');
const assert=require('assert/strict');
app.whenReady().then(async()=>{
 const win=new BrowserWindow({show:false,webPreferences:{contextIsolation:true}});
 await win.loadFile(path.resolve(__dirname,'../app/index.html'));
 for(const [width,height] of [[1920,960],[1366,768]]){
  win.setContentSize(width,height);
  for(const theme of ['dark','light']){
   let baseline;
   for(const view of ['director','planned','upscale','motion','audio','integrations','settings']){
    const result=await win.webContents.executeJavaScript(`(()=>{
     document.documentElement.dataset.theme=${JSON.stringify(theme)};
     document.body.dataset.view=${JSON.stringify(view)};
     document.querySelectorAll('.studio-view').forEach(p=>p.hidden=(p.dataset.youtubeView||p.dataset.workspace)!==${JSON.stringify(view)});
     document.querySelector('#plannedWorkspace').hidden=${JSON.stringify(view)}!=='planned';
     return ['.shell','.sidebar','.brand-mark','.topbar','main'].map(s=>{
      const e=document.querySelector(s),c=getComputedStyle(e),r=e.getBoundingClientRect();
      return {selector:s,width:r.width,x:r.x,y:r.y,background:c.backgroundImage,radius:c.borderRadius};
     });
    })()`);
    if(!baseline)baseline=result;else assert.deepEqual(result,baseline,`${width} ${theme} ${view}: shell changed`);
   }
  }
 }
 win.setContentSize(1920,960);
 await win.webContents.executeJavaScript(`document.documentElement.dataset.theme='dark';document.body.dataset.view='upscale';document.querySelectorAll('.studio-view').forEach(p=>p.hidden=p.dataset.workspace!=='upscale');document.querySelector('#plannedWorkspace').hidden=true;`);
 await new Promise(resolve=>setTimeout(resolve,300));
 require('fs').writeFileSync(path.resolve(__dirname,'../backups/unified-shell-20260927-01/upscale.png'),(await win.webContents.capturePage()).toPNG());
 console.log('PASS: shared shell geometry, glass backgrounds and radii across 7 views, 2 sizes, dark/light (28 states).');
 win.destroy();app.quit();
}).catch(e=>{console.error(e);app.exit(1)});
