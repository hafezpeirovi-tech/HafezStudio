/* Creates only a NEW review project. Existing projects are never saved/closed/deleted here.
 * API references: Adobe-CEP/Samples PProPanel Premiere.jsx newProject/createCaptionTrack/save.
 */
$._hafez.finishGlassReview = function (requestJson) {
    var report = {ok:false, mode:"finish_glass", saved:false, caption_created:false,
        publication_ready:false, messages:[], project:"", sequence:"", sequence_id:"", mogrt_count:0};
    function key(p) { return String(new File(p).fsName).replace(/\\/g,"/").toLowerCase(); }
    function requireTarget(request, id) {
        if (!app.project || key(app.project.path) !== key(request.expected_project_path)) throw Error("Active review project changed");
        if (id && (!app.project.activeSequence || String(app.project.activeSequence.sequenceID)!==id)) throw Error("Active review sequence changed");
    }
    function sourceSnapshot(seq) {
        var rows=[];
        for (var media=0;media<2;media++) {
            var tracks=media===0 ? seq.videoTracks : seq.audioTracks;
            for (var t=0;t<2;t++) {
                var track=tracks[t], clips=[];
                for (var i=0;i<track.clips.numItems;i++) {
                    var clip=track.clips[i];
                    clips.push([String(clip.nodeId),String(clip.start.ticks),String(clip.end.ticks),
                        String(clip.inPoint.ticks),String(clip.outPoint.ticks),String(clip.projectItem.getMediaPath()),clip.disabled]);
                }
                rows.push([media,t,track.isMuted(),clips]);
            }
        }
        return $._hafez.stringify(rows);
    }
    function writeNew(path,data) {
        var file=new File(path);
        if (file.exists) throw Error("Bound native plan already exists; no retry");
        file.encoding="UTF-8";
        if (!file.open("w")) throw Error("Cannot create native binding plan");
        file.write($._hafez.stringify(data));file.close();
    }
    try {
        var request=$._hafez.parseJson(requestJson);
        if (request.protocol!=="hafez-glass-finish-v1" || request.mode!=="finish_glass" ||
            request.allow_create_project!==true || request.save_review_project!==true || request.export_movie!==false) throw Error("Unsupported Glass review authority");
        var projectFile=new File(request.expected_project_path), planFile=new File(request.plan_path);
        var xmlFile=new File(request.xml_path), captionsFile=new File(request.captions_path);
        if (projectFile.exists || !/\.prproj$/i.test(projectFile.name) || !planFile.exists || !xmlFile.exists || !captionsFile.exists) throw Error("Expected new project and existing review artifacts");
        if (key(projectFile.parent.fsName)!==key(planFile.parent.fsName) || key(xmlFile.parent.fsName)!==key(planFile.parent.fsName) || key(captionsFile.parent.fsName)!==key(planFile.parent.fsName)) throw Error("Review artifacts must share the isolated folder");
        var plan=$._hafez.readJson(request.plan_path);
        if (plan.style_pack!=="glass" || plan.purpose!=="isolated-native-qa" || plan.publication_ready!==false ||
            key(plan.expected_project_path)!==key(request.expected_project_path) || plan.sequence!==request.expected_sequence_name || plan.expected_sequence_id) throw Error("Unbound isolated Glass plan required");
        var planned=0;
        for (var g=0;g<plan.graphics.length;g++) planned+=plan.graphics[g].template_layers.length;
        if (planned!==request.expected_mogrt_count || plan.sfx_cues.length!==request.expected_sfx_count) throw Error("Native inventory differs from engine result");
        // Never closeDocument(), saveAs() or overwrite an existing project.
        if (app.newProject(projectFile.fsName)!==true) throw Error("Premiere did not create the new review project");
        requireTarget(request);
        report.project=app.project.path;
        if (app.project.sequences.numSequences!==0) throw Error("New review project is not empty");
        var imported=$._hafez.parseJson($._hafez.importXmlRequest($._hafez.stringify({
            protocol:"hafez-native-import-v1",mode:"import_xml",request_id:request.request_id,
            expected_project_path:request.expected_project_path,xml_path:request.xml_path,
            bin_name:"Glass - Current Review",expected_sequence_name:request.expected_sequence_name,
            expected_sequence_names:[request.expected_sequence_name]})));
        if (!imported.ok) throw Error(imported.messages.join(" | "));
        report.sequence_id=imported.sequence_id;report.sequence=imported.sequence;
        requireTarget(request,report.sequence_id);
        var seq=app.project.activeSequence;
        if (seq.videoTracks.numTracks!==4 || seq.audioTracks.numTracks!==5) throw Error("Unexpected native track inventory");
        if (seq.audioTracks[0].isMuted() || !seq.audioTracks[1].isMuted()) throw Error("Original dialogue/muted camera-2 state differs");
        if (seq.audioTracks[2].clips.numItems || seq.audioTracks[4].clips.numItems || seq.audioTracks[3].clips.numItems!==request.expected_sfx_count || seq.audioTracks[3].isMuted()) throw Error("Native SFX/music routing differs");
        for (var a=0;a<plan.sfx_cues.length;a++) {
            var cue=plan.sfx_cues[a], sound=seq.audioTracks[3].clips[a];
            var clock=plan.timeline_mapping.fps;
            var startTicks=Math.round(cue.start_frame*clock[1]*254016000000/clock[0]);
            var endTicks=Math.round(cue.end_frame*clock[1]*254016000000/clock[0]);
            if (String(sound.start.ticks)!==String(startTicks) || String(sound.end.ticks)!==String(endTicks) ||
                sound.disabled || key(sound.projectItem.getMediaPath())!==key(cue.asset_path)) throw Error("Native SFX first-frame sync/path mismatch");
        }
        var before=sourceSnapshot(seq);
        plan.expected_sequence_id=report.sequence_id;
        var boundPath=planFile.parent.fsName+"/Glass-Native-Bound.plan.json";
        writeNew(boundPath,plan);
        var applied=$._hafez.parseJson($._hafez.applyPlan(boundPath,false));
        report.apply=applied;
        if (!applied.ok || applied.failed || applied.disabled || applied.safetyFailures || applied.inserted!==planned) throw Error("Native MOGRT application failed; partial review preserved");
        requireTarget(request,report.sequence_id);
        if (sourceSnapshot(seq)!==before) throw Error("Camera/dialogue changed during MOGRT application");
        report.mogrt_count=applied.inserted;
        var bin=app.project.rootItem.createBin("Glass Captions");
        if (!bin) throw Error("Caption bin creation failed");
        if (!app.project.importFiles([captionsFile.fsName],true,bin,false)) throw Error("SRT import failed");
        if (bin.children.numItems!==1 || key(bin.children[0].getMediaPath())!==key(captionsFile.fsName)) throw Error("Imported caption identity mismatch");
        requireTarget(request,report.sequence_id);
        if (seq.createCaptionTrack(bin.children[0],0)!==true) throw Error("Native caption track creation unconfirmed");
        report.caption_created=true;
        if (sourceSnapshot(seq)!==before) throw Error("Camera/dialogue changed during caption creation");
        // Compositing is a separately reported native visual QA requirement, not fabricated API approval.
        report.compositing_review_required=true;
        report.fonts_provisional=true;
        requireTarget(request,report.sequence_id);
        app.project.save();
        if (!(new File(app.project.path)).exists) throw Error("Saved review project missing");
        report.saved=true;report.ok=true;
        report.messages.push("New native review saved with editable MOGRT, source SFX and captions. Font/compositing/editorial review remains. No movie exported.");
    } catch (error) {
        report.messages.push("Glass review stopped: "+error.message+" | line "+String(error.line||0));
        report.messages.push("Do not resend. Inspect preserved project and native receipt; no existing project was overwritten.");
    }
    return $._hafez.stringify(report);
};
