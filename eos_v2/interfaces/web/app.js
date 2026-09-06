const state={entities:[]};
const $=id=>document.getElementById(id);
async function load(){
  const r=await fetch('/api/v1/industry/packs');
  if(!r.ok){$('status').textContent='Sign in to use EOS';return;}
  const packs=await r.json(); $('status').textContent=`${packs.length||0} industry packs`;
}
function renderEntity(entity){
  $('empty').hidden=true;$('entity').hidden=false;$('title').textContent=entity.label||entity.name;$('version').textContent=`v${entity.version}`;
  const form=$('record');form.innerHTML='';
  (entity.fields||[]).forEach(f=>{const label=document.createElement('label');label.textContent=f.name;const input=document.createElement('input');input.name=f.name;input.required=!!f.required;input.type=f.field_type==='boolean'?'checkbox':(f.field_type==='integer'||f.field_type==='decimal'?'number':f.field_type==='date'?'date':'text');label.appendChild(input);form.appendChild(label)});
}
load().catch(()=>{$('status').textContent='Service unavailable'});