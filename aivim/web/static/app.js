'use strict';
const el=id=>document.getElementById(id);
let csrf='', capabilities={}, active=null, proposal=null, revision=0, undo=null;
const status=text=>{el('status').textContent=text;};
const clearProposal=()=>{proposal=null;el('apply').disabled=true;el('reject').disabled=true;};
el('code').addEventListener('input',()=>{revision++;if(proposal){clearProposal();status('Stale proposal: document changed. Ask for a fresh proposal.');}});
function models(){el('model').replaceChildren();for(const m of capabilities[el('provider').value]?.models||[]){const option=document.createElement('option');option.value=m;option.textContent=m;el('model').append(option);}}
el('provider').addEventListener('change',models);
async function jsonResponse(response){let data;try{data=await response.json();}catch{throw new Error('Server returned an unreadable response');}if(!response.ok){throw new Error(data.error?.message||'Request failed');}return data;}
fetch('/api/capabilities').then(jsonResponse).then(data=>{csrf=data.csrf_token;capabilities=data.providers;for(const [p,v] of Object.entries(capabilities)){const option=document.createElement('option');option.value=p;option.textContent=p+(v.available?'':' — unavailable');el('provider').append(option);}if(data.selection)el('provider').value=data.selection.provider;models();status('Ready. Review the provider and optional context before sending.');}).catch(err=>status(err.message));
el('submit').addEventListener('click',async()=>{
 if(active)return;
 clearProposal();const controller=new AbortController(),id=crypto.randomUUID(),base=el('code').value,baseRevision=revision;
 active={id,controller};el('submit').disabled=true;el('cancel').disabled=false;status('Pending: contacting selected provider…');
 const action=el('action').value;
 try{
  const data=await fetch('/api/ai-assist',{method:'POST',headers:{'Content-Type':'application/json','X-CSRF-Token':csrf},signal:controller.signal,body:JSON.stringify({request_id:id,action,provider:el('provider').value,model:el('model').value,language:el('language').value,code:base,context:el('context').value,specification:action==='generate'?el('instruction').value:'',query:action==='query'?el('instruction').value:''})}).then(jsonResponse);
  if(active?.id!==id)return;
  if(data.type==='proposal'){
   el('result').textContent=data.proposal.explanation+'\n\n'+data.proposal.diff;
   if(revision!==baseRevision||el('code').value!==base){status('Stale proposal: document changed. Input has been preserved.');return;}
   proposal=data.proposal;el('apply').disabled=false;el('reject').disabled=false;status('Proposal ready. Review its diff, then Apply or Reject.');
  }else{el('result').textContent=data.result;status('Response ready.');}
 }catch(err){if(active?.id===id)status(err.name==='AbortError'?'Cancelled. Input preserved.':err.message);}
 finally{if(active?.id===id){active=null;el('submit').disabled=false;el('cancel').disabled=true;}}
});
el('cancel').addEventListener('click',()=>{if(!active)return;const request=active;active=null;request.controller.abort();fetch('/api/cancel',{method:'POST',headers:{'Content-Type':'application/json','X-CSRF-Token':csrf},body:JSON.stringify({request_id:request.id})}).catch(()=>{});el('submit').disabled=false;el('cancel').disabled=true;status('Cancelled. Input preserved.');});
el('apply').addEventListener('click',()=>{if(!proposal)return;if(el('code').value!==proposal.base_content){clearProposal();status('Stale proposal: document changed.');return;}undo={before:el('code').value,after:proposal.content};el('code').value=proposal.content;revision++;clearProposal();el('undo').disabled=false;status('Proposal applied. Undo is available.');});
el('reject').addEventListener('click',()=>{clearProposal();status('Proposal rejected. Input preserved.');});
el('undo').addEventListener('click',()=>{if(!undo)return;if(el('code').value!==undo.after){status('Document changed after application; copy your edits before undoing.');return;}el('code').value=undo.before;revision++;undo=null;el('undo').disabled=true;status('Applied proposal undone.');});
async function copy(text){try{await navigator.clipboard.writeText(text);status('Copied.');}catch{status('Clipboard unavailable. Select the text and copy it with your browser.');}}
el('copy').addEventListener('click',()=>copy(el('code').value));el('copy-result').addEventListener('click',()=>copy(el('result').textContent));
el('download').addEventListener('click',()=>{const url=URL.createObjectURL(new Blob([el('code').value],{type:'text/plain;charset=utf-8'}));const a=document.createElement('a');a.href=url;a.download='aivim-document.txt';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);status('Document downloaded.');});

el('upload').addEventListener('change',async()=>{
 const file=el('upload').files[0];if(!file)return;
 if(el('code').value&&!window.confirm('Replace the current document? Cancel preserves it so you can copy or download it first.')){el('upload').value='';status('Open cancelled. Current document preserved.');return;}
 if(file.size>20*1024*1024){status('File exceeds the 20 MiB local editing limit. Existing input preserved.');return;}
 try{const text=await file.text();if(text.includes('\0')){status('Binary file cannot be edited. Existing input preserved.');return;}el('code').value=text;revision++;clearProposal();undo=null;el('undo').disabled=true;status('Local file opened. No content has been sent to a provider.');}
 catch{status('File could not be read. Existing input preserved.');}
});
