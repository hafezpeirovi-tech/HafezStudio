/* Reels native bridge. Only job-owned copies/new projects are saved. */
$._hafez.runReels = function (requestJson) {
    var report = {ok:false, saved:false, publication_ready:false, sequences:[]};
    function key(p) { return String(new File(p).fsName).replace(/\\/g,"/").toLowerCase(); }
    function pick(project,name) {
        var found=null;
        for(var i=0;i<project.sequences.numSequences;i++) if(project.sequences[i].name===name) {
            if(found) throw Error("Ambiguous sequence name"); found=project.sequences[i];
        }
        if(!found) throw Error("Sequence not found: "+name); return found;
    }
    function openCopy(file) {
        app.openDocument(file.fsName,true,true,true);
        return $._hafez.findOpenProject(file.fsName);
    }
    function time(seconds) { var t=new Time();t.seconds=seconds;return t; }
    function textValue(property,value) {
        var old=property.getValue();
        try {
            var data=$._hafez.parseJson(old);
            if(data.textEditValue!==undefined) data.textEditValue=value;
            else if(data.mTextParam && data.mTextParam.mStyleSheet) data.mTextParam.mStyleSheet.mText=value;
            else throw Error("Unknown Source Text format");
            property.setValue($._hafez.stringify(data),1);
        } catch(e) { if(typeof old==='string' && old.charAt(0)!=='{')property.setValue(value,1);else throw e; }
    }
    try {
        var request=$._hafez.parseJson(requestJson);
        if(request.protocol!=="hafez-reels-v1")throw Error("Invalid Reels protocol");
        if(request.mode==="reels_preview") {
            var previewPlanFile=new File(request.plan_path),previewPlan=$._hafez.readJson(previewPlanFile.fsName);
            var previewProjectFile=new File(previewPlan.expected_project),previewOut=new File(request.output),previewPreset=new File(request.preset);
            if(previewPlan.protocol!=="hafez-reels-v1" || previewProjectFile.name!=="Hafez-Reels.prproj" ||
                key(previewProjectFile.parent.fsName)!==key(previewPlanFile.parent.fsName) ||
                key(previewOut.parent.parent.fsName)!==key(previewPlanFile.parent.fsName) ||
                previewOut.parent.name!=="preview" || previewOut.exists || !previewPreset.exists)throw Error("Invalid isolated preview target");
            var previewClip=null;
            for(var pc=0;pc<previewPlan.clips.length;pc++)if(previewPlan.clips[pc].id===request.sequence)previewClip=previewPlan.clips[pc];
            if(!previewClip)throw Error("Preview sequence is not in this plan");
            var previewProject=openCopy(previewProjectFile),previewSequence=pick(previewProject,request.sequence);
            previewProject.openSequence(previewSequence.sequenceID);
            var previewStart=Number(request.start||0),previewEnd=request.end===undefined?Number(previewSequence.end)/254016000000:Number(request.end);
            if(!isFinite(previewStart)||!isFinite(previewEnd)||previewStart<0||previewEnd<=previewStart||previewEnd>Number(previewSequence.end)/254016000000+0.04)throw Error("Invalid preview range");
            var previousIn=previewSequence.getInPoint(),previousOut=previewSequence.getOutPoint();
            try {
                previewSequence.setInPoint(previewStart);previewSequence.setOutPoint(previewEnd);
                previewSequence.exportAsMediaDirect(previewOut.fsName,previewPreset.fsName,app.encoder.ENCODE_IN_TO_OUT);
            } finally {previewSequence.setInPoint(previousIn);previewSequence.setOutPoint(previousOut);}
            if(!previewOut.exists||previewOut.length===0)throw Error("Preview render did not complete");
            report.ok=true;report.output=previewOut.fsName;report.sequence=previewSequence.name;
            report.duration=previewEnd-previewStart;
            return $._hafez.stringify(report);
        }
        if(request.mode==="reels_export") {
            var source=new File(request.project), out=new File(request.output), preset=new File(request.preset);
            if(source.name!=="Analysis-Source.prproj" || out.exists || !preset.exists || key(source.parent.fsName)!==key(out.parent.fsName))throw Error("Expected isolated analysis copy and new output");
            var project=openCopy(source), seq=pick(project,request.sequence);
            project.openSequence(seq.sequenceID);
            var result=seq.exportAsMediaDirect(out.fsName,preset.fsName,0);
            if(!out.exists || out.length===0)throw Error("Analysis export failed: "+result);
            var settings=seq.getSettings(),frameTicks=Number(seq.timebase);
            report.ok=true;report.output=out.fsName;report.sequence=seq.name;
            report.media={width:settings.videoFrameWidth,height:settings.videoFrameHeight,
                frame_ticks:frameTicks,duration:Number(seq.end)/254016000000};
            return $._hafez.stringify(report);
        }
        if(request.mode!=="reels_finish")throw Error("Unknown Reels operation");
        var planFile=new File(request.plan_path),plan=$._hafez.readJson(planFile.fsName);
        if(plan.protocol!=="hafez-reels-v1" || !plan.clips.length || plan.clips.length>6 || plan.missing_templates.length)throw Error("Invalid or incomplete Reels plan");
        var dest=new File(plan.expected_project);
        if(key(dest.parent.fsName)!==key(planFile.parent.fsName) || dest.name!=="Hafez-Reels.prproj")throw Error("Project outside job");
        var project, sourceSequence=null;
        if(plan.native_source) {
            if(!dest.exists || key(dest.fsName)===key(plan.native_source.path))throw Error("Expected a separate native source copy");
            project=openCopy(dest);sourceSequence=pick(project,plan.native_source.sequence);
            for(var existing=0;existing<project.sequences.numSequences;existing++)for(var planned=0;planned<plan.clips.length;planned++) {
                if(project.sequences[existing].name===plan.clips[planned].id || project.sequences[existing].name===plan.clips[planned].id+" - Source layers")throw Error("Reel sequence already exists; use a new source copy");
            }
            var nativeRate=254016000000/Number(sourceSequence.timebase), requestedRate=plan.source.fps[0]/plan.source.fps[1];
            if(Math.abs(nativeRate-requestedRate)>0.001 || Math.abs(Number(sourceSequence.end)/254016000000-plan.source.duration)>2/nativeRate)throw Error("Analysis export does not match source sequence duration/frame rate");
        } else {
            if(dest.exists)throw Error("Output project already exists; no automatic retry");
            if(!app.newProject(dest.fsName))throw Error("Could not create Reels project");
            project=$._hafez.findOpenProject(dest.fsName);
            var bin=project.rootItem.createBin("Reels Media");
            if(!project.importFiles([plan.xml],true,bin,false))throw Error("Reels XML import failed");
        }
        for(var r=0;r<plan.clips.length;r++) {
            var clip=plan.clips[r], sequence;
            if(sourceSequence) {
                project.openSequence(sourceSequence.sequenceID);
                var oldIn=sourceSequence.getInPoint(),oldOut=sourceSequence.getOutPoint();
                try {
                    sourceSequence.setInPoint(clip.start);sourceSequence.setOutPoint(clip.end);
                    var section=sourceSequence.createSubsequence(true);
                    if(!section)throw Error("Could not extract source subsection");
                    section.name=clip.id+" - Source layers";
                } finally {sourceSequence.setInPoint(oldIn);sourceSequence.setOutPoint(oldOut);}
                sequence=project.createNewSequenceFromClips(clip.id,[section.projectItem],project.rootItem);
                if(!sequence)throw Error("Could not create nested Reel");
                var settings=sequence.getSettings();settings.videoFrameWidth=1080;settings.videoFrameHeight=1920;
                sequence.setSettings(settings);
                var applied=sequence.getSettings();
                if(applied.videoFrameWidth!==1080 || applied.videoFrameHeight!==1920)throw Error("Vertical sequence settings failed");
                var nested=sequence.videoTracks[0].clips[0], motion=null;
                for(var m=0;m<nested.components.numItems;m++) if(nested.components[m].matchName==="AE.ADBE Motion" || nested.components[m].matchName==="ADBE Motion")motion=nested.components[m];
                if(!motion)throw Error("Native Motion controls unavailable");
                // Motion properties use source pixels for scale and normalized sequence coordinates for position.
                var fitted=false,positioned=false;
                for(var p=0;p<motion.properties.numItems;p++) {
                    var prop=motion.properties[p];
                    if(prop.displayName==="Scale") {prop.setValue(Math.max(1080/plan.source.width,1100/plan.source.height)*100,1);fitted=true;}
                    if(prop.displayName==="Position") {prop.setValue([0.5,0.33],1);positioned=true;}
                }
                if(!fitted||!positioned)throw Error("Motion controls could not be configured");
            } else sequence=pick(project,clip.id);
            project.openSequence(sequence.sequenceID);
            for(var c=0;c<clip.motions.length;c++) {
                var cue=clip.motions[c];
                if(!(new File(cue.template_path)).exists)throw Error("Motion template missing");
                var item=sequence.importMGT(cue.template_path,String(Math.round(cue.start*254016000000)),2,0);
                if(!item)throw Error("MOGRT insertion failed");
                var component=item.getMGTComponent(),written=false;
                for(var k=0;k<component.properties.numItems;k++)if(component.properties[k].displayName==="Headline") {
                    textValue(component.properties[k],cue.text);written=true;
                }
                if(!written)throw Error("Editable Headline control missing");
                // The template has a bounded introduction; trimming its end preserves the intro.
                item.end=time(cue.end);
            }
            var captionBin=project.rootItem.createBin(clip.id+" Captions");
            if(!project.importFiles([clip.captions],true,captionBin,false) || captionBin.children.numItems!==1)throw Error("Caption import failed");
            if(sequence.createCaptionTrack(captionBin.children[0],0)!==true)throw Error("Caption track creation failed");
            var marker=sequence.markers.createMarker(0);marker.name="Hafez — بازبینی ریلز";marker.comments=clip.reason;
            report.sequences.push({name:sequence.name,id:String(sequence.sequenceID),motions:clip.motions.length});
        }
        $._hafez.requireProject(dest.fsName,project);project.save();
        report.saved=dest.exists;report.project=dest.fsName;report.ok=report.saved;
        report.review_required=["Persian captions","Layout and fonts","Color and source match"];
    } catch(error) {report.message=String(error.message)+" | line "+String(error.line||0);}
    return $._hafez.stringify(report);
};
